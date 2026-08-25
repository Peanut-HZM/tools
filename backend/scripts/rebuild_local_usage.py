"""重建本机最近的 Token 用量数据 — 修复多 agent 共用模型时归属错乱的历史数据。

背景：
    旧版 v2 同步使用"模型归属推断"（_infer_agent），当 claude 与 opencode
    同一天使用同一模型时，该模型全部用量被归入 claude，导致 opencode 数据丢失；
    同时 claude 遗留路径用合并 daily（全 agent 合计）写 claude 记录，数据被污染。
    新版同步已改为直接使用各 agent 自己的 daily 模型明细，本脚本用于把
    本机历史数据重建为精确数据。

用法（在 backend/ 目录下执行）:
    python -m scripts.rebuild_local_usage
    python -m scripts.rebuild_local_usage --days 90 --dry-run
"""
import argparse
import logging
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 重建时涉及的来源（本机可能写入的 agent）
SOURCES = ("claude", "opencode", "codex")


def main():
    parser = argparse.ArgumentParser(description="重建本机 Token 用量历史数据")
    parser.add_argument("--days", type=int, default=90, help="重建最近 N 天（默认 90）")
    parser.add_argument("--dry-run", action="store_true", help="只打印将删除的记录数，不实际执行")
    args = parser.parse_args()

    from app.models.base import SessionLocal
    from app.models.token_usage_models import TokenUsageRecord, DeviceRegistry
    from app.services.token_usage_sync_service import sync_token_usage
    from app.services.token_usage_cache import invalidate_user_query_cache
    from app.utils.device_id import get_device_id

    device_id = get_device_id()
    today = date.today()
    since = today - timedelta(days=args.days - 1)
    logger.info(f"本机 device_id: {device_id}, 重建范围: {since} ~ {today}")

    db = SessionLocal()
    try:
        # 找出本机 device 关联的所有用户
        user_ids = set()
        rows = db.query(DeviceRegistry.user_id).filter(
            DeviceRegistry.device_id == device_id
        ).distinct().all()
        user_ids.update(r[0] for r in rows)
        rows = db.query(TokenUsageRecord.user_id).filter(
            TokenUsageRecord.device_id == device_id
        ).distinct().all()
        user_ids.update(r[0] for r in rows)
        user_ids = {u for u in user_ids if u and u != "system"}
        logger.info(f"本机关联用户: {sorted(user_ids) or '无'}")
    finally:
        db.close()

    for user_id in sorted(user_ids):
        db = SessionLocal()
        try:
            query = db.query(TokenUsageRecord).filter(
                TokenUsageRecord.user_id == user_id,
                TokenUsageRecord.device_id == device_id,
                TokenUsageRecord.record_date >= since,
                TokenUsageRecord.record_date <= today,
                TokenUsageRecord.source.in_(SOURCES),
            )
            existing_count = query.count()

            if args.dry_run:
                logger.info(
                    f"[user={user_id}] dry-run: 将删除 {existing_count} 条旧记录"
                    f"（{since} ~ {today}），跳过实际执行"
                )
                continue

            deleted = query.delete(synchronize_session=False)
            db.commit()
            logger.info(f"[user={user_id}] 已删除 {deleted} 条旧记录（{since} ~ {today}）")

            result = sync_token_usage(user_id=user_id, days=args.days)
            invalidate_user_query_cache(user_id)
            logger.info(
                f"[user={user_id}] 重建完成: 写入 {result.get('total_records')} 条, "
                f"错误 {len(result.get('errors') or [])} 个"
            )
            for err in result.get("errors") or []:
                logger.warning(f"  - {err.get('source')}: {err.get('error')}")
        except Exception as e:
            logger.error(f"[user={user_id}] 重建失败: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

    logger.info("本机数据重建流程结束")


if __name__ == "__main__":
    main()
