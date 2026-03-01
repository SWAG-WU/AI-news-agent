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
from src.filters.new_model_filter import NewModelReleaseFilter
from src.filters.fun_github_filter import FunGithubFilter

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

    # 新模型发布额外配置
    DEFAULT_NEW_MODEL_EXTRA_COUNT = 3  # 新模型发布最大额外数量
    DEFAULT_NEW_MODEL_HOURS = 48  # 检测新模型发布的时间窗口（小时）

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
        "anthropic": CATEGORY_LAB_BLOG,
        "mistral_ai": CATEGORY_LAB_BLOG,
        "xai_blog": CATEGORY_LAB_BLOG,
        "microsoft_research": CATEGORY_LAB_BLOG,
        "nvidia_blog": CATEGORY_LAB_BLOG,
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
        self.new_model_extra_count = self.DEFAULT_NEW_MODEL_EXTRA_COUNT
        self.new_model_hours = self.DEFAULT_NEW_MODEL_HOURS
        self.dual_channel_mode = False  # 双渠道模式开关
        self.tools_channel_count = 5    # tools渠道输出数量
        self.academic_media_channel_count = 5  # 学术媒体渠道输出数量

        if config and hasattr(config, 'thresholds') and hasattr(config.thresholds, 'category_filter'):
            cf_config = config.thresholds.category_filter
            self.min_target_count = getattr(cf_config, 'min_target_count', self.DEFAULT_MIN_TARGET_COUNT)
            self.max_target_count = getattr(cf_config, 'max_target_count', self.DEFAULT_MAX_TARGET_COUNT)
            self.academic_min_count = getattr(cf_config, 'academic_min_count', self.DEFAULT_ACADEMIC_MIN_COUNT)
            self.academic_max_count = getattr(cf_config, 'academic_max_count', self.DEFAULT_ACADEMIC_MAX_COUNT)
            self.media_min_count = getattr(cf_config, 'media_min_count', self.DEFAULT_MEDIA_MIN_COUNT)
            self.latest_count = getattr(cf_config, 'latest_count', self.DEFAULT_LATEST_COUNT)
            self.new_model_extra_count = getattr(cf_config, 'new_model_extra_count', self.DEFAULT_NEW_MODEL_EXTRA_COUNT)
            self.new_model_hours = getattr(cf_config, 'new_model_hours', self.DEFAULT_NEW_MODEL_HOURS)
            self.dual_channel_mode = getattr(cf_config, 'dual_channel_mode', False)
            self.tools_channel_count = getattr(cf_config, 'tools_channel_count', 5)
            self.academic_media_channel_count = getattr(cf_config, 'academic_media_channel_count', 5)

        # 初始化新模型发布过滤器
        self.new_model_filter = NewModelReleaseFilter(config)

        # 初始化有趣GitHub项目过滤器
        self.fun_github_filter = FunGithubFilter(config)

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

            # 确保类别键存在，如果不存在则使用默认类别
            if category not in categorized:
                category = self.CATEGORY_MEDIA  # 默认归为媒体类

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
            category = article['category']
            # 确保类别是我们支持的类别之一
            if category in [self.CATEGORY_ACADEMIC, self.CATEGORY_MEDIA, self.CATEGORY_LAB_BLOG,
                           self.CATEGORY_TOOLS, self.CATEGORY_COMMUNITY, self.CATEGORY_NEWSLETTER]:
                return category
            else:
                # 如果不是我们支持的类别，返回 None 以便使用其他方式判断
                pass

        # 尝试使用 source_category 字段
        if 'source_category' in article and article['source_category']:
            category = article['source_category']
            # 确保类别是我们支持的类别之一
            if category in [self.CATEGORY_ACADEMIC, self.CATEGORY_MEDIA, self.CATEGORY_LAB_BLOG,
                           self.CATEGORY_TOOLS, self.CATEGORY_COMMUNITY, self.CATEGORY_NEWSLETTER]:
                return category
            else:
                # 如果不是我们支持的类别，返回 None 以便使用其他方式判断
                pass

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

        支持两种模式：
        1. 单渠道模式（默认）：混合输出不同类型的资讯
        2. 双渠道模式：分别输出工具类和学术/媒体类资讯
        """
        if self.dual_channel_mode:
            return self._filter_dual_channels(articles)
        else:
            return self._filter_single_channel(articles)

    def _filter_single_channel(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        单渠道过滤（按照用户新需求）

        新规则：
        1. 固定学术类：2条
        2. 固定工具类：3条
        3. 固定实验室类：3条
        4. 媒体类：填充至13-16条（如有特别资讯则相应增加）
        5. 特别资讯：仅在有知名大模型发布时启用（额外添加，不影响总数基础）
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

        # ========== 第1步：选择 2 条学术类资讯 ==========
        if academic_articles:
            sorted_academic = self._sort_articles_by_recency_and_score(academic_articles)
            selected_academic = sorted_academic[:2]  # 固定选择2条，即使总数不够也选择全部
            result.extend(selected_academic)
            selected_urls.update(a.get('url', '') for a in selected_academic)
            logger.info(f"  选择学术类: {len(selected_academic)} 条")
        else:
            # 如果没有学术类文章，从其他类别补充
            logger.warning(f"  学术类文章不足 (0/2)")
            # 从媒体、博客等类别中寻找可能的学术内容
            potential_academic = []
            all_remaining = [a for a in articles if a.get('url', '') not in selected_urls]

            for article in all_remaining:
                if len(potential_academic) >= 2:
                    break
                # 检查是否包含学术关键词
                title = article.get('title', '').lower()
                description = article.get('description', '').lower()
                text = f"{title} {description}"

                academic_keywords = ['paper', 'research', 'study', 'science', 'scientific', 'academic',
                                   'scholarly', 'conference', 'journal', 'thesis', 'dissertation',
                                   'publication', 'experiment', 'methodology', 'analysis']
                if any(keyword in text for keyword in academic_keywords):
                    article_copy = article.copy()
                    # 确保归类为学术类
                    article_copy['category'] = self.CATEGORY_ACADEMIC
                    potential_academic.append(article_copy)
                    selected_urls.add(article.get('url', ''))

            result.extend(potential_academic)
            logger.info(f"  从其他类别补充学术类: {len(potential_academic)} 条")

        # ========== 第2步：选择 3 条工具类资讯 ==========
        if tools_articles:
            sorted_tools = self._sort_articles_by_score(tools_articles)  # 按评分排序
            selected_tools = sorted_tools[:3]  # 固定选择3条，即使总数不够也选择全部
            result.extend(selected_tools)
            selected_urls.update(a.get('url', '') for a in selected_tools)
            logger.info(f"  选择工具类: {len(selected_tools)} 条")
        else:
            logger.warning(f"  工具类文章不足 (0/3)")

        # ========== 第3步：选择 3 条实验室博客类资讯 ==========
        if lab_blog_articles:
            sorted_lab_blog = self._sort_articles_by_recency_and_score(lab_blog_articles)
            selected_lab_blog = sorted_lab_blog[:3]  # 严格按照要求选择3条，不多选
            result.extend(selected_lab_blog)
            selected_urls.update(a.get('url', '') for a in selected_lab_blog)
            logger.info(f"  选择实验室类: {len(selected_lab_blog)} 条")
        else:
            logger.warning(f"  实验室类文章不足 (0/3)")

        # ========== 第4步：确保达到最低总数，优先选择媒体类 ==========
        target_min_total = 13  # 最少13条
        current_count = len(result)
        needed = max(0, target_min_total - current_count)

        # 优先填充媒体类
        if media_articles and needed > 0:
            remaining_media = [a for a in media_articles if a.get('url', '') not in selected_urls]
            if remaining_media:
                sorted_media = self._sort_articles_by_recency_and_score(remaining_media)
                selected_media = sorted_media[:min(needed, len(sorted_media))]
                result.extend(selected_media)
                selected_urls.update(a.get('url', '') for a in selected_media)
                logger.info(f"  选择媒体类: {len(selected_media)} 条")
                needed -= len(selected_media)

        # 如果仍有不足，从所有剩余文章中选择，优先选择媒体类
        if needed > 0:
            all_remaining = [a for a in articles if a.get('url', '') not in selected_urls]
            if all_remaining:
                # 先从媒体类剩余文章中选择
                remaining_media = [a for a in all_remaining if self._extract_category(a) == self.CATEGORY_MEDIA]
                if remaining_media:
                    sorted_media = self._sort_articles_by_recency_and_score(remaining_media)
                    media_to_add = sorted_media[:min(needed, len(sorted_media))]
                    result.extend(media_to_add)
                    selected_urls.update(a.get('url', '') for a in media_to_add)
                    logger.info(f"  从其他媒体类补充: {len(media_to_add)} 条")
                    needed -= len(media_to_add)

                # 如果仍不够，从所有剩余中选择
                if needed > 0:
                    all_remaining = [a for a in articles if a.get('url', '') not in selected_urls]
                    if all_remaining:
                        all_remaining_sorted = self._sort_articles_by_recency_and_score(all_remaining)
                        additional_articles = all_remaining_sorted[:needed]
                        result.extend(additional_articles)
                        selected_urls.update(a.get('url', '') for a in additional_articles)
                        logger.info(f"  补充其他类别: {len(additional_articles)} 条")

        # ========== 第5步：如果总数未达上限，可再填充至16条 ==========
        current_count = len(result)
        if current_count < 16:
            additional_needed = 16 - current_count
            all_remaining = [a for a in articles if a.get('url', '') not in selected_urls]
            if all_remaining:
                # 优先选择媒体类文章
                remaining_media = [a for a in all_remaining if self._extract_category(a) == self.CATEGORY_MEDIA]
                other_remaining = [a for a in all_remaining if self._extract_category(a) != self.CATEGORY_MEDIA]

                additional_articles = []
                # 优先选择媒体类
                if remaining_media:
                    sorted_media = self._sort_articles_by_recency_and_score(remaining_media)
                    media_to_add = sorted_media[:additional_needed]
                    additional_articles.extend(media_to_add)
                    additional_needed -= len(media_to_add)

                # 剩余名额选择其他类
                if additional_needed > 0 and other_remaining:
                    all_other_sorted = self._sort_articles_by_recency_and_score(other_remaining)
                    other_to_add = all_other_sorted[:additional_needed]
                    additional_articles.extend(other_to_add)

                result.extend(additional_articles)
                selected_urls.update(a.get('url', '') for a in additional_articles)
                logger.info(f"  额外填充: {len(additional_articles)} 条 (总数增至{len(result)})")

        # ========== 第6步：检测新模型发布，额外添加（不占用基础名额）==========
        new_model_articles = []
        all_articles_for_detection = articles + (result if self.storage else [])

        # 从未选中的文章中检测新模型发布
        selected_urls = set(a.get('url', '') for a in result)
        unsampled_articles = [a for a in articles if a.get('url', '') not in selected_urls]

        if unsampled_articles:
            new_model_articles = self.new_model_filter.filter_new_model_releases(
                unsampled_articles,
                max_extra=self.new_model_extra_count,
                hours=self.new_model_hours
            )

        # 将新模型发布资讯添加到结果中（作为额外资讯）
        final_result = result.copy()
        if new_model_articles:
            for article in new_model_articles:
                article['is_extra'] = True  # 标记为额外资讯
                article['extra_type'] = 'new_model_release'
            final_result.extend(new_model_articles)
            logger.info(f"CategoryFilter: 额外添加 {len(new_model_articles)} 条新模型发布资讯")

        # ========== 第7步：检测有趣GitHub项目，额外添加（不占用基础名额）==========
        fun_github_articles = []

        # 从未选中的文章中检测有趣GitHub项目
        selected_urls = set(a.get('url', '') for a in final_result)
        unsampled_articles = [a for a in articles if a.get('url', '') not in selected_urls]

        if unsampled_articles:
            fun_github_articles = self.fun_github_filter.filter_fun_github_projects(
                unsampled_articles
            )

        # 将有趣GitHub项目添加到结果中（作为额外资讯）
        if fun_github_articles:
            for article in fun_github_articles:
                article['is_extra'] = True  # 标记为额外资讯
                article['extra_type'] = 'fun_github_project'
            final_result.extend(fun_github_articles)
            logger.info(f"CategoryFilter: 额外添加 {len(fun_github_articles)} 条有趣GitHub项目")

        # 输出统计
        # 只统计常规输出
        regular_result = [a for a in final_result if not a.get('is_extra', False)]
        stats = self.get_stats(regular_result)
        logger.info(f"CategoryFilter: 常规输出 {len(regular_result)} 条 - {stats}")
        if new_model_articles:
            logger.info(f"CategoryFilter: 额外输出 {len(new_model_articles)} 条新模型发布资讯")
        if fun_github_articles:
            logger.info(f"CategoryFilter: 额外输出 {len(fun_github_articles)} 条有趣GitHub项目")

        return final_result

    def _filter_dual_channels(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        双渠道过滤

        渠道1：Tools渠道 - 专门筛选工具类（GitHub、Product Hunt等）资讯
        渠道2：学术媒体渠道 - 专门筛选学术、媒体类资讯
        """
        categorized = self.classify(articles)

        academic_articles = categorized[self.CATEGORY_ACADEMIC]
        media_articles = categorized[self.CATEGORY_MEDIA]
        tools_articles = categorized[self.CATEGORY_TOOLS]

        logger.info(f"双渠道模式: 输入 {len(articles)} 条")
        logger.info(f"  学术类: {len(academic_articles)}, 媒体类: {len(media_articles)}, 工具类: {len(tools_articles)}")

        result = []
        selected_urls = set()

        # ====== 渠道1: Tools频道 (按评分排序，选择最佳的) ======
        if tools_articles:
            sorted_tools = self._sort_articles_by_score(tools_articles)  # 按评分排序
            selected_tools = sorted_tools[:self.tools_channel_count]
            result.extend(selected_tools)
            selected_urls.update(a.get('url', '') for a in selected_tools)
            logger.info(f"  Tools频道: {len(selected_tools)} 条")

        # ====== 渠道2: 学术媒体频道 (优先学术，其次媒体) ======
        # 先选择学术类资讯
        remaining_academic = [a for a in academic_articles if a.get('url', '') not in selected_urls]
        if remaining_academic:
            sorted_academic = self._sort_articles_by_recency_and_score(remaining_academic)
            selected_academic = sorted_academic[:self.academic_media_channel_count//2]
            result.extend(selected_academic)
            selected_urls.update(a.get('url', '') for a in selected_academic)
            logger.info(f"  学术类: {len(selected_academic)} 条")

        # 再选择媒体类资讯补充
        remaining_media = [a for a in media_articles if a.get('url', '') not in selected_urls]
        if remaining_media:
            sorted_media = self._sort_articles_by_recency_and_score(remaining_media)
            # 补充到学术媒体频道的总数
            academic_selected = min(len(remaining_academic), self.academic_media_channel_count//2)
            media_needed = min(self.academic_media_channel_count - academic_selected, len(sorted_media))
            selected_media = sorted_media[:media_needed]
            result.extend(selected_media)
            selected_urls.update(a.get('url', '') for a in selected_media)
            logger.info(f"  媒体类: {len(selected_media)} 条")

        # ========== 第3步：检测新模型发布，额外添加（不占用主要名额）==========
        new_model_articles = []

        # 从未选中的文章中检测新模型发布
        selected_urls = set(a.get('url', '') for a in result)
        unsampled_articles = [a for a in articles if a.get('url', '') not in selected_urls]

        if unsampled_articles:
            new_model_articles = self.new_model_filter.filter_new_model_releases(
                unsampled_articles,
                max_extra=self.new_model_extra_count,
                hours=self.new_model_hours
            )

        # 将新模型发布资讯添加到结果中（作为额外资讯）
        final_result = result.copy()
        if new_model_articles:
            for article in new_model_articles:
                article['is_extra'] = True  # 标记为额外资讯
                article['extra_type'] = 'new_model_release'
            final_result.extend(new_model_articles)
            logger.info(f"CategoryFilter: 额外添加 {len(new_model_articles)} 条新模型发布资讯")

        # ========== 第4步：检测有趣GitHub项目，额外添加（不占用主要名额）==========
        fun_github_articles = []

        # 从未选中的文章中检测有趣GitHub项目
        selected_urls = set(a.get('url', '') for a in final_result)
        unsampled_articles = [a for a in articles if a.get('url', '') not in selected_urls]

        if unsampled_articles:
            fun_github_articles = self.fun_github_filter.filter_fun_github_projects(
                unsampled_articles
            )

        # 将有趣GitHub项目添加到结果中（作为额外资讯）
        if fun_github_articles:
            for article in fun_github_articles:
                article['is_extra'] = True  # 标记为额外资讯
                article['extra_type'] = 'fun_github_project'
            final_result.extend(fun_github_articles)
            logger.info(f"CategoryFilter: 额外添加 {len(fun_github_articles)} 条有趣GitHub项目")

        # 输出统计
        stats = self.get_stats(result)
        logger.info(f"CategoryFilter (双渠道): 常规输出 {len(result)} 条 - {stats}")
        if new_model_articles:
            logger.info(f"CategoryFilter: 额外输出 {len(new_model_articles)} 条新模型发布资讯")
        if fun_github_articles:
            logger.info(f"CategoryFilter: 额外输出 {len(fun_github_articles)} 条有趣GitHub项目")

        return final_result

    def _sort_articles_by_score(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        按评分排序文章（仅考虑评分，不考虑时间）

        Args:
            articles: 文章列表

        Returns:
            按评分排序的文章列表（评分最高的在前）
        """
        def sort_key(article):
            score = article.get('score', 0)
            # 使用负分数让评分高的排在前面
            return -score

        return sorted(articles, key=sort_key, reverse=False)

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
