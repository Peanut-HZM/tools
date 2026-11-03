"""守卫测试：集成测试不得触发生产库写入副作用

背景
    ``GET /api/token-usage/summary`` 在数据过期时（``sync_meta.is_stale``）
    会**自动触发真实后台同步**（``_maybe_trigger_stale_sync``），把本机
    Agent 的真实用量写进 ``token_usage_records`` / ``token_usage_sync_log``。

    集成测试调用 ``/summary`` 时若不隔离这个副作用，就会把**本机真实用量**
    写到测试 user_id 名下，形成生产库污染。历史上已发生：
      - ``user-1``（来自 test_token_usage_split_api.py）污染 470 行 / 458 亿 token
      - ``u1``（来自 test_token_usage_split_integration.py 旧版）污染 435 行
      - ``zztest_token_usage_split_u1`` 污染 171 行

    本文件用静态扫描 + 运行时断言两条手段防止复发。

判定口径
    1. 凡是通过 ``TestClient`` 调用 ``/summary``（含 ``/db-usage``）的测试，
       必须隔离 ``_maybe_trigger_stale_sync``（或 ``sync_token_usage``）。
    2. 任何测试都不得使用**非 UUID** 的 user_id 去触碰生产库路径 ——
       本项目真实 user_id 均为 UUID（见 ``token_usage_background_sync.
       _is_valid_user_id``），非 UUID 说明是测试账号。
"""
import ast
import pathlib
import re

import pytest

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
TESTS_ROOT = BACKEND_ROOT / "tests"

# 允许出现测试 user_id 的位置：这些文件只用 mock/临时 SQLite，不碰生产库
# user_id 形如 u1 / user-1 / test-user-xxx
_NON_UUID_USER_ID = re.compile(r"""["']((?:u|user|test|zztest)[-_a-zA-Z0-9]*)["']""")

# 静态扫描跳过的目录
SKIP_DIRS = {"__pycache__", "venv", ".venv", "node_modules", ".git"}


def _rel(path: pathlib.Path) -> str:
    return str(path.relative_to(BACKEND_ROOT)).replace("\\", "/")


def _test_files() -> list[pathlib.Path]:
    return sorted(TESTS_ROOT.rglob("*.py"))


def _source(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _calls_summary_endpoint(path: pathlib.Path) -> bool:
    """是否通过 HTTP 调用了 /summary 或 /db-usage（会触发 stale-sync）。

    路径后面可能跟 query string（如
    ``client.get("/api/token-usage/summary?type=daily&days=30")``），
    也可能是裸路径（``client.get("/summary")``），两种都要识别。
    """
    src = _source(path)
    patterns = (
        r"""["'](/api/token-usage/(?:summary|db-usage))(?:[?#][^"']*)?["']""",
        r"""["'](/(?:summary|db-usage))(?:[?#][^"']*)?["']""",
    )
    return any(re.search(p, src) for p in patterns)


def _isolates_stale_sync(path: pathlib.Path) -> bool:
    """是否隔离了 stale-sync / sync_token_usage 副作用。"""
    src = _source(path)
    return bool(
        re.search(r"""_maybe_trigger_stale_sync""", src)
        or re.search(r"""sync_token_usage""", src)
    )


class TestNoStaleSyncSideEffect:
    """调用 /summary 的测试必须隔离自动同步副作用"""

    def test_summary_calling_tests_isolate_stale_sync(self):
        """凡调 /summary 的测试文件，都必须显式隔离 stale-sync"""
        offenders = []
        for path in _test_files():
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if _calls_summary_endpoint(path) and not _isolates_stale_sync(path):
                offenders.append(_rel(path))
        assert offenders == [], (
            "这些测试调用了 /summary 但未隔离 _maybe_trigger_stale_sync，"
            f"会把本机真实用量写进生产库: {offenders}"
        )

    def test_no_test_calls_real_sync_token_usage(self):
        """测试不得直接调用真实 sync_token_usage（会写生产库）"""
        offenders = []
        for path in _test_files():
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            try:
                tree = ast.parse(_source(path))
            except SyntaxError:  # pragma: no cover
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = getattr(func, "id", None) or getattr(func, "attr", None)
                if name == "sync_token_usage":
                    # 允许被 patch 的引用（出现在 with patch(...) 里）
                    offenders.append(f"{_rel(path)}:{node.lineno}")
        # 该列表应为空：测试只能 patch 它，不能直接调用
        assert offenders == [], f"测试直接调用了 sync_token_usage: {offenders}"


class TestNoProductionDbWrites:
    """测试不得往生产库写数据"""

    def test_token_usage_tables_untouched_by_tests(self):
        """生产库的 token_usage 表不得出现非 UUID 的测试 user_id。

        真实 user_id 均为 UUID；非 UUID 的行只可能来自测试污染。
        """
        from app.config.database import get_pooled_db_connection, release_db_connection

        try:
            conn = get_pooled_db_connection()
        except Exception:
            pytest.skip("生产数据库不可达，跳过污染检查")

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, COUNT(*) AS c FROM token_usage_records
                    WHERE user_id IS NOT NULL
                      AND user_id <> 'system'
                      AND user_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                    GROUP BY user_id
                    """
                )
                rows = cur.fetchall()
        except Exception as exc:
            pytest.skip(f"查询失败，跳过污染检查: {exc}")
        finally:
            release_db_connection(conn)

        offenders = [
            f"{r['user_id']}({r['c']} 行)"
            for r in rows
            if int(r["c"]) > 0
        ]
        assert offenders == [], (
            "生产库 token_usage_records 存在非 UUID user_id 的测试污染，"
            f"请清理: {offenders}。清理后可用 scripts/cleanup_test_usage_data.py"
        )

    def test_no_test_device_ids_in_production(self):
        """生产库不得残留测试 device_id（test-* / zztest*）。"""
        from app.config.database import get_pooled_db_connection, release_db_connection

        try:
            conn = get_pooled_db_connection()
        except Exception:
            pytest.skip("生产数据库不可达，跳过污染检查")

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, device_id, COUNT(*) AS c FROM token_usage_records
                    WHERE device_id LIKE 'test-%%' OR device_id LIKE 'zztest%%'
                    GROUP BY user_id, device_id
                    """
                )
                rows = cur.fetchall()
        except Exception as exc:
            pytest.skip(f"查询失败，跳过污染检查: {exc}")
        finally:
            release_db_connection(conn)

        offenders = [
            f"user={r['user_id']} device={r['device_id']}({r['c']} 行)"
            for r in rows
        ]
        assert offenders == [], (
            f"生产库 token_usage_records 存在测试 device_id，请清理: {offenders}"
        )

    def test_no_test_user_ids_in_other_tables(self):
        """其它表也不得残留测试 user_id。

        覆盖 device_registry / password_audit_logs —— 它们同样会被测试写入。
        ``default-user`` / ``__global__`` / ``anonymous`` 是应用的内置合法值
        （见 app/routes/course_platform.py、app/services/monitor/），
        ``werewolf_game_record_players.user_id`` 存的是玩家序号而非用户 id，
        故不在检查范围。
        """
        from app.config.database import get_pooled_db_connection, release_db_connection

        legacy = ("default-user", "__global__", "anonymous", "system", "")
        uuid_re = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        tables = ("device_registry", "password_audit_logs")

        try:
            conn = get_pooled_db_connection()
        except Exception:
            pytest.skip("生产数据库不可达，跳过污染检查")

        offenders = []
        try:
            for table in tables:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            f"""
                            SELECT user_id, COUNT(*) AS c FROM "{table}"
                            WHERE user_id IS NOT NULL
                              AND user_id NOT IN {legacy}
                              AND user_id !~* '{uuid_re}'
                            GROUP BY user_id
                            """
                        )
                        for r in cur.fetchall():
                            offenders.append(f"{table} user={r['user_id']}({r['c']} 行)")
                except Exception as exc:
                    conn.rollback()
                    pytest.skip(f"查询 {table} 失败，跳过污染检查: {exc}")
        finally:
            release_db_connection(conn)

        assert offenders == [], (
            f"生产库存在测试 user_id，请用 scripts/cleanup_test_usage_data.py 清理: {offenders}"
        )
