"""
OpenClaw 管理路由
提供配置管理、连接状态监控、手动重连/断开功能
"""
import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.openclaw_service import openclaw_service
from app.services.openclaw_config_service import openclaw_config_service
from app.middleware.auth_middleware import get_current_user
from app.models.auth_models import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/openclaw", tags=["openclaw-admin"])


def get_admin_user(current_user: UserResponse = Depends(get_current_user)):
    """检查是否为管理员"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足：需要管理员权限")
    return current_user


class ConfigUpdateRequest(BaseModel):
    gateway_url: Optional[str] = None
    auth_mode: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    enabled: Optional[str] = None


@router.get("/config")
async def get_config(admin_user: UserResponse = Depends(get_admin_user)):
    """获取当前配置（密码和 Token 脱敏）"""
    config = openclaw_config_service.get_config()
    connection_info = openclaw_service.get_connection_info()
    # 密码脱敏
    password = config.get("password", "")
    config["password"] = "****" + password[-4:] if len(password) > 4 else ("****" if password else "")
    return {**config, **connection_info}


@router.put("/config")
async def update_config(
    request: ConfigUpdateRequest,
    admin_user: UserResponse = Depends(get_admin_user),
):
    """更新配置并热加载"""
    data = request.model_dump(exclude_unset=True)

    # 验证 gateway_url 格式
    if "gateway_url" in data:
        url = data["gateway_url"]
        if url and not re.match(r"^wss?://", url):
            raise HTTPException(status_code=400, detail="Gateway URL 格式错误，应以 ws:// 或 wss:// 开头")

    # 验证 enabled 值
    if "enabled" in data:
        if data["enabled"] not in ("true", "false"):
            raise HTTPException(status_code=400, detail="enabled 值必须为 true 或 false")

    # 验证 auth_mode 值
    if "auth_mode" in data:
        if data["auth_mode"] not in ("token", "token_with_password"):
            raise HTTPException(status_code=400, detail="auth_mode 必须为 token 或 token_with_password")

    # 更新数据库
    updated_config = openclaw_config_service.update_config(data)

    # 热加载
    try:
        await openclaw_service.reload_config(updated_config)
    except Exception as e:
        logger.error(f"OpenClaw 热加载失败: {e}")
        return {"ok": False, "message": f"配置已保存，但重连失败: {str(e)}", "config": openclaw_service.get_connection_info()}

    return {"ok": True, "config": openclaw_service.get_connection_info()}


@router.get("/status")
async def get_status(admin_user: UserResponse = Depends(get_admin_user)):
    """获取连接状态"""
    connection_info = openclaw_service.get_connection_info()

    if connection_info["connected"]:
        try:
            gateway_status = await openclaw_service.get_status()
            return {"ok": True, **connection_info, "gateway_status": gateway_status}
        except Exception as e:
            return {"ok": True, **connection_info, "gateway_status": {"error": str(e)}}

    return {"ok": True, **connection_info}


@router.post("/reconnect")
async def reconnect(admin_user: UserResponse = Depends(get_admin_user)):
    """手动重连"""
    try:
        config = openclaw_config_service.get_config()
        await openclaw_service.reload_config(config)
        return {"ok": True, "message": "重连成功", "config": openclaw_service.get_connection_info()}
    except Exception as e:
        logger.error(f"OpenClaw 重连失败: {e}")
        raise HTTPException(status_code=500, detail=f"重连失败: {str(e)}")


@router.post("/disconnect")
async def disconnect(admin_user: UserResponse = Depends(get_admin_user)):
    """断开连接"""
    try:
        await openclaw_service.stop()
        return {"ok": True, "message": "已断开连接", "config": openclaw_service.get_connection_info()}
    except Exception as e:
        logger.error(f"OpenClaw 断开连接失败: {e}")
        raise HTTPException(status_code=500, detail=f"断开连接失败: {str(e)}")
