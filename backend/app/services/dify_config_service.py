"""
Dify 配置服务 - 分层配置管理（DB 优先，.env 兜底）

优先级：DB 表 image_gen_dify_config > .env 环境变量 (settings.DIFY_*)
- DB 中 value_encrypted 字段以 AES-256-GCM 加密存储
- 空字符串视为"未配置"，回退到 .env 默认值
- 解密失败的行会跳过并记录日志，不影响其他 key
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.config import settings
from app.models.image_generation_models import ImageGenDifyConfig
from app.core.security import encrypt_api_key, decrypt_api_key

logger = logging.getLogger(__name__)


@dataclass
class DifyConfig:
    """Dify 完整运行配置（供 DifyClient 直接使用）"""
    api_url: str
    app_api_key: str
    workflow_text2img: str
    workflow_img2img: str
    workflow_inpaint: str
    workflow_upload_edit: str
    default_timeout: float


# 配置 key → settings 属性名 映射表
_ENV_MAP = {
    "api_url": "DIFY_API_URL",
    "app_api_key": "DIFY_APP_API_KEY",
    "workflow_text2img": "DIFY_WORKFLOW_TEXT2IMG",
    "workflow_img2img": "DIFY_WORKFLOW_IMG2IMG",
    "workflow_inpaint": "DIFY_WORKFLOW_INPAINT",
    "workflow_upload_edit": "DIFY_WORKFLOW_UPLOAD_EDIT",
    "default_timeout": "DIFY_DEFAULT_TIMEOUT",
}


class DifyConfigService:
    """
    分层配置服务：DB 优先，.env 兜底。

    用法：
        svc = DifyConfigService(db)
        cfg = svc.get_config()         # 返回 DifyConfig
        svc.update_config({...}, "admin")  # 加密写入 DB
    """

    def __init__(self, db: Optional[Session] = None):
        self._db = db

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------

    def get_config(self) -> DifyConfig:
        """
        获取完整 Dify 配置。
        对每个 key：若 DB 有非空值则用 DB，否则回退到 settings (即 .env)。
        """
        db_cfg = self._load_db_config()

        def _resolve(key: str, cast=float):
            """优先取 DB 值，空字符串视为未配置，回退 .env"""
            db_val = db_cfg.get(key)
            if db_val is not None and db_val != "":
                return cast(db_val)
            env_attr = _ENV_MAP[key]
            return cast(getattr(settings, env_attr))

        return DifyConfig(
            api_url=_resolve("api_url", cast=str),
            app_api_key=_resolve("app_api_key", cast=str),
            workflow_text2img=_resolve("workflow_text2img", cast=str),
            workflow_img2img=_resolve("workflow_img2img", cast=str),
            workflow_inpaint=_resolve("workflow_inpaint", cast=str),
            workflow_upload_edit=_resolve("workflow_upload_edit", cast=str),
            default_timeout=_resolve("default_timeout", cast=float),
        )

    def _load_db_config(self) -> Dict[str, str]:
        """从 DB 读取所有 key-value，解密失败则跳过该行"""
        db = self._get_session()
        owns_session = db is not self._db  # 自动创建的 session 需自行关闭
        try:
            result: Dict[str, str] = {}
            rows = db.execute(select(ImageGenDifyConfig)).scalars().all()
            for row in rows:
                try:
                    result[row.key] = decrypt_api_key(row.value_encrypted)
                except Exception as e:
                    logger.error(
                        "[image-gen-config] 解密失败 key=%s: %s", row.key, e
                    )
            return result
        finally:
            if owns_session:
                db.close()

    def _get_session(self) -> Session:
        """若构造时未传入 db，则临时创建并返回一个 session"""
        if self._db:
            return self._db
        from app.db.database import get_db_connection
        # 复用项目已有的 psycopg2 连接 → 包装成 SQLAlchemy session
        # 但为简单起见，这里用独立的 SQLite/PG session
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(settings.DATABASE_URL)
        Session = sessionmaker(bind=engine)
        return Session()

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------

    def update_config(self, partial: dict, updated_by: str) -> None:
        """
        部分更新 DB 配置。
        - None 值跳过（不修改）
        - 已存在的 key 更新密文 + updated_by
        - 新 key 插入新行
        """
        db = self._get_session()
        owns_session = db is not self._db
        try:
            for key, value in partial.items():
                if value is None:
                    continue
                encrypted = encrypt_api_key(str(value))
                existing = db.execute(
                    select(ImageGenDifyConfig).where(ImageGenDifyConfig.key == key)
                ).scalar_one_or_none()
                if existing:
                    existing.value_encrypted = encrypted
                    existing.updated_by = updated_by
                else:
                    db.add(ImageGenDifyConfig(
                        key=key,
                        value_encrypted=encrypted,
                        updated_by=updated_by,
                    ))
            db.commit()
            logger.info(
                "[image-gen-config] 更新配置 key=%s by=%s",
                list(partial.keys()), updated_by,
            )
        finally:
            if owns_session:
                db.close()

    # ------------------------------------------------------------------
    # 视图（供前端，不暴露明文 API key）
    # ------------------------------------------------------------------

    def get_config_view(self) -> dict:
        """返回给前端的配置视图，API key 只返回是否已设置"""
        cfg = self.get_config()
        return {
            "api_url": cfg.api_url,
            "is_api_key_set": bool(cfg.app_api_key),
            "workflow_text2img": cfg.workflow_text2img,
            "workflow_img2img": cfg.workflow_img2img,
            "workflow_inpaint": cfg.workflow_inpaint,
            "workflow_upload_edit": cfg.workflow_upload_edit,
            "default_timeout": cfg.default_timeout,
        }

    # ------------------------------------------------------------------
    # 连通性测试
    # ------------------------------------------------------------------

    def test_connection(self) -> tuple:
        """
        测试 Dify 连通性（调用 {api_url}/info）。
        返回 (ok: bool, message: str)。
        """
        cfg = self.get_config()
        if not cfg.api_url or not cfg.app_api_key:
            return False, "配置不完整"
        import httpx
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    f"{cfg.api_url}/info",
                    headers={"Authorization": f"Bearer {cfg.app_api_key}"},
                )
                if resp.status_code == 200:
                    return True, "连接成功"
                return False, f"HTTP {resp.status_code}"
        except Exception as e:
            logger.warning("[image-gen-config] 连通性测试失败: %s", e)
            return False, str(e)
