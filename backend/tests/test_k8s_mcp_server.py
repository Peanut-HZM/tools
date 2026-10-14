"""K8s MCP Server 协议层与认证测试

- 协议层：mcp 2.x InMemoryTransport 内存直连（不走网络）
- 认证层：TestClient 打挂载后的 /mcp/k8s，断言 401 行为
"""
import os
import sys

import pytest
from unittest.mock import patch, AsyncMock

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from mcp.client._memory import InMemoryTransport
from mcp.client.session import ClientSession

from app.mcp_server.k8s_server import server
from app.mcp_server import auth as mcp_auth

EXPECTED_TOOLS = {
    "list_clusters", "list_namespaces", "list_pods", "get_pod", "get_pod_events",
    "get_pod_logs", "download_pod_logs", "get_cluster_overview",
    "lookup_service_mapping", "save_service_mapping",
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def as_user_u1():
    token = mcp_auth.set_current_mcp_user_id("u1")
    yield "u1"
    mcp_auth.reset_current_mcp_user_id(token)


@pytest.mark.anyio
async def test_tool_set_is_exactly_readonly_ten():
    """只读边界：工具集合必须恰好等于 10 个只读工具，多一个都失败"""
    async with InMemoryTransport(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            assert names == EXPECTED_TOOLS
            forbidden = {"exec", "delete_pod", "scale", "restart", "patch",
                         "create", "apply", "get_secret", "get_configmap", "get_pvc"}
            assert not (names & forbidden)


@pytest.mark.anyio
async def test_call_list_clusters_via_mcp(as_user_u1):
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
        async with InMemoryTransport(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("list_clusters", {})
    assert result.is_error is False
    assert "gmdos-dev" in result.content[0].text


@pytest.mark.anyio
async def test_tool_error_returned_as_text(as_user_u1):
    with patch("app.services.k8s_mcp_tools_service.K8sToolService.get_config_by_id",
               return_value=None):
        async with InMemoryTransport(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "get_pod", {"cluster_id": "c1", "namespace": "desk-dev", "pod": "p"})
    assert "Error" in result.content[0].text
    assert "不存在" in result.content[0].text


@pytest.mark.anyio
async def test_missing_identity_returns_error_text():
    """不设置 contextvar：工具必须返回 Error 文本而非崩溃"""
    async with InMemoryTransport(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("list_clusters", {})
    assert "Error" in result.content[0].text


def test_mcp_endpoint_auth_401():
    """认证边界：无 token / 错误 token → 一律 401，绝不放行

    用裸 TestClient（不进 with）避免触发主 app lifespan——
    StreamableHTTPSessionManager.run() 全进程只允许一次，生产由 uvicorn
    单次 lifespan 启动；「有效 token 放行后的完整链路」由协议层
    contextvar 用例（as_user_u1）与端到端验收覆盖。
    """
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    assert client.post("/mcp/k8s", json={}).status_code == 401
    assert client.post("/mcp/k8s", json={},
                       headers={"Authorization": "Bearer pat_wrong"}).status_code == 401
