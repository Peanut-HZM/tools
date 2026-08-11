"""kubeconfig 解析器测试"""
import pytest
import yaml
from app.utils.k8s_config_parser import parse_kubeconfig, ParsedContext, KubeconfigParseError


MINIMAL_KUBECONFIG = {
    "apiVersion": "v1",
    "kind": "Config",
    "clusters": [
        {
            "name": "prod-cluster",
            "cluster": {"server": "https://k8s.prod.example.com:6443", "certificate-authority-data": "LS0tLS1..."},
        }
    ],
    "contexts": [
        {
            "name": "prod",
            "context": {"cluster": "prod-cluster", "user": "admin", "namespace": "default"},
        }
    ],
    "users": [
        {
            "name": "admin",
            "user": {"token": "eyJhbGciOi..."},
        }
    ],
    "current-context": "prod",
}


def _dump(obj) -> str:
    return yaml.safe_dump(obj)


def test_parse_single_context_bearer_token():
    """单 context + bearer token"""
    result = parse_kubeconfig(_dump(MINIMAL_KUBECONFIG))
    assert len(result.contexts) == 1
    ctx = result.contexts[0]
    assert ctx.context_name == "prod"
    assert ctx.cluster_name == "prod-cluster"
    assert ctx.server == "https://k8s.prod.example.com:6443"
    assert ctx.auth_type == "bearer_token"
    assert ctx.token == "eyJhbGciOi..."
    assert ctx.ca_cert is not None


def test_parse_multiple_contexts():
    """多 context 拆分成多条"""
    kc = {
        **MINIMAL_KUBECONFIG,
        "clusters": [
            {"name": "prod", "cluster": {"server": "https://prod:6443"}},
            {"name": "dev", "cluster": {"server": "https://dev:6443"}},
        ],
        "contexts": [
            {"name": "prod-ctx", "context": {"cluster": "prod", "user": "admin"}},
            {"name": "dev-ctx", "context": {"cluster": "dev", "user": "admin"}},
        ],
    }
    result = parse_kubeconfig(_dump(kc))
    assert len(result.contexts) == 2
    names = {c.context_name for c in result.contexts}
    assert names == {"prod-ctx", "dev-ctx"}


def test_parse_client_cert_auth():
    """client-certificate-data + client-key-data → auth_type=client_cert"""
    kc = {
        **MINIMAL_KUBECONFIG,
        "users": [
            {
                "name": "admin",
                "user": {
                    "client-certificate-data": "Y2VydC1kYXRh",
                    "client-key-data": "a2V5LWRhdGE=",
                },
            }
        ],
    }
    result = parse_kubeconfig(_dump(kc))
    ctx = result.contexts[0]
    assert ctx.auth_type == "client_cert"
    assert ctx.client_cert == "cert-data"
    assert ctx.client_key == "key-data"


def test_parse_basic_auth():
    """username + password → auth_type=basic_auth"""
    kc = {
        **MINIMAL_KUBECONFIG,
        "users": [
            {"name": "admin", "user": {"username": "alice", "password": "s3cret"}},
        ],
    }
    result = parse_kubeconfig(_dump(kc))
    ctx = result.contexts[0]
    assert ctx.auth_type == "basic_auth"
    assert ctx.username == "alice"
    assert ctx.password == "s3cret"


def test_parse_empty_raises():
    """空 kubeconfig 抛错"""
    with pytest.raises(KubeconfigParseError):
        parse_kubeconfig("")


def test_parse_invalid_yaml_raises():
    """非法 YAML 抛错"""
    with pytest.raises(KubeconfigParseError):
        parse_kubeconfig("{{invalid:: yaml")


def test_parse_missing_clusters_raises():
    """缺少 clusters 字段抛错"""
    with pytest.raises(KubeconfigParseError, match="clusters"):
        parse_kubeconfig(_dump({"apiVersion": "v1", "kind": "Config", "contexts": [], "users": []}))


def test_parse_context_with_missing_cluster_graceful():
    """context 引用了不存在的 cluster → 跳过该 context（记录 warning）"""
    kc = {
        **MINIMAL_KUBECONFIG,
        "contexts": [
            {"name": "orphan", "context": {"cluster": "nonexistent", "user": "admin"}},
            {"name": "valid", "context": {"cluster": "prod-cluster", "user": "admin"}},
        ],
    }
    result = parse_kubeconfig(_dump(kc))
    assert len(result.contexts) == 1
    assert result.contexts[0].context_name == "valid"


def test_parse_ca_cert_base64_decoded():
    """CA 证书被 base64 解码"""
    import base64
    raw_ca = "-----BEGIN CERTIFICATE-----\nMIIBxx...\n-----END CERTIFICATE-----\n"
    kc = {
        **MINIMAL_KUBECONFIG,
        "clusters": [
            {
                "name": "prod-cluster",
                "cluster": {
                    "server": "https://k8s.prod.example.com:6443",
                    "certificate-authority-data": base64.b64encode(raw_ca.encode()).decode(),
                },
            }
        ],
    }
    result = parse_kubeconfig(_dump(kc))
    ctx = result.contexts[0]
    assert ctx.ca_cert == raw_ca
