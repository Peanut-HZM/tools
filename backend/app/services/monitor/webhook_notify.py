"""
Webhook 推送 - 兼容钉钉/企业微信/飞书机器人 markdown 格式
"""
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


def send_webhook(url: str, title: str, content: str) -> bool:
    """推送告警到 Webhook，成功返回 True"""
    if not url:
        return False
    payload = {
        "msgtype": "markdown",
        "markdown": {"title": title, "content": content},
    }
    try:
        resp = httpx.post(url, json=payload, timeout=10)
        if resp.status_code < 400:
            return True
        logger.warning("Webhook 推送返回非成功状态: %s", resp.status_code)
        return False
    except Exception as e:
        logger.warning("Webhook 推送失败: %s", str(e))
        return False
