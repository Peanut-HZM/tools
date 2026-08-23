"""
Task 2.1 — DifyConfigService 分层配置管理 单元测试

使用 SQLite 内存 DB，每个用例一个干净 session。
覆盖范围：
  ✓ .env 全有 → 返回 .env 值（DB 无记录）
  ✓ DB 部分 key 覆盖 → DB 优先，其他回退 .env
  ✓ DB 全部覆盖 → 全用 DB
  ✓ 空字符串 / None 视为"未配置" → 回退 .env
  ✓ update_config 加密存储到 DB
  ✓ get_config_view 不暴露明文 API key
  ✓ test_connection 调 Dify /info 验证连通
  ✓ 解密失败时跳过该行、不抛异常
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.image_generation_models import ImageGenDifyConfig
from app.core.security import encrypt_api_key

# 确保 backend 目录在 sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.dify_config_service import DifyConfigService, DifyConfig


# ------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------

@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def svc(db_session):
    return DifyConfigService(db=db_session)


def _seed(db_session, key: str, plaintext: str, updated_by: str = "test"):
    """辅助：向 DB 插入一条加密配置"""
    db_session.add(ImageGenDifyConfig(
        key=key,
        value_encrypted=encrypt_api_key(plaintext),
        updated_by=updated_by,
    ))
    db_session.commit()


# ============================================================
# get_config — 分层回退
# ============================================================

class TestGetConfigEnvFallback:
    """DB 无记录 → 全部回退 .env"""

    def test_all_from_env(self, svc):
        with patch("app.services.dify_config_service.settings") as mock_settings:
            mock_settings.DIFY_API_URL = "https://env.example.com/v1"
            mock_settings.DIFY_APP_API_KEY = "env-app-key"
            mock_settings.DIFY_WORKFLOW_TEXT2IMG = "wf-text2img"
            mock_settings.DIFY_WORKFLOW_IMG2IMG = "wf-img2img"
            mock_settings.DIFY_WORKFLOW_INPAINT = "wf-inpaint"
            mock_settings.DIFY_WORKFLOW_UPLOAD_EDIT = "wf-upload-edit"
            mock_settings.DIFY_DEFAULT_TIMEOUT = 120.0

            cfg = svc.get_config()

        assert cfg.api_url == "https://env.example.com/v1"
        assert cfg.app_api_key == "env-app-key"
        assert cfg.workflow_text2img == "wf-text2img"
        assert cfg.workflow_img2img == "wf-img2img"
        assert cfg.workflow_inpaint == "wf-inpaint"
        assert cfg.workflow_upload_edit == "wf-upload-edit"
        assert cfg.default_timeout == 120.0


class TestGetConfigDbOverride:
    """DB 部分 key 覆盖 → DB 优先，其他回退 .env"""

    def test_partial_db_override(self, svc, db_session):
        # 只覆盖 api_url 和 app_api_key
        _seed(db_session, "api_url", "https://db.example.com/v1")
        _seed(db_session, "app_api_key", "db-app-key")

        with patch("app.services.dify_config_service.settings") as mock_settings:
            mock_settings.DIFY_API_URL = "https://env.example.com/v1"
            mock_settings.DIFY_APP_API_KEY = "env-app-key"
            mock_settings.DIFY_WORKFLOW_TEXT2IMG = "wf-text2img"
            mock_settings.DIFY_WORKFLOW_IMG2IMG = "wf-img2img"
            mock_settings.DIFY_WORKFLOW_INPAINT = "wf-inpaint"
            mock_settings.DIFY_WORKFLOW_UPLOAD_EDIT = "wf-upload-edit"
            mock_settings.DIFY_DEFAULT_TIMEOUT = 60.0

            cfg = svc.get_config()

        # DB 覆盖
        assert cfg.api_url == "https://db.example.com/v1"
        assert cfg.app_api_key == "db-app-key"
        # 其余回退 .env
        assert cfg.workflow_text2img == "wf-text2img"
        assert cfg.workflow_img2img == "wf-img2img"
        assert cfg.workflow_inpaint == "wf-inpaint"
        assert cfg.workflow_upload_edit == "wf-upload-edit"
        assert cfg.default_timeout == 60.0

    def test_full_db_override(self, svc, db_session):
        """DB 全部覆盖"""
        _seed(db_session, "api_url", "https://db.example.com/v1")
        _seed(db_session, "app_api_key", "db-app-key")
        _seed(db_session, "workflow_text2img", "db-wf-t2i")
        _seed(db_session, "workflow_img2img", "db-wf-i2i")
        _seed(db_session, "workflow_inpaint", "db-wf-inpaint")
        _seed(db_session, "workflow_upload_edit", "db-wf-upload")
        _seed(db_session, "default_timeout", "180")

        with patch("app.services.dify_config_service.settings") as mock_settings:
            mock_settings.DIFY_API_URL = "https://env.example.com/v1"
            mock_settings.DIFY_APP_API_KEY = "env-app-key"
            mock_settings.DIFY_WORKFLOW_TEXT2IMG = "env-wf-t2i"
            mock_settings.DIFY_WORKFLOW_IMG2IMG = "env-wf-i2i"
            mock_settings.DIFY_WORKFLOW_INPAINT = "env-wf-inpaint"
            mock_settings.DIFY_WORKFLOW_UPLOAD_EDIT = "env-wf-upload"
            mock_settings.DIFY_DEFAULT_TIMEOUT = 60.0

            cfg = svc.get_config()

        assert cfg.api_url == "https://db.example.com/v1"
        assert cfg.app_api_key == "db-app-key"
        assert cfg.workflow_text2img == "db-wf-t2i"
        assert cfg.workflow_img2img == "db-wf-i2i"
        assert cfg.workflow_inpaint == "db-wf-inpaint"
        assert cfg.workflow_upload_edit == "db-wf-upload"
        assert cfg.default_timeout == 180.0


class TestGetConfigEmptyStrings:
    """空字符串 / None 视为未配置 → 回退 .env"""

    def test_empty_string_falls_back(self, svc, db_session):
        _seed(db_session, "api_url", "")
        _seed(db_session, "app_api_key", "db-key")

        with patch("app.services.dify_config_service.settings") as mock_settings:
            mock_settings.DIFY_API_URL = "https://env.example.com/v1"
            mock_settings.DIFY_APP_API_KEY = "env-key"
            mock_settings.DIFY_WORKFLOW_TEXT2IMG = "wf-t2i"
            mock_settings.DIFY_WORKFLOW_IMG2IMG = "wf-i2i"
            mock_settings.DIFY_WORKFLOW_INPAINT = "wf-inpaint"
            mock_settings.DIFY_WORKFLOW_UPLOAD_EDIT = "wf-upload"
            mock_settings.DIFY_DEFAULT_TIMEOUT = 60.0

            cfg = svc.get_config()

        # 空字符串视为未配置，回退 .env
        assert cfg.api_url == "https://env.example.com/v1"
        # 非空字符串使用 DB
        assert cfg.app_api_key == "db-key"


class TestGetConfigDecryptFailure:
    """解密失败时跳过该行，不影响其他 key"""

    def test_decrypt_failure_skips_row(self, svc, db_session):
        # 插入一条密文损坏的记录
        db_session.add(ImageGenDifyConfig(
            key="api_url",
            value_encrypted="not-valid-encrypted-data",
            updated_by="test",
        ))
        _seed(db_session, "app_api_key", "db-key")
        db_session.commit()

        with patch("app.services.dify_config_service.settings") as mock_settings:
            mock_settings.DIFY_API_URL = "https://env.example.com/v1"
            mock_settings.DIFY_APP_API_KEY = "env-key"
            mock_settings.DIFY_WORKFLOW_TEXT2IMG = "wf-t2i"
            mock_settings.DIFY_WORKFLOW_IMG2IMG = "wf-i2i"
            mock_settings.DIFY_WORKFLOW_INPAINT = "wf-inpaint"
            mock_settings.DIFY_WORKFLOW_UPLOAD_EDIT = "wf-upload"
            mock_settings.DIFY_DEFAULT_TIMEOUT = 60.0

            cfg = svc.get_config()

        # 解密失败的 api_url 回退 .env
        assert cfg.api_url == "https://env.example.com/v1"
        # 其他正常
        assert cfg.app_api_key == "db-key"


# ============================================================
# update_config
# ============================================================

class TestUpdateConfig:
    def test_update_config_inserts_new_keys(self, svc, db_session):
        svc.update_config(
            {"api_url": "https://new.example.com/v1", "app_api_key": "new-key"},
            updated_by="admin",
        )
        rows = db_session.query(ImageGenDifyConfig).all()
        assert len(rows) == 2
        keys = {r.key for r in rows}
        assert keys == {"api_url", "app_api_key"}

    def test_update_config_overwrites_existing(self, svc, db_session):
        _seed(db_session, "api_url", "https://old.example.com/v1")

        svc.update_config({"api_url": "https://new.example.com/v1"}, updated_by="admin")

        rows = db_session.query(ImageGenDifyConfig).filter(
            ImageGenDifyConfig.key == "api_url"
        ).all()
        assert len(rows) == 1
        # 验证更新后的值能正确解密
        from app.core.security import decrypt_api_key
        assert decrypt_api_key(rows[0].value_encrypted) == "https://new.example.com/v1"
        assert rows[0].updated_by == "admin"

    def test_update_config_skips_none_values(self, svc, db_session):
        _seed(db_session, "api_url", "https://keep.example.com/v1")

        svc.update_config(
            {"api_url": None, "app_api_key": "new-key"},
            updated_by="admin",
        )

        from app.core.security import decrypt_api_key
        row = db_session.query(ImageGenDifyConfig).filter(
            ImageGenDifyConfig.key == "api_url"
        ).first()
        assert decrypt_api_key(row.value_encrypted) == "https://keep.example.com/v1"


# ============================================================
# get_config_view — 不暴露明文 API key
# ============================================================

class TestGetConfigView:
    def test_api_key_not_exposed(self, svc, db_session):
        _seed(db_session, "api_url", "https://db.example.com/v1")
        _seed(db_session, "app_api_key", "super-secret-key")

        with patch("app.services.dify_config_service.settings") as mock_settings:
            mock_settings.DIFY_API_URL = ""
            mock_settings.DIFY_APP_API_KEY = ""
            mock_settings.DIFY_WORKFLOW_TEXT2IMG = ""
            mock_settings.DIFY_WORKFLOW_IMG2IMG = ""
            mock_settings.DIFY_WORKFLOW_INPAINT = ""
            mock_settings.DIFY_WORKFLOW_UPLOAD_EDIT = ""
            mock_settings.DIFY_DEFAULT_TIMEOUT = 60.0

            view = svc.get_config_view()

        assert "super-secret-key" not in str(view)
        assert view["is_api_key_set"] is True
        assert view["api_url"] == "https://db.example.com/v1"

    def test_api_key_not_set_flag(self, svc):
        with patch("app.services.dify_config_service.settings") as mock_settings:
            mock_settings.DIFY_API_URL = ""
            mock_settings.DIFY_APP_API_KEY = ""
            mock_settings.DIFY_WORKFLOW_TEXT2IMG = ""
            mock_settings.DIFY_WORKFLOW_IMG2IMG = ""
            mock_settings.DIFY_WORKFLOW_INPAINT = ""
            mock_settings.DIFY_WORKFLOW_UPLOAD_EDIT = ""
            mock_settings.DIFY_DEFAULT_TIMEOUT = 60.0

            view = svc.get_config_view()

        assert view["is_api_key_set"] is False


# ============================================================
# test_connection — 调 Dify /info 验证连通
# ============================================================

class TestTestConnection:
    def test_connection_success(self, svc):
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = MagicMock()
        mock_client.get = MagicMock(return_value=mock_resp)
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.services.dify_config_service.settings") as mock_settings, \
             patch("httpx.Client", return_value=mock_client):
            mock_settings.DIFY_API_URL = "https://dify.example.com/v1"
            mock_settings.DIFY_APP_API_KEY = "test-key"
            mock_settings.DIFY_WORKFLOW_TEXT2IMG = ""
            mock_settings.DIFY_WORKFLOW_IMG2IMG = ""
            mock_settings.DIFY_WORKFLOW_INPAINT = ""
            mock_settings.DIFY_WORKFLOW_UPLOAD_EDIT = ""
            mock_settings.DIFY_DEFAULT_TIMEOUT = 60.0

            ok, msg = svc.test_connection()

        assert ok is True

    def test_connection_missing_config(self, svc):
        with patch("app.services.dify_config_service.settings") as mock_settings:
            mock_settings.DIFY_API_URL = ""
            mock_settings.DIFY_APP_API_KEY = ""
            mock_settings.DIFY_WORKFLOW_TEXT2IMG = ""
            mock_settings.DIFY_WORKFLOW_IMG2IMG = ""
            mock_settings.DIFY_WORKFLOW_INPAINT = ""
            mock_settings.DIFY_WORKFLOW_UPLOAD_EDIT = ""
            mock_settings.DIFY_DEFAULT_TIMEOUT = 60.0

            ok, msg = svc.test_connection()

        assert ok is False
        assert "配置不完整" in msg
