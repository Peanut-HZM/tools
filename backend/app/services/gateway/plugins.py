"""插件（对齐 magpie 的 Gateway middleware）

magpie 用 Bun 跑 JS 插件；本工具用**受控的 Python 中间件**实现同等能力：

* 中间件是一个目录里的 `.py` 文件，暴露一个 ``handle(body, ctx) -> body | None``
* 只能改写请求体 / 拒绝请求，**不能访问网络、不能读文件**（受限 globals）
* 单个中间件抛异常或超时 → 该请求保持原样（对齐 magpie：hook 失败不影响请求）

内置示例中间件：
* ``alias``：把 ``fast`` 之类的短模型名改写成真实模型
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

PLUGIN_DIR = Path(__file__).resolve().parent / "plugins"
DEFAULT_TIMEOUT_SECONDS = 2.0

#: 受限执行环境：禁止 import / open / 网络
_SAFE_BUILTINS = {
    "len": len, "str": str, "int": int, "float": float, "bool": bool,
    "dict": dict, "list": list, "tuple": tuple, "set": set,
    "min": min, "max": max, "abs": abs, "sorted": sorted, "any": any, "all": all,
    "isinstance": isinstance, "range": range, "enumerate": enumerate,
    "None": None, "True": True, "False": False,
}


@dataclass
class Plugin:
    name: str
    path: Path
    enabled: bool = True
    handle: Optional[Any] = None
    error: Optional[str] = None

    def to_public_dict(self) -> dict:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "error": self.error,
        }


@dataclass
class PluginContext:
    """中间件可见的上下文（不含任何凭据）"""

    protocol: str
    provider_id: Optional[str]
    model: Optional[str]
    extra: dict = field(default_factory=dict)


def _load_module(path: Path):
    """以受限名字空间执行插件源码"""
    source = path.read_text(encoding="utf-8")
    namespace: dict[str, Any] = {"__builtins__": _SAFE_BUILTINS}
    exec(compile(source, str(path), "exec"), namespace)  # noqa: S102 - 受限名字空间
    return namespace


def discover_plugins() -> list[Plugin]:
    """列出插件目录里的所有中间件"""
    plugins: list[Plugin] = []
    if not PLUGIN_DIR.is_dir():
        return plugins

    for path in sorted(PLUGIN_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        plugin = Plugin(name=path.stem, path=path)
        try:
            namespace = _load_module(path)
            handle = namespace.get("handle")
            if not callable(handle):
                plugin.error = "缺少 handle(body, ctx) 函数"
                plugin.enabled = False
            else:
                plugin.handle = handle
        except Exception as exc:
            plugin.error = f"{type(exc).__name__}: {exc}"
            plugin.enabled = False
        plugins.append(plugin)
    return plugins


def apply_plugins(
    body: dict,
    ctx: PluginContext,
    plugins: Optional[list[Plugin]] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[dict, list[str]]:
    """依次应用启用的中间件；返回 (改写后的 body, 生效的插件名)"""
    applied: list[str] = []
    current = body

    for plugin in plugins if plugins is not None else discover_plugins():
        if not plugin.enabled or plugin.handle is None:
            continue
        started = time.monotonic()
        try:
            result = plugin.handle(current, ctx)
        except Exception as exc:
            # 单个插件出错不影响请求（对齐 magpie）
            logger.warning("插件 %s 执行失败，请求保持原样: %s", plugin.name, exc)
            continue
        if time.monotonic() - started > timeout:
            logger.warning("插件 %s 超时（>%.1fs），请求保持原样", plugin.name, timeout)
            continue
        if result is None:
            # None 表示「不修改」
            applied.append(plugin.name)
            continue
        if not isinstance(result, dict):
            logger.warning("插件 %s 返回了非 dict，忽略", plugin.name)
            continue
        current = result
        applied.append(plugin.name)

    return current, applied
