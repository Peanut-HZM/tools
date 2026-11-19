"""从 magpie 读取已配置的供应商与订阅账号（只读）

## 为什么需要它

magpie 与本工具解决的是同一件事的两半：

* magpie：**把所有 CLI 接上一个本地网关**，供应商、Key、账号、余额都在它那里配
* 本工具：**展示套餐额度、切换 CLI 配置**

用户已经在 magpie 里配好的供应商（`~/.config/magpie/providers.json`），
不应该在本工具里再手工录一遍。本模块**只读** magpie 的文件与 CLI 输出，
把数据整理成 `subscription_quota_accounts` 能直接落库的结构。

## 数据来源（两个，互相补充）

1. `~/.config/magpie/providers.json` —— 供应商（含 API Key、endpoint、preset）
2. `magpie accounts --json` —— 订阅账号（含额度窗口、重置时间、套餐名）

第 2 项由 magpie 自己向各厂商查询，命中它的缓存时很快；CLI 不存在或
magpie 未安装时**如实返回空**，不编造数据。

## 安全约定

* 只读：从不写 magpie 的任何文件
* 不打印 Key：本模块的日志只记供应商 id 与数量

设计文档：docs/design/agent-subscription-merge.md
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: magpie 供应商 preset/id → 本工具 provider_id
#: 只映射本工具确实有查询器的那些；映射不到的会让用户手工选择类型。
PRESET_ALIASES: dict[str, str] = {
    # 官方订阅
    "anthropic": "claude",
    "openai": "codex",
    "google": "gemini",
    "google-vertex": "gemini",
    # 套餐型
    "kimi": "kimi",
    "kimi-code": "kimi",
    "kimi-code-cn": "kimi",
    "zhipu": "zhipu",
    "zai": "zhipu",
    "minimax": "minimax",
    "minimax-cn": "minimax",
    "opencode-go": "opencode_go",
    "opendesign": "opendesign",
    # 余额型
    "deepseek": "deepseek",
    "siliconflow": "siliconflow",
    "openrouter": "openrouter",
    "stepfun": "stepfun",
    "stepfun-cn": "stepfun",
    "novita": "novita",
    "ollama-cloud": "ollama_cloud",
    "volcengine": "volcengine",
    "zenmux": "zenmux",
    "command-code": "command_code",
}

#: 本工具没有查询器、但 magpie 认识的余额/中转站 → 归到通用余额接口
GENERIC_BALANCE_PRESETS = {
    "anthropic",
    "openai",
    "openrouter",
    "vercel",
    "gmicloud",
    "mistral",
    "groq",
    "bedrock",
    "bedrock-mantle",
    "azure",
    "moonshot",
    "moonshot-cn",
    "qwen",
    "qwen-cn",
    "xai",
    "xiaomi",
    "longcat",
    "baidu-qianfan",
    "tencent-cloud",
    "huaweicloud",
    "nous",
    "apikeyfan",
    "wandapi",
    "corecode",
    "sidrune",
    "fastai",
}


@dataclass
class MagpieProvider:
    """magpie providers.json 里的一条供应商"""

    id: str
    name: str
    preset: str = ""
    key: str = ""
    base_url: str = ""
    website: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def provider_id(self) -> Optional[str]:
        """映射到本工具的 provider_id（映射不到返回 None）"""
        for candidate in (self.preset, self.id):
            if not candidate:
                continue
            key = candidate.strip().lower()
            if key in PRESET_ALIASES:
                return PRESET_ALIASES[key]
            if key in GENERIC_BALANCE_PRESETS:
                return "generic_balance"
        return None

    def masked_key(self) -> str:
        if not self.key:
            return ""
        if len(self.key) <= 12:
            return "***"
        return f"{self.key[:6]}…{self.key[-4:]}"


@dataclass
class MagpieAccount:
    """`magpie accounts --json` 里的一条订阅账号"""

    agent: str
    user: str
    plan: str = ""
    active: bool = False
    windows: list[dict[str, Any]] = field(default_factory=list)
    balance: str = ""
    error: str = ""
    lapsed: str = ""
    alias: str = ""


def real_home() -> Path:
    """真实家目录（config.py 会把 HOME 覆盖成缓存目录）"""
    from app.services.subscription_quota.credentials import real_home as _real_home

    return _real_home()


def magpie_config_dir() -> Path:
    """magpie 配置目录（可用 MAGPIE_CONFIG_DIR 覆盖）"""
    override = os.environ.get("MAGPIE_CONFIG_DIR")
    if override:
        return Path(override)
    return real_home() / ".config" / "magpie"


def providers_json_path() -> Path:
    return magpie_config_dir() / "providers.json"


def _magpie_binary_candidates() -> list[Path]:
    """magpie 可执行文件的候选位置（按命中概率排序）"""
    home = real_home()
    candidates: list[Path] = []

    # 1) 各盘符的标准 Program Files（magpie 允许装到任意盘）
    for env_name in ("PROGRAMFILES", "PROGRAMW6432", "PROGRAMFILES(X86)"):
        root = os.environ.get(env_name)
        if root:
            candidates.append(Path(root) / "magpie" / "magpie.exe")

    for drive in "CDEFGH":
        candidates.append(Path(f"{drive}:/Program Files/magpie/magpie.exe"))
        candidates.append(Path(f"{drive}:/Program Files (x86)/magpie/magpie.exe"))

    # 2) 用户级安装
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "Programs" / "magpie" / "magpie.exe")

    # 3) 便携版（data 目录相邻）
    candidates.append(home / "magpie" / "magpie.exe")

    # 4) macOS / Linux
    candidates += [
        Path("/Applications/Magpie.app/Contents/MacOS/magpie"),
        home / "Applications" / "Magpie.app" / "Contents" / "MacOS" / "magpie",
        Path("/usr/local/bin/magpie"),
        Path("/usr/bin/magpie"),
        home / ".local" / "bin" / "magpie",
    ]
    return candidates


def _running_magpie_path() -> Optional[str]:
    """从运行中的 magpie 进程取可执行文件路径（Windows）

    magpie 允许装到任意盘（本机就装在 ``D:\\Program Files``），
    标准路径扫描会漏掉；运行中的进程一定有真实路径。
    """
    if os.name != "nt":
        return None
    try:
        import subprocess

        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-Process magpie -ErrorAction SilentlyContinue | "
                "Select-Object -First 1 -ExpandProperty Path)",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    path = (proc.stdout or "").strip()
    if path and Path(path).exists():
        return path
    return None


def find_magpie_binary() -> Optional[str]:
    """定位 magpie 可执行文件（PATH → 运行进程 → 常见安装位置）"""
    override = os.environ.get("MAGPIE_BIN")
    if override and Path(override).exists():
        return override

    found = shutil.which("magpie")
    if found:
        return found

    running = _running_magpie_path()
    if running:
        return running

    for path in _magpie_binary_candidates():
        if path.exists():
            return str(path)
    return None


def load_providers() -> list[MagpieProvider]:
    """读取 providers.json（文件不存在时返回空，不编造）"""
    path = providers_json_path()
    if not path.exists():
        logger.info("magpie providers.json 不存在: %s", path)
        return []

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("读取 magpie providers.json 失败: %s", exc, exc_info=True)
        return []

    items = raw.get("providers") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        return []

    out: list[MagpieProvider] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        provider_id = str(item.get("id") or "")
        if not provider_id:
            continue
        base_url = ""
        for field_name in ("chat", "anthropic", "responses", "baseAPI"):
            value = item.get(field_name)
            if isinstance(value, str) and value.startswith("http"):
                base_url = value
                break
        out.append(
            MagpieProvider(
                id=provider_id,
                name=str(item.get("name") or provider_id),
                preset=str(item.get("preset") or ""),
                key=str(item.get("key") or ""),
                base_url=base_url,
                website=str(item.get("website") or ""),
                extra={
                    k: v
                    for k, v in item.items()
                    if k not in ("id", "name", "preset", "key", "website")
                    and isinstance(v, (str, int, float, bool))
                },
            )
        )

    logger.info("从 magpie 读到 %d 个供应商", len(out))
    return out


def load_accounts(timeout: int = 45) -> list[MagpieAccount]:
    """通过 `magpie accounts --json` 读取订阅账号

    magpie 未安装 / CLI 失败时返回空列表并记日志（不静默伪造数据）。
    """
    binary = find_magpie_binary()
    if not binary:
        logger.info("未找到 magpie 可执行文件，跳过订阅账号同步")
        return []

    try:
        proc = subprocess.run(
            [binary, "accounts", "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.error("执行 magpie accounts 失败: %s", exc, exc_info=True)
        return []

    if proc.returncode != 0:
        logger.warning(
            "magpie accounts 退出码 %s: %s",
            proc.returncode,
            (proc.stderr or "").strip()[:300],
        )
        return []

    text = (proc.stdout or "").strip()
    if not text or text == "[]":
        return []

    try:
        rows = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("解析 magpie accounts JSON 失败: %s", exc, exc_info=True)
        return []

    if not isinstance(rows, list):
        return []

    accounts: list[MagpieAccount] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        agent = str(row.get("agent") or "")
        if not agent:
            continue
        windows = row.get("windows")
        accounts.append(
            MagpieAccount(
                agent=agent,
                user=str(row.get("user") or ""),
                plan=str(row.get("plan") or ""),
                active=bool(row.get("active")),
                windows=[w for w in windows if isinstance(w, dict)] if isinstance(windows, list) else [],
                balance=str(row.get("balance") or ""),
                error=str(row.get("error") or ""),
                lapsed=str(row.get("lapsed") or ""),
                alias=str(row.get("alias") or ""),
            )
        )

    logger.info("从 magpie 读到 %d 个订阅账号", len(accounts))
    return accounts


def magpie_available() -> bool:
    """magpie 是否可用于同步（providers.json 或 CLI 任一存在即可）"""
    return providers_json_path().exists() or find_magpie_binary() is not None
