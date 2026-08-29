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