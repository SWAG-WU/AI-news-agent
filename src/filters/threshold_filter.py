#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阈值过滤器

根据配置的阈值标准筛选资讯。
"""

import logging
from typing import Any, Dict, List
from datetime import datetime, timedelta

from src.config import Config, get_config

logger = logging.getLogger(__name__)


class ThresholdFilter:
    """
    阈值过滤器

    根据多种阈值标准筛选资讯，包括：
    - arXiv论文引用数
    - GitHub星标数
    - HuggingFace点赞数
    - 内容长度
    - 时间窗口
    - 综合评分
    """

    def __init__(self, config: Config = None):
        self.config = config or get_config()
        self.thresholds = self.config.thresholds

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
                # 计算综合评分
                score = self._calculate_score(article)
                article["score"] = score

                # 检查是否满足阈值条件
                if self._meets_thresholds(article):
                    filtered.append(article)
                else:
                    logger.debug(f"文章未达到阈值: {article.get('title', '')} (score: {score})")

            except Exception as e:
                logger.warning(f"过滤文章失败: {e}")
                # 出错时保留文章（避免误删）
                filtered.append(article)

        logger.info(f"阈值过滤: {len(articles)} -> {len(filtered)}")
        # 按评分排序
        filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
        return filtered

    def _meets_thresholds(self, article: Dict[str, Any]) -> bool:
        """
        检查文章是否满足阈值条件

        Args:
            article: 文章数据

        Returns:
            是否满足
        """
        # 1. 检查综合评分
        score = article.get("score", 0)
        if score < self.thresholds.scoring.min_score:
            return False

        # 2. 检查内容长度
        if not self._meets_content_thresholds(article):
            return False

        # 3. 检查时间窗口
        if not self._within_time_window(article):
            return False

        # 4. 根据来源检查特定阈值
        source = article.get("source") or ""

        if "arXiv" in source:
            return self._meets_arxiv_thresholds(article)
        elif "GitHub" in source:
            return self._meets_github_thresholds(article)
        elif "HuggingFace" in source:
            return self._meets_huggingface_thresholds(article)

        return True

    def _calculate_score(self, article: Dict[str, Any]) -> float:
        """
        计算文章综合评分

        评分维度：
        - source_priority: 数据源优先级 (0-1)
        - keyword_match: 关键词匹配度 (0-1)
        - recency: 时效性 (0-1)
        - engagement: 互动指标 (0-1)
        """
        weights = self.thresholds.scoring.weights

        # 1. 数据源优先级
        source_priority = self._score_source_priority(article)

        # 2. 关键词匹配
        keyword_match = self._score_keyword_match(article)

        # 3. 时效性
        recency = self._score_recency(article)

        # 4. 互动指标
        engagement = self._score_engagement(article)

        # 加权求和
        score = (
            weights.get("source_priority", 0.3) * source_priority +
            weights.get("keyword_match", 0.3) * keyword_match +
            weights.get("recency", 0.2) * recency +
            weights.get("engagement", 0.2) * engagement
        )

        return round(score, 3)

    def _score_source_priority(self, article: Dict[str, Any]) -> float:
        """数据源优先级评分"""
        source = article.get("source", "") or ""

        # 根据数据源类型评分
        priority_map = {
            "arXiv": 1.0,
            "arXiv Sanity": 1.0,
            "NeurIPS": 0.95,
            "ICML": 0.95,
            "OpenAI": 0.9,
            "Anthropic": 0.9,
            "Google DeepMind": 0.9,
            "Meta AI": 0.85,
            "HuggingFace": 0.8,
            "GitHub": 0.7,
            "MIT Technology Review": 0.75,
            "Nature AI": 0.8,
            "The Verge": 0.6,
        }

        for key, value in priority_map.items():
            if key in str(source):
                return value

        return 0.5  # 默认分数

    def _score_keyword_match(self, article: Dict[str, Any]) -> float:
        """关键词匹配评分"""
        # 使用matched_categories或简单统计
        matched = article.get("matched_categories", [])
        # 处理 None 值
        if matched is None:
            matched = []
        if matched and isinstance(matched, list):
            # 至少匹配一个分类给0.6分，每多一个增加0.1分
            return min(0.6 + len(matched) * 0.1, 1.0)

        # 没有matched_categories时简单检查
        # 处理 None 值
        title = article.get('title', '') or ''
        description = article.get('description', '') or ''
        text = f"{title} {description}".lower()
        keywords = self.config.keywords.get_all_keywords()

        # 确保 keywords 不是 None
        if keywords is None:
            keywords = []

        # 确保 keywords 是一个列表，而不是 None 或其他类型
        if not isinstance(keywords, list):
            keywords = list(keywords) if keywords else []

        matches = sum(1 for kw in keywords if kw and kw.lower() in text)
        return min(matches * 0.1, 1.0)

    def _score_recency(self, article: Dict[str, Any]) -> float:
        """时效性评分"""
        published_at = article.get("published_at")
        if not published_at:
            return 0.5  # 无时间信息给中等分

        try:
            pub_dt = self._parse_datetime(published_at)
            if not pub_dt:
                return 0.5

            hours_ago = (datetime.now() - pub_dt).total_seconds() / 3600

            # 24小时内给满分，之后递减
            if hours_ago <= 24:
                return 1.0
            elif hours_ago <= 48:
                return 0.7
            elif hours_ago <= 72:
                return 0.4
            else:
                return 0.2

        except Exception:
            return 0.5

    def _score_engagement(self, article: Dict[str, Any]) -> float:
        """互动指标评分"""
        # GitHub星标、HuggingFace点赞等
        stars = article.get("stars", 0)
        today_stars = article.get("today_stars", 0)
        likes = article.get("likes", 0)
        downloads = article.get("downloads", 0)

        # 综合互动分数
        score = today_stars * 0.01 + stars * 0.001 + likes * 0.01 + downloads * 0.0001

        return min(score, 1.0)

    def _meets_content_thresholds(self, article: Dict[str, Any]) -> bool:
        """检查内容长度阈值"""
        title = article.get("title", "")
        description = article.get("description", "")

        # 处理 None 值
        if title is None:
            title = ""
        if description is None:
            description = ""

        title_len = len(title)
        desc_len = len(description)

        thresholds = self.thresholds.content

        if title_len < thresholds.min_title_length:
            return False
        if title_len > thresholds.max_title_length:
            return False
        if desc_len < thresholds.min_description_length:
            return False

        return True

    def _within_time_window(self, article: Dict[str, Any]) -> bool:
        """检查是否在时间窗口内"""
        published_at = article.get("published_at")
        if not published_at:
            return True  # 无时间信息不过滤

        try:
            pub_dt = self._parse_datetime(published_at)
            if not pub_dt:
                return True

            hours = self.thresholds.time.primary_window_hours
            cutoff = datetime.now() - timedelta(hours=hours)
            return pub_dt >= cutoff

        except Exception:
            return True

    def _meets_arxiv_thresholds(self, article: Dict[str, Any]) -> bool:
        """检查arXiv论文阈值"""
        # 简化处理：实际需要调用arXiv API获取引用数
        # 这里假设论文已经通过其他方式筛选
        return True

    def _meets_github_thresholds(self, article: Dict[str, Any]) -> bool:
        """检查GitHub项目阈值"""
        thresholds = self.thresholds.github

        # 检查星标数（处理 None 值）
        stars_config = thresholds.stars
        if stars_config is not None and isinstance(stars_config, dict):
            min_stars = stars_config.get("min_stars", 0)
            stars = article.get("stars", 0)
            if stars < min_stars:
                return False

        # 检查今日星标（处理 None 值）
        if stars_config is not None and isinstance(stars_config, dict):
            min_today = stars_config.get("min_stars_daily", 0)
            today_stars = article.get("today_stars", 0)
            if today_stars < min_today:
                return False

        return True

    def _meets_huggingface_thresholds(self, article: Dict[str, Any]) -> bool:
        """检查HuggingFace模型阈值"""
        thresholds = self.thresholds.huggingface

        likes = article.get("likes", 0)
        downloads = article.get("downloads", 0)

        if likes < thresholds.min_likes:
            return False
        if downloads < thresholds.min_downloads:
            return False

        return True

    @staticmethod
    def _parse_datetime(dt_str: str) -> datetime | None:
        """解析日期时间字符串"""
        if not dt_str:
            return None

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d",
            "%a, %d %b %Y %H:%M:%S %z",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue

        return None
