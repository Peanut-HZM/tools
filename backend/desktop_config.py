"""
桌面模式配置 — 替代 config.py 中的 HOME 覆盖和路径逻辑。
桌面模式下不修改 HOME，使用独立的运行时路径。
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def get_desktop_project_root() -> Path:
    """
    获取桌面模式下的项目根目录。

    PyInstaller 冻结模式:
      - onefile: sys._MEIPASS 是临时解压目录
      - onedir: sys.executable 的父目录包含 _internal/
    开发模式:
      - 返回 backend/ 目录（与 config.py 一致）
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 冻结模式
        if hasattr(sys, '_MEIPASS'):
            # onefile 模式：临时解压目录
            return Path(sys._MEIPASS)
        else:
            # onedir 模式：可执行文件所在目录
            return Path(sys.executable).parent
    else:
        # 开发模式：与 config.py 保持一致
        return Path(__file__).parent


def get_desktop_data_dir() -> Path:
    """获取桌面模式下的数据目录（数据库、日志等）。"""
    root = get_desktop_project_root()
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_desktop_env_path() -> Path:
    """
    获取桌面模式下 .env 文件路径。
    优先级:
    1. 可执行文件同级目录（用户可编辑）
    2. 项目根目录下的 .env（打包内置）
    3. 用户数据目录 (~/.toolbox/.env)
    """
    if getattr(sys, 'frozen', False):
        # 优先查找可执行文件同级目录（用户配置）
        exe_dir = Path(sys.executable).parent
        user_env = exe_dir / ".env"
        if user_env.exists():
            return user_env

        # 其次查找打包内置的 .env
        frozen_env = get_desktop_project_root() / ".env"
        if frozen_env.exists():
            return frozen_env

        # 最后使用用户数据目录
        app_data = Path.home() / ".toolbox"
        app_data.mkdir(parents=True, exist_ok=True)
        return app_data / ".env"
    else:
        # 开发模式：与 config.py 一致
        return Path(__file__).parent.parent / ".env"


def init_desktop_config() -> None:
    """
    初始化桌面模式配置。
    必须在导入 app.config.config 之前调用。

    设置以下环境变量供 config.py 使用:
    - DESKTOP_MODE=1
    - DESKTOP_PROJECT_ROOT
    - DESKTOP_DATA_DIR
    - DESKTOP_ENV_PATH
    """
    os.environ["DESKTOP_MODE"] = "1"

    project_root = get_desktop_project_root()
    os.environ["DESKTOP_PROJECT_ROOT"] = str(project_root)

    data_dir = get_desktop_data_dir()
    os.environ["DESKTOP_DATA_DIR"] = str(data_dir)

    env_path = get_desktop_env_path()
    os.environ["DESKTOP_ENV_PATH"] = str(env_path)

    # 加载 .env
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"桌面模式: 已加载 {env_path}")
    else:
        logger.info(f"桌面模式: .env 不存在 ({env_path})，使用默认配置")

    # 设置 AI 模型缓存目录（不覆盖 HOME）
    cache_dir = data_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["PADDLE_HOME"] = str(cache_dir / "paddle")
    os.environ["HF_HOME"] = str(cache_dir / "huggingface")
    os.environ["MODELSCOPE_CACHE"] = str(cache_dir / "modelscope")
    os.environ["XDG_CACHE_HOME"] = str(cache_dir / "xdg")

    logger.info(f"桌面模式: PROJECT_ROOT={project_root}")
    logger.info(f"桌面模式: DATA_DIR={data_dir}")
