"""
markdown_file_service 扩展功能单元测试

覆盖 Task 2 的改动：
  - _scan_directory()  返回所有文件类型（不再仅 .md）
  - list_directory()   目录浏览方法
  - _build_breadcrumbs()  面包屑导航
  - get_file_paths()   获取文件路径
  - read_file_raw()    统一文件读取（文本 + 二进制）
"""
import os
import sys
import tempfile
import shutil
import pytest

# 支持从 backend/ 目录或 tests/ 目录运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.markdown_file_service import MarkdownFileService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def temp_dir():
    """创建临时目录用于测试"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def file_service(temp_dir):
    """创建 MarkdownFileService 实例，root 指向 temp_dir"""
    from pathlib import Path
    user_id = "test-user-task2"
    service = MarkdownFileService(user_id)
    # 与生产代码一致：_root_path 始终是已 resolve 的 Path 对象
    service._root_path = Path(temp_dir).resolve()
    return service


def _touch(path: str, content: str = "content"):
    """快速创建文件并写入内容"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# _scan_directory：返回所有文件类型
# ---------------------------------------------------------------------------
class TestScanDirectoryAllFiles:
    """_scan_directory 应该返回所有文件类型，而非只有 .md"""

    def test_includes_non_markdown_files(self, file_service, temp_dir):
        """非 .md 文件（如 .py, .txt）应出现在文件树中"""
        _touch(os.path.join(temp_dir, "readme.md"), "# Title")
        _touch(os.path.join(temp_dir, "main.py"), "print('hi')")
        _touch(os.path.join(temp_dir, "data.txt"), "hello")

        tree = file_service.get_directory_tree()
        file_names = [c.name for c in tree.children if c.type == "file"]

        assert "readme.md" in file_names
        assert "main.py" in file_names
        assert "data.txt" in file_names

    def test_file_node_has_extension_field(self, file_service, temp_dir):
        """文件节点应填充 extension 字段"""
        _touch(os.path.join(temp_dir, "notes.md"))
        tree = file_service.get_directory_tree()
        node = next(c for c in tree.children if c.name == "notes.md")
        assert node.extension == ".md"

    def test_file_node_has_file_type_field(self, file_service, temp_dir):
        """文件节点应填充 file_type 字段"""
        _touch(os.path.join(temp_dir, "index.html"))
        tree = file_service.get_directory_tree()
        node = next(c for c in tree.children if c.name == "index.html")
        assert node.file_type == "html"

    def test_file_node_has_previewable_field(self, file_service, temp_dir):
        """文件节点应填充 previewable 字段"""
        _touch(os.path.join(temp_dir, "readme.md"))
        _touch(os.path.join(temp_dir, "main.py"))
        tree = file_service.get_directory_tree()

        md_node = next(c for c in tree.children if c.name == "readme.md")
        py_node = next(c for c in tree.children if c.name == "main.py")

        assert md_node.previewable is True
        assert py_node.previewable is False

    def test_ignored_files_not_included(self, file_service, temp_dir):
        """被忽略的文件（如 .gitignore、node_modules）不应出现"""
        _touch(os.path.join(temp_dir, "good.md"))
        _touch(os.path.join(temp_dir, ".gitignore"))  # 隐藏文件，应被忽略
        os.makedirs(os.path.join(temp_dir, "node_modules"), exist_ok=True)
        _touch(os.path.join(temp_dir, "node_modules", "package.js"))

        tree = file_service.get_directory_tree()
        all_names = [c.name for c in tree.children]

        assert ".gitignore" not in all_names
        assert "node_modules" not in all_names

    def test_empty_directories_excluded(self, file_service, temp_dir):
        """没有任何文件的空目录不应出现在树中"""
        os.makedirs(os.path.join(temp_dir, "empty_dir"), exist_ok=True)
        _touch(os.path.join(temp_dir, "readme.md"))

        tree = file_service.get_directory_tree()
        dir_names = [c.name for c in tree.children if c.type == "directory"]
        assert "empty_dir" not in dir_names

    def test_directory_with_files_included(self, file_service, temp_dir):
        """包含文件的子目录应出现在树中"""
        os.makedirs(os.path.join(temp_dir, "docs"), exist_ok=True)
        _touch(os.path.join(temp_dir, "docs", "guide.md"))

        tree = file_service.get_directory_tree()
        dir_names = [c.name for c in tree.children if c.type == "directory"]
        assert "docs" in dir_names

    def test_nested_directory_scan(self, file_service, temp_dir):
        """嵌套目录中的文件也应被扫描"""
        _touch(os.path.join(temp_dir, "a", "b", "deep.py"), "pass")

        tree = file_service.get_directory_tree()
        a_dir = next(c for c in tree.children if c.name == "a")
        b_dir = next(c for c in a_dir.children if c.name == "b")
        deep_file = next(c for c in b_dir.children if c.name == "deep.py")

        assert deep_file.extension == ".py"
        assert deep_file.file_type == "code"
        assert deep_file.previewable is False


# ---------------------------------------------------------------------------
# list_directory
# ---------------------------------------------------------------------------
class TestListDirectory:
    """list_directory 返回目录和文件列表，用于浏览器对话框"""

    def test_root_directory_listing(self, file_service, temp_dir):
        """根目录浏览返回正确的目录和文件列表"""
        _touch(os.path.join(temp_dir, "readme.md"))
        _touch(os.path.join(temp_dir, "photo.png"))
        os.makedirs(os.path.join(temp_dir, "docs"), exist_ok=True)
        _touch(os.path.join(temp_dir, "docs", "guide.md"))

        result = file_service.list_directory()

        assert result["current_path"] in ("", ".")
        assert len(result["directories"]) == 1
        assert result["directories"][0]["name"] == "docs"
        file_names = [f["name"] for f in result["files"]]
        assert "readme.md" in file_names
        assert "photo.png" in file_names

    def test_subdirectory_listing(self, file_service, temp_dir):
        """浏览子目录"""
        os.makedirs(os.path.join(temp_dir, "docs"), exist_ok=True)
        _touch(os.path.join(temp_dir, "docs", "guide.md"))
        _touch(os.path.join(temp_dir, "docs", "api.html"))

        result = file_service.list_directory("docs")

        file_names = [f["name"] for f in result["files"]]
        assert "guide.md" in file_names
        assert "api.html" in file_names

    def test_list_directory_file_metadata(self, file_service, temp_dir):
        """文件条目包含扩展名、类型、可预览标志、大小"""
        _touch(os.path.join(temp_dir, "notes.md"), "hello world")

        result = file_service.list_directory()
        file_entry = next(f for f in result["files"] if f["name"] == "notes.md")

        assert file_entry["extension"] == ".md"
        assert file_entry["file_type"] == "markdown"
        assert file_entry["previewable"] is True
        assert file_entry["size"] > 0

    def test_list_directory_breadcrumbs(self, file_service, temp_dir):
        """子目录浏览返回正确的面包屑"""
        os.makedirs(os.path.join(temp_dir, "docs", "api"), exist_ok=True)

        result = file_service.list_directory("docs/api")
        crumb_names = [b["name"] for b in result["breadcrumbs"]]

        assert crumb_names[0] == os.path.basename(temp_dir)  # 根目录名
        assert "docs" in crumb_names
        assert "api" in crumb_names

    def test_list_directory_nonexistent_path_raises(self, file_service):
        """不存在的路径应抛出 ValueError"""
        with pytest.raises(ValueError, match="Directory not found"):
            file_service.list_directory("nonexistent/path")

    def test_list_directory_has_children_flag(self, file_service, temp_dir):
        """目录条目包含 has_children 标志"""
        # 有内容的子目录
        os.makedirs(os.path.join(temp_dir, "with_files"), exist_ok=True)
        _touch(os.path.join(temp_dir, "with_files", "readme.md"))

        # 空子目录
        os.makedirs(os.path.join(temp_dir, "empty_sub"), exist_ok=True)

        result = file_service.list_directory()
        with_files = next(d for d in result["directories"] if d["name"] == "with_files")
        empty_sub = next(d for d in result["directories"] if d["name"] == "empty_sub")

        assert with_files["has_children"] is True
        assert empty_sub["has_children"] is False

    def test_list_directory_ignored_entries_excluded(self, file_service, temp_dir):
        """被忽略的条目不出现在结果中"""
        _touch(os.path.join(temp_dir, ".hidden_file"))
        os.makedirs(os.path.join(temp_dir, "__pycache__"), exist_ok=True)
        _touch(os.path.join(temp_dir, "visible.md"))

        result = file_service.list_directory()
        all_names = (
            [d["name"] for d in result["directories"]]
            + [f["name"] for f in result["files"]]
        )
        assert ".hidden_file" not in all_names
        assert "__pycache__" not in all_names
        assert "visible.md" in all_names


# ---------------------------------------------------------------------------
# _build_breadcrumbs
# ---------------------------------------------------------------------------
class TestBuildBreadcrumbs:
    """_build_breadcrumbs 构建面包屑导航"""

    def test_root_breadcrumbs(self, file_service, temp_dir):
        """根目录面包屑只有根名称"""
        from pathlib import Path
        crumbs = file_service._build_breadcrumbs(Path(temp_dir))
        assert len(crumbs) == 1
        assert crumbs[0]["path"] == ""

    def test_subdir_breadcrumbs(self, file_service, temp_dir):
        """子目录面包屑包含所有层级"""
        from pathlib import Path
        target = (Path(temp_dir) / "docs" / "api").resolve()
        target.mkdir(parents=True, exist_ok=True)

        crumbs = file_service._build_breadcrumbs(target)
        assert len(crumbs) == 3  # root, docs, api
        assert crumbs[0]["path"] == ""
        assert crumbs[1]["name"] == "docs"
        assert crumbs[2]["name"] == "api"

    def test_outside_root_breadcrumbs(self, file_service, temp_dir):
        """不在 root 下的路径，面包屑只有根节点"""
        from pathlib import Path
        crumbs = file_service._build_breadcrumbs(Path("/tmp/outside_dir"))
        assert len(crumbs) == 1  # 仅根


# ---------------------------------------------------------------------------
# get_file_paths
# ---------------------------------------------------------------------------
class TestGetFilePaths:
    """get_file_paths 返回绝对/相对路径"""

    def test_get_file_paths(self, file_service, temp_dir):
        """返回正确的绝对路径、相对路径、文件名"""
        _touch(os.path.join(temp_dir, "docs", "readme.md"))

        result = file_service.get_file_paths("docs/readme.md")

        assert result["relative_path"] == "docs/readme.md"
        assert result["file_name"] == "readme.md"
        assert result["absolute_path"].endswith("docs/readme.md")
        assert result["root_path"] == str(file_service._root_path)

    def test_get_file_paths_traversal_blocked(self, file_service):
        """路径穿越应被拦截"""
        with pytest.raises(ValueError):
            file_service.get_file_paths("../../etc/passwd")


# ---------------------------------------------------------------------------
# get_directory_tree：向后兼容
# ---------------------------------------------------------------------------
class TestBackwardCompatibility:
    """确保现有行为不被破坏"""

    def test_directory_tree_still_returns_file_node(self, file_service, temp_dir):
        """get_directory_tree 仍返回 FileNode"""
        _touch(os.path.join(temp_dir, "readme.md"))
        tree = file_service.get_directory_tree()
        assert tree.type == "directory"
        assert isinstance(tree.children, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
