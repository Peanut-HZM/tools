"""
HTTP Client Service - 处理 HTTP 请求发送和数据管理

支持：
- 集合/请求/环境 CRUD（headers/params 支持 list 格式，含启用/禁用）
- 认证注入（bearer/basic/apikey）
- 动态变量（$timestamp/$uuid/$randomEmail 等内置动态值）
- 轻量 JSONPath 求值 + 可视化断言 + 后置提取变量（结果写回激活环境）
- 请求体类型：json/xml/form/form-data/raw/binary/graphql
- cURL 导入解析、Postman v2.1 导入导出、OpenAPI/Swagger 导入
"""

import logging
import uuid
import json
import time
import re
import random
import shlex
import ipaddress
import socket
import base64
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from urllib.parse import urlparse, quote

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

from app.config.database import get_pooled_db_connection, release_db_connection
from app.models.http_client_models import (
    CollectionCreate, CollectionUpdate,
    HttpRequestCreate, HttpRequestUpdate,
    EnvironmentCreate, EnvironmentUpdate,
    SendRequestRequest, SendRequestResponse,
    RequestHistoryCreate, AssertionResult,
    KeyValueItem, normalize_kv, kv_to_list_payload,
)

logger = logging.getLogger(__name__)


# ============= 轻量 JSONPath 求值器 =============

class JsonPathError(Exception):
    pass


def _tokenize_path(path: str) -> List[Tuple[str, Any]]:
    """将 JSONPath 表达式解析为 token 序列。

    支持：$ 根、.key、['key']、[index]、[-1]、[*]、.*、..key（递归下降）
    """
    tokens: List[Tuple[str, Any]] = []
    i = 0
    n = len(path)
    if not path:
        raise JsonPathError("空表达式")
    if path[0] == '$':
        i = 1
    elif not path.startswith(('.', '[')):
        # 允许省略 $，直接以 .key 或 key 开头
        tokens.append(('key', path))
        return tokens

    buf = ''
    while i < n:
        ch = path[i]
        if ch == '.':
            if i + 1 < n and path[i + 1] == '.':
                i += 1
                # 递归下降 ..key
                i += 1
                key = ''
                while i < n and path[i] not in '.[':
                    key += path[i]
                    i += 1
                if not key:
                    raise JsonPathError(f"递归下降缺少字段名: {path}")
                tokens.append(('recursive', key))
                continue
            i += 1
            if i < n and path[i] == '*':
                tokens.append(('wildcard', None))
                i += 1
                continue
            key = ''
            while i < n and path[i] not in '.[':
                key += path[i]
                i += 1
            if key:
                tokens.append(('key', key))
        elif ch == '[':
            i += 1
            end = path.find(']', i)
            if end == -1:
                raise JsonPathError(f"括号未闭合: {path}")
            inner = path[i:end].strip()
            i = end + 1
            if inner == '*' or inner == "'*'":
                tokens.append(('wildcard', None))
            elif inner.startswith("'") and inner.endswith("'") and len(inner) >= 2:
                tokens.append(('key', inner[1:-1]))
            elif inner.startswith('"') and inner.endswith('"') and len(inner) >= 2:
                tokens.append(('key', inner[1:-1]))
            else:
                try:
                    tokens.append(('index', int(inner)))
                except ValueError:
                    raise JsonPathError(f"不支持的索引: [{inner}]")
        else:
            # 无点号开头的字段名（容错）
            key = ''
            while i < n and path[i] not in '.[':
                key += path[i]
                i += 1
            if key:
                tokens.append(('key', key))
    return tokens


def _match_from(node: Any, tokens: List[Tuple[str, Any]], ti: int, out: List[Any]):
    """递归求值 token 序列，将所有匹配写入 out"""
    if ti >= len(tokens):
        out.append(node)
        return
    kind, arg = tokens[ti]
    if kind == 'key':
        if isinstance(node, dict) and arg in node:
            _match_from(node[arg], tokens, ti + 1, out)
    elif kind == 'index':
        if isinstance(node, list):
            idx = arg
            if -len(node) <= idx < len(node):
                _match_from(node[idx], tokens, ti + 1, out)
    elif kind == 'wildcard':
        if isinstance(node, dict):
            for v in node.values():
                _match_from(v, tokens, ti + 1, out)
        elif isinstance(node, list):
            for v in node:
                _match_from(v, tokens, ti + 1, out)
    elif kind == 'recursive':
        # 自身 + 全部后代中查找该字段
        _collect_by_key(node, arg, out, tokens, ti + 1)


def _collect_by_key(node: Any, key: str, out: List[Any], tokens: List[Tuple[str, Any]], next_ti: int):
    if isinstance(node, dict):
        if key in node:
            _match_from(node[key], tokens, next_ti, out)
        for v in node.values():
            _collect_by_key(v, key, out, tokens, next_ti)
    elif isinstance(node, list):
        for v in node:
            _collect_by_key(v, key, out, tokens, next_ti)


def jsonpath_extract(data: Any, path: str) -> List[Any]:
    """执行 JSONPath，返回所有匹配项（找不到返回空列表）"""
    tokens = _tokenize_path(path.strip())
    out: List[Any] = []
    _match_from(data, tokens, 0, out)
    return out


def jsonpath_first(data: Any, path: str) -> Tuple[bool, str]:
    """执行 JSONPath 取第一个匹配，返回 (是否命中, 序列化后的值)"""
    try:
        matches = jsonpath_extract(data, path)
    except JsonPathError as e:
        return False, f"JSONPath 语法错误：{e}"
    if not matches:
        return False, "未匹配到任何值"
    value = matches[0]
    if isinstance(value, (dict, list)):
        return True, json.dumps(value, ensure_ascii=False)
    if value is None:
        return True, "null"
    if isinstance(value, bool):
        return True, "true" if value else "false"
    return True, str(value)


# ============= 内置动态变量 =============

_RANDOM_WORDS = [
    "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel",
    "india", "juliet", "kilo", "lima", "mike", "november", "oscar", "papa",
    "quebec", "romeo", "sierra", "tango", "uniform", "victor", "whiskey",
    "xray", "yankee", "zulu", "amber", "basil", "cedar", "dusk", "ember",
    "frost", "garnet", "harbor", "ivory", "jasper", "kelp", "lunar", "maple",
]
_FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
                "David", "Elizabeth", "William", "Susan", "Richard", "Jessica", "Joseph", "Sarah"]
_LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
               "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"]
_CITIES = ["Beijing", "Shanghai", "Shenzhen", "Hangzhou", "Tokyo", "New York", "London",
           "Paris", "Berlin", "Singapore", "Sydney", "Toronto", "Seoul", "Dubai"]
_TLDS = ["com", "net", "org", "io", "dev", "cn", "co", "me"]


def _dyn_value(name: str) -> Optional[str]:
    """生成内置动态变量的值；未知返回 None"""
    now = int(time.time())
    mapping = {
        # 时间
        "$timestamp": str(now),
        "$timestampMs": str(now * 1000),
        "$isoTimestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "$dateNow": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "$dateToday": datetime.now().strftime("%Y-%m-%d"),
        # 标识
        "$uuid": str(uuid.uuid4()),
        "$guid": str(uuid.uuid4()),
        "$randomInt": str(random.randint(0, 10000)),
        "$randomBoolean": random.choice(["true", "false"]),
        # 人名/联系
        "$randomFirstName": random.choice(_FIRST_NAMES),
        "$randomLastName": random.choice(_LAST_NAMES),
        "$randomName": f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}",
        "$randomEmail": f"{random.choice(_FIRST_NAMES).lower()}.{random.choice(_LAST_NAMES).lower()}@example.{random.choice(_TLDS)}",
        "$randomPhone": f"+8613{random.randint(100000000, 999999999)}",
        # 地理
        "$randomCity": random.choice(_CITIES),
        "$randomCountry": random.choice(["China", "United States", "Japan", "Germany", "France", "United Kingdom"]),
        "$randomLatitude": f"{random.uniform(-90, 90):.6f}",
        "$randomLongitude": f"{random.uniform(-180, 180):.6f}",
        # 网络
        "$randomUrl": f"https://www.example.{random.choice(_TLDS)}/{random.choice(_RANDOM_WORDS)}",
        "$randomIPv4": f"{random.randint(1, 254)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
        "$randomUserAgent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 Safari/605.1.15",
        ]),
        # 业务杂项
        "$randomColor": random.choice(["red", "orange", "yellow", "green", "blue", "purple", "black", "white"]),
        "$randomHexColor": "#{:06x}".format(random.randint(0, 0xFFFFFF)),
        "$randomPrice": f"{random.uniform(1, 999):.2f}",
        "$randomCompanyName": f"{random.choice(_LAST_NAMES)} {random.choice(['Tech', 'Soft', 'Cloud', 'Data', 'Net'])} Co., Ltd",
        "$randomWord": random.choice(_RANDOM_WORDS),
        "$randomWords": " ".join(random.choices(_RANDOM_WORDS, k=random.randint(3, 6))),
        "$randomSentence": " ".join(random.choices(_RANDOM_WORDS, k=random.randint(8, 14))).capitalize() + ".",
        "$randomParagraph": " ".join(
            " ".join(random.choices(_RANDOM_WORDS, k=random.randint(8, 14))).capitalize() + "."
            for _ in range(random.randint(2, 4))
        ),
    }
    return mapping.get(name)


def is_safe_url(url: str) -> bool:
    """检查 URL 是否安全（非内网地址，防止 SSRF）"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False

        # 允许 localhost 用于本地开发测试
        if hostname.lower() in ['localhost', '127.0.0.1', '::1']:
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


# ============= form-data 安全常量 =============

# 单条目文件大小上限（25MB 解码后字节数），超过即拒绝
MAX_FILE_BYTES = 25 * 1024 * 1024
# 所有 file 条目累计大小上限（50MB），超过即拒绝
MAX_TOTAL_FILE_BYTES = 50 * 1024 * 1024
# base64 字符串长度上限（25MB → ~33.4MB base64），用于解码前快速拒绝超大请求
MAX_BASE64_CHARS = 35_000_000

# mime 类型白名单正则（type/subtype 仅允许字母数字和 .+-），防止 header-injection
MIME_PATTERN = re.compile(r'^[a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+$')

# 硬编码扩展名映射（不信任 mime 后缀），避免攻击者构造 `text/html` 等危险类型并伪造扩展名
MIME_TO_EXT: Dict[str, str] = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/gif': 'gif',
    'image/webp': 'webp',
    'image/svg+xml': 'svg',
    'image/bmp': 'bmp',
    'text/plain': 'txt',
    'text/csv': 'csv',
    'text/html': 'html',
    'text/xml': 'xml',
    'application/json': 'json',
    'application/xml': 'xml',
    'application/pdf': 'pdf',
    'application/zip': 'zip',
    'application/octet-stream': 'bin',
}


def sanitize_multipart_field_name(name: str) -> Optional[str]:
    """清洗 multipart 字段名：拒绝包含 \\r \\n \" 的字符，防止注入 boundary/header

    httpx 会用字段名构造 Content-Disposition: form-data; name="<key>"
    若 key 含 \r\n 或引号，可破坏 multipart 结构或注入额外 header
    """
    if not isinstance(name, str):
        return None
    if any(c in name for c in ('\r', '\n', '"')):
        return None
    # 限制长度，避免超长 key 撑爆 header
    if len(name) > 256:
        return None
    return name


def parse_data_url(data_url: str) -> Optional[Tuple[str, bytes, str]]:
    """解析 data:URL，格式：data:<mime>;base64,<data>

    安全校验：
    - mime 必须匹配白名单正则 ^[a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+$
    - 文件大小不能超过 MAX_FILE_BYTES（25MB）
    - base64 字符串长度不能超过 MAX_BASE64_CHARS（避免先构造再解码造成的 DoS）
    - 文件名扩展名使用硬编码映射（不信任 mime 自带后缀）
    """
    try:
        if not isinstance(data_url, str):
            return None
        # 先用 \r\n 防御：拒绝任何包含控制字符的 data URL（防止 header-injection）
        if any(c in data_url for c in ('\r', '\n')):
            return None
        match = re.match(r'^data:([^;]+);base64,(.+)$', data_url, re.DOTALL)
        if not match:
            return None
        mime_type = match.group(1).strip().lower()
        raw_b64 = match.group(2)
        # mime 白名单校验
        if not MIME_PATTERN.match(mime_type):
            logger.warning(f"Rejected data URL with invalid mime type: {mime_type!r}")
            return None
        # base64 长度上限（解码前快速拒绝）
        if len(raw_b64) > MAX_BASE64_CHARS:
            logger.warning(f"Rejected data URL: base64 length {len(raw_b64)} exceeds {MAX_BASE64_CHARS}")
            return None
        content = base64.b64decode(raw_b64, validate=True)
        # 解码后字节数上限
        if len(content) > MAX_FILE_BYTES:
            logger.warning(f"Rejected data URL: decoded size {len(content)} exceeds {MAX_FILE_BYTES}")
            return None
        # 使用硬编码扩展名映射（不信任 mime 后缀）
        ext = MIME_TO_EXT.get(mime_type, 'bin')
        filename = f"upload.{ext}"
        return (filename, content, mime_type)
    except Exception as e:
        logger.error(f"Failed to parse data URL: {e}")
        return None


class HttpClientService:
    """HTTP Client 服务类"""

    def __init__(self):
        pass

    # ============= Collection Methods =============

    def get_all_collections(self, workspace_id: str = "default") -> List[Dict]:
        """获取所有集合"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    def get_collection(self, collection_id: str) -> Optional[Dict]:
        """获取集合详情"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    def create_collection(self, request: CollectionCreate) -> Optional[Dict]:
        """创建集合"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    def update_collection(self, collection_id: str, request: CollectionUpdate) -> Optional[Dict]:
        """更新集合"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
            if request.parent_id is not None:
                # 防止将集合挂到自身形成环
                if request.parent_id == collection_id:
                    raise ValueError("不能将集合设置为自身的父集合")
                updates.append("parent_id = %s")
                values.append(request.parent_id)

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
                release_db_connection(conn)

    def delete_collection(self, collection_id: str) -> bool:
        """删除集合（级联删除子项）"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    # ============= Request Methods =============

    def get_requests_by_collection(self, collection_id: str) -> List[Dict]:
        """获取集合下的所有请求"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    def get_request(self, request_id: str) -> Optional[Dict]:
        """获取请求详情"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    def create_request(self, request: HttpRequestCreate) -> Optional[Dict]:
        """创建请求"""
        conn = None
        try:
            conn = get_pooled_db_connection()
            request_id = str(uuid.uuid4())
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO http_requests
                    (id, collection_id, name, method, url, headers, params,
                     body_type, body, form_data, auth_type, auth_config,
                     extract_variables, assertions, description, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    json.dumps(request.form_data or []),
                    request.auth_type,
                    json.dumps(request.auth_config),
                    json.dumps(request.extract_variables),
                    json.dumps(request.assertions),
                    request.description,
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
                release_db_connection(conn)

    def update_request(self, request_id: str, request: HttpRequestUpdate) -> Optional[Dict]:
        """更新请求"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
            if request.form_data is not None:
                updates.append("form_data = %s")
                values.append(json.dumps(request.form_data))
            if request.auth_type is not None:
                updates.append("auth_type = %s")
                values.append(request.auth_type)
            if request.auth_config is not None:
                updates.append("auth_config = %s")
                values.append(json.dumps(request.auth_config))
            if request.extract_variables is not None:
                updates.append("extract_variables = %s")
                values.append(json.dumps(request.extract_variables))
            if request.assertions is not None:
                updates.append("assertions = %s")
                values.append(json.dumps(request.assertions))
            if request.description is not None:
                updates.append("description = %s")
                values.append(request.description)
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
                release_db_connection(conn)

    def delete_request(self, request_id: str) -> bool:
        """删除请求"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    # ============= Environment Methods =============

    def get_all_environments(self, workspace_id: str = "default") -> List[Dict]:
        """获取所有环境"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    def get_active_environment(self, workspace_id: str = "default") -> Optional[Dict]:
        """获取当前激活的环境"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    def create_environment(self, request: EnvironmentCreate) -> Optional[Dict]:
        """创建环境"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                    (id, name, workspace_id, base_url, variables, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    env_id,
                    request.name,
                    request.workspace_id,
                    request.base_url,
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
                release_db_connection(conn)

    def update_environment(self, env_id: str, request: EnvironmentUpdate) -> Optional[Dict]:
        """更新环境"""
        conn = None
        try:
            conn = get_pooled_db_connection()
            updates = []
            values = []

            if request.name is not None:
                updates.append("name = %s")
                values.append(request.name)
            if request.base_url is not None:
                updates.append("base_url = %s")
                values.append(request.base_url.rstrip('/') if request.base_url else '')
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
                release_db_connection(conn)

    def _get_environment_raw(self, env_id: str) -> Optional[Dict]:
        """获取环境详情（内部方法）"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    def activate_environment(self, env_id: str) -> Optional[Dict]:
        """激活环境"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    def delete_environment(self, env_id: str) -> bool:
        """删除环境"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    # ============= 变量解析 =============

    def resolve_variables(self, text: str, variables: Dict[str, str]) -> str:
        """将 {{variableName}} 替换为环境变量值，支持内置动态变量"""
        if not text:
            return text

        def replacer(match):
            var_name = match.group(1).strip()
            if var_name in variables:
                return str(variables[var_name])
            dyn = _dyn_value(var_name)
            if dyn is not None:
                return dyn
            return match.group(0)

        return re.sub(r'\{\{(.+?)\}\}', replacer, text)

    # ============= 认证注入 =============

    def _apply_auth(
        self,
        auth_type: str,
        auth_config: Dict[str, Any],
        headers: Dict[str, str],
        params: Dict[str, str],
        variables: Dict[str, str],
    ) -> None:
        """将认证配置转换为实际的 Header / Query 参数（就地修改）"""
        if not auth_type or auth_type == 'none':
            return

        cfg = {k: self.resolve_variables(str(v), variables) for k, v in (auth_config or {}).items()}

        if auth_type == 'bearer':
            token = cfg.get('token', '')
            if token:
                headers['Authorization'] = f"Bearer {token}"
        elif auth_type == 'basic':
            username = cfg.get('username', '')
            password = cfg.get('password', '')
            raw = f"{username}:{password}"
            encoded = base64.b64encode(raw.encode('utf-8')).decode('ascii')
            headers['Authorization'] = f"Basic {encoded}"
        elif auth_type == 'apikey':
            key = cfg.get('key', '')
            value = cfg.get('value', '')
            if not key:
                return
            if cfg.get('in', 'header') == 'query':
                params[key] = value
            else:
                headers[key] = value

    # ============= 断言与提取 =============

    def _get_assert_actual(
        self,
        rule: Dict[str, Any],
        status_code: int,
        resp_headers: Dict[str, str],
        body: str,
        response_time: int,
    ) -> Tuple[str, str]:
        """获取断言的实际值，返回 (实际值, 错误说明)"""
        source = rule.get('source', 'status')
        expression = (rule.get('expression') or '').strip()

        if source == 'status':
            return str(status_code), ""
        if source == 'response_time':
            return str(response_time), ""
        if source == 'header':
            if not expression:
                return "", "未指定 Header 名"
            value = resp_headers.get(expression, resp_headers.get(expression.lower()))
            if value is None:
                return "", f"响应头 {expression} 不存在"
            return value, ""
        if source == 'body_json':
            if not expression:
                return "", "未指定 JSONPath 表达式"
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return "", "响应体不是合法 JSON"
            ok, value = jsonpath_first(data, expression)
            return value, ""
        if source == 'body_text':
            return body, ""
        return "", f"未知断言来源: {source}"

    def _compare_assert(self, operator: str, actual: str, expected: str) -> Tuple[bool, str]:
        """执行断言比较，返回 (是否通过, 说明)"""
        op = operator or 'equal'
        try:
            if op == 'exists':
                return (actual != "" or expected == ""), ""
            if op == 'not_exists':
                return actual == "", ""
            if op == 'is_empty':
                return actual == "", ""
            if op == 'not_empty':
                return actual != "", ""

            if op == 'equal':
                return actual == expected, f"期望 {expected!r}，实际 {actual!r}"
            if op == 'not_equal':
                return actual != expected, f"期望不等于 {expected!r}，实际 {actual!r}"
            if op == 'contains':
                return expected in actual, f"实际值不包含 {expected!r}"
            if op == 'not_contains':
                return expected not in actual, f"实际值包含 {expected!r}"
            if op == 'starts_with':
                return actual.startswith(expected), f"实际值不以 {expected!r} 开头"
            if op == 'ends_with':
                return actual.endswith(expected), f"实际值不以 {expected!r} 结尾"
            if op == 'regex_match':
                return bool(re.search(expected, actual)), f"正则 {expected!r} 未匹配"
            if op in ('greater_than', 'less_than', 'greater_or_equal', 'less_or_equal'):
                try:
                    a_num, e_num = float(actual), float(expected)
                except (ValueError, TypeError):
                    # 数值比较失败时退化为字符串比较
                    a_num, e_num = actual, expected
                if op == 'greater_than':
                    return a_num > e_num, f"期望 > {expected!r}，实际 {actual!r}"
                if op == 'less_than':
                    return a_num < e_num, f"期望 < {expected!r}，实际 {actual!r}"
                if op == 'greater_or_equal':
                    return a_num >= e_num, f"期望 >= {expected!r}，实际 {actual!r}"
                return a_num <= e_num, f"期望 <= {expected!r}，实际 {actual!r}"

            # exists / not_exists 需要 actual 语义补充：空字符串视为不存在
            return False, f"未知比较方式: {op}"
        except Exception as e:
            return False, f"断言执行异常: {e}"

    def _run_assertions(
        self,
        rules: List[Dict[str, Any]],
        variables: Dict[str, str],
        status_code: int,
        resp_headers: Dict[str, str],
        body: str,
        response_time: int,
    ) -> List[AssertionResult]:
        """执行全部断言规则"""
        results: List[AssertionResult] = []
        for rule in rules or []:
            if isinstance(rule, dict):
                rule_dict = rule
            else:
                rule_dict = rule.model_dump()
            if not rule_dict.get('enabled', True):
                continue
            name = rule_dict.get('name') or rule_dict.get('expression') or rule_dict.get('source', '')
            expected = self.resolve_variables(str(rule_dict.get('value', '') or ''), variables)
            actual, err = self._get_assert_actual(
                rule_dict, status_code, resp_headers, body, response_time,
            )
            if err:
                results.append(AssertionResult(
                    name=name, source=rule_dict.get('source', ''),
                    expression=rule_dict.get('expression', ''),
                    operator=rule_dict.get('operator', ''),
                    expected=expected, actual=actual,
                    passed=False, message=err,
                ))
                continue
            passed, message = self._compare_assert(rule_dict.get('operator', 'equal'), actual, expected)
            results.append(AssertionResult(
                name=name, source=rule_dict.get('source', ''),
                expression=rule_dict.get('expression', ''),
                operator=rule_dict.get('operator', ''),
                expected=expected, actual=actual,
                passed=passed, message=message,
            ))
        return results

    def _run_extractions(
        self,
        rules: List[Dict[str, Any]],
        variables: Dict[str, str],
        status_code: int,
        resp_headers: Dict[str, str],
        body: str,
        response_time: int,
    ) -> Dict[str, str]:
        """执行全部提取变量规则，返回 {变量名: 值}"""
        extracted: Dict[str, str] = {}
        for rule in rules or []:
            if isinstance(rule, dict):
                rule_dict = rule
            else:
                rule_dict = rule.model_dump()
            if not rule_dict.get('enabled', True):
                continue
            name = (rule_dict.get('name') or '').strip()
            if not name:
                continue
            source = rule_dict.get('source', 'body_json')
            expression = (rule_dict.get('expression') or '').strip()
            index = rule_dict.get('index')
            value: Optional[str] = None

            try:
                if source == 'status':
                    value = str(status_code)
                elif source == 'response_time':
                    value = str(response_time)
                elif source == 'header':
                    if expression:
                        value = resp_headers.get(expression, resp_headers.get(expression.lower()))
                elif source == 'body_json':
                    if expression:
                        try:
                            data = json.loads(body)
                            matches = jsonpath_extract(data, expression)
                            if matches:
                                if index is not None and isinstance(index, int) and 0 <= index < len(matches):
                                    picked = matches[index]
                                else:
                                    picked = matches[0]
                                if isinstance(picked, (dict, list)):
                                    value = json.dumps(picked, ensure_ascii=False)
                                elif picked is None:
                                    value = "null"
                                elif isinstance(picked, bool):
                                    value = "true" if picked else "false"
                                else:
                                    value = str(picked)
                        except json.JSONDecodeError:
                            logger.warning("提取变量失败：响应体不是合法 JSON")
                        except JsonPathError as e:
                            logger.warning(f"提取变量失败：JSONPath 语法错误 {e}")
                elif source == 'body_text':
                    if expression:
                        match = re.search(expression, body)
                        if match:
                            value = match.group(1) if match.groups() else match.group(0)
            except Exception as e:
                logger.error(f"提取变量 {name} 失败: {e}")

            if value is not None:
                extracted[name] = value
        return extracted

    def _persist_extracted_variables(self, workspace_id: str, extracted: Dict[str, str]) -> None:
        """将提取到的变量合并写入当前激活的环境（供后续请求使用）"""
        if not extracted:
            return
        env = self.get_active_environment(workspace_id or "default")
        if not env:
            logger.info("无激活环境，提取变量不持久化")
            return
        merged = dict(env.get("variables") or {})
        merged.update(extracted)
        self.update_environment(env["id"], EnvironmentUpdate(variables=merged))

    # ============= cURL 解析 =============

    def parse_curl_command(self, curl_command: str) -> Dict[str, Any]:
        """解析 cURL 命令为请求参数（返回 list 格式 headers/params 与认证配置）"""
        cmd = curl_command.strip()
        # 去掉行续符
        cmd = cmd.replace('\\\r\n', ' ').replace('\\\n', ' ')
        # 兼容 powershell 反引号续行
        cmd = cmd.replace('`\r\n', ' ').replace('`\n', ' ')

        if cmd.startswith('curl '):
            cmd = cmd[5:]
        elif cmd == 'curl':
            cmd = ''

        try:
            parts = shlex.split(cmd)
        except ValueError:
            parts = cmd.split()

        method = ''
        url = ''
        header_items: List[KeyValueItem] = []
        body: Optional[str] = None
        body_type = 'none'
        form_data_entries: List[Dict[str, Any]] = []
        form_urlencoded_pairs: List[Tuple[str, str]] = []
        basic_auth: Optional[Tuple[str, str]] = None
        has_data_flag = False

        def find_header(key: str) -> Optional[KeyValueItem]:
            for item in header_items:
                if item.key.lower() == key.lower():
                    return item
            return None

        def set_header(key: str, value: str):
            existing = find_header(key)
            if existing:
                existing.value = value
            else:
                header_items.append(KeyValueItem(key=key, value=value, enabled=True))

        def value_getter(i: int) -> Optional[str]:
            if i + 1 < len(parts):
                return parts[i + 1]
            return None

        i = 0
        while i < len(parts):
            part = parts[i]
            nxt = value_getter(i)
            if part in ('-X', '--request') and nxt is not None:
                method = nxt.upper()
                i += 2
            elif part in ('-H', '--header') and nxt is not None:
                header_val = nxt
                if ':' in header_val:
                    k, v = header_val.split(':', 1)
                    if k.strip():
                        set_header(k.strip(), v.strip())
                i += 2
            elif part in ('-d', '--data', '--data-raw', '--data-binary') and nxt is not None:
                body = nxt
                has_data_flag = True
                i += 2
            elif part == '--data-urlencode' and nxt is not None:
                has_data_flag = True
                if '=' in nxt:
                    k, v = nxt.split('=', 1)
                    form_urlencoded_pairs.append((k, v))
                i += 2
            elif part in ('-F', '--form', '--form-string') and nxt is not None:
                has_data_flag = True
                if '=' in nxt:
                    k, v = nxt.split('=', 1)
                    if v.startswith('@'):
                        form_data_entries.append({
                            'key': k, 'value': v[1:], 'type': 'file',
                            'enabled': True, 'description': '',
                        })
                    else:
                        form_data_entries.append({
                            'key': k, 'value': v, 'type': 'text',
                            'enabled': True, 'description': '',
                        })
                i += 2
            elif part in ('-u', '--user') and nxt is not None:
                if ':' in nxt:
                    user, pwd = nxt.split(':', 1)
                else:
                    user, pwd = nxt, ''
                basic_auth = (user, pwd)
                i += 2
            elif part in ('-b', '--cookie') and nxt is not None:
                if '; ' in nxt or '=' in nxt:
                    set_header('Cookie', nxt)
                i += 2
            elif part in ('-A', '--user-agent') and nxt is not None:
                set_header('User-Agent', nxt)
                i += 2
            elif part in ('-e', '--referer') and nxt is not None:
                set_header('Referer', nxt)
                i += 2
            elif part in ('-r', '--range') and nxt is not None:
                set_header('Range', nxt)
                i += 2
            elif part in ('-t', '--mime-type') and nxt is not None:
                set_header('Content-Type', nxt)
                i += 2
            elif part in ('--url',) and nxt is not None:
                url = nxt
                i += 2
            elif part in ('-G', '--get'):
                # -G 时 -d 数据变为查询参数
                if body:
                    try:
                        parsed_body = json.loads(body)
                    except Exception:
                        parsed_body = body
                    if isinstance(parsed_body, str) and '&' in parsed_body:
                        for pair in parsed_body.split('&'):
                            if '=' in pair:
                                k, v = pair.split('=', 1)
                                form_urlencoded_pairs.append((k, v))
                    body = None
                i += 1
            elif part in ('-k', '--insecure', '-s', '--silent', '-S', '--show-error',
                          '-v', '--verbose', '-i', '--include', '-L', '--location',
                          '--compressed', '--http1.1', '--http2', '-#', '--progress-bar',
                          '-f', '--fail', '--no-buffer', '-4', '--ipv4', '-6', '--ipv6'):
                i += 1
            elif part == '-o' or part == '--output' or part == '--connect-timeout' \
                    or part == '--max-time' or part == '--retry' or part == '-m':
                i += 2
            elif part.startswith('-') and part not in ('-',):
                # 跳过其他不认识的选项
                i += 1
                if i < len(parts) and not parts[i].startswith('-'):
                    i += 1
            else:
                if not url and (part.startswith('http://') or part.startswith('https://')):
                    url = part
                elif not url:
                    url = part
                i += 1

        # URL 查询参数提取到 params
        params: List[KeyValueItem] = []
        query_string = ''
        if url and '?' in url:
            url, query_string = url.split('?', 1)
            for pair in query_string.split('&'):
                if not pair:
                    continue
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    params.append(KeyValueItem(key=k, value=v, enabled=True))
                else:
                    params.append(KeyValueItem(key=pair, value='', enabled=True))

        # Basic auth 转认证配置
        auth_type = 'none'
        auth_config: Dict[str, Any] = {}
        if basic_auth is not None:
            auth_type = 'basic'
            auth_config = {'username': basic_auth[0], 'password': basic_auth[1]}
        else:
            auth_header = find_header('Authorization')
            if auth_header and auth_header.value.lower().startswith('bearer '):
                auth_type = 'bearer'
                auth_config = {'token': auth_header.value[7:].strip()}
                header_items.remove(auth_header)

        # 根据 Content-Type 与数据形态判断 body_type
        content_type = (find_header('Content-Type').value if find_header('Content-Type') else '') or ''
        ct = content_type.lower()

        if form_data_entries:
            body_type = 'form-data'
            body = None
        elif form_urlencoded_pairs:
            if has_data_flag and body and form_urlencoded_pairs:
                # -d 与 --data-urlencode 混用：合并为 urlencoded form
                if '=' in body and '{' != body.lstrip()[:1]:
                    for pair in body.split('&'):
                        if '=' in pair:
                            k, v = pair.split('=', 1)
                            form_urlencoded_pairs.append((k, v))
                body = None
            body_type = 'form'
            body = '&'.join(f"{quote(k)}={quote(v)}" for k, v in form_urlencoded_pairs)
            if not find_header('Content-Type'):
                set_header('Content-Type', 'application/x-www-form-urlencoded')
        elif body is not None:
            stripped = body.lstrip()
            if 'json' in ct or stripped.startswith('{') or stripped.startswith('['):
                body_type = 'json'
            elif 'x-www-form-urlencoded' in ct:
                body_type = 'form'
            elif 'xml' in ct:
                body_type = 'xml'
            else:
                body_type = 'raw'
        else:
            body_type = 'none'

        if not method:
            method = 'GET' if (body is None and body_type == 'none') else 'POST'

        # 单大括号 path 参数保持原样；返回 list 格式
        return {
            'method': method,
            'url': url,
            'headers': kv_to_list_payload(header_items),
            'params': kv_to_list_payload(params),
            'body': body,
            'body_type': body_type,
            'form_data': form_data_entries,
            'auth_type': auth_type,
            'auth_config': auth_config,
        }

    # ============= Send Request Method =============

    async def send_request(self, request: SendRequestRequest, user_id: str = "anonymous") -> Dict:
        """发送 HTTP 请求（代理转发），并执行断言与提取变量"""
        start_time = time.time()

        # 获取环境变量（含前置 URL）
        env = self.get_active_environment(request.workspace_id or "default")
        variables: Dict[str, str] = dict(env.get("variables", {}) or {}) if env else {}
        base_url = (env.get("base_url") or "").rstrip('/') if env else ""

        # 前置 URL 拼接：路径以 / 开头且环境配置了 baseUrl 时自动拼接
        raw_url = (request.url or '').strip()
        if base_url and raw_url.startswith('/') and not raw_url.startswith('//'):
            raw_url = base_url + raw_url

        # 变量替换：URL
        url = self.resolve_variables(raw_url, variables)

        # SSRF 防护检查（变量替换后）
        if not is_safe_url(url):
            raise ValueError(f"URL 不安全：{url} - 禁止访问内网地址")

        # 准备请求参数（仅发送启用的条目；同 key 后者覆盖前者）
        method = request.method.upper()
        headers: Dict[str, str] = {}
        for item in normalize_kv(request.headers):
            if not item.enabled or not item.key.strip():
                continue
            headers[self.resolve_variables(item.key.strip(), variables)] = \
                self.resolve_variables(item.value, variables)
        params: Dict[str, str] = {}
        for item in normalize_kv(request.params):
            if not item.enabled or not item.key.strip():
                continue
            params[self.resolve_variables(item.key.strip(), variables)] = \
                self.resolve_variables(item.value, variables)

        # 认证注入
        self._apply_auth(request.auth_type, request.auth_config, headers, params, variables)

        # 处理请求体
        body = None
        # form-data 类型：使用 httpx 的 files + data 参数（multipart/form-data）
        files_payload: Optional[Dict[str, Tuple[str, bytes, str]]] = None
        is_form_data = request.body_type == "form-data"

        if is_form_data:
            files_payload = {}
            data_payload: Dict[str, str] = {}
            total_file_bytes = 0
            for entry in (request.form_data or []):
                if isinstance(entry, dict):
                    entry_enabled = entry.get('enabled', True)
                    entry_key = entry.get('key', '')
                    entry_value = entry.get('value') or ""
                    entry_type = entry.get('type', 'text')
                else:
                    entry_enabled = entry.enabled
                    entry_key = entry.key
                    entry_value = entry.value or ""
                    entry_type = entry.type
                if not entry_enabled:
                    continue
                # 防御 \r\n / " 注入：清洗 key；不合法则跳过
                safe_key = sanitize_multipart_field_name(entry_key)
                if not safe_key:
                    logger.warning(f"Skipping form-data entry with unsafe key: {entry_key!r}")
                    continue
                # 变量替换
                resolved_key = self.resolve_variables(safe_key, variables)
                entry_type = entry_type
                if entry_type == "file" and isinstance(entry_value, str) and entry_value.startswith("data:"):
                    parsed = parse_data_url(entry_value)
                    if parsed:
                        # 累计文件大小（防止 DoS：单条已限 25MB，整体限 50MB）
                        total_file_bytes += len(parsed[1])
                        if total_file_bytes > MAX_TOTAL_FILE_BYTES:
                            raise ValueError(
                                f"form-data 文件总大小超过上限 {MAX_TOTAL_FILE_BYTES // (1024*1024)}MB"
                            )
                        filename, content, mime = parsed
                        files_payload[resolved_key] = (filename, content, mime)
                    else:
                        # data:URL 解析失败（如 mime 黑名单、过大、含控制字符）直接跳过，避免原样转发敏感数据
                        logger.warning(f"Dropping form-data file entry: parse failed or rejected")
                        continue
                else:
                    data_payload[resolved_key] = self.resolve_variables(str(entry_value), variables)
            # 让 httpx 自动设置 multipart Content-Type（不要手动覆盖）
            body = None
            # 用于 httpx.request 参数
            request_kwargs: Dict[str, Any] = {
                "data": data_payload,
                "files": files_payload if files_payload else None,
            }
        elif request.body_type == "binary" and request.body:
            # binary：body 为 base64 data URL，解码后以原始字节发送
            parsed = parse_data_url(request.body)
            if not parsed:
                raise ValueError("binary 请求体解析失败：需要 base64 data URL 格式")
            filename, content, mime = parsed
            headers.setdefault("Content-Type", mime)
            request_kwargs = {"content": content}
        elif request.body_type == "graphql" and request.body:
            # graphql：body 为 {"query": "...", "variables": {...}} JSON
            try:
                gql = json.loads(self.resolve_variables(request.body, variables))
            except json.JSONDecodeError as e:
                raise ValueError(f"GraphQL 请求体不是合法 JSON：{e}")
            if not isinstance(gql, dict) or not gql.get("query"):
                raise ValueError("GraphQL 请求体需要包含 query 字段")
            headers.setdefault("Content-Type", "application/json")
            request_kwargs = {"content": json.dumps(gql, ensure_ascii=False)}
        elif request.body and request.body_type != "none":
            resolved_body = self.resolve_variables(request.body, variables)
            if request.body_type == "json":
                headers.setdefault("Content-Type", "application/json")
                body = resolved_body
            elif request.body_type == "xml":
                headers.setdefault("Content-Type", "application/xml")
                body = resolved_body
            elif request.body_type == "form":
                # form：body 为 urlencoded 字符串，或 JSON 对象转 urlencoded
                content_type = headers.get("Content-Type", "").lower()
                if 'json' not in content_type:
                    headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
                body = resolved_body
            else:  # raw
                body = resolved_body
            request_kwargs = {"content": body if body else None}
        else:
            request_kwargs = {"content": None}

        actual_headers = dict(headers)

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
                    **request_kwargs,
                )

                # 计算响应时间
                response_time = int((time.time() - start_time) * 1000)  # 毫秒

                # 尝试检测内容类型
                content_type = response.headers.get("content-type", "")

                # 尝试解码响应体
                try:
                    body_content = response.text
                except Exception:
                    body_content = response.content.decode("utf-8", errors="replace")

                resp_headers = dict(response.headers)
                result = {
                    "status_code": response.status_code,
                    "status_text": response.reason_phrase or "",
                    "headers": resp_headers,
                    "body": body_content,
                    "response_time": response_time,
                    "size": len(response.content),
                    "content_type": content_type.split(";")[0] if content_type else None,
                    "request_url": str(response.url),
                    "request_headers": actual_headers,
                    "assertion_results": [],
                    "extracted_variables": {},
                    "error": None,
                }

                # 执行后置断言
                try:
                    assertion_results = self._run_assertions(
                        request.assertions or [], variables,
                        response.status_code, resp_headers, body_content, response_time,
                    )
                    result["assertion_results"] = [a.model_dump() for a in assertion_results]
                except Exception as e:
                    logger.error(f"断言执行失败: {e}")

                # 执行后置提取变量（结果写回激活环境）
                try:
                    extracted = self._run_extractions(
                        request.extract_variables or [], variables,
                        response.status_code, resp_headers, body_content, response_time,
                    )
                    result["extracted_variables"] = extracted
                    if extracted:
                        self._persist_extracted_variables(request.workspace_id or "default", extracted)
                except Exception as e:
                    logger.error(f"提取变量执行失败: {e}")

                # 保存历史记录
                try:
                    self._save_request_history(
                        user_id=user_id,
                        method=method,
                        url=url,
                        status_code=response.status_code,
                        response_time=response_time,
                        request_data={
                            "headers": actual_headers,
                            "params": params,
                            "body": request.body,
                            "body_type": request.body_type,
                            "auth_type": request.auth_type,
                        },
                        response_data={
                            "headers": resp_headers,
                            "body": body_content[:10000],  # 限制存储大小
                        },
                        request_id=request.request_id,
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
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    def get_request_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """获取请求历史"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    def delete_request_history(self, user_id: str, history_id: str) -> bool:
        """删除单条请求历史"""
        conn = None
        try:
            conn = get_pooled_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM http_request_history
                    WHERE id = %s AND user_id = %s
                """, (history_id, user_id))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting history: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                release_db_connection(conn)

    def clear_request_history(self, user_id: str) -> bool:
        """清空请求历史"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    # ============= JSON Schema 示例值生成（OpenAPI 导入用） =============

    def _sample_from_schema(self, schema: Dict[str, Any], depth: int = 0) -> Any:
        """从 JSON Schema 生成示例值（用于 OpenAPI 导入时填充请求体）"""
        if depth > 6 or not isinstance(schema, dict):
            return None
        if 'example' in schema:
            return schema['example']
        if 'default' in schema:
            return schema['default']
        if 'enum' in schema and schema['enum']:
            return schema['enum'][0]
        schema_type = schema.get('type')
        if schema_type == 'object' or 'properties' in schema:
            result = {}
            for prop, sub in (schema.get('properties') or {}).items():
                result[prop] = self._sample_from_schema(sub, depth + 1)
            return result
        if schema_type == 'array':
            items = schema.get('items') or {}
            return [self._sample_from_schema(items, depth + 1)]
        if schema_type == 'string':
            fmt = schema.get('format', '')
            if fmt in ('date', 'date-time'):
                return datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ' if fmt == 'date-time' else '%Y-%m-%d')
            if fmt == 'email':
                return 'user@example.com'
            if fmt == 'uuid':
                return str(uuid.uuid4())
            if fmt == 'url' or fmt == 'uri':
                return 'https://example.com'
            return 'string'
        if schema_type == 'integer':
            return 0
        if schema_type == 'number':
            return 0.0
        if schema_type == 'boolean':
            return True
        # 引用解析（$ref）有限支持：本地 #/components/schemas/xxx
        ref = schema.get('$ref', '')
        if ref.startswith('#/') and depth < 5:
            node: Any = {'components': {'schemas': {}}}  # 占位，实际由调用方上下文解析
            return None
        return None

    # ============= Import/Export Methods =============

    def _parse_url_object(self, url_data: Any) -> Tuple[str, List[KeyValueItem]]:
        """解析 Postman url 字段（str 或 object），返回 (raw_url, params)"""
        if isinstance(url_data, str):
            raw = url_data
            params: List[KeyValueItem] = []
            if '?' in raw:
                base, qs = raw.split('?', 1)
                for pair in qs.split('&'):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        params.append(KeyValueItem(key=k, value=v, enabled=True))
            return raw, params

        raw = url_data.get('raw', '')
        params = []
        for q in url_data.get('query', []) or []:
            if not q.get('key'):
                continue
            params.append(KeyValueItem(
                key=q['key'],
                value=q.get('value', ''),
                enabled=not q.get('disabled', False),
                description=q.get('description', '') or '',
            ))
        return raw, params

    def import_postman_collection(self, collection_data: Dict, workspace_id: str = "default") -> Dict:
        """导入 Postman Collection v2.1 格式（支持文件夹嵌套、body、auth）"""
        imported_count = 0
        failed_count = 0
        errors: List[str] = []

        try:
            info = collection_data.get("info", {})
            collection_name = info.get("name", "Imported Collection")
            items = collection_data.get("item", [])

            root = self.create_collection(CollectionCreate(
                name=collection_name,
                description="Imported from Postman",
                workspace_id=workspace_id,
            ))
            if not root:
                return {"success": False, "imported_count": 0,
                        "failed_count": len(items), "errors": ["创建根集合失败"]}

            root_id = root["id"]

            def auth_to_config(auth: Dict) -> Tuple[str, Dict]:
                if not auth:
                    return "none", {}
                t = auth.get('type', '')
                if t == 'bearer':
                    return 'bearer', {'token': auth.get('bearer', [{}])[0].get('token', '') if isinstance(auth.get('bearer'), list) else ''}
                if t == 'basic':
                    fields = {f.get('key'): f.get('value', '') for f in auth.get('basic', [])} if isinstance(auth.get('basic'), list) else {}
                    return 'basic', {'username': fields.get('username', ''), 'password': fields.get('password', '')}
                if t == 'apikey':
                    fields = {f.get('key'): f.get('value', '') for f in auth.get('apikey', [])} if isinstance(auth.get('apikey'), list) else {}
                    return 'apikey', {'key': fields.get('key', ''), 'value': fields.get('value', ''), 'in': fields.get('in', 'header')}
                return "none", {}

            def import_item(item: Dict, target_collection_id: str, idx: int) -> bool:
                nonlocal imported_count, failed_count
                try:
                    # 文件夹：递归创建子集合并导入其中请求
                    if "request" not in item:
                        folder_name = item.get("name", "Folder")
                        sub = self.create_collection(CollectionCreate(
                            name=folder_name,
                            description="Imported folder",
                            workspace_id=workspace_id,
                            parent_id=target_collection_id,
                            sort_order=idx,
                        ))
                        if not sub:
                            raise RuntimeError(f"创建子集合失败: {folder_name}")
                        for sub_idx, child in enumerate(item.get("item", []) or []):
                            import_item(child, sub["id"], sub_idx)
                        return True

                    request_data = item["request"]
                    url, params = self._parse_url_object(request_data.get("url", ""))

                    headers: List[KeyValueItem] = []
                    for h in request_data.get("header", []) or []:
                        if not h.get("key"):
                            continue
                        headers.append(KeyValueItem(
                            key=h["key"], value=h.get("value", ""),
                            enabled=not h.get("disabled", False),
                            description=h.get('description', '') or '',
                        ))

                    body_type = "none"
                    body: Optional[str] = None
                    form_data: List[Dict[str, Any]] = []
                    body_data = request_data.get("body")
                    if body_data:
                        mode = body_data.get("mode")
                        if mode == "raw":
                            options = body_data.get("options") or {}
                            lang = (options.get("raw") or {}).get("language", "text")
                            body_type = "json" if lang == "json" else "raw"
                            body = body_data.get("raw", "")
                        elif mode == "urlencoded":
                            body_type = "form"
                            body = "&".join(
                                f"{u.get('key', '')}={u.get('value', '')}"
                                for u in body_data.get("urlencoded", []) or []
                                if u.get('key')
                            )
                        elif mode == "formdata":
                            body_type = "form-data"
                            for fd in body_data.get("formdata", []) or []:
                                if not fd.get('key'):
                                    continue
                                form_data.append({
                                    'key': fd['key'],
                                    'value': fd.get('value', ''),
                                    'type': fd.get('type', 'text'),
                                    'enabled': not fd.get('disabled', False),
                                    'description': fd.get('description', '') or '',
                                })
                        elif mode == "graphql":
                            body_type = "graphql"
                            gql = {"query": body_data.get("query", ""), "variables": body_data.get("variables", {})}
                            body = json.dumps(gql, ensure_ascii=False)
                        elif mode == "file":
                            body_type = "binary"

                    auth_type, auth_config = auth_to_config(request_data.get("auth"))

                    created = self.create_request(HttpRequestCreate(
                        collection_id=target_collection_id,
                        name=item.get("name", f"Request {idx + 1}"),
                        method=request_data.get("method", "GET"),
                        url=url,
                        headers=kv_to_list_payload(headers),
                        params=kv_to_list_payload(params),
                        body_type=body_type,
                        body=body,
                        form_data=form_data,
                        auth_type=auth_type,
                        auth_config=auth_config,
                        description=item.get("description", "") if isinstance(item.get("description"), str) else "",
                        sort_order=idx,
                    ))
                    if not created:
                        raise RuntimeError("创建请求失败")
                    imported_count += 1
                    return True
                except Exception as e:
                    failed_count += 1
                    errors.append(f"导入条目 {item.get('name', idx + 1)} 失败: {e}")
                    return False

            for idx, item in enumerate(items):
                import_item(item, root_id, idx)

            return {
                "success": True,
                "imported_count": imported_count,
                "failed_count": failed_count,
                "errors": errors,
                "collection_id": root_id,
            }

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return {
                "success": False,
                "imported_count": 0,
                "failed_count": 0,
                "errors": [str(e)],
            }

    def import_openapi_spec(self, spec_text: str, collection_id: str, workspace_id: str = "default") -> Dict:
        """导入 OpenAPI 3.x / Swagger 2.0 规范（JSON 或 YAML）"""
        imported_count = 0
        failed_count = 0
        errors: List[str] = []

        try:
            import yaml
            try:
                spec = json.loads(spec_text)
            except (json.JSONDecodeError, TypeError):
                spec = yaml.safe_load(spec_text)

            if not isinstance(spec, dict):
                return {"success": False, "imported_count": 0,
                        "failed_count": 1, "errors": ["规范格式无法解析"]}

            is_openapi3 = str(spec.get('openapi', '')).startswith('3')
            is_swagger2 = str(spec.get('swagger', '')).startswith('2')
            if not is_openapi3 and not is_swagger2:
                return {"success": False, "imported_count": 0,
                        "failed_count": 1, "errors": ["仅支持 OpenAPI 3.x / Swagger 2.0"]}

            info = spec.get('info', {})
            spec_name = info.get('title', 'Imported OpenAPI')

            # 前置 URL：OAS3 servers[0].url；Swagger2 host+basePath
            if is_openapi3:
                servers = spec.get('servers') or []
                base = servers[0].get('url', '') if servers else ''
            else:
                scheme = (spec.get('schemes') or ['https'])[0]
                base = f"{scheme}://{spec.get('host', '')}{spec.get('basePath', '')}"
            if base and not base.startswith('{{') and not base.startswith('http'):
                base = f"https://{base}"

            # 根集合（按 tag 分组则创建子集合）
            root = self.get_collection(collection_id)
            if not root:
                root = self.create_collection(CollectionCreate(
                    name=spec_name, description="Imported from OpenAPI", workspace_id=workspace_id))
                if not root:
                    return {"success": False, "imported_count": 0,
                            "failed_count": 1, "errors": ["创建根集合失败"]}
                collection_id = root["id"]

            # 解析 $ref
            def resolve_ref(node: Any, depth: int = 0) -> Any:
                if depth > 8 or not isinstance(node, dict):
                    return node
                if '$ref' in node:
                    ref_path = node['$ref']
                    if ref_path.startswith('#/'):
                        target: Any = spec
                        for part in ref_path[2:].split('/'):
                            target = target.get(part) if isinstance(target, dict) else None
                            if target is None:
                                return {}
                        return resolve_ref(target, depth + 1)
                    return {}
                return {k: resolve_ref(v, depth + 1) if isinstance(v, dict) else v
                        for k, v in node.items()}

            HTTP_METHODS_OAS = {'get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace'}

            # 按 tag 分组创建子集合
            tag_collections: Dict[str, str] = {}

            def get_tag_collection(tag: str) -> str:
                if tag in tag_collections:
                    return tag_collections[tag]
                sub = self.create_collection(CollectionCreate(
                    name=tag, description="OpenAPI tag", workspace_id=workspace_id,
                    parent_id=collection_id, sort_order=len(tag_collections)))
                cid = sub["id"] if sub else collection_id
                tag_collections[tag] = cid
                return cid

            paths = spec.get('paths', {}) or {}
            for path, path_item in paths.items():
                if not isinstance(path_item, dict):
                    continue
                # path 级 parameters
                path_level_params = resolve_ref(path_item.get('parameters', []) or [])
                for method in path_item:
                    if method.lower() not in HTTP_METHODS_OAS:
                        continue
                    try:
                        op = resolve_ref(path_item[method])
                        if not isinstance(op, dict):
                            continue

                        name = op.get('summary') or op.get('operationId') or f"{method.upper()} {path}"

                        headers: List[KeyValueItem] = []
                        params: List[KeyValueItem] = []
                        for p in (path_level_params + resolve_ref(op.get('parameters', []) or [])):
                            if not isinstance(p, dict) or not p.get('name'):
                                continue
                            loc = p.get('in', 'query')
                            example = p.get('example', '')
                            if example == '':
                                schema = resolve_ref(p.get('schema', {}) or {})
                                example = schema.get('example', schema.get('default', ''))
                            entry = KeyValueItem(
                                key=p['name'], value=str(example),
                                enabled=True, description=p.get('description', '') or '')
                            if loc == 'query':
                                params.append(entry)
                            elif loc == 'header':
                                headers.append(entry)

                        # URL：{param} 保持占位符原样（发送时可用 {{变量}} 填充）
                        url = f"{base}{path}" if base else path

                        body_type = "none"
                        body: Optional[str] = None
                        request_body = resolve_ref(op.get('requestBody', {}) or {})
                        content = (request_body.get('content') or {}) if isinstance(request_body, dict) else {}
                        for ct, media in content.items():
                            schema = resolve_ref((media or {}).get('schema', {}) or {})
                            if not schema:
                                continue
                            sample = self._sample_from_schema(schema)
                            if 'json' in ct:
                                body_type = 'json'
                                body = json.dumps(sample, ensure_ascii=False, indent=2)
                            elif ct == 'application/x-www-form-urlencoded':
                                body_type = 'form'
                                if isinstance(sample, dict):
                                    body = '&'.join(f"{k}={v}" for k, v in sample.items())
                            elif ct.startswith('multipart/'):
                                body_type = 'form-data'
                            elif ct == 'application/xml':
                                body_type = 'xml'
                                body = str(sample)
                            else:
                                body_type = 'raw'
                                body = str(sample)
                            break

                        auth_type, auth_config = 'none', {}
                        created = self.create_request(HttpRequestCreate(
                            collection_id=get_tag_collection((op.get('tags') or ['未分组'])[0]),
                            name=name[:100],
                            method=method.upper(),
                            url=url,
                            headers=kv_to_list_payload(headers),
                            params=kv_to_list_payload(params),
                            body_type=body_type,
                            body=body,
                            form_data=[],
                            auth_type=auth_type,
                            auth_config=auth_config,
                            description=op.get('description', '') or '',
                            sort_order=imported_count,
                        ))
                        if not created:
                            raise RuntimeError("创建请求失败")
                        imported_count += 1
                    except Exception as e:
                        failed_count += 1
                        errors.append(f"导入 {method.upper()} {path} 失败: {e}")

            return {
                "success": True,
                "imported_count": imported_count,
                "failed_count": failed_count,
                "errors": errors,
                "collection_id": collection_id,
            }
        except Exception as e:
            logger.error(f"OpenAPI import failed: {e}")
            return {"success": False, "imported_count": 0,
                    "failed_count": 1, "errors": [str(e)]}

    def export_collection(self, collection_id: str) -> Dict:
        """导出集合为 Postman Collection v2.1 格式（含子集合、auth、body）"""
        try:
            collection = self.get_collection(collection_id)
            if not collection:
                return {"success": False, "error": "Collection not found"}

            def build_items(cid: str) -> List[Dict]:
                # 子集合
                conn = get_pooled_db_connection()
                children: List[Dict] = []
                try:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("""
                            SELECT id, name, description FROM http_request_collections
                            WHERE parent_id = %s ORDER BY sort_order, created_at
                        """, (cid,))
                        children = cur.fetchall()
                except Exception as e:
                    logger.error(f"查询子集合失败: {e}")
                finally:
                    release_db_connection(conn)

                items: List[Dict] = []
                for child in children:
                    items.append({
                        "name": child["name"],
                        "description": child.get("description", ""),
                        "item": build_items(child["id"]),
                    })

                requests = self.get_requests_by_collection(cid)
                for req in requests:
                    item: Dict[str, Any] = {
                        "name": req["name"],
                        "request": {
                            "method": req["method"],
                            "url": {"raw": req["url"], "query": [
                                {"key": p.get("key", ""), "value": p.get("value", ""), "disabled": not p.get("enabled", True)}
                                for p in (req.get("params") or []) if isinstance(p, dict) and p.get("key")
                            ]},
                            "header": [
                                {"key": h.get("key", ""), "value": h.get("value", ""), "disabled": not h.get("enabled", True)}
                                for h in (req.get("headers") or []) if isinstance(h, dict) and h.get("key")
                            ],
                        },
                        "response": [],
                    }
                    if req.get("description"):
                        item["request"]["description"] = req["description"]

                    body_type = req.get("body_type")
                    body_value = req.get("body")
                    if body_type == "json" and body_value:
                        item["request"]["body"] = {
                            "mode": "raw", "raw": body_value,
                            "options": {"raw": {"language": "json"}},
                        }
                    elif body_type in ("raw", "xml") and body_value:
                        item["request"]["body"] = {"mode": "raw", "raw": body_value}
                    elif body_type == "form" and body_value:
                        urlencoded = []
                        for pair in str(body_value).split('&'):
                            if '=' in pair:
                                k, v = pair.split('=', 1)
                                urlencoded.append({"key": k, "value": v})
                        item["request"]["body"] = {"mode": "urlencoded", "urlencoded": urlencoded}
                    elif body_type == "form-data":
                        formdata = []
                        for fd in (req.get("form_data") or []):
                            if isinstance(fd, dict) and fd.get('key'):
                                formdata.append({
                                    "key": fd['key'], "value": fd.get('value', ''),
                                    "type": fd.get('type', 'text'), "disabled": not fd.get('enabled', True),
                                })
                        if formdata:
                            item["request"]["body"] = {"mode": "formdata", "formdata": formdata}
                    elif body_type == "graphql" and body_value:
                        try:
                            gql = json.loads(body_value)
                            item["request"]["body"] = {
                                "mode": "graphql",
                                "graphql": {"query": gql.get("query", ""), "variables": gql.get("variables", {})},
                            }
                        except Exception:
                            pass

                    auth_type = req.get("auth_type")
                    auth_config = req.get("auth_config") or {}
                    if auth_type == "bearer":
                        item["request"]["auth"] = {"type": "bearer", "bearer": [
                            {"key": "token", "value": auth_config.get("token", "")}]}
                    elif auth_type == "basic":
                        item["request"]["auth"] = {"type": "basic", "basic": [
                            {"key": "username", "value": auth_config.get("username", "")},
                            {"key": "password", "value": auth_config.get("password", "")},
                        ]}
                    elif auth_type == "apikey":
                        item["request"]["auth"] = {"type": "apikey", "apikey": [
                            {"key": "key", "value": auth_config.get("key", "")},
                            {"key": "value", "value": auth_config.get("value", "")},
                            {"key": "in", "value": auth_config.get("in", "header")},
                        ]}

                    items.append(item)
                return items

            postman_collection = {
                "info": {
                    "name": collection["name"],
                    "description": collection.get("description", ""),
                    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                    "_postman_id": collection["id"],
                },
                "item": build_items(collection_id),
            }
            return {"success": True, "data": postman_collection}

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {"success": False, "error": str(e)}


# 单例
http_client_service = HttpClientService()
