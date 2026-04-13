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

    def update_tool(self, tool_id: str, data: dict) -> Optional[Tool]:
        """完整更新工具信息（行编辑）"""
        conn = None
        try:
            # 校验分类是否存在（如果提供了新分类）
            if "category" in data and data["category"]:
                cat_conn = get_db_connection()
                try:
                    with cat_conn.cursor() as cur:
                        cur.execute("SELECT id FROM tool_categories WHERE name = %s AND deleted = FALSE", (data["category"],))
                        if not cur.fetchone():
                            raise ValueError(f"分类不存在: {data['category']}")
                finally:
                    cat_conn.close()

            # 构建动态 UPDATE 语句
            updates = []
            params = []
            for field in ["title", "description", "icon", "icon_color", "category", "status", "sort_order"]:
                if field in data:
                    updates.append(f"{field} = %s")
                    params.append(data[field])

            # Boolean 字段特殊处理
            if "show_pc" in data:
                updates.append("show_pc = %s")
                params.append(data["show_pc"])
            if "show_mobile" in data:
                updates.append("show_mobile = %s")
                params.append(data["show_mobile"])
            if "custom_icon_url" in data:
                updates.append("custom_icon_url = %s")
                params.append(data["custom_icon_url"])

            if not updates:
                return None

            params.append(tool_id)

            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE tools SET {', '.join(updates)} WHERE id = %s RETURNING *",
                    params
                )
                row = cur.fetchone()
                conn.commit()
                if row:
                    return self._row_to_tool(row)
                return None
        except Exception as e:
            logger.error(f"Error updating tool {tool_id}: {e}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def get_tools_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "title",
        sort_order: str = "asc",
        show_pc: Optional[bool] = None,
        show_mobile: Optional[bool] = None,
    ) -> dict:
        """分页查询工具，支持搜索、筛选、排序"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # 构建 WHERE 条件
                conditions = []
                params = []

                if search:
                    conditions.append("(LOWER(title) LIKE LOWER(%s) OR LOWER(description) LIKE LOWER(%s))")
                    params.extend([f"%{search}%", f"%{search}%"])

                if status:
                    conditions.append("status = %s")
                    params.append(status)

                if category:
                    conditions.append("category = %s")
                    params.append(category)

                if show_pc is not None:
                    conditions.append("show_pc = %s")
                    params.append(show_pc)

                if show_mobile is not None:
                    conditions.append("show_mobile = %s")
                    params.append(show_mobile)

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                # 排序字段白名单
                sort_column = {
                    "title": "title",
                    "rating": "rating",
                    "usage_count": "usage_count",
                    "created_at": "created_at",
                }.get(sort_by, "title")
                sort_dir = "ASC" if sort_order == "asc" else "DESC"

                # 总数
                cur.execute(f"SELECT COUNT(*) FROM tools WHERE {where_clause}", params)
                total = cur.fetchone()["count"]

                total_pages = (total + page_size - 1) // page_size if total > 0 else 0

                # 分页数据
                offset = (page - 1) * page_size
                cur.execute(
                    f"SELECT * FROM tools WHERE {where_clause} ORDER BY {sort_column} {sort_dir} LIMIT %s OFFSET %s",
                    params + [page_size, offset]
                )
                rows = cur.fetchall()
                tools = [self._row_to_tool(row) for row in rows]

                return {
                    "tools": tools,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                }
        except Exception as e:
            logger.error(f"Error paginating tools: {e}")
            return {"tools": [], "total": 0, "page": 1, "page_size": 20, "total_pages": 0}
        finally:
            if conn:
                conn.close()

    def upload_tool_icon(self, tool_id: str, content: bytes, filename: str) -> Optional[str]:
        """上传工具图标到 OSS，上传前先删除旧图标"""
        from app.services.oss_service import oss_service
        from io import BytesIO

        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT id, custom_icon_url FROM tools WHERE id = %s", (tool_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Tool {tool_id} not found")

                # 删除旧 OSS 图标（如果存在）
                old_url = row[1]
                if old_url:
                    old_object_name = old_url.split("/", 3)[-1] if "/" in old_url else None
                    if old_object_name:
                        oss_service.delete_file(old_object_name)
                        logger.info(f"Deleted old icon for {tool_id}: {old_object_name}")
            conn.close()
            conn = None

            # 确定文件扩展名
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
            if ext not in ("png", "jpg", "jpeg", "gif", "svg", "webp"):
                raise ValueError(f"不支持的文件类型: {ext}")

            object_name = f"tools/icons/{tool_id}.{ext}"

            # 上传到 OSS
            url = oss_service.upload_file(
                object_name=object_name,
                data=BytesIO(content),
                size=len(content),
                content_type=f"image/{ext}",
                uploaded_by="admin"
            )

            if not url:
                raise ValueError("OSS 上传失败")

            # 更新数据库
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tools SET custom_icon_url = %s WHERE id = %s",
                    (url, tool_id)
                )
                conn.commit()

            return url
        except Exception as e:
            logger.error(f"Error uploading tool icon for {tool_id}: {e}")
            raise e
        finally:
            if conn:
                conn.close()

    def delete_tool_icon(self, tool_id: str) -> bool:
        """删除工具自定义图标"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tools SET custom_icon_url = NULL WHERE id = %s",
                    (tool_id,)
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting tool icon for {tool_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def get_tools_for_platform(self, platform: str, category: Optional[str] = None) -> List[Tool]:
        """按平台获取在线工具，支持分类过滤（参数化查询防止 SQL 注入）"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                base_sql = "SELECT * FROM tools WHERE status = 'online'"
                params: list = []

                if platform == "pc":
                    base_sql += " AND show_pc = TRUE"
                elif platform == "mobile":
                    base_sql += " AND show_mobile = TRUE"

                if category and category != "全部工具":
                    base_sql += " AND category = %s"
                    params.append(category)

                base_sql += " ORDER BY category, title"
                cur.execute(base_sql, params)

                rows = cur.fetchall()
                return [self._row_to_tool(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching tools for platform {platform}: {e}")
            return []
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
