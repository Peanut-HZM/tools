import pytest
from sqlalchemy.dialects import mysql, postgresql
from app.utils.sql_executor import (
    SQLExecutor,
    _split_by_terminator,
    split_sql_script,
)
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
        mock_engine.dialect = mysql.dialect()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        result = SQLExecutor.execute("cfg1", {}, "UPDATE t SET x = '{\"version\":1}'")

        assert result.success is True
        executed_stmt = mock_conn.execute.call_args[0][0]
        # 冒号保持字面量送达数据库，且未产生绑定参数占位符
        assert ":1" in executed_stmt.text
        assert "%(" not in executed_stmt.text

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
        mock_engine.dialect = mysql.dialect()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        SQLExecutor.execute("cfg1", {}, "SELECT * FROM t WHERE id = :user_id")

        executed_stmt = mock_conn.execute.call_args[0][0]
        # 未提供 params 时冒号保持字面量，且未产生绑定参数占位符
        assert ":user_id" in executed_stmt.text
        assert "%(" not in executed_stmt.text

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
        mock_engine.dialect = postgresql.dialect()
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


INCIDENT_SCRIPT = """DELIMITER $$
CREATE PROCEDURE `dt_pf_add_column`(
    IN p_table_name VARCHAR(64),
    IN p_column_name VARCHAR(64),
    IN p_column_ddl TEXT
)
BEGIN
    IF EXISTS (
        SELECT 1 FROM INFORMATION_SCHEMA.TABLES
         WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = p_table_name
    ) THEN
        SET @dt_pf_sql = CONCAT('ALTER TABLE `', p_table_name, '` ADD COLUMN ', p_column_ddl);
        PREPARE dt_pf_stmt FROM @dt_pf_sql;
        EXECUTE dt_pf_stmt;
        DEALLOCATE PREPARE dt_pf_stmt;
    END IF;
END$$
DELIMITER ;"""


class TestSplitSqlScript:
    """测试分隔符感知的脚本切分。"""

    def test_semicolons_inside_custom_terminator_segment_not_split(self):
        """自定义终止符段内的分号不结束语句（存储过程体保持单条）。"""
        segment = "BEGIN SELECT 1; SELECT 2; END$$"
        statements = _split_by_terminator(segment, "$$")
        assert len(statements) == 1
        assert statements[0].strip() == "BEGIN SELECT 1; SELECT 2; END"

    def test_terminator_inside_string_and_comment_not_split(self):
        """字符串/行注释/块注释内出现的终止符不切分；EOF 余留成句。"""
        segment = "-- end$$ here\n/* x$$y */\nSET @s = 'a$$b';\nSELECT 1$$\nSELECT 2"
        statements = _split_by_terminator(segment, "$$")
        assert len(statements) == 2
        assert "end$$ here" in statements[0]
        assert "x$$y" in statements[0]
        assert "a$$b" in statements[0]
        assert statements[0].rstrip().endswith("SELECT 1")
        assert statements[1].strip() == "SELECT 2"

    def test_double_quoted_hash_comment_and_escapes(self):
        """双引号字符串、# 行注释、串内转义不影响切分。"""
        segment = '# hash$$ comment\nSET @s = "a\\"$$b";\nSET @t = \'it\'\'s$$\';\nSELECT 3$$'
        statements = _split_by_terminator(segment, "$$")
        assert len(statements) == 1
        body = statements[0]
        assert 'a\\"$$b' in body
        assert "it''s$$" in body
        assert body.rstrip().endswith("SELECT 3")

    def test_directive_lines_split_segments(self):
        """指令行切换终止符且自身不产生语句。"""
        from app.utils.sql_executor import _split_segments

        segments = _split_segments("SELECT 1;\nDELIMITER $$\nPROC BODY$$\nDELIMITER ;\nSELECT 2;")
        assert [(s.strip(), t) for s, t in segments] == [
            ("SELECT 1;", ";"),
            ("PROC BODY$$", "$$"),
            ("SELECT 2;", ";"),
        ]

    def test_directive_inside_string_not_honored(self):
        """跨行字符串字面量内的伪指令行不切换终止符。"""
        from app.utils.sql_executor import _split_segments

        segments = _split_segments("SET @s = 'x\nDELIMITER $$\ny';\nSELECT @s;")
        assert [t for _, t in segments] == [";"]
        assert len(segments) == 1

    def test_directive_inside_comment_not_honored(self):
        """注释内的伪指令行不切换终止符。"""
        from app.utils.sql_executor import _split_segments

        segments = _split_segments("-- DELIMITER $$\n/* DELIMITER // */\nSELECT 1;")
        assert [t for _, t in segments] == [";"]

    def test_lowercase_delimiter_with_slash_terminator(self):
        """指令大小写不敏感，支持多字符终止符。"""
        from app.utils.sql_executor import _split_segments

        segments = _split_segments(
            "delimiter //\nBEGIN SELECT 1; END//\ndelimiter ;\nSELECT 2;"
        )
        assert [t for s, t in segments if s.strip()] == ["//", ";"]

    def test_incident_procedure_script_single_statement(self):
        """事故脚本：恰 1 条语句，不含 DELIMITER 与 $$。"""
        statements = split_sql_script(INCIDENT_SCRIPT)
        assert len(statements) == 1
        body = statements[0].strip()
        assert body.startswith("CREATE PROCEDURE")
        assert body.endswith("END")
        assert "DELIMITER" not in body
        assert "$$" not in body

    def test_mixed_script_order_and_count(self):
        """混合脚本：普通语句 + DELIMITER 块 + 普通语句，条数与顺序正确。"""
        script = "SELECT 1;\n" + INCIDENT_SCRIPT + "\nSELECT 2;"
        statements = split_sql_script(script)
        assert len(statements) == 3
        assert statements[0].strip() == "SELECT 1;"
        assert statements[1].strip().startswith("CREATE PROCEDURE")
        assert statements[2].strip() == "SELECT 2;"

    def test_eof_remainder_becomes_statement(self):
        """最后一段无终止符结尾的余留内容作为一条语句。"""
        statements = split_sql_script("DELIMITER $$\nSELECT 1$$\nSELECT 2")
        assert [s.strip() for s in statements] == ["SELECT 1", "SELECT 2"]

    def test_malformed_inline_delimiter_raises(self):
        """行中 DELIMITER / 裸 DELIMITER 抛中文 ValueError。"""
        with pytest.raises(ValueError, match="DELIMITER 是 mysql 客户端指令"):
            split_sql_script("SELECT 1; DELIMITER $$")
        with pytest.raises(ValueError, match="DELIMITER 是 mysql 客户端指令"):
            split_sql_script("DELIMITER\nSELECT 1;")

    def test_plain_multi_statement_script_unchanged(self):
        """无指令的普通多语句脚本行为不变（默认 ; 委托 sqlparse）。"""
        statements = split_sql_script("SELECT 1;\nUPDATE t SET a = 1;")
        assert [s.strip() for s in statements] == ["SELECT 1;", "UPDATE t SET a = 1;"]


class TestSQLExecutorDelimiterScript:
    """执行器级：事故脚本发送的语句不含 DELIMITER。"""

    @patch("app.utils.sql_executor.DBConnectionManager.get_engine")
    def test_executor_sends_procedure_without_delimiter(self, mock_get_engine):
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.returns_rows = False
        mock_result.rowcount = 0
        mock_conn.execute.return_value = mock_result
        mock_engine = MagicMock()
        mock_engine.dialect = mysql.dialect()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        result = SQLExecutor.execute("cfg1", {}, INCIDENT_SCRIPT)

        assert result.success is True
        executed = mock_conn.execute.call_args[0][0]
        assert executed.text.lstrip().startswith("CREATE PROCEDURE")
        assert "DELIMITER" not in executed.text

    @patch("app.utils.sql_executor.DBConnectionManager.get_engine")
    def test_executor_returns_chinese_error_for_malformed_delimiter(
        self, mock_get_engine
    ):
        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        result = SQLExecutor.execute("cfg1", {}, "SELECT 1; DELIMITER $$")

        assert result.success is False
        assert "DELIMITER 是 mysql 客户端指令" in result.error_message
