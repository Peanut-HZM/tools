"""图像生成助手 Agent 种子

图像生成页面（多轮对话式图生）依赖一个专门角色的 Agent：
- 多轮对话探究用户意图（信息不足时禁止调用 image_gen，先追问）
- 信息足够时复述意图并调用 image_gen 生成
幂等：按 slug 查询，已存在则不覆盖（保护 admin 人工修改），
仅当被禁用时重新激活。
"""
import logging

from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)

IMAGE_GEN_AGENT_SLUG = "image-generation-assistant"

# 多轮意图探究的核心约束（system_prompt）
IMAGE_GEN_AGENT_SYSTEM_PROMPT = """你是"图像生成助手"，通过多轮对话理解用户的图像需求，并调用 image_gen 工具生成图片。

工作方式（必须严格遵守）：
1. **信息不足时禁止调用 image_gen 工具**。先通过对话澄清关键要素：
   - 主体内容（画什么）
   - 风格（写实/插画/水彩/3D/像素等）
   - 画幅比例（1:1 / 16:9 / 9:16 等）
   - 数量与用途（头像/海报/配图等）
2. 每轮最多追问 2-3 个关键问题，语气自然友好，避免审问感；用户已明确说明的要素不要重复问。
3. 信息足够后：先用一句话复述你理解的意图，然后**必须在同一个回复中立即调用 image_gen 工具**（operation=text2img，prompt 用具体、有画面感的中文描述，包含已确认的风格与比例要求）。严禁只输出文字说明而不调用工具——用户无需再确认，你的复述即是执行宣告。
4. 生成成功后：简短说明结果并附上图片链接（链接只能来自 image_gen 工具的返回）。
   **绝对禁止编造图片链接**：任何你没有通过调用 image_gen 工具实际获得的 URL 都是编造。
   即使对话历史里出现过图片链接，每一张新图片也必须实际调用工具生成——
   在文本里描述"已生成"而未调用工具是严重错误。
5. 生成失败时：说明可能原因，并建议用户调整需求后重试。

注意：不要在用户首次输入模糊需求时直接生成图片——先对话，再生成。"""


def ensure_image_gen_agent(db: DBSession):
    """确保图像生成助手 Agent 存在（幂等）。

    - 按 slug 查询；不存在则创建（public，所有用户可用）
    - 已存在时不覆盖任何字段（保护 admin 的人工修改）
    - 已存在但 is_active=False 时重新激活（保证页面可用）
    """
    from app.models.agent import Agent

    agent = db.query(Agent).filter(Agent.slug == IMAGE_GEN_AGENT_SLUG).first()
    if agent is not None:
        changed = False
        if not agent.is_active:
            agent.is_active = True
            changed = True
        # 未绑定图像模型时自动挂上当前可用的 image_gen 模型（首选 seedream 文生图）
        if not agent.default_model_id:
            _bind_image_models(db, agent)
            changed = True
        if changed:
            db.commit()
            db.refresh(agent)
            logger.info("图像生成助手 Agent 已更新: id=%s", agent.id)
        return agent

    agent = Agent(
        name="图像生成助手",
        slug=IMAGE_GEN_AGENT_SLUG,
        description="通过多轮对话理解你的图像需求：先澄清意图（主体/风格/比例/数量），再真实生成图片",
        system_prompt=IMAGE_GEN_AGENT_SYSTEM_PROMPT,
        icon="fa-palette",
        icon_color="bg-purple-500",
        category="AI工具",
    )
    agent.visibility = "public"
    agent.is_active = True
    agent.is_default = False
    db.add(agent)
    db.flush()
    _bind_image_models(db, agent)
    db.commit()
    db.refresh(agent)
    logger.info("图像生成助手 Agent 已创建: id=%s", agent.id)
    return agent


def _bind_image_models(db: DBSession, agent) -> None:
    """为 Agent 绑定可用的 image_gen 模型（默认模型 + fallback 链）

    排除明显不可用于文生图的条目（视频/3D 类模型名）；
    首选 seedream 文生图端点。
    """
    from app.models.llm_model import LLMModel

    models = (
        db.query(LLMModel)
        .filter(LLMModel.category == "image_gen", LLMModel.is_active == True)  # noqa: E712
        .all()
    )
    if not models:
        logger.warning("无可用 image_gen 模型，Agent 未绑定: agent=%s", agent.id)
        return

    def _rank(m):
        name = (m.model_name or "").lower()
        if "seedream" in name:
            return 0
        if any(k in name for k in ("t2v", "i2v", "r2v", "video", "3d", "seedance")):
            return 9  # 视频/3D 类排最后（运行时会被解析器跳过）
        return 5

    ordered = sorted(models, key=_rank)
    agent.default_model_id = ordered[0].id
    # JSONB 列需字符串（UUID 对象不可序列化）
    agent.fallback_model_ids = [str(m.id) for m in ordered[1:]]
    logger.info(
        "图像模型已绑定: agent=%s default=%s fallbacks=%d",
        agent.id, ordered[0].model_name, len(ordered) - 1,
    )
