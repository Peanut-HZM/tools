"""守卫测试：运行时链路与全仓库不得再依赖 ccusage

背景
    Token 用量采集已全量改为原生读取器（直接读本机 Agent 数据目录），
    ccusage CLI 及其调用器已从项目中**彻底移除**。本文件用**静态扫描 +
    运行时断言**两条手段，防止 ccusage 依赖被后续改动重新引入。

移除后的允许范围
    - 各读取器 docstring 中"对齐 ccusage xxx 适配器"的口径说明文字。
      这些文字记录的是**口径来源**（原生实现复刻了 ccusage 的哪套规则），
      属于知识沉淀，不是可执行依赖。
    - 历史上 ccusage 引发的事故记录（CLAUDE.md / AGENTS.md 等文档）。

禁止范围
    - 任何 ``app/`` / ``scripts/`` / ``tests/`` 下的 Python 模块**导入**
      ccusage 相关实现。
    - 任何模块**调用** ccusage CLI（subprocess 方式）。
    - 任何模块在**非 docstring** 的位置出现 ccusage 符号（函数名、变量名、
      字符串常量形式的配置项路径等）。
"""
import ast
import pathlib

import pytest

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"

# 扫描时跳过的目录（虚拟环境与缓存，体积大且与本项目无关）
SKIP_DIRS = {"venv", ".venv", "__pycache__", ".git", "node_modules", "data", "logs"}

# 本文件自身必然包含 ccusage 字面量（守卫逻辑本身），扫描时排除
SELF_PATH = pathlib.Path(__file__).resolve()


def _is_self(path: pathlib.Path) -> bool:
    return path.resolve() == SELF_PATH


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


def _code_level_ccusage_refs(path: pathlib.Path) -> list[str]:
    """用 AST 找出**真正的代码引用**（排除 docstring 与注释）。

    判定口径：只有出现在 Name / Attribute / Import / FunctionDef 名字里的
    ccusage 才算代码依赖；字符串常量（docstring、提示文案）与注释不算。
    """
    try:
        tree = ast.parse(_read_source(path))
    except SyntaxError:  # pragma: no cover
        return []

    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and "ccusage" in node.id.lower():
            hits.append(f"Name:{node.id}@{node.lineno}")
        elif isinstance(node, ast.Attribute) and "ccusage" in node.attr.lower():
            hits.append(f"Attr:{node.attr}@{node.lineno}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if "ccusage" in node.name.lower():
                hits.append(f"Def:{node.name}@{node.lineno}")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, "module", "") or ""
            names = [a.name for a in node.names]
            if "ccusage" in module.lower() or any("ccusage" in n.lower() for n in names):
                hits.append(f"Import:{module or names}@{node.lineno}")
    return hits


class TestCcusageFullyRemoved:
    """ccusage 的可执行实现已彻底移除"""

    def test_invoker_module_deleted(self):
        """ccusage CLI 调用器文件必须不存在"""
        assert not (BACKEND_ROOT / "app/utils/ccusage_invoker.py").exists()

    def test_verify_script_deleted(self):
        """ccusage 对账脚本必须不存在"""
        assert not (BACKEND_ROOT / "scripts/verify_native_readers.py").exists()

    def test_no_module_imports_ccusage(self):
        """任何模块都不得导入 ccusage 相关实现"""
        offenders = []
        for path in BACKEND_ROOT.rglob("*.py"):
            rel = _rel(path)
            if any(part in SKIP_DIRS for part in path.parts) or _is_self(path):
                continue
            for name in _imported_modules(path):
                if "ccusage" in name.lower():
                    offenders.append(f"{rel} -> {name}")
        assert offenders == [], f"仍有模块导入 ccusage: {offenders}"

    def test_no_code_level_ccusage_symbols(self):
        """非 docstring 位置不得出现 ccusage 符号（函数名/变量名/导入）"""
        offenders = []
        for path in BACKEND_ROOT.rglob("*.py"):
            rel = _rel(path)
            if any(part in SKIP_DIRS for part in path.parts) or _is_self(path):
                continue
            for hit in _code_level_ccusage_refs(path):
                offenders.append(f"{rel} -> {hit}")
        assert offenders == [], f"仍有代码级 ccusage 引用: {offenders}"

    def test_no_module_invokes_ccusage_cli(self):
        """不得通过 subprocess 调用 ccusage CLI"""
        offenders = []
        for path in BACKEND_ROOT.rglob("*.py"):
            rel = _rel(path)
            if any(part in SKIP_DIRS for part in path.parts) or _is_self(path):
                continue
            source = _read_source(path)
            # 注释与 docstring 里的说明不算调用
            code_lines = [
                line
                for line in source.splitlines()
                if not line.strip().startswith("#")
            ]
            code = "\n".join(code_lines)
            if '"ccusage"' in code or "'ccusage'" in code:
                offenders.append(rel)
        assert offenders == [], f"仍有模块以字面量引用 ccusage CLI: {offenders}"


class TestNoRuntimeCcusageDependency:
    """同步链路必须保持纯原生"""

    def test_sync_service_has_no_ccusage_symbols(self):
        """同步服务里不应暴露任何 ccusage 符号"""
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

    def test_readers_registry_has_no_ccusage_source(self):
        """原生读取器注册表里不得有 ccusage 这个 source"""
        from app.utils.agent_readers import READERS

        assert not any("ccusage" in s.lower() for s in READERS)


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
