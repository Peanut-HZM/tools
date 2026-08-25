# backend/scripts/migrate_image_gen_quota_to_llm_quota.py
"""一次性数据迁移：image_gen_quota → llm_user_quota

幂等：ON CONFLICT (user_id) DO NOTHING
可重入：重复执行不会重复插入

运行：
  cd backend
  python -m scripts.migrate_image_gen_quota_to_llm_quota
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# 把 backend 加进 path（脚本可独立运行）
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import psycopg2  # noqa: E402

from app.config.config import get_settings  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# 防御性建表：确保 llm_user_quota 存在（IF NOT EXISTS，幂等）
SQL_ENSURE_TABLE = """
CREATE TABLE IF NOT EXISTS llm_user_quota (
    user_id VARCHAR(64) PRIMARY KEY,
    quota_mode VARCHAR(16) NOT NULL,
    daily_limit INTEGER,
    daily_used INTEGER NOT NULL DEFAULT 0,
    daily_reset_date TIMESTAMP WITH TIME ZONE,
    monthly_limit INTEGER,
    monthly_used INTEGER NOT NULL DEFAULT 0,
    monthly_reset_date TIMESTAMP WITH TIME ZONE,
    token_period VARCHAR(16),
    token_limit INTEGER,
    token_used INTEGER NOT NULL DEFAULT 0,
    token_reset_date TIMESTAMP WITH TIME ZONE,
    valid_from TIMESTAMP WITH TIME ZONE,
    valid_until TIMESTAMP WITH TIME ZONE,
    granted_by VARCHAR(64),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
"""

SQL_MIGRATE = """
INSERT INTO llm_user_quota (
    user_id, quota_mode,
    daily_limit, daily_used, daily_reset_date,
    monthly_limit, monthly_used, monthly_reset_date,
    token_used,
    valid_from, valid_until, granted_by, notes,
    created_at, updated_at
)
SELECT
    user_id, 'count' AS quota_mode,
    daily_limit, daily_used, daily_reset_date,
    monthly_limit, monthly_used, monthly_reset_date,
    0 AS token_used,
    valid_from, valid_until, granted_by, notes,
    created_at, updated_at
FROM image_gen_quota
ON CONFLICT (user_id) DO NOTHING;
"""


def migrate() -> tuple[int, int]:
    """执行迁移。返回 (migrated_count, skipped_count)。"""
    settings = get_settings()
    db_url = settings.DATABASE_URL
    if not db_url:
        raise SystemExit("DATABASE_URL 未配置")

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 防御性建表：确保目标表存在
            cur.execute(SQL_ENSURE_TABLE)

            # 源表存在性检查：旧表已 DROP 或从未建过则直接返回（幂等）
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'image_gen_quota')"
            )
            if not cur.fetchone()[0]:
                conn.commit()
                logger.info("源表 image_gen_quota 不存在，跳过迁移（0 inserted）")
                return 0, 0

            # 先统计旧表总数
            cur.execute("SELECT COUNT(*) FROM image_gen_quota")
            total = cur.fetchone()[0]

            cur.execute(SQL_MIGRATE)
            inserted = cur.rowcount

            cur.execute("SELECT COUNT(*) FROM llm_user_quota")
            new_total = cur.fetchone()[0]
            skipped = total - inserted
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "迁移完成：旧表 %d 条 → 新表写入 %d 条（跳过 %d，已存在）",
        total, inserted, skipped,
    )
    logger.info("新表现在共 %d 条", new_total)
    return inserted, skipped


if __name__ == "__main__":
    migrate()
