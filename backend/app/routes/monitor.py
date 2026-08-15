"""
监控模块 API 路由
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.middleware.auth_middleware import get_current_user_id
from app.models.monitor_models import (
    CreateMonitorServerRequest, UpdateMonitorServerRequest, MonitorServerResponse,
    ImportSSHRequest, TestMonitorServerRequest, AlertRuleCreateRequest,
    AlertRuleUpdateRequest, AlertRuleResponse,
    MonitorSettings, ServiceActionRequest,
)
from app.services.monitor import alert_engine, remote_ops
from app.services.monitor.collector import monitor_collector
from app.services.monitor.metric_repo import get_latest_metric, query_metrics
from app.services.monitor.server_service import MonitorServerService

router = APIRouter(prefix="/monitor", tags=["monitor"])


# ============ 服务器管理 ============

@router.get("/servers", response_model=List[MonitorServerResponse])
async def get_servers(user_id: str = Depends(get_current_user_id)):
    """获取服务器列表（含最近指标与实时状态）"""
    return MonitorServerService.get_servers(user_id)


@router.post("/servers", response_model=MonitorServerResponse)
async def create_server(
    request: CreateMonitorServerRequest,
    user_id: str = Depends(get_current_user_id),
):
    """新建监控服务器"""
    return MonitorServerService.create_server(user_id, request)


@router.post("/servers/test")
async def test_server_connection(
    request: TestMonitorServerRequest,
    user_id: str = Depends(get_current_user_id),
):
    """测试 SSH 连接"""
    MonitorServerService.test_connection(request)
    return {"success": True, "message": "连接成功"}


@router.post("/servers/import-ssh", response_model=MonitorServerResponse)
async def import_from_ssh(
    request: ImportSSHRequest,
    user_id: str = Depends(get_current_user_id),
):
    """从 SSH 配置导入监控服务器"""
    return MonitorServerService.import_from_ssh(user_id, request.ssh_config_id)


@router.put("/servers/{server_id}", response_model=MonitorServerResponse)
async def update_server(
    server_id: str,
    request: UpdateMonitorServerRequest,
    user_id: str = Depends(get_current_user_id),
):
    """更新监控服务器"""
    updated = MonitorServerService.update_server(user_id, server_id, request)
    if not updated:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return updated


@router.delete("/servers/{server_id}")
async def delete_server(
    server_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """删除监控服务器"""
    if not MonitorServerService.delete_server(user_id, server_id):
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return {"success": True}


@router.post("/servers/{server_id}/retry")
async def retry_server(
    server_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """手动触发采集（错误恢复）"""
    result = await monitor_collector.collect_now(server_id, user_id)
    if result is None:
        raise HTTPException(status_code=500, detail="采集失败，请检查连接配置")
    return {"success": True}


# ============ 监控数据 ============

@router.get("/servers/{server_id}/overview")
async def get_overview(server_id: str, user_id: str = Depends(get_current_user_id)):
    """获取服务器实时状态（最近一次采集指标）"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return {
        "server": {k: v for k, v in server.items() if k not in ("password", "private_key", "passphrase")},
        "metric": get_latest_metric(server_id),
    }


@router.get("/servers/{server_id}/metrics")
async def get_metrics(
    server_id: str,
    range: str = Query("1h", pattern="^(1h|6h|24h|7d)$"),
    user_id: str = Depends(get_current_user_id),
):
    """获取历史指标（7d 自动按小时聚合）"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return {"server_id": server_id, "range": range, "points": query_metrics(server_id, range)}


@router.get("/servers/{server_id}/partitions")
async def get_partitions(server_id: str, user_id: str = Depends(get_current_user_id)):
    """获取磁盘分区列表"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return {"partitions": await remote_ops.get_partitions(server)}


@router.get("/servers/{server_id}/system-info")
async def get_system_info(server_id: str, user_id: str = Depends(get_current_user_id)):
    """获取系统信息（60s 缓存）"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return await remote_ops.get_system_info(server)


# ============ 进程管理 ============

@router.get("/servers/{server_id}/processes")
async def get_processes(
    server_id: str,
    sort_by: str = Query("cpu_percent"),
    sort_order: str = Query("desc"),
    search: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    user_id: str = Depends(get_current_user_id),
):
    """获取进程列表（本机走 psutil，远程走 ps 命令）"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    if server["server_type"] == "local":
        from app.services.system_monitor_service import get_process_list
        return get_process_list(sort_by=sort_by, sort_order=sort_order,
                                search=search, project_type=project_type,
                                page=page, page_size=page_size)
    return await remote_ops.get_processes(
        server, sort_by=sort_by, sort_order=sort_order, search=search,
        project_type=project_type, page=page, page_size=page_size)


@router.post("/servers/{server_id}/processes/{pid}/kill")
async def kill_process(
    server_id: str,
    pid: int = Path(..., ge=1),  # pid 必须为正整数，防止负数/零误杀进程组
    user_id: str = Depends(get_current_user_id),
):
    """结束进程"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    if server["server_type"] == "local":
        from app.services.system_monitor_service import kill_process as kill_local
        ok = kill_local(pid)
    else:
        ok = await remote_ops.kill_process(server, pid)
    if not ok:
        raise HTTPException(status_code=400, detail="进程不存在或无法终止（可能权限不足）")
    return {"success": True, "pid": pid}


# ============ 服务管理 ============

@router.get("/servers/{server_id}/services")
async def get_services(server_id: str, user_id: str = Depends(get_current_user_id)):
    """获取 systemd 服务列表"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return {"services": await remote_ops.get_services(server)}


@router.post("/servers/{server_id}/services/{unit}/action")
async def service_action(
    server_id: str, unit: str, request: ServiceActionRequest,
    user_id: str = Depends(get_current_user_id),
):
    """执行服务操作（start/stop/restart）"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    result = await remote_ops.service_action(server, unit, request.action)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/servers/{server_id}/privileges")
async def get_privileges(server_id: str, user_id: str = Depends(get_current_user_id)):
    """检测 sudo 可用性"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return await remote_ops.check_privileges(server)


# ============ 告警 ============

@router.get("/alerts", response_model=List[AlertRuleResponse])
async def get_alerts(user_id: str = Depends(get_current_user_id)):
    """获取告警规则"""
    return alert_engine.get_rules(user_id)


@router.post("/alerts", response_model=AlertRuleResponse)
async def create_alert(
    request: AlertRuleCreateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """新建告警规则"""
    return alert_engine.create_rule(user_id, request)


@router.put("/alerts/{rule_id}", response_model=AlertRuleResponse)
async def update_alert(
    rule_id: str, request: AlertRuleUpdateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """更新告警规则"""
    updated = alert_engine.update_rule(user_id, rule_id, request)
    if not updated:
        raise HTTPException(status_code=404, detail="告警规则不存在")
    return updated


@router.delete("/alerts/{rule_id}")
async def delete_alert(rule_id: str, user_id: str = Depends(get_current_user_id)):
    """删除告警规则"""
    if not alert_engine.delete_rule(user_id, rule_id):
        raise HTTPException(status_code=404, detail="告警规则不存在")
    return {"success": True}


@router.get("/alerts/logs")
async def get_alert_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    user_id: str = Depends(get_current_user_id),
):
    """获取告警触发记录（含未读数）"""
    return alert_engine.get_logs(user_id, page=page, page_size=page_size)


@router.put("/alerts/logs/read")
async def mark_alert_logs_read(user_id: str = Depends(get_current_user_id)):
    """标记告警记录全部已读"""
    alert_engine.mark_logs_read(user_id)
    return {"success": True}


# ============ 设置 ============

@router.get("/settings")
async def get_settings(user_id: str = Depends(get_current_user_id)):
    """获取监控设置"""
    return MonitorServerService.get_settings(user_id)


@router.put("/settings")
async def save_settings(request: MonitorSettings, user_id: str = Depends(get_current_user_id)):
    """保存监控设置"""
    MonitorServerService.save_settings(user_id, request)
    return {"success": True}
