"""OpenDesign AMR 控制面 Key 的本地发现（只读，不写任何文件）

## 为什么需要这个模块

OpenDesign 的账单接口

    GET /api/v1/workspaces/{id}/billing/snapshot

**只认 AMR 控制面 Key**（形如 `vela_ctrl_…`）。而推理配置（ZCode / magpie /
OpenCode 的 provider 条目）里存的是**运行时推理 Key**（形如 `sk-amr-ew__…`），
拿它去查账单会被拒绝（实测 401/403）。两者长得完全不同，靠长度或前缀即可区分。

cc-switch 把控制面 Key 存在 `providers.meta.usage_script.apiKey`
（这是它自己的用量脚本配置），本机这个库存在，可以只读复用。

## 安全约定

* **只读**：`sqlite3` 以 `mode=ro` 打开，从不写 cc-switch 的任何文件
* **只认控制面形态**：只有 `vela_ctrl_` 前缀的 Key 才会被返回
* **找不到就返回 None**：不编造、不猜测、不拿推理 Key 凑数
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

#: 控制面 Key 前缀（AMR 控制面 Vela API 的凭证形态）
CONTROL_KEY_PREFIX = "vela_ctrl_"

#: 运行时推理 Key 前缀（账单接口一定拒绝）
RUNTIME_KEY_PREFIX = "sk-amr-ew_"


def is_control_key(key: Optional[str]) -> bool:
    """是否形如控制面 Key（只比前缀，不联网校验）"""
    return bool(key) and str(key).strip().startswith(CONTROL_KEY_PREFIX)


def looks_like_runtime_key(key: Optional[str]) -> bool:
    """是否形如运行时推理 Key（拿它查账单必被拒）"""
    return bool(key) and str(key).strip().startswith(RUNTIME_KEY_PREFIX)


def _ccswitch_db_path() -> Path:
    """cc-switch 数据库位置（复用 usage_import 的 REAL_HOME 解析，支持环境变量覆盖）"""
    from app.services.subscription_quota.usage_import import ccswitch_db_path

    return ccswitch_db_path()


def discover_control_keys(db_path: Optional[Path] = None) -> list[str]:
    """从 cc-switch 库读出所有 OpenDesign 控制面 Key（去重、按出现顺序）

    识别方式（任一满足即视为 OpenDesign 条目）：

    * `meta.usage_script.codingPlanProvider == "opendesign"`
    * 供应商名包含 `opendesign` / `open-design`
    * `settings_config` 里出现 `open-design.ai` 域名

    只返回形如 `vela_ctrl_…` 的 Key；其余（推理 Key、空值）一律丢弃。
    """
    path = db_path or _ccswitch_db_path()
    if not path.exists():
        logger.info("cc-switch 库不存在，跳过控制面 Key 发现: %s", path)
        return []

    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        logger.error("打开 cc-switch 库失败: %s", exc, exc_info=True)
        return []

    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT name, settings_config, meta FROM providers"
        ).fetchall()
    except sqlite3.Error as exc:
        logger.error("读取 cc-switch providers 失败: %s", exc, exc_info=True)
        conn.close()
        return []

    found: list[str] = []
    for row in rows:
        try:
            meta = json.loads(row["meta"] or "{}")
        except (json.JSONDecodeError, TypeError):
            meta = {}
        script = meta.get("usage_script") if isinstance(meta, dict) else None
        if not isinstance(script, dict):
            continue

        name = str(row["name"] or "").lower()
        cfg = str(row["settings_config"] or "").lower()
        provider_kind = str(script.get("codingPlanProvider") or "").lower()

        is_opendesign = (
            provider_kind == "opendesign"
            or "opendesign" in name
            or "open-design" in name
            or "open-design.ai" in cfg
        )
        if not is_opendesign:
            continue

        key = script.get("apiKey")
        if isinstance(key, str) and is_control_key(key):
            key = key.strip()
            if key not in found:
                found.append(key)

    conn.close()
    if found:
        logger.info("在 cc-switch 库里找到 %d 个 OpenDesign 控制面 Key", len(found))
    else:
        logger.info("cc-switch 库里没有 OpenDesign 控制面 Key")
    return found


def pick_control_key(db_path: Optional[Path] = None) -> Optional[str]:
    """取第一个可用的控制面 Key；没有则返回 None"""
    keys = discover_control_keys(db_path)
    return keys[0] if keys else None


def resolve_control_key(
    *candidates: Optional[str],
) -> tuple[Optional[str], str]:
    """从若干候选里挑出真正可用的控制面 Key

    返回 `(key, source)`，`source` 说明来源，便于日志与错误提示：

    * `"explicit"` —— 调用方显式传入的控制面 Key
    * `"cc-switch"` —— 从本机 cc-switch 库发现
    * `""` —— 没找到（此时 key 为 None）

    候选里形如运行时 Key 的会被**明确跳过**，不会误用。
    """
    for key in candidates:
        if is_control_key(key):
            return str(key).strip(), "explicit"

    discovered = pick_control_key()
    if discovered:
        return discovered, "cc-switch"

    return None, ""
