"""
LLM 配置管理路由
管理员接口
"""

from datetime import datetime
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
        description="供应商类型：openai, anthropic, azure_openai, baidu, aliyun, other",
    )
    base_url: str = Field(..., max_length=500)
    api_key: str = Field(..., description="API Key (明文，后端加密存储)")
    model_name: str = Field(..., max_length=100)
    request_params: Optional[Dict[str, Any]] = Field(
        default={}, description="请求参数：temperature, max_tokens, timeout"
    )
    category: str = Field(default="chat", description="分类：chat(对话类型), code(编程类型)")
    notes: Optional[str] = Field(None, max_length=500, description="备注")
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
    category: Optional[str] = Field(None, description="分类：chat(对话类型), code(编程类型)")
    notes: Optional[str] = Field(None, max_length=500, description="备注")
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class LLMConfigResponse(BaseModel):
    """配置响应"""

    id: str
    name: str
    provider_type: str
    base_url: str
    api_key_suffix: Optional[str]  # API Key 最后 4 位
    model_name: str
    request_params: Dict[str, Any]
    category: str  # chat: 对话类型，code: 编程类型
    notes: Optional[str]  # 备注
    is_default: bool
    is_active: bool
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class TestConnectionResponse(BaseModel):
    """连接测试结果"""

    success: bool
    message: str
    latency_ms: int


def _safe_iso(v) -> Optional[str]:
    """安全地将 datetime/字符串序列化为 ISO 字符串。

    背景：SQLAlchemy session 因 connection pool 被污染（PG transaction aborted）时，
    ORM 对象的 lazy 属性可能返回列键字符串（如 'llm_configs_created_at'）而非真实
    datetime/字符串。直接 .isoformat() 会抛 AttributeError。这里兼容 datetime、字符串、
    None，并识别列键模式返回 None，避免 500。
    """
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, str):
        # 检测 SQLAlchemy 列键（典型格式：表名_列名，如 'llm_configs_created_at'）
        if v and v.replace("_", "").isalnum():
            return None
        return v
    return str(v)


def _safe_str(v, default: str = "") -> str:
    """安全字符串转换：列键字符串（session 被污染时）返回 default。"""
    if v is None:
        return default
    if isinstance(v, str):
        if v and v.replace("_", "").isalnum():
            return default
        return v
    return str(v)


def _safe_bool(v, default: bool = False) -> bool:
    """安全布尔值转换：列键字符串（session 被污染时）返回 default。"""
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        if v and v.replace("_", "").isalnum():
            return default
        return v.lower() in ("true", "1", "yes")
    return bool(v)


def _safe_dict(v, default: Optional[dict] = None) -> Optional[dict]:
    """安全字典转换：列键字符串（session 被污染时）返回 default。"""
    if default is None:
        default = {}
    if v is None:
        return default
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        if v and v.replace("_", "").isalnum():
            return default
        # 尝试解析 JSON 字符串
        try:
            import json
            return json.loads(v)
        except (json.JSONDecodeError, ValueError):
            return default
    return default


def _config_to_dict(config) -> dict:
    """将 SQLAlchemy 配置对象转换为字典

    所有字段都通过 _safe_* 包装器访问，以防御 SQLAlchemy session
    因连接池污染而返回列键字符串的情况。此时返回安全的默认值而非
    500 崩溃。
    """
    import logging
    _logger = logging.getLogger(__name__)

    # 诊断日志：检查 session 是否被污染
    if hasattr(config, 'request_params') and isinstance(config.request_params, str):
        _logger.warning("[_config_to_dict] session 被污染! config.id=%r type=%s, request_params=%r",
                        config.id, type(config.id).__name__, config.request_params)

    return {
        "id": _safe_str(config.id),
        "name": _safe_str(config.name),
        "provider_type": _safe_str(config.provider_type),
        "base_url": _safe_str(config.base_url),
        "api_key_suffix": _safe_str(config.api_key_suffix, default=None) or None,
        "model_name": _safe_str(config.model_name),
        "request_params": _safe_dict(config.request_params),
        "category": _safe_str(config.category, default="chat"),
        "notes": _safe_str(config.notes, default=None) or None,
        "is_default": _safe_bool(config.is_default),
        "is_active": _safe_bool(config.is_active),
        "created_at": _safe_iso(config.created_at) or "",  # Pydantic 期望 str，不允许 None
        "updated_at": _safe_iso(config.updated_at),
    }


@router.get("/llm-configs", response_model=List[LLMConfigResponse])
async def list_llm_configs(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """获取所有 LLM 配置"""
    import logging
    _logger = logging.getLogger(__name__)
    _logger.warning("[list_llm_configs] 进入, db id=%s", id(db))

    service = LLMConfigService(db)
    configs = service.list_configs(skip=skip, limit=limit)
    _logger.warning("[list_llm_configs] 查询完成, configs count=%d", len(configs))
    if configs:
        c = configs[0]
        _logger.warning("[list_llm_configs] 第一个 config: id=%r type=%s, request_params type=%s",
                        c.id, type(c.id).__name__, type(c.request_params).__name__)
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
    # 更新限流配置
    global DEFAULT_RATE_LIMITS
    DEFAULT_RATE_LIMITS.update(limits)
    return DEFAULT_RATE_LIMITS
