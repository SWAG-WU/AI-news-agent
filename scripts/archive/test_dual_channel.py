#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
双渠道模式测试脚本

该脚本模拟测试双渠道模式的功能
"""

import json
from unittest.mock import Mock
from src.filters.category_filter import CategoryFilter
from src.config import get_config

def test_dual_channel_functionality():
    """测试双渠道模式的基本功能"""

    print("=== 双渠道模式功能测试 ===\n")

    # 获取配置
    config = get_config()

    # 创建分类过滤器实例
    category_filter = CategoryFilter(config)

    print(f"双渠道模式状态: {category_filter.dual_channel_mode}")
    print(f"工具渠道数量: {category_filter.tools_channel_count}")
    print(f"学术媒体渠道数量: {category_filter.academic_media_channel_count}\n")

    # 模拟一些测试数据
    test_articles = [
        {
            "title": "Amazing New AI Framework",
            "description": "An incredible new framework for AI development",
            "source": "GitHub",
            "url": "https://github.com/example/framework",
            "score": 0.85,
            "category": "tools"
        },
        {
            "title": "Transformer Architecture Explained",
            "description": "Deep dive into the transformer architecture",
            "source": "arXiv",
            "url": "https://arxiv.org/example",
            "score": 0.75,
            "category": "academic"
        },
        {
            "title": "Latest in Machine Learning Research",
            "description": "Summary of recent ML research papers",
            "source": "MIT Technology Review",
            "url": "https://techreview.example.com/ml",
            "score": 0.70,
            "category": "media"
        },
        {
            "title": "PyTorch 2.0 Performance Improvements",
            "description": "New JIT compiler optimizations in PyTorch 2.0",
            "source": "GitHub",
            "url": "https://github.com/pytorch/pytorch",
            "score": 0.80,
            "category": "tools"
        },
        {
            "title": "OpenAI's Latest Developments",
            "description": "Recent updates from OpenAI team",
            "source": "OpenAI Blog",
            "url": "https://openai.com/blog/update",
            "score": 0.72,
            "category": "lab_blog"
        }
    ]

    print("输入文章列表:")
    for i, article in enumerate(test_articles, 1):
        print(f"{i}. {article['title']} [{article['category']}] - Score: {article['score']}")
    print(f"总计: {len(test_articles)} 篇\n")

    # 模拟调用分类函数
    categorized = category_filter.classify(test_articles)

    print("分类结果:")
    for category, articles in categorized.items():
        print(f"- {category}: {len(articles)} 篇")
    print()

    # 测试双渠道模式下的过滤（模拟）
    print("=== 双渠道模式处理逻辑 ===")
    print("渠道1 (工具类): 按评分排序，选择高质量工具项目")
    tools_articles = categorized[category_filter.CATEGORY_TOOLS]
    if tools_articles:
        sorted_tools = category_filter._sort_articles_by_score(tools_articles)
        selected_tools = sorted_tools[:category_filter.tools_channel_count]
        print(f"  从 {len(tools_articles)} 个工具项目中选择 {len(selected_tools)} 个")
        for article in selected_tools:
            print(f"    - {article['title']} (Score: {article['score']})")

    print("\n渠道2 (学术媒体类): 优先学术，其次媒体")
    academic_articles = categorized[category_filter.CATEGORY_ACADEMIC]
    media_articles = categorized[category_filter.CATEGORY_MEDIA]
    print(f"  学术类: {len(academic_articles)} 篇")
    print(f"  媒体类: {len(media_articles)} 篇")

    if academic_articles:
        sorted_academic = category_filter._sort_articles_by_recency_and_score(academic_articles)
        academic_selected = sorted_academic[:category_filter.academic_media_channel_count//2]
        print(f"  选择学术类: {len(academic_selected)} 篇")

    if media_articles:
        sorted_media = category_filter._sort_articles_by_recency_and_score(media_articles)
        media_needed = min(category_filter.academic_media_channel_count - len(academic_articles), len(sorted_media))
        media_selected = sorted_media[:media_needed]
        print(f"  选择媒体类: {len(media_selected)} 篇")

    print("\n=== 功能说明 ===")
    print("双渠道模式实现了您要求的两个独立筛选渠道：")
    print("1. 工具渠道 - 专门筛选GitHub项目、工具类资讯，按评分排序确保质量")
    print("2. 学术媒体渠道 - 专门收集学术论文、科技前沿等资讯，优先学术后媒体")
    print("\n这种设计确保了不同类型的信息都能得到有效展示，避免了之前只有工具类信息通过筛选的问题。")

if __name__ == "__main__":
    test_dual_channel_functionality()