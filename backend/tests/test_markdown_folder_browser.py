"""
「打开文件夹」功能单元测试

覆盖打开文件夹（任意路径浏览）相关的关键行为：
  - 隐藏文件/目录可见、可进入（.git 等以 . 开头的目录必须能打开）
  - include_hidden=False 时隐藏条目被隐藏
  - 任意路径浏览：绝对路径、~ 展开、相对路径、.. 向上导航
  - 文件树扫描：符号链接环防护、节点预算截断标记
  - 工作区根目录失效时如实报错，而不是静默切换目录
  - /files/root 接口：~ 展开、exists 真实反映目录是否存在
"""
import os
import sys
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.middleware.auth_middleware import get_current_user_id
from app.services import markdown_file_service as service_module
from app.services.markdown_file_service import MarkdownFileService

TEST_USER_ID = "test-user-folder-browser"


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp = tempfile.mkdtemp(prefix="folder_browser_test_")
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def any_path_service(temp_dir):
    """任意路径模式的服务实例"""
    service = MarkdownFileService(TEST_USER_ID, allow_any_path=True)
    service._root_path = Path(temp_dir).resolve()
    return service


def _touch(path: str, content: str = "content"):
    """快速创建文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# 隐藏文件 / 隐藏目录
# ---------------------------------------------------------------------------
class TestHiddenEntries:
    """隐藏条目（以 . 开头）的可见性与可进入性"""

    def test_hidden_dir_visible_in_browse(self, any_path_service, temp_dir):
        """隐藏目录在浏览器中可见"""
        os.makedirs(os.path.join(temp_dir, ".git"), exist_ok=True)

        result = any_path_service.browse_directory(temp_dir)
        names = [item.name for item in result.items]

        assert ".git" in names

    def test_hidden_dir_can_be_entered(self, any_path_service, temp_dir):
        """隐藏目录可以直接进入，内容能正常加载"""
        hidden_dir = os.path.join(temp_dir, ".config")
        os.makedirs(hidden_dir, exist_ok=True)
        _touch(os.path.join(hidden_dir, "app.json"), "{}")

        result = any_path_service.browse_directory(hidden_dir)

        assert result.current_path == str(Path(hidden_dir).resolve())
        assert [item.name for item in result.items] == ["app.json"]

    def test_hidden_items_marked_in_response(self, any_path_service, temp_dir):
        """隐藏条目带 is_hidden 标记，前端可区分展示"""
        _touch(os.path.join(temp_dir, ".env"))
        _touch(os.path.join(temp_dir, "readme.md"))

        result = any_path_service.browse_directory(temp_dir)
        flags = {item.name: item.is_hidden for item in result.items}

        assert flags[".env"] is True
        assert flags["readme.md"] is False

    def test_include_hidden_false_hides_entries(self, temp_dir):
        """include_hidden=False 时隐藏条目不出现"""
        os.makedirs(os.path.join(temp_dir, ".git"), exist_ok=True)
        _touch(os.path.join(temp_dir, ".env"))

        service = MarkdownFileService(TEST_USER_ID, allow_any_path=True, include_hidden=False)
        service._root_path = Path(temp_dir).resolve()

        result = service.browse_directory(temp_dir)
        names = [item.name for item in result.items]

        assert ".git" not in names
        assert ".env" not in names


# ---------------------------------------------------------------------------
# 任意路径浏览
# ---------------------------------------------------------------------------
class TestBrowseAnyPath:
    """任意路径解析"""

    def test_absolute_path(self, any_path_service, temp_dir):
        """绝对路径"""
        result = any_path_service.browse_directory(temp_dir)
        assert result.current_path == str(Path(temp_dir).resolve())

    def test_relative_path_against_root(self, any_path_service, temp_dir):
        """相对路径相对当前根目录解析"""
        os.makedirs(os.path.join(temp_dir, "docs"), exist_ok=True)
        _touch(os.path.join(temp_dir, "docs", "a.md"))

        result = any_path_service.browse_directory("docs")

        assert result.current_path == str(Path(temp_dir, "docs").resolve())
        assert [item.name for item in result.items] == ["a.md"]

    def test_tilde_expanded(self, any_path_service):
        """~ 展开为用户主目录"""
        from app.config.config import REAL_HOME

        result = any_path_service.browse_directory("~")

        assert result.current_path == str(Path(REAL_HOME).resolve())

    def test_parent_traversal(self, any_path_service, temp_dir):
        """.. 允许（向上层导航是正常操作）"""
        sub = os.path.join(temp_dir, "sub")
        os.makedirs(sub, exist_ok=True)

        result = any_path_service.browse_directory(os.path.join(sub, ".."))

        assert result.current_path == str(Path(temp_dir).resolve())

    def test_sensitive_path_rejected(self, any_path_service):
        """系统敏感路径仍然拒绝"""
        with pytest.raises(ValueError, match="敏感"):
            any_path_service.browse_directory("/etc/shadow")

    def test_nonexistent_path_raises(self, any_path_service, temp_dir):
        """不存在的目录明确报错"""
        with pytest.raises(ValueError, match="目录不存在"):
            any_path_service.browse_directory(os.path.join(temp_dir, "nope"))

    def test_breadcrumbs_are_absolute(self, any_path_service, temp_dir):
        """面包屑每一级都是可直接跳转的绝对路径"""
        nested = os.path.join(temp_dir, "a", "b")
        os.makedirs(nested, exist_ok=True)

        result = any_path_service.browse_directory(nested)

        paths = [crumb["path"] for crumb in result.breadcrumbs]
        assert paths[0] == "/"
        assert str(Path(temp_dir).resolve()) in paths
        assert str(Path(nested).resolve()) in paths


# ---------------------------------------------------------------------------
# 文件树扫描健壮性
# ---------------------------------------------------------------------------
class TestTreeScanRobustness:
    """文件树扫描的健壮性"""

    def test_symlink_loop_does_not_recurse_forever(self, temp_dir):
        """软链接指回祖先目录时不会无限递归"""
        loop_dir = os.path.join(temp_dir, "a", "b")
        os.makedirs(loop_dir, exist_ok=True)
        _touch(os.path.join(loop_dir, "file.md"))
        try:
            os.symlink(temp_dir, os.path.join(loop_dir, "loop"))
        except (OSError, NotImplementedError):
            pytest.skip("当前平台不支持创建符号链接")

        service = MarkdownFileService(TEST_USER_ID, custom_root=temp_dir)
        tree = service.get_directory_tree()

        def count_nodes(node):
            total = 1
            for child in node.children or []:
                total += count_nodes(child)
            return total

        # 扫描必须终止，且节点数受控（没有无限展开）
        assert count_nodes(tree) < 20

        a_node = next(c for c in tree.children if c.name == "a")
        b_node = next(c for c in a_node.children if c.name == "b")
        # 环状链接仍然可见（用户能看到这个软链接），但不无限递归
        loop_node = next(c for c in b_node.children if c.name == "loop")
        assert loop_node.type == "directory"

    def test_scan_budget_marks_truncated(self, temp_dir, monkeypatch):
        """节点数超限时标记 truncated（显式告知，不静默丢内容）"""
        for i in range(20):
            _touch(os.path.join(temp_dir, f"file_{i:02d}.md"))

        monkeypatch.setattr(service_module, "MAX_SCAN_NODES", 5)
        service = MarkdownFileService(TEST_USER_ID, custom_root=temp_dir)
        tree = service.get_directory_tree()

        assert tree.truncated is True
        assert len(tree.children) <= 5

    def test_permission_denied_marks_inaccessible(self, temp_dir):
        """无权限目录标记 inaccessible，而不是伪装成空目录"""
        if os.geteuid() == 0:
            pytest.skip("root 用户无法复现权限不足场景")

        locked = os.path.join(temp_dir, "locked")
        os.makedirs(locked, exist_ok=True)
        _touch(os.path.join(locked, "secret.md"))
        os.chmod(locked, 0o000)
        try:
            service = MarkdownFileService(TEST_USER_ID, custom_root=temp_dir)
            tree = service.get_directory_tree()
            locked_node = next(c for c in tree.children if c.name == "locked")
            assert locked_node.inaccessible is True
        finally:
            os.chmod(locked, 0o755)


# ---------------------------------------------------------------------------
# 工作区根目录
# ---------------------------------------------------------------------------
class TestWorkspaceRoot:
    """工作区根目录的有效性"""

    def test_missing_custom_root_is_reported(self, temp_dir):
        """配置的根目录失效时如实标记（不静默切换目录）"""
        missing = os.path.join(temp_dir, "not-exists")
        service = MarkdownFileService(TEST_USER_ID, custom_root=missing)

        assert service._root_missing is True
        assert service._configured_root == missing

    def test_existing_custom_root_is_used(self, temp_dir):
        """存在的根目录正常生效"""
        service = MarkdownFileService(TEST_USER_ID, custom_root=temp_dir)

        assert service._root_missing is False
        assert str(service.get_root_path()) == str(Path(temp_dir).resolve())


# ---------------------------------------------------------------------------
# API：/files/root 与 /files/browse
# ---------------------------------------------------------------------------
class TestFolderBrowserApi:
    """打开文件夹相关 API"""

    @pytest.fixture
    def client(self, temp_dir):
        """TestClient，覆写 auth 与配置服务"""
        async def _override_get_current_user_id():
            return TEST_USER_ID

        app.dependency_overrides[get_current_user_id] = _override_get_current_user_id

        mock_config = MagicMock()
        mock_config.root_path = temp_dir

        with patch("app.routes.markdown_editor.MarkdownConfigService") as MockConfigService:
            instance = MockConfigService.return_value
            instance.load_config.return_value = mock_config
            yield TestClient(app)

        app.dependency_overrides.pop(get_current_user_id, None)

    def test_browse_include_hidden_false(self, client, temp_dir):
        """include_hidden=false 时隐藏条目不返回"""
        os.makedirs(os.path.join(temp_dir, ".git"), exist_ok=True)
        _touch(os.path.join(temp_dir, "readme.md"))

        response = client.get(
            f"/api/markdown-editor/files/browse?path={temp_dir}&include_hidden=false"
        )

        assert response.status_code == 200
        names = [item["name"] for item in response.json()["items"]]
        assert ".git" not in names
        assert "readme.md" in names

    def test_browse_returns_absolute_current_path(self, client, temp_dir):
        """current_path 是绝对路径，可直接作为工作区根目录"""
        response = client.get(f"/api/markdown-editor/files/browse?path={temp_dir}")

        assert response.status_code == 200
        assert response.json()["current_path"] == str(Path(temp_dir).resolve())

    def test_update_root_path_expands_tilde(self, client):
        """POST /files/root 支持 ~ 开头路径"""
        from app.config.config import REAL_HOME

        response = client.post(
            "/api/markdown-editor/files/root",
            json={"path": "~"},
        )

        assert response.status_code == 200
        assert response.json()["path"] == str(Path(REAL_HOME).resolve())

    def test_update_root_path_rejects_missing_dir(self, client, temp_dir):
        """不存在的目录明确报错"""
        response = client.post(
            "/api/markdown-editor/files/root",
            json={"path": os.path.join(temp_dir, "nope")},
        )

        assert response.status_code == 400

    def test_update_root_path_rejects_file(self, client, temp_dir):
        """文件不是目录，明确报错"""
        target = os.path.join(temp_dir, "a.md")
        _touch(target)

        response = client.post("/api/markdown-editor/files/root", json={"path": target})

        assert response.status_code == 400
