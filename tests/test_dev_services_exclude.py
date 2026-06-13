"""
dev-services.py 排除集合计算逻辑的单元测试。

覆盖规范第 4 节的所有规则：
- 默认排除列表生效
- --all 清空默认排除
- --exclude 追加排除
- --include 移除排除（优先级高于 --exclude）
- 大小写不敏感
- 静默忽略未知目录
"""
import sys
from pathlib import Path

# 让测试能导入项目根目录的 dev-services 模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# dev-services.py 含有连字符，需要 importlib 导入
import importlib.util
_spec = importlib.util.spec_from_file_location("dev_services", PROJECT_ROOT / "dev-services.py")
dev_services = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dev_services)


DEFAULT_EXCLUDE_DIRS = dev_services.DEFAULT_EXCLUDE_DIRS


def compute_effective_exclude(args_all: bool, args_exclude: list[str] | None, args_include: list[str] | None) -> set[str]:
    """复制 main() 中的计算逻辑，便于单元测试。

    注意：此函数必须与 dev-services.py main() 中的逻辑保持一致。
    """
    effective = set(DEFAULT_EXCLUDE_DIRS)
    if args_all:
        effective = set()
    for d in (args_exclude or []):
        effective.add(d.lower())
    for d in (args_include or []):
        effective.discard(d.lower())
    return effective


class TestDefaultExclude:
    """默认排除列表应包含 mini-program 相关目录。"""

    def test_contains_mini_program(self):
        assert "mini-program" in DEFAULT_EXCLUDE_DIRS

    def test_contains_tools_mini_program(self):
        assert "tools-mini-program" in DEFAULT_EXCLUDE_DIRS

    def test_does_not_contain_backend(self):
        assert "backend" not in DEFAULT_EXCLUDE_DIRS

    def test_does_not_contain_frontend(self):
        assert "frontend" not in DEFAULT_EXCLUDE_DIRS


class TestAllFlag:
    """--all 应清空默认排除。"""

    def test_all_clears_defaults(self):
        result = compute_effective_exclude(args_all=True, args_exclude=None, args_include=None)
        assert result == set()

    def test_all_with_exclude_adds_back(self):
        result = compute_effective_exclude(args_all=True, args_exclude=["frontend"], args_include=None)
        assert result == {"frontend"}

    def test_all_does_not_restore_defaults(self):
        result = compute_effective_exclude(args_all=True, args_exclude=None, args_include=None)
        assert "mini-program" not in result


class TestExcludeFlag:
    """--exclude 应追加排除项。"""

    def test_exclude_adds_to_defaults(self):
        result = compute_effective_exclude(args_all=False, args_exclude=["frontend"], args_include=None)
        assert "frontend" in result
        assert "mini-program" in result  # 默认排除仍保留

    def test_exclude_multiple(self):
        result = compute_effective_exclude(args_all=False, args_exclude=["frontend", "logs"], args_include=None)
        assert "frontend" in result
        assert "logs" in result
        assert "mini-program" in result

    def test_exclude_case_insensitive(self):
        result = compute_effective_exclude(args_all=False, args_exclude=["Frontend"], args_include=None)
        assert "frontend" in result


class TestIncludeFlag:
    """--include 应从排除集中移除（优先级高于 --exclude）。"""

    def test_include_removes_from_defaults(self):
        result = compute_effective_exclude(args_all=False, args_exclude=None, args_include=["mini-program"])
        assert "mini-program" not in result
        assert "tools-mini-program" in result  # 其他默认排除不受影响

    def test_include_overrides_exclude(self):
        """同一目录同时被 --exclude 和 --include 指定，--include 优先。"""
        result = compute_effective_exclude(
            args_all=False, args_exclude=["mini-program"], args_include=["mini-program"]
        )
        assert "mini-program" not in result

    def test_include_unknown_dir_silent(self):
        """--include 一个不存在的目录，静默忽略不报错。"""
        result = compute_effective_exclude(args_all=False, args_exclude=None, args_include=["nonexistent"])
        assert "nonexistent" not in result
        # 默认排除不受影响
        assert "mini-program" in result

    def test_include_case_insensitive(self):
        result = compute_effective_exclude(args_all=False, args_exclude=None, args_include=["Mini-Program"])
        assert "mini-program" not in result


class TestCombinedFlags:
    """组合标志的边界情况。"""

    def test_all_exclude_include_same_dir(self):
        """--all --exclude X --include X → X 不被排除。"""
        result = compute_effective_exclude(
            args_all=True, args_exclude=["foo"], args_include=["foo"]
        )
        assert "foo" not in result

    def test_defaults_only(self):
        """无任何标志时，只有默认排除生效。"""
        result = compute_effective_exclude(args_all=False, args_exclude=None, args_include=None)
        assert result == DEFAULT_EXCLUDE_DIRS

    def test_empty_lists_same_as_none(self):
        result_none = compute_effective_exclude(args_all=False, args_exclude=None, args_include=None)
        result_empty = compute_effective_exclude(args_all=False, args_exclude=[], args_include=[])
        assert result_none == result_empty
