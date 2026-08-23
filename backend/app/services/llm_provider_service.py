"""
大模型供应商服务（spec §16.5）

提供 LLMProvider 的 CRUD、启用/禁用、API Key 加解密、连通性测试等能力。
供 Task 1.5.4 的 admin API 以及前端页面调用。
"""

import logging
import time
import uuid as _uuid_mod
from typing import List, Optional, Tuple, Union

from sqlalchemy.orm import Session

from app.core.security import decrypt_api_key, encrypt_api_key
from app.models.llm_provider import LLMProvider
from app.services.llm.factory import get_provider

logger = logging.getLogger(__name__)

# ID 既可能是 UUID 对象，也可能是字符串（API 入口通常是字符串）
ID_LIKE = Union[str, _uuid_mod.UUID]


def _to_uuid(value: ID_LIKE) -> _uuid_mod.UUID:
    """统一把 str / UUID 转换为 UUID 对象"""
    if isinstance(value, _uuid_mod.UUID):
        return value
    return _uuid_mod.UUID(str(value))


class LLMProviderService:
    """LLM 供应商服务"""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def list_providers(self, active_only: bool = False) -> List[LLMProvider]:
        """列出供应商（可按活跃状态过滤）"""
        q = self.db.query(LLMProvider)
        if active_only:
            q = q.filter(LLMProvider.is_active == True)  # noqa: E712
        return q.order_by(LLMProvider.created_at.desc()).all()

    def get_provider(self, provider_id: ID_LIKE) -> Optional[LLMProvider]:
        """按 ID 查询单个供应商"""
        return self.db.query(LLMProvider).filter(LLMProvider.id == _to_uuid(provider_id)).first()

    # ------------------------------------------------------------------
    # 创建 / 更新
    # ------------------------------------------------------------------

    def create_provider(
        self,
        name: str,
        provider_type: str,
        base_url: str,
        api_key: str,
        notes: Optional[str] = None,
        is_active: bool = True,
    ) -> LLMProvider:
        """
        新建供应商。
        api_key 以明文传入，内部加密后存入 api_key_encrypted 字段；
        同时记录 api_key_suffix（末 4 位）便于人工识别。
        """
        p = LLMProvider(
            name=name,
            provider_type=provider_type,
            base_url=base_url,
            api_key_encrypted=encrypt_api_key(api_key),
            api_key_suffix=api_key[-4:] if len(api_key) >= 4 else api_key,
            notes=notes,
            is_active=is_active,
        )
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        logger.info("新建 LLMProvider: id=%s name=%s type=%s", p.id, p.name, p.provider_type)
        return p

    def update_provider(self, provider_id: ID_LIKE, **kwargs) -> Optional[LLMProvider]:
        """
        更新供应商字段。
        若 kwargs 包含 `api_key`（明文），则同步更新加密字段和 suffix。
        """
        p = self.get_provider(provider_id)
        if not p:
            return None

        # 单独处理 api_key：明文 → 加密 + suffix
        if "api_key" in kwargs:
            api_key = kwargs.pop("api_key")
            kwargs["api_key_encrypted"] = encrypt_api_key(api_key)
            kwargs["api_key_suffix"] = api_key[-4:] if len(api_key) >= 4 else api_key

        for k, v in kwargs.items():
            if hasattr(p, k):
                setattr(p, k, v)

        self.db.commit()
        self.db.refresh(p)
        logger.info("更新 LLMProvider: id=%s fields=%s", p.id, list(kwargs.keys()))
        return p

    def set_active(self, provider_id: ID_LIKE, is_active: bool) -> Optional[LLMProvider]:
        """启用 / 禁用供应商"""
        return self.update_provider(provider_id, is_active=is_active)

    # ------------------------------------------------------------------
    # 删除
    # ------------------------------------------------------------------

    def delete_provider(self, provider_id: ID_LIKE) -> bool:
        """
        删除供应商。
        若有 LLMModel 关联则拒绝删除（抛 ValueError），需先清理/迁移子记录。
        """
        # 延迟导入避免循环依赖
        from app.models.llm_model import LLMModel

        pid = _to_uuid(provider_id)
        linked = self.db.query(LLMModel).filter(LLMModel.provider_id == pid).count()
        if linked > 0:
            raise ValueError(f"存在关联模型 {linked} 条，请先删除/迁移")

        p = self.get_provider(pid)
        if not p:
            return False
        self.db.delete(p)
        self.db.commit()
        logger.info("删除 LLMProvider: id=%s", provider_id)
        return True

    # ------------------------------------------------------------------
    # 业务辅助
    # ------------------------------------------------------------------

    def reveal_api_key(self, provider_id: ID_LIKE) -> Optional[str]:
        """解密并返回 API Key 明文（admin 专用）"""
        p = self.get_provider(provider_id)
        if not p:
            return None
        return decrypt_api_key(p.api_key_encrypted)

    async def test_connection(self, provider_id: ID_LIKE) -> Tuple[bool, str, int]:
        """
        测试供应商连通性。
        返回 (ok, message, latency_ms)。
        """
        p = self.get_provider(provider_id)
        if not p:
            return False, "供应商不存在", 0
        try:
            api_key = decrypt_api_key(p.api_key_encrypted)
        except Exception as e:
            logger.warning("解密 API Key 失败: provider=%s err=%s", provider_id, e)
            return False, f"API Key 解密失败: {e}", 0

        try:
            # 使用一个占位模型名进行连通测试
            adapter = get_provider(p.provider_type, api_key, p.base_url, "test-model")
            start = time.time()
            ok, err = await adapter.test_connection()
            latency = int((time.time() - start) * 1000)
            logger.info(
                "连通性测试: provider=%s ok=%s latency=%dms", provider_id, ok, latency
            )
            return ok, err, latency
        except Exception as e:
            logger.warning("连通性测试异常: provider=%s err=%s", provider_id, e)
            return False, str(e), 0
