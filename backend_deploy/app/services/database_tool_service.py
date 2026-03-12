import uuid
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.config.database import get_db_connection
from app.models.database_tool_models import (
    DatabaseConfigBase, CreateDatabaseRequest, UpdateDatabaseRequest, 
    DatabaseConfigResponse, TestConnectionRequest, ConnectionTestResult,
    SQLExecutionRequest, SQLExecutionResult, ExecutionHistory,
    TableSchema, TableData, DatabaseType,
    ColumnDefinition, TableModificationRequest
)
from app.utils.encryption import EncryptionUtils
from app.utils.db_connection_manager import DBConnectionManager
from app.utils.sql_executor import SQLExecutor
from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)

class DatabaseToolService:
    
    @staticmethod
    def generate_ddl(user_id: str, config_id: str, table_name: str, database_name: str) -> str:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
            
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": database_name,
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        engine_key = f"{config_id}:{database_name}"
        engine = DBConnectionManager.get_engine(engine_key, config_dict)
        db_type = config_row['db_type']
        
        try:
            if db_type == DatabaseType.MYSQL or db_type == DatabaseType.MARIADB:
                with engine.connect() as conn:
                    result = conn.execute(text(f"SHOW CREATE TABLE {table_name}"))
                    row = result.fetchone()
                    if row and len(row) > 1:
                        return row[1]
            elif db_type == DatabaseType.SQLITE:
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'"))
                    row = result.fetchone()
                    if row:
                        return row[0]
            
            # Fallback for others (PostgreSQL, SQLServer, Oracle) using SQLAlchemy
            # Note: This might not be perfect as it reconstructs from metadata
            from sqlalchemy.schema import CreateTable
            from sqlalchemy import MetaData, Table
            
            metadata = MetaData()
            # We need to reflect the table first
            table = Table(table_name, metadata, autoload_with=engine)
            return str(CreateTable(table).compile(engine))
            
        except Exception as e:
            logger.error(f"Failed to generate DDL: {e}")
            raise e

    @staticmethod
    def modify_table_structure(user_id: str, config_id: str, request: TableModificationRequest) -> bool:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
            
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": request.database_name,
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        engine_key = f"{config_id}:{request.database_name}"
        engine = DBConnectionManager.get_engine(engine_key, config_dict)
        db_type = config_row['db_type']
        
        # Current support mainly for MySQL
        if db_type not in [DatabaseType.MYSQL, DatabaseType.MARIADB]:
             # TODO: Implement for other DBs
             # For now, we only support MySQL/MariaDB for structure modification as it requires specific DDL
             pass

        try:
            inspector = inspect(engine)
            existing_columns = inspector.get_columns(request.table_name)
            existing_col_map = {col['name']: col for col in existing_columns}
            
            statements = []
            
            # 1. Handle Columns
            # We need to preserve order, but ALTER usually appends or needs AFTER/FIRST
            # For simplicity, we just generate ADD/MODIFY/DROP. Reordering is hard.
            
            # Helper for MySQL type mapping/formatting
            def format_col_def(col: ColumnDefinition):
                def_str = f"`{col.name}` {col.type}"
                if col.length:
                    def_str += f"({col.length})"
                
                if not col.nullable:
                    def_str += " NOT NULL"
                else:
                    def_str += " NULL"
                
                if col.default_value is not None:
                    # simplistic quoting for default
                    if col.default_value.upper() in ['CURRENT_TIMESTAMP', 'NULL']:
                        def_str += f" DEFAULT {col.default_value}"
                    else:
                        def_str += f" DEFAULT '{col.default_value}'"
                
                if col.auto_increment:
                    def_str += " AUTO_INCREMENT"
                
                if col.comment:
                    def_str += f" COMMENT '{col.comment}'"
                    
                return def_str

            new_col_names = set()
            
            for col in request.columns:
                new_col_names.add(col.name)
                if col.name not in existing_col_map:
                    # ADD
                    statements.append(f"ALTER TABLE `{request.table_name}` ADD COLUMN {format_col_def(col)}")
                else:
                    # MODIFY
                    # We should check if it actually changed, but for now we can just MODIFY to be safe/lazy
                    # or compare fields.
                    # Comparing is safer to avoid unnecessary ops, but type conversion might make it tricky (e.g. VARCHAR(255) vs VARCHAR(255))
                    # Let's assume we modify if it exists.
                    # Note: In MySQL, MODIFY COLUMN needs full definition.
                    statements.append(f"ALTER TABLE `{request.table_name}` MODIFY COLUMN {format_col_def(col)}")

            # DROP columns
            for existing_name in existing_col_map:
                if existing_name not in new_col_names:
                    statements.append(f"ALTER TABLE `{request.table_name}` DROP COLUMN `{existing_name}`")

            # 2. Handle Table Comment
            if request.comment is not None:
                statements.append(f"ALTER TABLE `{request.table_name}` COMMENT = '{request.comment}'")
                
            # 3. Handle Table Rename
            if request.new_table_name and request.new_table_name != request.table_name:
                statements.append(f"ALTER TABLE `{request.table_name}` RENAME TO `{request.new_table_name}`")

            # Execute all statements
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                for sql in statements:
                    conn.execute(text(sql))
            
            return True

        except Exception as e:
            logger.error(f"Failed to modify table: {e}")
            raise e

    @staticmethod
    def delete_all_tables(user_id: str, config_id: str, database_name: str) -> bool:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
            
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": database_name,
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        engine_key = f"{config_id}:{database_name}"
        engine = DBConnectionManager.get_engine(engine_key, config_dict)
        db_type = config_row['db_type']
        
        try:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                # Disable foreign key checks for MySQL to avoid constraint errors
                if db_type == DatabaseType.MYSQL or db_type == DatabaseType.MARIADB:
                    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                    
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                for table in tables:
                    if db_type == DatabaseType.POSTGRESQL:
                        conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                    else:
                        conn.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
                
                # Re-enable foreign key checks
                if db_type == DatabaseType.MYSQL or db_type == DatabaseType.MARIADB:
                    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                    
            return True
        except Exception as e:
            logger.error(f"Failed to delete all tables: {e}")
            raise e

    @staticmethod
    def truncate_all_tables(user_id: str, config_id: str, database_name: str) -> bool:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
            
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": database_name,
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        engine_key = f"{config_id}:{database_name}"
        engine = DBConnectionManager.get_engine(engine_key, config_dict)
        db_type = config_row['db_type']
        
        try:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                # Disable foreign key checks for MySQL
                if db_type == DatabaseType.MYSQL or db_type == DatabaseType.MARIADB:
                    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                for table in tables:
                    if db_type == DatabaseType.SQLITE:
                        conn.execute(text(f"DELETE FROM `{table}`"))
                    elif db_type == DatabaseType.POSTGRESQL:
                        conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
                    else:
                        conn.execute(text(f"TRUNCATE TABLE `{table}`"))
                
                # Re-enable foreign key checks
                if db_type == DatabaseType.MYSQL or db_type == DatabaseType.MARIADB:
                    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                    
            return True
        except Exception as e:
            logger.error(f"Failed to truncate all tables: {e}")
            raise e

    @staticmethod
    def generate_all_tables_ddl(user_id: str, config_id: str, database_name: str) -> str:
        # Re-use existing generate_ddl logic but for all tables
        # Since getting all DDLs might be heavy, we should do it sequentially
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
        
        # We can reuse the single table generation logic
        # But let's avoid fetching config every time
        
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": database_name,
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        engine_key = f"{config_id}:{database_name}"
        engine = DBConnectionManager.get_engine(engine_key, config_dict)
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        full_ddl = ""
        
        for table in tables:
            try:
                # We can call the static method if we want, but better to inline or call helper to avoid overhead
                # Let's call helper
                ddl = DatabaseToolService.generate_ddl(user_id, config_id, table, database_name)
                full_ddl += f"-- Table: {table}\n{ddl};\n\n"
            except Exception as e:
                full_ddl += f"-- Failed to generate DDL for {table}: {str(e)}\n\n"
                
        return full_ddl

    # --------------------------------------------------------------------------
    # Database Configuration Management
    # --------------------------------------------------------------------------
    
    @staticmethod
    def get_all_configs(user_id: str, include_password: bool = False) -> List[DatabaseConfigResponse]:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM db_configs WHERE user_id = %s AND deleted = FALSE ORDER BY created_at DESC", 
                    (user_id,)
                )
                rows = cursor.fetchall()
                
                configs = []
                for row in rows:
                    password = None
                    if include_password:
                        try:
                            password = EncryptionUtils.decrypt(row['password_encrypted'])
                        except Exception:
                            password = None
                    # 'row' is a RealDictRow
                    config = DatabaseConfigResponse(
                        id=row['id'],
                        user_id=row['user_id'],
                        alias=row['alias'],
                        db_type=row['db_type'],
                        host=row['host'],
                        port=row['port'],
                        database_name=row['database_name'],
                        username=row['username'],
                        environment=row['environment'],
                        group_name=row['group_name'],
                        charset=row['charset'],
                        connect_timeout=row['connect_timeout'],
                        max_pool_size=row['max_pool_size'],
                        ssl_mode=row['ssl_mode'],
                        ssl_cert_path=row['ssl_cert_path'],
                        extra_config=row['extra_config'] if isinstance(row['extra_config'], dict) else (json.loads(row['extra_config']) if row['extra_config'] else None),
                        is_active=row['is_active'],
                        last_connected_at=row['last_connected_at'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        password=password
                    )
                    configs.append(config)
                return configs
        finally:
            conn.close()

    @staticmethod
    def get_config(config_id: str, user_id: str, include_password: bool = False) -> Optional[DatabaseConfigResponse]:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM db_configs WHERE id = %s AND user_id = %s AND deleted = FALSE",
                    (config_id, user_id)
                )
                row = cursor.fetchone()
                if not row:
                    return None
                password = None
                if include_password:
                    try:
                        password = EncryptionUtils.decrypt(row['password_encrypted'])
                    except Exception:
                        password = None
                return DatabaseConfigResponse(
                    id=row['id'],
                    user_id=row['user_id'],
                    alias=row['alias'],
                    db_type=row['db_type'],
                    host=row['host'],
                    port=row['port'],
                    database_name=row['database_name'],
                    username=row['username'],
                    environment=row['environment'],
                    group_name=row['group_name'],
                    charset=row['charset'],
                    connect_timeout=row['connect_timeout'],
                    max_pool_size=row['max_pool_size'],
                    ssl_mode=row['ssl_mode'],
                    ssl_cert_path=row['ssl_cert_path'],
                    extra_config=row['extra_config'] if isinstance(row['extra_config'], dict) else (json.loads(row['extra_config']) if row['extra_config'] else None),
                    is_active=row['is_active'],
                    last_connected_at=row['last_connected_at'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    password=password
                )
        finally:
            conn.close()

    @staticmethod
    def _get_config_with_password(config_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Internal helper to get config including encrypted password"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM db_configs WHERE id = %s AND user_id = %s AND deleted = FALSE",
                    (config_id, user_id)
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return dict(row)
        finally:
            conn.close()

    @staticmethod
    def create_config(user_id: str, request: CreateDatabaseRequest) -> DatabaseConfigResponse:
        conn = get_db_connection()
        try:
            # Encrypt password
            encrypted_password = EncryptionUtils.encrypt(request.password)
            
            config_id = str(uuid.uuid4())
            now = datetime.now()
            
            with conn.cursor() as cursor:
                # Check alias uniqueness for user
                cursor.execute(
                    "SELECT id FROM db_configs WHERE user_id = %s AND alias = %s AND deleted = FALSE",
                    (user_id, request.alias)
                )
                if cursor.fetchone():
                    raise ValueError(f"Alias '{request.alias}' already exists")

                cursor.execute(
                    """
                    INSERT INTO db_configs (
                        id, user_id, alias, db_type, host, port, database_name, username, 
                        password_encrypted, environment, group_name, charset, connect_timeout, 
                        max_pool_size, ssl_mode, ssl_cert_path, extra_config, is_active, 
                        created_at, updated_at, deleted
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, 
                        %s, %s, FALSE
                    )
                    """,
                    (
                        config_id, user_id, request.alias, request.db_type, request.host, request.port, 
                        request.database_name, request.username, encrypted_password, request.environment,
                        request.group_name, request.charset, request.connect_timeout, request.max_pool_size,
                        request.ssl_mode, request.ssl_cert_path, 
                        json.dumps(request.extra_config) if request.extra_config else None,
                        request.is_active, now, now
                    )
                )
                conn.commit()
                
            return DatabaseToolService.get_config(config_id, user_id)
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def update_config(config_id: str, user_id: str, request: UpdateDatabaseRequest) -> Optional[DatabaseConfigResponse]:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Check existence
                cursor.execute("SELECT id FROM db_configs WHERE id = %s AND user_id = %s AND deleted = FALSE", (config_id, user_id))
                if not cursor.fetchone():
                    return None
                
                updates = []
                params = []
                
                if request.alias is not None:
                    # Check alias uniqueness if changed
                    cursor.execute(
                        "SELECT id FROM db_configs WHERE user_id = %s AND alias = %s AND id != %s AND deleted = FALSE",
                        (user_id, request.alias, config_id)
                    )
                    if cursor.fetchone():
                        raise ValueError(f"Alias '{request.alias}' already exists")
                    updates.append("alias = %s")
                    params.append(request.alias)
                
                if request.host is not None:
                    updates.append("host = %s")
                    params.append(request.host)
                if request.port is not None:
                    updates.append("port = %s")
                    params.append(request.port)
                if request.database_name is not None:
                    updates.append("database_name = %s")
                    params.append(request.database_name)
                if request.username is not None:
                    updates.append("username = %s")
                    params.append(request.username)
                if request.password is not None:
                    encrypted = EncryptionUtils.encrypt(request.password)
                    updates.append("password_encrypted = %s")
                    params.append(encrypted)
                if request.environment is not None:
                    updates.append("environment = %s")
                    params.append(request.environment)
                if request.group_name is not None:
                    updates.append("group_name = %s")
                    params.append(request.group_name)
                if request.charset is not None:
                    updates.append("charset = %s")
                    params.append(request.charset)
                if request.connect_timeout is not None:
                    updates.append("connect_timeout = %s")
                    params.append(request.connect_timeout)
                if request.max_pool_size is not None:
                    updates.append("max_pool_size = %s")
                    params.append(request.max_pool_size)
                if request.ssl_mode is not None:
                    updates.append("ssl_mode = %s")
                    params.append(request.ssl_mode)
                if request.ssl_cert_path is not None:
                    updates.append("ssl_cert_path = %s")
                    params.append(request.ssl_cert_path)
                if request.extra_config is not None:
                    updates.append("extra_config = %s")
                    params.append(json.dumps(request.extra_config))
                if request.is_active is not None:
                    updates.append("is_active = %s")
                    params.append(request.is_active)
                
                if not updates:
                    return DatabaseToolService.get_config(config_id, user_id)
                
                updates.append("updated_at = %s")
                params.append(datetime.now())
                
                params.append(config_id)
                params.append(user_id)
                
                sql = f"UPDATE db_configs SET {', '.join(updates)} WHERE id = %s AND user_id = %s"
                cursor.execute(sql, tuple(params))
                conn.commit()
                
            # Clear engine cache if connection params changed
            DBConnectionManager.close_engine(config_id)
            
            return DatabaseToolService.get_config(config_id, user_id)
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def delete_config(config_id: str, user_id: str) -> bool:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Soft delete
                cursor.execute(
                    "UPDATE db_configs SET deleted = TRUE, updated_at = %s WHERE id = %s AND user_id = %s",
                    (datetime.now(), config_id, user_id)
                )
                if cursor.rowcount == 0:
                    return False
                conn.commit()
            
            # Close engine
            DBConnectionManager.close_engine(config_id)
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def test_connection(request: TestConnectionRequest) -> ConnectionTestResult:
        config_dict = {
            "db_type": request.db_type,
            "host": request.host,
            "port": request.port,
            "database_name": request.database_name,
            "username": request.username,
            "password": request.password,
            "ssl_mode": request.ssl_mode,
            "ssl_cert_path": request.ssl_cert_path
        }
        
        start_time = datetime.now()
        try:
            DBConnectionManager.test_connection(config_dict)
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            return ConnectionTestResult(
                success=True,
                message="Connection successful",
                elapsed_ms=elapsed
            )
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            return ConnectionTestResult(
                success=False,
                message=str(e),
                elapsed_ms=elapsed
            )

    @staticmethod
    def test_connection_by_id(config_id: str, user_id: str) -> ConnectionTestResult:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            return ConnectionTestResult(success=False, message="Configuration not found")
        
        # Decrypt password
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            return ConnectionTestResult(success=False, message="Failed to decrypt password")
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": config_row['database_name'],
            "username": config_row['username'],
            "password": password,
            "ssl_mode": config_row['ssl_mode'],
            "ssl_cert_path": config_row['ssl_cert_path'],
            "charset": config_row['charset']
        }
        
        start_time = datetime.now()
        try:
            DBConnectionManager.test_connection(config_dict)
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update last_connected_at
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE db_configs SET last_connected_at = %s WHERE id = %s",
                        (datetime.now(), config_id)
                    )
                    conn.commit()
            except:
                pass # Ignore update failure
            finally:
                conn.close()
                
            return ConnectionTestResult(
                success=True,
                message="Connection successful",
                elapsed_ms=elapsed
            )
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            return ConnectionTestResult(
                success=False,
                message=str(e),
                elapsed_ms=elapsed
            )

    # --------------------------------------------------------------------------
    # SQL Execution
    # --------------------------------------------------------------------------

    @staticmethod
    def _apply_pagination(sql: str, page: int, page_size: int, db_type: str) -> str:
        # Simple check if pagination already exists
        sql_upper = sql.upper()
        if "LIMIT" in sql_upper or "OFFSET" in sql_upper or "FETCH NEXT" in sql_upper:
            return sql
            
        offset = (page - 1) * page_size
        
        # Check if sql ends with semicolon
        sql = sql.strip()
        if sql.endswith(';'):
            sql = sql[:-1]
            
        if db_type in [DatabaseType.MYSQL, DatabaseType.POSTGRESQL, DatabaseType.SQLITE, DatabaseType.MARIADB]:
            return f"{sql} LIMIT {page_size} OFFSET {offset}"
        elif db_type == DatabaseType.SQLSERVER:
            if "ORDER BY" in sql_upper:
                return f"{sql} OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
        elif db_type == DatabaseType.ORACLE:
             if "ORDER BY" in sql_upper:
                 return f"{sql} OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
                 
        return sql

    @staticmethod
    def execute_sql(user_id: str, request: SQLExecutionRequest) -> SQLExecutionResult:
        config_row = DatabaseToolService._get_config_with_password(request.db_config_id, user_id)
        if not config_row:
            return SQLExecutionResult(
                success=False, 
                execution_time_ms=0, 
                error_message="Configuration not found or access denied"
            )
        
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            return SQLExecutionResult(
                success=False, 
                execution_time_ms=0, 
                error_message="Failed to decrypt password"
            )
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": request.database_name if request.database_name else config_row['database_name'],
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset'],
            "max_pool_size": config_row['max_pool_size']
        }
        
        final_sql = request.sql
        # Only apply auto-pagination if it's a single SELECT statement
        import sqlparse
        statements = sqlparse.split(request.sql)
        statements = [s for s in statements if s.strip()]
        
        if len(statements) == 1:
            if request.page and request.page_size and request.page > 0 and request.page_size > 0:
                if statements[0].strip().upper().startswith("SELECT"):
                     final_sql = DatabaseToolService._apply_pagination(
                         statements[0], 
                         request.page, 
                         request.page_size, 
                         config_row['db_type']
                     )

        result = SQLExecutor.execute(request.db_config_id, config_dict, final_sql, request.params)
        
        # Save history
        DatabaseToolService._save_history(user_id, request, result)
        
        return result

    @staticmethod
    def _save_history(user_id: str, request: SQLExecutionRequest, result: SQLExecutionResult):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                history_id = str(uuid.uuid4())
                cursor.execute(
                    """
                    INSERT INTO sql_execution_history (
                        id, user_id, db_config_id, sql_statement, sql_type, 
                        execution_status, affected_rows, execution_time_ms, 
                        error_message, result_data, result_size, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, 
                        %s, %s, %s, 
                        %s, %s, %s, %s
                    )
                    """,
                    (
                        history_id, user_id, request.db_config_id, request.sql, result.sql_type,
                        "success" if result.success else "failed",
                        result.affected_rows, int(result.execution_time_ms),
                        result.error_message,
                        json.dumps(result.result_data) if result.result_data else None,
                        len(json.dumps(result.result_data)) if result.result_data else 0,
                        datetime.now()
                    )
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save execution history: {e}")
        finally:
            conn.close()

    @staticmethod
    def get_history(user_id: str, limit: int = 50, offset: int = 0) -> List[ExecutionHistory]:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT h.*, c.alias as db_alias 
                    FROM sql_execution_history h
                    LEFT JOIN db_configs c ON h.db_config_id = c.id
                    WHERE h.user_id = %s 
                    ORDER BY h.created_at DESC 
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, limit, offset)
                )
                rows = cursor.fetchall()
                
                history = []
                for row in rows:
                    history.append(ExecutionHistory(
                        id=row['id'],
                        user_id=row['user_id'],
                        db_config_id=row['db_config_id'],
                        sql_statement=row['sql_statement'],
                        sql_type=row['sql_type'],
                        execution_status=row['execution_status'],
                        affected_rows=row['affected_rows'],
                        execution_time_ms=row['execution_time_ms'],
                        error_message=row['error_message'],
                        created_at=row['created_at'],
                        db_alias=row['db_alias']
                    ))
                return history
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # Schema Browsing
    # --------------------------------------------------------------------------
    
    @staticmethod
    def get_databases_list(user_id: str, config_id: str) -> List[str]:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
        
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": config_row['database_name'],
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        engine = DBConnectionManager.get_engine(config_id, config_dict)
        
        db_type = config_row['db_type']
        databases = []
        
        try:
            with engine.connect() as conn:
                if db_type == DatabaseType.MYSQL or db_type == DatabaseType.MARIADB:
                    result = conn.execute(text("SHOW DATABASES"))
                    databases = [row[0] for row in result]
                elif db_type == DatabaseType.POSTGRESQL:
                    result = conn.execute(text("SELECT datname FROM pg_database WHERE datistemplate = false"))
                    databases = [row[0] for row in result]
                elif db_type == DatabaseType.SQLSERVER:
                    result = conn.execute(text("SELECT name FROM sys.databases"))
                    databases = [row[0] for row in result]
                elif db_type == DatabaseType.SQLITE:
                    databases = ["main"]
        except Exception as e:
            logger.error(f"Failed to list databases: {e}")
            # If we can't list databases, maybe we are restricted or connection failed
            # return empty list or re-raise
            raise e
                
        return sorted(databases)

    @staticmethod
    def get_database_structure(user_id: str, config_id: str, database_name: str) -> Dict[str, List[Dict[str, Any]]]:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
            
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": database_name,
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        # Use a temporary config_id to avoid caching/conflict with main connection
        temp_config_id = f"{config_id}:{database_name}"
        
        try:
            engine = DBConnectionManager.get_engine(temp_config_id, config_dict)
            inspector = inspect(engine)
            db_type = config_row['db_type']
            
            tables_data = []
            views_data = []

            # Optimized fetching for MySQL/MariaDB
            if db_type == DatabaseType.MYSQL or db_type == DatabaseType.MARIADB:
                with engine.connect() as conn:
                    # Fetch Tables
                    sql_tables = text("""
                        SELECT TABLE_NAME, TABLE_COMMENT 
                        FROM information_schema.TABLES 
                        WHERE TABLE_SCHEMA = :schema AND TABLE_TYPE = 'BASE TABLE'
                    """)
                    result_tables = conn.execute(sql_tables, {"schema": database_name})
                    for row in result_tables:
                        tables_data.append({"name": row[0], "comment": row[1]})
                    
                    # Fetch Views
                    sql_views = text("""
                        SELECT TABLE_NAME 
                        FROM information_schema.VIEWS 
                        WHERE TABLE_SCHEMA = :schema
                    """)
                    result_views = conn.execute(sql_views, {"schema": database_name})
                    for row in result_views:
                        views_data.append({"name": row[0], "comment": None})
            else:
                # Fallback for other DBs (N+1 for comments or just names)
                # For now, just names to avoid performance hit, unless we implement specific queries
                for name in inspector.get_table_names():
                    try:
                        comment = inspector.get_table_comment(name).get('text')
                    except:
                        comment = None
                    tables_data.append({"name": name, "comment": comment})
                
                for name in inspector.get_view_names():
                    views_data.append({"name": name, "comment": None})
            
            # Sort by name
            tables_data.sort(key=lambda x: x['name'])
            views_data.sort(key=lambda x: x['name'])
            
            return {
                "tables": tables_data,
                "views": views_data,
            }
        except Exception as e:
            logger.error(f"Failed to get database structure: {e}")
            raise e

    @staticmethod
    def get_tables(user_id: str, config_id: str) -> List[str]:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
            
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": config_row['database_name'],
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        engine = DBConnectionManager.get_engine(config_id, config_dict)
        inspector = inspect(engine)
        return inspector.get_table_names()

    @staticmethod
    def get_table_schema(user_id: str, config_id: str, table_name: str, database_name: Optional[str] = None) -> TableSchema:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
            
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        target_db = database_name if database_name else config_row['database_name']

        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": target_db,
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        # Use a unique key if database_name is provided to avoid using cached engine of default DB
        engine_key = f"{config_id}:{target_db}" if database_name else config_id
        
        # DBConnectionManager now handles key generation based on database_name
        engine = DBConnectionManager.get_engine(engine_key, config_dict)
        inspector = inspect(engine)
        
        # Get table comment
        table_comment = None
        try:
            table_comment = inspector.get_table_comment(table_name).get('text')
        except:
            pass

        columns = []
        for col in inspector.get_columns(table_name):
            # Convert SQLAlchemy type to string
            col['type'] = str(col['type'])
            # Ensure comment is present
            if 'comment' not in col:
                col['comment'] = None
            columns.append(col)
            
        pk_constraint = inspector.get_pk_constraint(table_name)
        primary_key = pk_constraint.get('constrained_columns', [])
        
        indexes = inspector.get_indexes(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        
        return TableSchema(
            table_name=table_name,
            comment=table_comment,
            columns=columns,
            primary_key=primary_key,
            indexes=indexes,
            foreign_keys=foreign_keys
        )

    @staticmethod
    def query_table_data(
        user_id: str, 
        config_id: str, 
        table_name: str, 
        database_name: Optional[str] = None,
        where_clause: Optional[str] = None,
        order_by_clause: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> SQLExecutionResult:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            return SQLExecutionResult(success=False, execution_time_ms=0, error_message="Configuration not found")
            
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            return SQLExecutionResult(success=False, execution_time_ms=0, error_message="Failed to decrypt password")

        # If database_name is provided (e.g. for multi-db connections), use it
        # Otherwise use the default from config
        target_db = database_name if database_name else config_row['database_name']
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": target_db,
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset'],
            "max_pool_size": config_row['max_pool_size']
        }
        
        # We need a unique engine key if we are switching databases dynamically
        engine_key = f"{config_id}:{target_db}" if database_name else config_id
        
        # Construct SQL
        # Note: This is a direct SQL construction. 
        # Since this is a DB tool for developers, we allow raw WHERE/ORDER BY clauses.
        # But we should be careful about injection if this was a public app.
        
        # Basic validation to prevent simple injection of "; DROP TABLE" style attacks if possible,
        # though user has SQL execution rights anyway via the main tool.
        
        sql = f"SELECT * FROM {table_name}"
        count_sql = f"SELECT COUNT(*) FROM {table_name}"
        
        if where_clause and where_clause.strip():
            sql += f" WHERE {where_clause}"
            count_sql += f" WHERE {where_clause}"
            
        if order_by_clause and order_by_clause.strip():
            sql += f" ORDER BY {order_by_clause}"
            
        # Pagination
        offset = (page - 1) * page_size
        
        # Use SQLExecutor logic but adapted for pagination
        # Or just construct the limit/offset string based on DB type
        # SQLAlchemy handles this if we use select().limit().offset(), but we are using raw strings for where clause.
        # Most DBs support LIMIT/OFFSET or similar.
        
        db_type = config_row['db_type']
        
        if db_type == DatabaseType.SQLSERVER:
            # SQL Server 2012+ supports OFFSET/FETCH
            # It requires ORDER BY to use OFFSET/FETCH
            if not order_by_clause or not order_by_clause.strip():
                # Need default order by for pagination
                sql += " ORDER BY (SELECT NULL)" 
            sql += f" OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
        elif db_type == DatabaseType.ORACLE:
            # Oracle 12c+
            sql += f" OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
        else:
            # MySQL, PostgreSQL, SQLite
            sql += f" LIMIT {page_size} OFFSET {offset}"

        return SQLExecutor.execute(engine_key, config_dict, sql)

    # --------------------------------------------------------------------------
    # Database Administration (DDL)
    # --------------------------------------------------------------------------

    @staticmethod
    def create_database_instance(user_id: str, config_id: str, database_name: str, charset: str = 'utf8mb4') -> bool:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
        
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        # Connect to the default database of the connection to execute CREATE DATABASE
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": config_row['database_name'], # Connect to default DB
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        db_type = config_row['db_type']
        sql = ""
        
        # Simple sanitization for database name (alphanumeric + underscore)
        # In a real tool, we should use proper quoting/escaping
        if not database_name.replace('_', '').isalnum():
             # Fallback or strict check. For now, let's assume valid input or basic quoting.
             # But better to quote it.
             pass

        # Quoting helper
        def quote_ident(name):
            return f'"{name}"' if db_type == DatabaseType.POSTGRESQL else f'`{name}`'

        quoted_name = quote_ident(database_name)

        if db_type == DatabaseType.MYSQL or db_type == DatabaseType.MARIADB:
            sql = f"CREATE DATABASE {quoted_name} CHARACTER SET {charset}"
        elif db_type == DatabaseType.POSTGRESQL:
            sql = f"CREATE DATABASE {quoted_name}"
            # Postgres cannot execute CREATE DATABASE inside a transaction block
            # We need to handle this. SQLAlchemy's execute usually auto-commits or we need execution_options(isolation_level="AUTOCOMMIT")
        elif db_type == DatabaseType.SQLSERVER:
            sql = f"CREATE DATABASE {quoted_name}"
        elif db_type == DatabaseType.SQLITE:
            # SQLite doesn't really "CREATE DATABASE" in the same way (it's a file)
            # We could ATTACH, but usually we just create a file. 
            # For now, skip or return False
            return False
            
        engine = DBConnectionManager.get_engine(config_id, config_dict)
        
        try:
            # For DDL that can't run in transaction (Postgres CREATE DB), we need autocommit
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text(sql))
            return True
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise e

    @staticmethod
    def drop_database_instance(user_id: str, config_id: str, database_name: str) -> bool:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
            
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": config_row['database_name'], # Connect to default DB
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        db_type = config_row['db_type']
        
        def quote_ident(name):
            return f'"{name}"' if db_type == DatabaseType.POSTGRESQL else f'`{name}`'

        quoted_name = quote_ident(database_name)
        sql = f"DROP DATABASE {quoted_name}"
        
        engine = DBConnectionManager.get_engine(config_id, config_dict)
        
        try:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text(sql))
            return True
        except Exception as e:
            logger.error(f"Failed to drop database: {e}")
            raise e

    @staticmethod
    def drop_table_instance(user_id: str, config_id: str, database_name: str, table_name: str) -> bool:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
            
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": database_name, # Connect to specific DB
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        db_type = config_row['db_type']
        
        def quote_ident(name):
            return f'"{name}"' if db_type == DatabaseType.POSTGRESQL else f'`{name}`'

        quoted_table = quote_ident(table_name)
        sql = f"DROP TABLE {quoted_table}"
        
        # Unique key for engine because we might switch databases
        engine_key = f"{config_id}:{database_name}"
        engine = DBConnectionManager.get_engine(engine_key, config_dict)
        
        try:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text(sql))
            return True
        except Exception as e:
            logger.error(f"Failed to drop table: {e}")
            raise e

    @staticmethod
    def truncate_table_instance(user_id: str, config_id: str, database_name: str, table_name: str) -> bool:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
            
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": database_name,
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        db_type = config_row['db_type']
        
        def quote_ident(name):
            return f'"{name}"' if db_type == DatabaseType.POSTGRESQL else f'`{name}`'

        quoted_table = quote_ident(table_name)
        
        if db_type == DatabaseType.SQLITE:
            sql = f"DELETE FROM {quoted_table}"
        else:
            sql = f"TRUNCATE TABLE {quoted_table}"
        
        engine_key = f"{config_id}:{database_name}"
        engine = DBConnectionManager.get_engine(engine_key, config_dict)
        
        try:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text(sql))
            return True
        except Exception as e:
            logger.error(f"Failed to truncate table: {e}")
            raise e

    # --------------------------------------------------------------------------
    # Search
    # --------------------------------------------------------------------------

    @staticmethod
    def search_tables(user_id: str, config_id: str, keyword: str) -> List[Dict[str, str]]:
        """
        Search for tables and views matching the keyword across all databases (if supported).
        Returns a list of { "database": "db_name", "table": "table_name", "type": "table|view" }
        """
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
            
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            raise ValueError("Failed to decrypt password")
            
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": config_row['database_name'],
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset']
        }
        
        db_type = config_row['db_type']
        results = []
        
        try:
            # MySQL/MariaDB: Use information_schema for global search
            if db_type == DatabaseType.MYSQL or db_type == DatabaseType.MARIADB:
                engine = DBConnectionManager.get_engine(config_id, config_dict)
                with engine.connect() as conn:
                    # Search tables and views
                    sql = text("""
                        SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE 
                        FROM information_schema.TABLES 
                        WHERE TABLE_NAME LIKE :keyword
                        AND TABLE_SCHEMA NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
                        ORDER BY TABLE_SCHEMA, TABLE_NAME
                        LIMIT 100
                    """)
                    rows = conn.execute(sql, {"keyword": f"%{keyword}%"}).fetchall()
                    for row in rows:
                        results.append({
                            "database": row[0],
                            "table": row[1],
                            "type": "view" if "VIEW" in str(row[2]).upper() else "table"
                        })
                        
            # PostgreSQL: Search in current DB only (due to isolation)
            # Or we could try to iterate over all DBs, but that's expensive.
            # For now, search in the connected database.
            elif db_type == DatabaseType.POSTGRESQL:
                engine = DBConnectionManager.get_engine(config_id, config_dict)
                with engine.connect() as conn:
                    sql = text("""
                        SELECT table_schema, table_name, table_type
                        FROM information_schema.tables
                        WHERE table_name ILIKE :keyword
                        AND table_schema NOT IN ('information_schema', 'pg_catalog')
                        LIMIT 100
                    """)
                    rows = conn.execute(sql, {"keyword": f"%{keyword}%"}).fetchall()
                    current_db = config_row['database_name']
                    for row in rows:
                        results.append({
                            "database": current_db, # Postgres tables are in schema, but we list DBs. 
                                                    # Actually, get_databases_list lists DBs.
                                                    # This search is limited to current DB.
                            "table": row[1],
                            "type": "view" if "VIEW" in str(row[2]).upper() else "table"
                        })
                        
            # SQL Server: Search in current DB
            elif db_type == DatabaseType.SQLSERVER:
                engine = DBConnectionManager.get_engine(config_id, config_dict)
                with engine.connect() as conn:
                    sql = text("""
                        SELECT TABLE_CATALOG, TABLE_NAME, TABLE_TYPE
                        FROM information_schema.TABLES
                        WHERE TABLE_NAME LIKE :keyword
                        LIMIT 100
                    """)
                    rows = conn.execute(sql, {"keyword": f"%{keyword}%"}).fetchall()
                    for row in rows:
                        results.append({
                            "database": row[0],
                            "table": row[1],
                            "type": "view" if "VIEW" in str(row[2]).upper() else "table"
                        })
                        
            # SQLite
            elif db_type == DatabaseType.SQLITE:
                engine = DBConnectionManager.get_engine(config_id, config_dict)
                with engine.connect() as conn:
                    sql = text("""
                        SELECT name, type FROM sqlite_master 
                        WHERE name LIKE :keyword AND type IN ('table', 'view')
                        LIMIT 100
                    """)
                    rows = conn.execute(sql, {"keyword": f"%{keyword}%"}).fetchall()
                    for row in rows:
                        results.append({
                            "database": "main",
                            "table": row[0],
                            "type": row[1]
                        })
                        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Don't fail the whole request, just return empty or what we found
            
        return results
