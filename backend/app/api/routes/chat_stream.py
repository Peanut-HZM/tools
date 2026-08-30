"""
流式对话接口（Task 16：AgentRuntime 接入）

Phase 1 兼容策略：
- 外部 SSE 形状不变（前端兼容）：user_message / chunk / done / error
- 内部使用 AgentRuntime 驱动 LLM 调用
- AgentRuntime 内部事件（thinking / tool_call / handoff / guardrail）暂不暴露给前端

v1 起已迁移到 LLMProvider + LLMModel（原 llm_configs 表仅保留用于回滚过渡）。
"""

import json
import uuid
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.services.conversation_service import ConversationService, MessageService
from app.services.agent_management_service import AgentService as AgentManagementService
from app.services.llm_quota_service import LLMQuotaService

from app.services.harness.agent_runtime import AgentRuntime
from app.services.harness.llm_bridge import LLMFunctionBridge
from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tool_registry import ToolRegistry
from app.services.harness.tools.image_gen import ImageGenTool
from app.services.oss_service import oss_service
from app.services.harness.tools.memory_read import MemoryReadTool
from app.services.harness.tools.skill_save import SkillSaveTool
from app.services.harness.tools.skill_read import SkillReadTool
from app.services.harness.tools.skill_delete import SkillDeleteTool
from app.services.harness.tools.file_read import FileReadTool
from app.services.harness.tools.file_write import FileWriteTool
from app.services.harness.tools.file_list import FileListTool
from app.services.harness.tools.code_execute import CodeExecuteTool
from app.services.harness.tools.memory_search import MemorySearchTool
from app.services.harness.tools.memory_write import MemoryWriteTool
from app.services.harness.session import Session as HarnessSession
from app.services.harness.trace_recorder import TraceRecorder
from app.services.llm.ordered_gateway import OrderedLLMGateway

logger = logging.getLogger(__name__)


def _can_use_agent(agent, user: dict) -> bool:
    """P2-④: 聊天入口的 Agent 可见性校验。

    - public / unlisted：所有登录用户可用
    - private：仅 owner 或 admin 可用（owner_id 为空时仅 admin）
    """
    visibility = getattr(agent, "visibility", "public") or "public"
    if visibility != "private":
        return True
    owner_id = getattr(agent, "owner_id", None)
    if owner_id is not None and str(owner_id) == str(user.get("id")):
        return True
    return user.get("role") == "admin"

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/{conversation_id}/chat/stream")
async def chat_stream(
    conversation_id: uuid.UUID,
    request: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    流式对话接口
    使用 SSE (Server-Sent Events) 实时返回 AI 生成的内容

    Phase 1（Task 16）：内部使用 AgentRuntime，外部 SSE 形状保持兼容。
    """
    content = request.get("content", "")
    llm_config_id = request.get("llm_config_id")
    agent_id = request.get("agent_id")

    # 1. 验证会话所有权
    conv_service = ConversationService(db)
    conversation = conv_service.get_conversation(conversation_id, current_user["id"])
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 2. 创建用户消息
    msg_service = MessageService(db)
    user_message = msg_service.create_message(
        conversation_id=conversation_id, sender_type="user", content=content
    )
    user_msg_dict = {
        "id": str(user_message.id),
        "conversation_id": str(user_message.conversation_id),
        "sender_type": user_message.sender_type,
        "content": user_message.content,
        "message_type": user_message.message_type,
        "sent_at": user_message.sent_at.isoformat() if user_message.sent_at else None,
    }

    # 3. quota 预占
    quota_svc = LLMQuotaService(db)
    planned = (len(content) * 100) // 4
    res_id = quota_svc.check_and_reserve(
        user_id=current_user["id"],
        category="text",
        planned_tokens=planned,
    )

    # 4. 加载 Agent（优先级：请求指定 > 会话绑定 > 默认 Agent）
    agent_service = AgentManagementService(db)
    if agent_id:
        agent = agent_service.get_agent(agent_id)
    elif getattr(conversation, "agent_id", None):
        agent = agent_service.get_agent(conversation.agent_id)
    else:
        agent = agent_service.get_default_agent()

    # P2-④: 可见性校验（private 仅 owner/admin 可用）
    if agent and not _can_use_agent(agent, current_user):
        raise HTTPException(status_code=403, detail="该 Agent 为私有，无权使用")
    if not agent:
        try:
            quota_svc.rollback(res_id)
        except Exception:
            pass
        raise HTTPException(status_code=503, detail="没有可用的 Agent")

    # 5. 构建 harness pipeline
    llm_gateway = OrderedLLMGateway(db)
    llm_bridge = LLMFunctionBridge(llm_gateway)
    tool_registry = ToolRegistry(db)
    # 注册内置工具（按需注册）
    tool_registry.register_builtin(ImageGenTool())
    # 注册内存工具（按 Agent.memory_long_term_enabled 控制可用性）
    tool_registry.register_builtin(MemoryReadTool())
    tool_registry.register_builtin(MemoryWriteTool())
    tool_registry.register_builtin(MemorySearchTool())
    # 注册技能工具（按 Agent.memory_procedural_enabled 控制可用性）
    tool_registry.register_builtin(SkillSaveTool())
    tool_registry.register_builtin(SkillReadTool())
    tool_registry.register_builtin(SkillDeleteTool())
    # 注册沙箱工具（按 Agent.sandbox_enabled 控制可用性）
    tool_registry.register_builtin(FileReadTool())
    tool_registry.register_builtin(FileWriteTool())
    tool_registry.register_builtin(FileListTool())
    tool_registry.register_builtin(CodeExecuteTool())
    trace_recorder = TraceRecorder(db)

    # 加载对话历史到 Session（best-effort）
    harness_session = _init_harness_session(db, conversation, agent, conversation_id)

    ctx = ToolContext(
        user_id=current_user["id"],
        conversation_id=conversation_id,
        agent_id=str(agent.id),
        session=harness_session,
        db=db,
        oss_service=oss_service,
        llm_gateway=llm_gateway,
        event_emitter=None,
        quota_service=quota_svc,
        trace_recorder=trace_recorder,
        cancel_event=None,
    )
    # P3 图生页面：绑定 agent（image_gen 工具靠 ctx.agent 解析图像模型链）
    ctx.agent = agent

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, harness_session, ctx)

    async def generate_stream():
        # 错误状态下跳过后续 Event（runtime 在 error 后仍可能 yield done with fallback）
        errored = False
        # 本轮 image_gen 成功产生的附件（写入 done 的 agent 消息，刷新后可持久显示）
        image_attachments = []
        try:
            # 1. user_message
            yield (
                f"data: {json.dumps({'type': 'user_message', 'data': user_msg_dict}, ensure_ascii=False)}\n\n"
            )

            # 2. 驱动 runtime，映射 Event → 外部 SSE 形状
            async for event in runtime.run(content):
                if event.type == "text_delta":
                    text = event.payload.get("text", "")
                    yield (
                        f"data: {json.dumps({'type': 'chunk', 'content': text}, ensure_ascii=False)}\n\n"
                    )

                elif event.type == "error":
                    err_msg = event.payload.get("message", "未知错误")
                    errored = True
                    try:
                        quota_svc.rollback(res_id)
                    except Exception:
                        pass
                    yield (
                        f"data: {json.dumps({'type': 'error', 'message': err_msg}, ensure_ascii=False)}\n\n"
                    )

                elif event.type == "done":
                    if errored:
                        # 错误状态后跳过 done SSE（fallback 文本不暴露给前端）
                        continue

                    final_text = event.payload.get("final_text", "")
                    final_usage = event.payload.get("usage") or {}

                    prompt_tokens = int(final_usage.get("prompt_tokens") or 0)
                    completion_tokens = int(final_usage.get("completion_tokens") or 0)
                    total_tokens = int(
                        final_usage.get("total_tokens")
                        or (prompt_tokens + completion_tokens)
                    )
                    llm_model_name = final_usage.get("model") or "unknown"

                    # 写 agent message 到 Message 表
                    agent_message = msg_service.create_message(
                        conversation_id=conversation_id,
                        sender_type="agent",
                        content=final_text,
                    )
                    agent_message.prompt_tokens = prompt_tokens
                    agent_message.completion_tokens = completion_tokens
                    agent_message.total_tokens = total_tokens
                    # P3 图生页面：持久化本轮生成的图片附件（刷新后仍可显示）
                    if image_attachments:
                        agent_message.attachments = image_attachments
                    if llm_config_id:
                        agent_message.llm_config_id = llm_config_id
                    agent_message.llm_model_name = llm_model_name
                    db.commit()

                    # quota 校正
                    quota_svc.record_usage(
                        user_id=current_user["id"],
                        category="text",
                        actual_tokens=total_tokens,
                        reservation_id=res_id,
                        model_used=llm_model_name,
                    )

                    # 幻觉链接防护：模型可能模仿历史编造 image-gen OSS 链接
                    # （文本声称已生成但实际未调用工具）。此类链接替换为无效提示，
                    # 避免用户点击 404。真实链接集合来自本轮 tool_result 附件。
                    if final_text and "image-gen/" in final_text:
                        import re as _re

                        real_urls = {
                            a.get("url") for a in image_attachments if a.get("url")
                        }

                        def _flag_hallucinated(m):
                            return (
                                m.group(0)
                                if m.group(0) in real_urls
                                else "⚠️（该链接无效：图片未实际生成，请重新发起生成请求）"
                            )

                        final_text = _re.sub(
                            r"https://[^\s)\]]*/image-gen/[0-9a-f]{32}\.png",
                            _flag_hallucinated,
                            final_text,
                        )
                        agent_message.content = final_text

                    agent_msg_dict = {
                        "id": str(agent_message.id),
                        "conversation_id": str(agent_message.conversation_id),
                        "sender_type": agent_message.sender_type,
                        "content": agent_message.content,
                        "message_type": agent_message.message_type,
                        "sent_at": agent_message.sent_at.isoformat()
                        if agent_message.sent_at
                        else None,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "llm_model_name": llm_model_name,
                        # P3 图生页面：本轮生成的图片附件（前端刷新后仍可显示）
                        "attachments": image_attachments or [],
                    }

                    yield (
                        f"data: {json.dumps({'type': 'done', 'data': agent_msg_dict}, ensure_ascii=False)}\n\n"
                    )

                elif event.type == "tool_call_start":
                    # P3 图生页面：转发工具调用开始事件（Task 19 最小集）
                    # 注意：Event payload 为扁平结构 {id, name, arguments}
                    start_data = {
                        "id": event.payload.get("id"),
                        "name": event.payload.get("name", ""),
                        "arguments": event.payload.get("arguments", {}),
                    }
                    yield (
                        f"data: {json.dumps({'type': 'tool_call_start', 'data': start_data}, ensure_ascii=False, default=str)}\n\n"
                    )

                elif event.type == "tool_result":
                    # P3 图生页面：转发工具结果事件
                    # 注意：Event payload 为扁平结构
                    # {id, name, success, content_type, content, attachments, error}
                    atts = list(event.payload.get("attachments") or [])
                    if event.payload.get("name") == "image_gen" and event.payload.get("success"):
                        image_attachments.extend(atts)
                    result_content = event.payload.get("content")
                    # content 截断 4KB，避免 SSE 过大（注意勿遮蔽外层请求 content）
                    if isinstance(result_content, (dict, list)):
                        content_out = json.loads(
                            json.dumps(result_content, ensure_ascii=False, default=str)[:4096]
                        )
                    else:
                        content_out = str(result_content or "")[:4096]
                    result_data = {
                        "id": event.payload.get("id"),
                        "name": event.payload.get("name", ""),
                        "success": bool(event.payload.get("success", False)),
                        "content_type": event.payload.get("content_type", ""),
                        "content": content_out,
                        "attachments": atts,
                        "error": event.payload.get("error"),
                    }
                    yield (
                        f"data: {json.dumps({'type': 'tool_result', 'data': result_data}, ensure_ascii=False, default=str)}\n\n"
                    )

                # 其余事件（thinking_delta / guardrail_triggered / handoff /
                # text_complete）仍不暴露给前端（后续按需扩展）

        except Exception as e:
            # 脱敏：不将 str(e) 暴露给前端，避免泄露 DB schema / 第三方 key / stack 片段
            logger.error(f"chat_stream error: {e}", exc_info=True)
            try:
                if not errored:
                    quota_svc.rollback(res_id)
            except Exception:
                pass
            if not errored:
                yield (
                    f"data: {json.dumps({'type': 'error', 'message': '服务内部错误，请稍后重试'}, ensure_ascii=False)}\n\n"
                )

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _init_harness_session(
    db: Session,
    conversation: Any,
    agent: Any,
    conversation_id: str,
) -> HarnessSession:
    """创建 HarnessSession 并填充历史消息。

    best-effort：查询失败不阻断请求。
    """
    harness_session = HarnessSession(conversation, agent)
    try:
        from app.models.message import Message as MessageORM
        # 按 agent 配置截断历史消息（默认 20），避免长会话下加载过多上下文
        window = getattr(agent, "memory_short_term_window", 20) or 20
        history_msgs = (
            db.query(MessageORM)
            .filter_by(conversation_id=conversation_id)
            .order_by(MessageORM.sent_at.desc())
            .limit(window)
            .all()
        )
        history_msgs = list(reversed(history_msgs))  # 恢复时间升序
        # 为每条历史消息注入 role 属性（runtime 的 _build_messages_for_llm 依赖此字段）
        for m in history_msgs:
            m.role = "user" if m.sender_type == "user" else "assistant"
        harness_session.messages = list(history_msgs)
    except Exception as e:
        logger.error(f"加载对话历史失败: {e}", exc_info=True)
    return harness_session
