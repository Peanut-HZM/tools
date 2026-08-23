# DifyClient Python 实现草稿

**目的**：在 Phase 3 实施前预先规划 DifyClient 完整实现
**适用 Plan Phase**：3
**依赖**：spec §5.2, plan Phase 0 完成

---

## 关键设计决策

1. **异步 HTTP**：使用 `httpx.AsyncClient`，避免阻塞 gunicorn worker
2. **配置实时读取**：每次调用都从 `DifyConfigService.get_config()` 读，不缓存（spec §2 决策）
3. **同步阻塞模式**：Dify `response_mode: "blocking"`，60s 超时
4. **重试**：不重试（spec 全局约束 7）
5. **错误分类**：`DifyError` 异常分类，便于上层处理降级

---

## 完整代码

```python
"""backend/app/services/dify_client.py

Dify 工作流 HTTP 客户端，封装 4 个 operation 的调用。
本应用不直接调图像生成 API，全部走 Dify 工作流路由。

参考 spec §5.2 关键接口定义。
"""
import logging
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import httpx

from app.services.dify_config_service import DifyConfigService
from app.core.exceptions import DifyError

logger = logging.getLogger(__name__)


@dataclass
class DifyRunResult:
    """Dify 工作流调用的标准化结果"""
    image_urls: List[str]           # 生成结果图片 URL 列表
    model_used: str                # 实际调用的模型（从工作流节点传递）
    workflow_run_id: str           # Dify 工作流运行 ID
    elapsed_seconds: float         # 总耗时
    raw_response: Dict[str, Any]   # 原始响应（用于调试/审计）


class DifyClient:
    """Dify 工作流 HTTP 客户端"""

    def __init__(self, config_svc: Optional[DifyConfigService] = None):
        self._config_svc = config_svc or DifyConfigService()

    async def run_text2img(
        self,
        prompt: str,
        size: str = "1024x1024",
        n: int = 1,
        style: Optional[str] = None,
        model_preference: str = "auto",
        user_id: str = "",
        timeout: Optional[float] = None,
    ) -> DifyRunResult:
        """调用 text2img 工作流

        Args:
            prompt: 文本提示词
            size: 图像尺寸 (1024x1024, 1024x1792, 1792x1024)
            n: 生成数量 (1-4)
            style: 风格 (natural, vivid, auto)
            model_preference: 模型偏好 (auto, doubao, qwen, hailuo)
            user_id: 用户标识（Dify 用于追踪）
            timeout: 超时秒数（默认 60s）
        """
        config = await self._config_svc.get_config()
        if not config.workflow_text2img:
            raise DifyError("text2img workflow not configured", kind="config_error")

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
        reference_image_url: str,
        strength: float = 0.6,
        size: str = "1024x1024",
        model_preference: str = "auto",
        user_id: str = "",
        timeout: Optional[float] = None,
    ) -> DifyRunResult:
        """调用 img2img 工作流

        Args:
            prompt: 文本提示词
            reference_image_url: 参考图 OSS 签名 URL
            strength: 变化强度 0.0-1.0
            size: 输出尺寸
        """
        config = await self._config_svc.get_config()
        if not config.workflow_img2img:
            raise DifyError("img2img workflow not configured", kind="config_error")

        inputs = {
            "prompt": prompt,
            "reference_image_url": reference_image_url,
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
        size: str = "1024x1024",
        model_preference: str = "auto",
        user_id: str = "",
        timeout: Optional[float] = None,
    ) -> DifyRunResult:
        """调用 inpaint 工作流

        Args:
            prompt: 文本提示词
            image_url: 待编辑图 OSS 签名 URL
            mask_url: 蒙版图 URL（白色=重绘区域）
            size: 输出尺寸
        """
        config = await self._config_svc.get_config()
        if not config.workflow_inpaint:
            raise DifyError("inpaint workflow not configured", kind="config_error")

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
        prompt: Optional[str] = None,
        model_preference: str = "auto",
        user_id: str = "",
        timeout: Optional[float] = None,
    ) -> DifyRunResult:
        """调用 upload_edit 工作流

        Args:
            image_url: 待编辑图 OSS 签名 URL
            edit_type: upscale / denoise / style_transfer / background_remove / relight
            prompt: 可选提示词（部分 edit 类型需要）
        """
        config = await self._config_svc.get_config()
        if not config.workflow_upload_edit:
            raise DifyError("upload_edit workflow not configured", kind="config_error")

        inputs = {
            "image_url": image_url,
            "edit_type": edit_type,
            "prompt": prompt or "",
            "model_preference": model_preference,
        }
        return await self._run_workflow(
            config=config,
            workflow_id=config.workflow_upload_edit,
            inputs=inputs,
            user_id=user_id,
            timeout=timeout or config.default_timeout,
        )

    async def test_connection(self) -> tuple:
        """测试 Dify 连通性"""
        config = await self._config_svc.get_config()
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

    # ============ 私有方法 ============

    async def _run_workflow(
        self,
        config,
        workflow_id: str,
        inputs: Dict[str, Any],
        user_id: str,
        timeout: float,
    ) -> DifyRunResult:
        """统一的工作流调用逻辑"""
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

                if resp.status_code != 200:
                    error_body = resp.text[:500]
                    logger.error(
                        f"[dify-client] workflow {workflow_id} failed: "
                        f"HTTP {resp.status_code}, body: {error_body}"
                    )
                    # 区分错误类型
                    if resp.status_code == 404:
                        raise DifyError(
                            f"Workflow not found: {workflow_id}",
                            kind="workflow_not_found",
                        )
                    elif resp.status_code == 401:
                        raise DifyError(
                            "Unauthorized - check DIFY_APP_API_KEY",
                            kind="auth_error",
                        )
                    elif resp.status_code == 429:
                        raise DifyError(
                            "Dify rate limit exceeded",
                            kind="rate_limit",
                        )
                    else:
                        raise DifyError(
                            f"HTTP {resp.status_code}: {error_body}",
                            kind="http_error",
                        )

                data = resp.json()
                return self._parse_response(data, elapsed)

        except httpx.TimeoutException:
            logger.error(
                f"[dify-client] workflow {workflow_id} timeout after {timeout}s"
            )
            raise DifyError(
                f"Dify workflow timeout ({timeout}s)",
                kind="timeout",
            )
        except httpx.ConnectError as e:
            logger.error(f"[dify-client] connect error: {e}")
            raise DifyError(
                f"Cannot connect to Dify: {e}",
                kind="connection_error",
            )

    def _parse_response(self, data: Dict[str, Any], elapsed: float) -> DifyRunResult:
        """解析 Dify 工作流响应"""
        status = data.get("status", "unknown")

        if status == "failed":
            error_msg = data.get("error", "unknown error")
            raise DifyError(
                f"Workflow execution failed: {error_msg}",
                kind="workflow_failed",
            )

        if status == "stopped":
            raise DifyError(
                "Workflow execution stopped",
                kind="workflow_stopped",
            )

        outputs = data.get("outputs", {})

        # 从工作流 outputs 提取
        image_urls = outputs.get("image_urls", [])
        if isinstance(image_urls, str):
            # 部分情况下 Dify 会返回 JSON 字符串
            import json
            try:
                image_urls = json.loads(image_urls)
            except json.JSONDecodeError:
                image_urls = []

        model_used = outputs.get("model_used", "unknown")

        if not image_urls:
            logger.warning(
                f"[dify-client] workflow returned no image_urls. "
                f"Outputs: {list(outputs.keys())}"
            )
            raise DifyError(
                "Workflow returned no images",
                kind="empty_result",
            )

        return DifyRunResult(
            image_urls=image_urls,
            model_used=model_used,
            workflow_run_id=data.get("workflow_run_id", ""),
            elapsed_seconds=elapsed,
            raw_response=data,
        )
```

---

## 异常定义（`app/core/exceptions.py`）

```python
"""backend/app/core/exceptions.py

统一异常定义（含错误分类）。
"""
from typing import Literal


DifyErrorKind = Literal[
    "config_error",          # 配置缺失/错误
    "auth_error",             # API Key 无效
    "workflow_not_found",     # Workflow ID 不存在
    "workflow_failed",        # Dify 工作流执行失败
    "workflow_stopped",       # 工作流被中止
    "http_error",             # 其他 HTTP 错误
    "timeout",                # 调用超时
    "connection_error",       # 连接失败
    "rate_limit",             # 限流
    "empty_result",           # 返回空结果
    "parse_error",            # 响应解析失败
]


class DifyError(Exception):
    """Dify 调用错误（含分类）"""

    def __init__(self, message: str, kind: DifyErrorKind = "unknown"):
        super().__init__(message)
        self.message = message
        self.kind = kind

    def __str__(self):
        return f"[{self.kind}] {self.message}"


class QuotaExceeded(Exception):
    """配额超限"""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class ServiceDegraded(Exception):
    """服务降级中（连续失败触发）"""

    def __init__(self, message: str = "服务暂时不可用，请稍后重试"):
        super().__init__(message)
        self.message = message
```

---

## 关键接口回顾

```python
@dataclass
class DifyConfig:
    """Dify 配置（来自 DifyConfigService.get_config）"""
    api_url: str                       # https://dify.peanuthzm.com.cn/v1
    app_api_key: str                   # app-xxxxxxxxxxxx
    workflow_text2img: str             # wf_xxx
    workflow_img2img: str              # wf_yyy
    workflow_inpaint: str              # wf_zzz
    workflow_upload_edit: str          # wf_aaa
    default_timeout: float             # 60.0

@dataclass
class DifyRunResult:
    image_urls: List[str]
    model_used: str
    workflow_run_id: str
    elapsed_seconds: float
    raw_response: Dict[str, Any]
```

---

## 测试要点（Phase 3 测试用例）

1. **mock DifyConfigService** — 返回固定 config
2. **mock httpx.AsyncClient** — 模拟成功响应 + 各种错误响应
3. **测试用例**：
   - test_text2img_success: 验证正确的 inputs 构造 + 响应解析
   - test_img2img_with_strength: 验证 strength 字段正确传递
   - test_workflow_404_raises_workflow_not_found
   - test_timeout_raises_timeout_error
   - test_empty_images_raises_empty_result
   - test_connection_success / failure

---

## 后续依赖

- Phase 2: `DifyConfigService`（提供 DifyConfig）
- Phase 4: `ImageGenQuotaService`（在 ImageGenService 调用 DifyClient 前预留配额）
- Phase 5: `ImageGenService`（编排 DifyClient + OSS + Quota + History）
- Phase 8: `ImageGenPromptPolisher`（润色提示词后传给 DifyClient）
