#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RSS博客采集器

从各类官方博客和科技媒体采集资讯。
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin

import feedparser
from bs4 import BeautifulSoup

from src.collectors.base_collector import BaseCollector, MultiSourceCollector, CollectorError
from src.config import Config, get_config

logger = logging.getLogger(__name__)


class BlogCollector(MultiSourceCollector):
    """
    RSS博客采集器

    支持从多个RSS源采集资讯。
    """

    async def _collect_from_source(self, source) -> List[Dict[str, Any]]:
        """从单个博客源采集"""
        # 兼容新旧配置格式
        if source.collector and source.collector.get("rss_url"):
            rss_url = source.collector.get("rss_url")
            base_url = source.collector.get("base_url") or source.collector.get("base_url")
        elif source.config:
            rss_url = source.config.rss_url
            base_url = source.config.base_url
        else:
            logger.warning(f"{source._name} 没有配置RSS URL")
            return []

        logger.info(f"开始采集 {source._name} RSS")

        try:
            response_text = await self._fetch(rss_url)
            if not response_text:
                return []

            feed = feedparser.parse(response_text)
            articles = []

            for entry in feed.entries:
                try:
                    article = self._parse_entry(entry, source)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"解析 {source._name} 条目失败: {e}")
                    continue

            logger.info(f"{source._name} 采集到 {len(articles)} 条资讯")
            return articles

        except Exception as e:
            logger.error(f"{source._name} 采集失败: {e}")
            return []

    def _parse_entry(self, entry: Any, source) -> Optional[Dict[str, Any]]:
        """
        解析RSS条目

        Args:
            entry: feedparser条目
            source: 数据源配置

        Returns:
            解析后的文章数据
        """
        # 提取基本信息
        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        description = entry.get("description", "")
        content = entry.get("content", [{"value": ""}])[0].get("value", "")
        published = entry.get("published", entry.get("pubDate", ""))
        author = entry.get("author", "")

        # 提取正文（优先使用content，其次description）
        full_content = content or description

        # 清理HTML标签（如果需要纯文本）
        clean_content = self._clean_html(full_content)

        # 获取完整URL（有些RSS是相对路径）- 兼容新旧格式
        base_url = None
        if source.collector and source.collector.get("base_url"):
            base_url = source.collector.get("base_url")
        elif source.config:
            base_url = source.config.base_url

        url = urljoin(base_url, link) if base_url else link

        # 使用配置中的 category，如果不存在则使用 type 作为 fallback
        article_category = source._category or self._map_category(source._type)

        return {
            "url": url,
            "title": title,
            "description": clean_content[:1000],
            "published_at": published,
            "source": source.name,
            "category": article_category,
            "author": author,
            "tags": self._extract_tags(entry),
            "score": 0,
        }

    def _clean_html(self, html: str) -> str:
        """清理HTML标签，保留纯文本"""
        if not html:
            return ""

        soup = BeautifulSoup(html, "lxml")

        # 移除script和style标签
        for element in soup(["script", "style", "nav", "footer", "aside"]):
            element.decompose()

        # 获取文本
        text = soup.get_text(separator=" ", strip=True)

        # 清理多余空格
        import re
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _map_category(self, source_type: str) -> str:
        """将数据源类型映射到分类"""
        mapping = {
            "blog": "tech",
            "media": "industry",
            "conference": "tech",
        }
        return mapping.get(source_type, "tech")

    def _extract_tags(self, entry: Any) -> List[str]:
        """提取标签"""
        tags = []

        # 从tags字段提取
        if "tags" in entry:
            for tag in entry.tags:
                if "term" in tag:
                    tags.append(tag.term)

        # 从categories字段提取
        if "categories" in entry:
            tags.extend(entry.categories)

        return list(set(tags))


class HuggingFaceCollector(BaseCollector):
    """
    HuggingFace采集器

    采集HuggingFace博客和热门模型。
    """

    def __init__(self, config: Optional[Config] = None, source_id: str = "huggingface_blog"):
        super().__init__(config, source_id)
        self.base_url = "https://huggingface.co"

    async def collect(self, hours: int = 168) -> List[Dict[str, Any]]:
        """采集HuggingFace资讯"""
        all_articles = []

        # 采集博客
        blog_articles = await self._collect_blog(hours)
        all_articles.extend(blog_articles)

        # 采集热门模型
        model_articles = await self._collect_trending_models(hours)
        all_articles.extend(model_articles)

        return all_articles

    async def _collect_blog(self, hours: int) -> List[Dict[str, Any]]:
        """采集HuggingFace博客"""
        rss_url = f"{self.base_url}/blog/feed.xml"

        try:
            response_text = await self._fetch(rss_url)
            if not response_text:
                return []

            feed = feedparser.parse(response_text)
            articles = []

            for entry in feed.entries:
                try:
                    article = self._parse_blog_entry(entry, hours)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"解析HuggingFace博客条目失败: {e}")
                    continue

            return articles

        except Exception as e:
            logger.error(f"HuggingFace博客采集失败: {e}")
            return []

    def _parse_blog_entry(self, entry: Any, hours: int) -> Optional[Dict[str, Any]]:
        """解析HuggingFace博客条目"""
        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        description = entry.get("description", "")
        published = entry.get("published", "")

        if not self._is_within_time_window(published, hours):
            return None

        # 清理HTML
        clean_desc = self._clean_html(description)

        return {
            "url": link,
            "title": title,
            "description": clean_desc[:1000],
            "published_at": published,
            "source": "HuggingFace Blog",
            "category": "tech",
            "tags": self._extract_tags(entry),
            "score": 0,
        }

    async def _collect_trending_models(self, hours: int = 168) -> List[Dict[str, Any]]:
        """采集HuggingFace热门模型"""
        # HuggingFace没有公开的trending API，这里简化处理
        # 实际需要爬取或使用第三方API
        logger.info("HuggingFace热门模型采集暂未实现")
        return []

    def _clean_html(self, html: str) -> str:
        """清理HTML标签"""
        if not html:
            return ""

        soup = BeautifulSoup(html, "lxml")
        for element in soup(["script", "style"]):
            element.decompose()
        text = soup.get_text(separator=" ", strip=True)

        import re
        return re.sub(r"\s+", " ", text).strip()

    def _extract_tags(self, entry: Any) -> List[str]:
        """提取标签"""
        tags = []
        if "tags" in entry:
            for tag in entry.tags:
                if "term" in tag:
                    tags.append(tag.term)
        return tags


class TechMediaCollector(BlogCollector):
    """
    科技媒体采集器

    专门采集MIT Technology Review等科技媒体。
    """

    async def _collect_from_source(self, source) -> List[Dict[str, Any]]:
        """从科技媒体采集"""
        if source.type != "media":
            return await super()._collect_from_source(source)

        # 科技媒体可能需要特殊处理
        # 例如：过滤AI相关文章
        articles = await super()._collect_from_source(source)

        # 过滤AI相关文章
        filtered = [a for a in articles if self._is_ai_related(a)]
        logger.info(f"{source.name} AI相关文章: {len(filtered)}/{len(articles)}")

        return filtered

    def _is_ai_related(self, article: Dict[str, Any]) -> bool:
        """检查文章是否与AI相关"""
        config = get_config()
        keywords = config.keywords.get_all_keywords()

        text = f"{article.get('title', '')} {article.get('description', '')}".lower()

        return any(keyword.lower() in text for keyword in keywords)
