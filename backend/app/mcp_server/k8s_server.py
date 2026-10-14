"""K8s 排障 MCP Server（严格只读）

10 个工具 = 8 个查询/日志 + 2 个服务定位映射存取（映射仅写平台元数据表）。
mcp 2.x API：MCPServer + @server.tool()；streamable_http_app 全进程单例。
"""
import json
import logging

from mcp.server.mcpserver import MCPServer

from app.mcp_server.auth import get_current_mcp_user_id
from app.services.k8s_mcp_tools_service import K8sMcpToolsService

logger = logging.getLogger(__name__)

server = MCPServer(
    name="k8s-troubleshoot",
    instructions=(
        "K8s 只读排障工具集：查集群/Pod 状态、拉取与下载日志、事件、服务定位记忆。"
        "禁止任何写操作。排障建议：先 lookup_service_mapping 命中记忆；"
        "RESTARTS>0 时优先 previous=true 拉崩溃前日志。"
    ),
)


async def _call(coro) -> str:
    """统一执行与错误包装：任何异常都转为 Error: 文本，不向客户端抛协议错误"""
    try:
        result = await coro
        return json.dumps(result, ensure_ascii=False, default=str)
    except PermissionError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        logger.error("MCP 工具执行失败: %s", e, exc_info=True)
        return f"Error: {type(e).__name__}: {e}"


@server.tool()
async def list_clusters() -> str:
    """列出当前用户的全部 K8s 集群连接（id、名称、server、健康信息）。排障第一步。"""
    return await _call(K8sMcpToolsService.list_clusters(get_current_mcp_user_id()))


@server.tool()
async def list_namespaces(cluster_id: str) -> str:
    """列出指定集群连接的命名空间（受连接的 namespace_filter 约束）"""
    return await _call(
        K8sMcpToolsService.list_namespaces(get_current_mcp_user_id(), cluster_id))


@server.tool()
async def list_pods(cluster_id: str, namespace: str = "", keyword: str = "",
                    status: str = "", limit: int = 200) -> str:
    """列出 Pod（状态/重启次数/运行时间/节点/Pod IP/容器名）。

    namespace 留空查全集群（仍受 namespace_filter 约束）；keyword 按 Pod 名模糊匹配；
    status 可选 Running/CrashLoopBackOff/Error/Pending 等进行过滤。
    """
    return await _call(K8sMcpToolsService.list_pods(
        get_current_mcp_user_id(), cluster_id,
        namespace=namespace or None, keyword=keyword or None,
        status=status or None, limit=limit))


@server.tool()
async def get_pod(cluster_id: str, namespace: str, pod: str) -> str:
    """获取 Pod 详情（容器状态、重启原因 lastState、镜像、QoS）"""
    return await _call(K8sMcpToolsService.get_pod(
        get_current_mcp_user_id(), cluster_id, namespace, pod))


@server.tool()
async def get_pod_events(cluster_id: str, namespace: str = "", pod: str = "") -> str:
    """查询 Warning 事件（OOMKilled/调度失败/镜像拉取失败等）。namespace/pod 留空查全集群。"""
    return await _call(K8sMcpToolsService.get_pod_events(
        get_current_mcp_user_id(), cluster_id,
        namespace=namespace or None, pod=pod or None))


@server.tool()
async def get_pod_logs(cluster_id: str, namespace: str, pod: str,
                       container: str = "", tail_lines: int = 500,
                       previous: bool = False, since_seconds: int = 0,
                       grep: str = "") -> str:
    """拉取容器日志文本（tail 上限 2000 行）。

    previous=true 读取上一个已终止容器的日志（崩溃前现场，RESTARTS>0 时优先）；
    grep 传正则（如 "ERROR|Exception"）在服务端过滤降噪；
    since_seconds 只返回最近 N 秒日志（0=不限）。
    """
    return await _call(K8sMcpToolsService.get_pod_logs_text(
        get_current_mcp_user_id(), cluster_id, namespace, pod,
        container=container or None, tail_lines=tail_lines, previous=previous,
        since_seconds=since_seconds or None, grep=grep or None))


@server.tool()
async def download_pod_logs(cluster_id: str, namespace: str, pod: str,
                            container: str = "", previous: bool = False) -> str:
    """下载完整日志到项目 logs/k8s-mcp/ 目录（上限 50MB），返回文件路径。

    适合大日志：拿到路径后用 Grep/Read 工具本地检索，避免撑爆上下文。
    日志目录已在 .gitignore 中忽略，不会进入版本库。
    """
    return await _call(K8sMcpToolsService.download_pod_logs(
        get_current_mcp_user_id(), cluster_id, namespace, pod,
        container=container or None, previous=previous))


@server.tool()
async def get_cluster_overview(cluster_id: str, namespace: str = "") -> str:
    """集群排障概览：异常 Pod（非 Running 或重启>0）+ 最近 30 分钟 Warning 事件。一次调用代替多轮。"""
    return await _call(K8sMcpToolsService.get_cluster_overview(
        get_current_mcp_user_id(), cluster_id, namespace=namespace or None))


@server.tool()
async def lookup_service_mapping(project_key: str) -> str:
    """查询「项目 → 集群/命名空间/容器」定位记忆（project_key 通常取本地项目目录名）。命中则无需再发现。"""
    return await _call(K8sMcpToolsService.lookup_service_mapping(
        get_current_mcp_user_id(), project_key))


@server.tool()
async def save_service_mapping(project_key: str, cluster_id: str, namespace: str,
                               deployment: str = "", container: str = "",
                               evidence: str = "", source: str = "user_confirmed") -> str:
    """保存服务定位记忆（同项目覆盖更新，幂等）。

    source 必须是 jenkinsfile / config_file / traversal / user_confirmed 之一，
    如实记录定位来源；evidence 记录依据（如 Jenkinsfile 片段、匹配到的 Pod 名）。
    仅写平台元数据表，不触碰任何集群资源。
    """
    return await _call(K8sMcpToolsService.save_service_mapping(
        get_current_mcp_user_id(), project_key, cluster_id, namespace,
        deployment=deployment or None, container=container or None,
        evidence=evidence, source=source))


# ---- streamable HTTP app（全进程单例：每次调用会新建 session_manager） ----

_streamable_app = None


def get_mcp_starlette_app():
    global _streamable_app
    if _streamable_app is None:
        # streamable_http_path="/k8s" 配合主应用 mount("/mcp", ...) 拼出端点 /mcp/k8s
        # （直接 mount("/mcp/k8s") 时精确路径会被主应用 307 到带尾斜杠的地址）
        _streamable_app = server.streamable_http_app(
            stateless_http=True, host="127.0.0.1", streamable_http_path="/k8s")
    return _streamable_app
