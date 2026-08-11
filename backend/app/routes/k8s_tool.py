"""K8s 控制台工具路由

提供连接配置的 CRUD 端点：列表 / 上传 / 粘贴 / 手动创建 / 更新 / 删除，
以及连通性测试和健康状态查询（Task 7 实现）。
"""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from typing import List, Optional

from app.middleware.auth_middleware import get_current_user_id
from app.models.k8s_tool_models import (
    CreateK8sManualRequest,
    CreateK8sPasteRequest,
    DeleteK8sRequest,
    K8sApiException,
    K8sConfigResponse,
    K8sConnectionHealth,
    UpdateK8sRequest,
    UpdateK8sAuthRequest,
    UpdateConfigSortRequest,
)
from app.services.k8s_tool_service import K8sToolService
from app.config.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/k8s-tool", tags=["k8s-tool"])


# ============ 连接配置 CRUD ============


@router.get("/configs", response_model=List[K8sConfigResponse])
async def get_configs(user_id: str = Depends(get_current_user_id)):
    """列出当前用户的所有连接配置（脱敏，不含敏感字段原文）"""
    return K8sToolService.get_configs(user_id)


@router.post("/configs/upload", response_model=List[K8sConfigResponse])
async def upload_kubeconfig(
    file: UploadFile = File(..., description="kubeconfig 文件（UTF-8 文本）"),
    namespace_filter: str = Form(default="[]", description="命名空间过滤，JSON 数组"),
    user_id: str = Depends(get_current_user_id),
):
    """上传 kubeconfig 文件，按其中每个 context 批量创建连接配置"""
    # 文件大小校验（优先使用 file.size，回退到实际读取字节数）
    if file.size and file.size > settings.K8S_UPLOAD_MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过限制（{settings.K8S_UPLOAD_MAX_SIZE} bytes）",
        )

    content = await file.read()
    if len(content) > settings.K8S_UPLOAD_MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过限制（{settings.K8S_UPLOAD_MAX_SIZE} bytes）",
        )

    # 仅接受 UTF-8 编码文本
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件必须是 UTF-8 编码的文本")

    # 解析命名空间过滤参数（非法 JSON 降级为空列表）
    try:
        ns_filter = json.loads(namespace_filter) if namespace_filter != "[]" else []
    except json.JSONDecodeError:
        ns_filter = []

    return K8sToolService.create_from_kubeconfig(user_id, text, ns_filter)


@router.post("/configs/paste", response_model=List[K8sConfigResponse])
async def paste_kubeconfig(
    request: CreateK8sPasteRequest,
    user_id: str = Depends(get_current_user_id),
):
    """粘贴 kubeconfig 文本，按其中每个 context 批量创建连接配置"""
    return K8sToolService.create_from_kubeconfig(
        user_id, request.kubeconfig_text, request.namespace_filter
    )


@router.post("/configs/manual", response_model=K8sConfigResponse)
async def create_manual(
    request: CreateK8sManualRequest,
    user_id: str = Depends(get_current_user_id),
):
    """手动表单创建单条连接配置"""
    return K8sToolService.create_config(user_id, request)


@router.put("/configs/update", response_model=K8sConfigResponse)
async def update_config(
    request: UpdateK8sRequest,
    user_id: str = Depends(get_current_user_id),
):
    """更新连接配置（仅允许修改 name / namespace_filter）"""
    try:
        return K8sToolService.update_config(user_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/configs/update-auth", response_model=K8sConfigResponse)
async def update_config_auth(
    request: UpdateK8sAuthRequest,
    user_id: str = Depends(get_current_user_id),
):
    """更新连接的认证信息（token/cert/key 等）"""
    try:
        return K8sToolService.update_config_auth(user_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/configs/delete")
async def delete_config(
    request: DeleteK8sRequest = Body(...),
    user_id: str = Depends(get_current_user_id),
):
    """软删除连接配置（保留数据用于审计）"""
    success = K8sToolService.delete_config(user_id, request.id)
    if not success:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"message": "Config deleted successfully"}


@router.post("/configs/sort")
async def update_config_sort(
    request: UpdateConfigSortRequest,
    user_id: str = Depends(get_current_user_id),
):
    """批量更新连接配置的排序顺序"""
    try:
        K8sToolService.update_sort_order(user_id, request.config_ids)
        return {"message": "排序已更新"}
    except Exception as e:
        logger.error("更新排序失败: %s", e)
        raise HTTPException(status_code=500, detail="排序更新失败，请稍后重试")


# ============ 连通性测试 / 健康状态 ============


@router.post("/configs/{config_id}/test", response_model=K8sConnectionHealth)
async def test_connection(
    config_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """测试指定连接的 API Server 连通性"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    try:
        async with build_client(config) as bundle:
            # 尝试列出 namespaces 来测试连通性
            namespaces = await bundle.core_v1.list_namespace()
            server_version = None

            # 尝试获取 server 版本（非关键操作，失败不影响结果）
            try:
                version_info = await bundle.core_v1.api_client.call_api(
                    '/version', 'GET',
                    auth_settings=['BearerToken'],
                    response_type='object',
                    _return_http_data_only=True
                )
                server_version = version_info.get('gitVersion') if version_info else None
            except Exception as e:
                logger.warning(f"获取 server 版本失败: {e}")

            # 更新测试结果到数据库
            K8sToolService.update_test_result(
                config_id,
                success=True,
                error=None,
                metrics_available=True  # 如果能列出 namespace，通常 metrics 也可用
            )

            return K8sConnectionHealth(
                reachable=True,
                server_version=server_version,
                tested_at=datetime.now(),
            )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"连接测试失败 (config_id={config_id}): {error_msg}", exc_info=True)

        # 更新测试结果到数据库
        K8sToolService.update_test_result(
            config_id,
            success=False,
            error=error_msg,
            metrics_available=False
        )

        raise HTTPException(status_code=500, detail=f"连接失败: {error_msg}")


@router.get("/configs/{config_id}/health", response_model=K8sConnectionHealth)
async def get_health(
    config_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """获取指定连接的健康状态（复用 test 端点逻辑）"""
    return await test_connection(config_id, user_id)


# ============ 资源查询（Namespace + Node） ============

from app.services.k8s_client_factory import build_client
from app.services.k8s_resource_service import K8sResourceService


def _k8s_api_error_to_http(e: K8sApiException) -> HTTPException:
    """K8sApiException → HTTPException（保留结构化错误码）"""
    return HTTPException(
        status_code=e.error.status_code or 500,
        detail={"code": e.error.code, "message": e.error.message},
    )


@router.get("/{config_id}/namespaces")
async def list_namespaces(
    config_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """列出所有 namespace"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.list_namespaces(bundle)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/nodes")
async def list_nodes(
    config_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """列出所有 node"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.list_nodes(bundle)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/nodes/{name}")
async def get_node(
    config_id: str,
    name: str,
    user_id: str = Depends(get_current_user_id),
):
    """获取 node 详情"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.get_node(bundle, name)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


# ============ 资源查询（Pod） ============


@router.get("/{config_id}/pods")
async def list_pods(
    config_id: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """列出指定 namespace 的 pods"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.list_pods(bundle, namespace)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/pods/{name}")
async def get_pod(
    config_id: str,
    name: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """获取 pod 详情"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.get_pod_detail(bundle, name, namespace)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/pods/{name}/yaml")
async def get_pod_yaml(
    config_id: str,
    name: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """获取 pod YAML（只读）"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            yaml_dict = await K8sResourceService.get_pod_yaml(bundle, name, namespace)
            import yaml
            return {"yaml": yaml.safe_dump(yaml_dict, default_flow_style=False)}
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/pods/{name}/events")
async def get_pod_events(
    config_id: str,
    name: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """获取 pod 相关 events（Task 10 补全 list_events 方法后可用）"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            # 先获取 pod UID
            pod = await bundle.core_v1.read_namespaced_pod(name, namespace)
            field_selector = f"involvedObject.uid={pod.metadata.uid}"
            return await K8sResourceService.list_events(bundle, namespace, field_selector)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


# ============ 资源查询（工作负载控制器） ============


@router.get("/{config_id}/deployments")
async def list_deployments(
    config_id: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """列出指定 namespace 的 deployments"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.list_deployments(bundle, namespace)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/deployments/{name}")
async def get_deployment(
    config_id: str,
    name: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """获取 deployment 详情（含关联 pods）"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.get_deployment_detail(bundle, name, namespace)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/replicasets")
async def list_replicasets(
    config_id: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """列出指定 namespace 的 replicasets"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.list_replicasets(bundle, namespace)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/statefulsets")
async def list_statefulsets(
    config_id: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """列出指定 namespace 的 statefulsets"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.list_statefulsets(bundle, namespace)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/daemonsets")
async def list_daemonsets(
    config_id: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """列出指定 namespace 的 daemonsets"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.list_daemonsets(bundle, namespace)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/jobs")
async def list_jobs(
    config_id: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """列出指定 namespace 的 jobs"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.list_jobs(bundle, namespace)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/cronjobs")
async def list_cronjobs(
    config_id: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """列出指定 namespace 的 cronjobs"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.list_cronjobs(bundle, namespace)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


# ============ 资源查询（Events + ConfigMap / Secret / PVC） ============


@router.get("/{config_id}/events")
async def list_events(
    config_id: str,
    namespace: str = Query(..., description="命名空间"),
    field_selector: str = Query(None, description="字段过滤（如 involvedObject.name=xxx）"),
    user_id: str = Depends(get_current_user_id),
):
    """列出指定 namespace 的 events"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.list_events(bundle, namespace, field_selector)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/configmaps/{name}")
async def get_configmap(
    config_id: str,
    name: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """获取 configmap 详情"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.get_configmap(bundle, name, namespace)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/secrets/{name}")
async def get_secret(
    config_id: str,
    name: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """获取 secret 详情（data 字段 base64 解码返回明文）"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.get_secret(bundle, name, namespace, user_id)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


@router.get("/{config_id}/pvcs/{name}")
async def get_pvc(
    config_id: str,
    name: str,
    namespace: str = Query(..., description="命名空间"),
    user_id: str = Depends(get_current_user_id),
):
    """获取 PVC 详情"""
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        async with build_client(config) as bundle:
            return await K8sResourceService.get_pvc(bundle, name, namespace)
    except K8sApiException as e:
        raise _k8s_api_error_to_http(e)


# ============ Pod 日志 WebSocket 流（Task 11） ============


@router.websocket("/{config_id}/ws/pods/{name}/logs")
async def pod_logs_ws(
    websocket: WebSocket,
    config_id: str,
    name: str,
    namespace: str = Query(..., description="命名空间"),
    container: Optional[str] = Query(None, description="容器名（多容器 Pod 时必填）"),
    tail_lines: int = Query(100, description="返回末尾行数"),
    since_seconds: Optional[int] = Query(None, description="只返回最近 N 秒内的日志"),
    follow: bool = Query(True, description="是否持续跟踪日志流"),
    previous: bool = Query(False, description="是否读取上一个已终止容器的日志"),
    token: str = Query(..., description="鉴权 Token"),
):
    """Pod 日志流 WebSocket 端点

    鉴权通过 query param `token` 完成（WebSocket 无法使用 HTTP Header）。
    日志行以纯文本逐行推送到客户端，follow=True 时保持连接直到客户端断开。
    """
    # 1. 鉴权：在 accept 之前验证 token，失败直接关闭
    from app.services.auth_service import get_auth_service
    auth_service = get_auth_service()
    try:
        token_data = auth_service.verify_token_data(token)
        user_id = token_data.user_id
    except ValueError:
        await websocket.close(code=4003, reason="Authentication failed")
        return

    # 2. 获取配置：确认配置存在且属于当前用户
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        await websocket.close(code=4000, reason="Config not found")
        return

    # 3. 鉴权和配置校验通过，接受 WebSocket 连接
    await websocket.accept()

    # 4. 构造 K8s 客户端 → 拉取日志流
    try:
        async with build_client(config) as bundle:
            kwargs = {
                "name": name,
                "namespace": namespace,
                "tail_lines": tail_lines,
                "follow": follow,
                "previous": previous,
                "_preload_content": False,  # 返回原始流而非预加载内容
            }
            if container:
                kwargs["container"] = container
            if since_seconds:
                kwargs["since_seconds"] = since_seconds

            # read_namespaced_pod_log 返回 HTTP 响应流（_preload_content=False）
            log_stream = await bundle.core_v1.read_namespaced_pod_log(**kwargs)

            # 5. 使用 aiohttp 的 content 流式读取日志行，逐行推送到 WebSocket
            # kubernetes_asyncio 返回的是 aiohttp.ClientResponse，需要用 content 属性读取
            async for line in log_stream.content:
                if isinstance(line, bytes):
                    line = line.decode("utf-8", errors="replace")
                # 确保每行以换行符结尾
                if not line.endswith('\n'):
                    line += '\n'
                await websocket.send_text(line)

    except WebSocketDisconnect:
        # 客户端主动断开，正常情况，仅记录 info 日志
        logger.info("WebSocket 客户端断开: pod=%s, namespace=%s", name, namespace)
    except Exception as e:
        # 日志流异常：发送错误帧后关闭连接
        logger.error("Pod 日志流异常: pod=%s, namespace=%s, error=%s", name, namespace, e)
        try:
            await websocket.send_json({
                "type": "error",
                "code": "LOG_STREAM_ERROR",
                "message": str(e),
            })
            await websocket.close(code=4001)
        except Exception:
            # 关闭本身也可能失败（连接已断），忽略
            pass


# ============ Pod Exec 交互式终端 WebSocket（Task 12） ============


@router.websocket("/{config_id}/ws/pods/{name}/exec")
async def pod_exec_ws(
    websocket: WebSocket,
    config_id: str,
    name: str,
    namespace: str = Query(..., description="命名空间"),
    container: Optional[str] = Query(None, description="容器名（多容器 Pod 时必填）"),
    command: str = Query("/bin/sh", description="要执行的命令"),
    token: str = Query(..., description="鉴权 Token"),
):
    """Pod exec 交互式终端 WebSocket

    双向转发：WebSocket 输入 → K8s stdin；K8s stdout/stderr → WebSocket 输出。
    支持 resize：客户端发 {"type":"resize","cols":N,"rows":N} → channel 0 发送 resize 命令。
    使用 asyncio.gather 并发读写。
    """
    import asyncio

    # 1. 鉴权：在 accept 之前验证 token，失败直接关闭
    from app.services.auth_service import get_auth_service
    auth_service = get_auth_service()
    try:
        token_data = auth_service.verify_token_data(token)
        user_id = token_data.user_id
    except ValueError:
        await websocket.close(code=4003, reason="Authentication failed")
        return

    # 2. 获取配置：确认配置存在且属于当前用户
    config = K8sToolService.get_config_by_id(user_id, config_id)
    if not config:
        await websocket.close(code=4000, reason="Config not found")
        return

    # 3. 鉴权和配置校验通过，接受 WebSocket 连接
    await websocket.accept()

    # 4. 构造 K8s 客户端 → exec
    try:
        async with build_client(config) as bundle:
            exec_command = [command]
            kwargs = {
                "name": name,
                "namespace": namespace,
                "command": exec_command,
                "stdin": True,
                "stdout": True,
                "stderr": True,
                "tty": True,
                "_preload_content": False,
            }
            if container:
                kwargs["container"] = container

            # connect_get_namespaced_pod_exec 返回 WSClient（kubernetes_asyncio）
            resp = await bundle.core_v1.connect_get_namespaced_pod_exec(**kwargs)

            # 5. 双向转发：WebSocket ↔ K8s exec stream

            async def read_from_k8s():
                """从 K8s exec stream 读取 stdout/stderr → 发送到 WebSocket"""
                try:
                    while True:
                        if not resp.is_open():
                            break
                        # run_forever 处理 WebSocket 帧，timeout 避免永久阻塞
                        resp.run_forever(timeout=0.1)
                        if resp.peek_stdout():
                            data = resp.read_stdout()
                            if data:
                                await websocket.send_json({"type": "output", "data": data})
                        if resp.peek_stderr():
                            data = resp.read_stderr()
                            if data:
                                await websocket.send_json({"type": "output", "data": data})
                except Exception as e:
                    logger.error("K8s exec 读取异常: pod=%s, namespace=%s, error=%s", name, namespace, e)

            async def write_to_k8s():
                """从 WebSocket 接收输入 → 写入 K8s exec stdin；处理 resize 消息"""
                try:
                    while True:
                        msg = await websocket.receive_json()
                        if msg.get("type") == "input":
                            # 用户输入写入 stdin
                            resp.write_stdin(msg["data"])
                        elif msg.get("type") == "resize":
                            # resize 通过 channel 0 发送终端尺寸变更命令
                            # 格式：\x01<cols>\x02<rows>（WSClient resize 协议）
                            cols = msg.get("cols", 80)
                            rows = msg.get("rows", 24)
                            size_cmd = f"\x01{cols}\x02{rows}"
                            resp.write_channel(0, size_cmd)
                except WebSocketDisconnect:
                    logger.info("Exec WebSocket 客户端断开: pod=%s, namespace=%s", name, namespace)
                except Exception as e:
                    logger.error("K8s exec 写入异常: pod=%s, namespace=%s, error=%s", name, namespace, e)

            # 并发执行读写，任一方结束即退出
            await asyncio.gather(read_from_k8s(), write_to_k8s())

    except WebSocketDisconnect:
        # 客户端主动断开，正常情况
        logger.info("Exec WebSocket 客户端断开: pod=%s, namespace=%s", name, namespace)
    except Exception as e:
        # exec 异常：发送错误帧后关闭连接
        logger.error("Exec 异常: pod=%s, namespace=%s, error=%s", name, namespace, e)
        try:
            await websocket.send_json({
                "type": "error",
                "code": "EXEC_ERROR",
                "message": str(e),
            })
            await websocket.close(code=4001)
        except Exception:
            # 关闭本身也可能失败（连接已断），忽略
            pass
