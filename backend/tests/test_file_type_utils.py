"""
文件类型工具函数的单元测试

覆盖:
  - get_file_type(name)   根据文件名返回类型分类
  - get_extension(name)   返回小写扩展名（含点号）
  - is_previewable(name)  判断文件是否支持预览
  - FileNode 模型新增字段 (extension, file_type, previewable)
"""
import os
import sys
import pytest

# 支持从 backend/ 目录或 tests/ 目录运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.path_utils import (
    get_file_type,
    get_extension,
    is_previewable,
    FILE_TYPE_MAP,
    PREVIEWABLE_TYPES,
)
from app.models.file_models import FileNode


# ---------------------------------------------------------------------------
# get_file_type
# ---------------------------------------------------------------------------
class TestGetFileType:
    """get_file_type 根据扩展名返回文件类型分类"""

    # --- Markdown ---
    def test_markdown_md(self):
        assert get_file_type("readme.md") == "markdown"

    def test_markdown_markdown(self):
        assert get_file_type("notes.markdown") == "markdown"

    def test_markdown_uppercase(self):
        """大小写不敏感"""
        assert get_file_type("README.MD") == "markdown"

    def test_markdown_mixed_case(self):
        assert get_file_type("Doc.Markdown") == "markdown"

    # --- HTML ---
    def test_html_html(self):
        assert get_file_type("index.html") == "html"

    def test_html_htm(self):
        assert get_file_type("page.htm") == "html"

    def test_html_uppercase(self):
        assert get_file_type("INDEX.HTML") == "html"

    # --- Text ---
    @pytest.mark.parametrize(
        "filename",
        ["data.txt", "app.log", "config.json", "settings.yaml",
         "settings.yml", "feed.xml", "data.csv", "app.ini", "app.cfg", "config.toml"],
    )
    def test_text_types(self, filename):
        assert get_file_type(filename) == "text"

    # --- Image ---
    @pytest.mark.parametrize(
        "filename",
        ["pic.png", "photo.jpg", "photo.jpeg", "anim.gif",
         "logo.svg", "pic.webp", "pic.bmp", "favicon.ico"],
    )
    def test_image_types(self, filename):
        assert get_file_type(filename) == "image"

    # --- Code ---
    @pytest.mark.parametrize(
        "filename",
        ["app.py", "main.js", "app.ts", "comp.tsx", "comp.jsx",
         "Main.java", "main.go", "main.rs", "main.c", "main.cpp",
         "header.h", "style.css", "theme.scss", "run.sh", "query.sql"],
    )
    def test_code_types(self, filename):
        assert get_file_type(filename) == "code"

    # --- Unknown ---
    def test_unknown_extension(self):
        assert get_file_type("data.xyz") == "other"

    def test_no_extension(self):
        assert get_file_type("Makefile") == "other"

    def test_empty_string(self):
        assert get_file_type("") == "other"

    # --- 路径中包含扩展名 ---
    def test_full_path(self):
        """传入完整路径时，应匹配最后一段的扩展名"""
        # get_file_type 以 endswith 匹配，所以路径也能工作
        assert get_file_type("/home/user/notes.md") == "markdown"

    # --- FILE_TYPE_MAP 常量完整性 ---
    def test_file_type_map_has_expected_keys(self):
        expected_keys = {"markdown", "html", "text", "image", "code"}
        assert expected_keys == set(FILE_TYPE_MAP.keys())

    def test_previewable_types_is_set(self):
        assert isinstance(PREVIEWABLE_TYPES, set)
        assert "markdown" in PREVIEWABLE_TYPES
        assert "html" in PREVIEWABLE_TYPES


# ---------------------------------------------------------------------------
# get_extension
# ---------------------------------------------------------------------------
class TestGetExtension:
    """get_extension 返回小写的扩展名（含点号）"""

    def test_simple_extension(self):
        assert get_extension("readme.md") == ".md"

    def test_uppercase_extension(self):
        """返回小写"""
        assert get_extension("README.MD") == ".md"

    def test_mixed_case_extension(self):
        assert get_extension("page.Html") == ".html"

    def test_no_extension(self):
        assert get_extension("Makefile") == ""

    def test_double_extension(self):
        """os.path.splitext 只返回最后一个扩展名"""
        assert get_extension("archive.tar.gz") == ".gz"

    def test_hidden_file(self):
        """以点开头的文件名（如 .gitignore）不算扩展名"""
        # os.path.splitext('.gitignore') -> ('.gitignore', '')
        assert get_extension(".gitignore") == ""

    def test_hidden_file_with_extension(self):
        # os.path.splitext('.config.json') -> ('.config', '.json')
        assert get_extension(".config.json") == ".json"

    def test_empty_string(self):
        assert get_extension("") == ""


# ---------------------------------------------------------------------------
# is_previewable
# ---------------------------------------------------------------------------
class TestIsPreviewable:
    """is_previewable 判断文件是否支持预览（markdown / html）"""

    def test_markdown_is_previewable(self):
        assert is_previewable("readme.md") is True

    def test_markdown_uppercase_is_previewable(self):
        assert is_previewable("README.MD") is True

    def test_html_is_previewable(self):
        assert is_previewable("index.html") is True

    def test_htm_is_previewable(self):
        assert is_previewable("page.htm") is True

    def test_python_not_previewable(self):
        assert is_previewable("main.py") is False

    def test_text_not_previewable(self):
        assert is_previewable("data.txt") is False

    def test_image_not_previewable(self):
        assert is_previewable("pic.png") is False

    def test_unknown_not_previewable(self):
        assert is_previewable("data.xyz") is False

    def test_no_extension_not_previewable(self):
        assert is_previewable("Makefile") is False


# ---------------------------------------------------------------------------
# FileNode 模型扩展
# ---------------------------------------------------------------------------
class TestFileNodeModel:
    """FileNode 模型新增字段测试"""

    def test_file_node_with_new_fields(self):
        """新字段可以正常赋值"""
        node = FileNode(
            name="readme.md",
            path="docs/readme.md",
            type="file",
            extension=".md",
            file_type="markdown",
            previewable=True,
        )
        assert node.extension == ".md"
        assert node.file_type == "markdown"
        assert node.previewable is True

    def test_file_node_without_new_fields(self):
        """新字段是可选的，缺省为 None"""
        node = FileNode(name="test", path="test", type="directory")
        assert node.extension is None
        assert node.file_type is None
        assert node.previewable is None

    def test_file_node_backward_compatible(self):
        """不传新字段时，行为与旧版一致"""
        node = FileNode(
            name="file.txt",
            path="path/file.txt",
            type="file",
            size=1024,
        )
        assert node.name == "file.txt"
        assert node.path == "path/file.txt"
        assert node.type == "file"
        assert node.size == 1024

    def test_file_node_with_children(self):
        """带子节点的目录，新字段为 None"""
        child = FileNode(
            name="child.md",
            path="dir/child.md",
            type="file",
            extension=".md",
            file_type="markdown",
            previewable=True,
        )
        parent = FileNode(
            name="dir",
            path="dir",
            type="directory",
            children=[child],
        )
        assert parent.extension is None
        assert len(parent.children) == 1
        assert parent.children[0].file_type == "markdown"

    def test_file_node_type_validation_still_works(self):
        """type 字段的 pattern 约束仍然有效"""
        with pytest.raises(Exception):  # ValidationError
            FileNode(name="x", path="x", type="invalid_type")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
