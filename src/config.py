#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置加载模块

负责加载和管理所有配置文件，包括数据源、关键词、阈值和飞书配置。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


# ==================== 数据源配置模型 ====================

class SourceRateLimit(BaseModel):
    """数据源限流配置"""
    requests_per_minute: Optional[int] = None


class SourceConfig(BaseModel):
    """单个数据源配置"""
    base_url: str
    rss_url: Optional[str] = None
    search_query: Optional[str] = None
    max_results: Optional[int] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = None
    languages: Optional[List[str]] = None
    spoken_language: Optional[str] = None
    since: Optional[str] = None
    topic: Optional[str] = None
    news_url: Optional[str] = None


class Source(BaseModel):
    """数据源模型"""
    id: str
    name: str
    type: str  # academic, blog, code, conference, media
    priority: int
    enabled: bool = True
    config: SourceConfig
    rate_limit: Optional[SourceRateLimit] = None
    note: Optional[str] = None


class SourcesConfig(BaseModel):
    """数据源配置集合"""
    sources: List[Source]
    fallback_sources: Optional[List[Source]] = None

    def get_enabled_sources(self) -> List[Source]:
        """获取已启用的数据源"""
        return [s for s in self.sources if s.enabled]

    def get_sources_by_type(self, source_type: str) -> List[Source]:
        """按类型获取数据源"""
        return [s for s in self.sources if s.type == source_type and s.enabled]

    def get_sources_by_priority(self, min_priority: Optional[int] = None,
                                max_priority: Optional[int] = None) -> List[Source]:
        """按优先级范围获取数据源"""
        sources = self.get_enabled_sources()
        if min_priority is not None:
            sources = [s for s in sources if s.priority >= min_priority]
        if max_priority is not None:
            sources = [s for s in sources if s.priority <= max_priority]
        return sorted(sources, key=lambda x: x.priority)


# ==================== 关键词配置模型 ====================

class KeywordCategory(BaseModel):
    """关键词分类"""
    name: str
    description: str
    keywords: List[str]


class ExcludedKeywords(BaseModel):
    """排除关键词"""
    name: str
    description: str
    keywords: List[str]


class AliasMapping(BaseModel):
    """关键词别名映射"""
    description: str
    mappings: Dict[str, List[str]]


class KeywordsConfig(BaseModel):
    """关键词配置集合"""
    categories: Dict[str, KeywordCategory]
    excluded_keywords: ExcludedKeywords
    alias_mapping: AliasMapping

    def get_all_keywords(self) -> List[str]:
        """获取所有包含关键词"""
        all_keywords = []
        for category in self.categories.values():
            all_keywords.extend(category.keywords)
        return list(set(all_keywords))

    def get_category_keywords(self, category_name: str) -> List[str]:
        """获取指定分类的关键词"""
        if category_name in self.categories:
            return self.categories[category_name].keywords
        return []

    def is_excluded(self, text: str) -> bool:
        """检查文本是否包含排除关键词"""
        text_lower = text.lower()
        for keyword in self.excluded_keywords.keywords:
            if keyword.lower() in text_lower:
                return True
        return False


# ==================== 阈值配置模型 ====================

class ArxivThresholds(BaseModel):
    """arXiv阈值配置"""
    min_citations: int = 10
    min_scites: int = 5
    check_arxiv_sanity: bool = True
    min_sanity_score: int = 20


class GithubThresholds(BaseModel):
    """GitHub阈值配置"""
    trending: Optional[Dict[str, Any]] = None
    stars: Optional[Dict[str, int]] = None
    forks: Optional[Dict[str, int]] = None


class HuggingFaceThresholds(BaseModel):
    """HuggingFace阈值配置"""
    min_likes: int = 50
    min_downloads: int = 1000
    trending_check: bool = True


class ContentThresholds(BaseModel):
    """内容阈值配置"""
    min_title_length: int = 10
    max_title_length: int = 200
    min_description_length: int = 50
    required_categories_count: int = 1


class TimeThresholds(BaseModel):
    """时间阈值配置"""
    primary_window_hours: int = 24
    secondary_window_hours: int = 48
    fallback_window_days: int = 7


class DailyOutputThresholds(BaseModel):
    """每日输出阈值配置"""
    max_items_per_category: Dict[str, int]
    min_total_items: int = 5
    fallback_min_total_items: int = 3


class ScoringThresholds(BaseModel):
    """评分阈值配置"""
    weights: Dict[str, float]
    min_score: float = 0.6
    high_score_threshold: float = 0.8


class DeduplicationThresholds(BaseModel):
    """去重阈值配置"""
    enabled: bool = True
    method: str = "url_hash"
    similarity_threshold: float = 0.85
    content_hash_algorithm: str = "sha256"


class RetryThresholds(BaseModel):
    """重试配置"""
    max_retries: int = 3
    retry_delay_seconds: int = 5
    timeout_seconds: int = 30


class ThresholdsConfig(BaseModel):
    """阈值配置集合"""
    arxiv: ArxivThresholds
    github: GithubThresholds
    huggingface: HuggingFaceThresholds
    content: ContentThresholds
    time: TimeThresholds
    daily_output: DailyOutputThresholds
    scoring: ScoringThresholds
    deduplication: DeduplicationThresholds
    retry: RetryThresholds


# ==================== 飞书配置模型 ====================

class FeishuWebhook(BaseModel):
    """飞书Webhook配置"""
    enabled: bool = True
    url: str
    secret: Optional[str] = None
    note: Optional[str] = None


class FeishuMessage(BaseModel):
    """飞书消息配置"""
    msg_type: str = "text"
    content_type: str = "markdown"
    card: Optional[Dict[str, Any]] = None


class FeishuSchedule(BaseModel):
    """飞书定时配置"""
    enabled: bool = True
    cron: str = "0 9 * * *"
    timezone: str = "Asia/Shanghai"
    description: str = "每天早上9点推送"


class FeishuRetry(BaseModel):
    """飞书重试配置"""
    max_retries: int = 3
    retry_interval_seconds: int = 300


class FeishuTesting(BaseModel):
    """飞书测试模式配置"""
    mode: bool = False
    test_output_path: str = "data/test_output.md"
    description: str = "测试模式：true时输出到文件不推送"


class FeishuNotification(BaseModel):
    """飞书通知配置"""
    notify_on_success: bool = False
    notify_on_failure: bool = True
    failure_notification_webhook: str = ""


class FeishuRateLimit(BaseModel):
    """飞书限流配置"""
    enabled: bool = True
    max_messages_per_minute: int = 20


class FeishuConfig(BaseModel):
    """飞书配置集合"""
    webhook: FeishuWebhook
    message: FeishuMessage
    schedule: FeishuSchedule
    retry: FeishuRetry
    testing: FeishuTesting
    notification: FeishuNotification
    rate_limit: FeishuRateLimit


# ==================== 环境变量配置 ====================

class EnvSettings(BaseSettings):
    """环境变量配置"""
    # 飞书
    feishu_webhook_url: str
    feishu_webhook_secret: str = ""

    # 智谱 AI API
    zhipuai_api_key: str = ""
    zhipuai_model: str = "glm-4-flash"

    # GitHub
    github_token: str = ""

    # 代理
    http_proxy: str = ""
    https_proxy: str = ""

    # 其他
    log_level: str = "INFO"
    tz: str = "Asia/Shanghai"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        env_prefix = ""  # 环境变量不加前缀


# ==================== 主配置类 ====================

class Config:
    """配置管理主类"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._env = EnvSettings()
        self._load_all_configs()

    def _load_json(self, filename: str) -> Dict[str, Any]:
        """加载JSON配置文件"""
        file_path = self.config_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_all_configs(self):
        """加载所有配置"""
        # 加载数据源配置
        sources_data = self._load_json("sources.json")
        self.sources = SourcesConfig(**sources_data)

        # 加载关键词配置
        keywords_data = self._load_json("keywords.json")
        self.keywords = KeywordsConfig(**keywords_data)

        # 加载阈值配置
        thresholds_data = self._load_json("thresholds.json")
        self.thresholds = ThresholdsConfig(**thresholds_data)

        # 加载飞书配置
        feishu_data = self._load_json("feishu.json")
        # 用环境变量覆盖webhook配置
        if "webhook" in feishu_data:
            feishu_data["webhook"]["url"] = self._env.feishu_webhook_url
            feishu_data["webhook"]["secret"] = self._env.feishu_webhook_secret
        self.feishu = FeishuConfig(**feishu_data)

    # ==================== 便捷访问方法 ====================

    @property
    def zhipuai_api_key(self) -> str:
        return self._env.zhipuai_api_key

    @property
    def zhipuai_model(self) -> str:
        return self._env.zhipuai_model

    @property
    def github_token(self) -> str:
        return self._env.github_token

    @property
    def http_proxy(self) -> str:
        return self._env.http_proxy

    @property
    def https_proxy(self) -> str:
        return self._env.https_proxy

    @property
    def log_level(self) -> str:
        return self._env.log_level

    @property
    def timezone(self) -> str:
        return self._env.tz

    def is_test_mode(self) -> bool:
        """是否为测试模式"""
        return self.feishu.testing.mode


# ==================== 单例模式 ====================

_config_instance: Optional[Config] = None


def get_config(config_dir: str = "config") -> Config:
    """获取配置单例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_dir)
    return _config_instance
