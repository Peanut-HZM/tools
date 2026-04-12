"""
Application Configuration
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file explicitly
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# ------------------------------------------------------------------------------
# Environment Setup for AI Models (PaddleOCR, FunASR)
# ------------------------------------------------------------------------------
# Set cache directories to local project folder to avoid permission issues in sandbox
# and ensure portability.
PROJECT_ROOT = Path(__file__).parent.parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Hack: PaddleOCR/PaddleX often hardcodes ~/.paddleocr or ~/.paddlex
# We redirect HOME to our cache dir to capture these writes.
os.environ["HOME"] = str(CACHE_DIR)

# Set standard cache environment variables
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
    
    # Database
    DATABASE_URL: str
    # Security
    JWT_SECRET_KEY: str = "VPYvNpIeL36rBs1XlICVkPlsNgP+Lp1FQCyp17cCOk4="
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 天
    DB_ENCRYPTION_KEY: str = "VPYvNpIeL36rBs1XlICVkPlsNgP+Lp1FQCyp17cCOk4=" # Default key for dev
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://localhost:5177,http://localhost:5178,http://localhost:5179,http://localhost:5180,http://localhost:5181,http://localhost:5182,http://localhost:5183,http://localhost:5184,http://localhost:5185,http://localhost:5186,http://localhost:5187,http://localhost:5188,http://localhost:5189,http://localhost:5190,http://localhost:3000,https://tools.peanuthzm.com.cn"

    # OpenClaw Gateway
    OPENCLAW_GATEWAY_URL: str = "ws://127.0.0.1:18081"
    OPENCLAW_TOKEN: str = ""

    # Aliyun OSS
    ALIYUN_OSS_ACCESS_KEY_ID: str = "LTAI5t6mbZdwcN8dWgKv3p51"
    ALIYUN_OSS_ACCESS_KEY_SECRET: str = "uSIkuXXyPMgUOtBraMeNE8v4df54kn"
    ALIYUN_OSS_ENDPOINT: str = "oss-cn-beijing.aliyuncs.com"
    ALIYUN_OSS_BUCKET_NAME: str = "oss-peanut"
    ALIYUN_OSS_CALLBACK_URL: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
