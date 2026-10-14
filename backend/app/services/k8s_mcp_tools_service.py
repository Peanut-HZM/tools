"""K8s MCP 工具服务层（只读）

供 app/mcp_server/k8s_server.py 的 MCP 工具调用。
只读硬边界：本模块只封装「查询 + 日志读取/落盘」，不存在任何集群写操作；
namespace_filter 非空时强制白名单；所有大小参数服务端封顶。
"""
import json
import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models.k8s_tool_models import K8sApiException  # noqa: F401（Task 6 错误包装复用）
from app.services.k8s_tool_service import K8sToolService
from app.services.k8s_resource_service import (
    K8sResourceService,
    _pod_to_summary,
    _parse_timestamp,
)
from app.services.k8s_client_factory import build_client
from app.services.k8s_service_mapping_service import K8sServiceMappingService

logger = logging.getLogger(__name__)

# ---- 服务端强制上限（spec 第 2/5.2 节） ----
LOG_TAIL_MAX = 2000
DEFAULT_TAIL = 500
MAX_GREP_MATCH_LINES = 300
LOG_FILE_MAX_BYTES = 50 * 1024 * 1024

# 日志落盘：tools 项目根 logs/k8s-mcp/（logs/ 已被 .gitignore 忽略，不入库）
# backend/app/services/k8s_mcp_tools_service.py → parents[3] = tools 项目根
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOGS_DIR = PROJECT_ROOT / "logs" / "k8s-mcp"

POD_NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
_SEGMENT_SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]+")

_WARNING_EVENT_WINDOW_SECONDS = 30 * 60


def _to_timestamp(ts) -> float:
    """事件时间转时间戳；datetime 用 timestamp()，字符串尝试 ISO 解析，失败为 0"""
    if isinstance(ts, datetime):
        return ts.timestamp()
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _event_to_dict(e) -> dict:
    """kubernetes_asyncio 事件对象 → K8sEventInfo 同构 dict（与 list_events 字段一致）"""
    io = e.involved_object
    return {
        "type": e.type or "Normal",
        "reason": e.reason or "",
        "message": e.message or "",
        "object_kind": io.kind if io else "",
        "object_name": io.name if io else "",
        "object_namespace": io.namespace if io else "",
        "count": e.count or 1,
        "first_seen": _parse_timestamp(e.first_timestamp),
        "last_seen": _parse_timestamp(e.last_timestamp),
    }


class K8sMcpToolsService:
    """MCP 只读工具业务层（@staticmethod）"""

    # 类属性镜像：write_log_file 统一走 K8sMcpToolsService.LOGS_DIR，
    # 使测试可 monkeypatch 类属性替换落盘目录
    LOGS_DIR = LOGS_DIR

    # ============ 配置与安全校验 ============

    @staticmethod
    def _load_config(user_id: str, cluster_id: str) -> dict:
        """加载当前用户的集群连接；不存在即 404 语义"""
        config = K8sToolService.get_config_by_id(user_id, cluster_id)
        if not config:
            raise ValueError(f"集群连接不存在或无权访问: {cluster_id}")
        return config

    @staticmethod
    def _check_namespace_allowed(config: dict, namespace: str) -> None:
        """连接配置了 namespace_filter 白名单时，越界 namespace 拒绝查询"""
        raw = config.get("namespace_filter") or "[]"
        try:
            ns_filter = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            ns_filter = []
        if ns_filter and namespace not in ns_filter:
            raise ValueError(
                f"命名空间 {namespace} 不在该连接允许的 namespace_filter 内: {ns_filter}")

    @staticmethod
    @asynccontextmanager
    async def _async_config_bundle(user_id: str, cluster_id: str):
        """加载配置 + 构造 K8s 客户端（凭证只在服务端内存解密）"""
        config = K8sMcpToolsService._load_config(user_id, cluster_id)
        async with build_client(config) as bundle:
            yield config, bundle

    @staticmethod
    def _validate_pod_name(name: str) -> str:
        """Pod/容器名严格白名单（K8s 命名规范），防注入/路径穿越"""
        if not name or not POD_NAME_RE.match(name):
            raise ValueError(f"非法 Pod/容器名: {name!r}")
        return name

    # ============ 纯函数工具 ============

    @staticmethod
    def filter_pods(items: list, keyword: Optional[str] = None,
                    status: Optional[str] = None) -> list:
        """按名称关键词与状态过滤 Pod 摘要列表"""
        result = items
        if keyword:
            result = [p for p in result if keyword.lower() in str(p.get("name", "")).lower()]
        if status:
            result = [p for p in result
                      if status.lower() in (str(p.get("status", "")).lower(),
                                            str(p.get("phase", "")).lower())]
        return result

    @staticmethod
    def validate_tail_lines(tail_lines: Optional[int]) -> int:
        """tail 行数：默认 500，服务端封顶 2000，非法值报错"""
        if tail_lines is None:
            return DEFAULT_TAIL
        if tail_lines < 1:
            raise ValueError("tail_lines 必须 >= 1")
        return min(tail_lines, LOG_TAIL_MAX)

    @staticmethod
    def grep_log(text: str, pattern: str) -> dict:
        """逐行正则过滤；匹配行输出封顶 MAX_GREP_MATCH_LINES"""
        try:
            compiled = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"grep 正则无效: {e}") from e
        lines = text.splitlines()
        matched = [ln for ln in lines if compiled.search(ln)]
        truncated = len(matched) > MAX_GREP_MATCH_LINES
        return {
            "matched_lines": matched[:MAX_GREP_MATCH_LINES],
            "matched": len(matched),
            "total_lines": len(lines),
            "truncated": truncated,
        }

    # ============ 查询编排（k8s_server.py 的 MCP 工具逐个对应） ============

    @staticmethod
    async def list_clusters(user_id: str) -> dict:
        """当前用户的全部集群连接（脱敏，含健康信息）"""
        configs = K8sToolService.get_configs(user_id)
        return {"clusters": [c.model_dump() for c in configs], "total": len(configs)}

    @staticmethod
    async def list_namespaces(user_id: str, cluster_id: str) -> dict:
        async with K8sMcpToolsService._async_config_bundle(user_id, cluster_id) as (config, bundle):
            ns_list = await K8sResourceService.list_namespaces(bundle)
            raw = config.get("namespace_filter") or "[]"
            try:
                ns_filter = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                ns_filter = []
            names = [ns.name for ns in ns_list]
            if ns_filter:
                names = [n for n in names if n in ns_filter]
            return {"namespaces": names, "total": len(names)}

    @staticmethod
    async def list_pods(user_id: str, cluster_id: str, namespace: Optional[str] = None,
                        keyword: Optional[str] = None, status: Optional[str] = None,
                        limit: Optional[int] = None) -> dict:
        """Pod 列表：namespace 为空时查全集群（仍受 namespace_filter 约束）"""
        limit = min(limit or 200, 200)
        async with K8sMcpToolsService._async_config_bundle(user_id, cluster_id) as (config, bundle):
            if namespace:
                K8sMcpToolsService._check_namespace_allowed(config, namespace)
                data = await K8sResourceService.list_pods(bundle, namespace)
                # K8sResourceService.list_pods 返回 K8sPodSummary 模型列表，转 dict 供过滤/序列化
                items = [p.model_dump() for p in data["items"]]
            else:
                raw = config.get("namespace_filter") or "[]"
                try:
                    ns_filter = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    ns_filter = []
                pod_list = await bundle.core_v1.list_pod_for_all_namespaces()
                items = [_pod_to_summary(p).model_dump()
                         for p in pod_list.items
                         if not ns_filter or p.metadata.namespace in ns_filter]
            items = K8sMcpToolsService.filter_pods(items, keyword, status)[:limit]
            logger.info("MCP list_pods 用户=%s 集群=%s ns=%s keyword=%s 返回 %d 条",
                        user_id, cluster_id, namespace, keyword, len(items))
            return {"items": items, "total": len(items)}

    @staticmethod
    async def get_pod(user_id: str, cluster_id: str, namespace: str, pod: str) -> dict:
        K8sMcpToolsService._validate_pod_name(pod)
        async with K8sMcpToolsService._async_config_bundle(user_id, cluster_id) as (config, bundle):
            K8sMcpToolsService._check_namespace_allowed(config, namespace)
            return await K8sResourceService.get_pod_detail(bundle, pod, namespace)

    @staticmethod
    async def get_pod_events(user_id: str, cluster_id: str,
                             namespace: Optional[str] = None,
                             pod: Optional[str] = None) -> dict:
        """Warning 事件：可按 Pod 名前缀过滤；namespace 为空时查全集群"""
        async with K8sMcpToolsService._async_config_bundle(user_id, cluster_id) as (config, bundle):
            if namespace:
                K8sMcpToolsService._check_namespace_allowed(config, namespace)
                events = await K8sResourceService.list_events(
                    bundle, namespace, field_selector="type=Warning")
                event_dicts = [e.model_dump() for e in events]
            else:
                event_list = await bundle.core_v1.list_event_for_all_namespaces(
                    field_selector="type=Warning")
                event_dicts = [_event_to_dict(e) for e in event_list.items]
        if pod:
            K8sMcpToolsService._validate_pod_name(pod)
            event_dicts = [ev for ev in event_dicts
                           if str(ev.get("object_name", "")).startswith(pod)]
        return {"events": event_dicts, "total": len(event_dicts)}

    @staticmethod
    async def get_pod_logs_text(user_id: str, cluster_id: str, namespace: str, pod: str,
                                container: Optional[str] = None,
                                tail_lines: Optional[int] = None,
                                previous: bool = False,
                                since_seconds: Optional[int] = None,
                                grep: Optional[str] = None) -> dict:
        """拉取日志文本（tail 封顶 2000；可选 grep 过滤；previous=崩溃前日志）"""
        K8sMcpToolsService._validate_pod_name(pod)
        if container:
            K8sMcpToolsService._validate_pod_name(container)
        tail = K8sMcpToolsService.validate_tail_lines(tail_lines)
        async with K8sMcpToolsService._async_config_bundle(user_id, cluster_id) as (config, bundle):
            K8sMcpToolsService._check_namespace_allowed(config, namespace)
            text = await K8sResourceService.get_pod_logs(
                bundle, pod, namespace, container, tail, previous, since_seconds)
        result: dict = {
            "pod": pod, "namespace": namespace, "container": container,
            "previous": previous, "tail_lines": tail,
            "returned_lines": len(text.splitlines()), "text": text,
        }
        if grep:
            filtered = K8sMcpToolsService.grep_log(text, grep)
            result["text"] = "\n".join(filtered["matched_lines"])
            result["grep"] = {"pattern": grep, "matched": filtered["matched"],
                              "total_lines": filtered["total_lines"],
                              "truncated": filtered["truncated"]}
            result["returned_lines"] = len(filtered["matched_lines"])
        logger.info("MCP get_pod_logs 用户=%s 集群=%s %s/%s previous=%s tail=%s grep=%s",
                    user_id, cluster_id, namespace, pod, previous, tail, bool(grep))
        return result

    # ============ 日志落盘 ============

    @staticmethod
    def build_log_filename(cluster_name: str, namespace: str, pod: str,
                           container: Optional[str], previous: bool) -> str:
        """生成安全文件名：pod/container 严格白名单，cluster/namespace 清洗"""
        K8sMcpToolsService._validate_pod_name(pod)
        if container:
            K8sMcpToolsService._validate_pod_name(container)
        cluster_seg = _SEGMENT_SANITIZE_RE.sub("-", cluster_name).strip("-.") or "cluster"
        ns_seg = _SEGMENT_SANITIZE_RE.sub("-", namespace).strip("-.") or "ns"
        parts = [cluster_seg, ns_seg, pod, container or "all"]
        if previous:
            parts.append("previous")
        return "-".join(parts) + ".log"

    @staticmethod
    def write_log_file(text: str, filename: str) -> dict:
        """写日志到 logs/k8s-mcp/；超 50MB 按字节截断（多字节安全）。

        通过 K8sMcpToolsService.LOGS_DIR 类属性访问目录（而非模块全局名），
        使测试可以 monkeypatch 类属性替换落盘目录。
        """
        raw = text.encode("utf-8")
        truncated = len(raw) > LOG_FILE_MAX_BYTES
        if truncated:
            raw = raw[:LOG_FILE_MAX_BYTES]
            text = raw.decode("utf-8", errors="ignore")
        logs_dir = K8sMcpToolsService.LOGS_DIR
        logs_dir.mkdir(parents=True, exist_ok=True)
        path = logs_dir / filename          # filename 各段已经白名单/清洗
        path.write_text(text, encoding="utf-8")
        size = path.stat().st_size
        logger.info("MCP 日志落盘 %s（%d 字节，截断=%s）", path, size, truncated)
        return {"path": str(path), "size_bytes": size, "lines": len(text.splitlines()),
                "truncated": truncated,
                "note": f"超过 {LOG_FILE_MAX_BYTES // (1024 * 1024)}MB 已截断" if truncated else ""}

    @staticmethod
    async def download_pod_logs(user_id: str, cluster_id: str, namespace: str, pod: str,
                                container: Optional[str] = None,
                                previous: bool = False) -> dict:
        """完整日志落盘本地文件（不进对话上下文），返回路径与统计"""
        config = K8sMcpToolsService._load_config(user_id, cluster_id)
        K8sMcpToolsService._check_namespace_allowed(config, namespace)
        filename = K8sMcpToolsService.build_log_filename(
            config.get("name", "cluster"), namespace, pod, container, previous)
        async with K8sMcpToolsService._async_config_bundle(user_id, cluster_id) as (_c, bundle):
            text = await K8sResourceService.get_pod_logs(
                bundle, pod, namespace, container, None, previous)
        result = K8sMcpToolsService.write_log_file(text, filename)
        result.update({"pod": pod, "namespace": namespace, "container": container,
                       "previous": previous})
        return result

    # ============ 集群概览 ============

    @staticmethod
    def _is_abnormal(pod: dict) -> bool:
        return pod.get("phase") != "Running" or pod.get("restarts", 0) > 0

    @staticmethod
    async def get_cluster_overview(user_id: str, cluster_id: str,
                                   namespace: Optional[str] = None) -> dict:
        """一次调用返回异常 Pod + 最近 30 分钟 Warning 事件（减少 Agent 多轮调用）"""
        pods_data = await K8sMcpToolsService.list_pods(
            user_id, cluster_id, namespace=namespace, keyword=None, status=None, limit=200)
        abnormal = [p for p in pods_data["items"] if K8sMcpToolsService._is_abnormal(p)]
        events_data = await K8sMcpToolsService.get_pod_events(user_id, cluster_id, namespace, None)
        cutoff = datetime.now().timestamp() - _WARNING_EVENT_WINDOW_SECONDS
        recent = [e for e in events_data["events"]
                  if e.get("last_seen") is None or _to_timestamp(e.get("last_seen")) >= cutoff]
        return {"abnormal_pods": abnormal, "abnormal_total": len(abnormal),
                "warning_events": recent, "warning_total": len(recent)}

    # ============ 服务定位映射桥接 ============

    @staticmethod
    def _validate_mapping_target(user_id: str, cluster_id: str, namespace: str) -> None:
        """保存映射前校验目标合法：cluster 属于该用户且 namespace 在白名单内"""
        config = K8sMcpToolsService._load_config(user_id, cluster_id)
        K8sMcpToolsService._check_namespace_allowed(config, namespace)

    @staticmethod
    async def lookup_service_mapping(user_id: str, project_key: str) -> dict:
        mapping = K8sServiceMappingService.lookup_mapping(user_id, project_key)
        if not mapping:
            return {"found": False, "project_key": project_key,
                    "note": "无该项目的定位记忆，请走发现流程（Jenkinsfile/配置文件推断或全量遍历）"}
        return {"found": True, **mapping}

    @staticmethod
    async def save_service_mapping(user_id: str, project_key: str, cluster_id: str,
                                   namespace: str, deployment: Optional[str] = None,
                                   container: Optional[str] = None,
                                   evidence: str = "", source: str = "user_confirmed") -> dict:
        K8sMcpToolsService._validate_mapping_target(user_id, cluster_id, namespace)
        row = K8sServiceMappingService.save_mapping(
            user_id, project_key, cluster_id, namespace, deployment, container,
            evidence, source)
        logger.info("MCP 保存服务定位映射 用户=%s 项目=%s", user_id, project_key)
        return {"saved": True, **row}
