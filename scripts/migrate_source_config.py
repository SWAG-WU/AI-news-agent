#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
信息源配置迁移脚本

将旧的配置格式迁移到新的统一配置格式。
"""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict


# 设置控制台输出编码为 UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class SourceConfigMigrator:
    """信息源配置迁移器"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.sources_file = self.config_dir / "sources.json"
        self.backup_file = self.config_dir / f"sources.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def migrate(self) -> bool:
        """执行迁移"""
        print("=" * 60)
        print("信息源配置迁移工具")
        print("=" * 60)
        print()

        # 1. 备份原配置
        print(f"📦 备份原配置到: {self.backup_file.name}")
        shutil.copy2(self.sources_file, self.backup_file)
        print("✅ 备份完成")
        print()

        # 2. 读取原配置
        print(f"📖 读取配置文件: {self.sources_file}")
        with open(self.sources_file, "r", encoding="utf-8") as f:
            old_data = json.load(f)

        old_sources = old_data.get("sources", [])
        fallback_sources = old_data.get("fallback_sources", [])

        print(f"   找到 {len(old_sources)} 个主信息源")
        print(f"   找到 {len(fallback_sources)} 个备用信息源")
        print()

        # 3. 转换配置
        print("🔄 开始转换配置...")
        new_sources = []
        for source in old_sources:
            new_source = self._convert_source(source)
            new_sources.append(new_source)

        # 转换 fallback_sources
        new_fallback = []
        for source in fallback_sources:
            new_source = self._convert_source(source)
            new_fallback.append(new_source)

        print(f"✅ 转换了 {len(new_sources)} 个主信息源")
        print(f"✅ 转换了 {len(new_fallback)} 个备用信息源")
        print()

        # 4. 构建新配置
        new_config = {
            "$schema": "./schemas/source.schema.json",
            "title": "AI资讯信息源配置",
            "description": "统一格式配置 - 由迁移工具自动生成",
            "sources": new_sources,
            "fallback_sources": new_fallback,
            "global_settings": {
                "default_rate_limit": {
                    "requests_per_minute": 10,
                    "burst_size": 5
                },
                "default_cache": {
                    "enabled": True,
                    "ttl_minutes": 60,
                    "strategy": "memory"
                },
                "timeout": {
                    "connect": 10,
                    "read": 30
                }
            },
            "categories": {
                "academic": {"max_items_per_day": 20, "min_score": 0.6},
                "lab_blog": {"max_items_per_day": 15, "min_score": 0.5},
                "media": {"max_items_per_day": 30, "min_score": 0.4},
                "tools": {"max_items_per_day": 25, "min_score": 0.3},
                "community": {"max_items_per_day": 10, "min_score": 0.7},
                "newsletter": {"max_items_per_day": 5, "min_score": 0.5}
            }
        }

        # 5. 写入新配置
        print(f"💾 写入新配置到: {self.sources_file}")
        with open(self.sources_file, "w", encoding="utf-8") as f:
            json.dump(new_config, f, ensure_ascii=False, indent=2)

        print("✅ 迁移完成！")
        print()

        # 6. 显示统计
        self._show_statistics(new_sources + new_fallback)

        print()
        print("📝 注意事项：")
        print("   1. 原配置已备份，如需回滚请使用备份文件")
        print("   2. 请检查新配置是否正确")
        print("   3. 部分信息源可能需要手动调整配置")
        print("   4. 环境变量配置请使用 ${VAR_NAME} 格式")

        return True

    def _convert_source(self, old_source: Dict[str, Any]) -> Dict[str, Any]:
        """转换单个信息源配置"""

        # 提取基本信息
        source_id = old_source.get("id", "")
        source_name = old_source.get("name", "")
        source_type = old_source.get("type", "")
        source_category = old_source.get("category", "media")
        priority = old_source.get("priority", 5)
        enabled = old_source.get("enabled", True)

        # 提取旧的 config 配置
        old_config = old_source.get("config", {})
        old_rate_limit = old_source.get("rate_limit", {})

        # 根据类型确定 collector type
        if source_type == "blog" or source_type == "media" or source_type == "conference":
            if old_config.get("rss_url"):
                collector_type = "rss"
            else:
                collector_type = "scraper"
        elif source_type == "academic":
            if source_id.startswith("arxiv"):
                collector_type = "api"
            elif old_config.get("rss_url"):
                collector_type = "rss"
            else:
                collector_type = "scraper"
        elif source_type == "code":
            collector_type = "scraper"
        else:
            # 默认使用 rss
            collector_type = "rss"

        # 构建新配置
        new_source = {
            "metadata": {
                "id": source_id,
                "name": source_name,
                "description": f"{source_name} - {source_category}",
                "version": "1.0.0",
                "homepage": old_config.get("base_url"),
                "icon": self._get_icon_for_category(source_category),
                "tags": [source_type]
            },
            "categorization": {
                "category": source_category,
                "type": collector_type,
                "priority": priority,
                "language": "en"
            },
            "collector": self._build_collector_config(collector_type, old_config, source_id),
            "authentication": {
                "type": "none"
            },
            "rate_limit": {
                "requests_per_minute": old_rate_limit.get("requests_per_minute", 10)
            },
            "filters": {},
            "cache": {
                "enabled": True,
                "ttl_minutes": 60
            },
            "status": {
                "enabled": enabled,
                "stable": enabled and priority <= 3,
                "notes": "由迁移工具自动转换"
            },
            "monitoring": {
                "log_level": "INFO",
                "alert_on_failure": False
            }
        }

        return new_source

    def _build_collector_config(self, collector_type: str, old_config: Dict[str, Any], source_id: str) -> Dict[str, Any]:
        """构建采集器配置"""

        if collector_type == "rss":
            return {
                "type": "rss",
                "rss_url": old_config.get("rss_url"),
                "base_url": old_config.get("base_url"),
                "update_frequency": "daily",
                "item_limit": old_config.get("max_results", 50)
            }

        elif collector_type == "api":
            # 主要是 arXiv
            return {
                "type": "api",
                "base_url": old_config.get("base_url", "http://export.arxiv.org/api/query"),
                "endpoint": "",
                "method": "GET",
                "params": {
                    "search_query": old_config.get("search_query"),
                    "max_results": old_config.get("max_results", 50),
                    "sortBy": old_config.get("sort_by", "submittedDate"),
                    "sortOrder": old_config.get("sort_order", "descending")
                },
                "response_format": "xml",
                "data_path": "feed.entries"
            }

        elif collector_type == "scraper":
            return {
                "type": "scraper",
                "url": old_config.get("base_url", old_config.get("news_url")),
                "base_url": old_config.get("base_url"),
                "selectors": {
                    "container": ".item, article, .post",
                    "title": ".title, h1, h2, h3",
                    "url": "a[href]",
                    "description": ".description, .excerpt, .summary",
                    "author": ".author, .byline",
                    "published_at": "time, .date, [datetime]"
                },
                "render_js": False
            }

        else:
            return {
                "type": "rss",
                "rss_url": old_config.get("rss_url"),
                "base_url": old_config.get("base_url")
            }

    def _get_icon_for_category(self, category: str) -> str:
        """根据分类获取图标"""
        icons = {
            "academic": "🎓",
            "lab_blog": "🏢",
            "media": "📰",
            "tools": "🛠️",
            "community": "💬",
            "newsletter": "📧"
        }
        return icons.get(category, "📄")

    def _show_statistics(self, sources: list):
        """显示统计信息"""
        print("📊 迁移统计：")
        print()

        # 按分类统计
        category_count = {}
        type_count = {}
        enabled_count = 0

        for source in sources:
            cat = source["categorization"]["category"]
            typ = source["categorization"]["type"]
            status = source["status"]["enabled"]

            category_count[cat] = category_count.get(cat, 0) + 1
            type_count[typ] = type_count.get(typ, 0) + 1
            if status:
                enabled_count += 1

        print("   按分类统计:")
        for cat, count in sorted(category_count.items()):
            print(f"     - {cat}: {count}")

        print()
        print("   按采集方式统计:")
        for typ, count in sorted(type_count.items()):
            print(f"     - {typ}: {count}")

        print()
        print(f"   总计: {len(sources)} 个信息源，{enabled_count} 个已启用")


def main():
    """主函数"""
    migrator = SourceConfigMigrator("config")

    try:
        success = migrator.migrate()
        if success:
            print()
            print("✨ 迁移成功完成！")
            return 0
        else:
            print()
            print("❌ 迁移失败")
            return 1
    except Exception as e:
        print(f"\n❌ 迁移出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
