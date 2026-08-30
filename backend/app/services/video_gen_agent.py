"""视频生成助手 Agent 种子

视频生成页面（多轮对话式视频生成）依赖一个专门角色的 Agent：
- 多轮对话探究用户意图（信息不足时先追问）
- 信息足够时复述意图并调用 video_gen 工具生成视频
幂等：按 slug 查询，已存在则不覆盖。
"""
import logging

from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)

VIDEO_GEN_AGENT_SLUG = "video-generation-assistant"

VIDEO_GEN_AGENT_SYSTEM_PROMPT = """你是"视频生成助手"，通过多轮对话理解用户的视频需求，并调用 video_gen 工具生成短视频。

工作方式（必须严格遵守）：
1. **信息不足时禁止调用 video_gen 工具**。先通过对话澄清关键要素：
   - 视频内容（什么场景/故事/画面）
   - 风格（写实/动漫/3D/水墨/赛博朋克等）
   - 画幅比例（16:9 横屏 / 9:16 竖屏 / 1:1 方形等）
   - 时长偏好（4-15 秒）
   - 分辨率（480P/768P/2K）
2. 每轮最多追问 2-3 个关键问题，语气自然友好；用户已明确的要素不要重复问。
3. 信息足够后：先用一句话复述你理解的意图，然后**必须在同一个回复中立即调用 video_gen 工具**。严禁只输出文字说明而不调用工具。

提示词工程（调用 video_gen 前必须完成）：
- **推断意图**：从用户描述推断画面预期（如"动漫战斗"→ 动作感强烈、特效丰富、镜头切换快）。
- **扩写 prompt**：把简短描述扩写为有画面感的详细视频描述，依次覆盖：
  主体动作与细节 → 场景环境 → 镜头运动（推/拉/摇/跟/航拍） → 光线氛围 →
  视觉风格与色调 → 节奏感与情绪。
- **硬约束原样保留**：用户明确指定的风格/比例/时长，必须原样体现在 prompt 与参数中。
- 系统会对 prompt 做专业润色，你只需保证意图完整无歧义。
4. 生成成功后：简短说明结果并附上视频（链接只能来自 video_gen 工具返回）。
   **绝对禁止编造视频链接**。
5. 生成失败时：说明可能原因并建议调整需求后重试。

注意：不要在用户首次输入模糊需求时直接生成——先对话，再生成。"""


def ensure_video_gen_agent(db: DBSession):
    """确保视频生成助手 Agent 存在（幂等）"""
    from app.models.agent import Agent

    agent = db.query(Agent).filter(Agent.slug == VIDEO_GEN_AGENT_SLUG).first()
    if agent is not None:
        changed = False
        if not agent.is_active:
            agent.is_active = True
            changed = True
        if not agent.default_model_id:
            _bind_video_models(db, agent)
            changed = True
        if changed:
            db.commit()
            db.refresh(agent)
            logger.info("视频生成助手 Agent 已更新: id=%s", agent.id)
        return agent

    agent = Agent(
        name="视频生成助手",
        slug=VIDEO_GEN_AGENT_SLUG,
        description="通过多轮对话理解你的视频需求：先澄清意图（内容/风格/比例/时长），再真实生成视频",
        system_prompt=VIDEO_GEN_AGENT_SYSTEM_PROMPT,
        icon="fa-video",
        icon_color="bg-blue-500",
        category="AI工具",
    )
    agent.visibility = "public"
    agent.is_active = True
    agent.is_default = False
    db.add(agent)
    db.flush()
    _bind_video_models(db, agent)
    db.commit()
    db.refresh(agent)
    logger.info("视频生成助手 Agent 已创建: id=%s", agent.id)
    return agent


def _bind_video_models(db: DBSession, agent) -> None:
    """为 Agent 绑定可用的 video_gen 模型"""
    from app.models.llm_model import LLMModel

    # 优先找 video_gen 分类
    models = (
        db.query(LLMModel)
        .filter(LLMModel.category == "video_gen", LLMModel.is_active == True)  # noqa: E712
        .all()
    )

    if not models:
        logger.warning("无可用 video_gen 模型，Agent 未绑定: agent=%s", agent.id)
        return

    def _rank(m):
        name = (m.model_name or "").lower()
        if "h3-max" in name or "max" in name:
            return 0  # Max 版本优先（生成更快）
        if "h3" in name:
            return 1
        return 5

    ordered = sorted(models, key=_rank)
    agent.default_model_id = ordered[0].id
    agent.fallback_model_ids = [str(m.id) for m in ordered[1:]]
    logger.info(
        "视频模型已绑定: agent=%s default=%s fallbacks=%d",
        agent.id, ordered[0].model_name, len(ordered) - 1,
    )
