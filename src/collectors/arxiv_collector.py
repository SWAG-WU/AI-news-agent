#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
arXiv论文采集器

从arXiv采集AI相关论文。
"""

import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote

import feedparser

from src.collectors.base_collector import BaseCollector, CollectorError
from src.config import Config, get_config

logger = logging.getLogger(__name__)


class ArxivCollector(BaseCollector):
    """arXiv论文采集器"""

    # arXiv CS.AI 相关的分类
    CATEGORIES = [
        "cs.AI",    # Artificial Intelligence
        "cs.CL",    # Computation and Language
        "cs.LG",    # Machine Learning
        "cs.CV",    # Computer Vision
        "cs.NE",    # Neural and Evolutionary Computing
        "stat.ML",  # Machine Learning (Statistics)
    ]

    def __init__(self, config: Optional[Config] = None, source_id: str = "arxiv_cs_ai"):
        super().__init__(config, source_id)
        self.base_url = "http://export.arxiv.org/api/query"

    async def collect(self, hours: int = 168, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        采集arXiv论文

        Args:
            hours: 时间窗口（小时）
            max_results: 最大结果数

        Returns:
            论文列表
        """
        logger.info(f"开始采集arXiv论文，时间窗口: {hours}小时")

        # 构建查询
        query = self._build_query()
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }

        try:
            # 发送请求
            url = f"{self.base_url}?{urlencode(params)}"
            response_text = await self._fetch(url)

            if not response_text:
                logger.warning("arXiv API返回空响应")
                return []

            # 解析响应
            feed = feedparser.parse(response_text)
            articles = []

            for entry in feed.entries:
                try:
                    article = self._parse_entry(entry, hours)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"解析arXiv条目失败: {e}")
                    continue

            logger.info(f"arXiv采集完成，获得 {len(articles)} 篇论文")
            return articles

        except Exception as e:
            logger.error(f"arXiv采集失败: {e}")
            raise CollectorError(f"arXiv采集失败: {e}")

    def _build_query(self) -> str:
        """构建arXiv搜索查询"""
        # 新格式：使用 collector.params.search_query
        if self.source_config and self.source_config.collector:
            search_query = self.source_config.collector.get("params", {}).get("search_query")
            if search_query:
                return search_query

        # 旧格式兼容：config.search_query
        if self.source_config and self.source_config.config and self.source_config.config.search_query:
            return self.source_config.config.search_query

        # 默认：查询AI相关分类
        cat_query = " OR ".join([f"cat:{cat}" for cat in self.CATEGORIES])
        return cat_query

    def _parse_entry(self, entry: Any, hours: int) -> Optional[Dict[str, Any]]:
        """
        解析arXiv条目

        Args:
            entry: feedparser条目
            hours: 时间窗口

        Returns:
            解析后的文章数据，或None（不在时间窗口内）
        """
        # 提取基本信息
        arxiv_id = self._extract_arxiv_id(entry.id)
        title = entry.title.strip().replace("\n", " ")
        authors = [author.name for author in entry.get("authors", [])]
        summary = entry.get("summary", "").strip()
        published = entry.get("published", "")

        # 检查时间窗口
        if not self._is_within_time_window(published, hours):
            return None

        # 构建URL
        url = f"https://arxiv.org/abs/{arxiv_id}"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        # 提取主要作者/机构
        primary_author = authors[0] if authors else ""
        institution = self._extract_institution(entry)

        # 构建描述（去除摘要中的换行和多余空格）
        description = re.sub(r"\s+", " ", summary).strip()

        return {
            "url": url,
            "title": title,
            "description": description[:1000],  # 限制长度
            "published_at": published,
            "source": "arXiv",
            "category": "academic",
            "author": primary_author,
            "authors": authors,
            "institution": institution,
            "arxiv_id": arxiv_id,
            "pdf_url": pdf_url,
            "tags": self._extract_categories(entry),
            "score": 0,  # 稍后计算
        }

    def _extract_arxiv_id(self, entry_id: str) -> str:
        """从arXiv URL提取论文ID"""
        # arXiv ID格式: arxiv.org/abs/2301.12345 or arxiv.org/abs/cs/1234567
        match = re.search(r"arxiv\.org/abs/([^/]+)", entry_id)
        if match:
            return match.group(1)
        return entry_id

    def _extract_institution(self, entry: Any) -> str:
        """从作者信息中提取机构"""
        # 尝试从作者注释中提取机构
        # arXiv格式通常在作者名后带机构注释
        authors = entry.get("authors", [])
        if authors and hasattr(authors[0], "affiliation"):
            return authors[0].affiliation
        return ""

    def _extract_categories(self, entry: Any) -> List[str]:
        """提取论文分类标签"""
        tags = []
        for tag in entry.get("tags", []):
            if "term" in tag:
                tags.append(tag["term"])
        return tags


class ArxivSanityCollector(BaseCollector):
    """
    arXiv Sanity采集器

    从arxiv-sanity.com获取热门论文（需要额外抓取）
    """

    BASE_URL = "https://arxiv-sanity.com"

    async def collect(self, hours: int = 48) -> List[Dict[str, Any]]:
        """采集arXiv Sanity热门论文"""
        logger.info("开始采集arXiv Sanity热门论文")

        # arXiv Sanity提供top/trending API
        url = f"{self.BASE_URL}/api/trending"

        try:
            response_text = await self._fetch(url)
            if not response_text:
                return []

            import json
            data = json.loads(response_text)

            articles = []
            for item in data.get("results", []):
                article = self._parse_sanity_item(item, hours)
                if article:
                    articles.append(article)

            logger.info(f"arXiv Sanity采集完成，获得 {len(articles)} 篇论文")
            return articles

        except Exception as e:
            logger.error(f"arXiv Sanity采集失败: {e}")
            return []

    def _parse_sanity_item(self, item: Dict[str, Any], hours: int) -> Optional[Dict[str, Any]]:
        """解析arXiv Sanity条目"""
        published = item.get("published", "")

        if not self._is_within_time_window(published, hours):
            return None

        arxiv_id = item.get("uid", "")
        title = item.get("title", "").strip()
        summary = item.get("summary", "").strip()
        authors = item.get("authors", [])

        # arXiv Sanity提供点赞数作为热度指标
        votes = item.get("votes", 0)
        comments = item.get("comments", 0)

        return {
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "title": title,
            "description": summary[:1000],
            "published_at": published,
            "source": "arXiv Sanity",
            "category": "tech",
            "author": authors[0] if authors else "",
            "authors": authors,
            "arxiv_id": arxiv_id,
            "score": votes + comments * 2,  # 计算热度分
        }
