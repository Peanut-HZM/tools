"""
大模型供应商管理路由（管理员）

提供 LLMProvider 的 CRUD、连通性测试、API Key 明文揭示等管理端点。
调用 LLMProviderService 完成业务逻辑。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import get_db
from app.api.dependencies import get_current_user
from app.services.llm_provider_service import LLMProviderService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/llm-providers", tags=["admin-llm-providers"])


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

class ProviderCreate(BaseModel):
    """创建供应商请求"""
    name: str = Field(..., min_length=1, max_length=100)
    provider_type: str = Field(..., max_length=50, description="供应商类型：openai/anthropic/azure_openai/baidu/aliyun/other")
    base_url: str = Field(..., max_length=500)
    api_key: str = Field(..., description="API Key 明文，后端加密存储")
    notes: Optional[str] = Field(None, max_length=500)
    is_active: bool = True


class ProviderUpdate(BaseModel):
    """更新供应商请求"""
    name: Optional[str] = Field(None, max_length=100)
    provider_type: Optional[str] = Field(None, max_length=50)
    base_url: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = Field(None, description="API Key 明文，留空不修改")
    notes: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class ProviderResponse(BaseModel):
    """供应商响应"""
    id: str
    name: str
    provider_type: str
    base_url: str
    api_key_suffix: Optional[str]
    notes: Optional[str]
    is_active: bool
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class TestConnectionResponse(BaseModel):
    """连通性测试结果"""
    success: bool
    message: str
    latency_ms: int


class RevealResponse(BaseModel):
    """API Key 明文揭示"""
    api_key: str


# ------------------------------------------------------------------
# 辅助函数
# ------------------------------------------------------------------

def _provider_to_dict(p) -> dict:
    """将 SQLAlchemy 对象转换为字典"""
    return {
        "id": str(p.id),
        "name": p.name,
        "provider_type": p.provider_type,
        "base_url": p.base_url,
        "api_key_suffix": p.api_key_suffix,
        "notes": p.notes,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


# ------------------------------------------------------------------
# 端点
# ------------------------------------------------------------------

@router.get("", response_model=List[ProviderResponse])
async def list_providers(
    active_only: bool = False,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """获取供应商列表"""
    svc = LLMProviderService(db)
    providers = svc.list_providers(active_only=active_only)
    return [_provider_to_dict(p) for p in providers]


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    body: ProviderCreate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """新建供应商"""
    svc = LLMProviderService(db)
    try:
        p = svc.create_provider(
            name=body.name,
            provider_type=body.provider_type,
            base_url=body.base_url,
            api_key=body.api_key,
            notes=body.notes,
            is_active=body.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        # api_key_hash unique 约束冲突
        db.rollback()
        raise HTTPException(status_code=400, detail="provider with this api_key already exists")
    return _provider_to_dict(p)


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """获取单个供应商详情"""
    svc = LLMProviderService(db)
    p = svc.get_provider(provider_id)
    if not p:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return _provider_to_dict(p)


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: str,
    body: ProviderUpdate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """更新供应商"""
    svc = LLMProviderService(db)
    update_data = {k: v for k, v in body.dict().items() if v is not None}
    try:
        p = svc.update_provider(provider_id, **update_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="provider with this api_key already exists")
    if not p:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return _provider_to_dict(p)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """删除供应商"""
    svc = LLMProviderService(db)
    try:
        ok = svc.delete_provider(provider_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return None


@router.post("/{provider_id}/toggle")
async def toggle_provider(
    provider_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """切换供应商启用/禁用状态"""
    svc = LLMProviderService(db)
    p = svc.get_provider(provider_id)
    if not p:
        raise HTTPException(status_code=404, detail="供应商不存在")
    svc.set_active(provider_id, not p.is_active)
    return {"id": str(p.id), "is_active": not p.is_active}


@router.post("/{provider_id}/test", response_model=TestConnectionResponse)
async def test_provider_connection(
    provider_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """测试供应商连通性"""
    svc = LLMProviderService(db)
    ok, msg, latency = await svc.test_connection(provider_id)
    return TestConnectionResponse(success=ok, message=msg, latency_ms=latency)


@router.post("/{provider_id}/reveal", response_model=RevealResponse)
async def reveal_provider_key(
    provider_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """揭示供应商 API Key 明文（仅管理员）"""
    svc = LLMProviderService(db)
    key = svc.reveal_api_key(provider_id)
    if key is None:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return RevealResponse(api_key=key)
