#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import json
from datetime import datetime

# 连接到数据库
conn = sqlite3.connect('data/history.db')
cursor = conn.cursor()

print("=== 数据库表结构 ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for table in tables:
    print(f"表名: {table[0]}")

print("\n=== articles 表结构 ===")
cursor.execute("PRAGMA table_info(articles);")
columns = cursor.fetchall()
for col in columns:
    print(f"列: {col[1]}, 类型: {col[2]}, 是否为空: {col[3]}")

print("\n=== sent_history 表结构 ===")
cursor.execute("PRAGMA table_info(sent_history);")
columns = cursor.fetchall()
for col in columns:
    print(f"列: {col[1]}, 类型: {col[2]}, 是否为空: {col[3]}")

print("\n=== articles 表数据统计 ===")
cursor.execute("SELECT COUNT(*) FROM articles;")
total_articles = cursor.fetchone()[0]
print(f"总文章数: {total_articles}")

cursor.execute("SELECT COUNT(*) FROM articles WHERE is_sent = 1;")
sent_articles = cursor.fetchone()[0]
print(f"已发送文章数: {sent_articles}")

cursor.execute("SELECT COUNT(*) FROM articles WHERE is_sent = 0;")
unsent_articles = cursor.fetchone()[0]
print(f"未发送文章数: {unsent_articles}")

print("\n=== 最近5条记录 ===")
cursor.execute("SELECT id, title, source, is_sent, sent_at, collected_at FROM articles ORDER BY collected_at DESC LIMIT 5;")
recent_articles = cursor.fetchall()
for article in recent_articles:
    print(f"ID: {article[0]}, 标题: {article[1][:50]}..., 来源: {article[2]}, 已发送: {bool(article[3])}, 发送时间: {article[4]}, 收集时间: {article[5]}")

print("\n=== 推送历史统计 ===")
cursor.execute("SELECT COUNT(*) FROM sent_history;")
total_history = cursor.fetchone()[0]
print(f"推送历史记录数: {total_history}")

if total_history > 0:
    cursor.execute("SELECT date, article_count, success, sent_at FROM sent_history ORDER BY sent_at DESC LIMIT 5;")
    history_records = cursor.fetchall()
    for record in history_records:
        print(f"日期: {record[0]}, 推送数量: {record[1]}, 成功: {bool(record[2])}, 推送时间: {record[3]}")

conn.close()