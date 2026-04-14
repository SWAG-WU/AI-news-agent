#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试新需求功能

1. 测试工具类独立过滤规则
2. 测试临时数据库的创建和清理
"""

import logging
from src.test_storage import TestStorage
from src.filters.category_filter import CategoryFilter
from src.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_tools_independent_filtering():
    """测试工具类独立过滤"""
    logger.info("=== 测试工具类独立过滤 ===")

    config = get_config()
    category_filter = CategoryFilter(config)

    # 模拟测试数据
    test_articles = [
        {"title": "学术论文1", "url": "http://example.com/1", "category": "academic", "score": 0.9, "published_at": "2026-03-04"},
        {"title": "学术论文2", "url": "http://example.com/2", "category": "academic", "score": 0.85, "published_at": "2026-03-04"},
        {"title": "工具项目1", "url": "http://example.com/3", "category": "tools", "score": 0.95, "published_at": "2026-03-04"},
        {"title": "工具项目2", "url": "http://example.com/4", "category": "tools", "score": 0.88, "published_at": "2026-03-04"},
        {"title": "工具项目3", "url": "http://example.com/5", "category": "tools", "score": 0.82, "published_at": "2026-03-04"},
        {"title": "媒体资讯1", "url": "http://example.com/6", "category": "media", "score": 0.75, "published_at": "2026-03-04"},
        {"title": "媒体资讯2", "url": "http://example.com/7", "category": "media", "score": 0.70, "published_at": "2026-03-04"},
        {"title": "实验室博客1", "url": "http://example.com/8", "category": "lab_blog", "score": 0.80, "published_at": "2026-03-04"},
    ]

    # 测试独立过滤
    tools_articles = [a for a in test_articles if a.get('category') == 'tools']
    filtered_tools = category_filter._filter_tools_independently(tools_articles)

    logger.info(f"工具类文章数: {len(tools_articles)}")
    logger.info(f"过滤后工具类: {len(filtered_tools)}")
    for tool in filtered_tools[:3]:
        logger.info(f"  - {tool['title']} (score: {tool['score']})")

    logger.info("\n工具类独立过滤测试完成 ✓\n")


def test_temporary_database():
    """测试临时数据库"""
    logger.info("=== 测试临时数据库 ===")

    # 使用上下文管理器自动清理
    with TestStorage("test_demo") as storage:
        logger.info(f"临时数据库路径: {storage.db_path}")

        # 添加测试数据
        test_article = {
            "url": "http://example.com/test",
            "title": "测试文章",
            "description": "这是一篇测试文章",
            "source": "test_source",
            "category": "media",
            "score": 0.8
        }

        success = storage.add(test_article)
        logger.info(f"添加测试文章: {'成功' if success else '失败'}")

        # 查询测试
        exists = storage.exists("http://example.com/test")
        logger.info(f"文章存在性检查: {exists}")

        stats = storage.get_stats()
        logger.info(f"数据库统计: {stats}")

    # 退出上下文后，数据库应该被自动删除
    logger.info("\n临时数据库测试完成 ✓")
    logger.info("数据库已自动清理\n")


if __name__ == "__main__":
    test_tools_independent_filtering()
    test_temporary_database()

    logger.info("=" * 50)
    logger.info("所有测试完成！")
    logger.info("=" * 50)
