from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.utils.db_connection_manager import DBConnectionManager
from app.models.database_tool_models import SQLExecutionResult
import time
import logging
import datetime

logger = logging.getLogger(__name__)

class SQLExecutor:
    
    @staticmethod
    def execute(config_id: str, config: Dict[str, Any], sql: str, params: Optional[Dict[str, Any]] = None) -> SQLExecutionResult:
        start_time = time.time()
        engine = DBConnectionManager.get_engine(config_id, config)
        
        try:
            with engine.connect() as conn:
                # Determine if it's a SELECT statement (simplistic check)
                is_select = sql.strip().upper().startswith("SELECT")
                
                # Create text clause
                stmt = text(sql)
                
                # Execute
                if params:
                    result = conn.execute(stmt, params)
                else:
                    result = conn.execute(stmt)
                
                # Commit if not select (SQLAlchemy 2.0+ auto-begins transaction)
                if not is_select:
                    conn.commit()
                
                execution_time = (time.time() - start_time) * 1000
                
                if is_select:
                    # Fetch results
                    if result.returns_rows:
                        # Convert to list of dicts
                        # result.keys() returns column names
                        columns = list(result.keys())
                        rows = [dict(row._mapping) for row in result.fetchall()]
                        
                        # Handle serialization of special types (datetime, etc.)
                        serialized_rows = []
                        for row in rows:
                            new_row = {}
                            for k, v in row.items():
                                if isinstance(v, (datetime.datetime, datetime.date)):
                                    new_row[k] = v.isoformat()
                                else:
                                    new_row[k] = v
                            serialized_rows.append(new_row)
                            
                        return SQLExecutionResult(
                            success=True,
                            sql_type="SELECT",
                            affected_rows=len(serialized_rows),
                            execution_time_ms=execution_time,
                            result_data=serialized_rows,
                            columns=columns
                        )
                    else:
                        # Should not happen for SELECT usually
                        return SQLExecutionResult(
                            success=True,
                            sql_type="SELECT",
                            affected_rows=0,
                            execution_time_ms=execution_time,
                            result_data=[],
                            columns=[]
                        )
                else:
                    # DML/DDL
                    affected = result.rowcount
                    return SQLExecutionResult(
                        success=True,
                        sql_type="DML/DDL",
                        affected_rows=affected,
                        execution_time_ms=execution_time
                    )
                    
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            execution_time = (time.time() - start_time) * 1000
            return SQLExecutionResult(
                success=False,
                execution_time_ms=execution_time,
                error_message=str(e)
            )
