"""
Contact Message Service - 联系留言业务逻辑层
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import Depends

from app.models.base import get_db
from app.models.contact_message import ContactMessage, MessageStatus, ContactMessageResponse


class ContactMessageService:
    """联系留言服务类"""

    def __init__(self, db: Session):
        self.db = db

    def create_message(
        self,
        name: str,
        email: str,
        subject: Optional[str],
        content: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ContactMessageResponse:
        """
        创建新留言

        Args:
            name: 姓名
            email: 邮箱
            subject: 主题
            content: 留言内容
            ip_address: IP 地址
            user_agent: 用户代理

        Returns:
            ContactMessageResponse: 创建的留言
        """
        # 验证邮箱格式（简单验证）
        if "@" not in email or "." not in email:
            raise ValueError("无效的邮箱格式")

        # 验证内容长度
        if len(content) < 10:
            raise ValueError("留言内容至少需要 10 个字符")

        if len(content) > 10000:
            raise ValueError("留言内容不能超过 10000 个字符")

        db_message = ContactMessage(
            name=name,
            email=email,
            subject=subject,
            content=content,
            ip_address=ip_address,
            user_agent=user_agent,
            status=MessageStatus.UNREAD
        )

        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)

        return ContactMessageResponse.model_validate(db_message)

    def get_message(self, message_id: UUID) -> Optional[ContactMessageResponse]:
        """
        获取单个留言详情

        Args:
            message_id: 留言 ID

        Returns:
            ContactMessageResponse 或 None
        """
        db_message = self.db.query(ContactMessage).filter(
            ContactMessage.id == message_id
        ).first()

        if not db_message:
            return None

        return ContactMessageResponse.model_validate(db_message)

    def get_messages(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[MessageStatus] = None,
        keyword: Optional[str] = None
    ) -> dict:
        """
        获取留言列表（支持分页、筛选、搜索）

        Args:
            page: 页码
            page_size: 每页数量
            status: 状态筛选
            keyword: 搜索关键词

        Returns:
            dict: {items: [], total: int}
        """
        query = self.db.query(ContactMessage)

        # 状态筛选
        if status:
            query = query.filter(ContactMessage.status == status)

        # 关键词搜索（姓名、邮箱、主题）
        if keyword:
            search_pattern = f"%{keyword}%"
            query = query.filter(
                or_(
                    ContactMessage.name.ilike(search_pattern),
                    ContactMessage.email.ilike(search_pattern),
                    ContactMessage.subject.ilike(search_pattern),
                    ContactMessage.content.ilike(search_pattern)
                )
            )

        # 总数
        total = query.count()

        # 分页排序（最新的在前）
        db_messages = query.order_by(
            ContactMessage.created_at.desc()
        ).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        items = [ContactMessageResponse.model_validate(msg) for msg in db_messages]

        return {"items": items, "total": total}

    def update_message(
        self,
        message_id: UUID,
        update_data: "ContactMessageUpdate"
    ) -> ContactMessageResponse:
        """
        更新留言

        Args:
            message_id: 留言 ID
            update_data: 更新数据

        Returns:
            ContactMessageResponse: 更新后的留言

        Raises:
            ValueError: 留言不存在
        """
        from app.models.contact_message import ContactMessageUpdate

        db_message = self.db.query(ContactMessage).filter(
            ContactMessage.id == message_id
        ).first()

        if not db_message:
            raise ValueError("留言不存在")

        # 更新字段
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if value is not None:
                setattr(db_message, field, value)

        self.db.commit()
        self.db.refresh(db_message)

        return ContactMessageResponse.model_validate(db_message)

    def mark_as_read(self, message_id: UUID) -> bool:
        """
        标记留言为已读

        Args:
            message_id: 留言 ID

        Returns:
            bool: 是否成功
        """
        db_message = self.db.query(ContactMessage).filter(
            ContactMessage.id == message_id
        ).first()

        if not db_message:
            return False

        if db_message.status == MessageStatus.UNREAD:
            db_message.status = MessageStatus.READ
            self.db.commit()

        return True

    def batch_update_status(
        self,
        message_ids: List[UUID],
        status: MessageStatus
    ) -> int:
        """
        批量更新留言状态

        Args:
            message_ids: 留言 ID 列表
            status: 新状态

        Returns:
            int: 更新的数量
        """
        updated_count = self.db.query(ContactMessage).filter(
            ContactMessage.id.in_(message_ids)
        ).update(
            {ContactMessage.status: status},
            synchronize_session=False
        )
        self.db.commit()
        return updated_count

    def batch_delete_messages(
        self,
        message_ids: List[UUID]
    ) -> int:
        """
        批量删除留言

        Args:
            message_ids: 留言 ID 列表

        Returns:
            int: 删除的数量
        """
        deleted_count = self.db.query(ContactMessage).filter(
            ContactMessage.id.in_(message_ids)
        ).delete(synchronize_session=False)
        self.db.commit()
        return deleted_count

    def delete_message(self, message_id: UUID) -> bool:
        """
        删除单个留言

        Args:
            message_id: 留言 ID

        Returns:
            bool: 是否成功
        """
        db_message = self.db.query(ContactMessage).filter(
            ContactMessage.id == message_id
        ).first()

        if not db_message:
            return False

        self.db.delete(db_message)
        self.db.commit()
        return True

    def get_stats(self) -> dict:
        """
        获取留言统计信息

        Returns:
            dict: 统计数据
        """
        total = self.db.query(ContactMessage).count()
        unread = self.db.query(ContactMessage).filter(
            ContactMessage.status == MessageStatus.UNREAD
        ).count()
        processing = self.db.query(ContactMessage).filter(
            ContactMessage.status == MessageStatus.PROCESSING
        ).count()
        resolved = self.db.query(ContactMessage).filter(
            ContactMessage.status == MessageStatus.RESOLVED
        ).count()

        return {
            "total": total,
            "unread": unread,
            "processing": processing,
            "resolved": resolved
        }


# Dependency injection
def get_contact_message_service(db: Session = Depends(get_db)) -> ContactMessageService:
    """获取留言服务实例"""
    return ContactMessageService(db)
