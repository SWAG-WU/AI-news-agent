#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
类别过滤器

根据信息源类型对资讯进行分类和过滤，确保每日输出满足指定类型的数量要求。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.config import Config

logger = logging.getLogger(__name__)


class CategoryFilter:
    """
    类别过滤器

    按照信息源类型对资讯进行分类和筛选，确保：
    1. 优先输出 1 条学术类资讯（academic）
    2. 优先输出 2 条媒体类资讯（media）
    3. 数量不足时用其他类型资讯填补
    4. 总输出数量默认为 3 条
    """

    # 类别定义（基于 sources.json 中的 categorization.category）
    CATEGORY_ACADEMIC = "academic"       # 学术类：arXiv, Papers With Code, Nature AI, NeurIPS, ICML 等
    CATEGORY_MEDIA = "media"            # 媒体类：机器之心, MIT Tech Review, The Decoder 等
    CATEGORY_LAB_BLOG = "lab_blog"      # 实验室博客：OpenAI, DeepMind, Anthropic 等
    CATEGORY_TOOLS = "tools"            # 工具类：Product Hunt, Futurepedia, GitHub 等
    CATEGORY_COMMUNITY = "community"    # 社区类：Hacker News, Reddit 等
    CATEGORY_NEWSLETTER = "newsletter"  # 通讯类：The Batch, Import AI 等

    # 输出配置
    DEFAULT_MIN_TARGET_COUNT = 10  # 最小输出数量
    DEFAULT_MAX_TARGET_COUNT = 15  # 最大输出数量
    DEFAULT_ACADEMIC_MIN_COUNT = 1  # 最少学术类数量
    DEFAULT_MEDIA_MIN_COUNT = 2  # 最少媒体类数量

    # 填补优先级（当学术/媒体不足时，按此顺序填补）
    FALLBACK_PRIORITY = [
        CATEGORY_LAB_BLOG,
        CATEGORY_TOOLS,
        CATEGORY_COMMUNITY,
        CATEGORY_NEWSLETTER,
    ]

    # 信息源名称到类别的映射（用于没有明确 category 字段的旧数据）
    SOURCE_CATEGORY_MAPPING = {
        # 学术类
        "arxiv": CATEGORY_ACADEMIC,
        "arxiv_cs_ai": CATEGORY_ACADEMIC,
        "papers_with_code": CATEGORY_ACADEMIC,
        "huggingface_papers": CATEGORY_ACADEMIC,
        "the_gradient": CATEGORY_ACADEMIC,
        "nature_ai": CATEGORY_ACADEMIC,
        "neurips": CATEGORY_ACADEMIC,
        "icml": CATEGORY_ACADEMIC,

        # 媒体类
        "jiqizhixin": CATEGORY_MEDIA,
        "synced": CATEGORY_MEDIA,
        "mit_tech_review": CATEGORY_MEDIA,
        "the_decoder": CATEGORY_MEDIA,
        "semafor_ai": CATEGORY_MEDIA,
        "the_verge_ai": CATEGORY_MEDIA,

        # 实验室博客
        "openai_blog": CATEGORY_LAB_BLOG,
        "google_deepmind": CATEGORY_LAB_BLOG,
        "meta_ai_blog": CATEGORY_LAB_BLOG,
        "anthropic_blog": CATEGORY_LAB_BLOG,
        "mistral_ai": CATEGORY_LAB_BLOG,
        "xai_blog": CATEGORY_LAB_BLOG,
        "tongyi_lab": CATEGORY_LAB_BLOG,
        "zhipu_ai": CATEGORY_LAB_BLOG,
        "huggingface_blog": CATEGORY_LAB_BLOG,

        # 工具类
        "product_hunt_ai": CATEGORY_TOOLS,
        "futurepedia": CATEGORY_TOOLS,
        "theresanai": CATEGORY_TOOLS,
        "huggingface_spaces": CATEGORY_TOOLS,
        "github_trending_ai": CATEGORY_TOOLS,

        # 社区类
        "hacker_news": CATEGORY_COMMUNITY,
        "reddit_ml": CATEGORY_COMMUNITY,
        "lilog": CATEGORY_COMMUNITY,

        # 通讯类
        "the_batch": CATEGORY_NEWSLETTER,
        "import_ai": CATEGORY_NEWSLETTER,
        "bens_bites": CATEGORY_NEWSLETTER,
    }

    def __init__(self, config: Optional[Config] = None, storage=None):
        """
        初始化类别过滤器

        Args:
            config: 配置对象
            storage: 存储对象，用于获取未发送的历史文章
        """
        self.config = config
        self.storage = storage

        # 从配置读取阈值（如果有）
        self.min_target_count = self.DEFAULT_MIN_TARGET_COUNT
        self.max_target_count = self.DEFAULT_MAX_TARGET_COUNT
        self.academic_min_count = self.DEFAULT_ACADEMIC_MIN_COUNT
        self.media_min_count = self.DEFAULT_MEDIA_MIN_COUNT

        if config and hasattr(config, 'thresholds') and hasattr(config.thresholds, 'category_filter'):
            cf_config = config.thresholds.category_filter
            self.min_target_count = getattr(cf_config, 'min_target_count', self.DEFAULT_MIN_TARGET_COUNT)
            self.max_target_count = getattr(cf_config, 'max_target_count', self.DEFAULT_MAX_TARGET_COUNT)
            self.academic_min_count = getattr(cf_config, 'academic_min_count', self.DEFAULT_ACADEMIC_MIN_COUNT)
            self.media_min_count = getattr(cf_config, 'media_min_count', self.DEFAULT_MEDIA_MIN_COUNT)

    def classify(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        对资讯进行类别分类

        Args:
            articles: 资讯列表

        Returns:
            分类后的字典，格式: {"academic": [...], "media": [...], ...}
        """
        categorized = {
            self.CATEGORY_ACADEMIC: [],
            self.CATEGORY_MEDIA: [],
            self.CATEGORY_LAB_BLOG: [],
            self.CATEGORY_TOOLS: [],
            self.CATEGORY_COMMUNITY: [],
            self.CATEGORY_NEWSLETTER: [],
        }

        for article in articles:
            category = self._extract_category(article)
            categorized[category].append(article)

        return categorized

    def _extract_category(self, article: Dict[str, Any]) -> str:
        """
        从文章中提取类别

        优先级：
        1. article.get('category') - 文章明确指定的类别
        2. article.get('source_category') - 来源的类别
        3. 根据 source 名称映射

        Args:
            article: 文章数据

        Returns:
            类别名称
        """
        # 优先使用文章的 category 字段
        if 'category' in article and article['category']:
            return article['category']

        # 尝试使用 source_category 字段
        if 'source_category' in article and article['source_category']:
            return article['source_category']

        # 根据 source 名称映射
        source = article.get('source', '').lower()
        source_id = article.get('source_id', '').lower()

        # 尝试匹配 source_id
        if source_id:
            for key, category in self.SOURCE_CATEGORY_MAPPING.items():
                if key in source_id:
                    return category

        # 尝试匹配 source 名称
        if source:
            for key, category in self.SOURCE_CATEGORY_MAPPING.items():
                if key in source:
                    return category

        # 默认归为媒体类
        logger.debug(f"无法分类文章: {article.get('title', '')}, 归类为 media")
        return self.CATEGORY_MEDIA

    def filter_for_daily_output(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        为每日输出进行过滤，确保输出数量和类型满足要求

        规则：
        1. 总输出数量：10-15 条
        2. 至少 1 条学术类资讯
        3. 至少 2 条媒体类资讯
        4. 其余用各类资讯填补（优先级：实验室博客 > 工具类 > 社区类 > 通讯类）

        Args:
            articles: 资讯列表

        Returns:
            过滤后的资讯列表
        """
        categorized = self.classify(articles)

        academic_articles = categorized[self.CATEGORY_ACADEMIC]
        media_articles = categorized[self.CATEGORY_MEDIA]
        lab_blog_articles = categorized[self.CATEGORY_LAB_BLOG]
        tools_articles = categorized[self.CATEGORY_TOOLS]
        community_articles = categorized[self.CATEGORY_COMMUNITY]
        newsletter_articles = categorized[self.CATEGORY_NEWSLETTER]

        total_input = len(articles)

        logger.info(f"CategoryFilter: 输入 {total_input} 条")
        logger.info(f"  学术类: {len(academic_articles)}, 媒体类: {len(media_articles)}, "
                   f"实验室博客: {len(lab_blog_articles)}, 工具类: {len(tools_articles)}, "
                   f"社区类: {len(community_articles)}, 通讯类: {len(newsletter_articles)}")

        result = []

        # 1. 优先选择学术类文章（至少 1 条）
        if academic_articles:
            sorted_academic = self._sort_articles_by_recency_and_score(academic_articles)
            selected = min(self.academic_min_count, len(sorted_academic))
            result.extend(sorted_academic[:selected])
            logger.info(f"  选择学术类: {selected} 条")
        else:
            logger.warning(f"  学术类文章不足 (0/{self.academic_min_count})")

        # 2. 优先选择媒体类文章（至少 2 条）
        if media_articles:
            sorted_media = self._sort_articles_by_recency_and_score(media_articles)
            selected = min(self.media_min_count, len(sorted_media))
            result.extend(sorted_media[:selected])
            logger.info(f"  选择媒体类: {selected} 条")
        else:
            logger.warning(f"  媒体类文章不足 ({len(media_articles)}/{self.media_min_count})")

        # 3. 计算还需填补的数量，目标是达到 min_target_count
        target_count = self.min_target_count
        needed = target_count - len(result)

        # 4. 按优先级填补剩余名额
        # 收集所有剩余文章（学术、媒体、实验室博客、工具、社区、通讯）
        remaining_pools = []

        # 学术类剩余
        if academic_articles:
            remaining_academic = academic_articles[self.academic_min_count:]
            if remaining_academic:
                remaining_pools.append((self.CATEGORY_ACADEMIC, remaining_academic))

        # 媒体类剩余
        if media_articles:
            remaining_media = media_articles[self.media_min_count:]
            if remaining_media:
                remaining_pools.append((self.CATEGORY_MEDIA, remaining_media))

        # 其他类别
        remaining_pools.extend([
            (self.CATEGORY_LAB_BLOG, lab_blog_articles),
            (self.CATEGORY_TOOLS, tools_articles),
            (self.CATEGORY_COMMUNITY, community_articles),
            (self.CATEGORY_NEWSLETTER, newsletter_articles),
        ])

        # 填补剩余名额
        for category_name, pool in remaining_pools:
            if needed <= 0:
                break
            if pool:
                sorted_pool = self._sort_articles_by_recency_and_score(pool)
                selected = min(needed, len(sorted_pool))
                result.extend(sorted_pool[:selected])
                needed -= selected
                logger.info(f"  从 {category_name} 填补: {selected} 条")

        # 5. 如果仍然不足，尝试增加到 max_target_count
        if needed > 0 and len(result) < self.max_target_count:
            additional_needed = min(self.max_target_count - len(result), needed)
            if additional_needed > 0:
                # 从所有文章中选择未被选中的
                selected_urls = {a.get('url', '') for a in result}
                all_remaining = [a for a in articles if a.get('url', '') not in selected_urls]
                sorted_remaining = self._sort_articles_by_recency_and_score(all_remaining)
                additional = min(additional_needed, len(sorted_remaining))
                result.extend(sorted_remaining[:additional])
                needed -= additional
                logger.info(f"  从所有文章补充: {additional} 条")

        # 6. 如果仍然不足，从数据库获取未发送的历史文章补充
        if needed > 0 and self.storage:
            logger.info(f"CategoryFilter: 当前文章不足 {len(result)} 条，从数据库获取未发送的历史文章补充")
            unsent_articles = self.storage.get_unsent(limit=needed)

            for article in unsent_articles:
                article_dict = article.to_dict()
                article_dict.setdefault('description', '')
                article_dict.setdefault('score', article.score or 0)
                article_dict.setdefault('published_at', article.published_at)
                result.append(article_dict)

            logger.info(f"CategoryFilter: 从数据库补充了 {len(unsent_articles)} 条未发送的历史文章")

        # 7. 最终保证输出数量在 min-max 范围内
        result = result[:self.max_target_count]

        # 输出统计
        stats = self.get_stats(result)
        logger.info(f"CategoryFilter: 输出 {len(result)} 条 - {stats}")

        return result

    def _sort_articles_by_recency_and_score(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对文章进行排序：优先选择较新的文章，然后按评分

        Args:
            articles: 文章列表

        Returns:
            排序后的文章列表
        """
        def sort_key(article):
            score = article.get('score', 0)
            published_at = self._extract_published_at(article)
            # 时间戳：越新越好
            timestamp = published_at.timestamp() if published_at else 0
            # 综合排序：优先较新，然后按评分
            # 使用负时间戳让越新的排在前面
            return (-timestamp, score)

        return sorted(articles, key=sort_key, reverse=False)

    def _extract_published_at(self, article: Dict[str, Any]) -> Optional[datetime]:
        """
        从文章中提取发布时间

        Args:
            article: 文章数据

        Returns:
            发布时间（timezone-naive），或 None
        """
        published_at = article.get("published_at")
        if published_at:
            if isinstance(published_at, datetime):
                if published_at.tzinfo is not None:
                    return published_at.replace(tzinfo=None)
                return published_at
            if isinstance(published_at, str):
                return self._parse_datetime(published_at)

        return None

    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """解析日期时间字符串，返回 timezone-naive 的 datetime"""
        if not dt_str:
            return None

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
                parsed = datetime.strptime(dt_str, fmt)
                if parsed.tzinfo is not None:
                    parsed = parsed.replace(tzinfo=None)
                return parsed
            except ValueError:
                continue

        try:
            from email.utils import parsedate_to_datetime
            parsed = parsedate_to_datetime(dt_str)
            if parsed.tzinfo is not None:
                parsed = parsed.replace(tzinfo=None)
            return parsed
        except Exception:
            pass

        return None

    def get_stats(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取类别统计信息

        Args:
            articles: 资讯列表

        Returns:
            统计信息字典
        """
        categorized = self.classify(articles)

        stats = {
            "total": len(articles),
            self.CATEGORY_ACADEMIC: len(categorized[self.CATEGORY_ACADEMIC]),
            self.CATEGORY_MEDIA: len(categorized[self.CATEGORY_MEDIA]),
            self.CATEGORY_LAB_BLOG: len(categorized[self.CATEGORY_LAB_BLOG]),
            self.CATEGORY_TOOLS: len(categorized[self.CATEGORY_TOOLS]),
            self.CATEGORY_COMMUNITY: len(categorized[self.CATEGORY_COMMUNITY]),
            self.CATEGORY_NEWSLETTER: len(categorized[self.CATEGORY_NEWSLETTER]),
        }

        return stats

    def __repr__(self) -> str:
        return (f"CategoryFilter(min_target={self.min_target_count}, max_target={self.max_target_count}, "
               f"academic_min={self.academic_min_count}, media_min={self.media_min_count})")
