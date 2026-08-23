"""
backend/app/services/dify_client.py

Dify 工作流 HTTP 客户端，封装 4 个 operation 的调用。
本应用不直接调图像生成 API，全部走 Dify 工作流路由。

设计要点（spec §5.2, plan Phase 3）：
- 使用 httpx.AsyncClient（异步，不阻塞 gunicorn worker）
- 每次调用从 DifyConfigService.get_config() 实时读配置（不缓存）
- response_mode: "blocking"，同步等待工作流完成
- 不重试（spec 全局约束 7）
- 错误分类通过 DifyError.kind 标识，便于上层降级处理

参考：docs/plans/2026-08-23-image-generation-dify-client-design.md
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

import httpx

from app.services.dify_config_service import DifyConfigService, DifyConfig
from app.core.exceptions import DifyError

logger = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class DifyRunResult:
    """Dify 工作流调用的标准化结果"""
    image_urls: List[str]           # 生成结果图片 URL 列表
    model_used: str                 # 实际调用的模型（从工作流节点传递）
    raw_response: Dict[str, Any]    # 原始响应（用于调试/审计）
    elapsed_seconds: float          # 总耗时（秒）


@dataclass
class ChatRunResult:
    """Chatflow 多轮对话调用的标准化结果"""
    conversation_id: str             # 多轮对话 ID（首次创建时 Dify 返回，后续轮次回传）
    answer: str                      # LLM 回复文本（追问问题 or 生成说明）
    image_urls: List[str] = field(default_factory=list)  # 生成的图片（<<GENERATE>> 触发后才有值）
    model_used: str = ""             # 实际调用的模型
    polish_prompt: str = ""          # 润色后的英文图像生成提示词
    history_id: Optional[str] = None  # 触发生成时写入的历史记录 ID
    raw_response: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# DifyClient
# ============================================================

class DifyClient:
    """
    Dify 工作流 HTTP 客户端。

    4 个 run 方法 + test_connection，共享 _run_workflow 私有方法。
    每次调用实时读取 DifyConfigService.get_config() 获取最新配置。
    """

    def __init__(self, config_svc: Optional[DifyConfigService] = None):
        self._config_svc = config_svc or DifyConfigService()

    # ------------------------------------------------------------------
    # 公开方法 — 4 个 operation
    # ------------------------------------------------------------------

    async def run_text2img(
        self,
        prompt: str,
        size: str,
        n: int,
        style: Optional[str],
        model_preference: str,
        user_id: str,
        timeout: Optional[float] = None,
    ) -> DifyRunResult:
        """
        调用 text2img 工作流。

        Args:
            prompt: 文本提示词
            size: 图像尺寸 (1024x1024, 1024x1792, 1792x1024)
            n: 生成数量 (1-4)
            style: 风格 (natural, vivid, auto, None)
            model_preference: 模型偏好 (auto, doubao, qwen, hailuo)
            user_id: 用户标识（Dify 用于追踪）
            timeout: 超时秒数（默认取 config.default_timeout）
        """
        config = self._get_config()
        if not config.workflow_text2img:
            raise DifyError("text2img 工作流未配置", kind="config_error")

        inputs = {
            "prompt": prompt,
            "size": size,
            "n": n,
            "style": style or "auto",
            "model_preference": model_preference,
        }
        return await self._run_workflow(
            config=config,
            workflow_id=config.workflow_text2img,
            inputs=inputs,
            user_id=user_id,
            timeout=timeout or config.default_timeout,
        )

    async def run_img2img(
        self,
        prompt: str,
        reference_url: str,
        strength: float,
        size: str,
        model_preference: str,
        user_id: str,
        timeout: Optional[float] = None,
    ) -> DifyRunResult:
        """
        调用 img2img 工作流。

        Args:
            prompt: 文本提示词
            reference_url: 参考图 OSS 签名 URL
            strength: 变化强度 0.0-1.0
            size: 输出尺寸
            model_preference: 模型偏好
            user_id: 用户标识
            timeout: 超时秒数
        """
        config = self._get_config()
        if not config.workflow_img2img:
            raise DifyError("img2img 工作流未配置", kind="config_error")

        inputs = {
            "prompt": prompt,
            "reference_url": reference_url,
            "strength": strength,
            "size": size,
            "model_preference": model_preference,
        }
        return await self._run_workflow(
            config=config,
            workflow_id=config.workflow_img2img,
            inputs=inputs,
            user_id=user_id,
            timeout=timeout or config.default_timeout,
        )

    async def run_inpaint(
        self,
        prompt: str,
        image_url: str,
        mask_url: str,
        size: str,
        model_preference: str,
        user_id: str,
        timeout: Optional[float] = None,
    ) -> DifyRunResult:
        """
        调用 inpaint（局部重绘）工作流。

        Args:
            prompt: 文本提示词
            image_url: 待编辑图 OSS 签名 URL
            mask_url: 蒙版图 URL（白色=重绘区域）
            size: 输出尺寸
            model_preference: 模型偏好
            user_id: 用户标识
            timeout: 超时秒数
        """
        config = self._get_config()
        if not config.workflow_inpaint:
            raise DifyError("inpaint 工作流未配置", kind="config_error")

        inputs = {
            "prompt": prompt,
            "image_url": image_url,
            "mask_url": mask_url,
            "size": size,
            "model_preference": model_preference,
        }
        return await self._run_workflow(
            config=config,
            workflow_id=config.workflow_inpaint,
            inputs=inputs,
            user_id=user_id,
            timeout=timeout or config.default_timeout,
        )

    async def run_upload_edit(
        self,
        image_url: str,
        edit_type: str,
        prompt: Optional[str],
        user_id: str,
        timeout: Optional[float] = None,
    ) -> DifyRunResult:
        """
        调用 upload_edit（上传编辑）工作流。

        Args:
            image_url: 待编辑图 OSS 签名 URL
            edit_type: upscale / denoise / style_transfer / background_remove / relight
            prompt: 可选提示词（部分 edit 类型需要）
            user_id: 用户标识
            timeout: 超时秒数
        """
        config = self._get_config()
        if not config.workflow_upload_edit:
            raise DifyError("upload_edit 工作流未配置", kind="config_error")

        inputs = {
            "image_url": image_url,
            "edit_type": edit_type,
            "prompt": prompt or "",
        }
        return await self._run_workflow(
            config=config,
            workflow_id=config.workflow_upload_edit,
            inputs=inputs,
            user_id=user_id,
            timeout=timeout or config.default_timeout,
        )

    # ------------------------------------------------------------------
    # Chatflow 多轮对话调用（4 个 operation）
    # ------------------------------------------------------------------

    async def chat_text2img(
        self,
        prompt: str,
        conversation_id: Optional[str],
        size: str,
        n: int,
        style: Optional[str],
        model_preference: str,
        user_id: str,
        timeout: Optional[float] = None,
    ) -> ChatRunResult:
        """调用 text2img-chat Chatflow（多轮对话模式）"""
        config = self._get_config()
        if not config.workflow_text2img:
            raise DifyError("text2img Chatflow 未配置", kind="config_error")

        inputs = {
            "size": size,
            "n": n,
            "style": style or "auto",
            "model_preference": model_preference,
        }
        payload = {
            "inputs": inputs,
            "query": prompt,
            "response_mode": "blocking",
            "user": user_id or "anonymous",
            "conversation_id": conversation_id or "",
        }
        return await self._call_chat(
            config=config,
            endpoint="/chat-messages",
            payload=payload,
            user_id=user_id,
            timeout=timeout or config.default_timeout,
        )

    async def chat_img2img(
        self,
        prompt: str,
        reference_url: str,
        conversation_id: Optional[str],
        strength: float,
        size: str,
        model_preference: str,
        user_id: str,
        timeout: Optional[float] = None,
    ) -> ChatRunResult:
        """调用 img2img-chat Chatflow"""
        config = self._get_config()
        if not config.workflow_img2img:
            raise DifyError("img2img Chatflow 未配置", kind="config_error")

        inputs = {
            "reference_url": reference_url,
            "strength": strength,
            "size": size,
            "model_preference": model_preference,
        }
        payload = {
            "inputs": inputs,
            "query": prompt,
            "response_mode": "blocking",
            "user": user_id or "anonymous",
            "conversation_id": conversation_id or "",
        }
        return await self._call_chat(
            config=config,
            endpoint="/chat-messages",
            payload=payload,
            user_id=user_id,
            timeout=timeout or config.default_timeout,
        )

    async def chat_inpaint(
        self,
        prompt: str,
        image_url: str,
        mask_url: str,
        conversation_id: Optional[str],
        size: str,
        model_preference: str,
        user_id: str,
        timeout: Optional[float] = None,
    ) -> ChatRunResult:
        """调用 inpaint-chat Chatflow"""
        config = self._get_config()
        if not config.workflow_inpaint:
            raise DifyError("inpaint Chatflow 未配置", kind="config_error")

        inputs = {
            "image_url": image_url,
            "mask_url": mask_url,
            "size": size,
            "model_preference": model_preference,
        }
        payload = {
            "inputs": inputs,
            "query": prompt,
            "response_mode": "blocking",
            "user": user_id or "anonymous",
            "conversation_id": conversation_id or "",
        }
        return await self._call_chat(
            config=config,
            endpoint="/chat-messages",
            payload=payload,
            user_id=user_id,
            timeout=timeout or config.default_timeout,
        )

    async def chat_upload_edit(
        self,
        image_url: str,
        edit_type: str,
        conversation_id: Optional[str],
        prompt: Optional[str],
        user_id: str,
        timeout: Optional[float] = None,
    ) -> ChatRunResult:
        """调用 upload-edit-chat Chatflow"""
        config = self._get_config()
        if not config.workflow_upload_edit:
            raise DifyError("upload_edit Chatflow 未配置", kind="config_error")

        inputs = {
            "image_url": image_url,
            "edit_type": edit_type,
        }
        payload = {
            "inputs": inputs,
            "query": prompt or "",
            "response_mode": "blocking",
            "user": user_id or "anonymous",
            "conversation_id": conversation_id or "",
        }
        return await self._call_chat(
            config=config,
            endpoint="/chat-messages",
            payload=payload,
            user_id=user_id,
            timeout=timeout or config.default_timeout,
        )

    async def _call_chat(
        self,
        config: "DifyConfig",
        endpoint: str,
        payload: Dict[str, Any],
        user_id: str,
        timeout: float,
    ) -> ChatRunResult:
        """Chatflow 统一调用：POST /chat-messages"""
        url = f"{config.api_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {config.app_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    error_body = resp.text[:500]
                    logger.error(
                        "[dify-chat] 调用失败: HTTP %d, body: %s",
                        resp.status_code, error_body,
                    )
                    self._raise_http_error(resp.status_code, "chat", error_body)

                data = resp.json()
                return self._parse_chat_response(data)

        except DifyError:
            raise
        except httpx.TimeoutException:
            raise DifyError(f"Chatflow 调用超时 ({timeout}s)", kind="timeout")
        except httpx.ConnectError as e:
            raise DifyError(f"无法连接 Dify: {e}", kind="connection_error")
        except Exception as e:
            logger.error("[dify-chat] 未预期异常: %s", e, exc_info=True)
            raise DifyError(f"未预期的错误: {e}", kind="http_error")

    def _parse_chat_response(self, data: Dict[str, Any]) -> ChatRunResult:
        """解析 Chatflow 响应"""
        conversation_id = data.get("conversation_id", "")
        answer = data.get("answer", "")
        metadata = data.get("metadata", {}) or {}

        # 图片从 metadata.images 提取（如工作流末尾输出到此字段）
        image_urls = metadata.get("images", [])
        if isinstance(image_urls, str):
            try:
                image_urls = json.loads(image_urls)
            except (json.JSONDecodeError, ValueError):
                image_urls = []
        if not isinstance(image_urls, list):
            image_urls = []

        # 若 answer 含 <<GENERATE>> 且 metadata 有 images，标记为已生成
        return ChatRunResult(
            conversation_id=conversation_id,
            answer=answer,
            image_urls=image_urls,
            model_used=metadata.get("model_used", ""),
            polish_prompt=metadata.get("polish_prompt", ""),
            raw_response=data,
        )

    # ------------------------------------------------------------------
    # 连通性测试
    # ------------------------------------------------------------------

    async def test_connection(self) -> tuple:
        """
        测试 Dify 连通性（调用 {api_url}/info）。
        返回 (ok: bool, message: str)。
        """
        config = self._get_config()
        if not config.api_url or not config.app_api_key:
            return False, "配置不完整（缺少 api_url 或 app_api_key）"

        url = f"{config.api_url}/info"
        headers = {"Authorization": f"Bearer {config.app_api_key}"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    return True, "连接成功"
                return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
        except httpx.TimeoutException:
            return False, "连接超时"
        except Exception as e:
            return False, f"连接失败: {e}"

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    def _get_config(self) -> DifyConfig:
        """从 DifyConfigService 获取配置（同步方法）"""
        return self._config_svc.get_config()

    async def _run_workflow(
        self,
        config: DifyConfig,
        workflow_id: str,
        inputs: Dict[str, Any],
        user_id: str,
        timeout: float,
    ) -> DifyRunResult:
        """
        统一的工作流调用逻辑。
        4 个 run_* 方法共享此实现。

        Args:
            config: Dify 配置
            workflow_id: 工作流 ID（用于日志）
            inputs: 工作流输入参数
            user_id: 用户标识
            timeout: 超时秒数
        """
        url = f"{config.api_url}/workflows/run"
        headers = {
            "Authorization": f"Bearer {config.app_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": inputs,
            "response_mode": "blocking",
            "user": user_id or "anonymous",
        }

        start_time = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
                elapsed = time.monotonic() - start_time

                # HTTP 错误分类
                if resp.status_code != 200:
                    error_body = resp.text[:500]
                    logger.error(
                        "[dify-client] workflow %s 失败: HTTP %d, body: %s",
                        workflow_id, resp.status_code, error_body,
                    )
                    self._raise_http_error(resp.status_code, workflow_id, error_body)

                # 解析响应
                try:
                    data = resp.json()
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error("[dify-client] 响应 JSON 解析失败: %s", e)
                    raise DifyError(
                        f"响应解析失败: {e}", kind="parse_error",
                    )

                return self._parse_response(data, elapsed)

        except DifyError:
            # DifyError 直接向上传播，不再包装
            raise
        except httpx.TimeoutException:
            logger.error(
                "[dify-client] workflow %s 超时 (%.1fs)", workflow_id, timeout,
            )
            raise DifyError(
                f"Dify 工作流超时 ({timeout}s)", kind="timeout",
            )
        except httpx.ConnectError as e:
            logger.error("[dify-client] 连接失败: %s", e)
            raise DifyError(
                f"无法连接 Dify: {e}", kind="connection_error",
            )
        except Exception as e:
            logger.error("[dify-client] 未预期异常: %s", e, exc_info=True)
            raise DifyError(
                f"未预期的错误: {e}", kind="http_error",
            )

    def _raise_http_error(self, status_code: int, workflow_id: str, body: str):
        """根据 HTTP 状态码抛出分类的 DifyError"""
        if status_code == 401:
            raise DifyError(
                "认证失败 - 请检查 DIFY_APP_API_KEY", kind="auth_error",
            )
        elif status_code == 404:
            raise DifyError(
                f"工作流不存在: {workflow_id}", kind="workflow_not_found",
            )
        elif status_code == 429:
            raise DifyError(
                "Dify 请求限流", kind="rate_limit",
            )
        else:
            raise DifyError(
                f"HTTP {status_code}: {body}", kind="http_error",
            )

    def _parse_response(self, data: Dict[str, Any], elapsed: float) -> DifyRunResult:
        """
        解析 Dify 工作流响应。

        Dify 响应结构：
        {
            "task_id": "...",
            "workflow_run_id": "...",
            "data": {
                "status": "succeeded" | "failed" | "stopped",
                "outputs": { "image_urls": [...], "model_used": "..." },
                "error": "..."
            }
        }
        """
        # 兼容两种格式：data 包裹 or 直接顶层
        workflow_data = data.get("data", data) if isinstance(data.get("data"), dict) else data
        status = workflow_data.get("status", "unknown")

        # 工作流状态检查
        if status == "failed":
            error_msg = workflow_data.get("error", "未知错误")
            logger.error("[dify-client] 工作流执行失败: %s", error_msg)
            raise DifyError(
                f"工作流执行失败: {error_msg}", kind="workflow_failed",
            )

        if status == "stopped":
            logger.warning("[dify-client] 工作流被中止")
            raise DifyError(
                "工作流被中止", kind="workflow_stopped",
            )

        # 提取 outputs
        outputs = workflow_data.get("outputs", {})
        if not isinstance(outputs, dict):
            outputs = {}

        # 提取 image_urls（可能是 list 或 JSON 字符串）
        image_urls = outputs.get("image_urls", [])
        if isinstance(image_urls, str):
            try:
                image_urls = json.loads(image_urls)
            except (json.JSONDecodeError, ValueError):
                image_urls = []

        # 确保是列表
        if not isinstance(image_urls, list):
            image_urls = []

        model_used = outputs.get("model_used", "unknown")

        # 空结果检查
        if not image_urls:
            logger.warning(
                "[dify-client] 工作流返回空 image_urls, outputs keys: %s",
                list(outputs.keys()),
            )
            raise DifyError(
                "工作流未返回任何图片", kind="empty_result",
            )

        return DifyRunResult(
            image_urls=image_urls,
            model_used=model_used,
            raw_response=data,
            elapsed_seconds=elapsed,
        )
