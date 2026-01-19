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

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Tool Aggregation API"
    ENV: str = "dev"
    DEBUG: bool = True
    USERS_DATA_PATH: str = "./data/users"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@39.107.229.30:5432/tools"
    
    # Security
    JWT_SECRET_KEY: str = "VPYvNpIeL36rBs1XlICVkPlsNgP+Lp1FQCyp17cCOk4="
    JWT_EXPIRE_MINUTES: int = 1440
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://localhost:5177,http://localhost:5178,http://localhost:5179,http://localhost:5180,http://localhost:3000,https://tools.peanuthzm.com.cn"
    
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
