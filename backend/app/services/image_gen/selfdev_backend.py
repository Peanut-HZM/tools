"""自研后端：用 AgentOrchestrator + ToolExecutor 完成对话 + 图像生成"""

from __future__ import annotations

import logging
import uuid

from app.services.image_gen.agent_orchestrator import AgentOrchestrator
from app.services.image_gen.base import BackendContext, BackendResult, IImageGenerationBackend
from app.services.image_gen.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


class SelfDevelopedBackend(IImageGenerationBackend):
    """自研图像生成后端"""

    def __init__(self, orchestrator: AgentOrchestrator, executor: ToolExecutor, conv_repo):
        self._orch = orchestrator
        self._exec = executor
        self._conv = conv_repo

    async def run(self, ctx: BackendContext) -> BackendResult:
        logger.info(f"[selfdev_backend] op={ctx.operation} user={ctx.user_id}")

        # 1. 加载或创建对话
        conversation_id = ctx.conversation_id or str(uuid.uuid4())
        if ctx.conversation_id:
            history = await self._conv.load(ctx.conversation_id)
        else:
            history = []

        # 2. 组装 messages：system + history + 当前用户输入
        system_msg = self._build_system_message(ctx)
        messages = [{"role": "system", "content": system_msg}] + history + [
            {"role": "user", "content": ctx.query}
        ]

        # 3. 跑 orchestrator
        tools = [self._generate_image_tool()]
        answer, tool_results = await self._orch.run(
            messages=messages,
            tools=tools,
            executor=self._exec,
        )

        # 4. 提取 image_urls
        image_urls: list[str] = []
        for r in tool_results:
            if "image_urls" in r:
                image_urls.extend(r["image_urls"])

        # 5. 保存对话
        messages.append({"role": "assistant", "content": answer})
        await self._conv.save(
            user_id=ctx.user_id,
            conversation_id=conversation_id,
            operation=ctx.operation,
            messages=messages[1:],  # 去掉 system
        )

        return BackendResult(
            image_urls=image_urls,
            answer_text=answer,
            conversation_id=conversation_id,
            model_used="",  # TODO: 从 OrderedLLMGateway 透出
            backend="selfdev",
        )

    def _build_system_message(self, ctx: BackendContext) -> str:
        """构造 system message"""
        return (
            "你是一个图像生成助手。用户会描述想生成的图像，你需要：\n"
            "1. 如果用户描述不够具体，可以追问（最多 2 轮）\n"
            "2. 当描述足够清晰时，调用 generate_image 工具生成图像\n"
            "3. 生成后简短回复用户\n"
            f"当前操作类型：{ctx.operation}"
        )

    def _generate_image_tool(self) -> dict:
        """generate_image tool 定义"""
        return {
            "type": "function",
            "function": {
                "name": "generate_image",
                "description": "生成或修改图像",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string", "enum": ["text2img", "img2img", "inpaint", "upload_edit"]},
                        "prompt": {"type": "string"},
                        "size": {"type": "string"},
                        "n": {"type": "integer"},
                        "reference_image_url": {"type": "string"},
                        "mask_image_url": {"type": "string"},
                        "strength": {"type": "number"},
                        "edit_type": {"type": "string"},
                    },
                    "required": ["operation", "prompt"],
                },
            },
        }
