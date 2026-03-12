"""
LLM 故障回退服务
当主 LLM 配置失败时，自动切换到备用配置
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import logging

from app.services.llm.factory import get_provider
from app.models import LLMConfig

logger = logging.getLogger(__name__)


class LLMFallbackService:
    """LLM 故障回退服务"""

    def __init__(self, db: Session):
        self.db = db
        self._max_retries = 2
        self._timeout = 30  # 秒

    async def generate_with_fallback(
        self,
        prompt: str,
        primary_config_id: Optional[str] = None,
        context: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> str:
        """
        使用故障回退机制生成响应

        Args:
            prompt: 提示词
            primary_config_id: 主配置 ID
            context: 对话上下文
            **kwargs: 其他参数

        Returns:
            生成的响应文本
        """
        # 获取可用的 LLM 配置列表
        configs = self._get_available_configs(primary_config_id)

        if not configs:
            raise ValueError("没有可用的 LLM 配置")

        last_error = None

        # 依次尝试每个配置
        for config in configs:
            try:
                logger.info(
                    f"尝试使用 LLM 配置：{config.name} ({config.provider_type})"
                )

                provider = get_provider(config.provider_type)

                # 构建消息
                messages = self._build_messages(prompt, context)

                # 调用 LLM
                response = await provider.generate(
                    messages=messages,
                    model_name=config.model_name,
                    **config.params,
                    **kwargs,
                )

                logger.info(f"LLM 配置 {config.name} 调用成功")
                return response

            except Exception as e:
                logger.warning(
                    f"LLM 配置 {config.name} 调用失败：{str(e)}. 尝试下一个配置..."
                )
                last_error = e
                continue

        # 所有配置都失败
        error_msg = f"所有 LLM 配置都失败。最后错误：{str(last_error)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def _get_available_configs(
        self, primary_config_id: Optional[str] = None
    ) -> List[LLMConfig]:
        """
        获取可用的 LLM 配置列表

        优先级：
        1. 指定的主配置
        2. 默认配置
        3. 其他活跃配置
        """
        configs = (
            self.db.query(LLMConfig)
            .filter(LLMConfig.is_active == True)
            .order_by(LLMConfig.is_default.desc(), LLMConfig.id)
            .all()
        )

        if not configs:
            return []

        # 如果指定了主配置，将其移到列表前面
        if primary_config_id:
            primary = next((c for c in configs if str(c.id) == primary_config_id), None)
            if primary:
                configs.remove(primary)
                configs.insert(0, primary)

        return configs

    def _build_messages(
        self, prompt: str, context: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, str]]:
        """
        构建 LLM 消息列表

        Args:
            prompt: 用户提示词
            context: 对话上下文

        Returns:
            消息列表
        """
        messages = []

        # 添加系统提示
        messages.append(
            {
                "role": "system",
                "content": "你是一个专业的产品经理助手，帮助用户生成高质量的产品需求文档（PRD）。",
            }
        )

        # 添加上下文消息
        if context:
            for msg in context[-10:]:  # 只使用最近 10 条消息
                role = "user" if msg.get("sender_type") == "user" else "assistant"
                messages.append({"role": role, "content": msg.get("content", "")})

        # 添加当前提示
        messages.append({"role": "user", "content": prompt})

        return messages

    async def test_all_configs(self) -> Dict[str, Any]:
        """
        测试所有 LLM 配置的可用性

        Returns:
            测试结果
        """
        configs = self._get_available_configs()
        results = {
            "total": len(configs),
            "available": 0,
            "unavailable": 0,
            "details": [],
        }

        test_prompt = "Hello"

        for config in configs:
            try:
                provider = get_provider(config.provider_type)
                messages = [{"role": "user", "content": test_prompt}]

                # 简单测试（不等待完整响应）
                await provider.generate(
                    messages=messages, model_name=config.model_name, max_tokens=10
                )

                results["available"] += 1
                results["details"].append(
                    {
                        "id": str(config.id),
                        "name": config.name,
                        "provider": config.provider_type,
                        "status": "available",
                    }
                )

            except Exception as e:
                results["unavailable"] += 1
                results["details"].append(
                    {
                        "id": str(config.id),
                        "name": config.name,
                        "provider": config.provider_type,
                        "status": "unavailable",
                        "error": str(e),
                    }
                )

        return results


def get_llm_fallback_service(db: Session) -> LLMFallbackService:
    """获取 LLM 回退服务实例"""
    return LLMFallbackService(db)
