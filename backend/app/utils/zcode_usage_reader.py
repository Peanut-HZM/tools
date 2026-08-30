"""ZCode Token 用量读取器

从 ZCode 本地 SQLite 数据库（~/.zcode/cli/db/db.sqlite）读取 model_usage 表，
按 (日期, 模型) 聚合后输出与 ccusage 一致的 record 格式，供 sync_token_usage 写入。
"""

import logging
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _find_zcode_db() -> Optional[str]:
    """定位 ZCode CLI 数据库文件路径。"""
    home = Path.home()
    candidates = [
        home / ".zcode" / "cli" / "db" / "db.sqlite",
    ]
    # Windows: 也检查 AppData/Roaming
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "ZCode" / "cli" / "db" / "db.sqlite")

    for path in candidates:
        if path.exists():
            return str(path)
    return None


def fetch_zcode_records(
    since_date: date,
    until_date: date,
) -> dict:
    """从 ZCode SQLite 数据库读取 model_usage 并按 (日期, 模型) 聚合。

    Args:
        since_date: 起始日期（含）
        until_date: 结束日期（含）

    Returns:
        {
            "records": list[dict],  # 每条含 record_date, model, input_tokens, ...
            "errors": list[dict],
        }
    """
    db_path = _find_zcode_db()
    if not db_path:
        logger.info("[zcode] 未找到 ZCode 数据库，跳过")
        return {
            "records": [],
            "errors": [{
                "source": "zcode",
                "error": "未找到 ZCode 数据库（~/.zcode/cli/db/db.sqlite）",
                "error_code": "DB_NOT_FOUND",
                "remediation": "请确认 ZCode 已安装并使用过",
                "details": {},
            }],
        }

    since_ms = int(datetime.combine(since_date, datetime.min.time()).timestamp() * 1000)
    until_ms = int(datetime.combine(until_date + timedelta(days=1), datetime.min.time()).timestamp() * 1000) - 1

    records: list[dict] = []
    errors: list[dict] = []

    try:
        # 使用 WAL 模式打开，避免锁定 ZCode 正在使用的数据库
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 按 (日期, 模型) 聚合 model_usage 中 completed 状态的记录
        cur.execute("""
            SELECT
                DATE(started_at / 1000, 'unixepoch', 'localtime') AS record_date,
                model_id,
                SUM(input_tokens) AS input_tokens,
                SUM(output_tokens) AS output_tokens,
                SUM(cache_creation_input_tokens) AS cache_creation_tokens,
                SUM(cache_read_input_tokens) AS cache_read_tokens,
                SUM(computed_total_tokens) AS total_tokens,
                COUNT(*) AS request_count
            FROM model_usage
            WHERE status = 'completed'
              AND started_at >= ?
              AND started_at <= ?
            GROUP BY record_date, model_id
            ORDER BY record_date DESC, total_tokens DESC
        """, (since_ms, until_ms))

        for row in cur.fetchall():
            record_date_str = row["record_date"]
            if not record_date_str:
                continue
            try:
                record_date = date.fromisoformat(record_date_str)
            except (ValueError, TypeError):
                continue

            model = row["model_id"] or "unknown"
            input_tokens = int(row["input_tokens"] or 0)
            output_tokens = int(row["output_tokens"] or 0)
            cache_creation = int(row["cache_creation_tokens"] or 0)
            cache_read = int(row["cache_read_tokens"] or 0)
            total_tokens = int(row["total_tokens"] or 0)
            if total_tokens == 0:
                total_tokens = input_tokens + output_tokens + cache_creation + cache_read

            records.append({
                "record_date": record_date,
                "source": "zcode",
                "tool_id": "zcode",
                "tool_name": "ZCode",
                "model": model,
                "model_display_name": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_tokens": cache_creation,
                "cache_read_tokens": cache_read,
                "total_tokens": total_tokens,
                "total_cost": 0.0,  # ZCode 不暴露 cost 数据
                "source_raw": "zcode-sqlite",
            })

        conn.close()
        logger.info(
            f"[zcode] 从 {db_path} 读取 {len(records)} 条聚合记录 "
            f"({since_date} ~ {until_date})"
        )

    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower() or "busy" in str(e).lower():
            logger.warning(f"[zcode] 数据库被锁定（ZCode 可能正在使用）: {e}")
            errors.append({
                "source": "zcode",
                "error": f"ZCode 数据库被锁定: {e}",
                "error_code": "DB_LOCKED",
                "remediation": "请关闭 ZCode 后重试，或稍后再试",
                "details": {"exception": str(e)},
            })
        else:
            logger.error(f"[zcode] 数据库读取失败: {e}", exc_info=True)
            errors.append({
                "source": "zcode",
                "error": f"ZCode 数据库读取失败: {e}",
                "error_code": "DB_READ_ERROR",
                "remediation": "请检查 ZCode 数据库是否完整",
                "details": {"exception": str(e)},
            })
    except Exception as e:
        logger.error(f"[zcode] 读取异常: {e}", exc_info=True)
        errors.append({
            "source": "zcode",
            "error": f"zcode: {str(e)}",
            "error_code": "READ_ERROR",
            "remediation": "请检查 ZCode 安装是否完整",
            "details": {"exception": str(e)},
        })

    return {"records": records, "errors": errors}
