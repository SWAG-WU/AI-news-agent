#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
迁移脚本：用新算法重算所有 content_hash

新算法：title|description -> lower().strip() -> 去多余空格 -> SHA256
"""

import hashlib
import sqlite3
from pathlib import Path


def compute_content_hash(title: str, description: str = "") -> str:
    content = f"{title}|{description}".lower().strip()
    content = " ".join(content.split())
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def migrate(db_path: str = "data/history.db"):
    if not Path(db_path).exists():
        print(f"数据库不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id, title, raw_data FROM articles")
    rows = cur.fetchall()
    print(f"共 {len(rows)} 条记录需要迁移")

    updated = 0
    for row_id, title, raw_data in rows:
        # 从 raw_data 提取 description
        description = ""
        if raw_data:
            import json
            try:
                data = json.loads(raw_data)
                description = data.get("description", "")
            except Exception:
                pass

        new_hash = compute_content_hash(title or "", description)
        cur.execute(
            "UPDATE articles SET content_hash = ? WHERE id = ?",
            (new_hash, row_id)
        )
        updated += 1

    conn.commit()
    conn.close()
    print(f"迁移完成，更新了 {updated} 条记录")


if __name__ == "__main__":
    migrate()
