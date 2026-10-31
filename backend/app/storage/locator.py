"""
存储位置枚举与仓库路由

注意：本地凭据库（~/.toolbox/toolbox.db）与主应用库（settings.DATABASE_URL）
是两个不同的库。远程服务器存储指主应用库 —— 当 DATABASE_URL 指向 PG 且可达时，
配置可存主应用库；不可达或为 sqlite 时，只能存本地专用库。
"""
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class StorageLocation(str, Enum):
    """配置存储位置"""

    LOCAL = "local"    # 本机 SQLite（~/.toolbox/toolbox.db）
    SERVER = "server"  # 服务器 PostgreSQL（主应用库）

    @classmethod
    def from_value(cls, value) -> "StorageLocation":
        """从字符串解析存储位置；非法值抛异常（不做静默兜底）"""
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"未知存储位置：{value}")


def server_available() -> tuple[bool, str]:
    """判定远程服务器是否可用。

    Returns:
        (是否可用, 原因说明)。不可用时原因非空，可直接展示给用户。
    """
    from app.config.config import settings

    url = (settings.DATABASE_URL or "").strip()

    if not url:
        return False, "未配置数据库地址（DATABASE_URL 为空），无法使用服务器存储"

    if url.startswith("sqlite://"):
        return False, "当前为 SQLite 部署模式（无远程服务器），凭据将仅保存在本机"

    if not url.startswith("postgresql://"):
        return False, f"不支持的数据库类型：{url.split('://')[0]}"

    try:
        from app.config.database import get_pooled_db_connection, release_db_connection

        conn = get_pooled_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        finally:
            release_db_connection(conn)
    except Exception as exc:
        logger.warning("远程服务器不可达：%s", exc)
        return False, f"远程服务器不可达：{exc}"

    return True, ""


def get_repository(location: StorageLocation, tool: str):
    """按存储位置返回对应仓库实现。

    Args:
        location: 存储位置
        tool: 工具标识（'database' / 'k8s' / 'ssh' / 'redis'）
    """
    from app.storage.repository import get_repository as _get_repository

    return _get_repository(location, tool)


def get_local_repo(tool: str):
    """获取本地仓库"""
    return get_repository(StorageLocation.LOCAL, tool)


def get_remote_repo(tool: str):
    """获取远程仓库"""
    return get_repository(StorageLocation.SERVER, tool)
