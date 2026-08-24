"""
大模型模型管理路由（管理员）

提供 LLMModel 的 CRUD、设置全局/分类默认等管理端点。
调用 LLMModelService 完成业务逻辑。
"""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import get_db
from app.api.dependencies import get_current_user
from app.services.llm_model_service import LLMModelService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/llm-models", tags=["admin-llm-models"])


# ------------------------------------------------------------------
# 鉴权依赖
# ------------------------------------------------------------------

def require_admin(current_user: dict = Depends(get_current_user)):
    """要求管理员角色"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# ------------------------------------------------------------------
# Pydantic schemas
# ------------------------------------------------------------------

class ModelCreate(BaseModel):
    """创建模型请求"""
    name: str = Field(..., min_length=1, max_length=100)
    model_name: str = Field(..., min_length=1, max_length=100, description="模型标识，如 gpt-4o")
    provider_id: str = Field(..., description="供应商 ID")
    request_params: Optional[str] = Field(None, description="JSON 字符串格式的请求参数")
    category: str = Field(default="text", description="分类：text / vision / image_gen / voice / embedding / ocr")
    is_default: bool = False
    is_default_for_category: bool = False
    notes: Optional[str] = Field(None, max_length=500)
    is_active: bool = True


class ModelUpdate(BaseModel):
    """更新模型请求"""
    name: Optional[str] = Field(None, max_length=100)
    model_name: Optional[str] = Field(None, max_length=100)
    provider_id: Optional[str] = None
    request_params: Optional[str] = None
    category: Optional[str] = None
    is_default: Optional[bool] = None
    is_default_for_category: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class ModelResponse(BaseModel):
    """模型响应"""
    id: str
    name: str
    model_name: str
    provider_id: str
    provider_name: Optional[str] = None
    request_params: Optional[str] = None
    category: str
    is_default: bool
    is_default_for_category: bool
    notes: Optional[str]
    is_active: bool
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class SetDefaultRequest(BaseModel):
    """设置默认请求"""
    category: Optional[str] = Field(None, description="分类名，None 表示全局默认")


# ------------------------------------------------------------------
# 辅助函数
# ------------------------------------------------------------------

def _model_to_dict(m) -> dict:
    """将 SQLAlchemy 模型对象转换为字典"""
    # provider 通过 joined load 已加载
    provider_name = None
    if hasattr(m, "provider") and m.provider:
        provider_name = m.provider.name

    return {
        "id": str(m.id),
        "name": m.name,
        "model_name": m.model_name,
        "provider_id": str(m.provider_id),
        "provider_name": provider_name,
        "request_params": m.request_params,
        "category": m.category or "text",
        "is_default": m.is_default,
        "is_default_for_category": m.is_default_for_category,
        "notes": m.notes,
        "is_active": m.is_active,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


# ------------------------------------------------------------------
# 端点
# ------------------------------------------------------------------

@router.get("", response_model=List[ModelResponse])
async def list_models(
    category: Optional[str] = None,
    provider_id: Optional[str] = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """获取模型列表"""
    svc = LLMModelService(db)
    models = svc.list_models(category=category, provider_id=provider_id, active_only=active_only)
    return [_model_to_dict(m) for m in models]


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    body: ModelCreate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """新建模型"""
    svc = LLMModelService(db)
    m = svc.create_model(
        name=body.name,
        model_name=body.model_name,
        provider_id=body.provider_id,
        request_params=body.request_params,
        category=body.category,
        is_default=body.is_default,
        is_default_for_category=body.is_default_for_category,
        notes=body.notes,
        is_active=body.is_active,
    )
    return _model_to_dict(m)


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """获取单个模型详情"""
    svc = LLMModelService(db)
    m = svc.get_model(model_id)
    if not m:
        raise HTTPException(status_code=404, detail="模型不存在")
    return _model_to_dict(m)


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: str,
    body: ModelUpdate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """更新模型"""
    svc = LLMModelService(db)
    update_data = {k: v for k, v in body.dict().items() if v is not None}
    m = svc.update_model(model_id, **update_data)
    if not m:
        raise HTTPException(status_code=404, detail="模型不存在")
    return _model_to_dict(m)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """删除模型"""
    svc = LLMModelService(db)
    ok = svc.delete_model(model_id)
    if not ok:
        raise HTTPException(status_code=404, detail="模型不存在")
    return None


@router.post("/{model_id}/set-default")
async def set_default_model(
    model_id: str,
    body: SetDefaultRequest = SetDefaultRequest(),
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """设置模型为默认（全局或分类）"""
    svc = LLMModelService(db)
    ok = svc.set_default(model_id, category=body.category)
    if not ok:
        raise HTTPException(status_code=404, detail="模型不存在")
    return {"message": "已设为默认", "model_id": model_id, "category": body.category}
