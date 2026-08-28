"""
K8s 资源查询 Service

只读查询：list / read / get。不导入 write/patch/delete 方法。
"""
import logging
from datetime import datetime
from typing import List, Optional

from kubernetes_asyncio.client import ApiException

from app.models.k8s_tool_models import (
    K8sNamespaceInfo,
    K8sNodeSummary,
    K8sPodSummary,
    K8sWorkloadSummary,
    K8sEventInfo,
    K8sError,
    K8sApiException,
)

logger = logging.getLogger(__name__)


class K8sResourceService:
    """K8s 资源查询服务（只读）"""

    @staticmethod
    async def list_namespaces(bundle) -> List[K8sNamespaceInfo]:
        """列出所有 namespace"""
        try:
            ns_list = await bundle.core_v1.list_namespace()
            return [
                K8sNamespaceInfo(
                    name=ns.metadata.name,
                    status=ns.status.phase if ns.status else "Unknown",
                    created_at=_parse_timestamp(ns.metadata.creation_timestamp),
                )
                for ns in ns_list.items
            ]
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def list_nodes(bundle) -> List[K8sNodeSummary]:
        """列出所有 node"""
        try:
            node_list = await bundle.core_v1.list_node()
            return [_node_to_summary(n) for n in node_list.items]
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def get_node(bundle, name: str) -> dict:
        """获取 node 详情"""
        try:
            node = await bundle.core_v1.read_node(name)
            return _node_to_detail(node)
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def list_pods(bundle, namespace: str, limit: Optional[int] = None) -> dict:
        """列出指定 namespace 的 pods，返回 {items, total} 分页格式"""
        try:
            pod_list = await bundle.core_v1.list_namespaced_pod(namespace)
            items = [_pod_to_summary(p) for p in pod_list.items]
            return {"items": items, "total": len(items)}
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def get_pod_detail(bundle, name: str, namespace: str) -> dict:
        """获取 pod 详情"""
        try:
            pod = await bundle.core_v1.read_namespaced_pod(name, namespace)
            return _pod_to_detail(pod)
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def get_pod_yaml(bundle, name: str, namespace: str) -> dict:
        """获取 pod YAML 序列化字典（由路由层用 yaml.safe_dump 转为字符串）"""
        try:
            from kubernetes_asyncio.client import ApiClient
            pod = await bundle.core_v1.read_namespaced_pod(name, namespace)
            api_client = ApiClient()
            return api_client.sanitize_for_serialization(pod)
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    # ============ 工作负载控制器 ============

    @staticmethod
    async def list_deployments(bundle, namespace: str) -> List[K8sWorkloadSummary]:
        """列出 deployments"""
        try:
            dep_list = await bundle.apps_v1.list_namespaced_deployment(namespace)
            return [_deployment_to_summary(d) for d in dep_list.items]
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def get_deployment_detail(bundle, name: str, namespace: str) -> dict:
        """获取 deployment 详情 + 关联 pods"""
        try:
            dep = await bundle.apps_v1.read_namespaced_deployment(name, namespace)
            # 查找关联 pods（通过 label selector）
            match_labels = dep.spec.selector.match_labels if dep.spec.selector else {}
            label_selector = ",".join(f"{k}={v}" for k, v in match_labels.items())
            related_pods = await bundle.core_v1.list_namespaced_pod(
                namespace, label_selector=label_selector
            )
            return {
                "deployment": _deployment_to_summary(dep),
                "pods": [_pod_to_summary(p) for p in related_pods.items],
                "labels": dep.metadata.labels or {},
                "annotations": dep.metadata.annotations or {},
                "strategy": dep.spec.strategy.type if dep.spec.strategy else "RollingUpdate",
            }
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def list_replicasets(bundle, namespace: str) -> List[K8sWorkloadSummary]:
        """列出 replicasets"""
        try:
            rs_list = await bundle.apps_v1.list_namespaced_replica_set(namespace)
            return [_replicaset_to_summary(rs) for rs in rs_list.items]
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def list_statefulsets(bundle, namespace: str) -> List[K8sWorkloadSummary]:
        """列出 statefulsets"""
        try:
            sts_list = await bundle.apps_v1.list_namespaced_stateful_set(namespace)
            return [_statefulset_to_summary(s) for s in sts_list.items]
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def list_daemonsets(bundle, namespace: str) -> List[K8sWorkloadSummary]:
        """列出 daemonsets"""
        try:
            ds_list = await bundle.apps_v1.list_namespaced_daemon_set(namespace)
            return [_daemonset_to_summary(ds) for ds in ds_list.items]
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def list_jobs(bundle, namespace: str) -> List[K8sWorkloadSummary]:
        """列出 jobs"""
        try:
            job_list = await bundle.batch_v1.list_namespaced_job(namespace)
            return [_job_to_summary(j) for j in job_list.items]
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def list_cronjobs(bundle, namespace: str) -> List[K8sWorkloadSummary]:
        """列出 cronjobs"""
        try:
            cj_list = await bundle.batch_v1.list_namespaced_cron_job(namespace)
            return [_cronjob_to_summary(cj) for cj in cj_list.items]
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    # ============ Events + 关联资源 ============

    @staticmethod
    async def list_events(bundle, namespace: str, field_selector: str = None) -> List[K8sEventInfo]:
        """列出 events（支持 field_selector 过滤）"""
        try:
            kwargs = {"namespace": namespace}
            if field_selector:
                kwargs["field_selector"] = field_selector
            event_list = await bundle.core_v1.list_namespaced_event(**kwargs)
            return [
                K8sEventInfo(
                    type=e.type or "Normal",
                    reason=e.reason or "",
                    message=e.message or "",
                    object_kind=e.involved_object.kind if e.involved_object else "",
                    object_name=e.involved_object.name if e.involved_object else "",
                    object_namespace=e.involved_object.namespace if e.involved_object else namespace,
                    count=e.count or 1,
                    first_seen=_parse_timestamp(e.first_timestamp),
                    last_seen=_parse_timestamp(e.last_timestamp),
                )
                for e in event_list.items
            ]
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def get_configmap(bundle, name: str, namespace: str) -> dict:
        """获取 configmap 详情"""
        try:
            cm = await bundle.core_v1.read_namespaced_config_map(name, namespace)
            return {
                "name": cm.metadata.name,
                "namespace": cm.metadata.namespace,
                "data": dict(cm.data) if cm.data else {},
                "labels": cm.metadata.labels or {},
                "annotations": cm.metadata.annotations or {},
                "created_at": _parse_timestamp(cm.metadata.creation_timestamp),
            }
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def get_secret(bundle, name: str, namespace: str, user_id: str = None) -> dict:
        """获取 secret 详情（data base64 解码返回明文）"""
        import base64

        # 审计日志：记录 Secret 访问行为
        logger.info(f"[AUDIT] Secret access: user_id={user_id}, secret={name}, namespace={namespace}")

        try:
            secret = await bundle.core_v1.read_namespaced_secret(name, namespace)
            # 解码 data 字段（K8s Secret data 是 base64 编码的）
            decoded_data = {}
            if secret.data:
                for k, v in secret.data.items():
                    try:
                        decoded_data[k] = base64.b64decode(v).decode("utf-8")
                    except Exception:
                        # 非 base64 原文，保留原值
                        decoded_data[k] = v
            return {
                "name": secret.metadata.name,
                "namespace": secret.metadata.namespace,
                "type": secret.type,
                "data": decoded_data,
                "labels": secret.metadata.labels or {},
                "annotations": secret.metadata.annotations or {},
                "created_at": _parse_timestamp(secret.metadata.creation_timestamp),
            }
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def get_pvc(bundle, name: str, namespace: str) -> dict:
        """获取 PVC（PersistentVolumeClaim）详情"""
        try:
            pvc = await bundle.core_v1.read_namespaced_persistent_volume_claim(name, namespace)
            return {
                "name": pvc.metadata.name,
                "namespace": pvc.metadata.namespace,
                "status": pvc.status.phase if pvc.status else "Unknown",
                "capacity": dict(pvc.status.capacity) if pvc.status and pvc.status.capacity else {},
                "volume_name": pvc.spec.volume_name,
                "storage_class": pvc.spec.storage_class_name,
                "access_modes": pvc.spec.access_modes or [],
                "labels": pvc.metadata.labels or {},
                "annotations": pvc.metadata.annotations or {},
                "created_at": _parse_timestamp(pvc.metadata.creation_timestamp),
            }
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)

    @staticmethod
    async def get_pod_logs(
        bundle,
        name: str,
        namespace: str,
        container: Optional[str] = None,
        tail_lines: Optional[int] = None,
        previous: bool = False,
    ) -> str:
        """获取 pod 完整日志（非 follow，一次性读取）

        Args:
            bundle: K8s 客户端 bundle
            name: Pod 名称
            namespace: 命名空间
            container: 容器名（多容器 pod 时使用）
            tail_lines: 返回末尾行数（None 表示返回全部日志）
            previous: 是否读取上一个已终止容器的日志

        Returns:
            日志文本（utf-8 解码）

        Raises:
            K8sApiException: K8s API 错误
        """
        try:
            kwargs: dict = {
                "name": name,
                "namespace": namespace,
                "follow": False,
                "previous": previous,
            }
            if container:
                kwargs["container"] = container
            if tail_lines is not None:
                kwargs["tail_lines"] = tail_lines

            response = await bundle.core_v1.read_namespaced_pod_log(**kwargs)
            # kubernetes_asyncio 在 follow=False 时直接返回 str，而不是流式响应对象
            if isinstance(response, str):
                return response
            # 如果是响应对象（设置了 _preload_content=False），需要读取内容
            if hasattr(response, 'read'):
                content = await response.read()
                if isinstance(content, bytes):
                    return content.decode("utf-8", errors="replace")
                return content
            # 兜底：尝试转换为字符串
            return str(response)
        except ApiException as e:
            raise _api_exception_to_k8s_error(e)


# ============ 内部辅助函数 ============


def _parse_timestamp(ts) -> Optional[datetime]:
    """解析 K8s 时间戳"""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _node_to_summary(node) -> K8sNodeSummary:
    """K8s Node 对象 → K8sNodeSummary"""
    labels = node.metadata.labels or {}
    roles = [
        k.split("/")[-1]
        for k, v in labels.items()
        if k.startswith("node-role.kubernetes.io/")
    ]
    if not roles:
        roles = ["worker"]

    # 状态：取 Ready condition
    status = "NotReady"
    if node.status and node.status.conditions:
        for cond in node.status.conditions:
            if cond.type == "Ready":
                status = "Ready" if cond.status == "True" else "NotReady"
                break

    node_info = node.status.node_info if node.status else None
    capacity = node.status.capacity if node.status else {}

    return K8sNodeSummary(
        name=node.metadata.name,
        status=status,
        roles=roles,
        version=node_info.kubelet_version if node_info else "Unknown",
        os_image=node_info.os_image if node_info else "Unknown",
        kernel_version=node_info.kernel_version if node_info else "Unknown",
        container_runtime=node_info.container_runtime_version if node_info else "Unknown",
        created_at=_parse_timestamp(node.metadata.creation_timestamp),
        conditions=[
            {"type": c.type, "status": c.status, "reason": c.reason, "message": c.message}
            for c in (node.status.conditions or [])
        ],
        capacity_cpu=capacity.get("cpu"),
        capacity_memory=capacity.get("memory"),
    )


def _node_to_detail(node) -> dict:
    """K8s Node 对象 → 详情 dict"""
    summary = _node_to_summary(node)
    return {
        **summary.dict(),
        "labels": node.metadata.labels or {},
        "annotations": node.metadata.annotations or {},
        "taints": [
            {"key": t.key, "value": t.value, "effect": t.effect}
            for t in (node.spec.taints or [])
        ] if node.spec else [],
        "allocatable": dict(node.status.allocatable) if node.status and node.status.allocatable else {},
        "addresses": [
            {"type": a.type, "address": a.address}
            for a in (node.status.addresses or [])
        ],
    }


def _api_exception_to_k8s_error(e: ApiException) -> K8sApiException:
    """K8s ApiException → K8sApiException"""
    code_map = {
        401: "CONNECTION_FAILED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        408: "TIMEOUT",
    }
    # 添加详细日志，帮助调试认证问题
    logger.error(
        f"K8s API 异常: status={e.status}, reason={e.reason}, body={e.body}"
    )

    # 检测是否是 namespace 权限不足
    is_namespace_forbidden = (
        e.status == 403
        and e.body
        and "namespaces is forbidden" in str(e.body)
    )

    return K8sApiException(K8sError(
        code="NAMESPACE_FORBIDDEN" if is_namespace_forbidden else code_map.get(e.status, "CONNECTION_FAILED"),
        message=f"K8s API 错误：{e.reason}",
        k8s_reason=str(e.body) if e.body else "",
        status_code=e.status,
    ))


# ============ Pod 辅助函数 ============


def _pod_to_summary(pod) -> K8sPodSummary:
    """K8s Pod 对象 → K8sPodSummary"""
    # 计算 ready 和 restarts
    container_statuses = pod.status.container_statuses or []
    ready_count = sum(1 for cs in container_statuses if cs.ready)
    total_count = len(pod.spec.containers) if pod.spec.containers else 0
    restarts = sum(cs.restart_count for cs in container_statuses)

    # 计算整体状态（类似 kubectl get pods 的 STATUS 列）
    phase = pod.status.phase if pod.status else "Unknown"
    status = _compute_pod_status(pod)

    return K8sPodSummary(
        name=pod.metadata.name,
        namespace=pod.metadata.namespace,
        status=status,
        phase=phase,
        ready=f"{ready_count}/{total_count}",
        restarts=restarts,
        node=pod.spec.node_name or "Unknown",
        pod_ip=pod.status.pod_ip if pod.status else None,
        created_at=_parse_timestamp(pod.metadata.creation_timestamp),
        containers=[c.name for c in (pod.spec.containers or [])],
    )


def _pod_to_detail(pod) -> dict:
    """K8s Pod 对象 → 详情 dict"""
    summary = _pod_to_summary(pod)
    return {
        "name": pod.metadata.name,
        "namespace": pod.metadata.namespace,
        "uid": pod.metadata.uid,
        "phase": pod.status.phase if pod.status else "Unknown",
        "status": summary.status,
        "node": pod.spec.node_name or "Unknown",
        "pod_ip": pod.status.pod_ip if pod.status else None,
        "host_ip": pod.status.host_ip if pod.status else None,
        "qos_class": pod.status.qos_class if pod.status else None,
        "created_at": _parse_timestamp(pod.metadata.creation_timestamp),
        "labels": pod.metadata.labels or {},
        "annotations": pod.metadata.annotations or {},
        "containers": [
            _container_info(cs, pod.spec.containers)
            for cs in (pod.status.container_statuses or [])
        ],
        "init_containers": [
            _container_info(cs, pod.spec.init_containers)
            for cs in (pod.status.init_container_statuses or [])
        ],
        "conditions": [
            {
                "type": c.type,
                "status": c.status,
                "reason": c.reason,
                "message": c.message,
                "last_transition_time": str(c.last_transition_time),
            }
            for c in (pod.status.conditions or [])
        ],
        "owner_references": [
            {"kind": o.kind, "name": o.name, "uid": o.uid}
            for o in (pod.metadata.owner_references or [])
        ],
    }


def _container_info(container_status, spec_containers) -> dict:
    """容器状态信息"""
    # 找到对应的 spec container（获取镜像和资源限制）
    spec = next(
        (c for c in (spec_containers or []) if c.name == container_status.name),
        None,
    )
    resources_req = {}
    resources_lim = {}
    if spec and spec.resources:
        if spec.resources.requests:
            resources_req = dict(spec.resources.requests)
        if spec.resources.limits:
            resources_lim = dict(spec.resources.limits)

    # 解析容器状态
    state = "unknown"
    state_detail = ""
    started_at = None
    if container_status.state:
        if container_status.state.running:
            state = "running"
            started_at = _parse_timestamp(container_status.state.running.started_at)
        elif container_status.state.waiting:
            state = "waiting"
            state_detail = container_status.state.waiting.reason or ""
        elif container_status.state.terminated:
            state = "terminated"
            state_detail = container_status.state.terminated.reason or ""

    return {
        "name": container_status.name,
        "image": spec.image if spec else "unknown",
        "ready": container_status.ready,
        "state": state,
        "state_detail": state_detail,
        "restart_count": container_status.restart_count,
        "started_at": started_at,
        "resources_requests": resources_req,
        "resources_limits": resources_lim,
    }


def _compute_pod_status(pod) -> str:
    """计算 Pod 整体状态（类似 kubectl get pods 的 STATUS 列）

    优先级：
    1. CrashLoopBackOff / ImagePullBackOff / ErrImagePull / OOMKilled 等异常状态
    2. ContainerCreating
    3. 全部容器 ready → Running
    4. 兜底返回 phase
    """
    phase = pod.status.phase if pod.status else "Unknown"

    # 优先检测异常状态
    for cs in pod.status.container_statuses or []:
        if cs.state and cs.state.waiting:
            reason = cs.state.waiting.reason
            if reason in (
                "CrashLoopBackOff",
                "ImagePullBackOff",
                "ErrImagePull",
                "CreateContainerConfigError",
            ):
                return reason
        if cs.state and cs.state.terminated:
            reason = cs.state.terminated.reason
            if reason == "OOMKilled":
                return "OOMKilled"

    # ContainerCreating
    for cs in pod.status.container_statuses or []:
        if cs.state and cs.state.waiting and cs.state.waiting.reason == "ContainerCreating":
            return "ContainerCreating"

    # Terminating（有 deletionTimestamp 但尚未删除完成）
    if pod.metadata.deletion_timestamp:
        return "Terminating"

    # 全部 ready → Running
    if phase == "Running" and all(
        cs.ready for cs in (pod.status.container_statuses or [])
    ):
        return "Running"

    return phase


# ============ 工作负载辅助函数 ============


def _deployment_to_summary(dep) -> K8sWorkloadSummary:
    """K8s Deployment 对象 → K8sWorkloadSummary"""
    desired = dep.spec.replicas or 0
    ready = dep.status.ready_replicas or 0
    available = dep.status.available_replicas or 0
    images = list({c.image for c in (dep.spec.template.spec.containers or [])})
    return K8sWorkloadSummary(
        name=dep.metadata.name,
        namespace=dep.metadata.namespace,
        kind="Deployment",
        ready=f"{ready}/{desired}",
        desired=desired,
        available=available,
        images=images,
        created_at=_parse_timestamp(dep.metadata.creation_timestamp),
        labels=dep.metadata.labels or {},
    )


def _replicaset_to_summary(rs) -> K8sWorkloadSummary:
    """K8s ReplicaSet 对象 → K8sWorkloadSummary"""
    desired = rs.spec.replicas or 0
    ready = rs.status.ready_replicas or 0
    images = list({c.image for c in (rs.spec.template.spec.containers or [])})
    return K8sWorkloadSummary(
        name=rs.metadata.name,
        namespace=rs.metadata.namespace,
        kind="ReplicaSet",
        ready=f"{ready}/{desired}",
        desired=desired,
        available=ready,
        images=images,
        created_at=_parse_timestamp(rs.metadata.creation_timestamp),
        labels=rs.metadata.labels or {},
    )


def _statefulset_to_summary(sts) -> K8sWorkloadSummary:
    """K8s StatefulSet 对象 → K8sWorkloadSummary"""
    desired = sts.spec.replicas or 0
    ready = sts.status.ready_replicas or 0
    images = list({c.image for c in (sts.spec.template.spec.containers or [])})
    return K8sWorkloadSummary(
        name=sts.metadata.name,
        namespace=sts.metadata.namespace,
        kind="StatefulSet",
        ready=f"{ready}/{desired}",
        desired=desired,
        available=ready,
        images=images,
        created_at=_parse_timestamp(sts.metadata.creation_timestamp),
        labels=sts.metadata.labels or {},
    )


def _daemonset_to_summary(ds) -> K8sWorkloadSummary:
    """K8s DaemonSet 对象 → K8sWorkloadSummary"""
    desired = ds.status.desired_number_scheduled or 0
    ready = ds.status.number_ready or 0
    images = list({c.image for c in (ds.spec.template.spec.containers or [])})
    return K8sWorkloadSummary(
        name=ds.metadata.name,
        namespace=ds.metadata.namespace,
        kind="DaemonSet",
        ready=f"{ready}/{desired}",
        desired=desired,
        available=ready,
        images=images,
        created_at=_parse_timestamp(ds.metadata.creation_timestamp),
        labels=ds.metadata.labels or {},
    )


def _job_to_summary(job) -> K8sWorkloadSummary:
    """K8s Job 对象 → K8sWorkloadSummary"""
    desired = job.spec.completions or 1
    succeeded = job.status.succeeded or 0
    images = list({c.image for c in (job.spec.template.spec.containers or [])})
    return K8sWorkloadSummary(
        name=job.metadata.name,
        namespace=job.metadata.namespace,
        kind="Job",
        ready=f"{succeeded}/{desired}",
        desired=desired,
        available=succeeded,
        images=images,
        created_at=_parse_timestamp(job.metadata.creation_timestamp),
        labels=job.metadata.labels or {},
    )


def _cronjob_to_summary(cj) -> K8sWorkloadSummary:
    """K8s CronJob 对象 → K8sWorkloadSummary"""
    return K8sWorkloadSummary(
        name=cj.metadata.name,
        namespace=cj.metadata.namespace,
        kind="CronJob",
        ready="N/A",
        desired=0,
        available=0,
        images=[],
        created_at=_parse_timestamp(cj.metadata.creation_timestamp),
        labels=cj.metadata.labels or {},
    )
