"""记忆向量回填任务

Phase 3 Plan-1B / Task 6

启动时扫描 `agent_memory_long_term` 表，对 embedding 为空的行生成 embedding 并写回。
- 批次大小：BATCH_SIZE (50)
- 批次间隔：BATCH_INTERVAL (1.0s)
- best-effort：失败仅 log，不抛异常
"""
import asyncio
import json
import logging
from typing import Optional

from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session as DBSession

from app.services.harness.embeddings.provider import EmbeddingProvider

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
BATCH_INTERVAL = 1.0  # seconds


async def backfill_memory_embeddings(
    db: DBSession,
    provider: EmbeddingProvider,
    batch_size: int = BATCH_SIZE,
    batch_interval: float = BATCH_INTERVAL,
) -> int:
    """回填缺失 embedding 的记忆行

    返回成功回填的行数。失败不抛异常，仅 log。
    """
    from app.models.agent_memory import AgentMemoryLongTerm

    try:
        total = (
            db.query(AgentMemoryLongTerm)
            .filter(AgentMemoryLongTerm.embedding.is_(None))
            .count()
        )
    except Exception as e:
        logger.warning("记忆向量回填：统计失败: %s", type(e).__name__)
        return 0

    if total == 0:
        logger.info("记忆向量回填：无需回填")
        return 0

    logger.info("记忆向量回填：发现 %d 条待处理记录", total)
    filled = 0
    # 软上限：避免极多行时启动期长跑（每批 1s × 200 批 = 200s 仍可接受）
    max_iterations = 200
    iteration = 0

    while filled < total and iteration < max_iterations:
        iteration += 1
        try:
            batch = (
                db.query(AgentMemoryLongTerm)
                .filter(AgentMemoryLongTerm.embedding.is_(None))
                .limit(batch_size)
                .all()
            )
        except Exception as e:
            logger.warning("记忆向量回填：查询批次失败: %s", type(e).__name__)
            break

        if not batch:
            break

        # 构造每行的文本（优先 text 字段，否则 JSON dump）
        texts = []
        for row in batch:
            value = row.value
            if isinstance(value, dict) and "text" in value:
                texts.append(str(value["text"])[:2000])
            else:
                texts.append(json.dumps(value, ensure_ascii=False)[:2000])

        try:
            vectors = await provider.embed(texts)
        except Exception as e:
            logger.warning(
                "回填 embedding 生成失败（已回填 %d 条）: %s",
                filled, type(e).__name__,
            )
            break

        if not vectors or len(vectors) != len(batch):
            logger.warning(
                "回填 embedding 返回数量不匹配（expected=%d, got=%d），中止",
                len(batch), len(vectors) if vectors else 0,
            )
            break

        # 逐行更新 + 单批 commit
        for row, vec in zip(batch, vectors):
            row.embedding = json.dumps(vec)
            filled += 1

        try:
            db.commit()
        except Exception as e:
            logger.error("回填 commit 失败: %s", type(e).__name__)
            try:
                db.rollback()
            except Exception:
                pass
            break

        logger.info("记忆向量回填：已完成 %d/%d", filled, total)

        if filled >= total:
            break

        # 批次间隔（避免对 EmbeddingProvider 触发限流）
        try:
            await asyncio.sleep(batch_interval)
        except asyncio.CancelledError:
            logger.info("记忆向量回填：任务被取消，已完成 %d/%d", filled, total)
            break

    if filled >= total:
        logger.info("记忆向量回填完成：%d/%d", filled, total)
    else:
        logger.warning(
            "记忆向量回填：提前结束，已完成 %d/%d（可能需要下次启动继续）",
            filled, total,
        )
    return filled


def count_pending_rows(db: DBSession) -> int:
    """统计缺失 embedding 的行数（用于启动判断是否需要回填）"""
    from app.models.agent_memory import AgentMemoryLongTerm
    try:
        return (
            db.query(AgentMemoryLongTerm)
            .filter(AgentMemoryLongTerm.embedding.is_(None))
            .count()
        )
    except Exception as e:
        logger.warning("统计待回填行数失败: %s", type(e).__name__)
        return 0


async def run_startup_backfill(db: DBSession) -> Optional[int]:
    """启动期回填入口：根据环境变量创建 provider，仅在有 API key 时执行

    返回实际回填的行数；未执行时返回 None。
    """
    import os

    api_key = (
        os.environ.get("EMBEDDING_API_KEY")
        or os.environ.get("OPENAI_API_KEY", "")
    )
    if not api_key:
        logger.info("记忆向量回填：未配置 EMBEDDING_API_KEY / OPENAI_API_KEY，跳过")
        return None

    try:
        from app.services.harness.embeddings.factory import create_embedding_provider
        provider = create_embedding_provider({
            "embedding_provider": "openai",
            "embedding_api_key": api_key,
        })
    except Exception as e:
        logger.warning("记忆向量回填：创建 provider 失败: %s", type(e).__name__)
        return None

    try:
        return await backfill_memory_embeddings(db, provider)
    except Exception as e:
        logger.error("记忆向量回填任务失败: %s", type(e).__name__)
        return None