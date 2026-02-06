#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
关键词过滤器

根据关键词配置过滤资讯。
"""

import logging
from typing import Any, Dict, List
import re

from src.config import Config, get_config

logger = logging.getLogger(__name__)


class KeywordFilter:
    """
    关键词过滤器

    根据关键词配置筛选资讯，保留包含相关关键词的资讯。
    """

    def __init__(self, config: Config = None):
        self.config = config or get_config()
        self.keywords_config = self.config.keywords

        # 预编译关键词正则表达式（提高性能）
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """预编译关键词正则表达式"""
        patterns = {}

        for category_name, category in self.keywords_config.categories.items():
            compiled = []
            for keyword in category.keywords:
                try:
                    # 不区分大小写，支持单词边界
                    pattern = re.compile(
                        r"\b" + re.escape(keyword) + r"\b",
                        re.IGNORECASE
                    )
                    compiled.append(pattern)
                except re.error:
                    logger.warning(f"关键词正则编译失败: {keyword}")
            patterns[category_name] = compiled

        return patterns

    def filter(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤文章列表

        Args:
            articles: 原始文章列表

        Returns:
            过滤后的文章列表
        """
        filtered = []

        for article in articles:
            try:
                if self._should_keep(article):
                    # 添加匹配的关键词分类信息
                    article["matched_categories"] = self._get_matched_categories(article)
                    filtered.append(article)
            except Exception as e:
                logger.warning(f"过滤文章失败: {e}")
                # 出错时保留文章（避免误删）
                filtered.append(article)

        logger.info(f"关键词过滤: {len(articles)} -> {len(filtered)}")
        return filtered

    def _should_keep(self, article: Dict[str, Any]) -> bool:
        """
        判断是否应该保留文章

        Args:
            article: 文章数据

        Returns:
            是否保留
        """
        # 1. 检查排除关键词
        if self._has_excluded_keyword(article):
            return False

        # 2. 检查是否包含任何目标关键词
        return self._has_target_keyword(article)

    def _has_excluded_keyword(self, article: Dict[str, Any]) -> bool:
        """检查是否包含排除关键词"""
        text = self._get_search_text(article)

        for keyword in self.keywords_config.excluded_keywords.keywords:
            if keyword.lower() in text.lower():
                logger.debug(f"文章包含排除关键词 '{keyword}': {article.get('title', '')}")
                return True

        return False

    def _has_target_keyword(self, article: Dict[str, Any]) -> bool:
        """检查是否包含目标关键词"""
        text = self._get_search_text(article)

        # 使用预编译的正则表达式匹配
        for category_patterns in self._compiled_patterns.values():
            for pattern in category_patterns:
                if pattern.search(text):
                    return True

        return False

    def _get_search_text(self, article: Dict[str, Any]) -> str:
        """获取用于搜索的文本"""
        fields = ["title", "description", "tags"]
        text_parts = []

        for field in fields:
            value = article.get(field, "")
            if isinstance(value, list):
                text_parts.extend([str(v) for v in value])
            else:
                text_parts.append(str(value))

        return " ".join(text_parts)

    def _get_matched_categories(self, article: Dict[str, Any]) -> List[str]:
        """获取文章匹配的关键词分类"""
        text = self._get_search_text(article)
        matched = []

        for category_name, category in self.keywords_config.categories.items():
            for keyword in category.keywords:
                if keyword.lower() in text.lower():
                    matched.append(category_name)
                    break

        return matched

    def calculate_score(self, article: Dict[str, Any]) -> float:
        """
        根据关键词匹配计算文章得分

        Args:
            article: 文章数据

        Returns:
            得分（0-1之间）
        """
        text = self._get_search_text(article)
        text_lower = text.lower()

        # 统计匹配的关键词数量
        total_keywords = 0
        matched_keywords = 0

        for category in self.keywords_config.categories.values():
            for keyword in category.keywords:
                total_keywords += 1
                if keyword.lower() in text_lower:
                    matched_keywords += 1

        # 计算得分比例
        if total_keywords == 0:
            return 0.0

        return min(matched_keywords / total_keywords, 1.0)
