#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
新模型发布过滤器

检测新AI模型发布的资讯，用于突破每日10条限制，额外添加重要模型发布资讯。
"""

import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from src.config import Config

logger = logging.getLogger(__name__)


class NewModelReleaseFilter:
    """
    新模型发布过滤器

    检测资讯是否为新模型发布，当检测到新模型发布时，
    可以在固定的10条资讯之外额外添加这些资讯。
    """

    # 主流AI公司/实验室
    AI_LABS = [
        "openai", "anthropic", "google", "deepmind", "meta", "facebook",
        "microsoft", "amazon", "nvidia", "apple", "xai", "elon musk",
        "mistral", "inflection", "character.ai", "adept", "cohere",
        "百度", "阿里巴巴", "阿里", "腾讯", "字节跳动", "智谱", "月之暗面",
        "01.ai", "零一万物", "minimax", "昆仑万维", "360", "科大讯飞"
    ]

    # 主流模型名称模式
    MODEL_PATTERNS = [
        r"GPT-\d+(\.\d+)?([a-z])?",
        r"Claude\s*(3\s*\.?\s*[5-7]|3\.5|3\.7|Opus|Sonnet|Haiku)",
        r"Gemini\s*(2\s*\.?\s*0?|1\.5|1\.5\s*Pro|Ultra|Pro|Flash)",
        r"Llama\s*(3\.?1?|2|3)(\s*-\s*[1-9]+[0-9]*[Bb])?",
        r"GLM[-_]?\d+(\.\d+)?",
        r"Qwen[-_]?\d+(\.\d+)?",
        r"Yi[-_]?(Large|VL|34[Bb]|9[Bb])",
        r"Baichuan[-_]?\d+",
        r"Hunyuan[-_]?\d+",
        r"Grok[-_]?\d+(\.\d+)?",
        r"Mistral[-_]?(Large|7[Bb]|8x7[Bb]|Mixtral)",
        r"Phi[-_]?\d+(\.\d+)?",
        r"Sora(\s*v\d+(\.\d+)?)?",
        r"Stable\s*Diffusion\s*\d+(\.\d+)?",
        r"Midjourney\s*v?\d+(\.\d+)?",
        r"DALL[-_]?E\s*[23]?",
        r"Flux\s*\d+(\.\d+)?",
    ]

    def __init__(self, config: Optional[Config] = None):
        """
        初始化新模型发布过滤器

        Args:
            config: 配置对象
        """
        self.config = config

        # 加载新模型发布关键词
        self.new_model_keywords = set()
        if config and hasattr(config, 'keywords'):
            new_model_category = config.keywords.categories.get('new_model')
            if new_model_category:
                self.new_model_keywords = set(kw.lower() for kw in new_model_category.keywords)

        # 编译模型名称正则
        self.model_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in self.MODEL_PATTERNS]

        # 已记录的模型（避免重复）
        self._recorded_models = set()

    def is_new_model_release(self, article: Dict[str, Any]) -> bool:
        """
        判断资讯是否为新模型发布

        Args:
            article: 文章数据

        Returns:
            是否为新模型发布
        """
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        content = f"{title} {description}"

        # 检查是否包含新模型发布关键词
        has_keyword = any(kw in content for kw in self.new_model_keywords)

        if not has_keyword:
            return False

        # 检查是否包含模型名称
        has_model_name = any(regex.search(content) for regex in self.model_regexes)

        if not has_model_name:
            # 如果没有模型名称，但有发布关键词，检查是否来自AI实验室
            source = article.get('source', '').lower()
            is_from_ai_lab = any(lab in source for lab in self.AI_LABS)
            return is_from_ai_lab

        return True

    def extract_model_name(self, article: Dict[str, Any]) -> Optional[str]:
        """
        从资讯中提取模型名称

        Args:
            article: 文章数据

        Returns:
            模型名称，或None
        """
        title = article.get('title', '')
        description = article.get('description', '')
        content = f"{title} {description}"

        # 尝试从标题中提取模型名称
        for regex in self.model_regexes:
            match = regex.search(title)
            if match:
                return match.group(0)

        # 从描述中提取
        for regex in self.model_regexes:
            match = regex.search(description)
            if match:
                return match.group(0)

        return None

    def get_model_info(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取模型发布信息

        Args:
            article: 文章数据

        Returns:
            模型信息字典
        """
        model_name = self.extract_model_name(article)

        # 尝试提取公司
        source = article.get('source', '')
        company = None
        for lab in self.AI_LABS:
            if lab.lower() in source.lower():
                company = lab
                break

        return {
            "model_name": model_name,
            "company": company,
            "title": article.get('title', ''),
            "url": article.get('url', ''),
            "source": source,
            "published_at": article.get('published_at', ''),
        }

    def filter_new_model_releases(
        self,
        articles: List[Dict[str, Any]],
        max_extra: int = 3,
        hours: int = 48
    ) -> List[Dict[str, Any]]:
        """
        从资讯列表中筛选新模型发布资讯

        Args:
            articles: 资讯列表
            max_extra: 最多额外添加的数量
            hours: 时间窗口（小时），只考虑最近N小时内的发布

        Returns:
            新模型发布资讯列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        new_model_articles = []

        for article in articles:
            # 检查是否为新模型发布
            if not self.is_new_model_release(article):
                continue

            # 检查发布时间
            published_at = self._extract_published_at(article)
            if published_at and published_at < cutoff_time:
                continue

            # 检查是否已记录
            model_info = self.get_model_info(article)
            model_key = f"{model_info['company']}_{model_info['model_name']}"
            if model_key in self._recorded_models:
                continue

            # 标记为新模型发布
            article_copy = article.copy()
            article_copy['is_new_model_release'] = True
            article_copy['model_info'] = model_info

            new_model_articles.append(article_copy)
            self._recorded_models.add(model_key)

            if len(new_model_articles) >= max_extra:
                break

        if new_model_articles:
            logger.info(f"检测到 {len(new_model_articles)} 条新模型发布资讯")
            for item in new_model_articles:
                model_info = item['model_info']
                logger.info(f"  - {model_info['company']}: {model_info['model_name']}")

        return new_model_articles

    def _extract_published_at(self, article: Dict[str, Any]) -> Optional[datetime]:
        """提取发布时间"""
        published_at = article.get("published_at")
        if not published_at:
            return None

        if isinstance(published_at, datetime):
            return published_at

        if isinstance(published_at, str):
            formats = (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d",
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S GMT",
            )
            for fmt in formats:
                try:
                    return datetime.strptime(published_at, fmt)
                except ValueError:
                    continue

        return None

    def has_new_model_today(self) -> bool:
        """
        检查今天是否已有新模型发布记录

        Returns:
            是否今天已记录过新模型
        """
        return len(self._recorded_models) > 0

    def get_daily_model_summary(self) -> List[Dict[str, Any]]:
        """
        获取今天已记录的新模型发布摘要

        Returns:
            模型发布信息列表
        """
        return list(self._recorded_models)

    def reset_daily_record(self):
        """重置每日记录（在每天首次运行时调用）"""
        self._recorded_models.clear()
        logger.info("已重置新模型发布每日记录")
