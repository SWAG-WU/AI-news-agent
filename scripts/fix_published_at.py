#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库修复脚本

从 raw_data 中提取 published_at 并更新数据库中的字段。
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from email.utils import parsedate_to_datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from src.storage import Article


def parse_published_at(dt_str: str) -> datetime:
    """解析发布时间"""
    if not dt_str:
        return None

    # 尝试多种格式
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
    )

    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue

    # 尝试使用 email.utils
    try:
        return parsedate_to_datetime(dt_str)
    except Exception:
        pass

    return None


def main():
    """主函数"""
    # 连接数据库
    db_path = Path(__file__).parent.parent / "data" / "history.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    print("=== 数据库修复脚本 ===")
    print(f"数据库路径: {db_path}")
    print()

    # 获取所有 published_at 为空但 raw_data 不为空的记录
    articles = session.query(Article).filter(
        Article.published_at.is_(None),
        Article.raw_data.isnot(None)
    ).all()

    print(f"找到 {len(articles)} 条需要修复的记录")

    success_count = 0
    failed_count = 0
    failed_samples = []

    for article in articles:
        try:
            # 解析 raw_data
            raw_data = json.loads(article.raw_data)
            published_at_str = raw_data.get("published_at")

            if not published_at_str:
                failed_count += 1
                continue

            # 解析时间
            published_at = parse_published_at(published_at_str)

            if published_at:
                # 更新数据库
                article.published_at = published_at
                success_count += 1

                if success_count <= 5:
                    print(f"  [{success_count}] ID={article.id}: {published_at}")
            else:
                failed_count += 1
                if len(failed_samples) < 3:
                    failed_samples.append({
                        "id": article.id,
                        "title": article.title[:50],
                        "raw_published_at": published_at_str
                    })

        except Exception as e:
            failed_count += 1
            print(f"  错误 ID={article.id}: {e}")

    # 提交更改
    try:
        session.commit()
        print()
        print(f"=== 修复完成 ===")
        print(f"成功: {success_count} 条")
        print(f"失败: {failed_count} 条")

        if failed_samples:
            print()
            print("失败样本:")
            for sample in failed_samples:
                print(f"  ID={sample['id']}: {sample['title']}")
                print(f"    原始时间: {sample['raw_published_at']}")

    except Exception as e:
        session.rollback()
        print(f"提交失败: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
