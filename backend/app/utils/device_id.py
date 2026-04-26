"""设备标识工具 — 生成并持久化稳定的设备 UUID"""

import getpass
import logging
import platform
import socket
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_device_id() -> str:
    """获取设备唯一标识（UUID）"""
    config_dir = Path.home() / ".tools"
    config_dir.mkdir(parents=True, exist_ok=True)
    device_file = config_dir / "device_id"

    if device_file.exists():
        return device_file.read_text().strip()

    device_id = str(uuid.uuid4())
    try:
        device_file.write_text(device_id)
        logger.info(f"已生成并保存设备标识: {device_id}")
    except Exception as e:
        logger.warning(f"设备标识持久化失败，将使用临时 UUID: {e}")

    return device_id


def get_device_display_name() -> str:
    """获取设备显示名称（用户名@主机名）"""
    try:
        username = getpass.getuser() or "unknown"
        hostname = socket.gethostname() or "unknown"
        return f"{username}@{hostname}"
    except Exception:
        return "unknown"
