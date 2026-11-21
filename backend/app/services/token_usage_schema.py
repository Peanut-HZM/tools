"""Token Usage 表结构幂等迁移（调用渠道 channel）

背景
----
项目部署链路（deploy.py）不自动执行 alembic，历史表结构靠启动时
``Base.metadata.create_all`` + 幂等 DDL 补齐。``create_all`` **不会**给已存在的
表加列，也不会替换唯一约束，因此渠道列必须在应用启动时幂等处理。

本模块只做三件事（失败不阻断应用启动，仅记录 warning）：
1. 给 ``token_usage_records`` 增加 ``channel`` 列；
2. 把旧的 5 列唯一约束 `(user_id, device_id, record_date, source, model)`
   替换为 6 列唯一约束（含 channel）；
3. 补渠道查询索引。

历史行不在这里回填：同步服务写入前会删除本轮覆盖日期内的 ``channel IS NULL``
旧行，再用带渠道的新行覆盖，避免「旧行 + 新行」双计。
"""

from __future__ import annotations

import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)

_TABLE = "token_usage_records"

_OLD_UNIQUE_COLUMNS = {
    "user_id",
    "device_id",
    "record_date",
    "source",
    "model",
}

_NEW_UNIQUE_COLUMNS = {
    "user_id",
    "device_id",
    "record_date",
    "source",
    "channel",
    "model",
}

_CHANNEL_INDEX = "idx_token_usage_channel"
_UNIQUE_INDEX = "uq_token_usage_channel_key"


def _sqlite_columns(conn) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({_TABLE})")).fetchall()
    return {row[1] for row in rows}


def _pg_unique_constraints(conn) -> list[tuple[str, set[str]]]:
    """返回 (约束名, 列集合) 列表。"""
    rows = conn.execute(
        text(
            """
            SELECT c.conname,
                   array(
                       SELECT a.attname
                       FROM unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord)
                       JOIN pg_attribute a
                         ON a.attrelid = c.conrelid AND a.attnum = k.attnum
                       ORDER BY k.ord
                   ) AS cols
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = :table AND c.contype = 'u'
            """
        ),
        {"table": _TABLE},
    ).fetchall()
    result: list[tuple[str, set[str]]] = []
    for name, cols in rows:
        result.append((name, set(cols or [])))
    return result


def _pg_unique_indexes(conn) -> list[tuple[str, set[str]]]:
    rows = conn.execute(
        text(
            """
            SELECT i.indexrelid::regclass::text AS index_name,
                   array(
                       SELECT a.attname
                       FROM unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord)
                       JOIN pg_attribute a
                         ON a.attrelid = i.indrelid AND a.attnum = k.attnum
                       ORDER BY k.ord
                   ) AS cols
            FROM pg_index i
            JOIN pg_class t ON t.oid = i.indrelid
            WHERE t.relname = :table AND i.indisunique
            """
        ),
        {"table": _TABLE},
    ).fetchall()
    return [(name, set(cols or [])) for name, cols in rows]


def _ensure_postgres(conn) -> None:
    conn.execute(
        text(f"ALTER TABLE {_TABLE} ADD COLUMN IF NOT EXISTS channel VARCHAR(64)")
    )

    # 1) 删除旧的 5 列唯一约束（含其索引）
    for name, cols in _pg_unique_constraints(conn):
        if cols == _OLD_UNIQUE_COLUMNS:
            conn.execute(text(f'ALTER TABLE {_TABLE} DROP CONSTRAINT "{name}"'))
            logger.info("[token-usage-schema] 已删除旧唯一约束 %s", name)

    # 2) 没有覆盖 6 列的唯一索引时补一个
    existing_unique = _pg_unique_indexes(conn)
    if not any(cols == _NEW_UNIQUE_COLUMNS for _, cols in existing_unique):
        conn.execute(
            text(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {_UNIQUE_INDEX} "
                f"ON {_TABLE} (user_id, device_id, record_date, source, channel, model)"
            )
        )
        logger.info("[token-usage-schema] 已创建渠道唯一索引 %s", _UNIQUE_INDEX)

    # 3) 渠道查询索引
    conn.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS {_CHANNEL_INDEX} "
            f"ON {_TABLE} (user_id, record_date, channel)"
        )
    )


def _ensure_sqlite(conn) -> None:
    columns = _sqlite_columns(conn)
    if "channel" not in columns:
        conn.execute(text(f"ALTER TABLE {_TABLE} ADD COLUMN channel VARCHAR(64)"))
        logger.info("[token-usage-schema] SQLite 已增加 channel 列")

    # SQLite 无法原地修改唯一约束；测试/本地库由 Base.metadata.create_all
    # 按新 ORM 定义建表。这里只补普通索引。
    conn.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS {_CHANNEL_INDEX} "
            f"ON {_TABLE} (user_id, record_date, channel)"
        )
    )


def ensure_token_usage_channel_schema(engine=None) -> bool:
    """幂等补列 / 换唯一约束 / 建索引。返回是否执行成功。"""
    try:
        if engine is None:
            from app.models.base import engine as default_engine

            engine = default_engine

        dialect = engine.dialect.name
        with engine.begin() as conn:
            if dialect == "postgresql":
                _ensure_postgres(conn)
            else:
                _ensure_sqlite(conn)
        logger.info("[token-usage-schema] 渠道表结构检查完成 (dialect=%s)", dialect)
        return True
    except Exception as exc:  # 不阻断应用启动
        logger.warning("[token-usage-schema] 渠道表结构迁移失败: %s", exc)
        return False