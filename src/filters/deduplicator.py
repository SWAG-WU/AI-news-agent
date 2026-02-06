#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
去重器

基于URL和内容哈希去除重复资讯。
"""

import logging
from typing import Any, Dict, List, Set, Optional
from difflib import SequenceMatcher

from src.config import Config, get_config
from src.storage import SQLiteStorage

logger = logging.getLogger(__name__)


class Deduplicator:
    """
    去重器

    支持多种去重策略：
    1. URL哈希去重（精确匹配）
    2. 内容哈希去重（标题+描述）
    3. 相似度去重（模糊匹配）
    """

    def __init__(self, storage: Optional[SQLiteStorage] = None, config: Optional[Config] = None):
        self.storage = storage
        self.config = config or get_config()
        self.thresholds = self.config.thresholds.deduplication

        # 用于当前批次的去重缓存
        self._seen_urls: Set[str] = set()
        self._seen_content_hashes: Set[str] = set()

    async def deduplicate(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        去除重复文章

        Args:
            articles: 原始文章列表

        Returns:
            去重后的文章列表
        """
        if not self.thresholds.enabled:
            logger.info("去重功能已禁用")
            return articles

        logger.info(f"开始去重，原始文章数: {len(articles)}")

        unique_articles = []
        duplicate_count = 0

        for article in articles:
            try:
                # 检查是否重复
                is_duplicate, duplicate_type = await self._is_duplicate(article)

                if is_duplicate:
                    duplicate_count += 1
                    logger.debug(f"发现重复文章 ({duplicate_type}): {article.get('title', '')}")
                else:
                    # 标记为已见
                    self._mark_as_seen(article)
                    unique_articles.append(article)

            except Exception as e:
                logger.warning(f"去重检查失败: {e}")
                # 出错时保留文章
                unique_articles.append(article)

        logger.info(f"去重完成: 移除 {duplicate_count} 篇重复文章，剩余 {len(unique_articles)} 篇")
        return unique_articles

    async def _is_duplicate(self, article: Dict[str, Any]) -> tuple[bool, str]:
        """
        检查文章是否重复

        Returns:
            (是否重复, 重复类型)
        """
        method = self.thresholds.method

        # 1. URL哈希去重
        if method in ["url_hash", "both", "all"]:
            if await self._is_duplicate_by_url(article):
                return True, "url"

        # 2. 内容哈希去重
        if method in ["content_hash", "both", "all"]:
            if await self._is_duplicate_by_content_hash(article):
                return True, "content_hash"

        # 3. 相似度去重
        if method in ["similarity", "all"]:
            if await self._is_duplicate_by_similarity(article):
                return True, "similarity"

        return False, ""

    async def _is_duplicate_by_url(self, article: Dict[str, Any]) -> bool:
        """通过URL哈希检查重复"""
        url = article.get("url", "")
        if not url:
            return False

        # 检查当前批次缓存
        if url in self._seen_urls:
            return True

        # 检查数据库（同步方法）
        if self.storage:
            return self.storage.exists(url)

        return False

    async def _is_duplicate_by_content_hash(self, article: Dict[str, Any]) -> bool:
        """通过内容哈希检查重复"""
        title = article.get("title", "")
        description = article.get("description", "")

        content_hash = self._compute_content_hash(title, description)

        # 检查当前批次缓存
        if content_hash in self._seen_content_hashes:
            return True

        # 检查数据库（同步方法）
        if self.storage:
            return self.storage.exists_by_content(title, description)

        return False

    async def _is_duplicate_by_similarity(self, article: Dict[str, Any]) -> bool:
        """通过相似度检查重复"""
        title = article.get("title", "")
        description = article.get("description", "")

        threshold = self.thresholds.similarity_threshold

        # 检查当前批次中的相似文章
        for seen_url in self._seen_urls:
            # 这里需要从某处获取已见文章的标题
            # 简化处理：只检查标题相似度
            pass

        # 检查数据库中的相似文章
        if self.storage:
            similar = await self._find_similar_in_storage(title, description, threshold)
            return similar

        return False

    async def _find_similar_in_storage(self, title: str, description: str,
                                       threshold: float) -> bool:
        """在存储中查找相似文章"""
        if not self.storage:
            return False

        # 获取最近的文章进行比较
        recent_articles = self.storage.get_recent(days=7, limit=100)

        for article in recent_articles:
            # 计算标题相似度
            title_sim = self._similarity(title, article.title)
            if title_sim >= threshold:
                logger.debug(f"发现相似标题: {title} vs {article.title} (sim: {title_sim:.2f})")
                return True

        return False

    def _compute_content_hash(self, title: str, description: str = "") -> str:
        """计算内容哈希"""
        import hashlib

        # 标准化文本
        content = f"{title}|{description}".lower().strip()
        content = " ".join(content.split())  # 移除多余空格

        algorithm = self.thresholds.content_hash_algorithm
        if algorithm == "sha256":
            return hashlib.sha256(content.encode()).hexdigest()
        elif algorithm == "md5":
            import hashlib
            return hashlib.md5(content.encode()).hexdigest()
        else:
            return hashlib.sha256(content.encode()).hexdigest()

    def _similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度（使用SequenceMatcher）"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _mark_as_seen(self, article: Dict[str, Any]):
        """标记文章为已见"""
        url = article.get("url", "")
        if url:
            self._seen_urls.add(url)

        title = article.get("title", "")
        description = article.get("description", "")
        content_hash = self._compute_content_hash(title, description)
        self._seen_content_hashes.add(content_hash)

    def reset(self):
        """重置去重状态（用于新批次）"""
        self._seen_urls.clear()
        self._seen_content_hashes.clear()


class ContentDeduplicator:
    """
    内容去重器（基于文本相似度）

    使用更高级的文本相似度算法，如：
    - TF-IDF + 余弦相似度
    - MinHash
    - SimHash
    """

    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold

    def deduplicate(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于内容相似度去重"""
        unique = []
        seen_texts = []

        for article in articles:
            text = self._get_combined_text(article)

            # 检查与已见文本的相似度
            is_duplicate = False
            for seen_text in seen_texts:
                sim = self._compute_similarity(text, seen_text)
                if sim >= self.threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(article)
                seen_texts.append(text)

        return unique

    def _get_combined_text(self, article: Dict[str, Any]) -> str:
        """获取组合文本"""
        title = article.get("title", "")
        description = article.get("description", "")
        return f"{title} {description}".lower()

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        # 简单实现：使用SequenceMatcher
        # 生产环境可以使用更复杂的算法
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1, text2).ratio()


class FuzzyDeduplicator(Deduplicator):
    """
    模糊去重器

    处理URL不同但内容相同的文章，如：
    - 同一新闻在不同网站的转载
    - 同一论文在不同平台的发布
    """

    async def _is_duplicate_by_similarity(self, article: Dict[str, Any]) -> bool:
        """模糊相似度检查"""
        title = article.get("title", "")
        description = article.get("description", "")

        # 检查是否是已知的转载来源
        if self._is_crosspost(article):
            return True

        # 使用父类的相似度检查
        return await super()._is_duplicate_by_similarity(article)

    def _is_crosspost(self, article: Dict[str, Any]) -> bool:
        """检查是否为转载"""
        url = article.get("url", "")
        title = article.get("title", "")

        # 已知的转载模式
        crosspost_patterns = {
            "arxiv.org": {
                "arxiv-sanity.com",
                "arxiv-vanity.com",
                "paperswithcode.com",
            },
            "github.com": {
                "gomarketing.io",
                "journal.dev",
            },
        }

        for source, mirrors in crosspost_patterns.items():
            if source in url:
                return False  # 原始来源

            for mirror in mirrors:
                if mirror in url:
                    # 检查标题是否匹配（可能略有不同）
                    # 这里简化处理
                    return True

        return False
