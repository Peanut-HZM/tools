"""
Author: Peanut
Created: 2026-06-08
Purpose: 设备名称解析与 alias 聚合辅助函数
"""

from sqlalchemy.orm import Session

from app.models.token_usage_models import DeviceRegistry, DeviceIdAlias


def load_device_name_map(db: Session, user_id: str) -> dict[str, str]:
    """
    加载用户下所有设备的显示名称。
    返回: {device_id: display_name}
    """
    rows = db.query(DeviceRegistry).filter(DeviceRegistry.user_id == user_id).all()
    return {
        row.device_id: row.display_name or row.default_display_name or row.device_id
        for row in rows
    }


def load_alias_map(db: Session, user_id: str) -> dict[str, str]:
    """
    加载用户下所有 device_id 的别名映射。
    返回: {alias_device_id: canonical_device_id}
    """
    rows = db.query(DeviceIdAlias).filter(DeviceIdAlias.user_id == user_id).all()
    return {row.alias_device_id: row.canonical_device_id for row in rows}


def resolve_canonical_device_id(device_id: str, alias_map: dict[str, str]) -> str:
    """将 alias_device_id 解析为 canonical_device_id，无映射时返回原值"""
    return alias_map.get(device_id, device_id)


def resolve_device_name(device_id: str, device_name_map: dict[str, str]) -> str:
    """解析设备显示名称，无注册信息时返回 device_id"""
    return device_name_map.get(device_id, device_id)
