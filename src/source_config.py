#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一信息源配置加载器

支持新的统一配置格式，提供配置验证、环境变量替换等功能。
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CategoryType(Enum):
    """6大分类类型"""
    ACADEMIC = "academic"
    LAB_BLOG = "lab_blog"
    MEDIA = "media"
    TOOLS = "tools"
    COMMUNITY = "community"
    NEWSLETTER = "newsletter"


class CollectorType(Enum):
    """采集器类型"""
    RSS = "rss"
    API = "api"
    SCRAPER = "scraper"
    NEWSLETTER = "newsletter"


class AuthType(Enum):
    """认证类型"""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    BASIC = "basic"


@dataclass
class SourceMetadata:
    """信息源元数据"""
    id: str
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    icon: Optional[str] = None


@dataclass
class SourceCategorization:
    """分类信息"""
    category: CategoryType
    type: CollectorType
    priority: int = 5
    language: str = "en"


@dataclass
class RSSCollectorConfig:
    """RSS采集器配置"""
    rss_url: str
    base_url: Optional[str] = None
    update_frequency: str = "daily"
    item_limit: int = 50


@dataclass
class APICollectorConfig:
    """API采集器配置"""
    base_url: str
    endpoint: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    response_format: str = "json"
    data_path: Optional[str] = None


@dataclass
class ScraperCollectorConfig:
    """爬虫采集器配置"""
    url: str
    base_url: Optional[str] = None
    selectors: Dict[str, str] = field(default_factory=dict)
    render_js: bool = False
    wait_for_selector: Optional[str] = None


@dataclass
class NewsletterCollectorConfig:
    """Newsletter采集器配置"""
    url: str
    archive_url: Optional[str] = None
    extractor: str = "html"
    rss_url: Optional[str] = None


@dataclass
class AuthenticationConfig:
    """认证配置"""
    type: AuthType = AuthType.NONE
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"
    bearer_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class RateLimitConfig:
    """限流配置"""
    requests_per_minute: int = 10
    requests_per_hour: Optional[int] = None
    burst_size: int = 5
    retry_after: int = 60


@dataclass
class FilterConfig:
    """过滤配置"""
    include_keywords: List[str] = field(default_factory=list)
    exclude_keywords: List[str] = field(default_factory=list)
    min_score: Optional[float] = None
    max_age_hours: Optional[int] = None
    domains: List[str] = field(default_factory=list)


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    ttl_minutes: int = 60
    strategy: str = "memory"


@dataclass
class StatusConfig:
    """状态配置"""
    enabled: bool = True
    stable: bool = False
    notes: Optional[str] = None


@dataclass
class MonitoringConfig:
    """监控配置"""
    log_level: str = "INFO"
    alert_on_failure: bool = False
    collect_metrics: bool = True


@dataclass
class SourceConfig:
    """统一的信息源配置"""
    metadata: SourceMetadata
    categorization: SourceCategorization
    collector: Union[RSSCollectorConfig, APICollectorConfig, ScraperCollectorConfig, NewsletterCollectorConfig]
    authentication: AuthenticationConfig = field(default_factory=AuthenticationConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    filters: FilterConfig = field(default_factory=FilterConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    status: StatusConfig = field(default_factory=StatusConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)


class SourceConfigLoader:
    """统一信息源配置加载器"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.schema_path = self.config_dir / "schemas" / "source.schema.json"
        self.template_path = self.config_dir / "sources.template.json"
        self.sources_path = self.config_dir / "sources.json"

    def load_template(self) -> Dict[str, Any]:
        """加载配置模板"""
        if not self.template_path.exists():
            raise FileNotFoundError(f"配置模板不存在: {self.template_path}")

        with open(self.template_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_sources(self) -> List[SourceConfig]:
        """加载所有信息源配置"""
        if not self.sources_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.sources_path}")

        with open(self.sources_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        sources = []
        for source_data in data.get("sources", []):
            try:
                config = self._parse_source_config(source_data)
                sources.append(config)
            except Exception as e:
                logger.error(f"解析信息源配置失败: {source_data.get('metadata', {}).get('id', 'unknown')}: {e}")

        return sources

    def load_source_by_id(self, source_id: str) -> Optional[SourceConfig]:
        """根据ID加载单个信息源配置"""
        sources = self.load_sources()
        for source in sources:
            if source.metadata.id == source_id:
                return source
        return None

    def _parse_source_config(self, data: Dict[str, Any]) -> SourceConfig:
        """解析单个信息源配置"""
        # 替换环境变量
        data = self._substitute_env_vars(data)

        # 解析元数据
        metadata_data = data.get("metadata", {})
        metadata = SourceMetadata(
            id=metadata_data.get("id", ""),
            name=metadata_data.get("name", ""),
            description=metadata_data.get("description"),
            version=metadata_data.get("version", "1.0.0"),
            tags=metadata_data.get("tags", []),
            homepage=metadata_data.get("homepage"),
            icon=metadata_data.get("icon")
        )

        # 解析分类
        categorization_data = data.get("categorization", {})
        categorization = SourceCategorization(
            category=CategoryType(categorization_data.get("category", "media")),
            type=CollectorType(categorization_data.get("type", "rss")),
            priority=categorization_data.get("priority", 5),
            language=categorization_data.get("language", "en")
        )

        # 解析采集器配置
        collector_data = data.get("collector", {})
        collector_type = collector_data.get("type", "rss")

        if collector_type == "rss":
            collector = RSSCollectorConfig(
                rss_url=collector_data.get("rss_url", ""),
                base_url=collector_data.get("base_url"),
                update_frequency=collector_data.get("update_frequency", "daily"),
                item_limit=collector_data.get("item_limit", 50)
            )
        elif collector_type == "api":
            collector = APICollectorConfig(
                base_url=collector_data.get("base_url", ""),
                endpoint=collector_data.get("endpoint", ""),
                method=collector_data.get("method", "GET"),
                headers=collector_data.get("headers", {}),
                params=collector_data.get("params", {}),
                response_format=collector_data.get("response_format", "json"),
                data_path=collector_data.get("data_path")
            )
        elif collector_type == "scraper":
            collector = ScraperCollectorConfig(
                url=collector_data.get("url", ""),
                base_url=collector_data.get("base_url"),
                selectors=collector_data.get("selectors", {}),
                render_js=collector_data.get("render_js", False),
                wait_for_selector=collector_data.get("wait_for_selector")
            )
        elif collector_type == "newsletter":
            collector = NewsletterCollectorConfig(
                url=collector_data.get("url", ""),
                archive_url=collector_data.get("archive_url"),
                extractor=collector_data.get("extractor", "html"),
                rss_url=collector_data.get("rss_url")
            )
        else:
            raise ValueError(f"不支持的采集器类型: {collector_type}")

        # 解析认证配置
        auth_data = data.get("authentication", {})
        authentication = AuthenticationConfig(
            type=AuthType(auth_data.get("type", "none")),
            api_key=auth_data.get("api_key"),
            api_key_header=auth_data.get("api_key_header", "X-API-Key"),
            bearer_token=auth_data.get("bearer_token")
        )

        # 解析限流配置
        rate_limit_data = data.get("rate_limit", {})
        rate_limit = RateLimitConfig(
            requests_per_minute=rate_limit_data.get("requests_per_minute", 10),
            requests_per_hour=rate_limit_data.get("requests_per_hour"),
            burst_size=rate_limit_data.get("burst_size", 5),
            retry_after=rate_limit_data.get("retry_after", 60)
        )

        # 解析过滤配置
        filter_data = data.get("filters", {})
        filters = FilterConfig(
            include_keywords=filter_data.get("include_keywords", []),
            exclude_keywords=filter_data.get("exclude_keywords", []),
            min_score=filter_data.get("min_score"),
            max_age_hours=filter_data.get("time_range", {}).get("max_age_hours") if filter_data.get("time_range") else None,
            domains=filter_data.get("domains", [])
        )

        # 解析缓存配置
        cache_data = data.get("cache", {})
        cache = CacheConfig(
            enabled=cache_data.get("enabled", True),
            ttl_minutes=cache_data.get("ttl_minutes", 60),
            strategy=cache_data.get("strategy", "memory")
        )

        # 解析状态配置
        status_data = data.get("status", {})
        status = StatusConfig(
            enabled=status_data.get("enabled", True),
            stable=status_data.get("stable", False),
            notes=status_data.get("notes")
        )

        # 解析监控配置
        monitoring_data = data.get("monitoring", {})
        monitoring = MonitoringConfig(
            log_level=monitoring_data.get("log_level", "INFO"),
            alert_on_failure=monitoring_data.get("alert_on_failure", False),
            collect_metrics=monitoring_data.get("metrics", {}).get("collect_count", True)
        )

        return SourceConfig(
            metadata=metadata,
            categorization=categorization,
            collector=collector,
            authentication=authentication,
            rate_limit=rate_limit,
            filters=filters,
            cache=cache,
            status=status,
            monitoring=monitoring
        )

    def _substitute_env_vars(self, data: Any) -> Any:
        """递归替换环境变量"""
        if isinstance(data, str):
            # 匹配 ${ENV_VAR} 格式
            pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
            matches = re.findall(pattern, data)

            for var_name in matches:
                env_value = os.environ.get(var_name)
                if env_value is None:
                    logger.warning(f"环境变量 {var_name} 未设置")
                else:
                    data = data.replace(f"${{{var_name}}}", env_value)

            return data
        elif isinstance(data, dict):
            return {k: self._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_vars(item) for item in data]
        else:
            return data

    def validate_config(self, config_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证配置格式"""
        errors = []

        # 检查必需字段
        if "metadata" not in config_data:
            errors.append("缺少 metadata 字段")
        else:
            metadata = config_data["metadata"]
            if "id" not in metadata:
                errors.append("metadata.id 是必需的")
            if "name" not in metadata:
                errors.append("metadata.name 是必需的")

        if "categorization" not in config_data:
            errors.append("缺少 categorization 字段")
        else:
            categorization = config_data["categorization"]
            if "category" not in categorization:
                errors.append("categorization.category 是必需的")
            elif categorization["category"] not in ["academic", "lab_blog", "media", "tools", "community", "newsletter"]:
                errors.append(f"无效的 category: {categorization['category']}")

            if "type" not in categorization:
                errors.append("categorization.type 是必需的")
            elif categorization["type"] not in ["rss", "api", "scraper", "newsletter"]:
                errors.append(f"无效的 type: {categorization['type']}")

        if "collector" not in config_data:
            errors.append("缺少 collector 字段")

        return len(errors) == 0, errors

    def get_enabled_sources(self) -> List[SourceConfig]:
        """获取所有启用的信息源"""
        all_sources = self.load_sources()
        return [s for s in all_sources if s.status.enabled]

    def get_sources_by_category(self, category: CategoryType) -> List[SourceConfig]:
        """按分类获取信息源"""
        all_sources = self.get_enabled_sources()
        return [s for s in all_sources if s.categorization.category == category]

    def get_sources_by_priority(self, min_priority: int = 1, max_priority: int = 10) -> List[SourceConfig]:
        """按优先级获取信息源"""
        all_sources = self.get_enabled_sources()
        return [s for s in all_sources if min_priority <= s.categorization.priority <= max_priority]


# 便捷函数
def load_source_config(config_dir: str = "config") -> SourceConfigLoader:
    """加载配置管理器"""
    return SourceConfigLoader(config_dir)


def get_source_configs(config_dir: str = "config") -> List[SourceConfig]:
    """获取所有信息源配置"""
    loader = load_source_config(config_dir)
    return loader.load_sources()


def get_enabled_source_configs(config_dir: str = "config") -> List[SourceConfig]:
    """获取所有启用的信息源配置"""
    loader = load_source_config(config_dir)
    return loader.get_enabled_sources()
