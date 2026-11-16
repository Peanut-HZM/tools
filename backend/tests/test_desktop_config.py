"""桌面模式配置测试"""
import os
import sys
import socket
import pytest
from pathlib import Path

# 确保 backend 在 sys.path 中
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


class TestDesktopConfig:
    """测试 desktop_config.py 的核心功能"""

    def test_get_desktop_project_root_dev_mode(self):
        """开发模式下项目根目录正确"""
        from desktop_config import get_desktop_project_root
        root = get_desktop_project_root()
        assert root.exists()
        assert (root / "desktop_app.py").exists()

    def test_get_desktop_data_dir_creates(self):
        """数据目录自动创建"""
        import tempfile
        # 在临时目录中模拟冻结模式
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["DESKTOP_PROJECT_ROOT"] = tmp
            from desktop_config import get_desktop_data_dir
            data_dir = get_desktop_data_dir()
            assert data_dir.exists()
            assert data_dir.name == "data"
            # 清理环境变量
            del os.environ["DESKTOP_PROJECT_ROOT"]


class TestDesktopApp:
    """测试 desktop_app.py 的功能"""

    def test_find_available_port(self):
        """端口查找正常工作"""
        from desktop_app import find_available_port
        port = find_available_port(19100)
        assert 19100 <= port < 19120
        # 验证端口确实可用
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))

    def test_find_available_port_skips_used(self):
        """端口查找跳过已被占用的端口"""
        from desktop_app import find_available_port
        # 占用 19200
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 19200))
            port = find_available_port(19200)
            assert port != 19200
            assert 19200 < port < 19220

    def test_get_frontend_dist_path_dev_mode(self):
        """开发模式下 dist 路径正确"""
        from desktop_app import get_frontend_dist_path
        dist = get_frontend_dist_path()
        assert dist.endswith("frontend/dist") or dist.endswith("frontend\\dist")


class TestConfigIsolation:
    """测试 config.py 的桌面模式隔离"""

    def test_home_not_overridden_in_desktop_mode(self):
        """桌面模式下 HOME 不被覆盖"""
        original_home = os.environ.get("HOME")
        # 模拟桌面模式
        os.environ["DESKTOP_MODE"] = "1"
        os.environ["DESKTOP_PROJECT_ROOT"] = str(BACKEND_DIR)
        os.environ["DESKTOP_DATA_DIR"] = str(BACKEND_DIR / "data")
        os.environ["DESKTOP_ENV_PATH"] = str(BACKEND_DIR / ".env")

        # 重新导入配置
        import importlib
        import app.config.config
        importlib.reload(app.config.config)

        # HOME 应该保持不变
        assert os.environ.get("HOME") == original_home

        # 清理
        del os.environ["DESKTOP_MODE"]
        del os.environ["DESKTOP_PROJECT_ROOT"]
        del os.environ["DESKTOP_DATA_DIR"]
        del os.environ["DESKTOP_ENV_PATH"]

    def test_default_database_url(self):
        """DATABASE_URL 有 SQLite 默认值"""
        from app.config.config import Settings
        field = Settings.model_fields['DATABASE_URL']
        assert field.default == "sqlite:///./data/tools.db"
        assert not field.is_required()


class TestSpaRoutes:
    """测试桌面模式 SPA 静态服务装配（setup_spa_routes）"""

    def _make_app_with_dist(self, tmp_path):
        """构建带 dist 目录与示例 API 路由的最小 FastAPI 应用"""
        from fastapi import FastAPI
        from desktop_app import setup_spa_routes

        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "index.html").write_text(
            "<html><body>TOOLBOX_SPA</body></html>", encoding="utf-8"
        )
        assets = dist / "assets"
        assets.mkdir()
        (assets / "app.js").write_text("console.log(1);", encoding="utf-8")

        app = FastAPI()

        @app.get("/api/v1/health")
        async def health():
            return {"status": "ok"}

        ok = setup_spa_routes(app, str(dist))
        return app, ok

    def test_setup_returns_true_with_valid_dist(self, tmp_path):
        app, ok = self._make_app_with_dist(tmp_path)
        assert ok is True

    def test_setup_returns_false_without_index(self, tmp_path):
        from fastapi import FastAPI
        from desktop_app import setup_spa_routes

        empty = tmp_path / "empty_dist"
        empty.mkdir()
        app = FastAPI()
        assert setup_spa_routes(app, str(empty)) is False

    def test_root_serves_index_html(self, tmp_path):
        """根路径必须返回前端页面而非 JSON（缺陷 1 回归）"""
        from fastapi.testclient import TestClient

        app, _ = self._make_app_with_dist(tmp_path)
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "TOOLBOX_SPA" in resp.text

    def test_read_root_json_route_removed(self, tmp_path):
        """endpoint 名为 read_root 的 JSON 根路由装配后被移除"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from desktop_app import setup_spa_routes

        dist = tmp_path / "dist2"
        dist.mkdir()
        (dist / "index.html").write_text("<html>SPA</html>", encoding="utf-8")

        app = FastAPI()

        @app.get("/")
        def read_root():
            return {"message": "Tool Aggregation API"}

        setup_spa_routes(app, str(dist))
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Tool Aggregation API" not in resp.text

    def test_api_route_still_works(self, tmp_path):
        """既有 API 路由优先于 catch-all，不受 SPA 装配影响"""
        from fastapi.testclient import TestClient

        app, _ = self._make_app_with_dist(tmp_path)
        client = TestClient(app)
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_unknown_api_path_404(self, tmp_path):
        """未知 API 路径显式 404 JSON，不做 SPA 兜底"""
        from fastapi.testclient import TestClient

        app, _ = self._make_app_with_dist(tmp_path)
        client = TestClient(app)
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404
        assert resp.headers["content-type"].startswith("application/json")

    def test_mcp_prefix_404(self, tmp_path):
        """mcp 前缀未知路径显式 404"""
        from fastapi.testclient import TestClient

        app, _ = self._make_app_with_dist(tmp_path)
        client = TestClient(app)
        resp = client.get("/mcp/nonexistent")
        assert resp.status_code == 404

    def test_static_file_served(self, tmp_path):
        """dist 内静态文件直出"""
        from fastapi.testclient import TestClient

        app, _ = self._make_app_with_dist(tmp_path)
        client = TestClient(app)
        resp = client.get("/assets/app.js")
        assert resp.status_code == 200
        assert "console.log(1);" in resp.text

    def test_missing_asset_with_extension_404(self, tmp_path):
        """带扩展名但缺失的资源显式 404（不回退 index.html）"""
        from fastapi.testclient import TestClient

        app, _ = self._make_app_with_dist(tmp_path)
        client = TestClient(app)
        resp = client.get("/assets/stale-chunk.js")
        assert resp.status_code == 404

    def test_deep_link_fallback_to_index(self, tmp_path):
        """BrowserRouter 深链接回退 index.html（缺陷 2 回归）"""
        from fastapi.testclient import TestClient

        app, _ = self._make_app_with_dist(tmp_path)
        client = TestClient(app)
        resp = client.get("/tools/token-usage")
        assert resp.status_code == 200
        assert "TOOLBOX_SPA" in resp.text

    def test_path_traversal_blocked(self, tmp_path):
        """路径穿越被阻断：dist 外文件不可读"""
        from fastapi.testclient import TestClient

        secret = tmp_path / "secret.txt"
        secret.write_text("TOP_SECRET", encoding="utf-8")
        app, _ = self._make_app_with_dist(tmp_path)
        client = TestClient(app)
        resp = client.get("/../secret.txt")
        assert "TOP_SECRET" not in resp.text
