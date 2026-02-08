#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间过滤器

根据发布时间对资讯进行分类和过滤，确保每日输出满足数量和比例要求。
"""

import logging
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple

from src.config import Config


logger = logging.getLogger(__name__)


class TimeFilter:
    """
    时间过滤器

    按照时间跨度对资讯进行分类和筛选，确保：
    1. 每日输出固定数量（默认 10 条）
    2. 一年内信息占比达到目标比例（默认 80%）
    3. 当年信息不足时可降低比例至最低阈值（默认 70%）
    """

    # 时间分组定义
    GROUP_RECENT = "recent"  # 一年内（近期）
    GROUP_HISTORICAL = "historical"  # 一年外（历史）

    def __init__(self, config: Optional[Config] = None):
        """
        初始化时间过滤器

        Args:
            config: 配置对象
        """
        self.config = config

        # 从配置读取阈值
        self.recent_threshold_days = 365  # 默认一年内
        self.daily_target_count = 10  # 每日目标输出数量
        self.target_recent_ratio = 0.80  # 目标近期比例（80%）
        self.min_recent_ratio = 0.70  # 最低近期比例（70%）

        if config and hasattr(config, 'thresholds') and hasattr(config.thresholds, 'time_filter'):
            tf_config = config.thresholds.time_filter
            self.recent_threshold_days = getattr(tf_config, 'recent_threshold_days', 365)
            self.daily_target_count = getattr(tf_config, 'daily_target_count', 10)
            self.target_recent_ratio = getattr(tf_config, 'target_recent_ratio', 0.80)
            self.min_recent_ratio = getattr(tf_config, 'min_recent_ratio', 0.70)

    def get_cutoff_date(self) -> datetime:
        """
        获取截止日期时间（动态计算）

        使用当前系统时间，计算过去 365 天（不含当天）的日期。

        Returns:
            截止日期时间
        """
        # 使用动态系统当前时间
        now = datetime.now()
        # 一年前的日期（不含当天，所以用 days=365+1=366 来确保是完整的 365 天）
        # 例如：今天是 2026-04-05，截止日期是 2025-04-06
        cutoff = now - timedelta(days=self.recent_threshold_days + 1)

        # 将时间部分设为 23:59:59，确保包含当天发布的所有内容
        cutoff = cutoff.replace(hour=23, minute=59, second=59, microsecond=999999)

        return cutoff

    def get_today(self) -> datetime:
        """
        获取今天的结束时间（23:59:59）

        Returns:
            今天的结束时间
        """
        now = datetime.now()
        return now.replace(hour=23, minute=59, second=59, microsecond=999999)

    def classify(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        对资讯进行时间分类

        分类规则：
        - 一年内：发布时间在 [截止日期, 今天] 之间
        - 一年外：发布时间早于截止日期

        Args:
            articles: 资讯列表

        Returns:
            分类后的字典，格式: {"recent": [...], "historical": [...]}
        """
        recent = []
        historical = []

        cutoff_date = self.get_cutoff_date()
        today_end = self.get_today()

        for article in articles:
            published_at = self._extract_published_at(article)

            if not published_at:
                # 没有发布时间的文章归为历史类
                time_group = self.GROUP_HISTORICAL
            elif cutoff_date <= published_at <= today_end:
                time_group = self.GROUP_RECENT
            else:
                time_group = self.GROUP_HISTORICAL

            # 添加时间分组标记
            article_copy = article.copy()
            article_copy['_time_group'] = time_group

            if time_group == self.GROUP_RECENT:
                recent.append(article_copy)
            else:
                historical.append(article_copy)

        return {
            self.GROUP_RECENT: recent,
            self.GROUP_HISTORICAL: historical
        }

    def filter_for_daily_output(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        为每日输出进行过滤，确保输出数量和比例满足要求

        规则：
        1. 每日输出固定数量（默认 10 条）
        2. 优先使用一年内信息（目标 80%）
        3. 当年信息不足时，可降低比例至最低阈值（70%）
        4. 用一年外信息补充至目标数量

        Args:
            articles: 资讯列表

        Returns:
            过滤后的资讯列表（保证返回 daily_target_count 条）
        """
        classified = self.classify(articles)
        recent = classified[self.GROUP_RECENT]
        historical = classified[self.GROUP_HISTORICAL]

        total_input = len(articles)
        recent_count = len(recent)
        historical_count = len(historical)

        logger.info(f"TimeFilter: 输入 {total_input} 条 (近期: {recent_count}, 历史: {historical_count})")

        # 计算目标数量
        target_recent_primary = int(self.daily_target_count * self.target_recent_ratio)  # 80% = 8 条
        target_recent_fallback = int(self.daily_target_count * self.min_recent_ratio)   # 70% = 7 条
        target_historical_primary = self.daily_target_count - target_recent_primary    # 20% = 2 条
        target_historical_fallback = self.daily_target_count - target_recent_fallback  # 30% = 3 条

        # 选择近期文章（按评分和时间排序）
        recent_sorted = self._sort_articles(recent)

        # 选择历史文章（按评分排序）
        historical_sorted = self._sort_articles(historical)

        # 策略 1：尝试使用目标比例（80%）
        if len(recent_sorted) >= target_recent_primary:
            # 近期文章足够，使用目标比例
            selected_recent = recent_sorted[:target_recent_primary]
            needed_historical = min(target_historical_primary, len(historical_sorted))
            selected_historical = historical_sorted[:needed_historical]

            result = selected_recent + selected_historical

            # 如果总数不足，用剩余的近期文章补充
            if len(result) < self.daily_target_count:
                additional = recent_sorted[target_recent_primary:target_recent_primary + (self.daily_target_count - len(result))]
                result.extend(additional)

            logger.info(f"TimeFilter: 使用目标比例 80% - 近期 {len(selected_recent)} 条, 历史 {len(selected_historical)} 条")
        # 策略 2：使用最低比例（70%）
        elif len(recent_sorted) >= target_recent_fallback:
            # 近期文章不足 80%，但满足 70% 最低要求
            selected_recent = recent_sorted[:target_recent_fallback]
            needed_historical = min(target_historical_fallback, len(historical_sorted))
            selected_historical = historical_sorted[:needed_historical]

            result = selected_recent + selected_historical

            # 如果总数不足，用剩余的历史文章补充
            if len(result) < self.daily_target_count:
                additional = historical_sorted[len(selected_historical):len(selected_historical) + (self.daily_target_count - len(result))]
                result.extend(additional)

            logger.info(f"TimeFilter: 使用最低比例 70% - 近期 {len(selected_recent)} 条, 历史 {len(selected_historical)} 条")
        # 策略 3：近期文章严重不足，使用所有可用的近期文章
        else:
            # 近期文章连 70% 都不够，使用所有近期文章 + 历史文章补充
            selected_recent = recent_sorted
            needed_historical = min(self.daily_target_count - len(selected_recent), len(historical_sorted))
            selected_historical = historical_sorted[:needed_historical]

            result = selected_recent + selected_historical
            logger.warning(f"TimeFilter: 近期文章严重不足 ({len(selected_recent)}/{self.daily_target_count})，使用所有近期 + 历史补充")

        # 最终保证输出数量
        result = result[:self.daily_target_count]

        # 输出统计
        actual_recent = sum(1 for a in result if a.get('_time_group') == self.GROUP_RECENT)
        actual_ratio = actual_recent / len(result) if result else 0
        logger.info(f"TimeFilter: 输出 {len(result)} 条 (近期: {actual_recent} ({actual_ratio:.1%}), 历史: {len(result) - actual_recent})")

        return result

    def _sort_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对文章进行排序

        排序规则：优先按评分降序，其次按发布时间降序

        Args:
            articles: 文章列表

        Returns:
            排序后的文章列表
        """
        def sort_key(article):
            score = article.get('score', 0)
            published_at = self._extract_published_at(article)
            # 将 datetime 转换为时间戳用于排序
            timestamp = published_at.timestamp() if published_at else 0
            return (score, timestamp)

        return sorted(articles, key=sort_key, reverse=True)

    def get_stats(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取时间统计信息

        Args:
            articles: 资讯列表

        Returns:
            统计信息字典
        """
        classified = self.classify(articles)
        recent = classified[self.GROUP_RECENT]
        historical = classified[self.GROUP_HISTORICAL]

        total = len(articles)
        recent_count = len(recent)
        historical_count = len(historical)

        cutoff_date = self.get_cutoff_date()
        today_end = self.get_today()

        stats = {
            "total": total,
            "recent_count": recent_count,
            "recent_ratio": recent_count / total if total > 0 else 0,
            "historical_count": historical_count,
            "historical_ratio": historical_count / total if total > 0 else 0,
            "meets_target_ratio": (recent_count / total) >= self.target_recent_ratio if total > 0 else False,
            "meets_min_ratio": (recent_count / total) >= self.min_recent_ratio if total > 0 else False,
            "target_ratio": self.target_recent_ratio,
            "min_ratio": self.min_recent_ratio,
            "cutoff_date": cutoff_date.isoformat(),
            "today": today_end.isoformat(),
            "daily_target_count": self.daily_target_count,
        }

        # 按年份统计
        year_counts = {}
        for article in articles:
            published_at = self._extract_published_at(article)
            if published_at:
                year = published_at.year
                year_counts[year] = year_counts.get(year, 0) + 1

        if year_counts:
            stats["by_year"] = dict(sorted(year_counts.items()))

        return stats

    def _extract_published_at(self, article: Dict[str, Any]) -> Optional[datetime]:
        """
        从文章中提取发布时间

        Args:
            article: 文章数据

        Returns:
            发布时间，或 None
        """
        # 优先使用 published_at 字段
        published_at = article.get("published_at")
        if published_at:
            if isinstance(published_at, datetime):
                return published_at
            if isinstance(published_at, date):
                # 将 date 转换为 datetime（当天的 23:59:59）
                return datetime.combine(published_at, datetime.max.time())
            if isinstance(published_at, str):
                return self._parse_datetime(published_at)

        # 尝试从其他字段提取
        return None

    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """解析日期时间字符串"""
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
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue

        # 尝试使用 email.utils
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(dt_str)
        except Exception:
            pass

        return None
