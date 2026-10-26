"""守卫测试：运行时链路不得再依赖 ccusage

背景
    Token 用量采集已全量改为原生读取器（直接读本机 Agent 数据目录），
    不再调用任何外部 CLI。本文件用**静态扫描 + 运行时断言**两条手段，
    防止 ccusage 依赖被后续改动重新引入运行时链路。

例外（允许保留）
    - ``app/utils/ccusage_invoker.py``：仅供开发期对账脚本
      ``scripts/verify_native_readers.py`` 作为独立交叉验证基准使用，
      不允许被任何 ``app/`` 下的运行时模块导入。
    - 各读取器 docstring 中"对齐 ccusage xxx 适配器"的口径说明文字。
"""
import ast
import pathlib

import pytest

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"

# 扫描时跳过的目录（虚拟环境与缓存，体积大且与本项目无关）
SKIP_DIRS = {"venv", ".venv", "__pycache__", ".git", "node_modules", "data", "logs"}

# 允许保留 ccusage 引用的模块（开发期工具 / 口径说明）
ALLOWED_CCUSAGE_MODULES = {
    "app/utils/ccusage_invoker.py",
}

# 允许在文档字符串中出现 "ccusage" 的模块
DOC_ONLY_ALLOWED = {
    "app/utils/agent_readers/claude_reader.py",
    "app/utils/agent_readers/codex_reader.py",
    "app/utils/agent_readers/copilot_reader.py",
    "app/utils/agent_readers/kimi_reader.py",
    "app/utils/agent_readers/minimax_reader.py",
    "app/utils/agent_readers/openclaw_reader.py",
    "app/utils/agent_readers/opencode_reader.py",
    "app/utils/agent_readers/base.py",
    "app/utils/agent_readers/__init__.py",
}


def _module_files() -> list[pathlib.Path]:
    return sorted(APP_ROOT.rglob("*.py"))


def _rel(path: pathlib.Path) -> str:
    return str(path.relative_to(BACKEND_ROOT)).replace("\\", "/")


def _read_source(path: pathlib.Path) -> str:
    """读取源码；个别历史文件可能不是 UTF-8，用 replace 兜底。"""
    return path.read_text(encoding="utf-8", errors="replace")


def _imported_modules(path: pathlib.Path) -> set[str]:
    """解析文件中的 import / from-import，返回被导入的模块名集合。"""
    try:
        tree = ast.parse(_read_source(path))
    except SyntaxError:  # pragma: no cover - 语法错误由其他测试覆盖
        return set()

    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # 相对导入
                continue
            if node.module:
                names.add(node.module)
            for alias in node.names:
                names.add(f"{node.module}.{alias.name}" if node.module else alias.name)
    return names


class TestNoRuntimeCcusageDependency:
    """静态扫描：app/ 下不得有模块导入 ccusage 相关实现"""

    def test_no_app_module_imports_ccusage_invoker(self):
        offenders = []
        for path in _module_files():
            rel = _rel(path)
            if rel in ALLOWED_CCUSAGE_MODULES:
                continue
            for name in _imported_modules(path):
                if "ccusage_invoker" in name or "usage_fetcher" in name:
                    offenders.append(f"{rel} -> {name}")
        assert offenders == [], f"运行时模块仍导入 ccusage: {offenders}"

    def test_no_app_module_imports_removed_fetcher_modules(self):
        """usage_fetcher / usage_fetcher_v2 已删除，任何模块都不应再引用"""
        offenders = []
        for path in _module_files():
            for name in _imported_modules(path):
                if "usage_fetcher" in name:
                    offenders.append(f"{_rel(path)} -> {name}")
        assert offenders == [], f"仍引用已删除的 fetcher 模块: {offenders}"

    def test_sync_service_has_no_ccusage_branches(self):
        """同步服务里不应残留 ccusage 相关函数或分支"""
        from app.services import token_usage_sync_service as svc

        for name in dir(svc):
            assert "ccusage" not in name.lower(), f"同步服务仍暴露 ccusage 符号: {name}"

    def test_routes_have_no_ccusage_cli_fallback(self):
        """路由层不应再有直查 ccusage CLI 的降级路径"""
        from app.routes import token_usage

        assert not hasattr(token_usage, "_fallback_to_cli")
        assert hasattr(token_usage, "_fallback_to_native")

    def test_sync_service_exposes_only_native_entrypoint(self):
        """对外只保留 sync_token_usage 一个同步入口"""
        from app.services import token_usage_sync_service as svc

        assert hasattr(svc, "sync_token_usage")
        assert not hasattr(svc, "sync_token_usage_v2")


class TestCcusageInvokerIsDevOnly:
    """ccusage 调用器必须只被开发期对账脚本使用"""

    def test_only_verify_script_imports_it(self):
        importers: set[str] = set()
        for path in BACKEND_ROOT.rglob("*.py"):
            rel = _rel(path)
            if rel in ALLOWED_CCUSAGE_MODULES:
                continue
            if rel.startswith("tests/"):
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            for name in _imported_modules(path):
                if "ccusage_invoker" in name:
                    importers.add(rel)
        assert importers == {"scripts/verify_native_readers.py"}, (
            f"ccusage_invoker 只允许被开发期对账脚本导入，实际: {sorted(importers)}"
        )

    def test_verify_script_still_works_as_cross_check(self):
        """对账脚本仍能定位 ccusage（作为独立交叉验证基准）"""
        from app.utils.ccusage_invoker import find_ccusage

        # 不要求本机一定装了 ccusage，只要求发现逻辑可调用不抛异常
        assert find_ccusage() is None or isinstance(find_ccusage(), str)


class TestNoCollectionModeSwitch:
    """采集模式开关已随 ccusage 一并移除"""

    def test_mode_config_removed(self):
        from app.config.config import Settings

        assert not hasattr(Settings, "TOKEN_USAGE_NATIVE_READERS_MODE")

    def test_mode_override_helper_removed(self):
        from app.services import token_usage_sync_service as svc

        assert not hasattr(svc, "native_readers_mode_override")
        assert not hasattr(svc, "_native_readers_mode")


@pytest.mark.parametrize(
    "module_path",
    [
        "app.services.token_usage_sync_service",
        "app.routes.token_usage",
        "app.services.token_usage_scheduler",
    ],
)
def test_key_modules_import_cleanly(module_path):
    """改造后的关键模块必须能正常导入（无残留引用）"""
    import importlib

    assert importlib.import_module(module_path) is not None
