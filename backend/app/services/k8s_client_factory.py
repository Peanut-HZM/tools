"""
K8s API 客户端工厂

按需从 DB 解密配置 → 构造 kubernetes_asyncio.ApiClient → 用完自动释放。
使用 asynccontextmanager 模式，确保临时文件和连接在退出时清理。
"""
import json
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional

import kubernetes_asyncio
import kubernetes_asyncio.client as k8s_client

from app.utils.encryption import EncryptionUtils

logger = logging.getLogger(__name__)


@dataclass
class ClientBundle:
    """K8s API 客户端集合，包含常用 API 分组实例"""
    core_v1: k8s_client.CoreV1Api
    apps_v1: k8s_client.AppsV1Api
    batch_v1: k8s_client.BatchV1Api
    custom_objects: k8s_client.CustomObjectsApi
    _api_client: k8s_client.ApiClient  # 内部引用，用于关闭时释放连接


def _write_temp_file(content: str, suffix: str) -> str:
    """将内容写入临时文件，返回文件路径。调用方负责清理。"""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return f.name


def _safe_unlink(path: Optional[str]) -> None:
    """安全删除临时文件，忽略文件不存在等 OSError。"""
    if not path:
        return
    try:
        os.unlink(path)
    except OSError:
        pass


@asynccontextmanager
async def build_client(config: dict):
    """
    根据数据库配置记录构造 K8s 客户端。

    使用方式：
        async with build_client(config_dict) as bundle:
            pods = await bundle.core_v1.list_pod_for_all_namespaces()

    Args:
        config: 数据库行 dict，必须包含以下字段：
            - server: K8s API Server 地址（如 https://k8s.example.com:6443）
            - auth_type: 认证类型，支持 bearer_token / client_cert / basic_auth
            - auth_data_encrypted: 加密后的认证数据（JSON 字符串）
            - ca_cert_encrypted: 加密后的 CA 证书内容（可选，为 None 时使用系统 CA）

    Yields:
        ClientBundle: 包含 core_v1 / apps_v1 / batch_v1 / custom_objects API 实例

    Raises:
        ValueError: 当 auth_data_encrypted 缺失或解密后不是合法 JSON 时
    """
    # 1. 解密 auth_data
    auth_data_encrypted = config.get("auth_data_encrypted")
    if not auth_data_encrypted:
        raise ValueError("auth_data_encrypted is missing，无法构造 K8s 客户端")

    auth_data_raw = EncryptionUtils.decrypt(auth_data_encrypted)
    try:
        auth_data = json.loads(auth_data_raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"auth_data 解密后不是合法 JSON: {e}") from e

    # 2. 解密 CA 证书（可选）
    ca_cert_encrypted = config.get("ca_cert_encrypted")
    ca_cert = EncryptionUtils.decrypt(ca_cert_encrypted) if ca_cert_encrypted else None

    # 3. 构造 kubernetes_asyncio Configuration
    k8s_config = k8s_client.Configuration()
    k8s_config.host = config["server"]

    # 记录需要清理的临时文件路径
    temp_ca_path: Optional[str] = None
    temp_cert_path: Optional[str] = None
    temp_key_path: Optional[str] = None

    try:
        # CA 证书处理
        if ca_cert:
            temp_ca_path = _write_temp_file(ca_cert, ".crt")
            k8s_config.ssl_ca_cert = temp_ca_path
            logger.debug("已写入临时 CA 证书文件: %s", temp_ca_path)
        else:
            # 无自定义 CA，使用系统 CA 验证
            k8s_config.verify_ssl = True

        # 认证处理
        auth_type = config.get("auth_type", "bearer_token")

        if auth_type == "bearer_token":
            token = auth_data.get("token")
            if not token:
                raise ValueError("auth_type=bearer_token 但 token 字段为空")
            # kubernetes_asyncio 的 auth_settings() 方法只识别 key 为 "BearerToken" 的项，
            # 识别后会自动构造 Authorization: Bearer <token> header
            k8s_config.api_key = {"BearerToken": token}
            logger.debug("使用 bearer_token 认证模式")

        elif auth_type == "client_cert":
            cert_data = auth_data.get("client_cert")
            key_data = auth_data.get("client_key")
            if not cert_data or not key_data:
                raise ValueError("auth_type=client_cert 但 client_cert/client_key 不完整")
            temp_cert_path = _write_temp_file(cert_data, ".crt")
            temp_key_path = _write_temp_file(key_data, ".key")
            k8s_config.cert_file = temp_cert_path
            k8s_config.key_file = temp_key_path
            logger.debug("使用 client_cert 认证模式，临时文件已写入")

        elif auth_type == "basic_auth":
            k8s_config.username = auth_data.get("username")
            k8s_config.password = auth_data.get("password")
            logger.debug("使用 basic_auth 认证模式")

        else:
            raise ValueError(f"不支持的 auth_type: {auth_type}")

        # 4. 创建 ApiClient
        api_client = k8s_client.ApiClient(configuration=k8s_config)

        try:
            # 5. 构造各 API 分组实例
            bundle = ClientBundle(
                core_v1=k8s_client.CoreV1Api(api_client),
                apps_v1=k8s_client.AppsV1Api(api_client),
                batch_v1=k8s_client.BatchV1Api(api_client),
                custom_objects=k8s_client.CustomObjectsApi(api_client),
                _api_client=api_client,
            )
            logger.info("K8s 客户端构造成功，server=%s, auth_type=%s", config["server"], auth_type)
            yield bundle

        finally:
            # 6. 关闭 ApiClient（释放 HTTP 连接池）
            await api_client.close()
            logger.debug("ApiClient 已关闭")

    finally:
        # 7. 清理所有临时文件（CA 证书、客户端证书、私钥）
        _safe_unlink(temp_ca_path)
        _safe_unlink(temp_cert_path)
        _safe_unlink(temp_key_path)
        if temp_ca_path or temp_cert_path or temp_key_path:
            logger.debug("临时证书文件已清理")
