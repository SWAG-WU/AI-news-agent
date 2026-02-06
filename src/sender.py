#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书推送模块

将格式化后的日报推送到飞书群机器人。
"""

import logging
import json
import hashlib
import hmac
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import time

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import Config, get_config

logger = logging.getLogger(__name__)


class FeishuSender:
    """
    飞书机器人推送器

    支持文本和卡片消息推送。
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.webhook_url = self.config.feishu.webhook.url
        self.secret = self.config.feishu.webhook.secret
        self.testing = self.config.feishu.testing.mode
        self.test_output_path = Path(self.config.feishu.testing.test_output_path)

        # 推送限流
        self._last_send_time = 0
        self._rate_limit = self.config.feishu.rate_limit.max_messages_per_minute

    async def send(self, content: str, msg_type: str = "text") -> Dict[str, Any]:
        """
        发送消息到飞书

        Args:
            content: 消息内容
            msg_type: 消息类型 (text, post, interactive)

        Returns:
            发送结果
        """
        if self.testing:
            return await self._send_to_file(content, msg_type)

        return await self._send_to_feishu(content, msg_type)

    async def _send_to_feishu(self, content: str, msg_type: str) -> Dict[str, Any]:
        """发送到飞书"""
        # 检查限流
        await self._check_rate_limit()

        # 构建消息
        message = self._build_message(content, msg_type)

        # 添加签名（如果配置了secret）
        if self.secret:
            message = self._add_signature(message)

        # 发送
        max_retries = self.config.feishu.retry.max_retries

        for attempt in range(max_retries):
            try:
                result = await self._do_send(message)
                logger.info("飞书消息发送成功")
                return {"success": True, "data": result}

            except Exception as e:
                logger.error(f"飞书消息发送失败 (尝试 {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    # 等待后重试
                    wait_time = self.config.feishu.retry.retry_interval_seconds
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    await self._sleep(wait_time)
                else:
                    # 最后一次尝试失败
                    return {"success": False, "error": str(e)}

        return {"success": False, "error": "达到最大重试次数"}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _do_send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """执行HTTP请求"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                return await response.json()

    def _build_message(self, content: str, msg_type: str) -> Dict[str, Any]:
        """构建消息体"""
        if msg_type == "text":
            return {
                "msg_type": "text",
                "content": {
                    "text": content
                }
            }
        elif msg_type == "post":
            return {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": "AI前沿日报",
                            "content": [
                                [
                                    {
                                        "tag": "text",
                                        "text": content
                                    }
                                ]
                            ]
                        }
                    }
                }
            }
        elif msg_type == "interactive":
            # 卡片消息
            if isinstance(content, dict):
                return content
            return {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": "AI前沿日报"
                        },
                        "template": "orange"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": content
                            }
                        }
                    ]
                }
            }
        else:
            raise ValueError(f"不支持的消息类型: {msg_type}")

    def _add_signature(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """添加签名（飞书要求）"""
        timestamp = str(int(time.time()))
        sign = self._generate_sign(timestamp)

        message["timestamp"] = timestamp
        message["sign"] = sign

        return message

    def _generate_sign(self, timestamp: str) -> str:
        """生成签名"""
        string_to_sign = f"{timestamp}\n{self.secret}"

        hmac_obj = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        )

        sign = hmac_obj.digest()
        return sign.hex()

    async def _check_rate_limit(self):
        """检查发送限流"""
        now = time.time()
        time_since_last = now - self._last_send_time

        min_interval = 60 / self._rate_limit

        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            logger.debug(f"限流等待 {wait_time:.2f} 秒")
            await self._sleep(wait_time)

        self._last_send_time = time.time()

    async def _sleep(self, seconds: float):
        """异步等待"""
        import asyncio
        await asyncio.sleep(seconds)

    async def _send_to_file(self, content: str, msg_type: str) -> Dict[str, Any]:
        """发送到文件（测试模式）"""
        self.test_output_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_{timestamp}.md"

        output_path = self.test_output_path.parent / filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"测试模式：内容已写入 {output_path}")

        return {
            "success": True,
            "test_mode": True,
            "output_file": str(output_path)
        }


class BatchFeishuSender(FeishuSender):
    """
    批量飞书推送器

    支持将长消息拆分为多条发送。
    """

    MAX_MESSAGE_LENGTH = 2000  # 飞书消息长度限制

    async def send(self, content: str, msg_type: str = "text") -> Dict[str, Any]:
        """
        发送消息（自动拆分长消息）

        Args:
            content: 消息内容
            msg_type: 消息类型

        Returns:
            发送结果
        """
        # 如果内容不超长，直接发送
        if len(content) <= self.MAX_MESSAGE_LENGTH:
            return await super().send(content, msg_type)

        # 拆分发送
        chunks = self._split_content(content)
        logger.info(f"消息过长 ({len(content)} 字符)，拆分为 {len(chunks)} 条发送")

        results = []
        for i, chunk in enumerate(chunks):
            logger.info(f"发送第 {i + 1}/{len(chunks)} 部分")
            result = await super().send(chunk, msg_type)
            results.append(result)

            # 等待避免限流
            if i < len(chunks) - 1:
                await self._sleep(2)

        # 返回整体结果
        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": success_count == len(results),
            "total": len(results),
            "success_count": success_count,
            "results": results
        }

    def _split_content(self, content: str) -> List[str]:
        """拆分内容"""
        chunks = []

        # 按段落拆分
        paragraphs = content.split("\n\n")
        current_chunk = ""

        for para in paragraphs:
            test_chunk = current_chunk + "\n\n" + para if current_chunk else para

            if len(test_chunk) <= self.MAX_MESSAGE_LENGTH:
                current_chunk = test_chunk
            else:
                # 当前段落加上后会超长
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # 如果单个段落就超长，需要强制拆分
                if len(para) > self.MAX_MESSAGE_LENGTH:
                    sub_chunks = self._force_split(para)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _force_split(self, text: str) -> List[str]:
        """强制拆分过长的文本"""
        chunks = []
        for i in range(0, len(text), self.MAX_MESSAGE_LENGTH):
            chunks.append(text[i:i + self.MAX_MESSAGE_LENGTH])
        return chunks


def create_sender(config: Optional[Config] = None,
                  batch: bool = False) -> FeishuSender:
    """
    创建推送器

    Args:
        config: 配置对象
        batch: 是否使用批量推送器

    Returns:
        推送器实例
    """
    if batch:
        return BatchFeishuSender(config)

    return FeishuSender(config)
