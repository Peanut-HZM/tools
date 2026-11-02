"""
user_display_preferences 表结构迁移 —— 按设备维度存储显示偏好

背景：
显示偏好（数据库工具的可见连接 / 可见数据库）原先只按 user_id 存一行，
导致同一用户在多台设备上的设置互相覆盖 —— 在 A 设备勾选的连接会同步到
B 设备，多台设备的列表混在一起。

迁移步骤（幂等，可重复执行）：
【远程 PostgreSQL】
1. 加 device_id 列（若不存在），默认 '' —— 历史行落到兜底行
2. 删掉旧的 user_id 单列主键
3. 建 (user_id, device_id) 复合主键
4. 建索引

【本地 SQLite】
SQLite 不支持 ALTER 改主键，采用「建新表 → 拷数据 → 换名」：
1. 若已有 device_id 列 → 结构已是新形态，跳过
2. 否则建 user_display_preferences_new（复合主键）
3. 拷历史数据（device_id=''）
4. 删旧表 → 新表改名

回滚：
    ALTER TABLE user_display_preferences DROP CONSTRAINT IF EXISTS user_display_preferences_pkey;
    ALTER TABLE user_display_preferences ADD PRIMARY KEY (user_id);
    ALTER TABLE user_display_preferences DROP COLUMN IF EXISTS device_id;
（回滚会丢失按设备区分的数据 —— 多台设备的偏好会合并成一份）
"""
import logging
import os
import sys

from sqlalchemy import text

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


def _column_exists(conn, table: str, column: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c LIMIT 1"
        ),
        {"t": table, "c": column},
    ).first()
    return row is not None


def _constraint_exists(conn, table: str, name: str) -> bool:
    row = conn.execute(
        text("SELECT 1 FROM pg_constraint WHERE conrelid = :t::regclass AND conname = :n LIMIT 1"),
        {"t": table, "n": name},
    ).first()
    return row is not None


def migrate_display_preferences_device_scope() -> bool:
    """执行迁移，返回 True 表示本次实际做了变更。"""
    from app.models.base import engine

    changed = False
    with engine.begin() as conn:
        # 表不存在则跳过（首次部署时由 init_db_tool.sql 建表）
        exists = conn.execute(
            text("SELECT 1 FROM information_schema.tables "
                 "WHERE table_name = 'user_display_preferences' LIMIT 1")
        ).first()
        if not exists:
            logger.info("user_display_preferences 表不存在，跳过迁移")
            return False

        # 1. 加 device_id 列
        if not _column_exists(conn, "user_display_preferences", "device_id"):
            conn.execute(
                text(
                    "ALTER TABLE user_display_preferences "
                    "ADD COLUMN device_id VARCHAR(128) NOT NULL DEFAULT ''"
                )
            )
            logger.info("已为 user_display_preferences 添加 device_id 列")
            changed = True

        # 2. 主键改造：旧的单列主键 user_id → 复合主键 (user_id, device_id)
        #    先检查当前主键定义，只在还是单列 user_id 时才动。
        pk_cols = conn.execute(
            text(
                "SELECT a.attname AS col "
                "FROM pg_index i "
                "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
                "WHERE i.indrelid = 'user_display_preferences'::regclass AND i.indisprimary "
                "ORDER BY a.attname"
            )
        ).fetchall()
        pk_names = sorted(r[0] for r in pk_cols)

        if pk_names == ["user_id"]:
            conn.execute(
                text("ALTER TABLE user_display_preferences DROP CONSTRAINT user_display_preferences_pkey")
            )
            conn.execute(
                text(
                    "ALTER TABLE user_display_preferences "
                    "ADD PRIMARY KEY (user_id, device_id)"
                )
            )
            logger.info("user_display_preferences 主键已改为 (user_id, device_id)")
            changed = True

        # 3. 索引
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_display_prefs_user_id "
                "ON user_display_preferences(user_id)"
            )
        )

    if changed:
        logger.info("user_display_preferences 设备维度迁移完成")
    return changed


def migrate_local_display_preferences_device_scope() -> bool:
    """迁移本地 SQLite 的 user_display_preferences 表（复合主键）。

    SQLite 不支持 ALTER 改主键，采用「建新表 → 拷数据 → 换名」。
    """
    from app.storage.local_db import get_local_engine, init_local_tables

    engine = get_local_engine()
    # 先确保表存在（否则下面没法判断列）
    init_local_tables(engine)

    changed = False
    with engine.begin() as conn:
        cols = conn.execute(
            text("PRAGMA table_info(user_display_preferences)")
        ).fetchall()
        if not cols:
            logger.info("本地 user_display_preferences 表不存在，跳过迁移")
            return False

        col_names = {row[1] for row in cols}
        if "device_id" in col_names:
            logger.info("本地 user_display_preferences 已是设备维度结构，跳过")
            return False

        logger.info("本地 user_display_preferences 迁移为设备维度结构…")
        conn.execute(
            text(
                "CREATE TABLE user_display_preferences_new ("
                "  user_id VARCHAR(64) NOT NULL,"
                "  device_id VARCHAR(128) NOT NULL DEFAULT '',"
                "  visible_connections TEXT,"
                "  visible_databases TEXT,"
                "  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "  PRIMARY KEY (user_id, device_id)"
                ")"
            )
        )
        conn.execute(
            text(
                "INSERT INTO user_display_preferences_new "
                "(user_id, device_id, visible_connections, visible_databases, updated_at) "
                "SELECT user_id, '', visible_connections, visible_databases, updated_at "
                "FROM user_display_preferences"
            )
        )
        conn.execute(text("DROP TABLE user_display_preferences"))
        conn.execute(
            text("ALTER TABLE user_display_preferences_new RENAME TO user_display_preferences")
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_display_prefs_user_id "
                "ON user_display_preferences(user_id)"
            )
        )
        changed = True

    logger.info("本地 user_display_preferences 设备维度迁移完成")
    return changed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    remote_changed = migrate_display_preferences_device_scope()
    local_changed = migrate_local_display_preferences_device_scope()
    print("迁移完成，远程有变更:", remote_changed, "本地有变更:", local_changed)
