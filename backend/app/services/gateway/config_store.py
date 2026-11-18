"""网关配置与状态（分组、开关、端口）

配置存 `gateway_config` 表（单行 JSON），避免再加一堆表。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text

from app.models.base import engine

logger = logging.getLogger(__name__)

TABLE = "gateway_config"

_CREATE = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    id            VARCHAR(32) PRIMARY KEY,
    config_json   TEXT NOT NULL,
    updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

_ready = False


def ensure_schema() -> None:
    global _ready
    if _ready:
        return
    try:
        with engine.begin() as conn:
            conn.execute(text(_CREATE))
        _ready = True
    except Exception as exc:
        logger.error("创建 %s 表失败: %s", TABLE, exc, exc_info=True)
        raise


DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "port": 3425,
    "host": "127.0.0.1",
    # 隐私掩码（magpie: Settings → Privacy → Masking，默认关闭）
    "masking": {
        "enabled": False,
        "maskCards": False,
        "maskIds": False,
        "extraWords": [],
    },
    # 路由组：名字 → 成员列表（``provider/model``）
    "groups": {
        "coding": [],
        "fast": [],
        "long-context": [],
    },
    # 意图路由开关
    "intentRouting": False,
    # 失败切换
    "failover": {"enabled": True, "maxRetries": 2},
}


@dataclass
class GatewayConfig:
    data: dict = field(default_factory=lambda: json.loads(json.dumps(DEFAULT_CONFIG)))

    @property
    def enabled(self) -> bool:
        return bool(self.data.get("enabled"))

    @property
    def port(self) -> int:
        return int(self.data.get("port") or 3425)

    @property
    def host(self) -> str:
        return str(self.data.get("host") or "127.0.0.1")

    @property
    def masking(self) -> dict:
        return self.data.get("masking") or DEFAULT_CONFIG["masking"]

    @property
    def groups(self) -> dict[str, list[str]]:
        groups = self.data.get("groups")
        return groups if isinstance(groups, dict) else {}

    @property
    def intent_routing(self) -> bool:
        return bool(self.data.get("intentRouting"))

    @property
    def failover(self) -> dict:
        cfg = self.data.get("failover")
        return cfg if isinstance(cfg, dict) else DEFAULT_CONFIG["failover"]

    def to_dict(self) -> dict:
        return dict(self.data)


def _merge(base: dict, override: dict) -> dict:
    """浅层合并（嵌套 dict 也合并一层）"""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def load_config() -> GatewayConfig:
    ensure_schema()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(f"SELECT config_json FROM {TABLE} WHERE id = 'default'")
            ).fetchone()
    except Exception as exc:
        logger.warning("读取网关配置失败，使用默认值: %s", exc)
        return GatewayConfig()

    if not row:
        return GatewayConfig()
    try:
        stored = json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return GatewayConfig()
    return GatewayConfig(data=_merge(DEFAULT_CONFIG, stored if isinstance(stored, dict) else {}))


def save_config(config: GatewayConfig) -> GatewayConfig:
    ensure_schema()
    payload = json.dumps(config.data, ensure_ascii=False)
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                INSERT INTO {TABLE} (id, config_json, updated_at)
                VALUES ('default', :cfg, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE
                SET config_json = EXCLUDED.config_json, updated_at = CURRENT_TIMESTAMP
                """
            ),
            {"cfg": payload},
        )
    logger.info("网关配置已保存（enabled=%s, port=%s）", config.enabled, config.port)
    return config
