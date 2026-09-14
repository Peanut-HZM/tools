"""
Task 4: 文件操作 API 端点测试

覆盖 9 个 API：
  - GET  /files/browse
  - POST /files/copy
  - POST /files/move
  - POST /files/rename
  - POST /files/delete
  - POST /files/create-item
  - POST /files/upload-any
  - GET  /files/download
  - GET  /files/info
"""
import os
import sys
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# 确保 backend 目录在 sys.path 中
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.middleware.auth_middleware import get_current_user_id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_USER_ID = "test-user-api-task4"


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp = tempfile.mkdtemp(prefix="task4_api_test_")
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def client(temp_dir):
    """TestClient，覆写 auth 依赖"""

    async def _override_get_current_user_id():
        return TEST_USER_ID

    app.dependency_overrides[get_current_user_id] = _override_get_current_user_id

    # Mock MarkdownConfigService.load_config 返回 temp_dir 作为 root_path
    mock_config = MagicMock()
    mock_config.root_path = temp_dir

    with patch(
        "app.routes.markdown_editor.MarkdownConfigService"
    ) as MockConfigService:
        instance = MockConfigService.return_value
        instance.load_config.return_value = mock_config
        yield TestClient(app)

    app.dependency_overrides.pop(get_current_user_id, None)


def _touch(path: str, content: str = "content"):
    """快速创建文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# Step 10-1: browse API 测试
# ---------------------------------------------------------------------------

class TestBrowseApi:
    """GET /files/browse 测试"""

    def test_browse_directory(self, client, temp_dir):
        """测试浏览目录 API"""
        # 创建测试文件
        _touch(os.path.join(temp_dir, "test.md"), "# Hello")
        _touch(os.path.join(temp_dir, "readme.txt"), "readme")

        response = client.get(f"/api/markdown-editor/files/browse?path={temp_dir}")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "breadcrumbs" in data
        assert data["total"] >= 2

    def test_browse_empty_directory(self, client, temp_dir):
        """测试浏览空目录"""
        empty_dir = os.path.join(temp_dir, "empty")
        os.makedirs(empty_dir)

        response = client.get(f"/api/markdown-editor/files/browse?path={empty_dir}")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_browse_nonexistent_path(self, client):
        """测试浏览不存在的路径"""
        response = client.get(
            "/api/markdown-editor/files/browse?path=/nonexistent_path_xyz"
        )
        assert response.status_code == 400

    def test_browse_sensitive_path(self, client):
        """测试访问敏感路径"""
        response = client.get(
            "/api/markdown-editor/files/browse?path=/etc/shadow"
        )
        assert response.status_code == 400

    def test_browse_pagination(self, client, temp_dir):
        """测试分页"""
        # 创建 5 个文件
        for i in range(5):
            _touch(os.path.join(temp_dir, f"file_{i}.md"), f"content {i}")

        response = client.get(
            f"/api/markdown-editor/files/browse?path={temp_dir}&page=1&page_size=2"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["has_more"] is True


# ---------------------------------------------------------------------------
# Step 10-2: copy API 测试
# ---------------------------------------------------------------------------

class TestCopyApi:
    """POST /files/copy 测试"""

    def test_copy_file(self, client, temp_dir):
        """测试复制文件"""
        source = os.path.join(temp_dir, "source.md")
        _touch(source, "original content")
        target = os.path.join(temp_dir, "copy.md")

        response = client.post(
            "/api/markdown-editor/files/copy",
            json={"source_path": source, "target_path": target},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert Path(target).exists()
        assert Path(target).read_text() == "original content"

    def test_copy_nonexistent_source(self, client, temp_dir):
        """测试复制不存在的源文件"""
        response = client.post(
            "/api/markdown-editor/files/copy",
            json={
                "source_path": os.path.join(temp_dir, "no_such_file"),
                "target_path": os.path.join(temp_dir, "target"),
            },
        )
        assert response.status_code == 400

    def test_copy_sensitive_path(self, client):
        """测试复制到敏感路径"""
        response = client.post(
            "/api/markdown-editor/files/copy",
            json={
                "source_path": "/tmp/some_file",
                "target_path": "/etc/shadow",
            },
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Step 10-3: move API 测试
# ---------------------------------------------------------------------------

class TestMoveApi:
    """POST /files/move 测试"""

    def test_move_file(self, client, temp_dir):
        """测试移动文件"""
        source = os.path.join(temp_dir, "original.md")
        _touch(source, "move me")
        target = os.path.join(temp_dir, "moved.md")

        response = client.post(
            "/api/markdown-editor/files/move",
            json={"source_path": source, "target_path": target},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert not Path(source).exists()
        assert Path(target).exists()

    def test_move_nonexistent_source(self, client, temp_dir):
        """测试移动不存在的源文件"""
        response = client.post(
            "/api/markdown-editor/files/move",
            json={
                "source_path": os.path.join(temp_dir, "ghost"),
                "target_path": os.path.join(temp_dir, "target"),
            },
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Step 10-4: rename API 测试
# ---------------------------------------------------------------------------

class TestRenameApi:
    """POST /files/rename 测试"""

    def test_rename_file(self, client, temp_dir):
        """测试重命名文件"""
        source = os.path.join(temp_dir, "old_name.md")
        _touch(source, "rename me")

        response = client.post(
            "/api/markdown-editor/files/rename-item",
            json={"path": source, "new_name": "new_name.md"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert not Path(source).exists()
        assert Path(os.path.join(temp_dir, "new_name.md")).exists()

    def test_rename_nonexistent(self, client, temp_dir):
        """测试重命名不存在的文件"""
        response = client.post(
            "/api/markdown-editor/files/rename-item",
            json={
                "path": os.path.join(temp_dir, "no_such_file"),
                "new_name": "whatever",
            },
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Step 10-5: delete API 测试
# ---------------------------------------------------------------------------

class TestDeleteApi:
    """POST /files/delete 测试"""

    def test_delete_file(self, client, temp_dir):
        """测试删除文件"""
        target = os.path.join(temp_dir, "delete_me.md")
        _touch(target, "goodbye")

        response = client.post(
            "/api/markdown-editor/files/delete-item",
            json={"path": target},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert not Path(target).exists()

    def test_delete_directory(self, client, temp_dir):
        """测试删除目录"""
        target_dir = os.path.join(temp_dir, "delete_dir")
        os.makedirs(target_dir)
        _touch(os.path.join(target_dir, "inner.md"), "inner")

        response = client.post(
            "/api/markdown-editor/files/delete-item",
            json={"path": target_dir},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert not Path(target_dir).exists()

    def test_delete_nonexistent(self, client, temp_dir):
        """测试删除不存在的文件"""
        response = client.post(
            "/api/markdown-editor/files/delete-item",
            json={"path": os.path.join(temp_dir, "ghost")},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Step 10-6: create-item API 测试
# ---------------------------------------------------------------------------

class TestCreateItemApi:
    """POST /files/create-item 测试"""

    def test_create_file(self, client, temp_dir):
        """测试创建文件"""
        response = client.post(
            "/api/markdown-editor/files/create-item",
            json={"parent_path": temp_dir, "name": "new.md", "type": "file"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert Path(os.path.join(temp_dir, "new.md")).exists()

    def test_create_directory(self, client, temp_dir):
        """测试创建目录"""
        response = client.post(
            "/api/markdown-editor/files/create-item",
            json={
                "parent_path": temp_dir,
                "name": "new_folder",
                "type": "directory",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert Path(os.path.join(temp_dir, "new_folder")).is_dir()

    def test_create_invalid_type(self, client, temp_dir):
        """测试创建无效类型"""
        response = client.post(
            "/api/markdown-editor/files/create-item",
            json={"parent_path": temp_dir, "name": "bad", "type": "symlink"},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Step 10-7: upload-any API 测试
# ---------------------------------------------------------------------------

class TestUploadAnyApi:
    """POST /files/upload-any 测试"""

    def test_upload_file(self, client, temp_dir):
        """测试上传文件"""
        response = client.post(
            f"/api/markdown-editor/files/upload-any?parent_path={temp_dir}",
            files={"file": ("uploaded.txt", b"file content", "text/plain")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert Path(os.path.join(temp_dir, "uploaded.txt")).exists()

    def test_upload_without_parent_path(self, client, temp_dir):
        """测试不指定 parent_path"""
        response = client.post(
            "/api/markdown-editor/files/upload-any",
            files={"file": ("test.txt", b"data", "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_no_filename(self, client, temp_dir):
        """测试上传无文件名"""
        response = client.post(
            f"/api/markdown-editor/files/upload-any?parent_path={temp_dir}",
            files={"file": ("", b"data", "text/plain")},
        )
        # FastAPI 可能返回 422（multipart 解析失败）或 400（handler 检查）
        assert response.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Step 10-8: download API 测试
# ---------------------------------------------------------------------------

class TestDownloadApi:
    """GET /files/download 测试"""

    def test_download_file(self, client, temp_dir):
        """测试下载文件"""
        target = os.path.join(temp_dir, "download_me.txt")
        _touch(target, "download content")

        response = client.get(
            f"/api/markdown-editor/files/download?path={target}"
        )
        assert response.status_code == 200
        assert response.content == b"download content"

    def test_download_nonexistent(self, client, temp_dir):
        """测试下载不存在的文件"""
        response = client.get(
            f"/api/markdown-editor/files/download?path={os.path.join(temp_dir, 'ghost')}"
        )
        assert response.status_code == 400

    def test_download_sensitive_path(self, client):
        """测试下载敏感路径"""
        response = client.get(
            "/api/markdown-editor/files/download?path=/etc/shadow"
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Step 10-9: info API 测试
# ---------------------------------------------------------------------------

class TestInfoApi:
    """GET /files/info 测试"""

    def test_get_file_info(self, client, temp_dir):
        """测试获取文件信息"""
        target = os.path.join(temp_dir, "info_test.md")
        _touch(target, "# Info Test")

        response = client.get(
            f"/api/markdown-editor/files/info?path={target}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "info_test.md"
        assert data["type"] == "file"
        assert data["extension"] == ".md"

    def test_get_directory_info(self, client, temp_dir):
        """测试获取目录信息"""
        response = client.get(
            f"/api/markdown-editor/files/info?path={temp_dir}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "directory"

    def test_info_nonexistent(self, client, temp_dir):
        """测试获取不存在路径的信息"""
        response = client.get(
            f"/api/markdown-editor/files/info?path={os.path.join(temp_dir, 'ghost')}"
        )
        assert response.status_code == 400

    def test_info_sensitive_path(self, client):
        """测试获取敏感路径信息"""
        response = client.get(
            "/api/markdown-editor/files/info?path=/etc/shadow"
        )
        assert response.status_code == 400
