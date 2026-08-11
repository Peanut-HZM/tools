"""
K8s 控制台工具 Service

连接配置 CRUD + kubeconfig 解析 + 连通性测试。
遵循项目模式：psycopg2 原生 SQL + Pydantic DTO + 静态方法。
"""
import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from app.config.database import get_pooled_db_connection, release_db_connection
from app.models.k8s_tool_models import (
    CreateK8sManualRequest,
    UpdateK8sRequest,
    UpdateK8sAuthRequest,
    K8sConfigResponse,
)
from app.utils.encryption import EncryptionUtils
from app.utils.k8s_config_parser import parse_kubeconfig, ParsedContext

logger = logging.getLogger(__name__)


class K8sToolService:
    """K8s 连接配置管理服务（所有方法均为 @staticmethod）"""

    # ============ 表初始化 ============

    @staticmethod
    def _ensure_table():
        """创建 k8s_connections 表（幂等，可重复执行）"""
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS k8s_connections (
                    id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    name VARCHAR(128) NOT NULL,
                    source_type VARCHAR(32) NOT NULL,
                    cluster_name VARCHAR(255) NOT NULL,
                    context_name VARCHAR(255) NOT NULL,
                    server VARCHAR(512) NOT NULL,
                    auth_type VARCHAR(32) NOT NULL,
                    auth_data_encrypted TEXT,
                    ca_cert_encrypted TEXT,
                    namespace_filter TEXT DEFAULT '[]',
                    is_metrics_available BOOLEAN DEFAULT FALSE,
                    last_test_at TIMESTAMP,
                    last_test_error TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    sort_order INTEGER DEFAULT 0,
                    deleted BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_k8s_conn_user "
                "ON k8s_connections(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_k8s_conn_user_deleted "
                "ON k8s_connections(user_id, deleted)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_k8s_conn_user_sort "
                "ON k8s_connections(user_id, sort_order, name)"
            )
            # 兼容已存在的表：添加 sort_order 字段
            cursor.execute("""
                ALTER TABLE k8s_connections
                ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0
            """)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)

    # ============ CRUD ============

    @staticmethod
    def get_configs(user_id: str) -> List[K8sConfigResponse]:
        """获取当前用户的所有连接配置（脱敏，不含敏感字段原文）"""
        K8sToolService._ensure_table()
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM k8s_connections "
                "WHERE user_id = %s AND deleted = FALSE "
                "ORDER BY sort_order ASC, name ASC",
                (user_id,),
            )
            rows = cursor.fetchall()
            return [K8sToolService._row_to_response(row) for row in rows]
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def update_sort_order(
        user_id: str, config_ids: List[str]
    ) -> None:
        """批量更新连接配置的排序顺序"""
        K8sToolService._ensure_table()
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            for idx, config_id in enumerate(config_ids):
                cursor.execute(
                    "UPDATE k8s_connections "
                    "SET sort_order = %s, updated_at = %s "
                    "WHERE id = %s AND user_id = %s AND deleted = FALSE",
                    (idx, datetime.now(), config_id, user_id),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def create_config(
        user_id: str, request: CreateK8sManualRequest
    ) -> K8sConfigResponse:
        """手动创建单条连接配置（敏感字段加密存储）"""
        K8sToolService._ensure_table()
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            config_id = str(uuid.uuid4())
            now = datetime.now()

            # 加密敏感字段：auth_data（token/cert/password 等）和 ca_cert
            auth_data = K8sToolService._build_auth_data(request)
            auth_data_encrypted = (
                EncryptionUtils.encrypt(json.dumps(auth_data)) if auth_data else None
            )
            ca_cert_encrypted = (
                EncryptionUtils.encrypt(request.ca_cert) if request.ca_cert else None
            )

            cursor.execute(
                """INSERT INTO k8s_connections
                   (id, user_id, name, source_type, cluster_name, context_name, server,
                    auth_type, auth_data_encrypted, ca_cert_encrypted, namespace_filter,
                    created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    config_id,
                    user_id,
                    request.name,
                    "manual",
                    request.name,       # cluster_name 默认使用显示名
                    request.name,       # context_name 默认使用显示名
                    request.server,
                    request.auth_type,
                    auth_data_encrypted,
                    ca_cert_encrypted,
                    json.dumps(request.namespace_filter),
                    now,
                    now,
                ),
            )
            conn.commit()

            # 查回刚插入的行，构建脱敏响应
            cursor.execute(
                "SELECT * FROM k8s_connections WHERE id = %s", (config_id,)
            )
            row = cursor.fetchone()
            return K8sToolService._row_to_response(row)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def create_from_kubeconfig(
        user_id: str,
        kubeconfig_text: str,
        namespace_filter: Optional[List[str]] = None,
    ) -> List[K8sConfigResponse]:
        """从 kubeconfig 文本批量创建连接配置（每个 context 一条）"""
        parsed = parse_kubeconfig(kubeconfig_text)
        results = []
        for ctx in parsed.contexts:
            req = K8sToolService._parsed_context_to_manual_request(
                ctx, namespace_filter or []
            )
            results.append(K8sToolService.create_config(user_id, req))
        return results

    @staticmethod
    def update_config(
        user_id: str, request: UpdateK8sRequest
    ) -> K8sConfigResponse:
        """更新连接配置（仅允许修改 name / namespace_filter）"""
        K8sToolService._ensure_table()
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            update_fields = ["updated_at = %s"]
            params: list = [datetime.now()]

            if request.name is not None:
                update_fields.append("name = %s")
                params.append(request.name)
            if request.namespace_filter is not None:
                update_fields.append("namespace_filter = %s")
                params.append(json.dumps(request.namespace_filter))

            params.extend([request.id, user_id])

            cursor.execute(
                f"UPDATE k8s_connections SET {', '.join(update_fields)} "
                "WHERE id = %s AND user_id = %s AND deleted = FALSE",
                params,
            )
            conn.commit()

            if cursor.rowcount == 0:
                raise ValueError("连接配置不存在或无权操作")

            cursor.execute(
                "SELECT * FROM k8s_connections WHERE id = %s", (request.id,)
            )
            row = cursor.fetchone()
            return K8sToolService._row_to_response(row)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def update_config_auth(
        user_id: str, request: UpdateK8sAuthRequest
    ) -> K8sConfigResponse:
        """更新连接的认证信息（仅更新提供的字段）"""
        K8sToolService._ensure_table()
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            # 检查配置是否存在并获取 auth_type
            cursor.execute(
                "SELECT id, auth_type FROM k8s_connections "
                "WHERE id = %s AND user_id = %s AND deleted = FALSE",
                (request.id, user_id),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("连接配置不存在或无权操作")

            auth_type = row['auth_type']
            update_fields = ["updated_at = %s"]
            params: list = [datetime.now()]

            # 收集认证数据更新
            auth_data_updates = {}
            if auth_type == 'bearer_token' and request.token:
                auth_data_updates['token'] = request.token
            if auth_type == 'client_cert':
                if request.client_cert:
                    auth_data_updates['client_cert'] = request.client_cert
                if request.client_key:
                    auth_data_updates['client_key'] = request.client_key
            if auth_type == 'basic_auth':
                if request.username:
                    auth_data_updates['username'] = request.username
                if request.password:
                    auth_data_updates['password'] = request.password

            # 如果有认证数据更新
            if auth_data_updates:
                cursor.execute(
                    "SELECT auth_data_encrypted FROM k8s_connections WHERE id = %s",
                    (request.id,),
                )
                existing_row = cursor.fetchone()
                if existing_row and existing_row['auth_data_encrypted']:
                    existing_decrypted = EncryptionUtils.decrypt(existing_row['auth_data_encrypted'])
                    existing_data = json.loads(existing_decrypted)
                    existing_data.update(auth_data_updates)
                    auth_data_encrypted = EncryptionUtils.encrypt(json.dumps(existing_data))
                else:
                    auth_data_encrypted = EncryptionUtils.encrypt(json.dumps(auth_data_updates))

                update_fields.append("auth_data_encrypted = %s")
                params.append(auth_data_encrypted)

            # CA 证书更新
            if request.ca_cert:
                ca_cert_encrypted = EncryptionUtils.encrypt(request.ca_cert)
                update_fields.append("ca_cert_encrypted = %s")
                params.append(ca_cert_encrypted)

            params.extend([request.id, user_id])

            cursor.execute(
                f"UPDATE k8s_connections SET {', '.join(update_fields)} "
                "WHERE id = %s AND user_id = %s AND deleted = FALSE",
                params,
            )
            conn.commit()

            if cursor.rowcount == 0:
                raise ValueError("连接配置不存在或无权操作")

            # 返回更新后的配置
            cursor.execute("SELECT * FROM k8s_connections WHERE id = %s", (request.id,))
            row = cursor.fetchone()
            return K8sToolService._row_to_response(row)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def update_test_result(
        config_id: str,
        success: bool,
        error: Optional[str] = None,
        metrics_available: bool = False,
    ) -> None:
        """更新连接测试结果"""
        K8sToolService._ensure_table()
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE k8s_connections
                SET last_test_at = %s,
                    last_test_error = %s,
                    is_metrics_available = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    datetime.now(),
                    error if not success else None,
                    metrics_available,
                    datetime.now(),
                    config_id,
                ),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"更新测试结果失败: {e}")
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def delete_config(user_id: str, config_id: str) -> bool:
        """软删除连接配置（SET deleted = TRUE，保留数据用于审计）"""
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE k8s_connections SET deleted = TRUE, updated_at = %s "
                "WHERE id = %s AND user_id = %s AND deleted = FALSE",
                (datetime.now(), config_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def get_config_by_id(user_id: str, config_id: str) -> Optional[dict]:
        """
        获取配置完整记录（含加密字段）。
        仅供内部使用（如建立 K8s 连接时解密凭据），不对外暴露。
        """
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM k8s_connections "
                "WHERE id = %s AND user_id = %s AND deleted = FALSE",
                (config_id, user_id),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            release_db_connection(conn)

    # ============ 内部辅助方法 ============

    @staticmethod
    def _build_auth_data(request: CreateK8sManualRequest) -> dict:
        """根据 auth_type 构建待加密的认证数据 dict"""
        if request.auth_type == "bearer_token":
            return {"token": request.token} if request.token else {}
        if request.auth_type == "client_cert":
            return {
                "client_cert": request.client_cert,
                "client_key": request.client_key,
            }
        if request.auth_type == "basic_auth":
            return {"username": request.username, "password": request.password}
        return {}

    @staticmethod
    def _parsed_context_to_manual_request(
        ctx: ParsedContext, namespace_filter: List[str]
    ) -> CreateK8sManualRequest:
        """将 ParsedContext 转换为 CreateK8sManualRequest（kubeconfig 批量导入用）"""
        return CreateK8sManualRequest(
            name=f"{ctx.cluster_name} / {ctx.context_name}",
            server=ctx.server,
            auth_type=ctx.auth_type,
            token=ctx.token,
            client_cert=ctx.client_cert,
            client_key=ctx.client_key,
            username=ctx.username,
            password=ctx.password,
            ca_cert=ctx.ca_cert,
            namespace_filter=namespace_filter,
        )

    @staticmethod
    def _row_to_response(row) -> K8sConfigResponse:
        """
        数据库行 → Pydantic 响应 DTO（脱敏）。
        auth_data_encrypted / ca_cert_encrypted 不直接返回，
        只通过 has_auth_data / has_ca_cert 布尔标志告知前端是否已配置。
        """
        ns_filter_raw = row.get("namespace_filter", "[]")
        try:
            ns_filter = (
                json.loads(ns_filter_raw) if isinstance(ns_filter_raw, str) else []
            )
        except (json.JSONDecodeError, TypeError):
            ns_filter = []

        return K8sConfigResponse(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            source_type=row["source_type"],
            cluster_name=row["cluster_name"],
            context_name=row["context_name"],
            server=row["server"],
            auth_type=row["auth_type"],
            has_auth_data=bool(row.get("auth_data_encrypted")),
            has_ca_cert=bool(row.get("ca_cert_encrypted")),
            namespace_filter=ns_filter,
            is_metrics_available=row.get("is_metrics_available", False),
            last_test_at=row.get("last_test_at"),
            last_test_error=row.get("last_test_error"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
