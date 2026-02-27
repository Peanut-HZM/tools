"""
LLM 配置管理路由
管理员接口
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.services.llm_config_service import LLMConfigService


router = APIRouter(prefix="/admin", tags=["admin"])


class LLMConfigCreate(BaseModel):
    """创建配置请求"""

    name: str = Field(..., min_length=1, max_length=100)
    provider_type: str = Field(
        ...,
        description="供应商类型: openai, anthropic, azure_openai, baidu, aliyun, other",
    )
    base_url: str = Field(..., max_length=500)
    api_key: str = Field(..., description="API Key (明文，后端加密存储)")
    model_name: str = Field(..., max_length=100)
    request_params: Optional[Dict[str, Any]] = Field(
        default={}, description="请求参数: temperature, max_tokens, timeout"
    )
    is_default: bool = False
    is_active: bool = True


class LLMConfigUpdate(BaseModel):
    """更新配置请求"""

    name: Optional[str] = Field(None, max_length=100)
    provider_type: Optional[str] = None
    base_url: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = Field(None, description="API Key (明文，后端加密存储)")
    model_name: Optional[str] = Field(None, max_length=100)
    request_params: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class LLMConfigResponse(BaseModel):
    """配置响应"""

    id: str
    name: str
    provider_type: str
    base_url: str
    model_name: str
    request_params: Dict[str, Any]
    is_default: bool
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class TestConnectionResponse(BaseModel):
    """连接测试结果"""

    success: bool
    message: str
    latency_ms: int


def _config_to_dict(config) -> dict:
    """将 SQLAlchemy 配置对象转换为字典"""
    return {
        "id": str(config.id),
        "name": config.name,
        "provider_type": config.provider_type,
        "base_url": config.base_url,
        "model_name": config.model_name,
        "request_params": config.request_params or {},
        "is_default": config.is_default,
        "is_active": config.is_active,
        "created_at": config.created_at.isoformat() if config.created_at else None,
    }


@router.get("/llm-configs", response_model=List[LLMConfigResponse])
async def list_llm_configs(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """获取所有 LLM 配置"""
    service = LLMConfigService(db)
    configs = service.list_configs(skip=skip, limit=limit)
    return [_config_to_dict(config) for config in configs]


@router.post(
    "/llm-configs",
    response_model=LLMConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_llm_config(config: LLMConfigCreate, db: Session = Depends(get_db)):
    """创建 LLM 配置"""
    service = LLMConfigService(db)
    config_obj = service.create_config(**config.dict())
    return _config_to_dict(config_obj)


@router.get("/llm-configs/{config_id}", response_model=LLMConfigResponse)
async def get_llm_config(config_id: str, db: Session = Depends(get_db)):
    """获取单个配置详情"""
    service = LLMConfigService(db)
    config = service.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return _config_to_dict(config)


@router.put("/llm-configs/{config_id}", response_model=LLMConfigResponse)
async def update_llm_config(
    config_id: str, update: LLMConfigUpdate, db: Session = Depends(get_db)
):
    """更新 LLM 配置"""
    service = LLMConfigService(db)

    # 过滤掉 None 值
    update_data = {k: v for k, v in update.dict().items() if v is not None}

    config = service.update_config(config_id, **update_data)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return _config_to_dict(config)


@router.delete("/llm-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_config(config_id: str, db: Session = Depends(get_db)):
    """删除 LLM 配置"""
    service = LLMConfigService(db)
    success = service.delete_config(config_id)
    if not success:
        raise HTTPException(status_code=404, detail="配置不存在")
    return None


@router.post("/llm-configs/{config_id}/test", response_model=TestConnectionResponse)
async def test_llm_config(config_id: str, db: Session = Depends(get_db)):
    """测试配置连接"""
    service = LLMConfigService(db)
    success, error, latency_ms = await service.test_connection(config_id)
    return TestConnectionResponse(
        success=success,
        message=error if not success else "连接成功",
        latency_ms=latency_ms,
    )


@router.post("/llm-configs/{config_id}/set-default")
async def set_default_config(config_id: str, db: Session = Depends(get_db)):
    """设置默认配置"""
    service = LLMConfigService(db)
    success = service.set_default_config(config_id)
    if not success:
        raise HTTPException(status_code=404, detail="配置不存在")
    return {"message": "已设置为默认配置"}


@router.get("/llm-stats")
async def get_llm_stats(db: Session = Depends(get_db)):
    """获取 LLM 统计信息"""
    service = LLMConfigService(db)
    stats = service.get_stats()
    return stats


# 限流配置（简化实现，实际可以存储在数据库中）
DEFAULT_RATE_LIMITS = {
    "normal_user": {"hourly_limit": 50},
    "premium_user": {"hourly_limit": 200},
}


@router.get("/rate-limits")
async def get_rate_limits():
    """获取限流配置"""
    return DEFAULT_RATE_LIMITS


@router.put("/rate-limits")
async def update_rate_limits(limits: Dict[str, Dict[str, int]]):
    """更新限流配置"""
    global DEFAULT_RATE_LIMITS
    DEFAULT_RATE_LIMITS.update(limits)
    return DEFAULT_RATE_LIMITS
