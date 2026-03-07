"""
CrossShare 服务层
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from app.models.cross_share import (
    Device,
    CrossMessage,
    CrossFile,
    CrossShareConfig,
)
from app.schemas.cross_share import (
    DeviceCreate,
    DeviceUpdate,
    MessageCreate,
    FileCreate,
    ConfigCreate,
    ConfigUpdate,
    MessageType,
    FileType,
)

logger = logging.getLogger(__name__)


class CrossShareService:
    """CrossShare 服务"""

    def __init__(self, db: Session):
        self.db = db

    # ============ 设备管理 ============

    def get_devices(self, user_id: str) -> List[Device]:
        """获取用户所有设备"""
        return self.db.query(Device).filter(Device.user_id == user_id).order_by(Device.created_at.desc()).all()

    def get_device_by_id(self, device_id: str, user_id: str) -> Optional[Device]:
        """根据 ID 获取设备"""
        return self.db.query(Device).filter(
            and_(Device.id == device_id, Device.user_id == user_id)
        ).first()

    def get_device_by_token(self, device_token: str) -> Optional[Device]:
        """根据 token 获取设备"""
        return self.db.query(Device).filter(Device.device_token == device_token).first()

    def create_or_update_device(self, user_id: str, device: DeviceCreate) -> Device:
        """创建或更新设备"""
        # 先查找是否已存在
        db_device = self.get_device_by_token(device.device_token)

        if db_device:
            # 更新现有设备
            db_device.device_name = device.device_name
            db_device.device_type = device.device_type or db_device.device_type
            db_device.ip_address = device.ip_address
            db_device.last_seen_at = datetime.now()
            db_device.is_active = True
        else:
            # 创建新设备
            db_device = Device(
                user_id=user_id,
                device_name=device.device_name,
                device_type=device.device_type,
                device_token=device.device_token,
                user_agent=device.user_agent,
                ip_address=device.ip_address,
                last_seen_at=datetime.now(),
            )
            self.db.add(db_device)

        self.db.commit()
        self.db.refresh(db_device)
        logger.info(f"设备已注册/更新：{device.device_name} (user_id={user_id})")
        return db_device

    def update_device(self, device_id: str, user_id: str, device: DeviceUpdate) -> Optional[Device]:
        """更新设备"""
        db_device = self.get_device_by_id(device_id, user_id)
        if not db_device:
            return None

        update_data = device.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_device, field, value)

        self.db.commit()
        self.db.refresh(db_device)
        return db_device

    def delete_device(self, device_id: str, user_id: str) -> bool:
        """删除设备"""
        db_device = self.get_device_by_id(device_id, user_id)
        if not db_device:
            return False

        self.db.delete(db_device)
        self.db.commit()
        logger.info(f"设备已删除：{device_id}")
        return True

    def ping_device(self, device_id: str, user_id: str) -> Optional[Device]:
        """更新设备活跃时间"""
        db_device = self.get_device_by_id(device_id, user_id)
        if not db_device:
            return None

        db_device.last_seen_at = datetime.now()
        self.db.commit()
        self.db.refresh(db_device)
        return db_device

    # ============ 消息管理 ============

    def get_messages(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        message_type: Optional[MessageType] = None,
    ) -> List[CrossMessage]:
        """获取消息列表"""
        query = self.db.query(CrossMessage).filter(CrossMessage.user_id == user_id)

        if message_type:
            query = query.filter(CrossMessage.message_type == message_type)

        # 过滤过期消息
        query = query.filter(
            or_(
                CrossMessage.expires_at.is_(None),
                CrossMessage.expires_at > datetime.now()
            )
        )

        return query.order_by(desc(CrossMessage.created_at)).offset(offset).limit(limit).all()

    def get_message_by_id(self, message_id: str, user_id: str) -> Optional[CrossMessage]:
        """根据 ID 获取消息"""
        return self.db.query(CrossMessage).filter(
            and_(
                CrossMessage.id == message_id,
                CrossMessage.user_id == user_id
            )
        ).first()

    def create_message(self, user_id: str, message: MessageCreate, from_device_id: Optional[str] = None) -> CrossMessage:
        """创建消息"""
        db_message = CrossMessage(
            user_id=user_id,
            from_device_id=from_device_id,
            content=message.content,
            message_type=message.message_type.value if isinstance(message.message_type, MessageType) else message.message_type,
            file_id=message.file_id,
            is_encrypted=message.is_encrypted,
            expires_at=message.expires_at,
        )
        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)
        logger.info(f"消息已创建：type={message.message_type}, user_id={user_id}")
        return db_message

    def mark_message_as_read(self, message_id: str, user_id: str) -> Optional[CrossMessage]:
        """标记消息为已读"""
        db_message = self.get_message_by_id(message_id, user_id)
        if not db_message:
            return None

        db_message.is_read = True
        self.db.commit()
        self.db.refresh(db_message)
        return db_message

    def update_message(self, message_id: str, user_id: str, content: Optional[str] = None, message_type: Optional[str] = None) -> Optional[CrossMessage]:
        """更新消息"""
        db_message = self.get_message_by_id(message_id, user_id)
        if not db_message:
            return None

        if content is not None:
            db_message.content = content
        if message_type is not None:
            db_message.message_type = message_type

        self.db.commit()
        self.db.refresh(db_message)
        logger.info(f"消息已更新：id={message_id}, user_id={user_id}")
        return db_message

    def delete_message(self, message_id: str, user_id: str) -> bool:
        """删除消息"""
        db_message = self.get_message_by_id(message_id, user_id)
        if not db_message:
            return False

        self.db.delete(db_message)
        self.db.commit()
        return True

    def get_clipboard_history(self, user_id: str, limit: int = 100) -> List[CrossMessage]:
        """获取剪贴板历史"""
        return self.db.query(CrossMessage).filter(
            and_(
                CrossMessage.user_id == user_id,
                CrossMessage.message_type == "clipboard"
            )
        ).order_by(desc(CrossMessage.created_at)).limit(limit).all()

    def create_clipboard_message(self, user_id: str, content: str, from_device_id: Optional[str] = None, is_encrypted: bool = False) -> CrossMessage:
        """创建剪贴板消息"""
        return self.create_message(
            user_id=user_id,
            message=MessageCreate(
                content=content,
                message_type="clipboard",
                is_encrypted=is_encrypted,
            ),
            from_device_id=from_device_id,
        )

    # ============ 文件管理 ============

    def get_files(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        file_type: Optional[FileType] = None,
        search: Optional[str] = None,
    ) -> List[CrossFile]:
        """获取文件列表"""
        query = self.db.query(CrossFile).filter(
            and_(
                CrossFile.user_id == user_id,
                CrossFile.is_deleted == False
            )
        )

        if file_type:
            query = query.filter(CrossFile.file_type == file_type.value if isinstance(file_type, FileType) else file_type)

        if search:
            query = query.filter(CrossFile.file_name.like(f"%{search}%"))

        return query.order_by(desc(CrossFile.created_at)).offset(offset).limit(limit).all()

    def get_file_by_id(self, file_id: str, user_id: str) -> Optional[CrossFile]:
        """根据 ID 获取文件"""
        return self.db.query(CrossFile).filter(
            and_(
                CrossFile.id == file_id,
                CrossFile.user_id == user_id,
                CrossFile.is_deleted == False
            )
        ).first()

    def get_file_by_hash(self, file_hash: str, user_id: str) -> Optional[CrossFile]:
        """根据 hash 获取文件（用于去重）"""
        return self.db.query(CrossFile).filter(
            and_(
                CrossFile.file_hash == file_hash,
                CrossFile.user_id == user_id,
                CrossFile.is_deleted == False
            )
        ).first()

    def create_file(self, user_id: str, file: FileCreate, expires_at: datetime = None) -> CrossFile:
        """创建文件记录
        
        参数:
            user_id: 用户 ID
            file: 文件创建信息
            expires_at: 文件过期时间，如果不传则根据配置的 file_expire_days 计算
        """
        db_file = CrossFile(
            user_id=user_id,
            upload_device_id=file.upload_device_id,
            oss_bucket=file.oss_bucket,
            oss_key=file.oss_key,
            file_name=file.file_name,
            file_size=file.file_size,
            file_type=file.file_type.value if isinstance(file.file_type, FileType) else file.file_type,
            file_hash=file.file_hash,
            expires_at=expires_at,
        )
        self.db.add(db_file)
        self.db.commit()
        self.db.refresh(db_file)
        logger.info(f"文件已创建：{file.file_name}, user_id={user_id}, expires_at={expires_at}")
        return db_file

    def delete_file(self, file_id: str, user_id: str) -> bool:
        """删除文件（软删除）"""
        db_file = self.get_file_by_id(file_id, user_id)
        if not db_file:
            return False

        db_file.is_deleted = True
        db_file.deleted_at = datetime.now()
        self.db.commit()
        logger.info(f"文件已删除：{file_id}")
        return True

    def update_file(self, file_id: str, user_id: str, file_name: Optional[str] = None, file_type: Optional[str] = None) -> Optional[CrossFile]:
        """更新文件信息"""
        db_file = self.get_file_by_id(file_id, user_id)
        if not db_file:
            return None

        if file_name is not None:
            db_file.file_name = file_name
        if file_type is not None:
            db_file.file_type = file_type

        self.db.commit()
        self.db.refresh(db_file)
        logger.info(f"文件已更新：id={file_id}, user_id={user_id}")
        return db_file

    def increment_download_count(self, file_id: str, user_id: str) -> Optional[CrossFile]:
        """增加下载计数"""
        db_file = self.get_file_by_id(file_id, user_id)
        if not db_file:
            return None

        db_file.download_count += 1
        self.db.commit()
        self.db.refresh(db_file)
        return db_file

    def get_storage_stats(self, user_id: str, config: CrossShareConfig) -> Dict[str, Any]:
        """获取存储统计"""
        # 总文件数和大小
        result = self.db.query(
            func.count(CrossFile.id).label('total_files'),
            func.sum(CrossFile.file_size).label('total_size')
        ).filter(
            and_(
                CrossFile.user_id == user_id,
                CrossFile.is_deleted == False
            )
        ).first()

        total_files = result.total_files or 0
        total_size = result.total_size or 0

        # 按文件类型统计
        type_stats = self.db.query(
            CrossFile.file_type,
            func.count(CrossFile.id).label('count')
        ).filter(
            and_(
                CrossFile.user_id == user_id,
                CrossFile.is_deleted == False
            )
        ).group_by(CrossFile.file_type).all()

        files_by_type = {stat.file_type: stat.count for stat in type_stats}

        return {
            "total_files": total_files,
            "total_size": total_size,
            "used_quota": total_size,
            "available_quota": config.storage_quota - total_size,
            "usage_percentage": (total_size / config.storage_quota * 100) if config.storage_quota > 0 else 0,
            "files_by_type": files_by_type,
        }

    # ============ 配置管理 ============

    def get_config(self, user_id: str) -> CrossShareConfig:
        """获取用户配置"""
        config = self.db.query(CrossShareConfig).filter(CrossShareConfig.user_id == user_id).first()

        if not config:
            # 创建默认配置
            config = CrossShareConfig(
                user_id=user_id,
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)

        return config

    def update_config(self, user_id: str, config: ConfigUpdate) -> CrossShareConfig:
        """更新用户配置"""
        db_config = self.get_config(user_id)

        update_data = config.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_config, field, value)

        self.db.commit()
        self.db.refresh(db_config)
        logger.info(f"配置已更新：user_id={user_id}")
        return db_config

    # ============ 清理过期数据 ============

    def cleanup_expired_messages(self) -> int:
        """清理过期消息"""
        deleted = self.db.query(CrossMessage).filter(
            and_(
                CrossMessage.expires_at.isnot(None),
                CrossMessage.expires_at < datetime.now()
            )
        ).delete(synchronize_session=False)
        self.db.commit()
        return deleted

    def cleanup_expired_files(self) -> int:
        """清理过期文件"""
        deleted = self.db.query(CrossFile).filter(
            and_(
                CrossFile.expires_at.isnot(None),
                CrossFile.expires_at < datetime.now()
            )
        ).delete(synchronize_session=False)
        self.db.commit()
        return deleted

    def cleanup_deleted_files(self) -> int:
        """清理已删除的文件记录（物理删除）"""
        deleted = self.db.query(CrossFile).filter(
            and_(
                CrossFile.is_deleted == True,
                CrossFile.deleted_at < datetime.now() - timedelta(days=30)
            )
        ).delete(synchronize_session=False)
        self.db.commit()
        return deleted
