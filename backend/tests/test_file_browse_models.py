"""
FileItem 和 BrowseResponse 数据模型单元测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import ValidationError
from app.models.file_models import FileItem, BrowseResponse


class TestFileItem:
    """FileItem 模型测试"""

    def test_create_file_item(self):
        """测试创建文件类型的 FileItem"""
        item = FileItem(
            name="readme.md",
            path="/docs/readme.md",
            type="file",
            size=1024,
            modified_at="2026-09-14T10:00:00",
            extension=".md",
            is_previewable=True,
        )
        assert item.name == "readme.md"
        assert item.path == "/docs/readme.md"
        assert item.type == "file"
        assert item.size == 1024
        assert item.modified_at == "2026-09-14T10:00:00"
        assert item.extension == ".md"
        assert item.is_previewable is True

    def test_create_directory_item(self):
        """测试创建目录类型的 FileItem"""
        item = FileItem(
            name="docs",
            path="/docs",
            type="directory",
            size=0,
            modified_at="2026-09-14T10:00:00",
        )
        assert item.type == "directory"
        assert item.size == 0
        assert item.extension == ""
        assert item.is_previewable is False

    def test_default_values(self):
        """测试默认值"""
        item = FileItem(
            name="test.txt",
            path="/test.txt",
            type="file",
            modified_at="2026-09-14T10:00:00",
        )
        assert item.size == 0
        assert item.extension == ""
        assert item.is_previewable is False

    def test_invalid_type_rejected(self):
        """测试非法 type 值被拒绝"""
        with pytest.raises(ValidationError):
            FileItem(
                name="bad",
                path="/bad",
                type="symlink",
                modified_at="2026-09-14T10:00:00",
            )

    def test_missing_required_fields(self):
        """测试缺少必填字段时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            FileItem(name="only_name")

    def test_type_only_file_or_directory(self):
        """测试 type 只接受 file 和 directory"""
        # file 和 directory 都合法
        FileItem(name="a", path="/a", type="file", modified_at="2026-01-01T00:00:00")
        FileItem(name="b", path="/b", type="directory", modified_at="2026-01-01T00:00:00")


class TestBrowseResponse:
    """BrowseResponse 模型测试"""

    def test_create_browse_response(self):
        """测试创建完整的 BrowseResponse"""
        items = [
            FileItem(
                name="file1.md",
                path="/docs/file1.md",
                type="file",
                size=512,
                modified_at="2026-09-14T10:00:00",
                extension=".md",
                is_previewable=True,
            ),
            FileItem(
                name="subdir",
                path="/docs/subdir",
                type="directory",
                modified_at="2026-09-14T09:00:00",
            ),
        ]
        response = BrowseResponse(
            current_path="/docs",
            breadcrumbs=[
                {"name": "root", "path": "/"},
                {"name": "docs", "path": "/docs"},
            ],
            items=items,
            total=2,
        )
        assert response.current_path == "/docs"
        assert len(response.breadcrumbs) == 2
        assert len(response.items) == 2
        assert response.total == 2
        assert response.has_more is False

    def test_has_more_default_false(self):
        """测试 has_more 默认值为 False"""
        response = BrowseResponse(
            current_path="/",
            breadcrumbs=[],
            items=[],
            total=0,
        )
        assert response.has_more is False

    def test_has_more_true(self):
        """测试显式设置 has_more 为 True"""
        response = BrowseResponse(
            current_path="/",
            breadcrumbs=[],
            items=[],
            total=100,
            has_more=True,
        )
        assert response.has_more is True

    def test_empty_items(self):
        """测试空目录响应"""
        response = BrowseResponse(
            current_path="/empty",
            breadcrumbs=[{"name": "empty", "path": "/empty"}],
            items=[],
            total=0,
        )
        assert response.items == []
        assert response.total == 0

    def test_missing_required_fields(self):
        """测试缺少必填字段时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            BrowseResponse(current_path="/")
