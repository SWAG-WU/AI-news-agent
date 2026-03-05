#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试数据库管理模块

提供临时测试数据库的创建和清理功能
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.storage import SQLiteStorage

logger = logging.getLogger(__name__)


class TestStorage(SQLiteStorage):
    """测试存储类 - 使用临时数据库"""

    def __init__(self, test_name: Optional[str] = None):
        """
        初始化测试存储

        Args:
            test_name: 测试名称，用于生成唯一的数据库文件名
        """
        # 生成测试数据库路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_name = test_name or "test"
        db_filename = f"test_{timestamp}.db"
        db_path = Path("data") / db_filename

        # 调用父类初始化
        super().__init__(str(db_path))

        self.is_test_db = True
        logger.info(f"创建测试数据库: {db_path}")

    def cleanup(self):
        """清理测试数据库"""
        try:
            # 关闭数据库连接
            if hasattr(self, 'engine'):
                self.engine.dispose()

            db_file = Path(self.db_path)
            if db_file.exists():
                db_file.unlink()
                logger.info(f"已删除测试数据库: {db_file}")
        except Exception as e:
            logger.error(f"删除测试数据库失败: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出 - 自动清理"""
        self.cleanup()
