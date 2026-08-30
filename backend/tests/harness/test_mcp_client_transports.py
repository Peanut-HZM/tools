"""McpClient 多 transport 单元测试（P2-①c）

mock 各 transport context manager，验证 connect() 分发正确、
stdio 参数构建正确、SSRF 校验只对 url 型 transport 生效。
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.harness.mcp_client import McpClient, McpConnectionError


@pytest.mark.asyncio
async def test_sse_uses_sse_client():
    """transport=sse（默认）→ 走 sse_client"""
    client = McpClient("http://localhost:3000", allow_private_hosts=True)
    with patch("app.services.harness.mcp_client.sse_client") as mock_sse:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
        cm.__aexit__ = AsyncMock(return_value=False)
        mock_sse.return_value = cm
        with patch("app.services.harness.mcp_client.ClientSession") as mock_cls:
            mock_cls.return_value = AsyncMock()
            await client.connect()
    mock_sse.assert_called_once()
    assert client.transport == "sse"


@pytest.mark.asyncio
async def test_http_uses_streamable_client():
    """transport=http → 走 streamable_http_client；3 元组适配为 (read, write)"""
    client = McpClient(
        "http://localhost:3000", transport="http", allow_private_hosts=True
    )
    with patch(
        "app.services.harness.mcp_client.streamable_http_client"
    ) as mock_http:
        cm = MagicMock()
        # streamable http 产出 3 元组 (read, write, get_session_id)
        cm.__aenter__ = AsyncMock(
            return_value=(MagicMock(), MagicMock(), MagicMock())
        )
        cm.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value = cm
        with patch("app.services.harness.mcp_client.ClientSession") as mock_cls:
            mock_cls.return_value = AsyncMock()
            await client.connect()
    mock_http.assert_called_once()
    assert client.transport == "http"


@pytest.mark.asyncio
async def test_stdio_uses_stdio_client():
    """transport=stdio → 走 stdio_client，StdioServerParameters 参数正确"""
    client = McpClient(
        "npx -y @modelcontextprotocol/server-everything",
        transport="stdio",
        command={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-everything"],
            "env": {"FOO": "bar"},
        },
    )
    with patch("app.services.harness.mcp_client.stdio_client") as mock_stdio:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
        cm.__aexit__ = AsyncMock(return_value=False)
        mock_stdio.return_value = cm
        with patch("app.services.harness.mcp_client.ClientSession") as mock_cls:
            mock_cls.return_value = AsyncMock()
            await client.connect()
    mock_stdio.assert_called_once()
    params = mock_stdio.call_args[0][0]
    assert params.command == "npx"
    assert params.args == ["-y", "@modelcontextprotocol/server-everything"]
    # 显式 env 应叠加在 SDK 默认最小环境之上
    assert params.env["FOO"] == "bar"
    assert "PATH" in params.env


def test_stdio_skips_url_validation():
    """stdio 不做 SSRF URL 校验（server_url 仅展示用）"""
    # 若误走 validate_url 会抛 McpConnectionError；不抛即通过
    McpClient("任何展示字符串", transport="stdio", command={"command": "npx"})


def test_http_validates_url():
    """http transport 走 SSRF 校验：内网默认拒绝"""
    with pytest.raises(McpConnectionError):
        McpClient("http://192.168.1.1:3000", transport="http")


def test_stdio_command_required():
    """stdio 缺 command 配置 → McpConnectionError"""
    with pytest.raises(McpConnectionError):
        McpClient("demo", transport="stdio", command=None)
    with pytest.raises(McpConnectionError):
        McpClient("demo", transport="stdio", command={"args": ["a"]})


def test_stdio_accepts_command_json_string():
    """command 也可传 JSON 字符串（与 DB 存储格式对齐）"""
    client = McpClient(
        "demo",
        transport="stdio",
        command=json.dumps({"command": "python", "args": ["-m", "demo"]}),
    )
    assert client._server_params.command == "python"


def test_unsupported_transport_rejected():
    """非法 transport → McpConnectionError"""
    with pytest.raises(McpConnectionError):
        McpClient("http://localhost:3000", transport="grpc", allow_private_hosts=True)


@pytest.mark.asyncio
async def test_disconnect_exits_transport_ctx():
    """disconnect 应统一退出 _transport_ctx"""
    client = McpClient("http://localhost:3000", allow_private_hosts=True)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
    cm.__aexit__ = AsyncMock(return_value=False)
    client._transport_ctx = cm
    client._session = AsyncMock()
    await client.disconnect()
    cm.__aexit__.assert_called_once()
    assert client._transport_ctx is None
