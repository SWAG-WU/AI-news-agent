#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书格式化模块

将资讯格式化为飞书机器人兼容的Markdown格式。
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import Config, get_config

logger = logging.getLogger(__name__)


class FeishuFormatter:
    """
    飞书格式化器

    将资讯列表格式化为飞书机器人兼容的Markdown日报。
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.prompts_dir = Path("prompts")

        # 分类映射
        self.category_map = {
            "tech": "🧠 技术突破",
            "industry": "🏢 行业动态",
            "policy": "⚖️ 政策与伦理",
            "opinion": "💡 专家观点",
            "highlights": "🔥 今日亮点",
        }

        # 加载提示词模板
        self._prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """加载日报生成提示词模板"""
        prompt_path = self.prompts_dir / "daily_report.txt"

        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()

        return None

    async def format(self, articles: List[Dict[str, Any]]) -> str:
        """
        格式化资讯为飞书日报

        Args:
            articles: 资讯列表

        Returns:
            格式化后的Markdown文本
        """
        logger.info(f"开始格式化日报，文章数: {len(articles)}")

        # 检查是否有足够内容
        min_items = self.config.thresholds.daily_output.min_total_items

        if len(articles) < min_items:
            logger.warning(f"资讯数量不足 ({len(articles)} < {min_items})，使用回退格式")
            return self._format_fallback(articles)

        # 按分类整理资讯
        categorized = self._categorize_articles(articles)

        # 生成日报
        report = self._generate_report(categorized)

        logger.info("日报格式化完成")
        return report

    def _categorize_articles(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """将文章按分类整理"""
        categorized = {
            "highlights": [],
            "tech": [],
            "industry": [],
            "policy": [],
            "opinion": [],
        }

        for article in articles:
            category = article.get("category", "tech")

            # 高分文章放入亮点
            score = article.get("score", 0)
            high_threshold = self.config.thresholds.scoring.high_score_threshold

            if score >= high_threshold and len(categorized["highlights"]) < 3:
                categorized["highlights"].append(article)
            else:
                # 根据源分类
                if category in categorized:
                    categorized[category].append(article)
                else:
                    categorized["tech"].append(article)

        return categorized

    def _generate_report(self, categorized: Dict[str, List[Dict[str, Any]]]) -> str:
        """生成日报文本"""
        lines = []

        # 标题
        date_str = datetime.now().strftime("%Y年%m月%d日")
        lines.append(f"【AI前沿日报｜{date_str}】")
        lines.append("")

        # 生成各分类内容
        for category_key, category_label in self.category_map.items():
            articles = categorized.get(category_key, [])

            if not articles:
                continue  # 空分类不显示

            # 检查是否超过最大数量
            max_items = self.config.thresholds.daily_output.max_items_per_category.get(
                category_key, 10
            )

            lines.append(f"{category_label}")

            for article in articles[:max_items]:
                lines.append(self._format_article(article, category_key))
                lines.append("")

        # 页脚
        lines.append(f"✅ 数据截至 {date_str} | 来源：arXiv / 官方博客 / 顶会等")

        return "\n".join(lines)

    def _format_article(self, article: Dict[str, Any], category: str) -> str:
        """格式化单篇文章"""
        title = article.get("title", "").strip()
        summary = article.get("summary", article.get("description", "")).strip()
        url = article.get("url", "")
        source = article.get("source", "")
        author = article.get("author", "")
        institution = article.get("institution", "")

        # 根据分类使用不同格式
        if category == "highlights":
            return self._format_highlight(title, summary)
        elif category == "tech":
            return self._format_tech_article(title, summary, author, institution, url)
        elif category == "industry":
            return self._format_industry_article(title, summary, source, url)
        elif category == "policy":
            return self._format_policy_article(title, summary, url)
        elif category == "opinion":
            return self._format_opinion_article(title, summary, author, url)
        else:
            return self._format_default_article(title, summary, url)

    def _format_highlight(self, title: str, summary: str) -> str:
        """格式化亮点文章"""
        lines = []
        lines.append(f"• {title}")
        lines.append(f"{summary[:150]}")  # 限制长度
        return "\n".join(lines)

    def _format_tech_article(self, title: str, summary: str,
                            author: str, institution: str, url: str) -> str:
        """格式化技术突破文章"""
        lines = []
        lines.append(f"• {title}")

        # 添加机构信息
        if institution:
            lines.append(f"（{institution}）")
        elif author:
            lines.append(f"（{author}）")

        lines.append(f"{summary[:200]}")
        if url:
            lines.append(f"[链接]({url})")

        return "\n".join(lines)

    def _format_industry_article(self, title: str, summary: str,
                                 source: str, url: str) -> str:
        """格式化行业动态文章"""
        lines = []
        lines.append(f"• {source}：{title}")
        lines.append(f"{summary[:150]}")
        if url:
            lines.append(f"[链接]({url})")
        return "\n".join(lines)

    def _format_policy_article(self, title: str, summary: str, url: str) -> str:
        """格式化政策伦理文章"""
        lines = []
        lines.append(f"• {title}")
        lines.append(f"{summary[:150]}")
        if url:
            lines.append(f"[链接]({url})")
        return "\n".join(lines)

    def _format_opinion_article(self, title: str, summary: str,
                                author: str, url: str) -> str:
        """格式化专家观点文章"""
        lines = []
        lines.append(f"• {author}：「{title}」")
        if url:
            lines.append(f"[出处]({url})")
        return "\n".join(lines)

    def _format_default_article(self, title: str, summary: str, url: str) -> str:
        """默认格式"""
        lines = []
        lines.append(f"• {title}")
        lines.append(f"{summary[:150]}")
        if url:
            lines.append(f"[链接]({url})")
        return "\n".join(lines)

    def _format_fallback(self, articles: List[Dict[str, Any]]) -> str:
        """格式化回退版本（资讯不足时）"""
        date_str = datetime.now().strftime("%Y年%m月%d日")

        lines = []
        lines.append(f"【AI前沿日报｜{date_str}】")
        lines.append("")

        if not articles:
            lines.append("🟡 当前时段暂无重大AI更新。")
            lines.append("")
            lines.append("建议持续关注 arXiv CS.AI 与 HuggingFace 新动向。")
        else:
            lines.append("🟡 当前时段重大更新较少，以下是为您整理的资讯：")
            lines.append("")

            for article in articles:
                lines.append(f"• {article.get('title', '')}")
                summary = article.get("summary", article.get("description", ""))
                if summary:
                    lines.append(f"  {summary[:100]}")
                lines.append("")

        lines.append("")
        lines.append(f"✅ 数据截至 {date_str} | 来源：arXiv / 官方博客 / 顶会等")

        return "\n".join(lines)


class FeishuCardFormatter(FeishuFormatter):
    """
    飞书卡片格式化器

    生成飞书卡片消息格式（更美观，需要额外配置）。
    """

    async def format(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        格式化为飞书卡片格式

        Returns:
            飞书卡片消息字典
        """
        # 先生成Markdown
        markdown = await super().format(articles)

        # 转换为卡片格式
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "AI前沿日报"
                    },
                    "template": "orange"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": markdown
                        }
                    }
                ]
            }
        }

        return card
