"""McpClient — MCP SSE 客户端

Phase 3-Plan-1A: MCP 工具支持核心骨架

实现 MCP 协议的 SSE transport，提供：
- connect(): 建立 SSE 长连接 + MCP 握手
- tools_list(): 调用 MCP tools/list
- tools_call(): 调用 MCP tools/call
- disconnect(): 关闭连接

注意：McpClient 仅供 McpTool 内部使用。所有外部调用必须通过 ToolRegistry.execute()
的 get_tools_for_agent() 鉴权（agent allowlist），不可直接调用 McpClient.tools_call。

架构保障：
- McpClient 不暴露给 LLM/agent 层
- McpTool 通过 ToolRegistry.register_dynamic() 注册
- ToolRegistry.execute() 校验 call.name 是否在 agent 的允许工具列表中
- 未授权的工具调用返回 ToolResult.error("未被授权")

参考: https://modelcontextprotocol.io/specification
"""
import asyncio
import ipaddress
import json
import logging
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

try:
    from mcp.client.sse import sse_client
    from mcp.client.stdio import (
        stdio_client,
        StdioServerParameters,
        get_default_environment,
    )
    from mcp.client.streamable_http import streamable_http_client
    from mcp import ClientSession
except ImportError:
    raise ImportError(
        "mcp package not installed. Run: pip install mcp>=1.0.0"
    )

logger = logging.getLogger(__name__)


# SSRF 防护：拒绝这些网段（与 http_tool.py 保持一致）
_BLOCKED_NETWORKS = [
    # IPv4 私有/环回/链路本地网段
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    # IPv6 环回/链路本地/私有网段
    ipaddress.ip_network("::1/128"),           # IPv6 环回
    ipaddress.ip_network("fc00::/7"),          # IPv6 唯一本地 (ULA)
    ipaddress.ip_network("::ffff:0:0/96"),     # IPv4 映射的 IPv6
]

# 永远拒绝的网段（即使 allow_private_hosts=True 也生效）
# 用于阻止云元数据服务（SSRF 经典攻击向量）以及链路本地地址
_ALWAYS_BLOCKED_NETWORKS = [
    ipaddress.ip_network("169.254.0.0/16"),  # IPv4 云元数据（AWS/GCP/Azure）
    ipaddress.ip_network("fe80::/10"),         # IPv6 链路本地
]


class McpConnectionError(Exception):
    """MCP 连接失败"""
    pass


def sanitize_url(url: str) -> str:
    """清理 URL 用于日志输出：移除 userinfo（user:pass@），只保留 scheme+host+port

    示例:
        >>> sanitize_url("http://user:pass@host:3000/path")
        'http://host:3000'
    """
    try:
        parsed = urlsplit(url)
        # 移除 userinfo
        host = parsed.hostname or ""
        # 处理 IPv6 字面量
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        netloc = host
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        return urlunsplit(parsed._replace(netloc=netloc, path="", query="", fragment=""))
    except Exception:
        return "<invalid-url>"


def _check_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """检查 IP 是否在黑名单网段中，返回 True 表示被阻止

    对 IPv4 映射的 IPv6 地址（如 ::ffff:127.0.0.1）提取嵌入的 IPv4 进行检查。
    """
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    for network in _BLOCKED_NETWORKS:
        if ip in network:
            return True
    return False


def _check_ip_always_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """检查 IP 是否在永远阻止的网段中（即使 allow_private_hosts=True 也阻止）

    用于云元数据服务（169.254/16）和链路本地（fe80::/10），
    这是 SSRF 攻击的经典目标——任何环境下都不应允许连接到这些地址。
    """
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    for network in _ALWAYS_BLOCKED_NETWORKS:
        if ip in network:
            return True
    return False


def validate_url(url: str, allow_private_hosts: bool = False) -> None:
    """验证 MCP server URL 的安全性（SSRF 防护）

    检查项：
    - scheme 必须是 http:// 或 https://
    - 必须有 hostname
    - 不允许 userinfo（user:pass@host）
    - **永远**拒绝云元数据服务（169.254/16）和链路本地（fe80::/10）——即使
      allow_private_hosts=True 也生效。这是 SSRF 攻击最常见的目标。
    - 默认拒绝 loopback/RFC1918/ULA 网段
    - DNS 解析后再次检查所有 IP（防 DNS rebinding）

    Args:
        url: 待验证的 URL
        allow_private_hosts: True 则允许 RFC1918/loopback/ULA 网段
            （仅开发/测试环境使用）。注意：此参数**不会**影响云元数据
            服务和链路本地地址的拒绝逻辑。

    Raises:
        McpConnectionError: URL 不安全时抛出

    .. note::
        **DNS rebinding / TOCTOU 风险**：
        validate_url() 在此函数中解析一次 DNS，但 sse_client 内部会再次解析
        hostname。如果在两次解析之间攻击者修改 DNS 记录（典型的 rebinding
        攻击），validate_url 的检查可能被绕过。

        缓解措施：
        1. 对于固定 IP 部署，建议使用 IP 字面量 URL（如 http://10.0.0.1:3000）
        2. 在不信任 DNS 的环境（multi-tenant）中，应通过反向代理访问 MCP server，
           并在代理层做 IP 锁定
        3. MCP SDK 当前不支持 IP pinning，因此本函数无法完全消除此风险
    """
    try:
        parsed = urlsplit(url)
    except Exception as e:
        raise McpConnectionError(f"Invalid URL format: {e}")

    # scheme 校验
    if parsed.scheme not in ("http", "https"):
        raise McpConnectionError(
            f"Invalid URL scheme '{parsed.scheme}': only http/https allowed"
        )

    # hostname 校验
    hostname = parsed.hostname
    if not hostname:
        raise McpConnectionError("URL must contain a hostname")

    # userinfo 校验（user:pass@host 模式）
    if parsed.username or parsed.password:
        raise McpConnectionError("URL must not contain userinfo (user:pass@host)")

    # DNS 解析后检查所有 IP（防 DNS rebinding + 永远阻止云元数据）
    try:
        # 先尝试直接解析为 IP 字面量
        try:
            ip = ipaddress.ip_address(hostname)
            # 永远阻止的网段优先检查（即使 allow_private_hosts=True）
            if _check_ip_always_blocked(ip):
                raise McpConnectionError(
                    f"URL resolves to blocked network (metadata/link-local): {hostname}"
                )
            if not allow_private_hosts and _check_ip_blocked(ip):
                raise McpConnectionError(
                    f"URL hostname resolves to blocked network: {hostname}"
                )
            return
        except ValueError:
            pass  # 不是 IP 字面量，继续 DNS 解析

        # DNS 解析
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if not infos:
            raise McpConnectionError(f"Cannot resolve hostname: {hostname}")

        for info in infos:
            addr = info[4][0]
            try:
                ip = ipaddress.ip_address(addr)
                # 永远阻止的网段优先检查
                if _check_ip_always_blocked(ip):
                    raise McpConnectionError(
                        f"URL hostname '{hostname}' resolves to blocked IP "
                        f"(metadata/link-local): {addr}"
                    )
                if not allow_private_hosts and _check_ip_blocked(ip):
                    raise McpConnectionError(
                        f"URL hostname '{hostname}' resolves to blocked IP: {addr}"
                    )
            except McpConnectionError:
                raise
            except ValueError:
                # 无法解析为 IP 地址，跳过
                pass
    except McpConnectionError:
        raise
    except socket.gaierror as e:
        raise McpConnectionError(f"DNS resolution failed for '{hostname}': {e}")
    except Exception as e:
        raise McpConnectionError(f"URL validation failed: {e}")


class McpClient:
    """MCP SSE 客户端

    用法:
        client = McpClient("http://example.com:3000", timeout=30)
        await client.connect()
        tools = await client.tools_list()
        result = await client.tools_call("tool_name", {"arg": "value"})
        await client.disconnect()
    """

    def __init__(
        self,
        server_url: str = "",
        *,
        transport: str = "sse",
        command: dict | str | None = None,
        headers: dict | None = None,
        timeout: int = 30,
        allow_private_hosts: bool = False,
    ):
        """
        Args:
            server_url: SSE / streamable HTTP 端点；stdio 时仅作展示摘要
            transport: "sse" / "http" / "stdio"（P2-①c）
            command: stdio 启动配置 dict 或 JSON 字符串：
                {"command": "npx", "args": [...], "env": {...}}
            headers: 可选的 HTTP headers（如 Authorization），仅 url 型 transport
            timeout: 操作超时秒数
            allow_private_hosts: True 则允许内网地址（仅开发/测试用）
        """
        if transport not in ("sse", "http", "stdio"):
            raise McpConnectionError(f"Unsupported transport: {transport}")

        if transport == "stdio":
            # stdio 无 URL 语义，跳过 SSRF 校验；本地代码执行风险由 admin 门禁覆盖
            self._server_params = self._build_stdio_params(command)
        else:
            # SSRF 防护：在连接前验证 URL（sse / http 共用）
            validate_url(server_url, allow_private_hosts=allow_private_hosts)

        self.server_url = server_url
        self.transport = transport
        self.headers = headers or {}
        self.timeout = timeout
        self.allow_private_hosts = allow_private_hosts  # 保留供调用方检查
        self._session: ClientSession | None = None
        self._transport_ctx = None  # 统一持有当前 transport 的 async context manager

    @staticmethod
    def _build_stdio_params(command: dict | str | None) -> StdioServerParameters:
        """构建 stdio 启动参数。

        env 策略（安全）：默认使用 SDK 最小环境（get_default_environment()，
        只含 PATH/HOME 等基础变量），显式配置的 env 追加其上——
        不透传后端进程完整环境，防止 secrets 泄露给子进程。
        """
        if isinstance(command, str):
            try:
                command = json.loads(command)
            except json.JSONDecodeError as e:
                raise McpConnectionError(f"Invalid command JSON: {e}") from e
        if not isinstance(command, dict) or not str(command.get("command") or "").strip():
            raise McpConnectionError(
                'stdio transport requires command config: '
                '{"command": "...", "args": [...], "env": {...}}'
            )
        env = None
        if command.get("env"):
            env = get_default_environment()
            env.update(command["env"])
        return StdioServerParameters(
            command=command["command"],
            args=list(command.get("args") or []),
            env=env,
        )

    async def _connect_sse(self):
        """内部方法：建立 SSE 连接，返回 (read_stream, write_stream)"""
        self._transport_ctx = sse_client(self.server_url, headers=self.headers)
        read_stream, write_stream = await self._transport_ctx.__aenter__()
        return read_stream, write_stream

    async def _connect_streamable_http(self):
        """内部方法：建立 streamable HTTP 连接，返回 (read_stream, write_stream)

        streamable_http_client 产出 (read, write, get_session_id) 三元组，
        ClientSession 只需前两项。
        """
        self._transport_ctx = streamable_http_client(
            self.server_url, headers=self.headers
        )
        streams = await self._transport_ctx.__aenter__()
        return streams[0], streams[1]

    async def _connect_stdio(self):
        """内部方法：spawn stdio 子进程并接入，返回 (read_stream, write_stream)"""
        self._transport_ctx = stdio_client(self._server_params)
        read_stream, write_stream = await self._transport_ctx.__aenter__()
        return read_stream, write_stream

    async def connect(self) -> None:
        """建立连接并完成 MCP 握手（按 transport 分发）"""
        safe_url = sanitize_url(self.server_url)
        connectors = {
            "sse": self._connect_sse,
            "http": self._connect_streamable_http,
            "stdio": self._connect_stdio,
        }
        try:
            read_stream, write_stream = await connectors[self.transport]()

            # 创建 ClientSession 并初始化
            # 注意：mcp SDK 2.x 要求先进入 session 的 async context（启动内部
            # dispatcher），否则 initialize() 抛 "called before run()"
            self._session = ClientSession(read_stream, write_stream)
            await self._session.__aenter__()
            await asyncio.wait_for(
                self._session.initialize(),
                timeout=self.timeout,
            )

            logger.info(
                f"MCP client connected to {safe_url} (transport={self.transport})"
            )
        except asyncio.TimeoutError:
            await self.disconnect()
            raise McpConnectionError(f"Connection timeout after {self.timeout}s")
        except McpConnectionError:
            raise
        except Exception as e:
            await self.disconnect()
            logger.error(
                "MCP connection failed to %s (transport=%s): %s",
                safe_url,
                self.transport,
                type(e).__name__,
            )
            raise McpConnectionError(f"Connection failed: {type(e).__name__}") from e

    async def tools_list(self) -> list[dict]:
        """调用 MCP tools/list 获取工具列表

        Returns:
            [{"name": "...", "description": "...", "inputSchema": {...}}, ...]
        """
        if not self._session:
            raise McpConnectionError("Not connected")

        try:
            result = await asyncio.wait_for(
                self._session.list_tools(),
                timeout=self.timeout,
            )
            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": getattr(tool, "inputSchema", {}),
                }
                for tool in result.tools
            ]
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.error("tools_list failed: %s", type(e).__name__)
            raise

    async def tools_call(self, name: str, arguments: dict) -> dict:
        """调用 MCP tools/call 执行工具

        Args:
            name: 工具名
            arguments: 工具参数

        Returns:
            {"content": [...], "isError": bool}
        """
        if not self._session:
            raise McpConnectionError("Not connected")

        try:
            result = await asyncio.wait_for(
                self._session.call_tool(name, arguments),
                timeout=self.timeout,
            )
            # SDK 1.x 字段为 isError，2.x 改名为 is_error（兼容两种版本）
            is_error = getattr(result, "is_error", None)
            if is_error is None:
                is_error = getattr(result, "isError", False)
            return {
                "content": [
                    {
                        "type": getattr(c, "type", "text"),
                        "text": getattr(c, "text", str(c)),
                    }
                    for c in result.content
                ],
                "isError": is_error,
            }
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.error("tools_call failed for tool '%s': %s", name, type(e).__name__)
            raise

    async def disconnect(self) -> None:
        """关闭连接"""
        safe_url = sanitize_url(self.server_url)

        if self._session:
            try:
                # SDK 2.x：通过 async context 的 __aexit__ 关闭（无 close() 方法）
                await self._session.__aexit__(None, None, None)
            except Exception as e:
                logger.warning("Error closing MCP session: %s", type(e).__name__)
            self._session = None

        if self._transport_ctx:
            try:
                await self._transport_ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.warning("Error closing transport context: %s", type(e).__name__)
            self._transport_ctx = None

        logger.info(f"MCP client disconnected from {safe_url}")
