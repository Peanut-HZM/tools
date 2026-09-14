"""
MarkdownFileService Task 3 单元测试

覆盖：
  - allow_any_path 模式
  - _validate_and_resolve 任意路径支持
  - browse_directory() 目录浏览（分页）
  - copy_item() 复制文件/文件夹
  - move_item() 移动文件/文件夹
  - get_download_path() 下载路径验证
  - get_file_info() 文件信息
"""
import os
import sys
import tempfile
import shutil
import pytest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.markdown_file_service import MarkdownFileService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def file_service(temp_dir):
    """普通模式（allow_any_path=False）"""
    service = MarkdownFileService("test-user-task3")
    service._root_path = Path(temp_dir).resolve()
    return service


@pytest.fixture
def any_path_service(temp_dir):
    """任意路径模式（allow_any_path=True）"""
    service = MarkdownFileService("test-user-task3", allow_any_path=True)
    service._root_path = Path(temp_dir).resolve()
    return service


def _touch(path: str, content: str = "content"):
    """快速创建文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# Step 1: allow_any_path 模式
# ---------------------------------------------------------------------------
class TestAllowAnyPathMode:
    """__init__ 支持 allow_any_path 参数"""

    def test_default_allow_any_path_is_false(self):
        """默认 allow_any_path 为 False"""
        service = MarkdownFileService("test-user")
        assert service.allow_any_path is False

    def test_allow_any_path_true(self):
        """传入 allow_any_path=True 时属性为 True"""
        service = MarkdownFileService("test-user", allow_any_path=True)
        assert service.allow_any_path is True


# ---------------------------------------------------------------------------
# Step 2: _validate_and_resolve 支持任意路径
# ---------------------------------------------------------------------------
class TestValidateAndResolveAnyPath:
    """_validate_and_resolve 在 allow_any_path 模式下使用 validate_any_path"""

    def test_any_path_mode_accepts_absolute_path(self, any_path_service, temp_dir):
        """任意路径模式接受绝对路径"""
        result = any_path_service._validate_and_resolve(temp_dir)
        assert str(result) == str(Path(temp_dir).resolve())

    def test_any_path_mode_rejects_sensitive_path(self, any_path_service):
        """任意路径模式拒绝敏感路径"""
        with pytest.raises(ValueError, match="敏感"):
            any_path_service._validate_and_resolve("/etc/shadow")

    def test_any_path_mode_rejects_traversal(self, any_path_service):
        """任意路径模式拒绝路径遍历"""
        with pytest.raises(ValueError, match="遍历"):
            any_path_service._validate_and_resolve("../../etc/passwd")

    def test_normal_mode_rejects_outside_root(self, file_service, temp_dir):
        """普通模式拒绝 root 外的路径"""
        with pytest.raises(ValueError):
            file_service._validate_and_resolve("/etc/passwd")

    def test_normal_mode_accepts_relative_path(self, file_service, temp_dir):
        """普通模式接受 root 内的相对路径"""
        _touch(os.path.join(temp_dir, "test.md"))
        result = file_service._validate_and_resolve("test.md")
        assert result.exists()


# ---------------------------------------------------------------------------
# Step 3: browse_directory
# ---------------------------------------------------------------------------
class TestBrowseDirectory:
    """browse_directory 方法"""

    def test_browse_root_directory(self, any_path_service, temp_dir):
        """浏览根目录返回所有条目"""
        _touch(os.path.join(temp_dir, "readme.md"))
        _touch(os.path.join(temp_dir, "notes.txt"))
        os.makedirs(os.path.join(temp_dir, "docs"), exist_ok=True)

        result = any_path_service.browse_directory(temp_dir)

        assert result.current_path == str(Path(temp_dir).resolve())
        assert result.total == 3
        assert len(result.items) == 3
        assert result.has_more is False

    def test_browse_subdirectory(self, any_path_service, temp_dir):
        """浏览子目录"""
        subdir = os.path.join(temp_dir, "docs")
        os.makedirs(subdir, exist_ok=True)
        _touch(os.path.join(subdir, "guide.md"))

        result = any_path_service.browse_directory(subdir)

        assert result.total == 1
        assert result.items[0].name == "guide.md"

    def test_browse_nonexistent_directory_raises(self, any_path_service, temp_dir):
        """不存在的目录抛出 ValueError"""
        fake_path = os.path.join(temp_dir, "nonexistent")
        with pytest.raises(ValueError, match="目录不存在"):
            any_path_service.browse_directory(fake_path)

    def test_browse_file_raises(self, any_path_service, temp_dir):
        """传入文件路径抛出 ValueError"""
        file_path = os.path.join(temp_dir, "readme.md")
        _touch(file_path)
        with pytest.raises(ValueError, match="目录不存在"):
            any_path_service.browse_directory(file_path)

    def test_browse_pagination(self, any_path_service, temp_dir):
        """分页功能"""
        for i in range(15):
            _touch(os.path.join(temp_dir, f"file_{i:02d}.md"))

        result_page1 = any_path_service.browse_directory(temp_dir, page=1, page_size=10)
        assert len(result_page1.items) == 10
        assert result_page1.total == 15
        assert result_page1.has_more is True

        result_page2 = any_path_service.browse_directory(temp_dir, page=2, page_size=10)
        assert len(result_page2.items) == 5
        assert result_page2.has_more is False

    def test_browse_directories_first(self, any_path_service, temp_dir):
        """目录排在文件前面"""
        _touch(os.path.join(temp_dir, "aaa.md"))
        os.makedirs(os.path.join(temp_dir, "zzz_dir"), exist_ok=True)

        result = any_path_service.browse_directory(temp_dir)
        assert result.items[0].type == "directory"
        assert result.items[1].type == "file"

    def test_browse_hidden_files_excluded(self, any_path_service, temp_dir):
        """隐藏文件被排除"""
        _touch(os.path.join(temp_dir, ".hidden"))
        _touch(os.path.join(temp_dir, "visible.md"))

        result = any_path_service.browse_directory(temp_dir)
        names = [item.name for item in result.items]
        assert ".hidden" not in names
        assert "visible.md" in names

    def test_browse_ignored_dirs_excluded(self, any_path_service, temp_dir):
        """忽略的目录（node_modules 等）被排除"""
        os.makedirs(os.path.join(temp_dir, "node_modules"), exist_ok=True)
        _touch(os.path.join(temp_dir, "node_modules", "pkg.js"))
        _touch(os.path.join(temp_dir, "readme.md"))

        result = any_path_service.browse_directory(temp_dir)
        names = [item.name for item in result.items]
        assert "node_modules" not in names

    def test_browse_file_item_fields(self, any_path_service, temp_dir):
        """FileItem 字段正确填充"""
        _touch(os.path.join(temp_dir, "test.md"), "# Hello")

        result = any_path_service.browse_directory(temp_dir)
        item = result.items[0]

        assert item.name == "test.md"
        assert item.type == "file"
        assert item.size > 0
        assert item.extension == ".md"
        assert item.is_previewable is True
        assert item.modified_at

    def test_browse_directory_item_fields(self, any_path_service, temp_dir):
        """目录 FileItem 字段"""
        os.makedirs(os.path.join(temp_dir, "docs"), exist_ok=True)

        result = any_path_service.browse_directory(temp_dir)
        item = result.items[0]

        assert item.name == "docs"
        assert item.type == "directory"
        assert item.size == 0
        assert item.extension == ""
        assert item.is_previewable is False

    def test_browse_breadcrumbs(self, any_path_service, temp_dir):
        """面包屑导航正确构建"""
        result = any_path_service.browse_directory(temp_dir)
        assert len(result.breadcrumbs) >= 1
        assert result.breadcrumbs[0]["name"] == "根目录"


# ---------------------------------------------------------------------------
# Step 4: copy_item
# ---------------------------------------------------------------------------
class TestCopyItem:
    """copy_item 方法"""

    def test_copy_file(self, any_path_service, temp_dir):
        """复制文件"""
        src = os.path.join(temp_dir, "source.md")
        dst = os.path.join(temp_dir, "copy.md")
        _touch(src, "original content")

        result = any_path_service.copy_item(src, dst)

        assert result["success"] is True
        assert Path(dst).exists()
        assert Path(dst).read_text() == "original content"
        assert Path(src).exists()

    def test_copy_directory(self, any_path_service, temp_dir):
        """复制文件夹"""
        src_dir = os.path.join(temp_dir, "src_dir")
        os.makedirs(src_dir, exist_ok=True)
        _touch(os.path.join(src_dir, "file.md"), "content")

        dst_dir = os.path.join(temp_dir, "dst_dir")
        result = any_path_service.copy_item(src_dir, dst_dir)

        assert result["success"] is True
        assert Path(dst_dir).is_dir()
        assert (Path(dst_dir) / "file.md").exists()

    def test_copy_nonexistent_source(self, any_path_service, temp_dir):
        """源路径不存在"""
        result = any_path_service.copy_item(
            os.path.join(temp_dir, "nonexistent.md"),
            os.path.join(temp_dir, "copy.md"),
        )
        assert result["success"] is False
        assert "不存在" in result["message"]

    def test_copy_existing_target(self, any_path_service, temp_dir):
        """目标路径已存在"""
        src = os.path.join(temp_dir, "source.md")
        dst = os.path.join(temp_dir, "existing.md")
        _touch(src)
        _touch(dst)

        result = any_path_service.copy_item(src, dst)
        assert result["success"] is False
        assert "已存在" in result["message"]

    def test_copy_creates_parent_dirs(self, any_path_service, temp_dir):
        """复制时自动创建目标父目录"""
        src = os.path.join(temp_dir, "source.md")
        dst = os.path.join(temp_dir, "nested", "deep", "copy.md")
        _touch(src, "content")

        result = any_path_service.copy_item(src, dst)
        assert result["success"] is True
        assert Path(dst).exists()


# ---------------------------------------------------------------------------
# Step 5: move_item
# ---------------------------------------------------------------------------
class TestMoveItem:
    """move_item 方法"""

    def test_move_file(self, any_path_service, temp_dir):
        """移动文件"""
        src = os.path.join(temp_dir, "source.md")
        dst = os.path.join(temp_dir, "moved.md")
        _touch(src, "content")

        result = any_path_service.move_item(src, dst)

        assert result["success"] is True
        assert Path(dst).exists()
        assert not Path(src).exists()

    def test_move_directory(self, any_path_service, temp_dir):
        """移动文件夹"""
        src_dir = os.path.join(temp_dir, "src_dir")
        os.makedirs(src_dir, exist_ok=True)
        _touch(os.path.join(src_dir, "file.md"))

        dst_dir = os.path.join(temp_dir, "dst_dir")
        result = any_path_service.move_item(src_dir, dst_dir)

        assert result["success"] is True
        assert Path(dst_dir).is_dir()
        assert not Path(src_dir).exists()

    def test_move_nonexistent_source(self, any_path_service, temp_dir):
        """源路径不存在"""
        result = any_path_service.move_item(
            os.path.join(temp_dir, "nonexistent"),
            os.path.join(temp_dir, "dst"),
        )
        assert result["success"] is False
        assert "不存在" in result["message"]

    def test_move_existing_target(self, any_path_service, temp_dir):
        """目标路径已存在"""
        src = os.path.join(temp_dir, "source.md")
        dst = os.path.join(temp_dir, "existing.md")
        _touch(src)
        _touch(dst)

        result = any_path_service.move_item(src, dst)
        assert result["success"] is False
        assert "已存在" in result["message"]


# ---------------------------------------------------------------------------
# Step 6: get_download_path
# ---------------------------------------------------------------------------
class TestGetDownloadPath:
    """get_download_path 方法"""

    def test_download_valid_file(self, any_path_service, temp_dir):
        """有效文件返回路径"""
        file_path = os.path.join(temp_dir, "readme.md")
        _touch(file_path, "content")

        result = any_path_service.get_download_path(file_path)
        assert result.exists()
        assert result.is_file()

    def test_download_nonexistent_raises(self, any_path_service, temp_dir):
        """不存在的文件抛出 ValueError"""
        with pytest.raises(ValueError, match="不存在"):
            any_path_service.get_download_path(os.path.join(temp_dir, "nope.md"))

    def test_download_directory_raises(self, any_path_service, temp_dir):
        """目录不是文件，抛出 ValueError"""
        with pytest.raises(ValueError, match="不是文件"):
            any_path_service.get_download_path(temp_dir)

    def test_download_oversized_file_raises(self, any_path_service, temp_dir):
        """超过 100MB 的文件抛出 ValueError"""
        file_path = os.path.join(temp_dir, "huge.bin")
        with open(file_path, "wb") as f:
            f.seek(101 * 1024 * 1024)
            f.write(b"\0")

        with pytest.raises(ValueError, match="过大"):
            any_path_service.get_download_path(file_path)

        os.remove(file_path)


# ---------------------------------------------------------------------------
# Step 7: get_file_info
# ---------------------------------------------------------------------------
class TestGetFileInfo:
    """get_file_info 方法"""

    def test_file_info(self, any_path_service, temp_dir):
        """文件信息正确"""
        file_path = os.path.join(temp_dir, "test.md")
        _touch(file_path, "# Hello")

        info = any_path_service.get_file_info(file_path)

        assert info["name"] == "test.md"
        assert info["type"] == "file"
        assert info["size"] > 0
        assert info["extension"] == ".md"
        assert info["is_previewable"] is True
        assert info["modified_at"]

    def test_directory_info(self, any_path_service, temp_dir):
        """目录信息正确"""
        info = any_path_service.get_file_info(temp_dir)

        assert info["type"] == "directory"
        assert info["size"] == 0
        assert info["extension"] == ""
        assert info["is_previewable"] is False

    def test_nonexistent_path_raises(self, any_path_service, temp_dir):
        """不存在的路径抛出 ValueError"""
        with pytest.raises(ValueError, match="不存在"):
            any_path_service.get_file_info(os.path.join(temp_dir, "nope"))


# ---------------------------------------------------------------------------
# 向后兼容性
# ---------------------------------------------------------------------------
class TestBackwardCompatibility:
    """确保原有功能不受影响"""

    def test_normal_mode_still_works(self, file_service, temp_dir):
        """普通模式下原有方法正常工作"""
        _touch(os.path.join(temp_dir, "readme.md"))
        tree = file_service.get_directory_tree()
        assert tree.type == "directory"
        assert len(tree.children) > 0

    def test_normal_mode_list_directory(self, file_service, temp_dir):
        """普通模式下 list_directory 正常工作"""
        _touch(os.path.join(temp_dir, "readme.md"))
        result = file_service.list_directory()
        assert len(result["files"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
