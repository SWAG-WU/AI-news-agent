#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书格式化模块

将资讯格式化为飞书机器人兼容的Markdown格式，支持6种分类显示。
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

    将资讯列表格式化为飞书机器人兼容的Markdown日报，支持6种分类：
    1. 学术研究 (academic)
    2. 实验室博客 (lab_blog)
    3. 专业媒体 (media)
    4. 工具产品 (tools)
    5. 社区讨论 (community)
    6. Newsletter (newsletter)
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.prompts_dir = Path("prompts")

        # 默认6种分类映射（如果配置文件不存在）
        self.category_map = {
            "academic": "🎓 学术研究",
            "lab_blog": "🏢 实验室博客",
            "media": "📰 专业媒体",
            "tools": "🛠️ 工具产品",
            "community": "💬 社区讨论",
            "newsletter": "📧 Newsletter",
        }

        # 加载自定义分类配置
        self._load_category_config()

        # 加载提示词模板
        self._prompt_template = self._load_prompt_template()

    def _load_category_config(self):
        """加载分类配置"""
        if self.config.categories:
            for cat_id, cat_info in self.config.categories.categories.items():
                self.category_map[cat_id] = f"{cat_info.icon} {cat_info.name}"

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

        # 分离常规资讯和额外资讯（新模型发布等）
        regular_articles = []
        extra_articles = []

        for article in articles:
            if article.get('is_extra', False):
                extra_articles.append(article)
            else:
                regular_articles.append(article)

        logger.info(f"常规资讯: {len(regular_articles)} 条, 额外资讯: {len(extra_articles)} 条")

        # 按分类整理资讯
        categorized = self._categorize_articles(regular_articles)

        # 生成日报
        report = self._generate_report(categorized, extra_articles)

        logger.info("日报格式化完成")
        return report

    def _categorize_articles(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        将文章按6种分类整理，并按发布时间降序排序（最新的在前）

        分类优先级：
        1. 如果文章已有 category 字段，使用该分类
        2. 否则根据 source 字段映射到分类
        3. 最后根据关键词内容推断分类
        """
        categorized = {
            "academic": [],
            "lab_blog": [],
            "media": [],
            "tools": [],
            "community": [],
            "newsletter": [],
        }

        for article in articles:
            category = self._determine_category(article)

            if category in categorized:
                categorized[category].append(article)
            else:
                # 默认归入学术研究
                categorized["academic"].append(article)

        # 按发布时间降序排序（最新的在前），published_at 为空的排在最后
        for category_key in categorized:
            categorized[category_key].sort(
                key=lambda x: x.get("published_at") or "1970-01-01T00:00:00Z",
                reverse=True
            )

        return categorized

    def _determine_category(self, article: Dict[str, Any]) -> str:
        """
        确定文章的分类

        优先级：
        1. 文章已有的 category 字段
        2. 根据 source 字段映射
        3. 根据关键词内容推断
        """
        # 1. 检查文章是否已有分类
        if "category" in article and article["category"] in self.category_map:
            return article["category"]

        # 2. 根据 source 映射
        source = article.get("source", "").lower()
        if self.config.categories:
            mapped = self.config.categories.map_source_to_category(source)
            if mapped:
                return mapped

        # 3. 根据关键词内容推断
        title = article.get("title", "").lower()
        description = article.get("description", "").lower()
        text = f"{title} {description}"

        if self.config.categories:
            inferred = self.config.categories.get_category_by_keywords(text)
            if inferred:
                return inferred

        # 4. 默认分类推断
        if any(kw in text for kw in ["arxiv", "paper", "research", "neurips", "icml"]):
            return "academic"
        elif any(kw in text for kw in ["openai", "deepmind", "anthropic", "google", "meta", "blog"]):
            return "lab_blog"
        elif any(kw in text for kw in ["product hunt", "tool", "app", "platform", "release"]):
            return "tools"
        elif any(kw in text for kw in ["hacker news", "reddit", "discussion"]):
            return "community"
        elif any(kw in text for kw in ["newsletter", "batch", "import ai"]):
            return "newsletter"
        else:
            return "media"

    def _generate_report(self, categorized: Dict[str, List[Dict[str, Any]]], extra_articles: List[Dict[str, Any]] = None) -> str:
        """生成日报文本"""
        lines = []

        # 标题
        date_str = datetime.now().strftime("%Y年%m月%d日")
        lines.append(f"# 【AI前沿日报｜{date_str}】")
        lines.append("")

        # 统计信息
        total_count = sum(len(articles) for articles in categorized.values())
        extra_count = len(extra_articles) if extra_articles else 0
        lines.append(f"📊 今日共收录 {total_count} 条资讯" + (f" + {extra_count} 条特别资讯" if extra_count > 0 else ""))
        lines.append("")

        # ========== 新模型发布特别资讯（如果有）==========
        if extra_articles and extra_count > 0:
            lines.append("## 🚀 特别关注：新模型发布")
            lines.append("")

            # 按新模型类型分组
            new_model_articles = [a for a in extra_articles if a.get('extra_type') == 'new_model_release']

            if new_model_articles:
                lines.append("*检测到重要模型发布，突破常规资讯限制*")
                lines.append("")

                for article in new_model_articles:
                    model_info = article.get('model_info', {})
                    model_name = model_info.get('model_name', '新模型')
                    company = model_info.get('company', '')

                    title = article.get("title", "").strip()
                    summary = article.get("summary", article.get("description", "")).strip()
                    url = article.get("url", "")
                    source = article.get("source", "")
                    published_at = article.get("published_at", "")

                    # 格式化时间
                    formatted_time = self._format_published_time(published_at)

                    # 格式化新模型发布资讯
                    lines.append(f"### {model_name}")
                    if company:
                        lines.append(f"*{company}*")
                    if formatted_time:
                        lines.append(f"*🕒 {formatted_time}*")
                    lines.append("")
                    lines.append(summary[:300])
                    if url:
                        lines.append(f"[查看详情]({url})")
                    lines.append("")

            lines.append("---")
            lines.append("")

        # ========== 常规资讯 ==========
        # 按分类优先级顺序生成内容
        category_order = ["academic", "lab_blog", "media", "tools", "community", "newsletter"]

        for category_key in category_order:
            articles = categorized.get(category_key, [])

            if not articles:
                continue  # 空分类不显示

            category_label = self.category_map.get(category_key, category_key)

            # 检查是否超过最大数量
            max_items = self.config.thresholds.daily_output.max_items_per_category.get(
                category_key, 10
            )

            lines.append(f"## {category_label}")
            lines.append("")

            for article in articles[:max_items]:
                lines.append(self._format_article(article, category_key))
                lines.append("")

        # 页脚
        lines.append("---")
        lines.append(f"✅ 数据截至 {date_str} | 来源：arXiv / 官方博客 / 专业媒体 / 社区等")

        return "\n".join(lines)

    def _format_article(self, article: Dict[str, Any], category: str) -> str:
        """格式化单篇文章"""
        title = article.get("title", "").strip()
        summary = article.get("summary", article.get("description", "")).strip()
        url = article.get("url", "")
        source = article.get("source", "")
        author = article.get("author", "")
        institution = article.get("institution", "")
        published_at = article.get("published_at", "")

        # 格式化发布时间
        formatted_time = self._format_published_time(published_at)

        # 根据分类使用不同格式
        if category == "academic":
            return self._format_academic_article(title, summary, author, institution, url, formatted_time)
        elif category == "lab_blog":
            return self._format_lab_blog_article(title, summary, source, url, formatted_time)
        elif category == "media":
            return self._format_media_article(title, summary, source, url, formatted_time)
        elif category == "tools":
            return self._format_tools_article(title, summary, url, formatted_time)
        elif category == "community":
            return self._format_community_article(title, summary, source, url, formatted_time)
        elif category == "newsletter":
            return self._format_newsletter_article(title, summary, source, url, formatted_time)
        else:
            return self._format_default_article(title, summary, url, formatted_time)

    def _format_published_time(self, published_at: str) -> str:
        """格式化发布时间为中文友好格式"""
        if not published_at:
            return ""

        try:
            # 尝试解析 ISO 格式时间
            for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ",
                       "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    dt = datetime.strptime(published_at.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
                    # 转换为北京时间 (UTC+8)
                    from datetime import timedelta
                    dt_beijing = dt + timedelta(hours=8)
                    return dt_beijing.strftime("%m月%d日 %H:%M")
                except ValueError:
                    continue
            return published_at
        except Exception:
            return published_at

    def _infer_source_from_url(self, url: str) -> str:
        """根据 URL 推断来源平台"""
        if not url:
            return ""

        url_lower = url.lower()

        # GitHub
        if "github.com" in url_lower or "github.io" in url_lower:
            return "GitHub"

        # OpenAI
        if "openai.com" in url_lower:
            return "OpenAI"

        # Microsoft
        if "microsoft.com" in url_lower or "microsoftresearch" in url_lower:
            return "Microsoft"

        # Google
        if "google.com" in url_lower or "googleblog" in url_lower:
            return "Google"

        # Meta
        if "meta.com" in url_lower or "fb.com" in url_lower:
            return "Meta"

        # Anthropic
        if "anthropic.com" in url_lower:
            return "Anthropic"

        # arXiv
        if "arxiv.org" in url_lower:
            return "arXiv"

        # Hugging Face
        if "huggingface.co" in url_lower:
            return "Hugging Face"

        # MIT Technology Review
        if "technologyreview.com" in url_lower:
            return "MIT Tech Review"

        # The Verge
        if "theverge.com" in url_lower:
            return "The Verge"

        # Wired
        if "wired.com" in url_lower:
            return "Wired"

        # Nature
        if "nature.com" in url_lower:
            return "Nature"

        # Wired
        if "wired.com" in url_lower:
            return "Wired"

        # 通用域名提取
        import re
        match = re.search(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+)\.(?:com|org|io|net|ai)', url_lower)
        if match:
            domain = match.group(1)
            # 简单首字母大写
            return domain.capitalize()

        return ""

    def _format_academic_article(self, title: str, summary: str,
                                author: str, institution: str, url: str,
                                formatted_time: str = "") -> str:
        """格式化学术研究文章"""
        lines = []
        lines.append(f"### {title}")

        # 添加作者/机构信息
        meta_info = []
        if author:
            meta_info.append(f"作者: {author}")
        if institution:
            meta_info.append(f"机构: {institution}")
        if formatted_time:
            meta_info.append(f"🕒 {formatted_time}")

        if meta_info:
            lines.append("*" + " | ".join(meta_info) + "*")

        lines.append("")
        lines.append(summary[:300])
        if url:
            lines.append(f"[查看论文]({url})")

        return "\n".join(lines)

    def _format_lab_blog_article(self, title: str, summary: str,
                                 source: str, url: str,
                                 formatted_time: str = "") -> str:
        """格式化实验室博客文章"""
        lines = []
        lines.append(f"### {title}")

        meta_info = []
        if source:
            meta_info.append(f"来源: {source}")
        if formatted_time:
            meta_info.append(f"🕒 {formatted_time}")

        if meta_info:
            lines.append("*" + " | ".join(meta_info) + "*")

        lines.append("")
        lines.append(summary[:300])
        if url:
            lines.append(f"[阅读原文]({url})")

        return "\n".join(lines)

    def _format_media_article(self, title: str, summary: str,
                             source: str, url: str,
                             formatted_time: str = "") -> str:
        """格式化专业媒体文章"""
        lines = []
        lines.append(f"### {title}")

        meta_info = []
        if source:
            meta_info.append(f"{source}")
        if formatted_time:
            meta_info.append(f"🕒 {formatted_time}")

        if meta_info:
            lines.append("*" + " | ".join(meta_info) + "*")

        lines.append("")
        lines.append(summary[:300])
        if url:
            lines.append(f"[阅读全文]({url})")

        return "\n".join(lines)

    def _format_tools_article(self, title: str, summary: str,
                             url: str,
                             formatted_time: str = "") -> str:
        """格式化工具产品文章"""
        lines = []
        lines.append(f"### {title}")

        if formatted_time:
            lines.append(f"*🕒 {formatted_time}*")

        lines.append("")
        lines.append(summary[:300])
        if url:
            lines.append(f"[查看产品]({url})")

        return "\n".join(lines)

    def _format_community_article(self, title: str, summary: str,
                                  source: str, url: str,
                                  formatted_time: str = "") -> str:
        """格式化社区讨论文章"""
        lines = []
        lines.append(f"### {title}")

        meta_info = []
        if source:
            meta_info.append(f"来源: {source}")
        if formatted_time:
            meta_info.append(f"🕒 {formatted_time}")

        if meta_info:
            lines.append("*" + " | ".join(meta_info) + "*")

        lines.append("")
        lines.append(summary[:300])
        if url:
            lines.append(f"[参与讨论]({url})")

        return "\n".join(lines)

    def _format_newsletter_article(self, title: str, summary: str,
                                   source: str, url: str,
                                   formatted_time: str = "") -> str:
        """格式化Newsletter文章"""
        lines = []
        lines.append(f"### {title}")

        meta_info = []
        if source:
            meta_info.append(f"来源: {source}")
        if formatted_time:
            meta_info.append(f"🕒 {formatted_time}")

        if meta_info:
            lines.append("*" + " | ".join(meta_info) + "*")

        lines.append("")
        lines.append(summary[:300])
        if url:
            lines.append(f"[阅读原文]({url})")

        return "\n".join(lines)

    def _format_default_article(self, title: str, summary: str, url: str,
                               formatted_time: str = "") -> str:
        """默认格式"""
        lines = []
        lines.append(f"### {title}")

        if formatted_time:
            lines.append(f"*🕒 {formatted_time}*")

        lines.append("")
        lines.append(summary[:300])
        if url:
            lines.append(f"[查看详情]({url})")

        return "\n".join(lines)

    def _format_fallback(self, articles: List[Dict[str, Any]]) -> str:
        """格式化回退版本（资讯不足时）"""
        date_str = datetime.now().strftime("%Y年%m月%d日")

        lines = []
        lines.append(f"# 【AI前沿日报｜{date_str}】")
        lines.append("")

        if not articles:
            lines.append("🟡 当前时段暂无重大AI更新。")
            lines.append("")
            lines.append("建议持续关注 arXiv CS.AI 与 HuggingFace 新动向。")
        else:
            lines.append("🟡 当前时段重大更新较少，以下是为您整理的资讯：")
            lines.append("")

            for article in articles:
                title = article.get('title', '')
                summary = article.get("summary", article.get("description", ""))
                url = article.get('url', '')
                source = article.get('source', '')

                lines.append(f"## {title}")
                if summary:
                    lines.append(summary[:200])
                # 添加来源和链接
                if source:
                    lines.append(f"*来源: {source}*")
                if url:
                    lines.append(f"[查看详情]({url})")
                lines.append("")

        lines.append("---")
        lines.append(f"✅ 数据截至 {date_str} | 来源：arXiv / 官方博客 / 专业媒体 / 社区等")

        return "\n".join(lines)


class FeishuCardFormatter(FeishuFormatter):
    """
    飞书卡片格式化器

    生成结构化飞书卡片消息，使用多元素布局替代纯文本 Markdown。
    """

    _LINK_LABELS = {
        "academic": "查看论文",
        "lab_blog": "阅读原文",
        "media": "阅读全文",
        "tools": "查看产品",
        "community": "参与讨论",
        "newsletter": "阅读原文",
        "extra": "查看详情",
    }

    async def format(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        格式化为飞书结构化卡片

        Returns:
            飞书卡片消息字典
        """
        date_str = datetime.now().strftime("%Y年%m月%d日")
        min_items = self.config.thresholds.daily_output.min_total_items

        if len(articles) < min_items:
            return self._build_fallback_card(articles, date_str)

        regular_articles = [a for a in articles if not a.get("is_extra", False)]
        extra_articles = [a for a in articles if a.get("is_extra", False)]
        categorized = self._categorize_articles(regular_articles)

        total_count = sum(len(v) for v in categorized.values())
        extra_count = len(extra_articles)

        elements = []

        # 统计摘要行
        summary_text = f"📊 今日共收录 **{total_count}** 条资讯"
        if extra_count > 0:
            summary_text += f" + **{extra_count}** 条特别资讯"
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": summary_text}})

        # 新模型发布特别资讯
        if extra_articles:
            elements.append({"tag": "hr"})
            # 使用引用样式突出特别资讯标题
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": "> 🚀 **特别关注：新模型发布**\n*> 检测到重要模型发布，突破常规资讯限制*"}
            })
            for i, article in enumerate(extra_articles):
                elements.append({"tag": "div", "text": {"tag": "lark_md", "content": self._article_to_lark_md(article, "extra")}})
                if i < len(extra_articles) - 1:
                    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "---"}})

        # 常规分类
        category_order = ["academic", "lab_blog", "media", "tools", "community", "newsletter"]
        for cat_key in category_order:
            arts = categorized.get(cat_key, [])
            if not arts:
                continue
            max_items = self.config.thresholds.daily_output.max_items_per_category.get(cat_key, 10)
            label = self.category_map.get(cat_key, cat_key)

            elements.append({"tag": "hr"})
            # 使用引用样式突出分类标题，增强视觉层级
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"> **{label}**"}})
            for i, article in enumerate(arts[:max_items]):
                elements.append({"tag": "div", "text": {"tag": "lark_md", "content": self._article_to_lark_md(article, cat_key)}})
                # 非最后一条文章后添加分隔线
                if i < len(arts[:max_items]) - 1:
                    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "---"}})

        # 页脚
        elements.append({"tag": "hr"})
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"✅ 数据截至 {date_str} | 来源：arXiv / 官方博客 / 专业媒体 / 社区等"}})

        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"📡 AI前沿日报 | {date_str}"},
                    "template": "blue"
                },
                "elements": elements
            }
        }

    def _article_to_lark_md(self, article: Dict[str, Any], category: str) -> str:
        """将文章转换为 lark_md 格式字符串，增强视觉层级"""
        title = article.get("title", "").strip()
        summary = article.get("summary", article.get("description", "")).strip()
        url = article.get("url", "")
        source = article.get("source", "")
        author = article.get("author", "")
        institution = article.get("institution", "")
        published_at = article.get("published_at", "")
        formatted_time = self._format_published_time(published_at)

        lines = [f"**▸ {title}**"]

        # 元信息行
        meta_parts = []
        if category == "academic":
            if author:
                meta_parts.append(f"👤 {author}")
            if institution:
                meta_parts.append(f"🏛️ {institution}")
            # 学术研究也显示来源平台
            if source:
                meta_parts.append(f"📢 {source}")
            else:
                inferred_source = self._infer_source_from_url(url)
                if inferred_source:
                    meta_parts.append(f"📢 {inferred_source}")
        elif category == "extra":
            model_info = article.get("model_info", {})
            company = model_info.get("company", "")
            if company:
                meta_parts.append(f"🏢 {company}")
            # 根据 URL 推断来源
            inferred_source = self._infer_source_from_url(url)
            if inferred_source:
                meta_parts.append(f"📢 {inferred_source}")
        else:
            # 优先使用 source，如果为空则根据 URL 推断
            if source:
                meta_parts.append(f"📢 {source}")
            else:
                # 根据 URL 推断来源平台
                inferred_source = self._infer_source_from_url(url)
                if inferred_source:
                    meta_parts.append(f"📢 {inferred_source}")
        if formatted_time:
            meta_parts.append(f"🕒 {formatted_time}")

        if meta_parts:
            lines.append("`" + " │ ".join(meta_parts) + "`")

        if summary:
            lines.append(f"> {summary[:280]}")

        if url:
            label = self._LINK_LABELS.get(category, "查看详情")
            lines.append(f"👉 [{label}]({url})")

        return "\n".join(lines)

    def _build_fallback_card(self, articles: List[Dict[str, Any]], date_str: str) -> Dict[str, Any]:
        """资讯不足时的回退卡片"""
        elements = []

        if not articles:
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "🟡 当前时段暂无重大AI更新。\n\n建议持续关注 arXiv CS.AI 与 HuggingFace 新动向。"}})
        else:
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "🟡 当前时段重大更新较少，以下是为您整理的资讯："}})
            for article in articles:
                title = article.get("title", "")
                summary = article.get("summary", article.get("description", ""))
                url = article.get("url", "")
                source = article.get("source", "")

                lines = [f"**{title}**"]
                if summary:
                    lines.append(summary[:200])
                if source:
                    lines.append(f"*来源: {source}*")
                if url:
                    lines.append(f"[查看详情]({url})")
                elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}})

        elements.append({"tag": "hr"})
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"✅ 数据截至 {date_str} | 来源：arXiv / 官方博客 / 专业媒体 / 社区等"}})

        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"📡 AI前沿日报 | {date_str}"},
                    "template": "blue"
                },
                "elements": elements
            }
        }
