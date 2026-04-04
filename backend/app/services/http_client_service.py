"""
HTTP Client Service - 处理 HTTP 请求发送和数据管理
"""

import logging
import uuid
import json
import time
import ipaddress
import socket
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

from app.config.database import get_db_connection
from app.models.http_client_models import (
    CollectionCreate, CollectionUpdate,
    HttpRequestCreate, HttpRequestUpdate,
    EnvironmentCreate, EnvironmentUpdate,
    SendRequestRequest, SendRequestResponse,
    RequestHistoryCreate,
)

logger = logging.getLogger(__name__)


def is_safe_url(url: str) -> bool:
    """检查 URL 是否安全（非内网地址，防止 SSRF）"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False

        # 允许 localhost 用于本地开发测试
        if hostname.lower() in ['localhost', '127.0.0.1']:
            return True

        # 解析 IP 地址
        ip = socket.gethostbyname(hostname)
        ip_addr = ipaddress.ip_address(ip)

        # 检查是否为私有地址
        if ip_addr.is_private:
            return False
        if ip_addr.is_loopback:
            return False
        if ip_addr.is_link_local:
            return False
        if ip_addr.is_reserved:
            return False

        return True
    except Exception as e:
        logger.error(f"URL safety check failed for {url}: {e}")
        return False


class HttpClientService:
    """HTTP Client 服务类"""

    def __init__(self):
        pass

    # ============= Collection Methods =============

    def get_all_collections(self, workspace_id: str = "default") -> List[Dict]:
        """获取所有集合"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM http_request_collections
                    WHERE workspace_id = %s
                    ORDER BY sort_order, created_at
                """, (workspace_id,))
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Error fetching collections: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_collection(self, collection_id: str) -> Optional[Dict]:
        """获取集合详情"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM http_request_collections
                    WHERE id = %s
                """, (collection_id,))
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Error fetching collection: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def create_collection(self, request: CollectionCreate) -> Optional[Dict]:
        """创建集合"""
        conn = None
        try:
            conn = get_db_connection()
            collection_id = str(uuid.uuid4())
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO http_request_collections
                    (id, name, description, workspace_id, parent_id, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    collection_id,
                    request.name,
                    request.description,
                    request.workspace_id,
                    request.parent_id,
                    request.sort_order,
                ))
                conn.commit()
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def update_collection(self, collection_id: str, request: CollectionUpdate) -> Optional[Dict]:
        """更新集合"""
        conn = None
        try:
            conn = get_db_connection()
            updates = []
            values = []

            if request.name is not None:
                updates.append("name = %s")
                values.append(request.name)
            if request.description is not None:
                updates.append("description = %s")
                values.append(request.description)
            if request.sort_order is not None:
                updates.append("sort_order = %s")
                values.append(request.sort_order)

            if not updates:
                return self.get_collection(collection_id)

            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(collection_id)

            query = f"""
                UPDATE http_request_collections
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING *
            """

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, values)
                conn.commit()
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Error updating collection: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def delete_collection(self, collection_id: str) -> bool:
        """删除集合（级联删除子项）"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # 由于设置了 ON DELETE CASCADE，子表记录会自动删除
                cur.execute("""
                    DELETE FROM http_request_collections
                    WHERE id = %s
                """, (collection_id,))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    # ============= Request Methods =============

    def get_requests_by_collection(self, collection_id: str) -> List[Dict]:
        """获取集合下的所有请求"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM http_requests
                    WHERE collection_id = %s
                    ORDER BY sort_order, created_at
                """, (collection_id,))
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Error fetching requests: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_request(self, request_id: str) -> Optional[Dict]:
        """获取请求详情"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM http_requests
                    WHERE id = %s
                """, (request_id,))
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Error fetching request: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def create_request(self, request: HttpRequestCreate) -> Optional[Dict]:
        """创建请求"""
        conn = None
        try:
            conn = get_db_connection()
            request_id = str(uuid.uuid4())
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO http_requests
                    (id, collection_id, name, method, url, headers, params,
                     body_type, body, auth_type, auth_config, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    request_id,
                    request.collection_id,
                    request.name,
                    request.method,
                    request.url,
                    json.dumps(request.headers),
                    json.dumps(request.params),
                    request.body_type,
                    request.body,
                    request.auth_type,
                    json.dumps(request.auth_config),
                    request.sort_order,
                ))
                conn.commit()
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Error creating request: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def update_request(self, request_id: str, request: HttpRequestUpdate) -> Optional[Dict]:
        """更新请求"""
        conn = None
        try:
            conn = get_db_connection()
            updates = []
            values = []

            if request.name is not None:
                updates.append("name = %s")
                values.append(request.name)
            if request.method is not None:
                updates.append("method = %s")
                values.append(request.method)
            if request.url is not None:
                updates.append("url = %s")
                values.append(request.url)
            if request.headers is not None:
                updates.append("headers = %s")
                values.append(json.dumps(request.headers))
            if request.params is not None:
                updates.append("params = %s")
                values.append(json.dumps(request.params))
            if request.body_type is not None:
                updates.append("body_type = %s")
                values.append(request.body_type)
            if request.body is not None:
                updates.append("body = %s")
                values.append(request.body)
            if request.auth_type is not None:
                updates.append("auth_type = %s")
                values.append(request.auth_type)
            if request.auth_config is not None:
                updates.append("auth_config = %s")
                values.append(json.dumps(request.auth_config))
            if request.sort_order is not None:
                updates.append("sort_order = %s")
                values.append(request.sort_order)

            if not updates:
                return self.get_request(request_id)

            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(request_id)

            query = f"""
                UPDATE http_requests
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING *
            """

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, values)
                conn.commit()
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Error updating request: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def delete_request(self, request_id: str) -> bool:
        """删除请求"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM http_requests
                    WHERE id = %s
                """, (request_id,))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting request: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    # ============= Environment Methods =============

    def get_all_environments(self, workspace_id: str = "default") -> List[Dict]:
        """获取所有环境"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM http_environments
                    WHERE workspace_id = %s
                    ORDER BY created_at
                """, (workspace_id,))
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Error fetching environments: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_active_environment(self, workspace_id: str = "default") -> Optional[Dict]:
        """获取当前激活的环境"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM http_environments
                    WHERE workspace_id = %s AND is_active = TRUE
                """, (workspace_id,))
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Error fetching active environment: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def create_environment(self, request: EnvironmentCreate) -> Optional[Dict]:
        """创建环境"""
        conn = None
        try:
            conn = get_db_connection()
            env_id = str(uuid.uuid4())

            # 如果设置为激活，先 deactivate 其他环境
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if request.is_active:
                    cur.execute("""
                        UPDATE http_environments
                        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE workspace_id = %s
                    """, (request.workspace_id,))

                cur.execute("""
                    INSERT INTO http_environments
                    (id, name, workspace_id, variables, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    env_id,
                    request.name,
                    request.workspace_id,
                    json.dumps(request.variables),
                    request.is_active,
                ))
                conn.commit()
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Error creating environment: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def update_environment(self, env_id: str, request: EnvironmentUpdate) -> Optional[Dict]:
        """更新环境"""
        conn = None
        try:
            conn = get_db_connection()
            updates = []
            values = []

            if request.name is not None:
                updates.append("name = %s")
                values.append(request.name)
            if request.variables is not None:
                updates.append("variables = %s")
                values.append(json.dumps(request.variables))
            if request.is_active is not None:
                updates.append("is_active = %s")
                values.append(request.is_active)

                # 如果设置为激活，先 deactivate 其他环境
                if request.is_active:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("""
                            UPDATE http_environments
                            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                            WHERE workspace_id = (SELECT workspace_id FROM http_environments WHERE id = %s)
                            AND id != %s
                        """, (env_id, env_id))

            if not updates:
                return self._get_environment_raw(env_id)

            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(env_id)

            query = f"""
                UPDATE http_environments
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING *
            """

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, values)
                conn.commit()
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Error updating environment: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def _get_environment_raw(self, env_id: str) -> Optional[Dict]:
        """获取环境详情（内部方法）"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM http_environments
                    WHERE id = %s
                """, (env_id,))
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Error fetching environment: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def activate_environment(self, env_id: str) -> Optional[Dict]:
        """激活环境"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 先 deactivate 所有环境
                cur.execute("""
                    UPDATE http_environments
                    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE workspace_id = (SELECT workspace_id FROM http_environments WHERE id = %s)
                """, (env_id,))

                # 激活指定环境
                cur.execute("""
                    UPDATE http_environments
                    SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                """, (env_id,))
                conn.commit()
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Error activating environment: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def delete_environment(self, env_id: str) -> bool:
        """删除环境"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM http_environments
                    WHERE id = %s
                """, (env_id,))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting environment: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    # ============= Send Request Method =============

    async def send_request(self, request: SendRequestRequest, user_id: str = "anonymous") -> Dict:
        """发送 HTTP 请求（代理转发）"""
        start_time = time.time()

        # SSRF 防护检查
        if not is_safe_url(request.url):
            raise ValueError(f"URL 不安全：{request.url} - 禁止访问内网地址")

        # 准备请求参数
        method = request.method.upper()
        url = request.url
        headers = request.headers or {}
        params = request.params or {}

        # 处理请求体
        body = None
        if request.body and request.body_type != "none":
            if request.body_type == "json":
                headers["Content-Type"] = "application/json"
                body = request.body
            elif request.body_type == "form":
                # form 格式需要解析
                try:
                    form_data = json.loads(request.body)
                    headers["Content-Type"] = "application/x-www-form-urlencoded"
                    params = form_data  # httpx 会自动处理
                except json.JSONDecodeError:
                    body = request.body
            else:  # raw
                body = request.body

        try:
            async with httpx.AsyncClient(
                follow_redirects=request.follow_redirects,
                timeout=httpx.Timeout(request.timeout / 1000.0),  # 转换为秒
                verify=True,  # 启用 SSL 验证
            ) as client:
                # 发送请求
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    content=body if body else None,
                )

                # 计算响应时间
                response_time = int((time.time() - start_time) * 1000)  # 毫秒

                # 尝试检测内容类型
                content_type = response.headers.get("content-type", "")

                # 尝试解码响应体
                try:
                    if "application/json" in content_type:
                        body_content = response.text
                    else:
                        body_content = response.text
                except Exception:
                    body_content = response.content.decode("utf-8", errors="replace")

                result = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": body_content,
                    "response_time": response_time,
                    "content_type": content_type.split(";")[0] if content_type else None,
                }

                # 保存历史记录
                try:
                    self._save_request_history(
                        user_id=user_id,
                        method=method,
                        url=url,
                        status_code=response.status_code,
                        response_time=response_time,
                        request_data={
                            "headers": headers,
                            "params": params,
                            "body": request.body,
                            "body_type": request.body_type,
                        },
                        response_data={
                            "headers": dict(response.headers),
                            "body": body_content[:10000],  # 限制存储大小
                        },
                    )
                except Exception as e:
                    logger.error(f"Failed to save request history: {e}")

                return result

        except httpx.TimeoutException as e:
            raise TimeoutError(f"请求超时（{request.timeout}ms）")
        except httpx.ConnectError as e:
            raise ConnectionError(f"连接失败：{str(e)}")
        except httpx.SSLError as e:
            raise ValueError(f"SSL 错误：{str(e)}")
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise

    def _save_request_history(
        self,
        user_id: str,
        method: str,
        url: str,
        status_code: int,
        response_time: int,
        request_data: Dict,
        response_data: Dict,
        request_id: Optional[str] = None,
    ):
        """保存请求历史"""
        conn = None
        try:
            conn = get_db_connection()
            history_id = str(uuid.uuid4())
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO http_request_history
                    (id, user_id, request_id, method, url, status_code,
                     response_time, request_data, response_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    history_id,
                    user_id,
                    request_id,
                    method,
                    url,
                    status_code,
                    response_time,
                    json.dumps(request_data),
                    json.dumps(response_data),
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving request history: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def get_request_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """获取请求历史"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM http_request_history
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (user_id, limit))
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Error fetching history: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def clear_request_history(self, user_id: str) -> bool:
        """清空请求历史"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM http_request_history
                    WHERE user_id = %s
                """, (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    # ============= Import/Export Methods =============

    def import_postman_collection(self, collection_data: Dict, workspace_id: str = "default") -> Dict:
        """导入 Postman Collection v2.1 格式"""
        imported_count = 0
        failed_count = 0
        errors = []

        try:
            # 解析 Postman Collection
            info = collection_data.get("info", {})
            collection_name = info.get("name", "Imported Collection")
            items = collection_data.get("item", [])

            # 创建集合
            collection_result = self.create_collection(CollectionCreate(
                name=collection_name,
                description=f"Imported from Postman",
                workspace_id=workspace_id,
            ))

            if not collection_result:
                errors.append("Failed to create collection")
                return {"success": False, "imported_count": 0, "failed_count": len(items), "errors": errors}

            collection_id = collection_result["id"]

            # 导入请求
            for idx, item in enumerate(items):
                try:
                    if "request" not in item:  # 可能是文件夹
                        continue

                    request_data = item["request"]
                    url_data = request_data.get("url", {})

                    # 构建 URL
                    if isinstance(url_data, dict):
                        url = f"{url_data.get('protocol', 'http')}://{url_data.get('host', [''])[0]}"
                        if url_data.get("path"):
                            url += "/" + "/".join(url_data["path"])
                        if url_data.get("query"):
                            url += "?" + "&".join([f"{q['key']}={q.get('value', '')}" for q in url_data["query"]])
                    else:
                        url = url_data

                    # 解析 Headers
                    headers = {}
                    if request_data.get("header"):
                        for header in request_data["header"]:
                            headers[header["key"]] = header.get("value", "")

                    # 解析 Body
                    body_type = "none"
                    body = None
                    if request_data.get("body"):
                        body_data = request_data["body"]
                        if body_data.get("mode") == "raw":
                            body_type = "json"
                            body = body_data.get("raw", "")
                        elif body_data.get("mode") == "formdata":
                            body_type = "form"
                            body = body_data.get("formdata", [])

                    # 创建请求
                    self.create_request(HttpRequestCreate(
                        collection_id=collection_id,
                        name=item.get("name", f"Request {idx + 1}"),
                        method=request_data.get("method", "GET"),
                        url=url,
                        headers=headers,
                        params={},
                        body_type=body_type,
                        body=body,
                        auth_type="none",
                        auth_config={},
                        sort_order=idx,
                    ))
                    imported_count += 1
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Failed to import item {idx + 1}: {str(e)}")

            return {
                "success": True,
                "imported_count": imported_count,
                "failed_count": failed_count,
                "errors": errors,
                "collection_id": collection_id,
            }

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return {
                "success": False,
                "imported_count": 0,
                "failed_count": 0,
                "errors": [str(e)],
            }

    def export_collection(self, collection_id: str) -> Dict:
        """导出集合为 Postman Collection v2.1 格式"""
        try:
            # 获取集合信息
            collection = self.get_collection(collection_id)
            if not collection:
                return {"success": False, "error": "Collection not found"}

            # 获取集合下的所有请求
            requests = self.get_requests_by_collection(collection_id)

            # 构建 Postman Collection 格式
            postman_collection = {
                "info": {
                    "name": collection["name"],
                    "description": collection.get("description", ""),
                    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                },
                "item": [],
            }

            for req in requests:
                item = {
                    "name": req["name"],
                    "request": {
                        "method": req["method"],
                        "url": {
                            "raw": req["url"],
                        },
                        "header": [
                            {"key": k, "value": v} for k, v in req.get("headers", {}).items()
                        ],
                    },
                }

                # 添加查询参数
                if req.get("params"):
                    item["request"]["url"]["query"] = [
                        {"key": k, "value": v} for k, v in req["params"].items()
                    ]

                # 添加 Body
                if req.get("body") and req.get("body_type") != "none":
                    if req["body_type"] == "json":
                        item["request"]["body"] = {
                            "mode": "raw",
                            "raw": req["body"],
                            "options": {"raw": {"language": "json"}},
                        }
                    elif req["body_type"] == "form":
                        item["request"]["body"] = {
                            "mode": "formdata",
                            "formdata": req["body"],
                        }

                # 添加认证
                if req.get("auth_type") == "bearer":
                    item["request"]["auth"] = {
                        "type": "bearer",
                        "bearer": [{"key": "token", "value": req["auth_config"].get("token", "")}],
                    }
                elif req.get("auth_type") == "basic":
                    item["request"]["auth"] = {
                        "type": "basic",
                        "basic": [
                            {"key": "username", "value": req["auth_config"].get("username", "")},
                            {"key": "password", "value": req["auth_config"].get("password", "")},
                        ],
                    }
                elif req.get("auth_type") == "apikey":
                    item["request"]["auth"] = {
                        "type": "apikey",
                        "apikey": [
                            {"key": "key", "value": req["auth_config"].get("key", "")},
                            {"key": "value", "value": req["auth_config"].get("value", "")},
                            {"key": "in", "value": req["auth_config"].get("in", "header")},
                        ],
                    }

                postman_collection["item"].append(item)

            return {"success": True, "data": postman_collection}

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {"success": False, "error": str(e)}


# 单例
http_client_service = HttpClientService()
