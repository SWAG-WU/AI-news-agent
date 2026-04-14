#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime

# 连接到数据库
conn = sqlite3.connect('data/history.db')
cursor = conn.cursor()

print("=== 检查2026-02-25之后的记录 ===")

# 查找2026-02-25之后的articles记录
cutoff_date = '2026-02-25'
cursor.execute("""
    SELECT COUNT(*), MIN(collected_at), MAX(collected_at)
    FROM articles
    WHERE collected_at > ?
""", (cutoff_date,))
result = cursor.fetchone()
count, min_date, max_date = result

print(f"2026-02-25之后的articles记录数量: {count}")
print(f"最早日期: {min_date}")
print(f"最晚日期: {max_date}")

if count > 0:
    print("\n前5条2026-02-25之后的记录:")
    cursor.execute("""
        SELECT id, title, source, collected_at, is_sent
        FROM articles
        WHERE collected_at > ?
        ORDER BY collected_at DESC
        LIMIT 5
    """, (cutoff_date,))

    records = cursor.fetchall()
    for record in records:
        print(f"  ID: {record[0]}, 标题: {record[1][:50]}..., 来源: {record[2]}, 时间: {record[3]}, 已发送: {record[4]}")

print("\n=== 检查sent_history表 ===")
cursor.execute("""
    SELECT COUNT(*), MIN(sent_at), MAX(sent_at)
    FROM sent_history
    WHERE sent_at > ?
""", (cutoff_date,))
result = cursor.fetchone()
sh_count, sh_min_date, sh_max_date = result

print(f"2026-02-25之后的sent_history记录数量: {sh_count}")
print(f"最早日期: {sh_min_date}")
print(f"最晚日期: {sh_max_date}")

conn.close()

print(f"\n总结: 将删除 {count} 条articles记录 和 {sh_count} 条sent_history记录")