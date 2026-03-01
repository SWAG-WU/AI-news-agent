#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime

print("=== 开始删除2026-02-25之后的记录 ===")

# 连接到数据库
conn = sqlite3.connect('data/history.db')
cursor = conn.cursor()

# 确认删除日期
cutoff_date = '2026-02-25'

# 首先，让我们备份当前的记录数
cursor.execute("SELECT COUNT(*) FROM articles;")
original_count = cursor.fetchone()[0]
print(f"删除前articles表记录总数: {original_count}")

# 开始事务
conn.execute("BEGIN TRANSACTION;")

try:
    # 删除2026-02-25之后的articles记录
    cursor.execute("""
        DELETE FROM articles
        WHERE collected_at > ?
    """, (cutoff_date,))

    deleted_articles = cursor.rowcount
    print(f"已删除 {deleted_articles} 条articles记录")

    # 由于sent_history表中没有2026-02-25之后的记录，无需删除
    print("sent_history表中无需要删除的记录")

    # 提交事务
    conn.commit()
    print("删除成功！事务已提交。")

except Exception as e:
    # 如果发生错误，回滚事务
    conn.rollback()
    print(f"删除过程中发生错误，已回滚: {e}")
    raise

# 检查删除后的记录数
cursor.execute("SELECT COUNT(*) FROM articles;")
new_count = cursor.fetchone()[0]
print(f"删除后articles表记录总数: {new_count}")

print(f"总共删除了 {original_count - new_count} 条记录")

# 验证删除结果
cursor.execute("""
    SELECT COUNT(*)
    FROM articles
    WHERE collected_at > ?
""", (cutoff_date,))
remaining_count = cursor.fetchone()[0]

if remaining_count == 0:
    print("✓ 确认：2026-02-25之后的记录已全部删除")
else:
    print(f"✗ 问题：仍有 {remaining_count} 条记录未删除")

conn.close()
print("\n数据库操作完成。")