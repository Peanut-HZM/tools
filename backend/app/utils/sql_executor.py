from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.utils.db_connection_manager import DBConnectionManager
from app.models.database_tool_models import SQLExecutionResult
import time
import logging
import datetime
import sqlparse

logger = logging.getLogger(__name__)


class SQLExecutor:
    @staticmethod
    def execute(
        config_id: str,
        config: Dict[str, Any],
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> SQLExecutionResult:
        start_time = time.time()
        engine = DBConnectionManager.get_engine(config_id, config)

        try:
            with engine.connect() as conn:
                # Split SQL into statements
                statements = sqlparse.split(sql)
                # Filter empty statements
                statements = [s for s in statements if s.strip()]

                if not statements:
                    return SQLExecutionResult(
                        success=True, execution_time_ms=0, affected_rows=0
                    )

                last_result = None
                total_affected = 0

                # Execute all statements
                for i, stmt_str in enumerate(statements):
                    # Skip empty statements that might remain
                    if not stmt_str.strip():
                        continue

                    stmt = text(stmt_str)

                    # Execute
                    if params:
                        result = conn.execute(stmt, params)
                    else:
                        result = conn.execute(stmt)

                    if not result.returns_rows:
                        total_affected += result.rowcount

                    last_result = result

                # Commit transaction
                conn.commit()

                execution_time = (time.time() - start_time) * 1000

                if last_result and last_result.returns_rows:
                    # Fetch results from the last query
                    columns = list(last_result.keys())
                    rows = [dict(row._mapping) for row in last_result.fetchall()]

                    # Handle serialization
                    serialized_rows = []
                    for row in rows:
                        new_row = {}
                        for k, v in row.items():
                            if isinstance(v, (datetime.datetime, datetime.date)):
                                new_row[k] = v.isoformat()
                            elif isinstance(v, int) and abs(v) > 9007199254740991:
                                new_row[k] = str(v)
                            else:
                                new_row[k] = v
                        serialized_rows.append(new_row)

                    return SQLExecutionResult(
                        success=True,
                        sql_type="SELECT",
                        affected_rows=len(serialized_rows),
                        execution_time_ms=execution_time,
                        result_data=serialized_rows,
                        columns=columns,
                    )
                else:
                    # DML/DDL
                    return SQLExecutionResult(
                        success=True,
                        sql_type="DML/DDL",
                        affected_rows=total_affected,
                        execution_time_ms=execution_time,
                    )

        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            execution_time = (time.time() - start_time) * 1000
            return SQLExecutionResult(
                success=False, execution_time_ms=execution_time, error_message=str(e)
            )
