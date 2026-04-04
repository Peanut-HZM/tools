"""
HTTP Client 数据库表初始化
"""

import logging
import uuid
from app.config.database import get_db_connection

logger = logging.getLogger(__name__)


def init_http_client_tables():
    """初始化 HTTP Client 相关的数据库表"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. 创建请求集合表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS http_request_collections (
                    id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    workspace_id VARCHAR(64) DEFAULT 'default',
                    parent_id VARCHAR(64),
                    sort_order INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Created table: http_request_collections")

            # 2. 创建 HTTP 请求表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS http_requests (
                    id VARCHAR(64) PRIMARY KEY,
                    collection_id VARCHAR(64) REFERENCES http_request_collections(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    method VARCHAR(10) NOT NULL DEFAULT 'GET',
                    url TEXT NOT NULL,
                    headers JSONB DEFAULT '{}',
                    params JSONB DEFAULT '{}',
                    body_type VARCHAR(20) DEFAULT 'none',
                    body TEXT,
                    auth_type VARCHAR(20) DEFAULT 'none',
                    auth_config JSONB DEFAULT '{}',
                    sort_order INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Created table: http_requests")

            # 3. 创建环境变量表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS http_environments (
                    id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    workspace_id VARCHAR(64) DEFAULT 'default',
                    variables JSONB DEFAULT '{}',
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Created table: http_environments")

            # 4. 创建请求历史表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS http_request_history (
                    id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    request_id VARCHAR(64) REFERENCES http_requests(id) ON DELETE SET NULL,
                    method VARCHAR(10) NOT NULL,
                    url TEXT NOT NULL,
                    status_code INT NOT NULL,
                    response_time INT NOT NULL,
                    request_data JSONB DEFAULT '{}',
                    response_data JSONB DEFAULT '{}',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Created table: http_request_history")

            # 5. 创建云端同步记录表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS http_sync_records (
                    id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    entity_type VARCHAR(20) NOT NULL,
                    entity_id VARCHAR(64) NOT NULL,
                    action VARCHAR(10) NOT NULL,
                    local_data JSONB DEFAULT '{}',
                    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Created table: http_sync_records")

            # 创建索引
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_http_requests_collection
                ON http_requests(collection_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_http_request_history_user
                ON http_request_history(user_id, timestamp DESC)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_http_environments_workspace
                ON http_environments(workspace_id, is_active)
            """)
            logger.info("Created indexes")

            # 插入默认环境数据
            cur.execute("""
                INSERT INTO http_environments (id, name, workspace_id, variables, is_active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(uuid.uuid4()), '默认环境', 'default', '{}', True))

            cur.execute("""
                INSERT INTO http_environments (id, name, workspace_id, variables, is_active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(uuid.uuid4()), '开发环境', 'default',
                  '{"baseUrl": "http://localhost:8080", "timeout": "30000"}', False))

            cur.execute("""
                INSERT INTO http_environments (id, name, workspace_id, variables, is_active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(uuid.uuid4()), '生产环境', 'default',
                  '{"baseUrl": "https://api.example.com", "timeout": "60000"}', False))

            logger.info("Inserted default environments")

            conn.commit()
            logger.info("HTTP Client tables initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize HTTP Client tables: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    init_http_client_tables()
    print("HTTP Client database tables initialized successfully!")
