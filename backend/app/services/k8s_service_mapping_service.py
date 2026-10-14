"""K8s 服务定位映射服务

记录「本地项目 → 集群/命名空间/容器」定位记忆，实现首次发现后永久命中。
安全：仅平台元数据读写，绝不触碰集群资源；按 user_id 隔离；UPSERT 幂等。
"""
import logging
import uuid
from datetime import datetime
from typing import Optional

from app.config.database import get_pooled_db_connection, release_db_connection

logger = logging.getLogger(__name__)

VALID_SOURCES = {"jenkinsfile", "config_file", "traversal", "user_confirmed"}
_table_ready = False


class K8sServiceMappingService:
    """服务定位映射（@staticmethod）"""

    @staticmethod
    def _ensure_table():
        """创建 k8s_service_mappings 表（幂等）"""
        global _table_ready
        if _table_ready:
            return
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS k8s_service_mappings (
                    id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    project_key VARCHAR(100) NOT NULL,
                    cluster_id VARCHAR(64) NOT NULL,
                    namespace VARCHAR(100) NOT NULL,
                    deployment VARCHAR(200),
                    container VARCHAR(200),
                    evidence TEXT NOT NULL DEFAULT '',
                    source VARCHAR(30) NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    UNIQUE (user_id, project_key)
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_k8s_svc_map_user "
                "ON k8s_service_mappings(user_id)"
            )
            conn.commit()
            _table_ready = True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def save_mapping(user_id: str, project_key: str, cluster_id: str, namespace: str,
                     deployment: Optional[str], container: Optional[str],
                     evidence: str, source: str) -> dict:
        """保存/覆盖更新映射（同 user_id + project_key 幂等）"""
        if source not in VALID_SOURCES:
            raise ValueError(f"非法 source: {source}，允许值 {sorted(VALID_SOURCES)}")
        K8sServiceMappingService._ensure_table()
        mapping_id = uuid.uuid4().hex
        now = datetime.now()
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO k8s_service_mappings
                    (id, user_id, project_key, cluster_id, namespace, deployment,
                     container, evidence, source, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, project_key) DO UPDATE SET
                    cluster_id = EXCLUDED.cluster_id,
                    namespace = EXCLUDED.namespace,
                    deployment = EXCLUDED.deployment,
                    container = EXCLUDED.container,
                    evidence = EXCLUDED.evidence,
                    source = EXCLUDED.source,
                    updated_at = EXCLUDED.updated_at
                RETURNING id, user_id, project_key, cluster_id, namespace, deployment,
                          container, evidence, source, created_at, updated_at
                """,
                (mapping_id, user_id, project_key, cluster_id, namespace,
                 deployment, container, evidence, source, now, now),
            )
            row = cursor.fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)
        logger.info("用户 %s 保存服务定位映射 %s → 集群 %s/%s（来源 %s）",
                    user_id, project_key, cluster_id, namespace, source)
        return dict(row)

    @staticmethod
    def lookup_mapping(user_id: str, project_key: str) -> Optional[dict]:
        """查询映射；附带集群名（连接可能已删除，cluster_name 可为 None）"""
        K8sServiceMappingService._ensure_table()
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT m.project_key, m.cluster_id, c.name AS cluster_name,
                       m.namespace, m.deployment, m.container,
                       m.evidence, m.source, m.updated_at
                FROM k8s_service_mappings m
                LEFT JOIN k8s_connections c ON c.id = m.cluster_id
                WHERE m.user_id = %s AND m.project_key = %s
                """,
                (user_id, project_key),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
            release_db_connection(conn)
        return dict(row) if row else None
