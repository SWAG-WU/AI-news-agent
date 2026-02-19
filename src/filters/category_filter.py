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
    DEFAULT_MAX_TARGET_COUNT = 10  # 最大输出数量（固定每天10条）
    DEFAULT_ACADEMIC_MIN_COUNT = 1  # 最少学术类数量
    DEFAULT_ACADEMIC_MAX_COUNT = 3  # 最多学术类数量
    DEFAULT_MEDIA_MIN_COUNT = 2  # 最少媒体类数量
    DEFAULT_LATEST_COUNT = 3  # 最新资讯数量（按时间排序）

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
        self.academic_max_count = self.DEFAULT_ACADEMIC_MAX_COUNT
        self.media_min_count = self.DEFAULT_MEDIA_MIN_COUNT
        self.latest_count = self.DEFAULT_LATEST_COUNT

        if config and hasattr(config, 'thresholds') and hasattr(config.thresholds, 'category_filter'):
            cf_config = config.thresholds.category_filter
            self.min_target_count = getattr(cf_config, 'min_target_count', self.DEFAULT_MIN_TARGET_COUNT)
            self.max_target_count = getattr(cf_config, 'max_target_count', self.DEFAULT_MAX_TARGET_COUNT)
            self.academic_min_count = getattr(cf_config, 'academic_min_count', self.DEFAULT_ACADEMIC_MIN_COUNT)
            self.academic_max_count = getattr(cf_config, 'academic_max_count', self.DEFAULT_ACADEMIC_MAX_COUNT)
            self.media_min_count = getattr(cf_config, 'media_min_count', self.DEFAULT_MEDIA_MIN_COUNT)
            self.latest_count = getattr(cf_config, 'latest_count', self.DEFAULT_LATEST_COUNT)

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

        新规则（按优先级）：
        1. 首先选择 3 条最新资讯（按发布时间排序，越靠近运行时间越好）
        2. 从剩余资讯中选择 1-3 条学术类资讯
        3. 其余用其他类型资讯填补至 10 条
        4. 严格控制学术资讯不超过 3 条

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
        selected_urls = set()

        # ========== 第1步：选择 3 条最新资讯（按时间优先） ==========
        all_articles_by_time = self._sort_articles_by_recency_only(articles)
        latest_articles = []
        for article in all_articles_by_time:
            if len(latest_articles) >= self.latest_count:
                break
            url = article.get('url', '')
            if url and url not in selected_urls:
                latest_articles.append(article)
                selected_urls.add(url)

        result.extend(latest_articles)
        logger.info(f"  选择最新资讯: {len(latest_articles)} 条")

        # ========== 第2步：从剩余资讯中选择 1-3 条学术类资讯 ==========
        remaining_academic = [a for a in academic_articles if a.get('url', '') not in selected_urls]
        if remaining_academic:
            sorted_academic = self._sort_articles_by_recency_and_score(remaining_academic)
            # 学术资讯数量控制在 1-3 条之间，根据可用数量动态调整
            academic_to_select = min(self.academic_max_count, len(sorted_academic))
            # 如果学术资讯足够多，至少选择 1 条
            if academic_to_select >= 1:
                academic_to_select = max(self.academic_min_count, academic_to_select)
            selected_academic = sorted_academic[:academic_to_select]
            result.extend(selected_academic)
            selected_urls.update(a.get('url', '') for a in selected_academic)
            logger.info(f"  选择学术类: {len(selected_academic)} 条")
        else:
            logger.warning(f"  学术类文章不足 (0/{self.academic_min_count})")

        # ========== 第3步：计算还需填补的数量 ==========
        target_count = self.min_target_count  # 固定 10 条
        needed = target_count - len(result)

        if needed > 0:
            logger.info(f"  还需填补: {needed} 条")

            # ========== 第4步：按优先级填补剩余名额 ==========
            # 收集所有剩余文章（排除学术类的上限控制）
            remaining_pools = []

            # 媒体类剩余（排除已选中的）
            remaining_media = [a for a in media_articles if a.get('url', '') not in selected_urls]
            if remaining_media:
                remaining_pools.append((self.CATEGORY_MEDIA, remaining_media))

            # 其他类别（按优先级）
            remaining_pools.extend([
                (self.CATEGORY_LAB_BLOG, [a for a in lab_blog_articles if a.get('url', '') not in selected_urls]),
                (self.CATEGORY_TOOLS, [a for a in tools_articles if a.get('url', '') not in selected_urls]),
                (self.CATEGORY_COMMUNITY, [a for a in community_articles if a.get('url', '') not in selected_urls]),
                (self.CATEGORY_NEWSLETTER, [a for a in newsletter_articles if a.get('url', '') not in selected_urls]),
            ])

            # 填补剩余名额
            for category_name, pool in remaining_pools:
                if needed <= 0:
                    break
                if pool:
                    sorted_pool = self._sort_articles_by_recency_and_score(pool)
                    selected = min(needed, len(sorted_pool))
                    result.extend(sorted_pool[:selected])
                    selected_urls.update(a.get('url', '') for a in sorted_pool[:selected])
                    needed -= selected
                    logger.info(f"  从 {category_name} 填补: {selected} 条")

        # ========== 第5步：如果仍然不足，从数据库获取未发送的历史文章补充 ==========
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

        # ========== 第6步：最终保证输出数量固定为 10 条 ==========
        result = result[:self.max_target_count]

        # 输出统计
        stats = self.get_stats(result)
        logger.info(f"CategoryFilter: 输出 {len(result)} 条 - {stats}")

        return result

    def _sort_articles_by_recency_only(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        纯按时间排序文章：优先选择最新的文章（越靠近运行时间越好）

        Args:
            articles: 文章列表

        Returns:
            按时间排序的文章列表（最新的在前）
        """
        def sort_key(article):
            published_at = self._extract_published_at(article)
            # 时间戳：越新越好
            timestamp = published_at.timestamp() if published_at else 0
            # 使用负时间戳让越新的排在前面
            return -timestamp

        return sorted(articles, key=sort_key, reverse=False)

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
