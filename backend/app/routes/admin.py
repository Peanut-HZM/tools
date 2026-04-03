"""
Admin Routes - APIs for administrative tasks (User Management, OSS Management)
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Dict, Any, Optional

from app.services.auth_service import get_auth_service, AuthService
from app.services.oss_service import oss_service
from app.services.stats_service import stats_service
from app.services.tools_service import tools_service
from app.services.settings_service import settings_service
from app.models.auth_models import UserResponse, UserRoleUpdate, UserCreate, UserListResponse, UserBatchDeleteRequest, UserBatchUpdateRoleRequest, AdminPasswordReset, AdminPasswordResetResponse
from app.models.stats_models import DashboardStats, ToolVisitRequest
from app.models import Tool
from app.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])

def get_admin_user(current_user: UserResponse = Depends(get_current_user)):
    """Dependency to check if current user is admin"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied: Admin access required")
    return current_user

# ==================== User Management ====================

@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search keyword for username/email"),
    role: Optional[str] = Query(None, pattern="^(user|admin)$", description="Filter by role"),
    admin_user: UserResponse = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """List users with pagination, search, and filter"""
    return auth_service.get_users_paginated(page=page, page_size=page_size, search=search, role=role)

@router.post("/users/batch-delete", response_model=dict)
async def batch_delete_users(
    request: UserBatchDeleteRequest,
    admin_user: UserResponse = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Batch delete users"""
    return auth_service.batch_delete_users(request.user_ids, admin_user.user_id)

@router.post("/users/batch-update-role", response_model=dict)
async def batch_update_user_role(
    request: UserBatchUpdateRoleRequest,
    admin_user: UserResponse = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Batch update user role"""
    return auth_service.batch_update_user_role(request.user_ids, request.role)

@router.put("/users/{user_id}/role", response_model=bool)
async def update_user_role(
    user_id: str,
    role_update: UserRoleUpdate,
    admin_user: UserResponse = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update user role"""
    success = auth_service.update_user_role(user_id, role_update.role)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return True

@router.post("/users", response_model=dict)
async def create_user_admin(
    user_data: dict = Body(...),
    admin_user: UserResponse = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Create a new user (admin only)"""
    username = user_data.get("username")
    email = user_data.get("email")
    role = user_data.get("role", "user")
    
    if not username or not email:
        raise HTTPException(status_code=400, detail="Username and email are required")
        
    try:
        password = auth_service.create_user_admin(username, email, role)
        return {"username": username, "password": password, "message": "User created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/users/{user_id}", response_model=bool)
async def delete_user(
    user_id: str,
    admin_user: UserResponse = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Delete user"""
    if user_id == admin_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    success = auth_service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return True


# ==================== Password Management ====================

@router.post("/users/{user_id}/reset-password", response_model=AdminPasswordResetResponse)
async def admin_reset_password(
    user_id: str,
    password_reset: AdminPasswordReset,
    admin_user: UserResponse = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Admin reset user password"""
    # Get client IP from request headers
    request = getattr(admin_reset, "request", None)
    ip_address = None
    if request:
        ip_address = request.headers.get("X-Forwarded-For", request.headers.get("X-Real-IP"))

    success, message, new_password = auth_service.admin_reset_password(
        user_id=user_id,
        mode=password_reset.mode,
        new_password=password_reset.new_password,
        reset_by_user_id=admin_user.user_id,
        ip_address=ip_address
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return AdminPasswordResetResponse(
        success=True,
        new_password=new_password,
        message=message
    )

# ==================== OSS Management ====================

@router.get("/oss/files", response_model=List[dict])
async def list_oss_files(
    limit: int = 100,
    offset: int = 0,
    admin_user: UserResponse = Depends(get_admin_user)
):
    """List all files in OSS (from DB)"""
    return oss_service.list_files_db(limit=limit, offset=offset)

@router.delete("/oss/files/{filename:path}", response_model=bool)
async def delete_oss_file(
    filename: str,
    admin_user: UserResponse = Depends(get_admin_user)
):
    """Delete any file from OSS"""
    # Filename here is the full object key/path
    return oss_service.delete_file(filename)

# ==================== Tool Management ====================

@router.get("/tools", response_model=List[Tool])
async def list_tools_admin(
    admin_user: UserResponse = Depends(get_admin_user)
):
    """List all tools (including offline)"""
    return tools_service.get_all_tools(include_offline=True)

@router.put("/tools/{tool_id}/status", response_model=bool)
async def update_tool_status(
    tool_id: str,
    status: str = Query(..., regex="^(online|offline)$"),
    admin_user: UserResponse = Depends(get_admin_user)
):
    """Update tool status"""
    return tools_service.update_tool_status(tool_id, status)

# ==================== System Settings ====================

@router.get("/settings", response_model=Dict[str, Any])
async def get_system_settings(
    admin_user: UserResponse = Depends(get_admin_user)
):
    """Get system settings"""
    return settings_service.get_settings()

@router.put("/settings", response_model=bool)
async def update_system_settings(
    settings: Dict[str, Any] = Body(...),
    admin_user: UserResponse = Depends(get_admin_user)
):
    """Update system settings"""
    # For now, we only support allow_registration, but we can iterate over keys
    for key, value in settings.items():
        settings_service.update_setting(key, value)
    return True

# ==================== Dashboard Statistics ====================

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    admin_user: UserResponse = Depends(get_admin_user)
):
    """Get dashboard statistics"""
    return stats_service.get_dashboard_stats()

@router.post("/stats/visit", response_model=bool)
async def record_tool_visit(
    visit_data: ToolVisitRequest
):
    """Record a tool visit (Public API, no admin check needed)"""
    # Note: Ideally this should be in a public stats router, but for simplicity we put it here
    # and bypass admin check. Or we can move it to tools router.
    # Given the requirement, let's keep it here but remove admin dependency for this endpoint if possible.
    # However, the router prefix is /api/admin. 
    # Let's move this to a separate public router or handle it differently.
    # Actually, for better structure, let's keep admin stats here and move public tracking to tools router.
    # But to follow the "User Input" which implies "Backend implementation", I will put it here for now
    # but I will NOT add the admin dependency.
    # WAIT: /api/admin/* usually implies protection. 
    # Let's put the public tracking endpoint in `app/routes/tools.py` instead?
    # No, let's just add it here and allow it. Or better, put it in `app/routes/tools.py`.
    # Let's verify `app/routes/tools.py` content.
    return stats_service.record_visit(visit_data.tool_id, visit_data.tool_name)
