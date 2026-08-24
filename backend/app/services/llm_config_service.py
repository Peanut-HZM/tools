"""
LLM 配置服务
处理大模型配置的 CRUD 操作
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import LLMConfig
from app.core.security import encrypt_api_key, decrypt_api_key
from app.services.llm.factory import get_provider


class LLMConfigService:
    """LLM 配置服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_config(
        self,
        name: str,
        provider_type: str,
        base_url: str,
        api_key: str,
        model_name: str,
        request_params: Optional[Dict[str, Any]] = None,
        category: str = "text",
        notes: Optional[str] = None,
        is_default: bool = False,
        is_active: bool = True,
    ) -> LLMConfig:
        """创建新配置"""
        # 加密 API Key
        encrypted_key = encrypt_api_key(api_key)
        # 提取 API Key 最后4位
        api_key_suffix = api_key[-4:] if len(api_key) >= 4 else api_key

        # 如果设置为默认，取消其他默认配置
        if is_default:
            self._unset_default_configs()

        config = LLMConfig(
            name=name,
            provider_type=provider_type,
            base_url=base_url,
            api_key_encrypted=encrypted_key,
            api_key_suffix=api_key_suffix,
            model_name=model_name,
            request_params=request_params or {},
            category=category,
            notes=notes,
            is_default=is_default,
            is_active=is_active,
        )

        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def update_config(self, config_id: str, **kwargs) -> Optional[LLMConfig]:
        """更新配置"""
        config = self.get_config(config_id)
        if not config:
            return None

        # 如果更新 API Key，需要加密并更新后缀
        if "api_key" in kwargs:
            api_key = kwargs.pop("api_key")
            kwargs["api_key_encrypted"] = encrypt_api_key(api_key)
            kwargs["api_key_suffix"] = api_key[-4:] if len(api_key) >= 4 else api_key

        # 如果设置为默认，取消其他默认配置
        if kwargs.get("is_default"):
            self._unset_default_configs()
        """更新配置"""
        config = self.get_config(config_id)
        if not config:
            return None

        # 如果更新 API Key，需要加密
        if "api_key" in kwargs:
            kwargs["api_key_encrypted"] = encrypt_api_key(kwargs.pop("api_key"))

        # 如果设置为默认，取消其他默认配置
        if kwargs.get("is_default"):
            self._unset_default_configs()

        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        self.db.commit()
        self.db.refresh(config)
        return config

    def delete_config(self, config_id: str) -> bool:
        """删除配置"""
        config = self.get_config(config_id)
        if not config:
            return False

        self.db.delete(config)
        self.db.commit()
        return True

    def get_config(self, config_id: str) -> Optional[LLMConfig]:
        """获取单个配置"""
        return self.db.query(LLMConfig).filter(LLMConfig.id == config_id).first()

    def list_configs(
        self, skip: int = 0, limit: int = 100, active_only: bool = False
    ) -> List[LLMConfig]:
        """列出所有配置"""
        query = self.db.query(LLMConfig)
        if active_only:
            query = query.filter(LLMConfig.is_active == True)
        return query.offset(skip).limit(limit).all()

    def get_default_config(self) -> Optional[LLMConfig]:
        """获取默认配置"""
        return (
            self.db.query(LLMConfig)
            .filter(LLMConfig.is_default == True, LLMConfig.is_active == True)
            .first()
        )

    def set_default_config(self, config_id: str) -> bool:
        """设置默认配置"""
        config = self.get_config(config_id)
        if not config:
            return False

        self._unset_default_configs()
        config.is_default = True
        self.db.commit()
        return True

    def _unset_default_configs(self):
        """取消所有默认配置"""
        self.db.query(LLMConfig).filter(LLMConfig.is_default == True).update(
            {"is_default": False}
        )
        self.db.commit()

    async def test_connection(self, config_id: str) -> tuple[bool, str, int]:
        """
        测试配置连接

        Returns:
            (是否成功, 错误信息, 延迟毫秒)
        """
        import time

        config = self.get_config(config_id)
        if not config:
            return False, "配置不存在", 0

        # 解密 API Key
        try:
            api_key = decrypt_api_key(config.api_key_encrypted)
        except Exception as e:
            return False, f"API Key 解密失败: {str(e)}", 0

        # 创建 Provider 并测试
        try:
            provider = get_provider(
                config.provider_type,
                api_key,
                config.base_url,
                config.model_name,
                **(config.request_params or {}),
            )

            start_time = time.time()
            success, error = await provider.test_connection()
            latency_ms = int((time.time() - start_time) * 1000)

            return success, error, latency_ms
        except Exception as e:
            return False, str(e), 0

    def get_stats(self) -> Dict[str, Any]:
        """获取配置统计信息"""
        total = self.db.query(func.count(LLMConfig.id)).scalar()
        active = (
            self.db.query(func.count(LLMConfig.id))
            .filter(LLMConfig.is_active == True)
            .scalar()
        )

        by_provider = (
            self.db.query(LLMConfig.provider_type, func.count(LLMConfig.id))
            .group_by(LLMConfig.provider_type)
            .all()
        )

        return {
            "total": total,
            "active": active,
            "by_provider": {p: c for p, c in by_provider},
        }
