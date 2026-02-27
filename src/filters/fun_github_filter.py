#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
有趣GitHub项目过滤器

从GitHub项目中筛选出简单、实用、能提升工作效率或增加工作乐趣的项目。
"""

import logging
from typing import Any, Dict, List
from datetime import datetime

from src.config import Config, get_config

logger = logging.getLogger(__name__)


class FunGithubFilter:
    """
    有趣GitHub项目过滤器

    专门从GitHub项目中识别那些：
    1. 简单易用，能提升工作效率的工具
    2. 有趣好玩，能增加工作乐趣的项目
    """

    def __init__(self, config: Config = None):
        self.config = config or get_config()

        # 定义提升效率的关键字
        self.productivity_keywords = [
            # 工作效率提升工具
            'tool', 'utility', 'helper', 'boilerplate', 'template',
            'automation', 'script', 'cli', 'workflow', 'productivity',
            'efficiency', 'optimize', 'speed', 'fast', 'quick',

            # 编程辅助工具
            'code', 'refactor', 'lint', 'format', 'debug', 'profile',
            'testing', 'mock', 'stub', 'automation',

            # 数据处理
            'data', 'excel', 'csv', 'json', 'parser', 'convert',
            'clean', 'process', 'transform',

            # 办公辅助
            'note', 'todo', 'calendar', 'task', 'schedule', 'organize',
            'manage', 'tracker', 'dashboard', 'report'
        ]

        # 定义有趣好玩的关键字
        self.fun_keywords = [
            # 游戏/娱乐
            'game', 'arcade', 'fun', 'play', 'toy', 'demo',
            'animation', 'gif', 'image', 'video', 'music',
            'art', 'pixel', 'sprite', 'retro', 'arcade',

            # 创意/趣味
            'creative', 'amazing', 'cool', 'awesome', 'funny',
            'humor', 'meme', 'comic', 'cartoon', 'bongo cat',
            'cat', 'pet', 'emoji', 'gaming', 'mascot',

            # 视觉效果
            'visual', 'effect', 'beautiful', 'pretty', 'design',
            'theme', 'color', 'light', 'dark', 'aesthetic',
        ]

        # 垃圾关键字（排除不合适的项目）
        self.boring_keywords = [
            'docs', 'documentation', 'tutorial', 'course',
            'exercise', 'homework', 'assignment', 'lecture',
            'deprecated', 'archived', 'legacy', 'backup'
        ]

    def filter_fun_github_projects(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        筛选有趣的GitHub项目

        Args:
            articles: 文章列表

        Returns:
            有趣的GitHub项目列表
        """
        fun_projects = []

        for article in articles:
            if self._is_github_project(article) and self._is_fun_or_productive(article):
                article_copy = article.copy()
                # 标记为有趣GitHub项目
                article_copy['special_category'] = 'fun_github'
                article_copy['score'] = self._calculate_fun_score(article)  # 重新计算分数
                fun_projects.append(article_copy)

        # 按分数排序，选择最好的项目
        fun_projects.sort(key=lambda x: x.get('score', 0), reverse=True)

        # 返回最多2个有趣的项目
        return fun_projects[:2]

    def _is_github_project(self, article: Dict[str, Any]) -> bool:
        """检查是否为GitHub项目"""
        source = article.get('source', '').lower()
        url = article.get('url', '').lower()

        # 检查是否来自GitHub
        return 'github' in source or 'github.com' in url

    def _is_fun_or_productive(self, article: Dict[str, Any]) -> bool:
        """检查项目是否有趣或实用"""
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        text = f"{title} {description}"

        # 检查是否有垃圾关键字
        for keyword in self.boring_keywords:
            if keyword in text:
                return False

        # 检查是否有提升效率的关键字
        has_productivity = any(keyword in text for keyword in self.productivity_keywords)

        # 检查是否有有趣的关键字
        has_fun = any(keyword in text for keyword in self.fun_keywords)

        # 检查是否有特定的有趣词汇（如bongo cat）
        has_special_fun = 'bongo cat' in text or 'bongo' in text or any(emoji in text for emoji in ['😺', '🐱', '🎮', '🎨'])

        return has_productivity or has_fun or has_special_fun

    def _calculate_fun_score(self, article: Dict[str, Any]) -> float:
        """计算有趣的分数"""
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        text = f"{title} {description}"

        score = 0.5  # 基础分数

        # 增加效率相关分数
        productivity_matches = sum(1 for keyword in self.productivity_keywords if keyword in text)
        score += productivity_matches * 0.1

        # 增加有趣相关分数
        fun_matches = sum(1 for keyword in self.fun_keywords if keyword in text)
        score += fun_matches * 0.1

        # 特殊有趣项加分
        if 'bongo cat' in text:
            score += 0.5
        if any(emoji in text for emoji in ['😺', '🐱', '🎮', '🎨']):
            score += 0.2

        # 基于星标数调整分数
        stars = article.get('stars', 0)
        if stars > 1000:
            score += 0.3
        elif stars > 100:
            score += 0.2
        elif stars > 10:
            score += 0.1

        return min(score, 1.0)  # 限制最高分为1.0