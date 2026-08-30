"""PluginLoader.scan() 单元测试

参考 docs/superpowers/specs/2026-08-30-agent-harness-phase3-plan2-1b-file-plugin-system-design.md §3.1, §3.3
"""
import logging
import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_registry():
    reg = MagicMock()
    reg.register_dynamic = MagicMock()
    return reg


def test_scan_empty_dir_logs_info_and_returns(mock_registry, tmp_path, caplog):
    """空目录：INFO log + register_dynamic 不被调用"""
    from app.services.harness.plugin_loader import PluginLoader

    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    loader = PluginLoader(mock_registry)
    with caplog.at_level(logging.INFO):
        loader.scan(plugins_dir)

    assert mock_registry.register_dynamic.call_count == 0
    assert any("no plugins" in rec.message.lower() for rec in caplog.records)


def test_scan_nonexistent_dir_warns_and_skips(mock_registry, tmp_path, caplog):
    """不存在目录：WARN log + 不抛异常"""
    from app.services.harness.plugin_loader import PluginLoader

    nonexistent = tmp_path / "does_not_exist"

    loader = PluginLoader(mock_registry)
    with caplog.at_level(logging.WARNING):
        loader.scan(nonexistent)

    assert mock_registry.register_dynamic.call_count == 0
    assert any("not found" in rec.message.lower() for rec in caplog.records)


def test_scan_loads_normal_plugin(mock_registry, tmp_path, caplog):
    """正常插件：1 个 register_dynamic 调用"""
    from app.services.harness.plugin_loader import PluginLoader

    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    (plugins_dir / "hello.py").write_text(
        textwrap.dedent('''
        from app.services.harness.plugin_loader import register_tool

        @register_tool(name="hello", description="hi", parameters={})
        async def hello(arguments, context):
            return {"text": "hi"}
        ''')
    )

    loader = PluginLoader(mock_registry)
    with caplog.at_level(logging.INFO):
        loader.scan(plugins_dir)

    assert mock_registry.register_dynamic.call_count == 1
    assert mock_registry.register_dynamic.call_args[0][0].name == "hello"


def test_scan_syntax_error_isolated(mock_registry, tmp_path, caplog):
    """syntax error 文件被隔离：ERROR log + 其他文件正常加载"""
    from app.services.harness.plugin_loader import PluginLoader

    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    # 第一个文件语法错（缩进坏）
    (plugins_dir / "bad.py").write_text("def broken(:\n    pass\n")
    # 第二个文件正常
    (plugins_dir / "good.py").write_text(
        textwrap.dedent('''
        from app.services.harness.plugin_loader import register_tool

        @register_tool(name="good_tool", description="ok", parameters={})
        async def good_tool(arguments, context):
            return {"text": "ok"}
        ''')
    )

    loader = PluginLoader(mock_registry)
    with caplog.at_level(logging.ERROR):
        loader.scan(plugins_dir)

    # 只有 good 被注册
    assert mock_registry.register_dynamic.call_count == 1
    assert mock_registry.register_dynamic.call_args[0][0].name == "good_tool"
    # bad 文件有 ERROR log
    assert any("bad.py" in rec.message for rec in caplog.records if rec.levelno == logging.ERROR)


def test_scan_value_error_isolated(mock_registry, tmp_path, caplog):
    """装饰器抛 ValueError（缺 name）的文件被隔离"""
    from app.services.harness.plugin_loader import PluginLoader

    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    (plugins_dir / "invalid.py").write_text(
        textwrap.dedent('''
        from app.services.harness.plugin_loader import register_tool

        @register_tool(name="", description="d", parameters={})
        async def invalid(arguments, context):
            return {"text": ""}
        ''')
    )
    (plugins_dir / "ok.py").write_text(
        textwrap.dedent('''
        from app.services.harness.plugin_loader import register_tool

        @register_tool(name="ok_tool", description="ok", parameters={})
        async def ok_tool(arguments, context):
            return {"text": ""}
        ''')
    )

    loader = PluginLoader(mock_registry)
    loader.scan(plugins_dir)

    assert mock_registry.register_dynamic.call_count == 1
    assert mock_registry.register_dynamic.call_args[0][0].name == "ok_tool"


def test_scan_skips_underscore_prefixed_files(mock_registry, tmp_path):
    """_*.py 视为私有文件，跳过"""
    from app.services.harness.plugin_loader import PluginLoader

    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    (plugins_dir / "_internal.py").write_text(
        textwrap.dedent('''
        from app.services.harness.plugin_loader import register_tool

        @register_tool(name="internal", description="d", parameters={})
        async def internal(arguments, context):
            return {"text": "no"}
        ''')
    )

    loader = PluginLoader(mock_registry)
    loader.scan(plugins_dir)

    assert mock_registry.register_dynamic.call_count == 0


def test_scan_skips_pycache(mock_registry, tmp_path):
    """__pycache__/ 目录被跳过"""
    from app.services.harness.plugin_loader import PluginLoader

    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    pycache = plugins_dir / "__pycache__"
    pycache.mkdir()
    (pycache / "cached.py").write_text("# should be skipped")

    loader = PluginLoader(mock_registry)
    loader.scan(plugins_dir)

    assert mock_registry.register_dynamic.call_count == 0


def test_scan_logs_loaded_plugin_names(mock_registry, tmp_path, caplog):
    """每个成功加载的 plugin 有 INFO log"""
    from app.services.harness.plugin_loader import PluginLoader

    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    (plugins_dir / "a.py").write_text(
        textwrap.dedent('''
        from app.services.harness.plugin_loader import register_tool

        @register_tool(name="tool_a", description="d", parameters={})
        async def tool_a(arguments, context):
            return {"text": "a"}
        ''')
    )

    loader = PluginLoader(mock_registry)
    with caplog.at_level(logging.INFO):
        loader.scan(plugins_dir)

    assert any("tool_a" in rec.message for rec in caplog.records)


def test_scan_with_none_registry_does_not_corrupt_singleton(
    mock_registry, tmp_path, monkeypatch
):
    """_registry 为 None 时 scan() 不应把 None 还原回全局单例。

    防御性测试 (对应 PluginLoader 类 docstring 中的 one-shot 注入语义)：

    - 如果调用 ``scan()`` 时 ``tool_registry._registry`` 为 None，说明全局
      单例已被 reset 或从未初始化。
    - 旧实现把 ``original = None`` 记下，在 finally 还原回去，结果是：
      下次 ``get_tool_registry()`` 调用 lazy-init 出一个**全新的、空的**
      ToolRegistry——本次 scan 刚注册的 plugins 被静默丢弃。
    - 修复后：scan() 仅在 original 非 None 时还原；original 为 None 时，
      scan 完成后 ``_registry`` 保留为 ``self.tool_registry``（one-shot
      注入），不再被错误地覆盖为 None。
    """
    from app.services.harness import tool_registry as _tr_module
    from app.services.harness.plugin_loader import PluginLoader

    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    (plugins_dir / "hello.py").write_text(
        textwrap.dedent('''
        from app.services.harness.plugin_loader import register_tool

        @register_tool(name="hello", description="hi", parameters={})
        async def hello(arguments, context):
            return {"text": "hi"}
        ''')
    )

    # 模拟"reset 后未重新初始化"的状态：单例为 None
    monkeypatch.setattr(_tr_module, "_registry", None)

    loader = PluginLoader(mock_registry)
    loader.scan(plugins_dir)

    # 关键断言：scan 完成后 _registry 不应被还原为 None
    # （旧 bug 会让 _registry = None，破坏 one-shot 注入语义）
    assert _tr_module._registry is mock_registry, (
        f"scan() 应保留 self.tool_registry 作为单例（one-shot 注入），"
        f"但 _registry 变成了 {_tr_module._registry!r}（被错误还原为 None）"
    )
    # mock 应当已经收到 1 次 register_dynamic 调用
    assert mock_registry.register_dynamic.call_count == 1
    # 同时验证：没有创建一个新的 ToolRegistry（这是 bug 场景下会发生的事）
    from app.services.harness.tool_registry import ToolRegistry
    assert not isinstance(_tr_module._registry, ToolRegistry) or _tr_module._registry is mock_registry