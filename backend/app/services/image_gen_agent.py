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
4. 生成成功后：简短说明结果并附上图片链接。
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
        if not agent.is_active:
            agent.is_active = True
            db.commit()
            db.refresh(agent)
            logger.info("图像生成助手 Agent 已重新激活: id=%s", agent.id)
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
    db.commit()
    db.refresh(agent)
    logger.info("图像生成助手 Agent 已创建: id=%s", agent.id)
    return agent
