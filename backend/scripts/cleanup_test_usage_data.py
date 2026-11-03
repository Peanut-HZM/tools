"""清理生产库中的测试污染数据

背景
    ``GET /api/token-usage/summary`` 在数据过期时会自动触发真实后台同步
    （``_maybe_trigger_stale_sync``），把本机 Agent 的真实用量写进
    ``token_usage_records``。集成测试若未隔离该副作用，就会把**本机真实
    用量**写到测试 user_id 名下，形成生产库污染。

    已确认的历史污染：
      - ``user-1``（来自 test_token_usage_split_api.py）470 行 / 458 亿 token
      - ``u1``（来自 test_token_usage_split_integration.py 旧版）435 行
      - ``zztest_token_usage_split_u1`` 171 行
      - 真实用户名下的测试 device_id（``test-device-id-12345`` 等）

    守卫测试 ``tests/test_no_production_db_pollution.py`` 会持续检查这些污染。

安全约束
    - **默认 dry-run**，只 SELECT 报告，不删除。加 ``--apply`` 才真正删除。
    - 只删**非 UUID 的 user_id**（真实 user_id 均为 UUID）+ **测试 device_id**
      前缀的行，绝不碰真实用户数据。
    - 每次删除都打印精确条数与 token 总量，便于审计。

用法
    python -m scripts.cleanup_test_usage_data            # 预览
    python -m scripts.cleanup_test_usage_data --apply     # 实际删除
    python -m scripts.cleanup_test_usage_data --apply --user-id u1
"""
from __future__ import annotations

import argparse
import logging
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 真实 user_id 均为 UUID；非 UUID 的只可能是测试账号
_UUID_RE = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

# 测试 device_id 前缀
_TEST_DEVICE_PATTERNS = ("test-%", "zztest%")


def _connect():
    from app.config.database import get_pooled_db_connection

    return get_pooled_db_connection()


def _release(conn):
    from app.config.database import release_db_connection

    release_db_connection(conn)


def _find_pollution(conn, only_user_id: str | None = None):
    """查出待清理的污染行（只读）。返回 (非UUID用户行, 测试device行, 同步日志)。"""
    where = f"user_id !~* '{_UUID_RE}'"
    params: tuple = ()
    if only_user_id:
        where = "user_id = %s"
        params = (only_user_id,)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT user_id, COUNT(*) AS c, COALESCE(SUM(total_tokens), 0) AS t
            FROM token_usage_records
            WHERE {where} AND user_id IS NOT NULL AND user_id <> 'system'
            GROUP BY user_id
            ORDER BY c DESC
            """,
            params,
        )
        bad_users = [
            (r["user_id"], int(r["c"]), int(r["t"])) for r in cur.fetchall()
        ]

        device_clause = " OR ".join(
            f"device_id LIKE '{p}'" for p in _TEST_DEVICE_PATTERNS
        )
        cur.execute(
            f"""
            SELECT user_id, device_id, COUNT(*) AS c,
                   COALESCE(SUM(total_tokens), 0) AS t
            FROM token_usage_records
            WHERE {device_clause}
            GROUP BY user_id, device_id
            ORDER BY c DESC
            """,
        )
        bad_devices = [
            (r["user_id"], r["device_id"], int(r["c"]), int(r["t"]))
            for r in cur.fetchall()
        ]

        cur.execute(
            f"""
            SELECT user_id, COUNT(*) AS c FROM token_usage_sync_log
            WHERE {where} AND user_id IS NOT NULL
            GROUP BY user_id
            """,
            params,
        )
        bad_logs = [(r["user_id"], int(r["c"])) for r in cur.fetchall()]

    return bad_users, bad_devices, bad_logs


# 除 token_usage_* 外，另有几张表也承载测试污染（同样的 stale-sync / 直接写入）
_EXTRA_TABLES = ("device_registry", "password_audit_logs")

# 这些 user_id 是应用的合法内置账号，不是测试污染
_LEGACY_USER_IDS = ("default-user", "__global__", "anonymous", "system")


def _find_extra_pollution(conn, only_user_id: str | None = None):
    """查出 device_registry / password_audit_logs 里的测试账号行。"""
    found = []
    with conn.cursor() as cur:
        for table in _EXTRA_TABLES:
            try:
                if only_user_id:
                    cur.execute(
                        f'SELECT COUNT(*) AS c FROM "{table}" WHERE user_id = %s',
                        (only_user_id,),
                    )
                    cnt = int(cur.fetchone()["c"])
                    if cnt:
                        found.append((table, only_user_id, cnt))
                    continue

                cur.execute(
                    f"""
                    SELECT user_id, COUNT(*) AS c FROM "{table}"
                    WHERE user_id IS NOT NULL
                      AND user_id <> ''
                      AND user_id NOT IN {_LEGACY_USER_IDS}
                      AND user_id !~* '{_UUID_RE}'
                    GROUP BY user_id
                    """
                )
                for r in cur.fetchall():
                    found.append((table, r["user_id"], int(r["c"])))
            except Exception:
                conn.rollback()
                continue
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="清理生产库中的测试污染数据")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="真正执行删除（默认只预览）",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="只处理指定 user_id（默认处理所有非 UUID user_id）",
    )
    args = parser.parse_args()

    conn = _connect()
    try:
        bad_users, bad_devices, bad_logs = _find_pollution(conn, args.user_id)
        bad_extra = _find_extra_pollution(conn, args.user_id)

        if not bad_users and not bad_devices and not bad_logs and not bad_extra:
            logger.info("未发现测试污染数据，无需清理")
            return 0

        print("=" * 72)
        print("发现测试污染数据：")
        print("-" * 72)
        for user_id, cnt, tokens in bad_users:
            print(f"  [非UUID用户] user_id={user_id!r} rows={cnt} tokens={tokens:,}")
        for user_id, device_id, cnt, tokens in bad_devices:
            print(
                f"  [测试device] user_id={user_id} device_id={device_id!r} "
                f"rows={cnt} tokens={tokens:,}"
            )
        for user_id, cnt in bad_logs:
            print(f"  [同步日志]   user_id={user_id!r} rows={cnt}")
        for table, user_id, cnt in bad_extra:
            print(f"  [其他表]     {table} user_id={user_id!r} rows={cnt}")
        print("-" * 72)

        if not args.apply:
            total_rows = sum(c for _, c, _ in bad_users)
            total_tokens = sum(t for _, _, t in bad_users)
            print(
                f"预览模式：将被清理 {total_rows} 行 / {total_tokens:,} token。"
                "\n加 --apply 执行实际删除。"
            )
            print("=" * 72)
            return 0

        deleted_records = 0
        deleted_logs = 0
        deleted_extra = 0
        with conn.cursor() as cur:
            where = f"user_id !~* '{_UUID_RE}'"
            params: tuple = ()
            if args.user_id:
                where = "user_id = %s"
                params = (args.user_id,)
            cur.execute(
                f"DELETE FROM token_usage_records "
                f"WHERE {where} AND user_id IS NOT NULL AND user_id <> 'system'",
                params,
            )
            deleted_records += cur.rowcount

            device_clause = " OR ".join(
                f"device_id LIKE '{p}'" for p in _TEST_DEVICE_PATTERNS
            )
            cur.execute(
                f"DELETE FROM token_usage_records WHERE {device_clause}"
            )
            deleted_records += cur.rowcount

            cur.execute(
                f"DELETE FROM token_usage_sync_log "
                f"WHERE {where} AND user_id IS NOT NULL",
                params,
            )
            deleted_logs += cur.rowcount

            for table, user_id, _cnt in bad_extra:
                try:
                    cur.execute(f'DELETE FROM "{table}" WHERE user_id = %s', (user_id,))
                    deleted_extra += cur.rowcount
                except Exception as exc:
                    conn.rollback()
                    cur = conn.cursor()
                    logger.warning("清理 %s 失败（跳过）: %s", table, exc)
            conn.commit()

        print(
            f"已清理：token_usage_records {deleted_records} 行，"
            f"token_usage_sync_log {deleted_logs} 行，"
            f"其他表 {deleted_extra} 行"
        )
        print("=" * 72)
        return 0
    finally:
        _release(conn)


if __name__ == "__main__":
    raise SystemExit(main())
