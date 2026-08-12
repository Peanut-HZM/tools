"""K8s 资源查询 Service 测试"""
import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from kubernetes_asyncio.client import ApiException
from app.services.k8s_resource_service import K8sResourceService, _api_exception_to_k8s_error
from app.models.k8s_tool_models import K8sApiException


@pytest.mark.asyncio
async def test_list_namespaces():
    """列出 namespaces"""
    mock_bundle = MagicMock()
    mock_ns_list = MagicMock()

    # 注意：MagicMock(name=...) 设置的是 mock 内部显示名，不是 .name 属性
    # 需要构造后显式赋值
    ns1_metadata = MagicMock()
    ns1_metadata.name = "default"
    ns1_metadata.creation_timestamp = "2026-01-01T00:00:00Z"

    ns2_metadata = MagicMock()
    ns2_metadata.name = "kube-system"
    ns2_metadata.creation_timestamp = "2026-01-01T00:00:00Z"

    mock_ns_list.items = [
        MagicMock(metadata=ns1_metadata, status=MagicMock(phase="Active")),
        MagicMock(metadata=ns2_metadata, status=MagicMock(phase="Active")),
    ]
    mock_bundle.core_v1.list_namespace = AsyncMock(return_value=mock_ns_list)

    result = await K8sResourceService.list_namespaces(mock_bundle)
    assert len(result) == 2
    assert result[0].name == "default"


@pytest.mark.asyncio
async def test_list_nodes():
    """列出 nodes"""
    mock_bundle = MagicMock()
    mock_node_list = MagicMock()
    mock_node = MagicMock()
    mock_node.metadata.name = "node-1"
    mock_node.metadata.creation_timestamp = "2026-01-01T00:00:00Z"
    mock_node.metadata.labels = {"kubernetes.io/role": "worker", "node.kubernetes.io/instance-type": "m5.large"}
    mock_node.status.conditions = [
        MagicMock(type="Ready", status="True"),
    ]
    mock_node.status.node_info = MagicMock(
        kubelet_version="v1.28.0",
        os_image="Ubuntu 22.04",
        kernel_version="5.15.0",
        container_runtime_version="containerd://1.7.0",
    )
    mock_node.status.capacity = {"cpu": "4", "memory": "16Gi"}
    mock_node_list.items = [mock_node]
    mock_bundle.core_v1.list_node = AsyncMock(return_value=mock_node_list)

    result = await K8sResourceService.list_nodes(mock_bundle)
    assert len(result) == 1
    assert result[0].name == "node-1"
    assert result[0].version == "v1.28.0"


@pytest.mark.asyncio
async def test_list_pods():
    """列出 pods"""
    mock_bundle = MagicMock()
    mock_pod_list = MagicMock()
    mock_pod = MagicMock()
    mock_pod.metadata.name = "nginx-pod"
    mock_pod.metadata.namespace = "default"
    mock_pod.metadata.creation_timestamp = "2026-01-01T00:00:00Z"
    mock_pod.status.phase = "Running"
    mock_pod.status.container_statuses = [
        MagicMock(
            name="nginx",
            ready=True,
            restart_count=0,
            state=MagicMock(running=MagicMock(started_at="2026-01-01T00:00:00Z"), waiting=None, terminated=None),
        )
    ]
    # 注意：MagicMock(name="nginx") 设置的是 mock 内部显示名，不是 .name 属性
    mock_container_spec = MagicMock()
    mock_container_spec.name = "nginx"
    mock_pod.spec.containers = [mock_container_spec]
    mock_pod.spec.node_name = "node-1"
    mock_pod.status.pod_ip = "10.0.0.1"
    mock_pod_list.items = [mock_pod]
    mock_bundle.core_v1.list_namespaced_pod = AsyncMock(return_value=mock_pod_list)

    result = await K8sResourceService.list_pods(mock_bundle, namespace="default")
    assert len(result) == 1
    assert result[0].name == "nginx-pod"
    assert result[0].phase == "Running"


@pytest.mark.asyncio
async def test_get_pod_detail():
    """获取 pod 详情"""
    mock_bundle = MagicMock()
    mock_pod = MagicMock()
    mock_pod.metadata.name = "nginx-pod"
    mock_pod.metadata.namespace = "default"
    mock_pod.metadata.uid = "abc-123"
    mock_pod.metadata.creation_timestamp = "2026-01-01T00:00:00Z"
    mock_pod.metadata.labels = {"app": "nginx"}
    mock_pod.metadata.annotations = {}
    mock_pod.metadata.owner_references = []
    mock_pod.status.phase = "Running"
    mock_pod.status.conditions = []
    mock_pod.status.container_statuses = []
    mock_pod.status.init_container_statuses = None
    mock_pod.spec.containers = []
    mock_pod.spec.init_containers = None
    mock_pod.spec.node_name = "node-1"
    mock_pod.status.pod_ip = "10.0.0.1"
    mock_pod.status.host_ip = "192.168.1.1"
    mock_pod.status.qos_class = "BestEffort"
    mock_bundle.core_v1.read_namespaced_pod = AsyncMock(return_value=mock_pod)

    result = await K8sResourceService.get_pod_detail(mock_bundle, "nginx-pod", "default")
    assert result["name"] == "nginx-pod"
    assert result["uid"] == "abc-123"


# ============ Events + ConfigMap / Secret / PVC 测试 ============


@pytest.mark.asyncio
async def test_list_events():
    """列出 events（无 field_selector）"""
    mock_bundle = MagicMock()
    mock_event_list = MagicMock()

    mock_event = MagicMock()
    mock_event.type = "Warning"
    mock_event.reason = "BackOff"
    mock_event.message = "Back-off restarting failed container"
    # involved_object 的各属性必须显式赋值，不能用 MagicMock(name=...)（那是设置显示名）
    mock_involved_obj = MagicMock()
    mock_involved_obj.kind = "Pod"
    mock_involved_obj.name = "nginx-pod"
    mock_involved_obj.namespace = "default"
    mock_event.involved_object = mock_involved_obj
    mock_event.count = 3
    mock_event.first_timestamp = "2026-01-01T00:00:00Z"
    mock_event.last_timestamp = "2026-01-01T01:00:00Z"
    mock_event_list.items = [mock_event]

    mock_bundle.core_v1.list_namespaced_event = AsyncMock(return_value=mock_event_list)

    result = await K8sResourceService.list_events(mock_bundle, namespace="default")
    assert len(result) == 1
    assert result[0].type == "Warning"
    assert result[0].reason == "BackOff"
    assert result[0].object_kind == "Pod"
    assert result[0].object_name == "nginx-pod"
    assert result[0].count == 3
    # 确认调用了 list_namespaced_event 且未传 field_selector
    mock_bundle.core_v1.list_namespaced_event.assert_awaited_once_with(namespace="default")


@pytest.mark.asyncio
async def test_list_events_with_field_selector():
    """列出 events（带 field_selector）"""
    mock_bundle = MagicMock()
    mock_event_list = MagicMock()
    mock_event_list.items = []
    mock_bundle.core_v1.list_namespaced_event = AsyncMock(return_value=mock_event_list)

    await K8sResourceService.list_events(
        mock_bundle, namespace="default", field_selector="involvedObject.uid=abc-123"
    )
    # 确认传入了 field_selector
    mock_bundle.core_v1.list_namespaced_event.assert_awaited_once_with(
        namespace="default", field_selector="involvedObject.uid=abc-123"
    )


@pytest.mark.asyncio
async def test_get_configmap():
    """获取 configmap 详情"""
    mock_bundle = MagicMock()
    mock_cm = MagicMock()
    mock_cm.metadata.name = "app-config"
    mock_cm.metadata.namespace = "default"
    mock_cm.metadata.labels = {"app": "myapp"}
    mock_cm.metadata.annotations = {"note": "test"}
    mock_cm.metadata.creation_timestamp = "2026-01-01T00:00:00Z"
    mock_cm.data = {"DB_HOST": "localhost", "DB_PORT": "5432"}
    mock_bundle.core_v1.read_namespaced_config_map = AsyncMock(return_value=mock_cm)

    result = await K8sResourceService.get_configmap(mock_bundle, "app-config", "default")
    assert result["name"] == "app-config"
    assert result["namespace"] == "default"
    assert result["data"] == {"DB_HOST": "localhost", "DB_PORT": "5432"}
    assert result["labels"] == {"app": "myapp"}


@pytest.mark.asyncio
async def test_get_secret_base64_decode():
    """获取 secret 详情：base64 正常解码"""
    mock_bundle = MagicMock()
    mock_secret = MagicMock()
    mock_secret.metadata.name = "db-creds"
    mock_secret.metadata.namespace = "default"
    mock_secret.metadata.labels = {}
    mock_secret.metadata.annotations = {}
    mock_secret.metadata.creation_timestamp = "2026-01-01T00:00:00Z"
    mock_secret.type = "Opaque"
    # K8s Secret data 存储的是 base64 编码值
    mock_secret.data = {
        "username": base64.b64encode(b"admin").decode("utf-8"),
        "password": base64.b64encode(b"secret123").decode("utf-8"),
    }
    mock_bundle.core_v1.read_namespaced_secret = AsyncMock(return_value=mock_secret)

    result = await K8sResourceService.get_secret(mock_bundle, "db-creds", "default", user_id="user-1")
    assert result["name"] == "db-creds"
    assert result["type"] == "Opaque"
    # 验证 base64 被正确解码
    assert result["data"]["username"] == "admin"
    assert result["data"]["password"] == "secret123"


@pytest.mark.asyncio
async def test_get_secret_invalid_base64_fallback():
    """获取 secret 详情：非 base64 数据时保留原值"""
    mock_bundle = MagicMock()
    mock_secret = MagicMock()
    mock_secret.metadata.name = "mixed-secret"
    mock_secret.metadata.namespace = "default"
    mock_secret.metadata.labels = {}
    mock_secret.metadata.annotations = {}
    mock_secret.metadata.creation_timestamp = "2026-01-01T00:00:00Z"
    mock_secret.type = "Opaque"
    # 一个有效 base64，一个是非法 base64 字符串
    mock_secret.data = {
        "valid_key": base64.b64encode(b"hello").decode("utf-8"),
        "raw_key": "this-is-not-base64!!!",
    }
    mock_bundle.core_v1.read_namespaced_secret = AsyncMock(return_value=mock_secret)

    result = await K8sResourceService.get_secret(mock_bundle, "mixed-secret", "default")
    assert result["data"]["valid_key"] == "hello"
    # 非 base64 值保留原文
    assert result["data"]["raw_key"] == "this-is-not-base64!!!"


@pytest.mark.asyncio
async def test_get_secret_audit_log(caplog):
    """获取 secret 时记录审计日志"""
    import logging as _logging
    mock_bundle = MagicMock()
    mock_secret = MagicMock()
    mock_secret.metadata.name = "audit-test"
    mock_secret.metadata.namespace = "prod"
    mock_secret.metadata.labels = {}
    mock_secret.metadata.annotations = {}
    mock_secret.metadata.creation_timestamp = "2026-01-01T00:00:00Z"
    mock_secret.type = "Opaque"
    mock_secret.data = None
    mock_bundle.core_v1.read_namespaced_secret = AsyncMock(return_value=mock_secret)

    with caplog.at_level(_logging.INFO, logger="app.services.k8s_resource_service"):
        await K8sResourceService.get_secret(
            mock_bundle, "audit-test", "prod", user_id="user-42"
        )

    # 验证审计日志包含关键字段
    audit_records = [r for r in caplog.records if "[AUDIT]" in r.message]
    assert len(audit_records) == 1
    assert "user_id=user-42" in audit_records[0].message
    assert "secret=audit-test" in audit_records[0].message
    assert "namespace=prod" in audit_records[0].message


@pytest.mark.asyncio
async def test_get_pvc():
    """获取 PVC 详情"""
    mock_bundle = MagicMock()
    mock_pvc = MagicMock()
    mock_pvc.metadata.name = "data-pvc"
    mock_pvc.metadata.namespace = "default"
    mock_pvc.metadata.labels = {"app": "db"}
    mock_pvc.metadata.annotations = {}
    mock_pvc.metadata.creation_timestamp = "2026-01-01T00:00:00Z"
    mock_pvc.status.phase = "Bound"
    mock_pvc.status.capacity = {"storage": "10Gi"}
    mock_pvc.spec.volume_name = "pv-001"
    mock_pvc.spec.storage_class_name = "standard"
    mock_pvc.spec.access_modes = ["ReadWriteOnce"]
    mock_bundle.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(return_value=mock_pvc)

    result = await K8sResourceService.get_pvc(mock_bundle, "data-pvc", "default")
    assert result["name"] == "data-pvc"
    assert result["status"] == "Bound"
    assert result["capacity"] == {"storage": "10Gi"}
    assert result["volume_name"] == "pv-001"
    assert result["storage_class"] == "standard"
    assert result["access_modes"] == ["ReadWriteOnce"]


@pytest.mark.asyncio
async def test_get_pvc_unknown_status():
    """获取 PVC：status 为空时返回 Unknown"""
    mock_bundle = MagicMock()
    mock_pvc = MagicMock()
    mock_pvc.metadata.name = "pending-pvc"
    mock_pvc.metadata.namespace = "default"
    mock_pvc.metadata.labels = {}
    mock_pvc.metadata.annotations = {}
    mock_pvc.metadata.creation_timestamp = "2026-01-01T00:00:00Z"
    mock_pvc.status = None
    mock_pvc.spec.volume_name = None
    mock_pvc.spec.storage_class_name = None
    mock_pvc.spec.access_modes = []
    mock_bundle.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(return_value=mock_pvc)

    result = await K8sResourceService.get_pvc(mock_bundle, "pending-pvc", "default")
    assert result["status"] == "Unknown"
    assert result["capacity"] == {}


def test_api_exception_to_k8s_error_namespace_forbidden():
    """测试 namespace 权限不足时返回 NAMESPACE_FORBIDDEN 错误码"""
    # 构造 403 错误，body 中包含 "namespaces is forbidden"
    exc = ApiException(status=403, reason="Forbidden")
    exc.body = 'namespaces is forbidden: User "system:serviceaccount:default:test" cannot list resource "namespaces"'

    result = _api_exception_to_k8s_error(exc)

    assert result.error.code == "NAMESPACE_FORBIDDEN"
    assert result.error.status_code == 403
    assert "namespaces is forbidden" in result.error.k8s_reason


def test_api_exception_to_k8s_error_generic_forbidden():
    """测试普通 403 错误返回 FORBIDDEN 错误码"""
    # 构造 403 错误，但 body 中不包含 "namespaces is forbidden"
    exc = ApiException(status=403, reason="Forbidden")
    exc.body = "some other forbidden error"

    result = _api_exception_to_k8s_error(exc)

    assert result.error.code == "FORBIDDEN"
    assert result.error.status_code == 403


def test_api_exception_to_k8s_error_other_codes():
    """测试其他 HTTP 状态码"""
    # 测试 404
    exc_404 = ApiException(status=404, reason="Not Found")
    exc_404.body = "namespace not found"
    result_404 = _api_exception_to_k8s_error(exc_404)
    assert result_404.error.code == "NOT_FOUND"

    # 测试 401
    exc_401 = ApiException(status=401, reason="Unauthorized")
    exc_401.body = "invalid token"
    result_401 = _api_exception_to_k8s_error(exc_401)
    assert result_401.error.code == "CONNECTION_FAILED"

    # 测试 408
    exc_408 = ApiException(status=408, reason="Request Timeout")
    exc_408.body = "request timeout"
    result_408 = _api_exception_to_k8s_error(exc_408)
    assert result_408.error.code == "TIMEOUT"

    # 测试未知状态码
    exc_500 = ApiException(status=500, reason="Internal Server Error")
    exc_500.body = "internal error"
    result_500 = _api_exception_to_k8s_error(exc_500)
    assert result_500.error.code == "CONNECTION_FAILED"  # 默认值


# ============ Pod 日志下载测试 ============


@pytest.mark.asyncio
async def test_get_pod_logs():
    """获取 pod 完整日志"""
    mock_bundle = MagicMock()
    mock_response = MagicMock()
    mock_response.read = AsyncMock(return_value=b"line1\nline2\nline3\n")
    mock_bundle.core_v1.read_namespaced_pod_log = AsyncMock(return_value=mock_response)

    result = await K8sResourceService.get_pod_logs(
        mock_bundle, "nginx-pod", "default", tail_lines=1000
    )
    assert result == "line1\nline2\nline3\n"
    mock_bundle.core_v1.read_namespaced_pod_log.assert_called_once()
    call_kwargs = mock_bundle.core_v1.read_namespaced_pod_log.call_args.kwargs
    assert call_kwargs["name"] == "nginx-pod"
    assert call_kwargs["namespace"] == "default"
    assert call_kwargs["follow"] is False
    assert call_kwargs["tail_lines"] == 1000


@pytest.mark.asyncio
async def test_get_pod_logs_with_container():
    """获取 pod 指定容器日志"""
    mock_bundle = MagicMock()
    mock_response = MagicMock()
    mock_response.read = AsyncMock(return_value=b"container log\n")
    mock_bundle.core_v1.read_namespaced_pod_log = AsyncMock(return_value=mock_response)

    result = await K8sResourceService.get_pod_logs(
        mock_bundle, "nginx-pod", "default", container="nginx"
    )
    assert result == "container log\n"
    call_kwargs = mock_bundle.core_v1.read_namespaced_pod_log.call_args.kwargs
    assert call_kwargs["container"] == "nginx"


@pytest.mark.asyncio
async def test_get_pod_logs_string_response():
    """获取 pod 日志：响应为字符串时直接返回"""
    mock_bundle = MagicMock()
    mock_response = MagicMock()
    mock_response.read = AsyncMock(return_value="already decoded string\n")
    mock_bundle.core_v1.read_namespaced_pod_log = AsyncMock(return_value=mock_response)

    result = await K8sResourceService.get_pod_logs(
        mock_bundle, "nginx-pod", "default"
    )
    assert result == "already decoded string\n"


@pytest.mark.asyncio
async def test_get_pod_logs_api_error():
    """获取 pod 日志：K8s API 异常转换为 K8sApiException"""
    mock_bundle = MagicMock()
    exc = ApiException(status=404, reason="Not Found")
    exc.body = "pod not found"
    mock_bundle.core_v1.read_namespaced_pod_log = AsyncMock(side_effect=exc)

    with pytest.raises(K8sApiException):
        await K8sResourceService.get_pod_logs(
            mock_bundle, "nonexistent-pod", "default"
        )
