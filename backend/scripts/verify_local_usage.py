"""校验本机（指定设备）Token 用量数据与原生读取器是否完全一致

校验项：
1. 唯一键无重复（同一 user/device/date/source/model 只有一行）
2. **可重算**的行（源文件仍在本机）与原生读取器逐键完全相等
3. 孤儿行（源文件已被清理，无法重算）原样保留，未被误删
4. 各 source / 用户的总量汇总

用法（在 backend/ 目录下执行）:
    python -m scripts.verify_local_usage --device-id <uuid>
    python -m scripts.verify_local_usage --json
"""

import argparse
import json
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _freeze_sqlite(src: Path, dst: Path) -> bool:
    """用 SQLite backup API 为活动中的数据库取一致快照。"""
    if not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
        target = sqlite3.connect(str(dst))
        source.backup(target)
        target.close()
        source.close()
    except sqlite3.Error as exc:
        logger.warning("快照 %s 失败: %s", src, exc)
        return False
    return True


def _prepare_live_snapshots() -> tuple[Path, Path]:
    """为两个"活动写入"的 SQLite 来源建立冻结快照并切换读取路径。

    zcode 与 MiniMax Code 的数据库在本机持续被写入，同步写入值与校验读取值
    之间会有毫秒级漂移（属正常现象，非数据错误）。用同一份冻结快照同时
    读取，可让校验变成确定性的。
    """
    tmp = Path(tempfile.mkdtemp(prefix="token_usage_verify_"))

    zcode_home = tmp / "zcode"
    zcode_src = Path.home() / ".zcode" / "cli" / "db" / "db.sqlite"
    if _freeze_sqlite(zcode_src, zcode_home / "cli" / "db" / "db.sqlite"):
        os.environ["ZCODE_HOME"] = str(zcode_home)
        logger.info("zcode 使用冻结快照: %s", zcode_home)
    else:
        logger.info("zcode 无本地数据库，跳过快照（保持实时读取）")

    minimax_home = tmp / "minimax"
    minimax_src = Path.home() / ".minimax" / "v2" / "sqlite" / "runtime-state.sqlite"
    if _freeze_sqlite(minimax_src, minimax_home / "v2" / "sqlite" / "runtime-state.sqlite"):
        os.environ["MINIMAX_HOME"] = str(minimax_home)
        logger.info("minimax 使用冻结快照: %s", minimax_home)
    else:
        logger.info("minimax 无本地数据库，跳过快照（保持实时读取）")

    return tmp, zcode_home


def _sync_device_users(device_id: str, days: int) -> None:
    """用当前读取路径为该设备的全部用户重新同步一次（upsert，不删除）。"""
    from app.models.base import SessionLocal
    from app.models.token_usage_models import DeviceRegistry, TokenUsageRecord
    from app.services.token_usage_sync_service import sync_token_usage

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
    finally:
        db.close()

    for user_id in sorted(user_ids):
        try:
            sync_token_usage(user_id=user_id, days=days)
        except Exception as exc:  # pragma: no cover
            logger.error("[user=%s] 同步失败: %s", user_id, exc, exc_info=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 Token 用量数据与原生读取器的一致性")
    parser.add_argument("--device-id", type=str, default=None, help="默认使用本机设备 ID")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="跳过同步步骤（只做只读比对；活动写入的来源可能出现漂移）",
    )
    parser.add_argument(
        "--days", type=int, default=365, help="同步/校验覆盖的天数（默认 365）"
    )
    parser.add_argument(
        "--since", type=str, default="2000-01-01", help="校验起始日期 YYYY-MM-DD"
    )
    args = parser.parse_args()

    from app.models.base import SessionLocal
    from app.models.token_usage_models import TokenUsageRecord
    from app.utils.agent_readers import read_all_agents
    from app.utils.device_id import get_device_id
    from sqlalchemy import func

    device_id = args.device_id or get_device_id()
    since = date.fromisoformat(args.since)

    logger.info("校验设备: %s，起始日期 %s", device_id, since)

    snapshot_dir, _ = _prepare_live_snapshots()

    native = read_all_agents(since, date.today())
    # 原生读取器按 (日期,模型) 聚合；DB 也是 (日期,模型) 一行，
    # 因此逐键比较需要按 (日期,模型) 建索引
    native_keys: dict[tuple[str, str, str], int] = {
        (r["source"], r["record_date"].isoformat(), r["model"]): r["total_tokens"]
        for r in native["records"]
    }
    logger.info(
        "原生读取器产出 %s 条 (source,日期,模型) 记录", len(native_keys)
    )

    # 先用同一份快照重新同步一次，使 DB 值与校验值来自同一时点的数据。
    # zcode / MiniMax Code 的数据库在本机持续被写入，若不这样做，
    # "同步写入值"与"校验读取值"之间会有毫秒级漂移（属正常现象，非数据错误）。
    if not args.skip_sync:
        logger.info("基于冻结快照重新同步本机全部用户…")
        _sync_device_users(device_id, days=args.days)

    db = SessionLocal()
    try:
        # 1) 唯一键重复检查（全库，不限本设备）
        dup_rows = db.query(
            TokenUsageRecord.user_id,
            TokenUsageRecord.device_id,
            TokenUsageRecord.record_date,
            TokenUsageRecord.source,
            TokenUsageRecord.model,
            func.count().label("n"),
        ).group_by(
            TokenUsageRecord.user_id,
            TokenUsageRecord.device_id,
            TokenUsageRecord.record_date,
            TokenUsageRecord.source,
            TokenUsageRecord.model,
        ).having(func.count() > 1).all()
        duplicates = len(dup_rows)

        rows = db.query(
            TokenUsageRecord.user_id,
            TokenUsageRecord.source,
            TokenUsageRecord.record_date,
            TokenUsageRecord.model,
            TokenUsageRecord.total_tokens,
        ).filter(TokenUsageRecord.device_id == device_id).all()

        mismatches: list[dict] = []
        orphans: list[dict] = []
        matched = 0
        per_source: dict[str, int] = defaultdict(int)
        for user_id, source, record_date, model, total in rows:
            per_source[source] += total
            key = (source, record_date.isoformat(), model)
            expected = native_keys.get(key)
            if expected is None:
                orphans.append(
                    {
                        "user_id": user_id,
                        "source": source,
                        "record_date": record_date.isoformat(),
                        "model": model,
                        "total_tokens": total,
                    }
                )
            elif expected != total:
                mismatches.append(
                    {
                        "user_id": user_id,
                        "source": source,
                        "record_date": record_date.isoformat(),
                        "model": model,
                        "db_total": total,
                        "native_total": expected,
                        "diff": expected - total,
                    }
                )
            else:
                matched += 1

        orphan_totals: dict[str, int] = defaultdict(int)
        for row in orphans:
            orphan_totals[row["source"]] += row["total_tokens"]
    finally:
        db.close()

    shutil.rmtree(snapshot_dir, ignore_errors=True)

    report = {
        "device_id": device_id,
        "duplicate_unique_keys": duplicates,
        "rows_checked": len(rows),
        "matched": matched,
        "mismatched": len(mismatches),
        "orphaned": len(orphans),
        "per_source_totals": dict(per_source),
        "orphan_totals": dict(orphan_totals),
        "mismatches": mismatches[:40],
        "orphan_samples": orphans[:10],
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print("=" * 74)
        print(f"Token 用量一致性校验  设备 {device_id}")
        print("=" * 74)
        print(f"  全库唯一键重复数       : {duplicates}   {'✅' if duplicates == 0 else '❌'}")
        print(f"  本机行数               : {len(rows)}")
        print(f"  与原生读取器完全相等   : {matched}")
        print(f"  与原生读取器不一致     : {len(mismatches)}   {'✅' if not mismatches else '❌'}")
        print(f"  孤儿行（源文件已清理） : {len(orphans)}  （原样保留，未删除）")
        print("  各 source 总量:")
        for source, total in sorted(per_source.items()):
            print(f"     {source:<12} {total:>22,}")
        if mismatches:
            print("  不一致明细（前 10 条）:")
            for m in mismatches[:10]:
                print(
                    f"     {m['user_id'][:8]} {m['source']:<8} {m['record_date']} {m['model'][:20]:<20} "
                    f"db={m['db_total']:>16,} native={m['native_total']:>16,} diff={m['diff']:>16,}"
                )
        print("=" * 74)

    ok = duplicates == 0 and not mismatches
    print(">>> 结论:", "全部一致" if ok else "存在不一致")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
