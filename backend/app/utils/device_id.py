"""设备标识工具 — 生成并持久化稳定的设备 UUID 和硬件指纹"""

import getpass
import hashlib
import logging
import os
import pwd
import socket
import uuid
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# 固定 salt，仅用于防止彩虹表，不用于区分用户
_FINGERPRINT_SALT = "tools-device-fingerprint-v1"


def _get_real_home() -> Path:
    """获取真实用户主目录，不受 config.py 覆盖 HOME 环境变量影响。"""
    uid = os.getuid()
    try:
        return Path(pwd.getpwuid(uid).pw_dir)
    except (KeyError, TypeError):
        return Path(os.environ.get("HOME", "/root"))


def get_device_id() -> str:
    """获取设备唯一标识（UUID），持久化到真实 HOME 目录下。"""
    config_dir = _get_real_home() / ".tools"
    config_dir.mkdir(parents=True, exist_ok=True)
    device_file = config_dir / "device_id"

    if device_file.exists():
        return device_file.read_text().strip()

    device_id = str(uuid.uuid4())
    try:
        device_file.write_text(device_id)
        logger.info(f"已生成并保存设备标识: {device_id} (path={device_file})")
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


def _get_mac_address() -> Optional[str]:
    """获取第一个非虚拟网卡的 MAC 地址"""
    try:
        import psutil
        interfaces = psutil.net_if_addrs()
        for name, addrs in interfaces.items():
            # 跳过常见虚拟/回环接口
            if any(
                name.lower().startswith(prefix)
                for prefix in ("lo", "docker", "br-", "veth", "vmnet", "ppp", "tun", "tap")
            ):
                continue
            for addr in addrs:
                if addr.family == psutil.AF_LINK:
                    mac = addr.address.replace(":", "").replace("-", "").lower()
                    if mac and mac != "000000000000" and mac != "ffffffffffff":
                        return mac
    except Exception as e:
        logger.debug(f"获取 MAC 地址失败: {e}")
    return None


def _build_fingerprint(mac: Optional[str], hostname: str, username: str) -> str:
    """基于 MAC + 主机名 + 用户名 + salt 生成本地指纹"""
    parts = [part for part in (mac, hostname, username, _FINGERPRINT_SALT) if part]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_device_fingerprint() -> Tuple[str, str]:
    """
    获取设备指纹。

    Returns:
        (fingerprint, id_type)
        - fingerprint: 硬件指纹哈希（MAC 不可用时回退为 UUID）
        - id_type: 'hardware'（基于 MAC）或 'uuid'（回退）
    """
    try:
        mac = _get_mac_address()
        hostname = socket.gethostname() or "unknown"
        username = getpass.getuser() or "unknown"

        if mac:
            return _build_fingerprint(mac, hostname, username), "hardware"

        # MAC 不可获取时回退为 UUID
        logger.debug("无法获取 MAC 地址，使用 UUID 作为指纹")
        return get_device_id(), "uuid"
    except Exception as e:
        logger.warning(f"生成设备指纹失败，使用 UUID 回退: {e}")
        return get_device_id(), "uuid"
