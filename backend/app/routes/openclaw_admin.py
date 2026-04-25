"""
OpenClaw 管理路由
提供配置管理、连接状态监控、手动重连/断开功能
"""
import logging
import re
import ssl
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
    # 保存完整 token 用于表单回显，脱敏值用于状态卡片展示
    real_token = config.get("token", "")
    masked_token = connection_info.get("token", "")
    return {**config, **connection_info, "token": real_token, "token_masked": masked_token}


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


class TestConnectionRequest(BaseModel):
    gateway_url: str
    auth_mode: str = "token"
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None


@router.post("/test-connection")
async def test_connection(
    request: TestConnectionRequest,
    admin_user: UserResponse = Depends(get_admin_user),
):
    """测试连接（不保存配置，仅验证当前输入能否连通）"""
    import asyncio
    import json
    import uuid
    import time
    from websockets import connect as ws_connect

    url = request.gateway_url
    # 根据认证模式决定是否嵌入用户名密码
    if request.auth_mode == "token_with_password" and request.username and request.password:
        if url.startswith("ws://"):
            url = url.replace("ws://", f"ws://{request.username}:{request.password}@", 1)
        elif url.startswith("wss://"):
            url = url.replace("wss://", f"wss://{request.username}:{request.password}@", 1)

    # 禁用 SSL 证书验证（支持自签名证书）
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    start_time = time.monotonic()
    try:
        async with ws_connect(url, ping_interval=30, ping_timeout=10, ssl=ssl_context) as ws:
            # 等待 connect.challenge
            challenge_raw = await asyncio.wait_for(ws.recv(), timeout=10)
            challenge = json.loads(challenge_raw)
            if challenge.get("event") != "connect.challenge":
                return {"ok": False, "message": f"预期 connect.challenge，收到: {challenge.get('event', 'unknown')}"}
            nonce = challenge.get("payload", {}).get("nonce", "")
            if not nonce:
                return {"ok": False, "message": "connect.challenge 缺少 nonce"}

            # 发送 connect 请求
            connect_msg = {
                "type": "req",
                "id": str(uuid.uuid4()),
                "method": "connect",
                "params": {
                    "minProtocol": 3,
                    "maxProtocol": 3,
                    "client": {
                        "id": "operator",
                        "displayName": "OpenClaw Admin",
                        "version": "1.0.0",
                    },
                    "caps": [],
                    "auth": {"token": request.token} if request.token else None,
                    "role": "operator",
                    "scopes": ["operator.admin"],
                },
            }
            connect_msg["params"] = {k: v for k, v in connect_msg["params"].items() if v is not None}

            await ws.send(json.dumps(connect_msg))

            # 等待 hello_ok
            response_raw = await asyncio.wait_for(ws.recv(), timeout=10)
            response = json.loads(response_raw)

            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            if response.get("ok"):
                return {"ok": True, "message": f"连接成功（耗时 {elapsed_ms}ms）"}
            else:
                error = response.get("error", {})
                return {"ok": False, "message": f"鉴权失败: {error.get('message', 'unknown')}"}
    except asyncio.TimeoutError:
        return {"ok": False, "message": "连接超时，请检查 Gateway 地址和网络"}
    except ConnectionRefusedError:
        return {"ok": False, "message": "连接被拒绝，Gateway 可能未启动"}
    except Exception as e:
        error_msg = str(e)
        if "connect" in error_msg.lower() or "refused" in error_msg.lower():
            return {"ok": False, "message": f"连接失败: {error_msg}"}
        return {"ok": False, "message": f"连接失败: {error_msg}"}
