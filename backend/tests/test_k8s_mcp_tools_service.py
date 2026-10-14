"""K8s MCP 工具服务层测试（第一部分：校验/过滤/grep/查询编排）"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.k8s_mcp_tools_service import (
    K8sMcpToolsService, LOG_TAIL_MAX, DEFAULT_TAIL, MAX_GREP_MATCH_LINES,
    LOG_FILE_MAX_BYTES,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ---------- 配置与命名空间白名单 ----------

def _config(ns_filter="[]"):
    return {"id": "c1", "name": "gmdos-dev", "server": "https://x:6443",
            "namespace_filter": ns_filter}


def test_load_config_raises_when_missing():
    with patch("app.services.k8s_mcp_tools_service.K8sToolService.get_config_by_id",
               return_value=None):
        with pytest.raises(ValueError, match="不存在"):
            K8sMcpToolsService._load_config("u1", "c1")


def test_load_config_returns_config():
    with patch("app.services.k8s_mcp_tools_service.K8sToolService.get_config_by_id",
               return_value=_config()) as m:
        assert K8sMcpToolsService._load_config("u1", "c1")["id"] == "c1"
        m.assert_called_once_with("u1", "c1")


def test_check_namespace_allowed_rejects():
    cfg = _config('["desk-dev","ai-work"]')
    with pytest.raises(ValueError, match="namespace_filter"):
        K8sMcpToolsService._check_namespace_allowed(cfg, "kube-system")
    K8sMcpToolsService._check_namespace_allowed(cfg, "desk-dev")          # 白名单内放行
    K8sMcpToolsService._check_namespace_allowed(_config("[]"), "any-ns")  # 未配置=全放行


# ---------- Pod 过滤 ----------

def _pod(name, phase="Running", status="Running", restarts=0, ns="desk-dev"):
    return {"name": name, "namespace": ns, "phase": phase, "status": status,
            "restarts": restarts, "ready": "1/1", "node": "n1", "pod_ip": "10.0.0.1",
            "created_at": None, "containers": ["app"]}


def _summary(name, phase="Running", restarts=0, ns="desk-dev"):
    """构造 K8sPodSummary（_pod_to_summary 的真实返回类型，供 model_dump 断言）"""
    from datetime import datetime
    from app.models.k8s_tool_models import K8sPodSummary
    return K8sPodSummary(name=name, namespace=ns, phase=phase, status=phase,
                         ready="1/1", restarts=restarts, node="n1", pod_ip="10.0.0.1",
                         created_at=datetime(2026, 10, 14), containers=["app"])


def test_filter_pods_by_keyword_and_status():
    items = [_pod("gmdos-admin-svc-abc"), _pod("wework-flow-xyz"),
             _pod("gmdos-admin-svc-crash", phase="Running", status="CrashLoopBackOff", restarts=5)]
    out = K8sMcpToolsService.filter_pods(items, keyword="gmdos-admin")
    assert len(out) == 2
    out = K8sMcpToolsService.filter_pods(items, status="CrashLoopBackOff")
    assert [p["name"] for p in out] == ["gmdos-admin-svc-crash"]
    out = K8sMcpToolsService.filter_pods(items)      # 不过滤
    assert len(out) == 3


# ---------- tail 上限 ----------

def test_validate_tail_lines_caps():
    assert K8sMcpToolsService.validate_tail_lines(None) == DEFAULT_TAIL
    assert K8sMcpToolsService.validate_tail_lines(100) == 100
    assert K8sMcpToolsService.validate_tail_lines(10 ** 9) == LOG_TAIL_MAX
    with pytest.raises(ValueError):
        K8sMcpToolsService.validate_tail_lines(0)
    with pytest.raises(ValueError):
        K8sMcpToolsService.validate_tail_lines(-5)


# ---------- grep ----------

def test_grep_log_filters_lines():
    text = "INFO ok\nERROR boom\nINFO fine\nCaused by: java.lang.Exception\nWARN x\n"
    out = K8sMcpToolsService.grep_log(text, r"ERROR|Caused by")
    assert out["matched"] == 2
    assert out["matched_lines"] == ["ERROR boom", "Caused by: java.lang.Exception"]
    assert out["total_lines"] == 5


def test_grep_log_invalid_pattern():
    with pytest.raises(ValueError, match="grep"):
        K8sMcpToolsService.grep_log("x", "(unclosed")


def test_grep_log_caps_matches():
    text = "ERROR line\n" * 500
    out = K8sMcpToolsService.grep_log(text, "ERROR")
    assert out["matched"] == 500
    assert len(out["matched_lines"]) == MAX_GREP_MATCH_LINES
    assert out["truncated"] is True


# ---------- 查询编排（mock bundle） ----------

@pytest.fixture
def bundle_ctx():
    """patch 配置加载与 build_client，返回可控 bundle

    cm.__aenter__ 返回单个 bundle 对象（与真实 build_client yield ClientBundle 一致），
    _async_config_bundle 解包后 yield (config, bundle)。
    """
    config = _config('[]')
    bundle = MagicMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=bundle)
    cm.__aexit__ = AsyncMock(return_value=False)
    with patch("app.services.k8s_mcp_tools_service.K8sToolService.get_config_by_id",
               return_value=config), \
         patch("app.services.k8s_mcp_tools_service.build_client", return_value=cm):
        yield bundle


@pytest.mark.anyio
async def test_list_pods_all_namespaces_filtered_by_ns_filter(bundle_ctx):
    # 换成带白名单的 config：全集群查询仍受 namespace_filter 约束
    config = _config('["desk-dev"]')
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=bundle_ctx)
    cm.__aexit__ = AsyncMock(return_value=False)
    p1, p2 = MagicMock(), MagicMock()
    p1.metadata.namespace = "desk-dev"
    p2.metadata.namespace = "kube-system"
    all_pods = MagicMock()
    all_pods.items = [p1, p2]
    bundle_ctx.core_v1.list_pod_for_all_namespaces = AsyncMock(return_value=all_pods)
    with patch("app.services.k8s_mcp_tools_service.K8sToolService.get_config_by_id",
               return_value=config), \
         patch("app.services.k8s_mcp_tools_service.build_client", return_value=cm), \
         patch("app.services.k8s_mcp_tools_service._pod_to_summary",
               side_effect=lambda p: _summary("pod-x", ns=p.metadata.namespace)):
        result = await K8sMcpToolsService.list_pods(
            "u1", "c1", namespace=None, keyword=None, status=None, limit=None)
    assert result["total"] == 1 and result["items"][0]["namespace"] == "desk-dev"


@pytest.mark.anyio
async def test_list_pods_namespaced_rejects_filtered_ns(bundle_ctx):
    # bundle_ctx 的 config ns_filter='[]' 不拦；这里换成带白名单的 config 验证拦截
    config = _config('["desk-dev"]')
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=bundle_ctx)
    cm.__aexit__ = AsyncMock(return_value=False)
    with patch("app.services.k8s_mcp_tools_service.K8sToolService.get_config_by_id",
               return_value=config), \
         patch("app.services.k8s_mcp_tools_service.build_client", return_value=cm):
        # 错误包装职责在 MCP 协议层 _call，编排层直接抛 ValueError
        with pytest.raises(ValueError, match="namespace_filter"):
            await K8sMcpToolsService.list_pods(
                "u1", "c1", namespace="kube-system", keyword=None, status=None, limit=None)


@pytest.mark.anyio
async def test_list_clusters(bundle_ctx):
    from datetime import datetime
    from app.models.k8s_tool_models import K8sConfigResponse
    dto = K8sConfigResponse(
        id="c1", user_id="u1", name="gmdos-dev", source_type="manual",
        cluster_name="gmdos-dev", context_name="gmdos-dev", server="https://x:6443",
        auth_type="bearer_token", has_auth_data=True, has_ca_cert=False,
        namespace_filter=[], is_metrics_available=False,
        created_at=datetime(2026, 10, 14), updated_at=datetime(2026, 10, 14),
    )
    with patch("app.services.k8s_mcp_tools_service.K8sToolService.get_configs",
               return_value=[dto]):
        out = await K8sMcpToolsService.list_clusters("u1")
    assert out["total"] == 1 and out["clusters"][0]["name"] == "gmdos-dev"


@pytest.mark.anyio
async def test_list_namespaces_applies_filter(bundle_ctx):
    bundle = bundle_ctx
    ns = MagicMock()
    ns.name = "desk-dev"
    ns2 = MagicMock()
    ns2.name = "kube-system"
    with patch("app.services.k8s_mcp_tools_service.K8sResourceService.list_namespaces",
               AsyncMock(return_value=[ns, ns2])):
        # ns_filter='[]' → 全部返回
        out = await K8sMcpToolsService.list_namespaces("u1", "c1")
        assert out["total"] == 2
    # 带白名单的 config
    config = _config('["desk-dev"]')
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=(config, bundle))
    cm.__aexit__ = AsyncMock(return_value=False)
    with patch("app.services.k8s_mcp_tools_service.K8sToolService.get_config_by_id",
               return_value=config), \
         patch("app.services.k8s_mcp_tools_service.build_client", return_value=cm), \
         patch("app.services.k8s_mcp_tools_service.K8sResourceService.list_namespaces",
               AsyncMock(return_value=[ns, ns2])):
        out = await K8sMcpToolsService.list_namespaces("u1", "c1")
        assert out["namespaces"] == ["desk-dev"]


@pytest.mark.anyio
async def test_get_pod(bundle_ctx):
    bundle = bundle_ctx
    detail = {"name": "gmdos-admin-svc-abc", "namespace": "desk-dev"}
    with patch("app.services.k8s_mcp_tools_service.K8sResourceService.get_pod_detail",
               AsyncMock(return_value=detail)) as m:
        out = await K8sMcpToolsService.get_pod("u1", "c1", "desk-dev", "gmdos-admin-svc-abc")
    assert out == detail
    m.assert_awaited_once_with(bundle, "gmdos-admin-svc-abc", "desk-dev")


@pytest.mark.anyio
async def test_get_pod_events_filters_by_pod_prefix(bundle_ctx):
    # list_events 真实返回 K8sEventInfo（Pydantic）列表，实现调 model_dump()
    from app.models.k8s_tool_models import K8sEventInfo

    def _ev(name):
        return K8sEventInfo(type="Warning", reason="BackOff", message="x",
                            object_kind="Pod", object_name=name,
                            object_namespace="desk-dev", count=3)
    with patch("app.services.k8s_mcp_tools_service.K8sResourceService.list_events",
               AsyncMock(return_value=[_ev("gmdos-admin-svc-abc"), _ev("other-pod-xyz")])) as m:
        out = await K8sMcpToolsService.get_pod_events(
            "u1", "c1", namespace="desk-dev", pod="gmdos-admin-svc-abc")
    m.assert_awaited_once()
    assert out["total"] == 1 and out["events"][0]["object_name"] == "gmdos-admin-svc-abc"


@pytest.mark.anyio
async def test_get_pod_events_all_namespaces(bundle_ctx):
    bundle = bundle_ctx
    e = MagicMock()
    e.type = "Warning"
    e.reason = "BackOff"
    e.message = "crash"
    io = MagicMock()
    io.kind = "Pod"
    io.name = "p-abc"
    io.namespace = "desk-dev"
    e.involved_object = io
    e.count = 2
    e.first_timestamp = None
    e.last_timestamp = None
    event_list = MagicMock()
    event_list.items = [e]
    bundle.core_v1.list_event_for_all_namespaces = AsyncMock(return_value=event_list)
    out = await K8sMcpToolsService.get_pod_events("u1", "c1", namespace=None, pod=None)
    assert out["total"] == 1 and out["events"][0]["object_name"] == "p-abc"


@pytest.mark.anyio
async def test_get_pod_logs_text_with_grep_and_previous(bundle_ctx):
    logs = "INFO ok\nERROR boom\nERROR again\n"
    with patch("app.services.k8s_mcp_tools_service.K8sResourceService.get_pod_logs",
               AsyncMock(return_value=logs)) as m:
        out = await K8sMcpToolsService.get_pod_logs_text(
            "u1", "c1", "desk-dev", "p-abc", container=None, tail_lines=100,
            previous=True, since_seconds=3600, grep="ERROR")
    m.assert_awaited_once()
    args = m.call_args
    assert args[0][4] == 100            # tail_lines 位置参数
    assert args[0][5] is True           # previous
    assert args[0][6] == 3600           # since_seconds
    assert out["returned_lines"] == 2   # grep 过滤后
    assert out["text"] == "ERROR boom\nERROR again"
    assert out["grep"]["matched"] == 2 and out["grep"]["total_lines"] == 3


# ---------- Task 5: 落盘 / overview / 映射 ----------

def test_build_log_filename_rejects_path_traversal():
    with pytest.raises(ValueError):
        K8sMcpToolsService.build_log_filename("c", "ns", "../../etc/passwd", None, False)
    with pytest.raises(ValueError):
        K8sMcpToolsService.build_log_filename("c", "ns", "Pod_BadName", None, False)
    with pytest.raises(ValueError):
        K8sMcpToolsService.build_log_filename("c", "ns", "ok-pod", "bad container", False)


def test_build_log_filename_sanitizes_cluster_and_ns():
    name = K8sMcpToolsService.build_log_filename(
        "gmdos dev(自签名)", "desk-dev", "gmdos-admin-svc-abc", "app", True)
    assert name == "gmdos-dev-desk-dev-gmdos-admin-svc-abc-app-previous.log"


def test_write_log_file_truncates(tmp_path, monkeypatch):
    monkeypatch.setattr(K8sMcpToolsService, "LOGS_DIR", tmp_path)
    big = "x" * (LOG_FILE_MAX_BYTES + 100)
    out = K8sMcpToolsService.write_log_file(big, "a.log")
    data = (tmp_path / "a.log").read_bytes()
    assert len(data) <= LOG_FILE_MAX_BYTES
    assert out["truncated"] is True and out["size_bytes"] == len(data)


def test_write_log_file_normal(tmp_path, monkeypatch):
    monkeypatch.setattr(K8sMcpToolsService, "LOGS_DIR", tmp_path)
    out = K8sMcpToolsService.write_log_file("line1\nline2\n", "b.log")
    assert out["truncated"] is False and out["lines"] == 2
    assert str(out["path"]).endswith("b.log")


@pytest.mark.anyio
async def test_download_pod_logs_end_to_end(bundle_ctx, tmp_path, monkeypatch):
    monkeypatch.setattr(K8sMcpToolsService, "LOGS_DIR", tmp_path)
    with patch("app.services.k8s_mcp_tools_service.K8sResourceService.get_pod_logs",
               AsyncMock(return_value="ERROR a\nINFO b\n")):
        out = await K8sMcpToolsService.download_pod_logs(
            "u1", "c1", "desk-dev", "gmdos-admin-svc-abc", container=None, previous=False)
    assert out["lines"] == 2 and out["truncated"] is False
    assert "gmdos-dev-desk-dev-gmdos-admin-svc-abc-all.log" in str(out["path"])


@pytest.mark.anyio
async def test_cluster_overview_aggregates(bundle_ctx):
    abnormal = _pod("crash-pod-abc", status="CrashLoopBackOff", restarts=7)
    normal = _pod("ok-pod-abc")
    with patch("app.services.k8s_mcp_tools_service.K8sMcpToolsService.list_pods",
               AsyncMock(return_value={"items": [abnormal, normal], "total": 2})), \
         patch("app.services.k8s_mcp_tools_service.K8sMcpToolsService.get_pod_events",
               AsyncMock(return_value={"events": [], "total": 0})):
        out = await K8sMcpToolsService.get_cluster_overview("u1", "c1", "desk-dev")
    assert [p["name"] for p in out["abnormal_pods"]] == ["crash-pod-abc"]
    assert out["warning_events"] == []


@pytest.mark.anyio
async def test_cluster_overview_filters_old_events(bundle_ctx):
    from datetime import datetime, timedelta
    recent_ev = {"type": "Warning", "reason": "BackOff", "message": "x",
                 "object_kind": "Pod", "object_name": "p-a", "object_namespace": "ns",
                 "count": 1, "first_seen": None,
                 "last_seen": datetime.now() - timedelta(minutes=5)}
    old_ev = {**recent_ev, "object_name": "p-b",
              "last_seen": datetime.now() - timedelta(hours=3)}
    with patch("app.services.k8s_mcp_tools_service.K8sMcpToolsService.list_pods",
               AsyncMock(return_value={"items": [], "total": 0})), \
         patch("app.services.k8s_mcp_tools_service.K8sMcpToolsService.get_pod_events",
               AsyncMock(return_value={"events": [recent_ev, old_ev], "total": 2})):
        out = await K8sMcpToolsService.get_cluster_overview("u1", "c1", "desk-dev")
    assert [e["object_name"] for e in out["warning_events"]] == ["p-a"]


@pytest.mark.anyio
async def test_mapping_bridge_calls_service():
    saved = {"project_key": "p", "cluster_id": "c1", "cluster_name": "gmdos-dev"}
    with patch("app.services.k8s_mcp_tools_service.K8sServiceMappingService.lookup_mapping",
               return_value=saved) as m:
        out = await K8sMcpToolsService.lookup_service_mapping("u1", "p")
    m.assert_called_once_with("u1", "p")
    assert out["found"] is True and out["cluster_name"] == "gmdos-dev"


@pytest.mark.anyio
async def test_lookup_mapping_miss_returns_found_false():
    with patch("app.services.k8s_mcp_tools_service.K8sServiceMappingService.lookup_mapping",
               return_value=None):
        out = await K8sMcpToolsService.lookup_service_mapping("u1", "nope")
    assert out["found"] is False


@pytest.mark.anyio
async def test_save_service_mapping_validates_target(bundle_ctx):
    with patch("app.services.k8s_mcp_tools_service.K8sServiceMappingService.save_mapping",
               return_value={"project_key": "p"}) as m:
        out = await K8sMcpToolsService.save_service_mapping(
            "u1", "p", "c1", "desk-dev", "dep", None, "evidence", "jenkinsfile")
    m.assert_called_once()
    assert out["saved"] is True


@pytest.mark.anyio
async def test_save_service_mapping_rejects_bad_namespace(bundle_ctx):
    config = _config('["desk-dev"]')
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=bundle_ctx)
    cm.__aexit__ = AsyncMock(return_value=False)
    with patch("app.services.k8s_mcp_tools_service.K8sToolService.get_config_by_id",
               return_value=config), \
         patch("app.services.k8s_mcp_tools_service.build_client", return_value=cm):
        with pytest.raises(ValueError, match="namespace_filter"):
            await K8sMcpToolsService.save_service_mapping(
                "u1", "p", "c1", "kube-system", None, None, "e", "traversal")


@pytest.mark.anyio
async def test_list_pods_namespaced_with_pydantic_items(bundle_ctx):
    """回归：K8sResourceService.list_pods 真实返回 K8sPodSummary 模型列表，
    MCP 层必须 model_dump 后再过滤（此前直接 .get 会 AttributeError）"""
    config = _config('["desk-dev"]')
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=bundle_ctx)
    cm.__aexit__ = AsyncMock(return_value=False)
    from app.models.k8s_tool_models import K8sPodSummary
    real_items = [_summary("gmdos-admin-svc-abc", restarts=2),
                  _summary("wework-flow-xyz")]
    with patch("app.services.k8s_mcp_tools_service.K8sToolService.get_config_by_id",
               return_value=config), \
         patch("app.services.k8s_mcp_tools_service.build_client", return_value=cm), \
         patch("app.services.k8s_mcp_tools_service.K8sResourceService.list_pods",
               AsyncMock(return_value={"items": real_items, "total": 2})):
        out = await K8sMcpToolsService.list_pods(
            "u1", "c1", namespace="desk-dev", keyword="gmdos-admin",
            status=None, limit=None)
    assert out["total"] == 1
    assert out["items"][0]["name"] == "gmdos-admin-svc-abc"
    assert out["items"][0]["restarts"] == 2
