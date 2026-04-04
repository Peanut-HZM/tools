from fastapi import APIRouter, Depends, WebSocket, Query, Body, HTTPException, Path as PathParam
from typing import List
from app.middleware.auth_middleware import get_current_user_id
from app.models.ssh_tool_models import (
    SSHConfigResponse, CreateSSHRequest, UpdateSSHRequest, DeleteSSHRequest,
    TestSSHConnectionRequest, TestSSHConnectionResponse,
    SFTPListRequest, SFTPListResponse, SFTPDownloadRequest, SFTPDownloadResponse,
    SFTPUploadRequest, SFTPUploadResponse, SFTPDeleteRequest, SFTPDeleteResponse,
    SFTPMkdirRequest, SFTPMkdirResponse, SFTPRenameRequest, SFTPRenameResponse,
    SSHTunnelRequest, SSHTunnelResponse, SSHTunnelListResponse, SSHTunnelStopRequest,
    BatchCommandRequest, BatchCommandResponse
)
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

# ============ SFTP 文件传输 API ============

@router.post("/configs/{id}/sftp/list", response_model=SFTPListResponse)
async def sftp_list_files(
    request: SFTPListRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """List remote directory files"""
    try:
        return SSHToolService.sftp_list_files(id, user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/sftp/download", response_model=SFTPDownloadResponse)
async def sftp_download_file(
    request: SFTPDownloadRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Download remote file"""
    try:
        return SSHToolService.sftp_download_file(id, user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/sftp/upload", response_model=SFTPUploadResponse)
async def sftp_upload_file(
    request: SFTPUploadRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Upload file to remote"""
    try:
        return SSHToolService.sftp_upload_file(id, user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/sftp/delete", response_model=SFTPDeleteResponse)
async def sftp_delete(
    request: SFTPDeleteRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Delete remote file or directory"""
    try:
        return SSHToolService.sftp_delete(id, user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/sftp/mkdir", response_model=SFTPMkdirResponse)
async def sftp_mkdir(
    request: SFTPMkdirRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Create remote directory"""
    try:
        return SSHToolService.sftp_mkdir(id, user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/sftp/rename", response_model=SFTPRenameResponse)
async def sftp_rename(
    request: SFTPRenameRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Rename/move remote file or directory"""
    try:
        return SSHToolService.sftp_rename(id, user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ SSH 隧道 API ============

@router.post("/configs/{id}/tunnel", response_model=SSHTunnelResponse)
async def create_tunnel(
    request: SSHTunnelRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Create SSH tunnel"""
    try:
        return await SSHToolService.create_tunnel(id, user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tunnels/stop")
async def stop_tunnel(
    request: SSHTunnelStopRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Stop SSH tunnel"""
    success = SSHToolService.stop_tunnel(request.tunnel_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tunnel not found")
    return {"message": "Tunnel stopped successfully"}

@router.get("/tunnels", response_model=SSHTunnelListResponse)
async def list_tunnels(user_id: str = Depends(get_current_user_id)):
    """List all active tunnels"""
    return SSHToolService.list_tunnels()

# ============ 批量命令执行 API ============

@router.post("/configs/{id}/batch-execute", response_model=BatchCommandResponse)
async def execute_batch_commands(
    request: BatchCommandRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Execute batch commands"""
    try:
        return SSHToolService.execute_batch_commands(id, user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
