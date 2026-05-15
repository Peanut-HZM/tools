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
