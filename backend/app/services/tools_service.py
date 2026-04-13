"""
Tools Service - Handles tool management and persistence using PostgreSQL
"""

import logging
import uuid
from typing import List, Optional, Dict
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from app.config.database import get_db_connection
from app.data.tools_data import TOOLS_DATA
from app.models import Tool, Category, ToolCreateRequest, CategoryCreateRequest

logger = logging.getLogger(__name__)


class ToolsService:
    """Service for managing tools in database"""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # Create tool_categories table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tool_categories (
                        id VARCHAR(64) PRIMARY KEY,
                        name VARCHAR(50) NOT NULL UNIQUE,
                        description VARCHAR(255),
                        icon VARCHAR(50),
                        sort_order INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        deleted BOOLEAN DEFAULT FALSE
                    )
                """)

                # Create tools table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tools (
                        id VARCHAR(50) PRIMARY KEY,
                        title VARCHAR(100) NOT NULL,
                        description TEXT,
                        icon VARCHAR(50),
                        icon_color VARCHAR(50),
                        category VARCHAR(50),
                        status VARCHAR(20) DEFAULT 'online',
                        usage_count INTEGER DEFAULT 0,
                        rating FLOAT DEFAULT 5.0,
                        sort_order INT DEFAULT 0,
                        custom_icon_url VARCHAR(500) DEFAULT NULL,
                        show_pc BOOLEAN DEFAULT TRUE,
                        show_mobile BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 迁移：为已有 tools 表新增字段
                cur.execute("""
                    ALTER TABLE tools
                    ADD COLUMN IF NOT EXISTS custom_icon_url VARCHAR(500) DEFAULT NULL
                """)
                cur.execute("""
                    ALTER TABLE tools
                    ADD COLUMN IF NOT EXISTS show_pc BOOLEAN DEFAULT TRUE
                """)
                cur.execute("""
                    ALTER TABLE tools
                    ADD COLUMN IF NOT EXISTS show_mobile BOOLEAN DEFAULT TRUE
                """)

                # Create tool_visits table for detailed tracking
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tool_visits (
                        id SERIAL PRIMARY KEY,
                        tool_id VARCHAR(50) REFERENCES tools(id),
                        visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_id VARCHAR(50)
                    )
                """)

                # Seed categories
                default_categories = [
                    "文本工具",
                    "转换工具",
                    "计算工具",
                    "设计工具",
                    "实用工具",
                    "开发工具",
                    "AI工具",
                ]
                # Ensure all categories from TOOLS_DATA are included
                for tool in TOOLS_DATA:
                    if tool.category and tool.category not in default_categories:
                        default_categories.append(tool.category)

                for idx, cat_name in enumerate(default_categories):
                    cur.execute(
                        """
                        INSERT INTO tool_categories (id, name, sort_order)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (name) DO NOTHING
                    """,
                        (str(uuid.uuid4()), cat_name, idx),
                    )

                # Seed or update tools database from TOOLS_DATA
                logger.info("Syncing tools database with static data...")
                for tool in TOOLS_DATA:
                    # usage_count is initialized to 0 for new tools, but preserved for existing ones via ON CONFLICT
                    # rating is updated from static data
                    cur.execute(
                        """
                        INSERT INTO tools (id, title, description, icon, icon_color, category, usage_count, rating, custom_icon_url, show_pc, show_mobile)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, TRUE, TRUE)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            description = EXCLUDED.description,
                            icon = EXCLUDED.icon,
                            icon_color = EXCLUDED.icon_color,
                            category = EXCLUDED.category,
                            rating = EXCLUDED.rating
                    """,
                        (
                            tool.id,
                            tool.title,
                            tool.description,
                            tool.icon,
                            tool.iconColor,
                            tool.category,
                            0,
                            tool.rating,
                        ),
                    )

            conn.commit()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def get_all_tools(self, include_offline: bool = False) -> List[Tool]:
        """Get all tools from database"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                if include_offline:
                    cur.execute("SELECT * FROM tools ORDER BY category, title")
                else:
                    cur.execute(
                        "SELECT * FROM tools WHERE status = 'online' ORDER BY category, title"
                    )

                rows = cur.fetchall()

                tools = []
                for row in rows:
                    # Map DB row back to Tool Pydantic model
                    # Note: Tool model uses camelCase for frontend, DB uses snake_case
                    # We need to ensure Tool model compatibility.
                    # Let's check Tool model definition in app/models/__init__.py or app/data/tools_data.py
                    # Assuming standard Tool model:
                    tools.append(
                        Tool(
                            id=row["id"],
                            title=row["title"],
                            description=row["description"],
                            icon=row["icon"],
                            iconColor=row["icon_color"],
                            category=row["category"],
                            usageCount=str(
                                row["usage_count"]
                            ),  # Convert back to string for frontend compatibility if needed
                            rating=row["rating"],
                            status=row[
                                "status"
                            ],  # Add status field to Tool model if not exists
                        )
                    )
                return tools
        except Exception as e:
            logger.error(f"Error fetching tools: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get tools by category"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                if category == "全部工具":
                    cur.execute(
                        "SELECT * FROM tools WHERE status = 'online' ORDER BY title"
                    )
                else:
                    cur.execute(
                        "SELECT * FROM tools WHERE status = 'online' AND category = %s ORDER BY title",
                        (category,),
                    )

                rows = cur.fetchall()
                return [self._row_to_tool(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching tools by category: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def search_tools(self, query: str) -> List[Tool]:
        """Search tools"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                search_term = f"%{query}%"
                cur.execute(
                    """
                    SELECT * FROM tools 
                    WHERE status = 'online' 
                    AND (LOWER(title) LIKE LOWER(%s) OR LOWER(description) LIKE LOWER(%s))
                """,
                    (search_term, search_term),
                )

                rows = cur.fetchall()
                return [self._row_to_tool(row) for row in rows]
        except Exception as e:
            logger.error(f"Error searching tools: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def update_tool_status(self, tool_id: str, status: str) -> bool:
        """Update tool status (online/offline)"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tools SET status = %s WHERE id = %s", (status, tool_id)
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating tool status: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def record_visit(self, tool_id: str, user_id: Optional[str] = None) -> bool:
        """Record tool visit"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # 1. 先检查工具是否存在（避免外键约束错误）
                cur.execute("SELECT id FROM tools WHERE id = %s", (tool_id,))
                if not cur.fetchone():
                    logger.warning(f"Tool not found, cannot record visit: {tool_id}")
                    return False

                # 2. Insert into log
                cur.execute(
                    "INSERT INTO tool_visits (tool_id, user_id) VALUES (%s, %s)",
                    (tool_id, user_id),
                )
                # 3. Update count
                cur.execute(
                    "UPDATE tools SET usage_count = usage_count + 1 WHERE id = %s",
                    (tool_id,),
                )
                conn.commit()
                logger.info(f"Recorded visit for tool: {tool_id}")
                return True
        except Exception as e:
            logger.error(f"Error recording visit for tool {tool_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def get_all_categories(self) -> List[Category]:
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM tool_categories WHERE deleted = FALSE ORDER BY sort_order"
                )
                rows = cur.fetchall()
                return [Category(**row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def create_category(self, request: CategoryCreateRequest) -> Optional[Category]:
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cat_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO tool_categories (id, name, description, icon, sort_order)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                """,
                    (
                        cat_id,
                        request.name,
                        request.description,
                        request.icon,
                        request.sort_order,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                if row:
                    return Category(**row)
                return None
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def update_category(
        self, cat_id: str, request: CategoryCreateRequest
    ) -> Optional[Category]:
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE tool_categories 
                    SET name = %s, description = %s, icon = %s, sort_order = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND deleted = FALSE
                    RETURNING *
                """,
                    (
                        request.name,
                        request.description,
                        request.icon,
                        request.sort_order,
                        cat_id,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                if row:
                    return Category(**row)
                return None
        except Exception as e:
            logger.error(f"Error updating category: {e}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def delete_category(self, cat_id: str) -> bool:
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # Logical delete
                cur.execute(
                    "UPDATE tool_categories SET deleted = TRUE WHERE id = %s", (cat_id,)
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def get_tool_stats(self) -> Dict:
        """Get tool statistics for dashboard"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # Total tools
                cur.execute("SELECT COUNT(*) FROM tools")
                total_tools = cur.fetchone()["count"]

                # Total visits
                cur.execute("SELECT COUNT(*) FROM tool_visits")
                total_visits = cur.fetchone()["count"]

                # Popular tools
                cur.execute("""
                    SELECT t.id, t.title, t.usage_count, MAX(tv.visit_time) as last_visited
                    FROM tools t
                    LEFT JOIN tool_visits tv ON t.id = tv.tool_id
                    GROUP BY t.id, t.title, t.usage_count
                    ORDER BY t.usage_count DESC
                    LIMIT 10
                """)
                popular_rows = cur.fetchall()

                popular_tools = []
                for row in popular_rows:
                    popular_tools.append(
                        {
                            "tool_id": row["id"],
                            "tool_name": row["title"],
                            "visit_count": row["usage_count"],
                            "last_visited": row["last_visited"]
                            if row["last_visited"]
                            else datetime.utcnow(),
                        }
                    )

                return {
                    "total_tools": total_tools,
                    "total_visits": total_visits,
                    "popular_tools": popular_tools,
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"total_tools": 0, "total_visits": 0, "popular_tools": []}
        finally:
            if conn:
                conn.close()

    def _row_to_tool(self, row) -> Tool:
        """Helper to convert DB row to Tool object"""
        # We need to make sure we don't pass 'status' if Tool model doesn't support it yet
        # But we should update Tool model to support it.
        # For now, let's assume we update Tool model or use dynamic dict unpacking if strict validation is off.
        # Ideally, update Pydantic model first.
        return Tool(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            icon=row["icon"],
            iconColor=row["icon_color"],
            category=row["category"],
            usageCount=str(row["usage_count"]),
            rating=row["rating"],
            status=row.get("status", "online"),
            custom_icon_url=row.get("custom_icon_url"),
            show_pc=row.get("show_pc", True),
            show_mobile=row.get("show_mobile", True),
        )


# Singleton instance
tools_service = ToolsService()
