#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM摘要生成模块

使用大语言模型生成资讯摘要。
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import Config, get_config

logger = logging.getLogger(__name__)


class LLMSummarizer:
    """
    LLM摘要生成器

    使用OpenAI API生成中文摘要。
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.prompts_dir = Path("prompts")

        # 初始化OpenAI客户端
        self.client = AsyncOpenAI(
            api_key=self.config.openai_api_key,
            base_url=self.config.openai_base_url,
        )
        self.model = self.config.openai_model

        # 加载提示词模板
        self._prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """加载摘要生成提示词模板"""
        prompt_path = self.prompts_dir / "summarize.txt"

        if not prompt_path.exists():
            logger.warning(f"提示词文件不存在: {prompt_path}")
            return self._get_default_prompt()

        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _get_default_prompt(self) -> str:
        """获取默认提示词"""
        return """你是一位专业的AI科技资讯编辑，擅长将复杂的技术内容转化为简洁、准确的中文摘要。

根据提供的资讯内容，生成一段**简洁、专业、风格统一**的中文摘要。

要求：
1. 长度：1-2句话，不超过80字
2. 风格：客观、专业，避免夸张
3. 内容：包含[机构/作者]、[技术名称]、[关键创新点]、[潜在影响]

资讯内容：
{{CONTENT}}
"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def summarize(self, article: Dict[str, Any]) -> str:
        """
        生成文章摘要

        Args:
            article: 文章数据

        Returns:
            生成的摘要
        """
        # 如果已有摘要且符合要求，直接返回
        existing_summary = article.get("summary", "")
        if existing_summary and len(existing_summary) >= 20:
            return existing_summary

        # 构建输入内容
        content = self._build_content(article)

        try:
            summary = await self._generate_summary(content)
            logger.debug(f"生成摘要: {article.get('title', '')[:30]}... -> {summary}")
            return summary

        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            # 回退：使用原描述截断
            return self._fallback_summary(article)

    def _build_content(self, article: Dict[str, Any]) -> str:
        """构建用于摘要的输入内容"""
        title = article.get("title", "")
        description = article.get("description", "")
        source = article.get("source", "")
        author = article.get("author", "")

        # 构建结构化输入
        parts = []
        if source:
            parts.append(f"来源：{source}")
        if author:
            parts.append(f"作者：{author}")
        parts.append(f"标题：{title}")
        if description:
            parts.append(f"内容：{description[:500]}")  # 限制输入长度

        return "\n".join(parts)

    async def _generate_summary(self, content: str) -> str:
        """调用LLM生成摘要"""
        prompt = self._prompt_template.replace("{{CONTENT}}", content)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一位专业的AI科技资讯编辑，擅长生成简洁准确的中文摘要。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=200,
        )

        summary = response.choices[0].message.content.strip()

        # 清理可能的引号
        summary = summary.strip('"\'""''')

        return summary

    def _fallback_summary(self, article: Dict[str, Any]) -> str:
        """回退摘要（使用原描述）"""
        description = article.get("description", "")

        if not description:
            return article.get("title", "")

        # 截取第一句话
        sentences = description.split("。")
        if sentences:
            first_sentence = sentences[0].strip()
            if len(first_sentence) >= 20:
                return first_sentence + "。"

        return description[:100]

    async def summarize_batch(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量生成摘要

        Args:
            articles: 文章列表

        Returns:
            添加了摘要的文章列表
        """
        logger.info(f"开始批量生成摘要，文章数: {len(articles)}")

        result = []
        for i, article in enumerate(articles):
            try:
                summary = await self.summarize(article)
                article["summary"] = summary
                result.append(article)

                if (i + 1) % 10 == 0:
                    logger.info(f"摘要进度: {i + 1}/{len(articles)}")

            except Exception as e:
                logger.error(f"生成摘要失败 ({i}): {e}")
                article["summary"] = self._fallback_summary(article)
                result.append(article)

        logger.info(f"批量摘要完成")
        return result


class CachedSummarizer(LLMSummarizer):
    """
    带缓存的摘要生成器

    避免对相同内容重复生成摘要。
    """

    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self._cache: Dict[str, str] = {}

    async def summarize(self, article: Dict[str, Any]) -> str:
        """生成摘要（带缓存）"""
        # 生成缓存键
        cache_key = self._get_cache_key(article)

        if cache_key in self._cache:
            logger.debug(f"使用缓存摘要: {cache_key}")
            return self._cache[cache_key]

        # 生成新摘要
        summary = await super().summarize(article)

        # 存入缓存
        self._cache[cache_key] = summary

        return summary

    def _get_cache_key(self, article: Dict[str, Any]) -> str:
        """生成缓存键"""
        import hashlib

        title = article.get("title", "")
        url = article.get("url", "")

        content = f"{title}|{url}"
        return hashlib.md5(content.encode()).hexdigest()

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


class MockSummarizer(LLMSummarizer):
    """
    模拟摘要生成器（用于测试）

    不调用真实API，返回简单的规则摘要。
    """

    async def summarize(self, article: Dict[str, Any]) -> str:
        """生成模拟摘要"""
        source = article.get("source", "")
        title = article.get("title", "")
        description = article.get("description", "")

        # 简单规则
        if description:
            # 取第一句话
            first = description.split("。")[0].split(".")[0].strip()
            if len(first) >= 20:
                return first + "。"
            return description[:100] + "..."

        return f"[{source}] {title}"


def create_summarizer(config: Optional[Config] = None,
                      use_cache: bool = True,
                      mock: bool = False) -> LLMSummarizer:
    """
    创建摘要生成器

    Args:
        config: 配置对象
        use_cache: 是否使用缓存
        mock: 是否使用模拟模式（不调用API）

    Returns:
        摘要生成器实例
    """
    if mock:
        return MockSummarizer(config)

    if use_cache:
        return CachedSummarizer(config)

    return LLMSummarizer(config)
