import uuid
import logging
import redis
import json
import time
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from app.config.database import get_db_connection
from app.models.redis_tool_models import (
    RedisConfigBase, CreateRedisRequest, UpdateRedisRequest,
    RedisConfigResponse, TestConnectionRequest, ConnectionTestResult,
    RedisKeyInfo, RedisKeyContent, KeyOperationRequest, RedisKeyType,
    KeysScanRequest, KeysScanResponse, KeyTTLRequest, KeyExportRequest,
    KeyExportResponse, KeyImportRequest, KeyImportResponse, LuaScriptRequest,
    LuaScriptResponse, ScriptTemplate, CreateScriptTemplateRequest,
    UpdateScriptTemplateRequest, CLICommandRequest, CLICommandResponse
)
from app.utils.encryption import EncryptionUtils

logger = logging.getLogger(__name__)

class RedisToolService:
    _column_map = None

    @staticmethod
    def _ensure_table():
        """确保 redis_configs 和 redis_script_templates 表存在"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Create redis_configs table if not exists
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS redis_configs (
                    id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    alias VARCHAR(64) NOT NULL,
                    host VARCHAR(255) NOT NULL,
                    port INT NOT NULL DEFAULT 6379,
                    username VARCHAR(128),
                    password_encrypted TEXT,
                    db INT DEFAULT 0,
                    group_name VARCHAR(64),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    deleted BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_redis_configs_user_id ON redis_configs(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_redis_configs_user_alias ON redis_configs(user_id, alias)")

            # Create redis_script_templates table if not exists
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS redis_script_templates (
                    id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    name VARCHAR(128) NOT NULL,
                    description TEXT,
                    script TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_redis_script_templates_user_id ON redis_script_templates(user_id)")

            conn.commit()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def _get_column_map():
        """获取列名映射（兼容不同版本的表结构）"""
        if RedisToolService._column_map:
            return RedisToolService._column_map
        RedisToolService._ensure_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'redis_configs'"
            )
            columns = {row['column_name'] for row in cursor.fetchall()}
        finally:
            cursor.close()
            conn.close()
        def pick(preferred: str, fallback: str):
            if preferred in columns:
                return preferred
            if fallback in columns:
                return fallback
            return preferred
        RedisToolService._column_map = {
            "deleted": pick("deleted", "is_deleted"),
            "password": pick("password_encrypted", "password")
        }
        return RedisToolService._column_map
    
    @staticmethod
    def _row_to_response(row) -> RedisConfigResponse:
        return RedisConfigResponse(
            id=row['id'],
            user_id=row['user_id'],
            alias=row['alias'],
            host=row['host'],
            port=row['port'],
            username=row['username'],
            db=row['db'],
            group_name=row['group_name'],
            is_active=row['is_active'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    @staticmethod
    def get_all_configs(user_id: str) -> List[RedisConfigResponse]:
        RedisToolService._ensure_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            column_map = RedisToolService._get_column_map()
            deleted_column = column_map["deleted"]
            cursor.execute(
                f"SELECT * FROM redis_configs WHERE user_id = %s AND {deleted_column} = FALSE ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [RedisToolService._row_to_response(row) for row in rows]
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_config(user_id: str, request: CreateRedisRequest) -> RedisConfigResponse:
        RedisToolService._ensure_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            column_map = RedisToolService._get_column_map()
            deleted_column = column_map["deleted"]
            config_id = str(uuid.uuid4())
            password_encrypted = EncryptionUtils.encrypt(request.password) if request.password else None

            cursor.execute(
                f"""
                INSERT INTO redis_configs
                (id, user_id, alias, host, port, username, password_encrypted, db, group_name, is_active, created_at, updated_at, {deleted_column})
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, FALSE)
                """,
                (
                    config_id, user_id, request.alias, request.host, request.port,
                    request.username, password_encrypted, request.db, request.group_name, request.is_active
                )
            )
            conn.commit()

            # Fetch created config
            cursor.execute("SELECT * FROM redis_configs WHERE id = %s", (config_id,))
            row = cursor.fetchone()
            return RedisToolService._row_to_response(row)
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create redis config: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_config(config_id: str, user_id: str) -> Optional[RedisConfigResponse]:
        RedisToolService._ensure_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            column_map = RedisToolService._get_column_map()
            deleted_column = column_map["deleted"]
            cursor.execute(
                f"SELECT * FROM redis_configs WHERE id = %s AND user_id = %s AND {deleted_column} = FALSE",
                (config_id, user_id)
            )
            row = cursor.fetchone()
            if row:
                return RedisToolService._row_to_response(row)
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def _get_config_with_password(config_id: str, user_id: str):
        RedisToolService._ensure_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            column_map = RedisToolService._get_column_map()
            deleted_column = column_map["deleted"]
            cursor.execute(
                f"SELECT * FROM redis_configs WHERE id = %s AND user_id = %s AND {deleted_column} = FALSE",
                (config_id, user_id)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update_config(config_id: str, user_id: str, request: UpdateRedisRequest) -> Optional[RedisConfigResponse]:
        RedisToolService._ensure_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            column_map = RedisToolService._get_column_map()
            deleted_column = column_map["deleted"]
            # Check existence
            cursor.execute(
                f"SELECT * FROM redis_configs WHERE id = %s AND user_id = %s AND {deleted_column} = FALSE",
                (config_id, user_id)
            )
            if not cursor.fetchone():
                return None
                
            update_fields = []
            params = []
            
            if request.alias is not None:
                update_fields.append("alias = %s")
                params.append(request.alias)
            if request.host is not None:
                update_fields.append("host = %s")
                params.append(request.host)
            if request.port is not None:
                update_fields.append("port = %s")
                params.append(request.port)
            if request.username is not None:
                update_fields.append("username = %s")
                params.append(request.username)
            if request.password is not None:
                update_fields.append("password_encrypted = %s")
                params.append(EncryptionUtils.encrypt(request.password))
            if request.db is not None:
                update_fields.append("db = %s")
                params.append(request.db)
            if request.group_name is not None:
                update_fields.append("group_name = %s")
                params.append(request.group_name)
            if request.is_active is not None:
                update_fields.append("is_active = %s")
                params.append(request.is_active)
                
            if not update_fields:
                return RedisToolService.get_config(config_id, user_id)
                
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(config_id)
            params.append(user_id)
            
            sql = f"UPDATE redis_configs SET {', '.join(update_fields)} WHERE id = %s AND user_id = %s"
            cursor.execute(sql, tuple(params))
            conn.commit()
            
            return RedisToolService.get_config(config_id, user_id)
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update redis config: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def delete_config(config_id: str, user_id: str) -> bool:
        RedisToolService._ensure_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            column_map = RedisToolService._get_column_map()
            deleted_column = column_map["deleted"]
            cursor.execute(
                f"UPDATE redis_configs SET {deleted_column} = TRUE WHERE id = %s AND user_id = %s",
                (config_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete redis config: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def _get_redis_client(host, port, password=None, username=None, db=0, decode_responses=True):
        return redis.Redis(
            host=host,
            port=port,
            username=username,
            password=password,
            db=db,
            decode_responses=decode_responses,
            socket_connect_timeout=5
        )

    @staticmethod
    def test_connection(request: TestConnectionRequest) -> ConnectionTestResult:
        start_time = datetime.now()
        try:
            r = RedisToolService._get_redis_client(
                host=request.host,
                port=request.port,
                username=request.username,
                password=request.password,
                db=request.db
            )
            r.ping()
            info = r.info()
            version = info.get('redis_version', 'unknown')
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            
            return ConnectionTestResult(
                success=True,
                message="Connection successful",
                elapsed_ms=elapsed,
                version=version
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=str(e)
            )

    @staticmethod
    def test_connection_by_id(config_id: str, user_id: str) -> ConnectionTestResult:
        config_row = RedisToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            return ConnectionTestResult(success=False, message="Configuration not found")
            
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted']) if config_row['password_encrypted'] else None
        except Exception:
            return ConnectionTestResult(success=False, message="Failed to decrypt password")
            
        request = TestConnectionRequest(
            host=config_row['host'],
            port=config_row['port'],
            username=config_row['username'],
            password=password,
            db=config_row['db']
        )
        return RedisToolService.test_connection(request)

    @staticmethod
    def _get_client_by_id(config_id: str, user_id: str, decode_responses=True):
        config_row = RedisToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
            
        password = EncryptionUtils.decrypt(config_row['password_encrypted']) if config_row['password_encrypted'] else None
        
        return RedisToolService._get_redis_client(
            host=config_row['host'],
            port=config_row['port'],
            username=config_row['username'],
            password=password,
            db=config_row['db'],
            decode_responses=decode_responses
        )

    @staticmethod
    def get_keys(config_id: str, user_id: str, pattern: str = "*") -> List[RedisKeyInfo]:
        try:
            r = RedisToolService._get_client_by_id(config_id, user_id)
            # Use scan_iter instead of keys for better performance and safety
            # Limit to 1000 keys to prevent UI freezing and timeouts
            keys = []
            count = 0
            MAX_KEYS = 1000
            
            for key in r.scan_iter(match=pattern, count=100):
                keys.append(key)
                count += 1
                if count >= MAX_KEYS:
                    break
            
            if not keys:
                return []
                
            result = []
            
            # Using pipeline for better performance
            pipe = r.pipeline()
            for key in keys:
                pipe.type(key)
                pipe.ttl(key)
                
            responses = pipe.execute()
            
            # Group responses: type, ttl per key
            for i, key in enumerate(keys):
                key_type = responses[i*2]
                ttl = responses[i*2+1]
                result.append(RedisKeyInfo(
                    key=key,
                    type=key_type,
                    ttl=ttl
                ))
                
            return result
        except Exception as e:
            logger.error(f"Failed to get keys: {e}")
            raise e

    @staticmethod
    def _safe_decode(val):
        """Recursively decode bytes to string, fallback to repr for binary"""
        if isinstance(val, bytes):
            try:
                return val.decode('utf-8')
            except UnicodeDecodeError:
                # Return repr for binary data, or maybe base64? 
                # For now, let's use repr so it's visible that it's binary
                return str(val)
        elif isinstance(val, list):
            return [RedisToolService._safe_decode(v) for v in val]
        elif isinstance(val, dict):
            return {RedisToolService._safe_decode(k): RedisToolService._safe_decode(v) for k, v in val.items()}
        elif isinstance(val, tuple):
             return tuple(RedisToolService._safe_decode(v) for v in val)
        return val

    @staticmethod
    def get_key_content(config_id: str, user_id: str, key: str) -> RedisKeyContent:
        try:
            # Use raw client to handle potential binary data
            r = RedisToolService._get_client_by_id(config_id, user_id, decode_responses=False)
            
            # Key type check (returns bytes)
            key_type_bytes = r.type(key)
            key_type = key_type_bytes.decode('utf-8') if isinstance(key_type_bytes, bytes) else str(key_type_bytes)
            
            ttl = r.ttl(key)
            value = None
            
            if key_type == 'string':
                value = r.get(key)
            elif key_type == 'list':
                value = r.lrange(key, 0, -1)
            elif key_type == 'set':
                value = list(r.smembers(key))
            elif key_type == 'zset':
                value = r.zrange(key, 0, -1, withscores=True)
            elif key_type == 'hash':
                value = r.hgetall(key)
            
            # Decode safely
            decoded_value = RedisToolService._safe_decode(value)
            
            return RedisKeyContent(
                key=key,
                type=key_type,
                ttl=ttl,
                value=decoded_value
            )
        except Exception as e:
            logger.error(f"Failed to get key content: {e}")
            raise e

    @staticmethod
    def set_key(config_id: str, user_id: str, request: KeyOperationRequest) -> bool:
        try:
            r = RedisToolService._get_client_by_id(config_id, user_id)
            
            if request.type == RedisKeyType.STRING:
                r.set(request.key, request.value)
            elif request.type == RedisKeyType.LIST:
                r.delete(request.key)
                if isinstance(request.value, list):
                    r.rpush(request.key, *request.value)
            elif request.type == RedisKeyType.SET:
                r.delete(request.key)
                if isinstance(request.value, list):
                    r.sadd(request.key, *request.value)
            elif request.type == RedisKeyType.HASH:
                if isinstance(request.value, dict):
                    r.hmset(request.key, request.value)
            elif request.type == RedisKeyType.ZSET:
                r.delete(request.key)
                # Expecting list of [value, score] or {value: score}
                if isinstance(request.value, dict):
                    r.zadd(request.key, request.value)
                elif isinstance(request.value, list):
                    # Handle list of tuples/lists
                    mapping = {item[0]: item[1] for item in request.value}
                    r.zadd(request.key, mapping)

            if request.ttl is not None and request.ttl >= 0:
                r.expire(request.key, request.ttl)
                
            return True
        except Exception as e:
            logger.error(f"Failed to set key: {e}")
            raise e

    @staticmethod
    def delete_keys(config_id: str, user_id: str, keys: List[str]) -> int:
        try:
            r = RedisToolService._get_client_by_id(config_id, user_id)
            return r.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to delete keys: {e}")
            raise e

    @staticmethod
    def batch_update_ttl(config_id: str, user_id: str, keys: List[str], ttl: int) -> int:
        """批量更新 key 的 TTL"""
        try:
            r = RedisToolService._get_client_by_id(config_id, user_id)
            updated = 0
            for key in keys:
                if ttl == -1:
                    if r.persist(key):
                        updated += 1
                else:
                    if r.expire(key, ttl):
                        updated += 1
            return updated
        except Exception as e:
            logger.error(f"Failed to batch update TTL: {e}")
            raise e

    @staticmethod
    def batch_rename(config_id: str, user_id: str, keys: List[str], pattern: str, replacement: str) -> int:
        """批量重命名 key，pattern 支持 * 通配符"""
        import fnmatch
        try:
            r = RedisToolService._get_client_by_id(config_id, user_id)
            renamed = 0
            for key in keys:
                if fnmatch.fnmatch(key, pattern):
                    # 简单替换：将 pattern 匹配的部分替换为 replacement
                    # pattern 如 "user:*"，key 如 "user:123"，replacement 如 "member:*"
                    if "*" in pattern:
                        parts = pattern.split("*")
                        if len(parts) == 2:
                            prefix, suffix = parts[0], parts[1]
                            if key.startswith(prefix) and (not suffix or key.endswith(suffix)):
                                middle = key[len(prefix):]
                                if suffix:
                                    middle = middle[:-len(suffix)]
                                new_key = replacement.replace("*", middle)
                            else:
                                continue
                        else:
                            new_key = replacement
                    else:
                        new_key = key.replace(pattern, replacement, 1)
                    if r.rename(key, new_key):
                        renamed += 1
            return renamed
        except Exception as e:
            logger.error(f"Failed to batch rename: {e}")
            raise e

    @staticmethod
    def update_key_ttl(config_id: str, user_id: str, request: KeyTTLRequest) -> bool:
        """更新 Key 的 TTL"""
        try:
            r = RedisToolService._get_client_by_id(config_id, user_id)
            if request.ttl == -1:
                # 移除 TTL
                return r.persist(request.key)
            else:
                # 设置 TTL
                return r.expire(request.key, request.ttl)
        except Exception as e:
            logger.error(f"Failed to update key TTL: {e}")
            raise e

    @staticmethod
    def persist_key(config_id: str, user_id: str, key: str) -> bool:
        """移除 Key 的 TTL"""
        try:
            r = RedisToolService._get_client_by_id(config_id, user_id)
            return r.persist(key)
        except Exception as e:
            logger.error(f"Failed to persist key: {e}")
            raise e

    @staticmethod
    def scan_keys(config_id: str, user_id: str, request: KeysScanRequest) -> KeysScanResponse:
        """分页扫描 Keys，支持类型过滤"""
        try:
            r = RedisToolService._get_client_by_id(config_id, user_id, decode_responses=True)

            # 使用 SCAN 命令迭代
            cursor = 0
            all_keys = []
            count = request.count

            # 如果有传入 cursor，从该位置继续
            if request.cursor > 0:
                cursor = request.cursor

            # 扫描获取 keys
            while len(all_keys) < count:
                result = r.scan(cursor=cursor, match=request.pattern, count=min(count * 2, 100))
                cursor, keys = result

                if request.key_type:
                    # 按类型过滤
                    for key in keys:
                        try:
                            key_type = r.type(key)
                            if key_type == request.key_type:
                                all_keys.append(key)
                        except:
                            continue
                else:
                    all_keys.extend(keys)

                if cursor == 0:
                    break

            # 获取每个 key 的详细信息
            keys_info = []
            for key in all_keys[:count]:
                try:
                    key_type = r.type(key)
                    ttl = r.ttl(key)
                    keys_info.append(RedisKeyInfo(key=key, type=key_type, ttl=ttl))
                except:
                    continue

            return KeysScanResponse(
                cursor=cursor,
                keys=keys_info,
                has_more=cursor != 0
            )
        except Exception as e:
            logger.error(f"Failed to scan keys: {e}")
            raise e

    @staticmethod
    def get_key_memory_usage(config_id: str, user_id: str, key: str) -> int:
        """获取 Key 的内存使用"""
        try:
            r = RedisToolService._get_client_by_id(config_id, user_id)
            return r.memory_usage(key) or 0
        except Exception as e:
            logger.error(f"Failed to get key memory usage: {e}")
            return 0

    @staticmethod
    def export_keys(config_id: str, user_id: str, request: KeyExportRequest) -> KeyExportResponse:
        """导出 Key 数据"""
        try:
            r = RedisToolService._get_client_by_id(config_id, user_id, decode_responses=False)
            exported_data = {}

            for key in request.keys:
                try:
                    key_type = r.type(key)
                    value = None

                    if key_type == b'string':
                        value = r.get(key)
                    elif key_type == b'list':
                        value = r.lrange(key, 0, -1)
                    elif key_type == b'set':
                        value = list(r.smembers(key))
                    elif key_type == b'zset':
                        value = r.zrange(key, 0, -1, withscores=True)
                    elif key_type == b'hash':
                        value = r.hgetall(key)

                    # 解码字节数据
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8')
                        except:
                            value = value.hex()
                    elif isinstance(value, list):
                        value = [v.decode('utf-8') if isinstance(v, bytes) else v for v in value]
                    elif isinstance(value, dict):
                        value = {k.decode('utf-8') if isinstance(k, bytes) else k:
                                v.decode('utf-8') if isinstance(v, bytes) else v
                                for k, v in value.items()}

                    exported_data[key] = {
                        'type': key_type.decode('utf-8') if isinstance(key_type, bytes) else key_type,
                        'value': value
                    }
                except Exception as e:
                    logger.error(f"Failed to export key {key}: {e}")
                    exported_data[key] = {'error': str(e)}

            return KeyExportResponse(
                data=json.dumps(exported_data, indent=2, ensure_ascii=False),
                count=len(request.keys)
            )
        except Exception as e:
            logger.error(f"Failed to export keys: {e}")
            raise e

    @staticmethod
    def import_keys(config_id: str, user_id: str, request: KeyImportRequest) -> KeyImportResponse:
        """导入 Key 数据"""
        try:
            r = RedisToolService._get_client_by_id(config_id, user_id, decode_responses=True)
            errors = []
            success_count = 0
            failed_count = 0

            data = json.loads(request.data)

            for key, key_data in data.items():
                try:
                    # 检查是否已存在
                    if not request.overwrite and r.exists(key):
                        errors.append({'key': key, 'error': 'Key already exists'})
                        failed_count += 1
                        continue

                    key_type = key_data.get('type', 'string')
                    value = key_data.get('value')

                    # 删除已存在的 key
                    if r.exists(key):
                        r.delete(key)

                    # 根据类型设置值
                    if key_type == 'string':
                        r.set(key, value)
                    elif key_type == 'list':
                        if isinstance(value, list):
                            r.rpush(key, *value)
                    elif key_type == 'set':
                        if isinstance(value, list):
                            r.sadd(key, *value)
                    elif key_type == 'zset':
                        if isinstance(value, list):
                            mapping = {item[0]: item[1] for item in value} if isinstance(value[0], list) else {}
                            if mapping:
                                r.zadd(key, mapping)
                    elif key_type == 'hash':
                        if isinstance(value, dict):
                            r.hmset(key, value)

                    success_count += 1
                except Exception as e:
                    errors.append({'key': key, 'error': str(e)})
                    failed_count += 1

            return KeyImportResponse(
                success_count=success_count,
                failed_count=failed_count,
                errors=errors
            )
        except Exception as e:
            logger.error(f"Failed to import keys: {e}")
            raise e

    @staticmethod
    def execute_lua_script(config_id: str, user_id: str, request: LuaScriptRequest) -> LuaScriptResponse:
        """执行 Lua 脚本"""
        try:
            r = RedisToolService._get_client_by_id(config_id, user_id)

            start_time = time.time()

            # 注册脚本并执行
            result = r.eval(request.script, len(request.keys), *request.keys, *request.args)

            execution_time = (time.time() - start_time) * 1000

            return LuaScriptResponse(
                result=result,
                execution_time_ms=execution_time
            )
        except Exception as e:
            logger.error(f"Failed to execute lua script: {e}")
            raise e

    # Script Template Management
    @staticmethod
    def get_script_templates(user_id: str) -> List[ScriptTemplate]:
        """获取用户的脚本模板列表"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM redis_script_templates WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [ScriptTemplate(**row) for row in rows]
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_script_template(user_id: str, request: CreateScriptTemplateRequest) -> ScriptTemplate:
        """创建脚本模板"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            template_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO redis_script_templates (id, user_id, name, description, script, created_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (template_id, user_id, request.name, request.description, request.script)
            )
            conn.commit()

            return ScriptTemplate(
                id=template_id,
                user_id=user_id,
                name=request.name,
                description=request.description,
                script=request.script,
                created_at=datetime.now()
            )
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create script template: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update_script_template(template_id: str, user_id: str, request: UpdateScriptTemplateRequest) -> bool:
        """更新脚本模板"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            updates = []
            params = []

            if request.name is not None:
                updates.append("name = %s")
                params.append(request.name)
            if request.description is not None:
                updates.append("description = %s")
                params.append(request.description)
            if request.script is not None:
                updates.append("script = %s")
                params.append(request.script)

            if not updates:
                return True

            params.append(template_id)
            params.append(user_id)

            cursor.execute(
                f"UPDATE redis_script_templates SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s",
                tuple(params)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update script template: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def delete_script_template(template_id: str, user_id: str) -> bool:
        """删除脚本模板"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM redis_script_templates WHERE id = %s AND user_id = %s",
                (template_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete script template: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def execute_cli_command(config_id: str, user_id: str, request: CLICommandRequest) -> CLICommandResponse:
        """执行 Redis CLI 命令"""
        try:
            r = RedisToolService._get_client_by_id(config_id, user_id)

            start_time = time.time()

            # 解析命令
            parts = request.command.strip().split()
            if not parts:
                return CLICommandResponse(
                    result=None,
                    error="Empty command",
                    execution_time_ms=0
                )

            cmd = parts[0].upper()
            args = parts[1:] if len(parts) > 1 else []

            # 执行命令
            result = r.execute_command(cmd, *args)

            execution_time = (time.time() - start_time) * 1000

            # 处理结果
            if isinstance(result, bytes):
                result = result.decode('utf-8')
            elif isinstance(result, list):
                result = [item.decode('utf-8') if isinstance(item, bytes) else item for item in result]

            return CLICommandResponse(
                result=result,
                error=None,
                execution_time_ms=execution_time
            )
        except Exception as e:
            logger.error(f"Failed to execute CLI command: {e}")
            return CLICommandResponse(
                result=None,
                error=str(e),
                execution_time_ms=0
            )
