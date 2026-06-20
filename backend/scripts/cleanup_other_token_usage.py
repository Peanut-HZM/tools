"""
Author: Peanut
Created: 2026-06-19
Purpose: 一次性清理 token_usage_records / token_usage_sync_log 中
         历史遗留的 source='other' 记录。仅手动执行一次。

用法:
    python scripts/cleanup_other_token_usage.py

会先打印待删除记录数，要求用户按 y 回车后才真正删除。
"""
import os
import sys

# 让脚本能 import app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.base import SessionLocal
from app.models.token_usage_models import TokenUsageRecord, TokenUsageSyncLog


def main() -> int:
    db = SessionLocal()
    try:
        records_count = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.source == "other")
            .count()
        )
        logs_count = (
            db.query(TokenUsageSyncLog)
            .filter(TokenUsageSyncLog.source == "other")
            .count()
        )
        print(
            f"即将删除: {records_count} 条 token_usage_records, "
            f"{logs_count} 条 token_usage_sync_log"
        )
        if records_count == 0 and logs_count == 0:
            print("没有需要清理的数据。")
            return 0

        answer = input("确认删除? (y/N): ").strip().lower()
        if answer != "y":
            print("已取消。")
            return 0

        records_deleted = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.source == "other")
            .delete(synchronize_session=False)
        )
        logs_deleted = (
            db.query(TokenUsageSyncLog)
            .filter(TokenUsageSyncLog.source == "other")
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"已删除 {records_deleted} 条 records, {logs_deleted} 条 sync_log")
        return 0
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130
    except Exception as exc:
        db.rollback()
        print(f"清理失败: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
