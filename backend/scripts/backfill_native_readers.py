"""按原生读取器口径回填/修正本机（指定设备）的 Token 用量历史

背景
    接入 Agent 原生读取器前，claude / codex / kimi 等来源的数据由 ccusage 采集，
    而项目当时安装的 ccusage 版本存在去重缺陷（同一请求被拆成多行时保留首条，
    首条常是 0 token 占位行），导致 Claude 用量被少计；zcode 来源则是把
    "含 cache 的 input" 当净输入累加，导致 cache 重复统计、总量虚高约 2 倍。

    本脚本用当前（已与 ccusage 最新版逐日对账零差异的）原生读取器重新同步，
    把**可重算**的历史行修正为正确值。

重要约束
    - **默认只做 upsert，不删除**。源文件已被本机清理的历史行（孤儿行）无法重算，
      删除会导致数据永久丢失，因此原样保留。
    - ``--drop-superseded`` **例外**：清理"被取代的占位行"。旧版同步曾把当天用量
      写成 ``model = '_total'`` 的聚合行（无法归属到具体模型）；原生读取器按模型
      产出后，同一天同一 source 会有"聚合行 + 按模型行"两份数据，汇总翻倍。
      只删"同 (用户, 设备, 日期, source) 下已存在按模型兄弟行"的占位行。
    - 通过业务层 ``sync_token_usage`` 写入，与页面「同步数据」按钮同一条路径。

用法（在 backend/ 目录下执行）:
    python -m scripts.backfill_native_readers --days 365
    python -m scripts.backfill_native_readers --days 365 --dry-run
    python -m scripts.backfill_native_readers --device-id <uuid>
    python -m scripts.backfill_native_readers --days 365 --drop-superseded
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


def _drop_superseded_placeholder_rows(
    device_id: str, user_ids: list[str], dry_run: bool = False
) -> int:
    """清理"被原生按模型行取代"的占位行。

    历史上有一次旧版同步把当天用量写成 ``model = '_total'`` 的聚合行（无法归属到
    具体模型）。原生读取器按模型产出后，同一天同一 source 会出现"聚合行 + 按模型行"
    两份数据，汇总时**翻倍**。

    判定条件（三者同时满足才认定为"被取代"）：
    1. ``model = '_total'`` 的占位行；
    2. 同一 (user_id, device_id, record_date, source) 下**已存在** model != '_total' 的行；
    3. 该行属于本次回填的目标设备与目标用户。

    只删被取代的占位行；源数据已清理、无法重算的历史行（没有按模型兄弟行）一律保留。
    """
    from app.models.base import SessionLocal
    from app.models.token_usage_models import TokenUsageRecord

    db = SessionLocal()
    try:
        placeholders = (
            db.query(TokenUsageRecord)
            .filter(
                TokenUsageRecord.device_id == device_id,
                TokenUsageRecord.user_id.in_(user_ids),
                TokenUsageRecord.model == "_total",
            )
            .all()
        )
        if not placeholders:
            logger.info("没有 _total 占位行，无需清理")
            return 0

        targets = []
        for row in placeholders:
            sibling = (
                db.query(TokenUsageRecord)
                .filter(
                    TokenUsageRecord.user_id == row.user_id,
                    TokenUsageRecord.device_id == row.device_id,
                    TokenUsageRecord.record_date == row.record_date,
                    TokenUsageRecord.source == row.source,
                    TokenUsageRecord.model != "_total",
                )
                .first()
            )
            if sibling is not None:
                targets.append(row)

        if not targets:
            logger.info("找到 %s 条 _total 占位行，但都没有对应的按模型行，全部保留", len(placeholders))
            return 0

        total_tokens = sum(int(row.total_tokens or 0) for row in targets)
        logger.info(
            "待清理的占位行 %s 条，合计 %s token：",
            len(targets),
            f"{total_tokens:,}",
        )
        for row in targets:
            logger.info(
                "   id=%s user=%s date=%s source=%s total=%s",
                row.id,
                row.user_id,
                row.record_date,
                row.source,
                f"{int(row.total_tokens or 0):,}",
            )

        if dry_run:
            logger.info("[dry-run] 不实际删除")
            return 0

        before = (
            db.query(TokenUsageRecord)
            .filter(
                TokenUsageRecord.device_id == device_id,
                TokenUsageRecord.user_id.in_(user_ids),
                TokenUsageRecord.model == "_total",
            )
            .count()
        )
        target_ids = [row.id for row in targets]
        deleted = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.id.in_(target_ids))
            .delete(synchronize_session=False)
        )
        db.commit()
        after = (
            db.query(TokenUsageRecord)
            .filter(
                TokenUsageRecord.device_id == device_id,
                TokenUsageRecord.user_id.in_(user_ids),
                TokenUsageRecord.model == "_total",
            )
            .count()
        )
        logger.info(
            "清理完成：删除 %s 条，_total 行数 %s → %s",
            deleted,
            before,
            after,
        )
        return deleted
    except Exception:
        db.rollback()
        logger.error("清理占位行失败，已回滚", exc_info=True)
        return 0
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
    parser.add_argument(
        "--drop-superseded",
        action="store_true",
        help=(
            "回填后清理被按模型行取代的 '_total' 占位行"
            "（旧版同步写入的聚合行，否则同一天会被重复统计两次）"
        ),
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
    logger.info("回填口径: 原生读取器")

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
                logger.warning(
                    "   - %s: %s", err.get("source"), str(err.get("error"))[:160]
                )
            invalidate_user_query_cache(user_id)
        except Exception as exc:  # pragma: no cover - 单个用户失败不影响其它
            logger.error("[user=%s] 回填失败: %s", user_id, exc, exc_info=True)
            failed.append((user_id, str(exc)))

    db = SessionLocal()
    try:
        db.commit()
    finally:
        db.close()

    if args.drop_superseded:
        removed = _drop_superseded_placeholder_rows(device_id, user_ids, dry_run=args.dry_run)
        logger.info("清理被取代的占位行：%s 条", removed)

    logger.info("=" * 60)
    logger.info("回填完成：用户 %s 个，写入合计 %s 条，失败 %s 个", len(user_ids), total_written, len(failed))
    for uid, err in failed:
        logger.error("  失败 user=%s: %s", uid, err)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
