"""
Author: Claude Code
Created: 2026-04-26
Purpose: Multi-database backup SQL generators
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from sqlalchemy import text

logger = logging.getLogger(__name__)


class BackupGenerator(ABC):
    """备份 SQL 生成器抽象基类"""

    @abstractmethod
    def get_create_table_ddl(self, conn, table: str, database_name: Optional[str] = None) -> str:
        """获取 CREATE TABLE DDL"""
        pass

    @abstractmethod
    def get_insert_statements(self, conn, table: str, database_name: Optional[str] = None) -> List[str]:
        """获取 INSERT INTO 语句列表"""
        pass

    def _quote_value(self, val) -> str:
        """安全地转义 SQL 值"""
        if val is None:
            return "NULL"
        if isinstance(val, bool):
            return "1" if val else "0"
        if isinstance(val, (int, float)):
            return str(val)
        # 字符串：转义单引号
        s = str(val).replace("'", "''")
        return f"'{s}'"


class MySQLBackupGenerator(BackupGenerator):
    """MySQL / MariaDB 备份生成器"""

    def get_create_table_ddl(self, conn, table: str, database_name: Optional[str] = None) -> str:
        try:
            result = conn.execute(text(f"SHOW CREATE TABLE `{table}`"))
            row = result.fetchone()
            if row:
                return row[1]
        except Exception as e:
            logger.warning(f"SHOW CREATE TABLE failed for {table}: {e}")
            # Fallback: 使用 SQLAlchemy inspector 构建
            return self._build_create_table_from_inspector(conn, table)
        return f"-- Failed to get DDL for table `{table}`"

    def _build_create_table_from_inspector(self, conn, table: str) -> str:
        """使用 SQLAlchemy inspector 构建 CREATE TABLE"""
        from sqlalchemy import inspect
        inspector = inspect(conn.engine)
        columns = inspector.get_columns(table)
        pk = inspector.get_pk_constraint(table)
        indexes = inspector.get_indexes(table)
        fks = inspector.get_foreign_keys(table)

        lines = [f"CREATE TABLE `{table}` ("]
        col_defs = []
        for col in columns:
            col_type = str(col['type'])
            nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
            default = ""
            if col.get('default') is not None:
                default = f" DEFAULT {self._quote_value(col['default'])}"
            auto_inc = " AUTO_INCREMENT" if col.get('autoincrement', False) else ""
            col_defs.append(f"    `{col['name']}` {col_type} {nullable}{default}{auto_inc}")

        # Primary Key
        if pk and pk.get('constrained_columns'):
            pk_cols = ', '.join([f"`{c}`" for c in pk['constrained_columns']])
            col_defs.append(f"    PRIMARY KEY ({pk_cols})")

        # Foreign Keys
        for fk in fks:
            if fk.get('constrained_columns') and fk.get('referred_table'):
                fk_cols = ', '.join([f"`{c}`" for c in fk['constrained_columns']])
                ref_cols = ', '.join([f"`{c}`" for c in fk.get('referred_columns', [])])
                ref_table = fk['referred_table']
                col_defs.append(f"    FOREIGN KEY ({fk_cols}) REFERENCES `{ref_table}` ({ref_cols})")

        lines.append(',\n'.join(col_defs))
        lines.append(")")

        # Indexes (non-PK)
        for idx in indexes:
            if idx.get('unique'):
                idx_cols = ', '.join([f"`{c}`" for c in idx['column_names']])
                lines.append(f"CREATE UNIQUE INDEX `{idx['name']}` ON `{table}` ({idx_cols});")
            elif not idx.get('name', '').startswith('PRIMARY'):
                idx_cols = ', '.join([f"`{c}`" for c in idx['column_names']])
                lines.append(f"CREATE INDEX `{idx['name']}` ON `{table}` ({idx_cols});")

        return '\n'.join(lines)

    def get_insert_statements(self, conn, table: str, database_name: Optional[str] = None) -> List[str]:
        statements = []
        try:
            result = conn.execute(text(f"SELECT * FROM `{table}`"))
            rows = result.fetchall()
            if not rows:
                return [f"-- Table `{table}` is empty"]

            columns = result.keys()
            col_str = ', '.join([f"`{c}`" for c in columns])

            for row in rows:
                values = [self._quote_value(val) for val in row]
                val_str = ', '.join(values)
                statements.append(f"INSERT INTO `{table}` ({col_str}) VALUES ({val_str});")

        except Exception as e:
            logger.warning(f"Failed to get data from `{table}`: {e}")
            statements.append(f"-- Failed to backup data for table `{table}`: {e}")

        return statements


class PostgreSQLBackupGenerator(BackupGenerator):
    """PostgreSQL 备份生成器"""

    def get_create_table_ddl(self, conn, table: str, database_name: Optional[str] = None) -> str:
        try:
            # 使用 pg_dump 风格的查询获取 DDL
            result = conn.execute(text(f"""
                SELECT pg_catalog.pg_get_tabledef('{table}'::regclass::oid)
            """))
            row = result.fetchone()
            if row and row[0]:
                return row[0]
        except Exception:
            pass

        # Fallback: 手动构建
        return self._build_create_table_pg(conn, table)

    def _build_create_table_pg(self, conn, table: str) -> str:
        from sqlalchemy import inspect
        inspector = inspect(conn.engine)
        columns = inspector.get_columns(table)
        pk = inspector.get_pk_constraint(table)
        indexes = inspector.get_indexes(table)
        fks = inspector.get_foreign_keys(table)

        lines = [f"CREATE TABLE IF NOT EXISTS \"{table}\" ("]
        col_defs = []
        for col in columns:
            col_type = str(col['type'])
            nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
            default = ""
            if col.get('default') is not None:
                default = f" DEFAULT {self._quote_value(col['default'])}"
            col_defs.append(f"    \"{col['name']}\" {col_type} {nullable}{default}")

        if pk and pk.get('constrained_columns'):
            pk_cols = ', '.join([f"\"{c}\"" for c in pk['constrained_columns']])
            col_defs.append(f"    PRIMARY KEY ({pk_cols})")

        for fk in fks:
            if fk.get('constrained_columns') and fk.get('referred_table'):
                fk_cols = ', '.join([f"\"{c}\"" for c in fk['constrained_columns']])
                ref_cols = ', '.join([f"\"{c}\"" for c in fk.get('referred_columns', [])])
                ref_table = fk['referred_table']
                col_defs.append(f"    FOREIGN KEY ({fk_cols}) REFERENCES \"{ref_table}\" ({ref_cols})")

        lines.append(',\n'.join(col_defs))
        lines.append(");")

        for idx in indexes:
            if not idx.get('name', '').startswith('PRIMARY'):
                idx_cols = ', '.join([f"\"{c}\"" for c in idx['column_names']])
                unique = "UNIQUE " if idx.get('unique') else ""
                lines.append(f"CREATE {unique}INDEX \"{idx['name']}\" ON \"{table}\" ({idx_cols});")

        return '\n'.join(lines)

    def get_insert_statements(self, conn, table: str, database_name: Optional[str] = None) -> List[str]:
        statements = []
        try:
            result = conn.execute(text(f'SELECT * FROM "{table}"'))
            rows = result.fetchall()
            if not rows:
                return [f"-- Table \"{table}\" is empty"]

            columns = result.keys()
            col_str = ', '.join([f'"{c}"' for c in columns])

            for row in rows:
                values = [self._quote_value(val) for val in row]
                val_str = ', '.join(values)
                statements.append(f'INSERT INTO "{table}" ({col_str}) VALUES ({val_str});')

        except Exception as e:
            logger.warning(f"Failed to get data from \"{table}\": {e}")
            statements.append(f"-- Failed to backup data for table \"{table}\": {e}")

        return statements


class SQLiteBackupGenerator(BackupGenerator):
    """SQLite 备份生成器"""

    def get_create_table_ddl(self, conn, table: str, database_name: Optional[str] = None) -> str:
        try:
            result = conn.execute(text(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=:name"
            ), {"name": table})
            row = result.fetchone()
            if row and row[0]:
                return row[0]
        except Exception as e:
            logger.warning(f"Failed to get DDL for {table}: {e}")
        return f"-- Failed to get DDL for table [{table}]"

    def get_insert_statements(self, conn, table: str, database_name: Optional[str] = None) -> List[str]:
        statements = []
        try:
            result = conn.execute(text(f'SELECT * FROM "{table}"'))
            rows = result.fetchall()
            if not rows:
                return [f"-- Table [{table}] is empty"]

            columns = result.keys()
            col_str = ', '.join([f'"{c}"' for c in columns])

            for row in rows:
                values = [self._quote_value(val) for val in row]
                val_str = ', '.join(values)
                statements.append(f'INSERT INTO "{table}" ({col_str}) VALUES ({val_str});')

        except Exception as e:
            logger.warning(f"Failed to get data from [{table}]: {e}")
            statements.append(f"-- Failed to backup data for table [{table}]: {e}")

        return statements


class SQLServerBackupGenerator(BackupGenerator):
    """SQL Server 备份生成器"""

    def get_create_table_ddl(self, conn, table: str, database_name: Optional[str] = None) -> str:
        # SQL Server 没有简单的 SHOW CREATE TABLE，需要手动构建
        from sqlalchemy import inspect
        inspector = inspect(conn.engine)
        columns = inspector.get_columns(table)
        pk = inspector.get_pk_constraint(table)
        indexes = inspector.get_indexes(table)
        fks = inspector.get_foreign_keys(table)

        lines = [f"IF OBJECT_ID('{table}', 'U') IS NOT NULL DROP TABLE [{table}];"]
        lines.append(f"CREATE TABLE [{table}] (")
        col_defs = []
        for col in columns:
            col_type = str(col['type'])
            nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
            default = ""
            if col.get('default') is not None:
                default = f" DEFAULT {self._quote_value(col['default'])}"
            identity = " IDENTITY(1,1)" if col.get('autoincrement', False) else ""
            col_defs.append(f"    [{col['name']}] {col_type}{identity} {nullable}{default}")

        if pk and pk.get('constrained_columns'):
            pk_cols = ', '.join([f"[{c}]" for c in pk['constrained_columns']])
            col_defs.append(f"    CONSTRAINT {pk.get('name', 'PK_' + table)} PRIMARY KEY ({pk_cols})")

        for fk in fks:
            if fk.get('constrained_columns') and fk.get('referred_table'):
                fk_cols = ', '.join([f"[{c}]" for c in fk['constrained_columns']])
                ref_cols = ', '.join([f"[{c}]" for c in fk.get('referred_columns', [])])
                ref_table = fk['referred_table']
                fk_name = fk.get('name', f"FK_{table}_{ref_table}")
                col_defs.append(f"    CONSTRAINT {fk_name} FOREIGN KEY ({fk_cols}) REFERENCES [{ref_table}] ({ref_cols})")

        lines.append(',\n'.join(col_defs))
        lines.append(");")

        for idx in indexes:
            if not idx.get('name', '').startswith('PK_'):
                idx_cols = ', '.join([f"[{c}]" for c in idx['column_names']])
                unique = "UNIQUE " if idx.get('unique') else ""
                lines.append(f"CREATE {unique}INDEX {idx['name']} ON [{table}] ({idx_cols});")

        return '\n'.join(lines)

    def get_insert_statements(self, conn, table: str, database_name: Optional[str] = None) -> List[str]:
        statements = []
        try:
            result = conn.execute(text(f"SELECT * FROM [{table}]"))
            rows = result.fetchall()
            if not rows:
                return [f"-- Table [{table}] is empty"]

            columns = result.keys()
            col_str = ', '.join([f"[{c}]" for c in columns])

            for row in rows:
                values = [self._quote_value(val) for val in row]
                val_str = ', '.join(values)
                statements.append(f"INSERT INTO [{table}] ({col_str}) VALUES ({val_str});")

        except Exception as e:
            logger.warning(f"Failed to get data from [{table}]: {e}")
            statements.append(f"-- Failed to backup data for table [{table}]: {e}")

        return statements


class OracleBackupGenerator(BackupGenerator):
    """Oracle 备份生成器"""

    def get_create_table_ddl(self, conn, table: str, database_name: Optional[str] = None) -> str:
        from sqlalchemy import inspect
        inspector = inspect(conn.engine)
        columns = inspector.get_columns(table)
        pk = inspector.get_pk_constraint(table)
        indexes = inspector.get_indexes(table)
        fks = inspector.get_foreign_keys(table)

        lines = [f"CREATE TABLE \"{table.upper()}\" ("]
        col_defs = []
        for col in columns:
            col_type = str(col['type'])
            nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
            default = ""
            if col.get('default') is not None:
                default = f" DEFAULT {self._quote_value(col['default'])}"
            col_defs.append(f"    \"{col['name'].upper()}\" {col_type} {nullable}{default}")

        if pk and pk.get('constrained_columns'):
            pk_cols = ', '.join([f'"{c.upper()}"' for c in pk['constrained_columns']])
            col_defs.append(f"    CONSTRAINT {pk.get('name', 'PK_' + table.upper())} PRIMARY KEY ({pk_cols})")

        for fk in fks:
            if fk.get('constrained_columns') and fk.get('referred_table'):
                fk_cols = ', '.join([f'"{c.upper()}"' for c in fk['constrained_columns']])
                ref_cols = ', '.join([f'"{c.upper()}"' for c in fk.get('referred_columns', [])])
                ref_table = fk['referred_table'].upper()
                fk_name = fk.get('name', f"FK_{table.upper()}_{ref_table}")
                col_defs.append(f"    CONSTRAINT {fk_name} FOREIGN KEY ({fk_cols}) REFERENCES \"{ref_table}\" ({ref_cols})")

        lines.append(',\n'.join(col_defs))
        lines.append(");")

        for idx in indexes:
            if not idx.get('name', '').startswith('PK_'):
                idx_cols = ', '.join([f'"{c.upper()}"' for c in idx['column_names']])
                unique = "UNIQUE " if idx.get('unique') else ""
                lines.append(f"CREATE {unique}INDEX \"{idx['name']}\" ON \"{table.upper()}\" ({idx_cols});")

        return '\n'.join(lines)

    def get_insert_statements(self, conn, table: str, database_name: Optional[str] = None) -> List[str]:
        statements = []
        try:
            result = conn.execute(text(f'SELECT * FROM "{table.upper()}"'))
            rows = result.fetchall()
            if not rows:
                return [f"-- Table \"{table.upper()}\" is empty"]

            columns = result.keys()
            col_str = ', '.join([f'"{c.upper()}"' for c in columns])

            for row in rows:
                values = [self._quote_value(val) for val in row]
                val_str = ', '.join(values)
                statements.append(f'INSERT INTO "{table.upper()}" ({col_str}) VALUES ({val_str});')

        except Exception as e:
            logger.warning(f"Failed to get data from \"{table.upper()}\": {e}")
            statements.append(f"-- Failed to backup data for table \"{table.upper()}\": {e}")

        return statements


# 生成器工厂
GENERATOR_MAP = {
    "mysql": MySQLBackupGenerator,
    "mariadb": MySQLBackupGenerator,
    "postgresql": PostgreSQLBackupGenerator,
    "sqlite": SQLiteBackupGenerator,
    "sqlserver": SQLServerBackupGenerator,
    "oracle": OracleBackupGenerator,
}


def get_generator(db_type: str) -> BackupGenerator:
    """根据数据库类型获取对应的备份生成器"""
    db_type = db_type.lower()
    if db_type not in GENERATOR_MAP:
        logger.warning(f"Unknown database type '{db_type}', falling back to MySQL generator")
        return MySQLBackupGenerator()
    return GENERATOR_MAP[db_type]()
