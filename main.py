#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI 前沿资讯收集 Agent - 主程序入口

每天早上9点自动采集、筛选、摘要并推送全球AI领域的前沿动态。
"""

import argparse
import asyncio
import logging
from datetime import datetime
from pathlib import Path
import signal
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from src.config import get_config
from src.storage import SQLiteStorage
from src.summarizer import create_summarizer
from src.filters.deduplicator import Deduplicator
from src.filters.keyword_filter import KeywordFilter
from src.filters.threshold_filter import ThresholdFilter
from src.filters.time_filter import TimeFilter
from src.formatter import FeishuFormatter
from src.sender import create_sender

# 配置日志
def setup_logging(log_level: str = "INFO"):
    """配置日志"""
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(logs_dir / "agent.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )


logger = logging.getLogger(__name__)


class AINewsAgent:
    """AI资讯收集Agent主类"""

    def __init__(self, config_dir: str = "config"):
        self.config = get_config(config_dir)
        self.storage = SQLiteStorage("data/history.db")

        # 创建组件
        self.collectors = self._create_collectors()
        self.filters = [
            KeywordFilter(self.config),
            ThresholdFilter(self.config),
        ]
        self.deduplicator = Deduplicator(self.storage, self.config)
        # 时间过滤器（用于确保近期资讯占比 > 80%）
        self.time_filter = TimeFilter(self.config) if self.config.thresholds.time_filter.enabled else None
        # 测试模式使用模拟摘要生成器
        use_mock = self.config.is_test_mode()
        self.summarizer = create_summarizer(self.config, mock=use_mock)
        self.formatter = FeishuFormatter(self.config)
        self.sender = create_sender(self.config)

    def _create_collectors(self):
        """创建数据源采集器"""
        from src.collectors.arxiv_collector import ArxivCollector
        from src.collectors.blog_collector import BlogCollector
        from src.collectors.github_collector import GithubCollector

        return {
            "arxiv": ArxivCollector(self.config),
            "blogs": BlogCollector(self.config),
            "github": GithubCollector(self.config),
        }

    async def run(self):
        """执行Agent主流程"""
        logger.info("=" * 50)
        logger.info("AI资讯收集Agent启动")
        logger.info("=" * 50)

        try:
            # 1. 采集资讯
            raw_news = await self._collect_news()

            # 2. 过滤资讯（关键词和阈值）
            filtered_news = await self._filter_news(raw_news)

            # 3. 去重
            unique_news = await self._deduplicate_news(filtered_news)

            # 4. 应用时间过滤器（确保 10 条输出，80% 近期）
            time_filtered_news = await self._apply_time_filter(unique_news)

            # 5. 生成摘要
            summarized_news = await self._summarize_news(time_filtered_news)

            # 6. 格式化输出
            report = await self._format_report(summarized_news)

            # 7. 推送
            await self._send_report(report)

            # 8. 保存历史
            await self._save_history(summarized_news)

            logger.info("=" * 50)
            logger.info("AI资讯收集Agent执行完成")
            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"Agent执行出错: {e}", exc_info=True)
            raise

    async def _collect_news(self) -> list:
        """从各个数据源采集资讯"""
        logger.info("Step 1: 采集资讯...")
        all_news = []

        for name, collector in self.collectors.items():
            try:
                async with collector:
                    news = await collector.collect()
                    all_news.extend(news)
                    logger.info(f"  {name}: 采集到 {len(news)} 条资讯")
            except Exception as e:
                logger.error(f"  {name}: 采集失败 - {e}")

        logger.info(f"  总计采集到 {len(all_news)} 条资讯")
        return all_news

    async def _filter_news(self, news: list) -> list:
        """根据关键词和阈值过滤资讯"""
        logger.info("Step 2: 过滤资讯...")
        filtered = news

        # 应用基本过滤器
        for filter_obj in self.filters:
            before = len(filtered)
            filtered = filter_obj.filter(filtered)
            after = len(filtered)
            logger.info(f"  {filter_obj.__class__.__name__}: {before} -> {after}")

        return filtered

    async def _apply_time_filter(self, news: list) -> list:
        """应用时间过滤器，确保每日输出满足数量和比例要求"""
        logger.info("Step 2.5: 应用时间过滤器...")

        if not self.time_filter:
            return news

        # 使用新的时间过滤方法，确保输出 10 条（80% 近期，20% 历史）
        filtered = self.time_filter.filter_for_daily_output(news)

        # 输出统计信息
        stats = self.time_filter.get_stats(filtered)
        logger.info(f"  最终输出: {len(filtered)} 条")
        logger.info(f"  时间范围: {stats['cutoff_date'][:10]} 至 {stats['today'][:10]}")
        logger.info(f"  近期比例: {stats['recent_count']}/{stats['total']} ({stats['recent_ratio']:.1%})")

        return filtered

    async def _deduplicate_news(self, news: list) -> list:
        """去重"""
        logger.info("Step 3: 去重...")
        unique = await self.deduplicator.deduplicate(news)
        logger.info(f"  去重后剩余 {len(unique)} 条资讯")
        return unique

    async def _summarize_news(self, news: list) -> list:
        """生成摘要"""
        logger.info("Step 4: 生成摘要...")
        summarized = await self.summarizer.summarize_batch(news)
        logger.info(f"  生成 {len(summarized)} 条摘要")
        return summarized

    async def _format_report(self, news: list) -> str:
        """格式化日报"""
        logger.info("Step 5: 格式化日报...")
        report = await self.formatter.format(news)
        # 显示预览
        preview = report[:200] + "..." if len(report) > 200 else report
        logger.info(f"  日报预览:\n{preview}")
        return report

    async def _send_report(self, report: str):
        """推送日报"""
        logger.info("Step 6: 推送日报...")
        result = await self.sender.send(report)
        if result.get("success"):
            logger.info("  推送成功")
        else:
            logger.error(f"  推送失败: {result.get('error')}")

    async def _save_history(self, news: list):
        """保存到历史记录"""
        logger.info("Step 7: 保存历史记录...")
        count = self.storage.add_batch(news)
        logger.info(f"  保存 {count} 条新记录")

    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.storage.get_stats()


async def run_agent_job():
    """执行Agent任务的作业函数"""
    try:
        # 初始化配置
        config = get_config()
        setup_logging(config.log_level)

        # 创建并运行Agent
        agent = AINewsAgent()
        await agent.run()

        # 输出统计信息
        stats = agent.get_stats()
        logger.info(f"统计信息: {stats}")

    except Exception as e:
        logger.error(f"任务执行出错: {e}", exc_info=True)


async def main(once: bool = False):
    """主函数 - 启动定时调度器或执行单次运行

    Args:
        once: 是否只执行一次（不启动调度器）
    """
    # 初始化配置
    config = get_config()
    setup_logging(config.log_level)

    # 单次运行模式
    if once:
        logger.info("单次运行模式")
        await run_agent_job()
        return

    # 获取时区配置，默认 Asia/Shanghai
    timezone = pytz.timezone(getattr(config, 'timezone', 'Asia/Shanghai'))

    # 创建调度器
    scheduler = AsyncIOScheduler(timezone=timezone)

    # 添加定时任务：每天9点执行
    scheduler.add_job(
        run_agent_job,
        CronTrigger(hour=9, minute=0),
        id='daily_news_collection',
        name='AI资讯每日收集',
        replace_existing=True
    )

    # 启动调度器
    scheduler.start()
    logger.info(f"定时调度器已启动 (时区: {timezone.zone})")
    logger.info("下次执行时间: %s", scheduler.get_job('daily_news_collection').next_run_time)

    # 优雅退出处理
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}，准备退出...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 等待退出信号
    await shutdown_event.wait()

    # 关闭调度器
    scheduler.shutdown()
    logger.info("定时调度器已关闭")


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="AI前沿资讯收集Agent")
    parser.add_argument(
        "--once",
        action="store_true",
        help="执行一次后退出（不启动定时调度器）"
    )
    args = parser.parse_args()

    asyncio.run(main(once=args.once))
