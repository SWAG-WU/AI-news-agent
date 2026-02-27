#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据存储模块

使用SQLite存储资讯历史记录，支持去重和查询。
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func

from src.config import get_config

Base = declarative_base()


# ==================== 数据库模型 ====================

class Article(Base):
    """资讯文章模型"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url_hash = Column(String(64), unique=True, index=True, nullable=False)
    url = Column(String(1024), nullable=False)
    title = Column(String(512), nullable=False)
    content_hash = Column(String(64), index=True)
    source = Column(String(100))
    category = Column(String(50))

    # 原始数据
    raw_data = Column(Text)

    # 处理后数据
    summary = Column(Text)
    keywords = Column(Text)  # JSON格式存储关键词列表

    # 元数据
    published_at = Column(DateTime)
    collected_at = Column(DateTime, default=datetime.now)
    sent_at = Column(DateTime)

    # 状态
    is_sent = Column(Boolean, default=False)
    is_skipped = Column(Boolean, default=False)
    skip_reason = Column(String(256))

    # 评分
    score = Column(Integer)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "source": self.source,
            "category": self.category,
            "summary": self.summary,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "is_sent": self.is_sent,
            "score": self.score,
        }


class SentHistory(Base):
    """推送历史模型"""
    __tablename__ = "sent_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(20), unique=True, index=True, nullable=False)  # 格式: YYYY-MM-DD
    article_count = Column(Integer, default=0)
    report_content = Column(Text)
    sent_at = Column(DateTime, default=datetime.now)
    success = Column(Boolean, default=True)
    error_message = Column(Text)


# ==================== 存储类 ====================

class SQLiteStorage:
    """SQLite存储管理类"""

    def __init__(self, db_path: str = "data/history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # SQLAlchemy引擎
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False}
        )
        self.SessionLocal = sessionmaker(bind=self.engine)

        # 创建表
        self._init_tables()

    def _init_tables(self):
        """初始化数据库表"""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    # ==================== 哈希计算 ====================

    @staticmethod
    def compute_url_hash(url: str) -> str:
        """计算URL的SHA256哈希"""
        if url is None:
            url = ""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_content_hash(title: str, description: str = "") -> str:
        """计算内容的SHA256哈希（用于相似内容检测）"""
        # 处理 None 值
        if title is None:
            title = ""
        if description is None:
            description = ""
        content = f"{title}|{description}".lower().strip()
        content = " ".join(content.split())  # 移除多余空格，与 Deduplicator 保持一致
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    # ==================== 添加文章 ====================

    def add(self, article: Dict[str, Any]) -> bool:
        """
        添加一篇文章到数据库

        Args:
            article: 文章数据字典，必须包含 url 和 title

        Returns:
            bool: 是否添加成功（False表示已存在）
        """
        session = self.get_session()
        try:
            url = article.get("url", "")
            url_hash = self.compute_url_hash(url)

            # 检查是否已存在
            existing = session.query(Article).filter_by(url_hash=url_hash).first()
            if existing:
                return False

            # 计算内容哈希
            content_hash = self.compute_content_hash(
                article.get("title", ""),
                article.get("description", "")
            )

            # 创建新记录
            new_article = Article(
                url_hash=url_hash,
                url=url,
                title=article.get("title", "")[:512],
                content_hash=content_hash,
                source=article.get("source", ""),
                category=article.get("category", ""),
                raw_data=json.dumps(article, ensure_ascii=False),
                summary=article.get("summary", ""),
                keywords=json.dumps(article.get("keywords", []), ensure_ascii=False),
                published_at=self._parse_datetime(article.get("published_at")),
                score=article.get("score", 0),
            )

            session.add(new_article)
            session.commit()
            return True

        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    def add_batch(self, articles: List[Dict[str, Any]]) -> int:
        """批量添加文章，返回新增数量"""
        count = 0
        for article in articles:
            if self.add(article):
                count += 1
        return count

    # ==================== 查询文章 ====================

    def exists(self, url: str) -> bool:
        """检查URL是否已存在"""
        session = self.get_session()
        try:
            url_hash = self.compute_url_hash(url)
            return session.query(Article).filter_by(url_hash=url_hash).first() is not None
        finally:
            session.close()

    def exists_by_content(self, title: str, description: str = "") -> bool:
        """通过内容哈希检查是否存在相似内容"""
        session = self.get_session()
        try:
            content_hash = self.compute_content_hash(title, description)
            return session.query(Article).filter_by(content_hash=content_hash).first() is not None
        finally:
            session.close()

    def get_by_url(self, url: str) -> Optional[Article]:
        """通过URL获取文章"""
        session = self.get_session()
        try:
            url_hash = self.compute_url_hash(url)
            return session.query(Article).filter_by(url_hash=url_hash).first()
        finally:
            session.close()

    def get_recent(self, days: int = 7, limit: int = 100) -> List[Article]:
        """获取最近N天的文章"""
        session = self.get_session()
        try:
            since = datetime.now() - timedelta(days=days)
            return session.query(Article).filter(
                Article.collected_at >= since
            ).order_by(Article.collected_at.desc()).limit(limit).all()
        finally:
            session.close()

    def get_unsent(self, limit: int = 50) -> List[Article]:
        """获取未发送的文章"""
        session = self.get_session()
        try:
            return session.query(Article).filter(
                Article.is_sent == False,
                Article.is_skipped == False
            ).order_by(Article.score.desc(), Article.collected_at.desc()).limit(limit).all()
        finally:
            session.close()

    # ==================== 更新文章 ====================

    def mark_sent(self, url: str) -> bool:
        """标记文章已发送"""
        session = self.get_session()
        try:
            url_hash = self.compute_url_hash(url)
            article = session.query(Article).filter_by(url_hash=url_hash).first()
            if article:
                article.is_sent = True
                article.sent_at = datetime.now()
                session.commit()
                return True
            return False
        finally:
            session.close()

    def mark_sent_batch(self, urls: List[str]) -> int:
        """批量标记已发送"""
        count = 0
        for url in urls:
            if self.mark_sent(url):
                count += 1
        return count

    def update_summary(self, url: str, summary: str) -> bool:
        """更新文章摘要"""
        session = self.get_session()
        try:
            url_hash = self.compute_url_hash(url)
            article = session.query(Article).filter_by(url_hash=url_hash).first()
            if article:
                article.summary = summary
                session.commit()
                return True
            return False
        finally:
            session.close()

    def update_score(self, url: str, score: int) -> bool:
        """更新文章评分"""
        session = self.get_session()
        try:
            url_hash = self.compute_url_hash(url)
            article = session.query(Article).filter_by(url_hash=url_hash).first()
            if article:
                article.score = score
                session.commit()
                return True
            return False
        finally:
            session.close()

    # ==================== 推送历史 ====================

    def add_sent_history(self, date: str, article_count: int,
                         report_content: str, success: bool = True,
                         error_message: str = "") -> bool:
        """添加推送历史"""
        session = self.get_session()
        try:
            history = SentHistory(
                date=date,
                article_count=article_count,
                report_content=report_content,
                success=success,
                error_message=error_message
            )
            session.merge(history)  # 使用merge避免重复日期冲突
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    def get_sent_history(self, days: int = 30) -> List[SentHistory]:
        """获取推送历史"""
        session = self.get_session()
        try:
            since = datetime.now() - timedelta(days=days)
            return session.query(SentHistory).filter(
                SentHistory.sent_at >= since
            ).order_by(SentHistory.sent_at.desc()).all()
        finally:
            session.close()

    def is_date_sent(self, date: str) -> bool:
        """检查指定日期是否已推送"""
        session = self.get_session()
        try:
            return session.query(SentHistory).filter_by(date=date).first() is not None
        finally:
            session.close()

    # ==================== 清理 ====================

    def clean_old_records(self, days: int = 30) -> int:
        """清理旧记录（保留已发送但超过N天的记录）"""
        session = self.get_session()
        try:
            cutoff = datetime.now() - timedelta(days=days)
            deleted = session.query(Article).filter(
                Article.is_sent == True,
                Article.sent_at < cutoff
            ).delete()
            session.commit()
            return deleted
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    # ==================== 工具方法 ====================

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """解析日期时间字符串"""
        if not dt_str:
            return None
        try:
            # 尝试多种格式
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d",
                # RFC 2822 format (RSS常用格式)
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S GMT",
            ):
                try:
                    return datetime.strptime(dt_str, fmt)
                except ValueError:
                    continue

            # 尝试使用 email.utils 解析 RFC 2822 格式
            try:
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(dt_str)
            except Exception:
                pass

            return None
        except Exception:
            return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        session = self.get_session()
        try:
            total = session.query(func.count(Article.id)).scalar()
            sent = session.query(func.count(Article.id)).filter(Article.is_sent == True).scalar()
            unsent = session.query(func.count(Article.id)).filter(Article.is_sent == False).scalar()

            # 最近7天统计
            week_ago = datetime.now() - timedelta(days=7)
            recent = session.query(func.count(Article.id)).filter(
                Article.collected_at >= week_ago
            ).scalar()

            return {
                "total_articles": total,
                "sent_articles": sent,
                "unsent_articles": unsent,
                "recent_week_articles": recent,
            }
        finally:
            session.close()


# ==================== 异步存储类（可选） ====================

class AsyncSQLiteStorage:
    """异步SQLite存储类（使用aiosqlite）"""

    def __init__(self, db_path: str = "data/history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """初始化数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url_hash TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content_hash TEXT,
                    source TEXT,
                    category TEXT,
                    raw_data TEXT,
                    summary TEXT,
                    keywords TEXT,
                    published_at TIMESTAMP,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    is_sent BOOLEAN DEFAULT 0,
                    is_skipped BOOLEAN DEFAULT 0,
                    skip_reason TEXT,
                    score INTEGER
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_url_hash ON articles(url_hash)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_hash ON articles(content_hash)
            """)
            await db.commit()

    async def exists(self, url: str) -> bool:
        """检查URL是否已存在"""
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM articles WHERE url_hash = ? LIMIT 1",
                (url_hash,)
            )
            return await cursor.fetchone() is not None

    async def add(self, article: Dict[str, Any]) -> bool:
        """添加文章"""
        url = article.get("url", "")
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()

        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO articles (
                        url_hash, url, title, source, category,
                        raw_data, summary, published_at, score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    url_hash,
                    url,
                    article.get("title", ""),
                    article.get("source", ""),
                    article.get("category", ""),
                    json.dumps(article, ensure_ascii=False),
                    article.get("summary", ""),
                    article.get("published_at"),
                    article.get("score", 0)
                ))
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                # URL已存在
                return False
