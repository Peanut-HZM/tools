"""McpClient 单元测试

使用 mock 模拟 SSE server，测试 connect / tools_list / tools_call / disconnect。
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.harness.mcp_client import McpClient, McpConnectionError


@pytest.mark.asyncio
async def test_mcp_client_connect_success():
    """测试成功连接"""
    # allow_private_hosts=True 因为 localhost 是环回地址，SSRF 防护默认拒绝
    client = McpClient(server_url="http://localhost:3000", allow_private_hosts=True)

    with patch("app.services.harness.mcp_client.ClientSession") as mock_cls:
        # MagicMock 原生支持 __aenter__（SDK 2.x 需先进入 session context）
        mock_session = MagicMock()
        mock_cls.return_value = mock_session
        mock_session.initialize = AsyncMock()

        with patch.object(client, "_connect_sse", new_callable=AsyncMock) as mock_sse:
            mock_sse.return_value = (AsyncMock(), AsyncMock())
            await client.connect()

        assert client._session is not None
        mock_session.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_client_connect_failure():
    """测试连接失败抛 McpConnectionError"""
    client = McpClient(server_url="http://localhost:3000", allow_private_hosts=True)

    with patch.object(client, "_connect_sse", new_callable=AsyncMock) as mock_sse:
        mock_sse.side_effect = Exception("Connection refused")

        with pytest.raises(McpConnectionError):
            await client.connect()


@pytest.mark.asyncio
async def test_mcp_client_tools_list():
    """测试 tools/list 返回工具列表"""
    client = McpClient(server_url="http://localhost:3000", allow_private_hosts=True)
    mock_session = AsyncMock()
    client._session = mock_session

    # mock list_tools 返回（注意：MagicMock 的 name 参数是 mock 自身名而非属性）
    mock_result = MagicMock()
    tool1 = MagicMock()
    tool1.name = "tool1"
    tool1.description = "Tool 1"
    tool1.inputSchema = {"type": "object"}
    tool2 = MagicMock()
    tool2.name = "tool2"
    tool2.description = "Tool 2"
    tool2.inputSchema = {"type": "object"}
    mock_result.tools = [tool1, tool2]
    mock_session.list_tools = AsyncMock(return_value=mock_result)

    tools = await client.tools_list()

    assert len(tools) == 2
    assert tools[0]["name"] == "tool1"
    assert tools[1]["description"] == "Tool 2"


@pytest.mark.asyncio
async def test_mcp_client_tools_call_success():
    """测试工具调用成功"""
    client = McpClient(server_url="http://localhost:3000", allow_private_hosts=True)
    mock_session = AsyncMock()
    client._session = mock_session

    mock_result = MagicMock()
    # SDK 2.x 字段名为 is_error（tools_call 兼容读取 is_error/isError）
    mock_result.is_error = False
    mock_result.content = [MagicMock(type="text", text="result")]
    mock_session.call_tool = AsyncMock(return_value=mock_result)

    result = await client.tools_call("tool1", {"arg": "value"})

    assert result["isError"] is False
    assert result["content"][0]["text"] == "result"


@pytest.mark.asyncio
async def test_mcp_client_tools_call_timeout():
    """测试工具调用超时"""
    import asyncio

    client = McpClient(server_url="http://localhost:3000", timeout=1, allow_private_hosts=True)
    mock_session = AsyncMock()
    client._session = mock_session

    async def slow_call(*args, **kwargs):
        await asyncio.sleep(2)
        return MagicMock()

    mock_session.call_tool = slow_call

    with pytest.raises(asyncio.TimeoutError):
        await client.tools_call("tool1", {})


@pytest.mark.asyncio
async def test_mcp_client_disconnect():
    """测试断开连接"""
    client = McpClient(server_url="http://localhost:3000", allow_private_hosts=True)
    mock_session = AsyncMock()
    client._session = mock_session

    await client.disconnect()

    assert client._session is None
    # SDK 2.x：通过 __aexit__ 关闭 session（无 close() 方法）
    mock_session.__aexit__.assert_called_once()
