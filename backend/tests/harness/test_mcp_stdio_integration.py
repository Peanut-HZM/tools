"""stdio transport 端到端集成测试（P2-①c）

用 sys.executable 启动真实 FastMCP 子进程，走完整 stdin/stdout 链路。
不 mock 任何 mcp 内部组件。
"""
import sys
import textwrap

import pytest
import pytest_asyncio

from app.services.harness.mcp_client import McpClient, McpConnectionError

# 临时 MCP server 脚本：提供一个 echo 工具
# 注意：mcp 2.x 中 FastMCP 已更名为 MCPServer
_SERVER_SCRIPT = textwrap.dedent(
    """
    import sys
    from mcp.server.mcpserver import MCPServer

    mcp = MCPServer("echo-server")

    @mcp.tool()
    def echo(text: str) -> str:
        \"\"\"Echo the input text back\"\"\"
        return f"echo: {text}"

    if __name__ == "__main__":
        mcp.run()  # 默认 stdio transport
    """
)


@pytest_asyncio.fixture
async def echo_client(tmp_path):
    """启动真实 stdio echo server 并完成握手的 client"""
    script = tmp_path / "echo_server.py"
    script.write_text(_SERVER_SCRIPT, encoding="utf-8")
    client = McpClient(
        f"python {script}",
        transport="stdio",
        command={"command": sys.executable, "args": [str(script)]},
        timeout=60,
    )
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_stdio_end_to_end_tools_list(echo_client):
    """真实子进程：connect → tools_list 返回 echo 工具"""
    tools = await echo_client.tools_list()
    names = [t["name"] for t in tools]
    assert "echo" in names


@pytest.mark.asyncio
async def test_stdio_end_to_end_tools_call(echo_client):
    """真实子进程：tools_call 拿到真实返回值"""
    result = await echo_client.tools_call("echo", {"text": "hello"})
    assert result["isError"] is False
    assert any("echo: hello" in c.get("text", "") for c in result["content"])


@pytest.mark.asyncio
async def test_stdio_command_not_found():
    """command 指向不存在的可执行文件 → McpConnectionError"""
    client = McpClient(
        "no-such-binary-xyz",
        transport="stdio",
        command={"command": "no-such-binary-xyz-12345"},
        timeout=30,
    )
    with pytest.raises(McpConnectionError):
        await client.connect()
