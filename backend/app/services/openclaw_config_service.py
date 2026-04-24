"""
OpenClaw 配置管理服务
管理 Gateway 连接配置的持久化和热加载
"""
import json
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from app.config.database import get_db_connection

logger = logging.getLogger(__name__)

DEFAULT_CONFIGS = {
    "gateway_url": "ws://127.0.0.1:18081",
    "token": "",
    "enabled": "true",
}


class OpenClawConfigService:
    """OpenClaw 配置管理服务（单例）"""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS openclaw_configs (
                        id VARCHAR(36) PRIMARY KEY,
                        config_key VARCHAR(50) UNIQUE NOT NULL,
                        config_value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 插入默认配置
                for key, value in DEFAULT_CONFIGS.items():
                    cur.execute(
                        """
                        INSERT INTO openclaw_configs (id, config_key, config_value)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (config_key) DO NOTHING
                        """,
                        (str(uuid.uuid4()), key, value),
                    )
            conn.commit()
            logger.info("OpenClaw configs table initialized")
        except Exception as e:
            logger.error(f"OpenClaw config table initialization failed: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def get_config(self) -> Dict[str, str]:
        """获取所有配置"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT config_key, config_value FROM openclaw_configs")
                rows = cur.fetchall()
                return {row["config_key"]: row["config_value"] for row in rows}
        except Exception as e:
            logger.error(f"Failed to load OpenClaw config: {e}")
            return DEFAULT_CONFIGS.copy()
        finally:
            if conn:
                conn.close()

    def update_config(self, data: Dict[str, str]) -> Dict[str, str]:
        """批量更新配置"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                for key, value in data.items():
                    if key in DEFAULT_CONFIGS:
                        cur.execute(
                            """
                            UPDATE openclaw_configs
                            SET config_value = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE config_key = %s
                            """,
                            (value, key),
                        )
                conn.commit()
            logger.info(f"OpenClaw config updated: {list(data.keys())}")
            return self.get_config()
        except Exception as e:
            logger.error(f"Failed to update OpenClaw config: {e}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def is_enabled(self) -> bool:
        """检查功能是否启用"""
        config = self.get_config()
        return config.get("enabled", "true").lower() == "true"


# 全局单例
openclaw_config_service = OpenClawConfigService()
