"""按原生读取器口径回填/修正本机（指定设备）的 Token 用量历史

背景
    接入 Agent 原生读取器前，claude / codex / kimi 等来源的数据由 ccusage 采集，
    而项目当时安装的 ccusage 版本存在去重缺陷（同一请求被拆成多行时保留首条，
    首条常是 0 token 占位行），导致 Claude 用量被少计；zcode 来源则是把
    "含 cache 的 input" 当净输入累加，导致 cache 重复统计、总量虚高约 2 倍。

    本脚本用当前（已与 ccusage 最新版逐日对账零差异的）原生读取器重新同步，
    把**可重算**的历史行修正为正确值。

重要约束
    - **只做 upsert，不删除**。源文件已被本机清理的历史行（孤儿行）无法重算，
      删除会导致数据永久丢失，因此原样保留。
    - 通过业务层 ``sync_token_usage`` 写入，与页面「同步数据」按钮同一条路径。

用法（在 backend/ 目录下执行）:
    python -m scripts.backfill_native_readers --days 365
    python -m scripts.backfill_native_readers --days 365 --dry-run
    python -m scripts.backfill_native_readers --device-id <uuid>
"""

import argparse
import logging
import sys
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _resolve_device_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    from app.utils.device_id import get_device_id

    return get_device_id()


def _find_users(device_id: str) -> list[str]:
    """找出与该设备关联的所有用户。

    两个来源取并集：
    - device_registry：曾在该设备上登录过的用户
    - token_usage_records：已有该设备数据的用户（可能未登记指纹）
    """
    from app.models.base import SessionLocal
    from app.models.token_usage_models import DeviceRegistry, TokenUsageRecord

    db = SessionLocal()
    try:
        user_ids: set[str] = set()
        for (uid,) in db.query(DeviceRegistry.user_id).filter(
            DeviceRegistry.device_id == device_id
        ).distinct().all():
            if uid:
                user_ids.add(uid)
        for (uid,) in db.query(TokenUsageRecord.user_id).filter(
            TokenUsageRecord.device_id == device_id
        ).distinct().all():
            if uid:
                user_ids.add(uid)
        return sorted(user_ids)
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="用原生读取器口径回填/修正指定设备的 Token 用量历史（只 upsert，不删除）"
    )
    parser.add_argument("--days", type=int, default=365, help="回填最近 N 天（默认 365）")
    parser.add_argument(
        "--device-id", type=str, default=None, help="指定设备 ID；默认使用本机设备 ID"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="只列出将要同步的用户，不实际写入"
    )
    parser.add_argument(
        "--only-user", type=str, default=None, help="只同步指定用户（调试用）"
    )
    args = parser.parse_args()

    device_id = _resolve_device_id(args.device_id)
    logger.info("目标设备: %s", device_id)

    user_ids = _find_users(device_id)
    if args.only_user:
        user_ids = [u for u in user_ids if u == args.only_user]
    logger.info("关联用户 %s 个: %s", len(user_ids), ", ".join(user_ids) or "无")

    if not user_ids:
        logger.warning("没有关联用户，无需回填")
        return 0

    from app.models.base import SessionLocal
    from app.services.token_usage_cache import invalidate_user_query_cache
    from app.services.token_usage_sync_service import sync_token_usage

    days = max(1, args.days)
    today = date.today()
    since = today - timedelta(days=days - 1)
    logger.info("回填范围: %s ~ %s", since, today)

    total_written = 0
    failed: list[tuple[str, str]] = []
    for user_id in user_ids:
        if args.dry_run:
            logger.info("[dry-run] 将同步用户 %s", user_id)
            continue
        try:
            result = sync_token_usage(user_id=user_id, days=days)
            written = result.get("total_records") or 0
            total_written += written
            errors = result.get("errors") or []
            logger.info(
                "[user=%s] 写入 %s 条，来源 %s，错误 %s 个",
                user_id,
                written,
                result.get("sources_synced"),
                len(errors),
            )
            for err in errors[:3]:
                logger.warning("   - %s: %s", err.get("source"), str(err.get("error"))[:160])
            invalidate_user_query_cache(user_id)
        except Exception as exc:  # pragma: no cover - 单个用户失败不影响其它
            logger.error("[user=%s] 回填失败: %s", user_id, exc, exc_info=True)
            failed.append((user_id, str(exc)))

    db = SessionLocal()
    try:
        db.commit()
    finally:
        db.close()

    logger.info("=" * 60)
    logger.info("回填完成：用户 %s 个，写入合计 %s 条，失败 %s 个", len(user_ids), total_written, len(failed))
    for uid, err in failed:
        logger.error("  失败 user=%s: %s", uid, err)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
