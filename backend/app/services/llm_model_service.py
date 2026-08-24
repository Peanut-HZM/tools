"""
大模型模型服务（spec §16.5）

提供 LLMModel 的 CRUD、全局默认 / 分类默认切换、按条件查询等能力。
供 Task 1.5.4 的 admin API 以及前端页面调用。

「默认」语义：
- is_default：全局唯一默认模型（下拉框首选）
- is_default_for_category：同一 category 下的默认模型
设置任一 default 开关时，需把同类其他记录的对应开关清为 False。
"""

import logging
import uuid as _uuid_mod
from typing import List, Optional, Union

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.llm_model import LLMModel

logger = logging.getLogger(__name__)

ID_LIKE = Union[str, _uuid_mod.UUID]


def _to_uuid(value: ID_LIKE) -> _uuid_mod.UUID:
    if isinstance(value, _uuid_mod.UUID):
        return value
    return _uuid_mod.UUID(str(value))


class LLMModelService:
    """LLM 模型服务"""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def list_models(
        self,
        category: Optional[str] = None,
        provider_id: Optional[ID_LIKE] = None,
        active_only: bool = False,
    ) -> List[LLMModel]:
        """按条件列出模型"""
        q = self.db.query(LLMModel)
        if active_only:
            q = q.filter(LLMModel.is_active == True)  # noqa: E712
        if category:
            q = q.filter(LLMModel.category == category)
        if provider_id:
            q = q.filter(LLMModel.provider_id == _to_uuid(provider_id))
        return q.order_by(LLMModel.created_at.desc()).all()

    def get_model(self, model_id: ID_LIKE) -> Optional[LLMModel]:
        """按 ID 查询单个模型"""
        return self.db.query(LLMModel).filter(LLMModel.id == _to_uuid(model_id)).first()

    def get_default_model(self, category: Optional[str] = None) -> Optional[LLMModel]:
        """
        获取默认模型。
        - category 为 None → 返回全局默认（is_default=True 且 is_active=True）
        - category 非 None → 返回该分类下的默认（is_default_for_category=True 且 is_active=True）
        """
        q = self.db.query(LLMModel).filter(LLMModel.is_active == True)  # noqa: E712
        if category:
            q = q.filter(
                and_(
                    LLMModel.category == category,
                    LLMModel.is_default_for_category == True,  # noqa: E712
                )
            )
        else:
            q = q.filter(LLMModel.is_default == True)  # noqa: E712
        return q.first()

    def list_by_provider(self, provider_id: ID_LIKE) -> List[LLMModel]:
        """列出某供应商下的所有模型"""
        return self.list_models(provider_id=provider_id)

    def list_by_category(self, category: str, active_only: bool = False) -> List[LLMModel]:
        """列出某分类下的所有模型"""
        return self.list_models(category=category, active_only=active_only)

    # ------------------------------------------------------------------
    # 创建 / 更新
    # ------------------------------------------------------------------

    def create_model(
        self,
        name: str,
        model_name: str,
        provider_id: ID_LIKE,
        request_params: Optional[str] = None,
        category: str = "text",
        is_default: bool = False,
        is_default_for_category: bool = False,
        notes: Optional[str] = None,
        is_active: bool = True,
    ) -> LLMModel:
        """
        新建模型。
        若设置 is_default / is_default_for_category，会先把同类其他记录的对应开关清 False。
        """
        # 先清理冲突的 default
        if is_default:
            self._unset_default_models()
        if is_default_for_category:
            self._unset_category_defaults(category)

        m = LLMModel(
            name=name,
            model_name=model_name,
            provider_id=_to_uuid(provider_id),
            request_params=request_params,
            category=category,
            is_default=is_default,
            is_default_for_category=is_default_for_category,
            notes=notes,
            is_active=is_active,
        )
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        logger.info(
            "新建 LLMModel: id=%s name=%s model=%s category=%s",
            m.id, m.name, m.model_name, m.category,
        )
        return m

    def update_model(self, model_id: ID_LIKE, **kwargs) -> Optional[LLMModel]:
        """
        更新模型字段。
        若 is_default / is_default_for_category 切换为 True，先清理同类冲突。
        """
        m = self.get_model(model_id)
        if not m:
            return None

        # 注意：必须先清理再赋值，否则 update 语句会把新记录也清掉
        if kwargs.get("is_default"):
            self._unset_default_models()
        if kwargs.get("is_default_for_category"):
            # 使用 m.category（当前记录的分类）作为清理范围
            self._unset_category_defaults(m.category)

        for k, v in kwargs.items():
            if hasattr(m, k):
                setattr(m, k, v)

        self.db.commit()
        self.db.refresh(m)
        logger.info("更新 LLMModel: id=%s fields=%s", m.id, list(kwargs.keys()))
        return m

    # ------------------------------------------------------------------
    # 默认切换
    # ------------------------------------------------------------------

    def set_default(self, model_id: ID_LIKE, category: Optional[str] = None) -> bool:
        """
        将某模型设为默认。
        - category 为 None → 设为全局默认（清其他 is_default）
        - category 非 None → 设为该分类默认（清同 category 其他 is_default_for_category）
        """
        m = self.get_model(model_id)
        if not m:
            return False

        if category:
            self._unset_category_defaults(category)
            m.is_default_for_category = True
            m.category = category
        else:
            self._unset_default_models()
            m.is_default = True

        self.db.commit()
        logger.info("设置默认: model=%s category=%s", model_id, category)
        return True

    # ------------------------------------------------------------------
    # 删除
    # ------------------------------------------------------------------

    def delete_model(self, model_id: ID_LIKE) -> bool:
        """删除模型"""
        m = self.get_model(model_id)
        if not m:
            return False
        self.db.delete(m)
        self.db.commit()
        logger.info("删除 LLMModel: id=%s", model_id)
        return True

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _unset_default_models(self) -> None:
        """把所有模型的全局 is_default 清为 False（由外层统一 commit）"""
        self.db.query(LLMModel).filter(
            LLMModel.is_default == True  # noqa: E712
        ).update({"is_default": False})

    def _unset_category_defaults(self, category: str) -> None:
        """把指定分类下的 is_default_for_category 清为 False（由外层统一 commit）"""
        self.db.query(LLMModel).filter(
            LLMModel.category == category,
            LLMModel.is_default_for_category == True,  # noqa: E712
        ).update({"is_default_for_category": False})
