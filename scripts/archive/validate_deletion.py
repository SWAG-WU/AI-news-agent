#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3

print("=== 删除后验证 ===")

# 连接到数据库
conn = sqlite3.connect('data/history.db')
cursor = conn.cursor()

# 检查总记录数
cursor.execute("SELECT COUNT(*) FROM articles;")
total_after = cursor.fetchone()[0]
print(f"articles表剩余记录数: {total_after}")

# 检查2026-02-25之后是否还有记录
cursor.execute("SELECT COUNT(*) FROM articles WHERE collected_at > '2026-02-25';")
still_after_cutoff = cursor.fetchone()[0]
print(f"2026-02-25之后仍有记录数: {still_after_cutoff}")

if still_after_cutoff == 0:
    print("确认：2026-02-25之后的记录已全部删除")
else:
    print(f"仍有 {still_after_cutoff} 条记录未删除")

# 显示最新的几条记录
print("\n最新的5条记录:")
cursor.execute("SELECT id, title, collected_at FROM articles ORDER BY collected_at DESC LIMIT 5;")
latest_records = cursor.fetchall()
for record in latest_records:
    print(f"  ID: {record[0]}, 日期: {record[2]}, 标题: {record[1][:50]}...")

# 检查最早的记录
print("\n最旧的5条记录:")
cursor.execute("SELECT id, title, collected_at FROM articles ORDER BY collected_at ASC LIMIT 5;")
oldest_records = cursor.fetchall()
for record in oldest_records:
    print(f"  ID: {record[0]}, 日期: {record[2]}, 标题: {record[1][:50]}...")

conn.close()
print("\n验证完成。")