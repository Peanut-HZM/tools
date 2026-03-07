"""
Contact Message Routes - 联系留言 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from typing import List, Optional
from uuid import UUID

from app.models.contact_message import (
    ContactMessage,
    MessageStatus,
    ContactMessageCreate,
    ContactMessageUpdate,
    ContactMessageResponse,
    ContactMessageListResponse,
)
from app.middleware.auth_middleware import get_current_user
from app.models.auth_models import UserResponse
from app.services.contact_message_service import get_contact_message_service, ContactMessageService

router = APIRouter(prefix="/api", tags=["contact"])

# ==================== Public APIs (无需认证) ====================

@router.post("/contact", response_model=ContactMessageResponse, status_code=201)
async def create_contact_message(
    message_data: ContactMessageCreate,
    request: Request,
    service: ContactMessageService = Depends(get_contact_message_service)
):
    """
    提交联系留言 (公开接口，无需认证)

    Args:
        message_data: 留言数据 (name, email, subject, content)
        request: FastAPI 请求对象 (用于获取 IP 和 User-Agent)

    Returns:
        ContactMessageResponse: 创建的留言信息
    """
    # 获取请求者 IP 和 User-Agent
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        message = service.create_message(
            name=message_data.name,
            email=message_data.email,
            subject=message_data.subject,
            content=message_data.content,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return message
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败：{str(e)}")


# ==================== Admin APIs (需要管理员权限) ====================

def get_admin_user(current_user: UserResponse = Depends(get_current_user)):
    """检查当前用户是否为管理员"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足：需要管理员权限")
    return current_user


@router.get("/admin/contact-messages", response_model=ContactMessageListResponse)
async def list_contact_messages(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选 (unread/read/processing/resolved)"),
    keyword: Optional[str] = Query(None, description="搜索关键词 (姓名/邮箱/主题)"),
    admin_user: UserResponse = Depends(get_admin_user),
    service: ContactMessageService = Depends(get_contact_message_service)
):
    """
    获取留言列表 (仅管理员)

    Args:
        page: 页码
        page_size: 每页数量
        status: 状态筛选
        keyword: 搜索关键词

    Returns:
        ContactMessageListResponse: 留言列表和分页信息
    """
    status_enum = None
    if status:
        try:
            status_enum = MessageStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态值：{status}")

    result = service.get_messages(
        page=page,
        page_size=page_size,
        status=status_enum,
        keyword=keyword
    )

    return ContactMessageListResponse(
        items=result["items"],
        total=result["total"],
        page=page,
        page_size=page_size
    )


@router.get("/admin/contact-messages/{message_id}", response_model=ContactMessageResponse)
async def get_contact_message(
    message_id: UUID,
    admin_user: UserResponse = Depends(get_admin_user),
    service: ContactMessageService = Depends(get_contact_message_service)
):
    """
    获取留言详情 (仅管理员)

    Args:
        message_id: 留言 ID

    Returns:
        ContactMessageResponse: 留言详情
    """
    message = service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="留言不存在")

    # 自动标记为已读
    service.mark_as_read(message_id)

    return message


@router.patch("/admin/contact-messages/{message_id}", response_model=ContactMessageResponse)
async def update_contact_message(
    message_id: UUID,
    update_data: ContactMessageUpdate,
    admin_user: UserResponse = Depends(get_admin_user),
    service: ContactMessageService = Depends(get_contact_message_service)
):
    """
    更新留言状态/回复 (仅管理员)

    Args:
        message_id: 留言 ID
        update_data: 更新数据 (status, admin_reply)

    Returns:
        ContactMessageResponse: 更新后的留言
    """
    try:
        message = service.update_message(message_id, update_data)
        return message
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败：{str(e)}")


@router.delete("/admin/contact-messages/{message_id}")
async def delete_contact_message(
    message_id: UUID,
    admin_user: UserResponse = Depends(get_admin_user),
    service: ContactMessageService = Depends(get_contact_message_service)
):
    """
    删除留言 (仅管理员)

    Args:
        message_id: 留言 ID

    Returns:
        删除成功消息
    """
    try:
        success = service.delete_message(message_id)
        if not success:
            raise HTTPException(status_code=404, detail="留言不存在")
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败：{str(e)}")


@router.post("/admin/contact-messages/batch-update")
async def batch_update_contact_messages(
    message_ids: List[UUID] = Body(..., description="留言 ID 列表"),
    status: Optional[MessageStatus] = Body(None, description="新状态"),
    admin_user: UserResponse = Depends(get_admin_user),
    service: ContactMessageService = Depends(get_contact_message_service)
):
    """
    批量更新留言状态 (仅管理员)

    Args:
        message_ids: 留言 ID 列表
        status: 新状态

    Returns:
        操作结果
    """
    if not status:
        raise HTTPException(status_code=400, detail="必须指定状态")

    try:
        updated_count = service.batch_update_status(message_ids, status)
        return {"message": f"成功更新 {updated_count} 条留言", "updated_count": updated_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量更新失败：{str(e)}")


@router.post("/admin/contact-messages/batch-delete")
async def batch_delete_contact_messages(
    message_ids: List[UUID] = Body(..., description="留言 ID 列表"),
    admin_user: UserResponse = Depends(get_admin_user),
    service: ContactMessageService = Depends(get_contact_message_service)
):
    """
    批量删除留言 (仅管理员)

    Args:
        message_ids: 留言 ID 列表

    Returns:
        操作结果
    """
    try:
        deleted_count = service.batch_delete_messages(message_ids)
        return {"message": f"成功删除 {deleted_count} 条留言", "deleted_count": deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量删除失败：{str(e)}")
