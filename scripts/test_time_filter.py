#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试时间过滤器功能

验证新的时间过滤器是否符合要求：
1. 每日输出 10 条信息
2. 一年内信息占 80%（可降至 70%）
3. 使用动态系统时间
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from src.storage import Article
from src.config import get_config
from src.filters.time_filter import TimeFilter


def main():
    """主函数"""
    print("=" * 60)
    print("时间过滤器测试 - 新规则")
    print("=" * 60)
    print()

    # 加载配置
    config = get_config()
    print("配置信息:")
    print(f"  - 每日目标数量: {config.thresholds.time_filter.daily_target_count} 条")
    print(f"  - 目标近期比例: {config.thresholds.time_filter.target_recent_ratio:.0%}")
    print(f"  - 最低近期比例: {config.thresholds.time_filter.min_recent_ratio:.0%}")
    print()

    # 创建时间过滤器
    time_filter = TimeFilter(config)

    # 显示动态时间范围
    cutoff_date = time_filter.get_cutoff_date()
    today_end = time_filter.get_today()
    print(f"动态时间范围:")
    print(f"  - 今天: {today_end.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  - 截止日期 (一年前): {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  - 时间跨度: {(today_end - cutoff_date).days} 天")
    print()

    # 连接数据库
    db_path = Path(__file__).parent.parent / "data" / "history.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    # 获取所有有发布时间的文章
    articles = session.query(Article).filter(
        Article.published_at.isnot(None)
    ).all()

    print(f"数据库中共有 {len(articles)} 篇文章（有发布时间）")
    print()

    # 转换为字典格式
    articles_data = []
    for article in articles:
        articles_data.append({
            "url": article.url,
            "title": article.title,
            "published_at": article.published_at,
            "score": article.score or 0,
            "source": article.source,
        })

    # 测试分类功能
    print("-" * 60)
    print("1. 分类测试")
    print("-" * 60)
    classified = time_filter.classify(articles_data)
    recent_count = len(classified[TimeFilter.GROUP_RECENT])
    historical_count = len(classified[TimeFilter.GROUP_HISTORICAL])
    total = len(articles_data)

    print(f"近期资讯: {recent_count} 篇 ({recent_count/total:.2%})")
    print(f"历史资讯: {historical_count} 篇 ({historical_count/total:.2%})")
    print()

    # 测试统计功能
    print("-" * 60)
    print("2. 统计测试")
    print("-" * 60)
    stats = time_filter.get_stats(articles_data)
    print(f"总文章数: {stats['total']}")
    print(f"近期文章数: {stats['recent_count']} ({stats['recent_ratio']:.2%})")
    print(f"历史文章数: {stats['historical_count']} ({stats['historical_ratio']:.2%})")
    print(f"满足目标比例 ({stats['target_ratio']:.0%}): {stats['meets_target_ratio']}")
    print(f"满足最低比例 ({stats['min_ratio']:.0%}): {stats['meets_min_ratio']}")
    print()

    if "by_year" in stats:
        print("按年份统计:")
        for year, count in sorted(stats["by_year"].items()):
            print(f"  {year}: {count} 篇")
        print()

    # 测试每日输出过滤功能
    print("-" * 60)
    print("3. 每日输出过滤测试 (核心功能)")
    print("-" * 60)

    filtered = time_filter.filter_for_daily_output(articles_data)

    print(f"输入: {len(articles_data)} 篇")
    print(f"输出: {len(filtered)} 篇 (目标: {config.thresholds.time_filter.daily_target_count} 篇)")

    # 统计输出结果
    output_recent = sum(1 for a in filtered if a.get('_time_group') == TimeFilter.GROUP_RECENT)
    output_historical = sum(1 for a in filtered if a.get('_time_group') == TimeFilter.GROUP_HISTORICAL)
    output_recent_ratio = output_recent / len(filtered) if filtered else 0

    print(f"近期文章: {output_recent} 篇 ({output_recent_ratio:.1%})")
    print(f"历史文章: {output_historical} 篇 ({1-output_recent_ratio:.1%})")
    print()

    # 验证结果
    print("-" * 60)
    print("4. 结果验证")
    print("-" * 60)

    success = True

    if len(filtered) != config.thresholds.time_filter.daily_target_count:
        print(f"[X] 输出数量不匹配: 期望 {config.thresholds.time_filter.daily_target_count}, 实际 {len(filtered)}")
        success = False
    else:
        print(f"[OK] 输出数量正确: {len(filtered)} 条")

    if output_recent_ratio >= config.thresholds.time_filter.target_recent_ratio:
        print(f"[OK] 达到目标比例: {output_recent_ratio:.1%} >= {config.thresholds.time_filter.target_recent_ratio:.0%}")
    elif output_recent_ratio >= config.thresholds.time_filter.min_recent_ratio:
        print(f"[OK] 达到最低比例: {output_recent_ratio:.1%} >= {config.thresholds.time_filter.min_recent_ratio:.0%}")
    else:
        print(f"[X] 未达到最低比例: {output_recent_ratio:.1%} < {config.thresholds.time_filter.min_recent_ratio:.0%}")
        success = False

    print()
    if success:
        print("[OK] 所有测试通过!")
    else:
        print("[X] 部分测试失败")

    # 显示输出文章列表
    print()
    print("-" * 60)
    print("5. 输出文章列表")
    print("-" * 60)

    for i, article in enumerate(filtered, 1):
        pub_date = article.get("published_at")
        date_str = pub_date.strftime("%Y-%m-%d") if pub_date else "Unknown"
        time_group = "近期" if article.get('_time_group') == TimeFilter.GROUP_RECENT else "历史"
        score = article.get("score", 0)
        print(f"{i}. [{date_str}] [{time_group}] (score:{score}) {article['title'][:50]}...")

    session.close()
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
