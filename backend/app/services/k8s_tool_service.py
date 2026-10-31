"""
K8s 控制台工具 Service

连接配置 CRUD + kubeconfig 解析 + 连通性测试。
遵循项目模式：Repository 双存储读写 + Pydantic DTO + 静态方法。
"""
import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from app.models.k8s_tool_models import (
    CreateK8sManualRequest,
    UpdateK8sRequest,
    UpdateK8sAuthRequest,
    K8sConfigResponse,
)
from app.utils.k8s_config_parser import parse_kubeconfig, ParsedContext

logger = logging.getLogger(__name__)


class K8sToolService:
    """K8s 连接配置管理服务（所有方法均为 @staticmethod）"""

    # ============ CRUD ============

    @staticmethod
    def get_configs(user_id: str) -> List[K8sConfigResponse]:
        """获取当前用户的所有连接配置（合并本地 + 服务器，脱敏）"""
        from app.storage.locator import StorageLocation, server_available
        from app.storage.repository import get_repository

        rows: list[dict] = []

        try:
            rows.extend(
                get_repository(StorageLocation.LOCAL, "k8s").list(user_id)
            )
        except Exception as exc:
            logger.warning("读取本地 K8s 配置失败：%s", exc)

        available, _ = server_available()
        if available:
            try:
                rows.extend(
                    get_repository(StorageLocation.SERVER, "k8s").list(user_id)
                )
            except Exception as exc:
                logger.warning("读取服务器 K8s 配置失败：%s", exc)

        rows.sort(key=lambda r: (r.get("sort_order", 0), r.get("name", "")))
        return [K8sToolService._row_to_response(row) for row in rows]

    @staticmethod
    def _locate(user_id: str, config_id: str):
        """定位配置所在位置与仓储；找不到返回 (None, None)"""
        from app.storage.locator import StorageLocation
        from app.storage.repository import get_repository

        for location in (StorageLocation.LOCAL, StorageLocation.SERVER):
            try:
                repo = get_repository(location, "k8s")
            except Exception:
                continue
            if repo.get(config_id, user_id):
                return repo, location
        return None, None

    @staticmethod
    def update_sort_order(
        user_id: str, config_ids: List[str]
    ) -> None:
        """批量更新连接配置的排序顺序（逐条定位所在存储位置）"""
        for idx, config_id in enumerate(config_ids):
            repo, location = K8sToolService._locate(user_id, config_id)
            if repo is None:
                continue
            repo.update(config_id, user_id, {"sort_order": idx}, location)

    @staticmethod
    def create_config(
        user_id: str,
        request: CreateK8sManualRequest,
        storage_location: "StorageLocation",
    ) -> K8sConfigResponse:
        """手动创建单条连接配置（敏感字段按存储位置加密）"""
        from app.storage.repository import get_repository

        repo = get_repository(storage_location, "k8s")
        config_id = str(uuid.uuid4())
        now = datetime.now()

        auth_data = K8sToolService._build_auth_data(request)
        payload = {
            "id": config_id,
            "name": request.name,
            "source_type": "manual",
            "cluster_name": request.name,
            "context_name": request.name,
            "server": request.server,
            "auth_type": request.auth_type,
            "namespace_filter": json.dumps(request.namespace_filter),
            "created_at": now,
            "updated_at": now,
        }
        # 敏感字段用目标仓储的密钥加密（本地用本地密钥，远程用服务器密钥）
        if auth_data:
            payload["auth_data_encrypted"] = repo._encrypt(json.dumps(auth_data))
        if request.ca_cert:
            payload["ca_cert_encrypted"] = repo._encrypt(request.ca_cert)

        repo.create(user_id, payload, storage_location)

        row = repo.get(config_id, user_id)
        if row is None:
            raise RuntimeError("K8s 配置创建后无法读回")
        return K8sToolService._row_to_response(row)

    @staticmethod
    def create_from_kubeconfig(
        user_id: str,
        kubeconfig_text: str,
        namespace_filter: Optional[List[str]] = None,
        storage_location: "StorageLocation" = None,
    ) -> List[K8sConfigResponse]:
        """从 kubeconfig 文本批量创建连接配置（每个 context 一条，落在同一存储位置）"""
        from app.storage.locator import StorageLocation

        if storage_location is None:
            storage_location = StorageLocation.LOCAL

        parsed = parse_kubeconfig(kubeconfig_text)
        results = []
        for ctx in parsed.contexts:
            req = K8sToolService._parsed_context_to_manual_request(
                ctx, namespace_filter or []
            )
            results.append(
                K8sToolService.create_config(user_id, req, storage_location)
            )
        return results

    @staticmethod
    def update_config(
        user_id: str,
        request: UpdateK8sRequest,
        storage_location: "StorageLocation | None" = None,
    ) -> K8sConfigResponse:
        """更新连接配置（仅允许修改 name / namespace_filter）"""
        if storage_location is not None:
            # 显式指定存储位置：直接用对应仓储
            from app.storage.repository import get_repository

            repo = get_repository(storage_location, "k8s")
            location = storage_location
        else:
            # 未指定：自动定位配置当前所在位置
            repo, location = K8sToolService._locate(user_id, request.id)
        if repo is None:
            raise ValueError(f"K8s 配置不存在：{request.id}")

        updates: dict = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.namespace_filter is not None:
            updates["namespace_filter"] = json.dumps(request.namespace_filter)

        updated = repo.update(request.id, user_id, updates, location)
        if updated is None:
            raise ValueError(f"K8s 配置不存在：{request.id}")
        return K8sToolService._row_to_response(updated)

    @staticmethod
    def update_config_auth(
        user_id: str,
        request: UpdateK8sAuthRequest,
        storage_location: "StorageLocation | None" = None,
    ) -> K8sConfigResponse:
        """更新连接的认证信息（仅更新提供的字段）"""
        if storage_location is not None:
            # 显式指定存储位置：直接用对应仓储
            from app.storage.repository import get_repository

            repo = get_repository(storage_location, "k8s")
            location = storage_location
        else:
            repo, location = K8sToolService._locate(user_id, request.id)
        if repo is None:
            raise ValueError(f"K8s 配置不存在：{request.id}")

        # 读取现有配置与已解密的认证数据（auth_type 决定更新哪些字段）
        row = repo.get_with_secret(request.id, user_id)
        if row is None:
            raise ValueError(f"K8s 配置不存在：{request.id}")

        auth_type = row["auth_type"]
        auth_data_updates: dict = {}
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

        updates: dict = {}
        if auth_data_updates:
            # 合并进已解密的认证数据后整体重加密
            existing_raw = row.get("auth_data_decrypted")
            if existing_raw:
                existing_data = json.loads(existing_raw)
                existing_data.update(auth_data_updates)
                merged = existing_data
            else:
                merged = auth_data_updates
            updates["auth_data_encrypted"] = repo._encrypt(json.dumps(merged))

        if request.ca_cert:
            updates["ca_cert_encrypted"] = repo._encrypt(request.ca_cert)

        updated = repo.update(request.id, user_id, updates, location)
        if updated is None:
            raise ValueError(f"K8s 配置不存在：{request.id}")
        return K8sToolService._row_to_response(updated)

    @staticmethod
    def update_test_result(
        user_id: str,
        config_id: str,
        success: bool,
        error: Optional[str] = None,
        metrics_available: bool = False,
    ) -> None:
        """更新连接测试结果（写入配置所在存储位置）"""
        repo, location = K8sToolService._locate(user_id, config_id)
        if repo is None:
            logger.warning("更新测试结果失败，配置不存在：%s", config_id)
            return
        try:
            repo.update(
                config_id,
                user_id,
                {
                    "last_test_at": datetime.now(),
                    "last_test_error": error if not success else None,
                    "is_metrics_available": metrics_available,
                },
                location,
            )
        except Exception as e:
            logger.error(f"更新测试结果失败: {e}")

    @staticmethod
    def delete_config(user_id: str, config_id: str) -> bool:
        """软删除连接配置（本地为硬删除，服务器侧由仓储决定）"""
        repo, _location = K8sToolService._locate(user_id, config_id)
        if repo is None:
            return False
        return repo.delete(config_id, user_id)

    @staticmethod
    def get_config_by_id(user_id: str, config_id: str) -> Optional[dict]:
        """
        获取配置完整记录（自动定位存储位置，含加密字段）。
        仅供内部使用（如建立 K8s 连接时解密凭据），不对外暴露。
        """
        repo, _location = K8sToolService._locate(user_id, config_id)
        if repo is None:
            return None
        return repo.get(config_id, user_id)

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

        # 落库为大写 LOCAL/SERVER，对外统一小写
        storage_location = str(row.get("storage_location") or "server").lower()

        return K8sConfigResponse(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            source_type=row["source_type"],
            cluster_name=row["cluster_name"],
            context_name=row["context_name"],
            server=row["server"],
            auth_type=row["auth_type"],
            storage_location=storage_location,
            has_auth_data=bool(row.get("auth_data_encrypted")),
            has_ca_cert=bool(row.get("ca_cert_encrypted")),
            namespace_filter=ns_filter,
            is_metrics_available=row.get("is_metrics_available", False),
            last_test_at=row.get("last_test_at"),
            last_test_error=row.get("last_test_error"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
