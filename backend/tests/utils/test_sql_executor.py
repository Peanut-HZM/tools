import pytest
from app.utils.sql_executor import SQLExecutor
from unittest.mock import MagicMock, patch


class TestSQLExecutorBindParameterEscaping:
    """测试 SQLExecutor 对冒号绑定参数的转义行为。"""

    @patch("app.utils.sql_executor.DBConnectionManager.get_engine")
    @patch("app.utils.sql_executor.sqlparse.split")
    def test_json_with_numeric_colon_not_treated_as_bind_param(
        self, mock_split, mock_get_engine
    ):
        """JSON 中的 :1 不应被 SQLAlchemy 视为命名参数绑定。"""
        mock_split.return_value = [
            "UPDATE t SET x = '{\"version\":1,\"fields\":[]}'"
        ]
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.returns_rows = False
        mock_result.rowcount = 1
        mock_conn.execute.return_value = mock_result
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        result = SQLExecutor.execute("cfg1", {}, "UPDATE t SET x = '{\"version\":1}'")

        assert result.success is True
        executed_stmt = mock_conn.execute.call_args[0][0]
        assert "\\:1" in executed_stmt.text

    @patch("app.utils.sql_executor.DBConnectionManager.get_engine")
    @patch("app.utils.sql_executor.sqlparse.split")
    def test_named_param_escaped_when_no_params_provided(
        self, mock_split, mock_get_engine
    ):
        """未提供 params 时，命名参数应被转义。"""
        mock_split.return_value = ["SELECT * FROM t WHERE id = :user_id"]
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.returns_rows = True
        mock_result.keys.return_value = ["id"]
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        SQLExecutor.execute("cfg1", {}, "SELECT * FROM t WHERE id = :user_id")

        executed_stmt = mock_conn.execute.call_args[0][0]
        assert "\\:user_id" in executed_stmt.text

    @patch("app.utils.sql_executor.DBConnectionManager.get_engine")
    @patch("app.utils.sql_executor.sqlparse.split")
    def test_postgres_type_cast_preserved(self, mock_split, mock_get_engine):
        """PostgreSQL 的 :: 类型转换语法不应被破坏。"""
        mock_split.return_value = ["SELECT 1::integer"]
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.returns_rows = True
        mock_result.keys.return_value = ["col"]
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        SQLExecutor.execute("cfg1", {}, "SELECT 1::integer")

        executed_stmt = mock_conn.execute.call_args[0][0]
        compiled = str(executed_stmt)
        assert "::integer" in compiled

    @patch("app.utils.sql_executor.DBConnectionManager.get_engine")
    @patch("app.utils.sql_executor.sqlparse.split")
    def test_params_provided_no_escaping(self, mock_split, mock_get_engine):
        """提供 params 时，不应进行转义。"""
        mock_split.return_value = ["SELECT * FROM t WHERE id = :user_id"]
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.returns_rows = True
        mock_result.keys.return_value = ["id"]
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        SQLExecutor.execute(
            "cfg1", {}, "SELECT * FROM t WHERE id = :user_id", {"user_id": 42}
        )

        call_args = mock_conn.execute.call_args[0]
        assert len(call_args) == 2
        assert call_args[1] == {"user_id": 42}
