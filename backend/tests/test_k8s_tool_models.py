"""K8s 工具 Pydantic DTO 模型测试"""
import pytest
from app.models.k8s_tool_models import (
    CreateK8sManualRequest,
    CreateK8sPasteRequest,
    UpdateK8sRequest,
    K8sConfigResponse,
    K8sConnectionHealth,
    K8sError,
)


def test_create_manual_request_minimal():
    """手动创建请求需要必填字段"""
    req = CreateK8sManualRequest(
        name="my-cluster",
        server="https://k8s.example.com:6443",
        auth_type="bearer_token",
        token="xxx",
    )
    assert req.name == "my-cluster"
    assert req.auth_type == "bearer_token"
    assert req.ca_cert is None


def test_create_manual_request_client_cert():
    """client_cert 模式需要 cert + key"""
    req = CreateK8sManualRequest(
        name="cert-cluster",
        server="https://k8s.example.com:6443",
        auth_type="client_cert",
        client_cert="---BEGIN CERT---",
        client_key="---BEGIN KEY---",
    )
    assert req.token is None
    assert req.client_cert is not None


def test_create_paste_request():
    """粘贴 kubeconfig 文本"""
    req = CreateK8sPasteRequest(kubeconfig_text="apiVersion: v1\nclusters: []")
    assert "apiVersion" in req.kubeconfig_text


def test_create_paste_request_size_limit():
    """超过 1MB 的 kubeconfig 被拒绝"""
    huge = "x" * (1_048_576 + 1)
    with pytest.raises(Exception):  # pydantic ValidationError
        CreateK8sPasteRequest(kubeconfig_text=huge)


def test_k8s_config_response_masks_secrets():
    """响应模型不包含敏感字段原文"""
    resp = K8sConfigResponse(
        id="abc",
        user_id="u1",
        name="prod",
        source_type="manual",
        cluster_name="prod-cluster",
        context_name="prod-ctx",
        server="https://k8s.example.com:6443",
        auth_type="bearer_token",
        has_auth_data=True,
        has_ca_cert=False,
        namespace_filter=[],
        is_metrics_available=True,
        last_test_at=None,
        last_test_error=None,
        created_at="2026-08-10T00:00:00",
        updated_at="2026-08-10T00:00:00",
    )
    assert resp.has_auth_data is True
    # 响应中没有 auth_data_encrypted 字段
    assert not hasattr(resp, "auth_data_encrypted")


def test_k8s_error_model():
    """K8s 错误模型"""
    err = K8sError(
        code="FORBIDDEN",
        message="当前配置无权限访问该资源",
        k8s_reason="Forbidden",
        status_code=403,
    )
    assert err.code == "FORBIDDEN"
