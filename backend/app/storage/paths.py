"""
本地存储路径推导

关键约束：config.py 在非桌面模式下把 HOME 覆盖为 backend/data/cache
（见 app/config/config.py:39），进程内 HOME 是"假家目录"。
本地数据目录必须基于 REAL_HOME 推导（app/config/config.py:21）。
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 本地数据目录名（放在真实家目录下）
LOCAL_DIR_NAME = ".toolbox"
LOCAL_DB_NAME = "toolbox.db"
LOCAL_KEY_NAME = "encryption.key"


def _real_home() -> Path:
    """获取真实家目录。

    必须用 REAL_HOME，不能用 Path.home() / os.path.expanduser("~")，
    因为 config.py 已把 HOME 环境变量覆盖为缓存目录。
    """
    from app.config.config import REAL_HOME

    return Path(REAL_HOME)


def get_local_data_dir() -> Path:
    """获取（并创建）本地数据目录 ~/.toolbox/"""
    data_dir = _real_home() / LOCAL_DIR_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_local_db_path() -> Path:
    """获取本地 SQLite 文件路径 ~/.toolbox/toolbox.db"""
    return get_local_data_dir() / LOCAL_DB_NAME


def get_local_key_path() -> Path:
    """获取本地加密密钥文件路径 ~/.toolbox/encryption.key"""
    return get_local_data_dir() / LOCAL_KEY_NAME
