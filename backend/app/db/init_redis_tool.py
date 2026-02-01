import os
import sys
import logging

# Add the parent directory to sys.path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_redis_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql_file_path = os.path.join(os.path.dirname(__file__), 'init_redis_tool.sql')
        
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
            
        logger.info("Executing Redis database initialization script...")
        cursor.execute(sql_script)
        conn.commit()
        logger.info("Redis database initialization completed successfully.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to initialize Redis database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_redis_db()
