"""图生验收脚本：真实调用 ImageGenTool（真实 gateway → 火山方舟 provider）

验收标准（spec §3.2）：
1. result.success == True 且 content.image_urls 非空
2. 每个 URL 可下载（HTTP 200 且 Content-Type 为 image/*）

用法：cd backend && .venv/Scripts/python scripts/acceptance_image_gen.py
"""
import asyncio
import sys

sys.path.insert(0, ".")

import httpx

from app.models import get_db
from app.models.llm_model import LLMModel
from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.image_gen import ImageGenTool
from app.services.llm.ordered_gateway import OrderedLLMGateway


async def main() -> int:
    db = next(get_db())

    # 全部激活的 image_gen 模型进 fallback 链，由工具自行故障转移
    # （个别条目可能是误挂类目的视频模型，靠 failover 跳过）
    models = (
        db.query(LLMModel)
        .filter(LLMModel.category == "image_gen", LLMModel.is_active == True)  # noqa: E712
        .all()
    )
    if not models:
        print("FAIL: 无激活的 image_gen 模型")
        return 1
    print("候选图像模型:", [m.name for m in models])

    # 构造最小 Agent 上下文（鸭子类型即可，工具只读这几个属性）
    class _Agent:  # noqa: D401
        id = "acceptance-agent"
        default_model_id = models[0].id
        fallback_model_ids = [m.id for m in models[1:]]

    gateway = OrderedLLMGateway(db)
    tool = ImageGenTool()
    ctx = ToolContext(
        user_id="00000000-0000-0000-0000-000000000001",
        conversation_id="00000000-0000-0000-0000-000000000002",
        agent_id="acceptance-agent",
        session=None,
        db=db,
        llm_gateway=gateway,
        event_emitter=None,
        quota_service=None,
        trace_recorder=None,
        cancel_event=None,
    )
    ctx.agent = _Agent()  # 工具通过 getattr(ctx, "agent") 读取模型链

    result = await tool.execute(
        {
            "prompt": "一只橙色的猫坐在窗台上看夕阳，写实摄影风格，16:9",
            "operation": "text2img",
            "count": 1,
        },
        ctx,
    )

    if not result.success:
        print(f"FAIL: 生成失败: {result.error_message}")
        return 1

    urls = (result.content or {}).get("image_urls", [])
    print(f"生成成功: {len(urls)} 张图")
    for u in urls:
        print(f"  URL: {u}")

    if not urls:
        print("FAIL: 无图片 URL")
        return 1

    # 下载校验：必须 HTTP 200 且 Content-Type 为 image/*
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        for u in urls:
            resp = await client.get(u)
            ctype = resp.headers.get("content-type", "")
            ok = resp.status_code == 200 and ctype.startswith("image/")
            print(f"  下载校验: {u[:80]}... → HTTP {resp.status_code} {ctype} {'OK' if ok else 'FAIL'}")
            if not ok:
                return 1

    print("ACCEPTANCE PASS: 图片真实生成成功且可下载")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
