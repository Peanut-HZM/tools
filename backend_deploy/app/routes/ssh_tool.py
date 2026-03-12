from fastapi import APIRouter, Depends, WebSocket, Query, Body, HTTPException
from typing import List
from app.middleware.auth_middleware import get_current_user_id
from app.models.ssh_tool_models import SSHConfigResponse, CreateSSHRequest, UpdateSSHRequest, DeleteSSHRequest, TestSSHConnectionRequest, TestSSHConnectionResponse
from app.services.ssh_tool_service import SSHToolService

router = APIRouter(prefix="/ssh-tool", tags=["ssh-tool"])

@router.get("/configs", response_model=List[SSHConfigResponse])
async def get_configs(user_id: str = Depends(get_current_user_id)):
    return SSHToolService.get_configs(user_id)

@router.post("/configs", response_model=SSHConfigResponse)
async def create_config(
    request: CreateSSHRequest,
    user_id: str = Depends(get_current_user_id)
):
    return SSHToolService.create_config(user_id, request)

@router.put("/configs/update", response_model=SSHConfigResponse)
async def update_config(
    request: UpdateSSHRequest,
    user_id: str = Depends(get_current_user_id)
):
    return SSHToolService.update_config(user_id, request)

@router.delete("/configs/delete")
async def delete_config(request: DeleteSSHRequest = Body(...), user_id: str = Depends(get_current_user_id)):
    success = SSHToolService.delete_config(user_id, request.id)
    if not success:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"message": "Config deleted successfully"}

@router.post("/test-connection", response_model=TestSSHConnectionResponse)
async def test_connection(
    request: TestSSHConnectionRequest,
    user_id: str = Depends(get_current_user_id)
):
    try:
        SSHToolService.test_connection(request)
        return TestSSHConnectionResponse(success=True, message="Connection successful")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.websocket("/ws")
async def ssh_websocket(
    websocket: WebSocket,
    config_id: str = Query(None, description="Configuration ID"),
    configId: str = Query(None, description="Configuration ID"),
    token: str = Query(..., description="Auth Token"),
    cols: int = Query(80),
    rows: int = Query(24)
):
    selected_config_id = config_id or configId
    if not selected_config_id:
        await websocket.close(code=4000, reason="Configuration ID missing")
        return
    await SSHToolService.handle_ssh_session(websocket, selected_config_id, token, cols, rows)

@router.websocket("/ws/{config_id}")
async def ssh_websocket_with_path(
    websocket: WebSocket,
    config_id: str,
    token: str = Query(..., description="Auth Token"),
    cols: int = Query(80),
    rows: int = Query(24)
):
    await SSHToolService.handle_ssh_session(websocket, config_id, token, cols, rows)
