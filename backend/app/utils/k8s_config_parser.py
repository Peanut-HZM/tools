"""
kubeconfig 文件解析器

将 kubeconfig YAML 文本解析为 ParsedContext 列表，
每个 context 对应一条独立的连接配置。
"""
import base64
import logging
from dataclasses import dataclass, field
from typing import List, Optional

import yaml

logger = logging.getLogger(__name__)


class KubeconfigParseError(Exception):
    """kubeconfig 解析错误"""


@dataclass
class ParsedContext:
    """从 kubeconfig 解析出的单个 context 连接信息"""
    context_name: str
    cluster_name: str
    server: str
    auth_type: str                   # 'bearer_token' | 'client_cert' | 'basic_auth'
    # bearer_token
    token: Optional[str] = None
    # client_cert
    client_cert: Optional[str] = None
    client_key: Optional[str] = None
    # basic_auth
    username: Optional[str] = None
    password: Optional[str] = None
    # CA
    ca_cert: Optional[str] = None
    # 默认 namespace
    namespace: Optional[str] = None


@dataclass
class ParsedKubeconfig:
    """kubeconfig 解析结果"""
    contexts: List[ParsedContext] = field(default_factory=list)


def _b64decode_optional(value: Optional[str]) -> Optional[str]:
    """Base64 解码，None 或空字符串返回 None"""
    if not value:
        return None
    try:
        return base64.b64decode(value).decode("utf-8")
    except Exception:
        return value  # 非 base64 原文直接返回


def parse_kubeconfig(text: str) -> ParsedKubeconfig:
    """
    解析 kubeconfig YAML 文本，返回 ParsedKubeconfig。

    - 每个 context → 一条 ParsedContext
    - 自动根据 user 字段推断 auth_type
    - 跳过引用了不存在 cluster 的 context（记录 warning）
    """
    if not text or not text.strip():
        raise KubeconfigParseError("kubeconfig 内容为空")

    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise KubeconfigParseError(f"YAML 解析失败: {e}") from e

    if not isinstance(doc, dict):
        raise KubeconfigParseError("kubeconfig 必须是 YAML 对象")

    clusters_list = doc.get("clusters") or []
    contexts_list = doc.get("contexts") or []
    users_list = doc.get("users") or []

    if not clusters_list:
        raise KubeconfigParseError("kubeconfig 缺少 'clusters' 字段")

    # 构建 cluster name → cluster data 映射
    clusters_by_name = {}
    for c in clusters_list:
        if isinstance(c, dict) and "name" in c:
            clusters_by_name[c["name"]] = c.get("cluster") or {}

    # 构建 user name → user data 映射
    users_by_name = {}
    for u in users_list:
        if isinstance(u, dict) and "name" in u:
            users_by_name[u["name"]] = u.get("user") or {}

    # 解析每个 context
    parsed_contexts: List[ParsedContext] = []
    skipped_auth_errors: List[str] = []

    for ctx_entry in contexts_list:
        if not isinstance(ctx_entry, dict):
            continue
        ctx_name = ctx_entry.get("name")
        ctx_data = ctx_entry.get("context") or {}
        if not ctx_name:
            continue

        cluster_name = ctx_data.get("cluster")
        user_name = ctx_data.get("user")
        namespace = ctx_data.get("namespace")

        # 校验 cluster 引用
        if not cluster_name or cluster_name not in clusters_by_name:
            logger.warning(
                f"Context '{ctx_name}' 引用了不存在的 cluster '{cluster_name}'，跳过"
            )
            continue

        cluster_data = clusters_by_name[cluster_name]
        server = cluster_data.get("server", "")
        if not server:
            logger.warning(f"Context '{ctx_name}' 的 cluster 缺少 server 字段，跳过")
            continue

        ca_cert = _b64decode_optional(cluster_data.get("certificate-authority-data"))

        # 解析 auth
        user_data = users_by_name.get(user_name, {}) if user_name else {}
        try:
            auth_type, token, client_cert, client_key, username, password = _resolve_auth(user_data)
        except KubeconfigParseError as e:
            # exec/auth-provider 插件不支持，记录并跳过该 context
            logger.warning(f"Context '{ctx_name}' 认证方式不支持: {e}")
            skipped_auth_errors.append(f"{ctx_name}: {e}")
            continue

        parsed_contexts.append(ParsedContext(
            context_name=ctx_name,
            cluster_name=cluster_name,
            server=server,
            auth_type=auth_type,
            token=token,
            client_cert=client_cert,
            client_key=client_key,
            username=username,
            password=password,
            ca_cert=ca_cert,
            namespace=namespace,
        ))

    if not parsed_contexts:
        if skipped_auth_errors:
            # 所有 context 都因认证方式不支持而跳过
            raise KubeconfigParseError(
                f"该 kubeconfig 中的所有 context 使用了暂不支持的认证方式：\n"
                + "\n".join(skipped_auth_errors)
                + "\n\n请使用 token、客户端证书或用户名密码方式创建连接。"
            )
        else:
            raise KubeconfigParseError("未解析出任何有效的 context")

    return ParsedKubeconfig(contexts=parsed_contexts)


def _resolve_auth(user_data: dict) -> tuple:
    """
    根据 user data 字段推断 auth_type 和对应凭据。

    Returns: (auth_type, token, client_cert, client_key, username, password)
    Raises: KubeconfigParseError 如果使用 exec 或 auth-provider 插件
    """
    # 检测 exec 插件（如 aws eks get-token, gcloud config config-helper 等）
    if "exec" in user_data:
        exec_config = user_data["exec"]
        command = exec_config.get("command", "")
        raise KubeconfigParseError(
            f"该 kubeconfig 使用 exec 认证插件（command: {command}），暂不支持。"
            f"请使用 token、客户端证书或用户名密码方式创建连接。"
        )

    # 检测 auth-provider 插件（如 gcp, azure, oidc 等）
    if "auth-provider" in user_data:
        provider_name = user_data["auth-provider"].get("name", "")
        raise KubeconfigParseError(
            f"该 kubeconfig 使用 auth-provider 认证插件（provider: {provider_name}），暂不支持。"
            f"请使用 token、客户端证书或用户名密码方式创建连接。"
        )

    # 优先级：token > client_cert > basic_auth
    token = user_data.get("token")
    if token:
        return ("bearer_token", token, None, None, None, None)

    client_cert_data = user_data.get("client-certificate-data")
    client_key_data = user_data.get("client-key-data")
    if client_cert_data and client_key_data:
        return (
            "client_cert",
            None,
            _b64decode_optional(client_cert_data),
            _b64decode_optional(client_key_data),
            None,
            None,
        )

    username = user_data.get("username")
    password = user_data.get("password")
    if username and password:
        return ("basic_auth", None, None, None, username, password)

    # 兜底：无认证信息，也当作 bearer_token 但 token 为空
    return ("bearer_token", token, None, None, None, None)
