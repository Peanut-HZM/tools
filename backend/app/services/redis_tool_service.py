import uuid
import logging
import redis
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.config.database import get_db_connection
from app.models.redis_tool_models import (
    RedisConfigBase, CreateRedisRequest, UpdateRedisRequest, 
    RedisConfigResponse, TestConnectionRequest, ConnectionTestResult,
    RedisKeyInfo, RedisKeyContent, KeyOperationRequest, RedisKeyType
)
from app.utils.encryption import EncryptionUtils

logger = logging.getLogger(__name__)

class RedisToolService:
    
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
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM redis_configs WHERE user_id = %s AND deleted = FALSE ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [RedisToolService._row_to_response(row) for row in rows]
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_config(user_id: str, request: CreateRedisRequest) -> RedisConfigResponse:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            config_id = str(uuid.uuid4())
            password_encrypted = EncryptionUtils.encrypt(request.password) if request.password else None
            
            cursor.execute(
                """
                INSERT INTO redis_configs 
                (id, user_id, alias, host, port, username, password_encrypted, db, group_name, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM redis_configs WHERE id = %s AND user_id = %s AND deleted = FALSE",
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
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM redis_configs WHERE id = %s AND user_id = %s AND deleted = FALSE",
                (config_id, user_id)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update_config(config_id: str, user_id: str, request: UpdateRedisRequest) -> Optional[RedisConfigResponse]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check existence
            cursor.execute(
                "SELECT * FROM redis_configs WHERE id = %s AND user_id = %s AND deleted = FALSE",
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
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE redis_configs SET deleted = TRUE WHERE id = %s AND user_id = %s",
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
