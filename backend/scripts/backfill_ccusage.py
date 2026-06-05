"""一次性全量回填脚本 — 部署时跑一次。

在 backend/ 目录下执行（确保 app.* 绝对导入可解析）:
    cd backend
    python -m scripts.backfill_ccusage
    python -m scripts.backfill_ccusage --since 2024-01-01 --batch-days 90
"""
import argparse
import logging
import os
import sys
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="全量回填 ccusage 数据")
    parser.add_argument("--since", default="2024-01-01", help="起始日期 YYYY-MM-DD")
    parser.add_argument("--batch-days", type=int, default=90, help="每批天数")
    args = parser.parse_args()

    from app.models.base import SessionLocal
    from app.services.token_usage_sync_service import sync_token_usage_v2
    from app.utils.device_id import get_device_id, get_device_display_name

    today = date.today()
    since = date.fromisoformat(args.since)
    total_synced = 0
    cursor = since

    while cursor <= today:
        until = min(cursor + timedelta(days=args.batch_days - 1), today)
        logger.info(f"回填 {cursor.isoformat()} ~ {until.isoformat()} ...")
        db = SessionLocal()
        try:
            count = sync_token_usage_v2(
                db=db,
                user_id="system_backfill",
                device_id=get_device_id(),
                device_name=get_device_display_name(),
                since=cursor.isoformat(),
                until=until.isoformat(),
            )
            total_synced += count
            logger.info(f"  本批同步 {count} 条")
        except Exception as e:
            logger.error(f"  本批失败: {e}", exc_info=True)
        finally:
            db.close()
        cursor = until + timedelta(days=1)

    logger.info(f"回填完成: 总计 {total_synced} 条")


if __name__ == "__main__":
    main()
