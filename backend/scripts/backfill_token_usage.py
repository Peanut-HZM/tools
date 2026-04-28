"""
回填 total_tokens 和生成 default_display_name

1. 将 total_tokens=0 的记录回填为 input+output+cache_creation+cache_read
2. 为设备生成默认的 default_display_name
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.base import SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

db = SessionLocal()
try:
    # ========== 1. 回填 total_tokens ==========
    logger.info("回填 total_tokens=0 的记录...")
    result = db.execute(text("""
        UPDATE token_usage_records
        SET total_tokens = input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens
        WHERE total_tokens = 0
          AND (input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens) > 0
    """))
    db.commit()
    logger.info(f"  -> 回填 {result.rowcount} 条记录")

    # ========== 2. 验证回填结果 ==========
    zero_total = db.execute(text("""
        SELECT COUNT(*) FROM token_usage_records WHERE total_tokens = 0
    """)).scalar()
    nonzero_total = db.execute(text("""
        SELECT COUNT(*) FROM token_usage_records WHERE total_tokens > 0
    """)).scalar()
    logger.info(f"回填后: zero={zero_total}, nonzero={nonzero_total}")

    # ========== 3. 更新设备的 default_display_name ==========
    # 从 token_usage_records 中提取 device_id 对应的 source 信息，生成有意义的名称
    logger.info("更新设备 default_display_name...")

    # 获取所有设备及其数据源
    device_info = db.execute(text("""
        SELECT DISTINCT device_id, source, COUNT(*) as cnt
        FROM token_usage_records
        GROUP BY device_id, source
        ORDER BY device_id
    """)).fetchall()

    device_sources: dict = {}
    for dev_id, source, cnt in device_info:
        if dev_id not in device_sources:
            device_sources[dev_id] = {}
        device_sources[dev_id][source] = cnt

    for dev_id, sources in device_sources.items():
        claude_cnt = sources.get('claude', 0)
        opencode_cnt = sources.get('opencode', 0)
        source_label = ""
        if claude_cnt > 0 and opencode_cnt > 0:
            source_label = "Claude+OpenCode"
        elif claude_cnt > 0:
            source_label = "Claude"
        else:
            source_label = "OpenCode"

        default_name = f"{dev_id[:8]} ({source_label})"

        db.execute(text("""
            UPDATE device_registry
            SET default_display_name = :name
            WHERE device_id = :dev_id AND (default_display_name IS NULL OR default_display_name = '')
        """), {"name": default_name, "dev_id": dev_id})
        logger.info(f"  -> {dev_id[:16]}... -> {default_name}")

    db.commit()
    logger.info("回填完成！")

    # ========== 4. 最终验证 ==========
    devices = db.execute(text("""
        SELECT device_id, display_name, default_display_name
        FROM device_registry
    """)).fetchall()
    print("\n最终设备列表:")
    for d in devices:
        name = d[1] or d[2] or d[0]
        print(f"  {d[0][:16]}... | display={d[1]} | default={d[2]} | name={name}")

except Exception as e:
    db.rollback()
    logger.error(f"失败: {e}")
    raise
finally:
    db.close()
