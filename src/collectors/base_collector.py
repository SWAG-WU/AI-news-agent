#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据源采集器基类

定义所有采集器的通用接口和基础功能。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging
import asyncio

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import Config, get_config

logger = logging.getLogger(__name__)


class CollectorError(Exception):
    """采集器异常基类"""
    pass


class RateLimitError(CollectorError):
    """限流异常"""
    pass


class ParseError(CollectorError):
    """解析异常"""
    pass


class BaseCollector(ABC):
    """数据源采集器基类"""

    def __init__(self, config: Optional[Config] = None, source_id: Optional[str] = None):
        self.config = config or get_config()
        self.source_id = source_id
        self.session: Optional[aiohttp.ClientSession] = None

        # 获取当前数据源配置
        self.source_config = None
        if source_id:
            for source in self.config.sources.sources:
                if source.id == source_id:
                    self.source_config = source
                    break

        # 限流配置
        self._request_times: List[float] = []
        self._rate_limit = 60  # 默认每分钟60次请求
        if self.source_config and self.source_config.rate_limit:
            self._rate_limit = self.source_config.rate_limit.requests_per_minute or 60

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._init_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self._close_session()

    async def _init_session(self):
        """初始化HTTP会话"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.thresholds.retry.timeout_seconds)
            connector = aiohttp.TCPConnector(limit=10)

            # 代理配置
            proxy = None
            if self.config.https_proxy:
                proxy = self.config.https_proxy

            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                trust_env=True,  # 从环境变量读取代理
            )

    async def _close_session(self):
        """关闭HTTP会话"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _check_rate_limit(self):
        """检查并执行限流"""
        now = asyncio.get_event_loop().time()
        # 移除超过1分钟的请求记录
        self._request_times = [t for t in self._request_times if now - t < 60]

        if len(self._request_times) >= self._rate_limit:
            # 等待直到可以发送请求
            sleep_time = 60 - (now - self._request_times[0])
            if sleep_time > 0:
                logger.debug(f"达到限流阈值，等待 {sleep_time:.2f} 秒")
                await asyncio.sleep(sleep_time)

        self._request_times.append(now)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    )
    async def _fetch(self, url: str, method: str = "GET",
                     headers: Optional[Dict[str, str]] = None,
                     params: Optional[Dict[str, Any]] = None,
                     data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        发送HTTP请求

        Args:
            url: 请求URL
            method: 请求方法
            headers: 请求头
            params: URL参数
            data: 请求体数据

        Returns:
            响应内容文本，失败返回None
        """
        await self._check_rate_limit()

        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html, application/xml, text/xml, */*",
        }
        if headers:
            default_headers.update(headers)

        try:
            async with self.session.request(
                method=method,
                url=url,
                headers=default_headers,
                params=params,
                json=data,
            ) as response:
                response.raise_for_status()
                return await response.text()

        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                raise RateLimitError(f"触发限流: {url}")
            logger.error(f"请求失败 {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"请求异常 {url}: {e}")
            raise

    @abstractmethod
    async def collect(self) -> List[Dict[str, Any]]:
        """
        采集资讯

        Returns:
            资讯列表，每条资讯包含至少以下字段：
            - url: str
            - title: str
            - description: str (可选)
            - published_at: str (可选)
            - source: str
            - category: str
        """
        pass

    def _normalize_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化文章格式

        Args:
            article: 原始文章数据

        Returns:
            标准化后的文章数据
        """
        normalized = {
            "url": article.get("url", ""),
            "title": article.get("title", "").strip(),
            "description": article.get("description", article.get("summary", article.get("abstract", ""))),
            "published_at": article.get("published_at", article.get("date", article.get("pubDate"))),
            "source": article.get("source", self.source_config.name if self.source_config else ""),
            "category": article.get("category", "tech"),
            "author": article.get("author", ""),
            "tags": article.get("tags", []),
            "score": article.get("score", 0),
        }

        # 移除空值
        return {k: v for k, v in normalized.items() if v is not None and v != ""}

    def _is_within_time_window(self, published_at: Optional[str],
                                hours: int = 48) -> bool:
        """
        检查发布时间是否在指定时间窗口内

        Args:
            published_at: 发布时间字符串
            hours: 时间窗口（小时）

        Returns:
            是否在时间窗口内
        """
        if not published_at:
            return True  # 无时间信息时不过滤

        try:
            # 尝试解析多种时间格式
            pub_dt = None
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d",
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S %Z",
            ):
                try:
                    pub_dt = datetime.strptime(published_at, fmt)
                    break
                except ValueError:
                    continue

            if pub_dt is None:
                return True

            cutoff = datetime.now() - timedelta(hours=hours)
            return pub_dt >= cutoff

        except Exception as e:
            logger.warning(f"解析时间失败 {published_at}: {e}")
            return True  # 解析失败时不过滤


class MultiSourceCollector(BaseCollector):
    """多数据源采集器基类"""

    async def collect(self) -> List[Dict[str, Any]]:
        """从多个数据源采集"""
        all_articles = []

        sources = self.config.sources.get_enabled_sources()

        for source in sources:
            try:
                articles = await self._collect_from_source(source)
                all_articles.extend(articles)
                logger.info(f"从 {source.name} 采集到 {len(articles)} 条资讯")
            except Exception as e:
                logger.error(f"从 {source.name} 采集失败: {e}")

        return all_articles

    @abstractmethod
    async def _collect_from_source(self, source) -> List[Dict[str, Any]]:
        """从单个数据源采集"""
        pass
