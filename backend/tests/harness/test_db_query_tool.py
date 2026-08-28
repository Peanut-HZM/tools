"""DbQueryTool 行为测试（Task 5）

覆盖：元数据 / 拒绝写操作 / 接受 SELECT 查询 / 安全加固验证
"""
from unittest.mock import MagicMock

import pytest

from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.db_query import DbQueryTool


def test_db_query_metadata():
    tool = DbQueryTool()
    assert tool.name == "db_query"
    assert "sql" in tool.parameters_schema["properties"]


@pytest.mark.asyncio
async def test_db_query_rejects_write():
    """DbQueryTool 应拒绝写操作"""
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)

    result = await tool.execute({"sql": "DELETE FROM users"}, ctx)
    assert result.success is False
    assert "只读" in result.error_message or "写操作" in result.error_message or "SQL 验证失败" in result.error_message


@pytest.mark.asyncio
async def test_db_query_rejects_drop():
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)

    result = await tool.execute({"sql": "DROP TABLE users"}, ctx)
    assert result.success is False


@pytest.mark.asyncio
async def test_db_query_executes_select(test_db):
    """DbQueryTool 应执行 SELECT 查询"""
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)
    ctx.db = test_db

    result = await tool.execute({"sql": "SELECT 1 AS n", "limit": 10}, ctx)
    assert result.success is True
    assert "1" in str(result.content) or result.content == [{"n": 1}]


# ---- 安全加固测试 ----

@pytest.mark.asyncio
async def test_db_query_blocks_dangerous_functions():
    """应阻止危险 PostgreSQL 函数"""
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)

    dangerous_sqls = [
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT lo_import('/etc/passwd')",
        "SELECT dblink_exec('conn', 'DROP TABLE users')",
        "SELECT pg_ls_dir('/tmp')",
        "SELECT lo_export(12345, '/tmp/out')",
        "SELECT pg_read_binary_file('/etc/shadow')",
        "SELECT copy_to('SELECT 1', '/tmp/out.csv')",
    ]

    for sql in dangerous_sqls:
        result = await tool.execute({"sql": sql}, ctx)
        assert result.success is False, f"Should have blocked: {sql}"
        assert "危险" in result.error_message or "验证失败" in result.error_message, (
            f"Should mention dangerous function for: {sql}, got: {result.error_message}"
        )


@pytest.mark.asyncio
async def test_db_query_blocks_into_clause():
    """应阻止 INTO 子句（防止 INSERT INTO ... SELECT 绕过）"""
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)

    into_sqls = [
        "SELECT * INTO new_table FROM users",
        "INSERT INTO users SELECT * FROM other",
    ]

    for sql in into_sqls:
        result = await tool.execute({"sql": sql}, ctx)
        assert result.success is False, f"Should have blocked INTO: {sql}"


@pytest.mark.asyncio
async def test_db_query_blocks_copy():
    """应阻止 COPY 语句"""
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)

    result = await tool.execute({"sql": "COPY users TO '/tmp/users.csv'"}, ctx)
    assert result.success is False


@pytest.mark.asyncio
async def test_db_query_blocks_comment_bypass():
    """应阻止通过注释绕过检查"""
    tool = DbQueryTool()

    # 注释包裹写操作：去除注释后是 SELECT 1，应通过
    ctx = MagicMock(spec=ToolContext)
    mock_result = MagicMock()
    mock_result.fetchmany.return_value = []
    mock_result.keys.return_value = ["n"]
    mock_result.returns_rows = True
    ctx.db = mock_result

    result = await tool.execute(
        {"sql": "SELECT /* DROP TABLE users */ 1"},
        ctx,
    )
    assert result.success is True, "Comment-wrapped safe SQL should pass"

    # 多语句：SELECT 1; DROP TABLE users — DROP 关键词应被阻止
    ctx2 = MagicMock(spec=ToolContext)
    result = await tool.execute(
        {"sql": "SELECT 1; DROP TABLE users"},
        ctx2,
    )
    assert result.success is False

    # 写操作通过注释伪装在开头
    ctx3 = MagicMock(spec=ToolContext)
    result = await tool.execute(
        {"sql": "/* comment */ INSERT INTO users VALUES (1)"},
        ctx3,
    )
    assert result.success is False


@pytest.mark.asyncio
async def test_db_query_blocks_ddl():
    """应阻止 DDL 语句"""
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)

    ddl_sqls = [
        "CREATE TABLE evil (id int)",
        "ALTER TABLE users DROP COLUMN name",
        "TRUNCATE TABLE logs",
    ]

    for sql in ddl_sqls:
        result = await tool.execute({"sql": sql}, ctx)
        assert result.success is False, f"Should have blocked DDL: {sql}"


@pytest.mark.asyncio
async def test_db_query_blocks_blocked_tables():
    """应阻止访问被 blocklist 的表"""
    tool = DbQueryTool()  # 默认 blocked_tables=['users', 'sessions', 'api_keys', 'secrets']
    ctx = MagicMock(spec=ToolContext)
    ctx.db = MagicMock()

    result = await tool.execute({"sql": "SELECT * FROM users"}, ctx)
    assert result.success is False
    assert "Access denied" in result.error_message or "blocked" in result.error_message


@pytest.mark.asyncio
async def test_db_query_blocks_blocked_tables_schema_qualified():
    """应阻止 schema.table 格式的被阻止表"""
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)
    ctx.db = MagicMock()

    result = await tool.execute({"sql": "SELECT * FROM public.users"}, ctx)
    assert result.success is False
    assert "Access denied" in result.error_message or "blocked" in result.error_message


@pytest.mark.asyncio
async def test_db_query_allows_non_blocked_tables():
    """应允许访问非 blocklist 的表"""
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)

    # mock db 返回空结果
    mock_result = MagicMock()
    mock_result.fetchmany.return_value = []
    mock_result.keys.return_value = ["id"]
    mock_result.returns_rows = True
    ctx.db = MagicMock()
    ctx.db.execute.return_value = mock_result

    result = await tool.execute({"sql": "SELECT * FROM products"}, ctx)
    assert result.success is True


@pytest.mark.asyncio
async def test_db_query_custom_blocked_tables():
    """自定义 blocked_tables 应生效"""
    tool = DbQueryTool(blocked_tables=["orders", "payments"])
    ctx = MagicMock(spec=ToolContext)
    ctx.db = MagicMock()

    result = await tool.execute({"sql": "SELECT * FROM orders"}, ctx)
    assert result.success is False

    # users 不再被阻止（默认 blocklist 被覆盖）
    mock_result = MagicMock()
    mock_result.fetchmany.return_value = []
    mock_result.keys.return_value = ["id"]
    mock_result.returns_rows = True
    ctx.db.execute.return_value = mock_result

    result = await tool.execute({"sql": "SELECT * FROM users"}, ctx)
    assert result.success is True


@pytest.mark.asyncio
async def test_db_query_allowed_tables_restricts():
    """设置 allowed_tables 时，只允许指定表"""
    tool = DbQueryTool(allowed_tables=["products", "categories"])
    ctx = MagicMock(spec=ToolContext)
    ctx.db = MagicMock()

    mock_result = MagicMock()
    mock_result.fetchmany.return_value = []
    mock_result.keys.return_value = ["id"]
    mock_result.returns_rows = True
    ctx.db.execute.return_value = mock_result

    # products 在 allowlist 中，应通过
    result = await tool.execute({"sql": "SELECT * FROM products"}, ctx)
    assert result.success is True

    # orders 不在 allowlist 中，应被拒绝
    result = await tool.execute({"sql": "SELECT * FROM orders"}, ctx)
    assert result.success is False
    assert "Access denied" in result.error_message or "allowlist" in result.error_message


@pytest.mark.asyncio
async def test_db_query_blocked_schema():
    """应阻止访问不在 allowed_schemas 中的 schema"""
    tool = DbQueryTool(allowed_schemas=["public"])
    ctx = MagicMock(spec=ToolContext)
    ctx.db = MagicMock()

    result = await tool.execute({"sql": "SELECT * FROM pg_catalog.pg_tables"}, ctx)
    assert result.success is False
    assert "schema" in result.error_message.lower() or "Access denied" in result.error_message


@pytest.mark.asyncio
async def test_db_query_cte_select_allowed():
    """合法的 CTE（WITH ... SELECT）应通过"""
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)

    mock_result = MagicMock()
    mock_result.fetchmany.return_value = []
    mock_result.keys.return_value = ["n"]
    mock_result.returns_rows = True
    ctx.db = MagicMock()
    ctx.db.execute.return_value = mock_result

    result = await tool.execute(
        {"sql": "WITH nums AS (SELECT 1 AS n) SELECT * FROM nums"},
        ctx,
    )
    assert result.success is True


@pytest.mark.asyncio
async def test_db_query_empty_sql():
    """空 SQL 应被拒绝"""
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)

    result = await tool.execute({"sql": ""}, ctx)
    assert result.success is False

    result = await tool.execute({"sql": "   "}, ctx)
    assert result.success is False


@pytest.mark.asyncio
async def test_db_query_comment_only_sql():
    """只有注释的 SQL 应被拒绝"""
    tool = DbQueryTool()

    # 块注释 — 去除后为空
    ctx = MagicMock(spec=ToolContext)
    result = await tool.execute({"sql": "/* just a comment */"}, ctx)
    assert result.success is False

    # 行注释带换行 — 去除后为空
    ctx2 = MagicMock(spec=ToolContext)
    result = await tool.execute({"sql": "-- line comment\n"}, ctx2)
    assert result.success is False

    # 纯空白 — 应被拒绝
    ctx3 = MagicMock(spec=ToolContext)
    result = await tool.execute({"sql": "   \n  \t  "}, ctx3)
    assert result.success is False
