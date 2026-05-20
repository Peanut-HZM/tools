"""
SQL Schema 注入器

基于 sqlparse AST 解析 SQL，为 PostgreSQL 中未指定 schema 的表名自动注入 schema 前缀。
仅处理已知的 SQL 关键字后的表名：FROM, JOIN 系列, UPDATE, INTO, ALTER TABLE, TRUNCATE TABLE, DROP TABLE。
"""

import sqlparse
from sqlparse.tokens import Keyword, DML, Punctuation


TABLE_KEYWORDS = {
    "FROM",
    "JOIN",
    "INNER JOIN",
    "LEFT JOIN",
    "RIGHT JOIN",
    "OUTER JOIN",
    "LEFT OUTER JOIN",
    "RIGHT OUTER JOIN",
    "FULL JOIN",
    "FULL OUTER JOIN",
    "CROSS JOIN",
    "NATURAL JOIN",
    "INTO",
    "UPDATE",
}

COMPOUND_KEYWORDS = {"ALTER TABLE", "TRUNCATE TABLE", "DROP TABLE"}

# SQL 保留关键字集合，避免把这些当作表名
SQL_KEYWORDS = {
    "SELECT", "INSERT", "UPDATE", "DELETE", "FROM", "WHERE", "AND", "OR",
    "NOT", "NULL", "AS", "ON", "IN", "IS", "LIKE", "BETWEEN", "ORDER",
    "BY", "GROUP", "HAVING", "LIMIT", "OFFSET", "UNION", "ALL", "DISTINCT",
    "EXISTS", "CASE", "WHEN", "THEN", "ELSE", "END", "WITH", "RECURSIVE",
    "VALUES", "INTO", "SET", "RETURNING", "TRUE", "FALSE", "DEFAULT",
    "CREATE", "ALTER", "DROP", "TRUNCATE", "TABLE", "INDEX", "VIEW",
    "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "CONSTRAINT", "UNIQUE",
    "CHECK",
}


def _is_schema_qualified(name: str) -> bool:
    """判断表名是否已包含 schema 前缀"""
    clean = name.strip().strip('"').strip("'")
    return "." in clean


def _inject_into_token(token_str: str, schema_name: str) -> str:
    """给单个 token 字符串注入 schema 前缀"""
    stripped = token_str.strip()
    if not stripped:
        return token_str
    if _is_schema_qualified(stripped):
        return token_str
    upper = stripped.upper()
    if upper in SQL_KEYWORDS:
        return token_str
    return f'"{schema_name}".{stripped}'


def inject_schema_name(sql: str, schema_name: str) -> str:
    """
    为 SQL 中未指定 schema 的表名注入 schema 前缀。

    Args:
        sql: 单条 SQL 语句
        schema_name: 要注入的 schema 名称

    Returns:
        注入 schema 前缀后的 SQL
    """
    if not schema_name:
        return sql

    parsed = sqlparse.parse(sql)
    if not parsed:
        return sql

    statements = []
    for stmt in parsed:
        s = str(stmt).strip()
        if s:
            statements.append(_process_statement(stmt, schema_name))

    return " ".join(statements) if statements else sql


def _process_statement(statement, schema_name: str) -> str:
    """处理单条 SQL 语句，为表名注入 schema 前缀"""
    tokens = list(statement.flatten())
    if not tokens:
        return str(statement)

    result_parts = []
    i = 0

    while i < len(tokens):
        token = tokens[i]
        token_str = str(token).strip()
        if not token_str:
            i += 1
            continue

        token_upper = token_str.upper()

        # 检查复合关键字（ALTER TABLE, TRUNCATE TABLE, DROP TABLE）
        if i + 1 < len(tokens):
            next_str = str(tokens[i + 1]).strip().upper()
            compound = f"{token_upper} {next_str}"
            if compound in COMPOUND_KEYWORDS:
                result_parts.append(token_str)
                result_parts.append(str(tokens[i + 1]).strip())
                i += 2
                while i < len(tokens) and not str(tokens[i]).strip():
                    i += 1
                if i < len(tokens):
                    table_token = str(tokens[i]).strip()
                    if not _is_schema_qualified(table_token):
                        table_token = f'"{schema_name}".{table_token}'
                    result_parts.append(table_token)
                    i += 1
                continue

        # 检查表关键字
        is_table_keyword = False

        if token_upper in TABLE_KEYWORDS:
            is_table_keyword = True
        elif token_upper == "JOIN":
            is_table_keyword = True

        if is_table_keyword:
            result_parts.append(token_str)
            i += 1
            while i < len(tokens) and not str(tokens[i]).strip():
                i += 1
            if i < len(tokens):
                table_token = str(tokens[i]).strip()
                if table_token.startswith("("):
                    result_parts.append(table_token)
                    i += 1
                    continue
                if not _is_schema_qualified(table_token):
                    next_i = i + 1
                    while next_i < len(tokens) and not str(tokens[next_i]).strip():
                        next_i += 1
                    if next_i < len(tokens) and str(tokens[next_i]).strip() == '(':
                        result_parts.append(table_token)
                    else:
                        table_token = f'"{schema_name}".{table_token}'
                        result_parts.append(table_token)
                    i += 1
                else:
                    result_parts.append(table_token)
                    i += 1
            continue

        # UPDATE 开头的表名处理（UPDATE 后面直接跟表名）
        if token_upper == "UPDATE":
            result_parts.append(token_str)
            i += 1
            while i < len(tokens) and not str(tokens[i]).strip():
                i += 1
            if i < len(tokens):
                table_token = str(tokens[i]).strip()
                if not _is_schema_qualified(table_token):
                    table_token = f'"{schema_name}".{table_token}'
                result_parts.append(table_token)
                i += 1
            continue

        result_parts.append(token_str)
        i += 1

    return " ".join(result_parts)


def process_sql_with_schema_injection(sql: str, schema_name: str) -> str:
    """
    处理可能包含多条语句的 SQL，为每条语句注入 schema 前缀。

    Args:
        sql: 可能包含多条语句的 SQL（以分号分隔）
        schema_name: 要注入的 schema 名称

    Returns:
        注入后的 SQL
    """
    if not schema_name:
        return sql

    statements = sqlparse.split(sql)
    processed = []

    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue
        processed.append(inject_schema_name(stmt, schema_name))

    return "; ".join(processed)
