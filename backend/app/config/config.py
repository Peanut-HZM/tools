"""
Application Configuration
"""

from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path
from dotenv import load_dotenv

import sys

# 检测桌面模式（由 desktop_app.py 或 desktop_config.py 设置）
_is_desktop = os.environ.get("DESKTOP_MODE") == "1"

# 保存真实 HOME（ccusage 等 CLI 工具依赖 HOME 读取 ~/.claude 等 agent 数据）
# 必须在覆盖 HOME 之前保存，否则 ccusage 将无法找到数据源
REAL_HOME = os.environ.get("HOME") or Path.home().expanduser()

if _is_desktop:
    # 桌面模式：使用独立配置，不覆盖 HOME
    env_path = Path(os.environ.get("DESKTOP_ENV_PATH", ""))
    if env_path.exists():
        load_dotenv(env_path)
    PROJECT_ROOT = Path(os.environ.get("DESKTOP_PROJECT_ROOT", "."))
    CACHE_DIR = PROJECT_ROOT / "data" / "cache"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # 桌面模式下不覆盖 HOME 环境变量
else:
    # 开发/服务器模式：保持原有行为
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    CACHE_DIR = PROJECT_ROOT / "data" / "cache"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["HOME"] = str(CACHE_DIR)  # 仅在非桌面模式下覆盖

# 设置标准缓存环境变量（两种模式共用）
os.environ["PADDLE_HOME"] = str(CACHE_DIR / "paddle")
os.environ["HF_HOME"] = str(CACHE_DIR / "huggingface")
os.environ["MODELSCOPE_CACHE"] = str(CACHE_DIR / "modelscope")
os.environ["XDG_CACHE_HOME"] = str(CACHE_DIR / "xdg")
# ------------------------------------------------------------------------------


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Tool Aggregation API"
    ENV: str = "dev"
    DEBUG: bool = True
    USERS_DATA_PATH: str = "./data/users"
    BACKEND_PORT: Optional[int] = 19092

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_mode(cls, value):
        """兼容把 DEBUG 写成环境名称的旧环境变量。"""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"dev", "debug", "development"}:
                return True
        return value

    # Database
    DATABASE_URL: str = "sqlite:///./data/tools.db"
    DB_PSYCOPG_POOL_MIN_CONN: int = 5      # 保持最小连接数
    DB_PSYCOPG_POOL_MAX_CONN: int = 50     # 增大最大连接数，避免并发请求时连接池耗尽
    DB_SQLALCHEMY_POOL_SIZE: int = 10      # 从 5 增加到 10
    DB_SQLALCHEMY_MAX_OVERFLOW: int = 10   # 保持不变
    DB_SQLALCHEMY_POOL_TIMEOUT: int = 10   # 保持不变
    DB_HEALTH_CHECK: str = "true"  # 开启连接健康检查：取出连接时 SELECT 1 探活，失效则重取，避免池中失效连接导致间歇性 500（如 "server closed the connection unexpectedly"）
    # Security
    JWT_SECRET_KEY: str = "dev-jwt-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 天
    DB_ENCRYPTION_KEY: str = "dev-db-encryption-change-me"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://localhost:5177,http://localhost:5178,http://localhost:5179,http://localhost:5180,http://localhost:5181,http://localhost:5182,http://localhost:5183,http://localhost:5184,http://localhost:5185,http://localhost:5186,http://localhost:5187,http://localhost:5188,http://localhost:5189,http://localhost:5190,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175,http://127.0.0.1:5176,http://127.0.0.1:5177,http://127.0.0.1:5178,http://127.0.0.1:5179,http://127.0.0.1:5180,http://127.0.0.1:5181,http://127.0.0.1:5182,http://127.0.0.1:5183,http://127.0.0.1:5184,http://127.0.0.1:5185,http://127.0.0.1:5186,http://127.0.0.1:5187,http://127.0.0.1:5188,http://127.0.0.1:5189,http://127.0.0.1:5190,http://localhost:3000,https://tools.peanuthzm.com.cn"

    # OpenClaw Gateway
    OPENCLAW_GATEWAY_URL: str = "ws://127.0.0.1:18081"
    OPENCLAW_TOKEN: str = ""

    # Aliyun OSS
    ALIYUN_OSS_ACCESS_KEY_ID: str = ""
    ALIYUN_OSS_ACCESS_KEY_SECRET: str = ""
    ALIYUN_OSS_ENDPOINT: str = "oss-cn-beijing.aliyuncs.com"
    ALIYUN_OSS_BUCKET_NAME: str = "oss-peanut"
    ALIYUN_OSS_CALLBACK_URL: str = ""

    # Storage Provider Selection
    STORAGE_PROVIDER: str = "aliyun_oss"  # "aliyun_oss" | "minio"

    # Minio 配置
    MINIO_ENDPOINT: str = "minio.peanuthzm.com.cn"
    MINIO_API_ENDPOINT: str = ""  # 内网 API 地址（如 127.0.0.1:9000），为空则使用 MINIO_ENDPOINT
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET_NAME: str = "tools-files"
    MINIO_SECURE: bool = True

    # Redis Cache for Token Usage
    CACHE_REDIS_HOST: str = "localhost"
    CACHE_REDIS_PORT: int = 6379
    CACHE_REDIS_DB: int = 0
    CACHE_REDIS_PASSWORD: str = ""
    CACHE_REDIS_TOKEN_USAGE_TTL: int = 3600  # 1 小时

    # Token Usage 后台定时同步
    TOKEN_USAGE_BACKGROUND_SYNC_ENABLED: bool = True
    TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS: int = 1800
    TOKEN_USAGE_BACKGROUND_SYNC_DAYS: int = 90
    TOKEN_USAGE_BACKGROUND_SYNC_INITIAL_DELAY_SECONDS: int = 60
    TOKEN_USAGE_BACKGROUND_SYNC_MAX_USERS_PER_RUN: int = 3

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
