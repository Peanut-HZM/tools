"""HttpTool — 管理员配置的 HTTP 调用工具

参考 spec §6.3 实现 ②

模板变量：
- {{args.xxx}}：工具参数
- {{ctx.user_id}} / {{ctx.conversation_id}} / {{ctx.agent_id}}：上下文
- {{secrets.XXX}}：从环境变量读取的密钥
- {{timestamp}}：当前时间戳

安全：
- URL 白名单：拒绝内网地址（SSRF 防护）
- 模板变量沙箱：只允许白名单变量
- 响应大小限制：默认 1MB
- DNS 解析检查：解析 hostname 后判断 IP 是否在黑名单网段
"""
import ipaddress
import logging
import os
import re
import time
import socket
from typing import Any, AsyncIterator
from urllib.parse import urlparse

import httpx

from app.services.harness.tool_protocol import (
    ToolContext,
    ToolEvent,
    ToolResult,
)

logger = logging.getLogger(__name__)


# SSRF 防护：拒绝这些网段
_BLOCKED_NETWORKS = [
    # IPv4 私有/环回/链路本地网段
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # 云元数据服务
    # IPv6 环回/链路本地/私有网段
    ipaddress.ip_network("::1/128"),           # IPv6 环回
    ipaddress.ip_network("fe80::/10"),         # IPv6 链路本地
    ipaddress.ip_network("fc00::/7"),          # IPv6 唯一本地 (ULA)
    ipaddress.ip_network("::ffff:0:0/96"),     # IPv4 映射的 IPv6（检查嵌入的 IPv4）
]

_TEMPLATE_PATTERN = re.compile(r"\{\{([^}]+)\}\}")
_MAX_RESPONSE_SIZE = 1024 * 1024  # 1MB


class _BufferedResponse:
    """流式下载完成后缓冲的响应对象，模拟 httpx.Response 的关键属性"""

    def __init__(self, status_code: int, headers, content: bytes, url: Any):
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self.url = url

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        import json as _json
        return _json.loads(self.content)


class HttpTool:
    """HTTP 工具：从 DB Tool 实体动态构造

    注意：HttpTool 直接实现 ToolProtocol（不继承 BuiltinTool），
    因为它是配置驱动而非代码驱动。
    """

    def __init__(self, db_tool):
        """
        Args:
            db_tool: Tool ORM 实体
        """
        self._db_tool = db_tool
        self._config = db_tool.config or {}

    # ---- ToolProtocol 元数据（委托到 db_tool）----

    @property
    def name(self) -> str:
        return self._db_tool.name

    @property
    def display_name(self) -> str:
        return self._db_tool.display_name

    @property
    def description(self) -> str:
        return self._db_tool.description

    @property
    def parameters_schema(self) -> dict:
        return self._db_tool.parameters_schema

    @property
    def returns_schema(self):
        return self._db_tool.returns_schema

    # ---- 生命周期 ----

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    # ---- 可用性 ----

    def is_available(self, ctx: ToolContext) -> bool:
        return self._db_tool.is_active

    # ---- LLM 集成 ----

    def to_function_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }

    # ---- 核心执行 ----

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        try:
            url = self._render_string(self._config.get("url", ""), args, ctx)
            method = (self._config.get("method", "GET") or "GET").upper()
            headers_template = self._config.get("headers", {}) or {}
            headers = {
                k: self._render_string(v, args, ctx)
                for k, v in headers_template.items()
            }

            # SSRF 检查（TOCTOU 防护：一次性解析 DNS，返回已校验的 IP）
            is_safe, resolved = self._is_url_safe(url)
            if not is_safe:
                return ToolResult.error(f"URL 不安全（SSRF 防护）: 已拒绝该请求")

            # 构造 body
            body_template = self._config.get("body_template")
            body = (
                self._render_value(body_template, args, ctx)
                if body_template
                else None
            )

            # 发请求（禁用自动跳转，手动跟随并校验每一跳，防止 SSRF via redirect）
            timeout = self._config.get("timeout", 30)
            max_redirects = 10
            current_url = url
            current_resolved = resolved  # 当前 URL 对应的已校验 IP

            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=False
            ) as client:
                resp = None
                for hop in range(max_redirects):
                    # 用已校验的 IP 直连，设置 Host 头保持虚拟主机路由正常
                    parsed = urlparse(current_url)
                    default_port = 443 if parsed.scheme == "https" else 80
                    port = parsed.port or default_port
                    # IPv6 地址在 URL 中需要方括号
                    host_part = (
                        f"[{current_resolved}]"
                        if ":" in current_resolved
                        else current_resolved
                    )
                    connect_url = (
                        f"{parsed.scheme}://{host_part}:{port}{parsed.path}"
                    )
                    if parsed.query:
                        connect_url += f"?{parsed.query}"

                    req_headers = {**headers, "Host": parsed.hostname or ""}

                    resp = await self._stream_request(
                        client, method, connect_url, req_headers, body
                    )
                    if isinstance(resp, ToolResult):
                        # 流式下载阶段返回了错误（响应过大等）
                        return resp

                    # 非重定向响应，跳出循环
                    if resp.status_code not in (301, 302, 303, 307, 308):
                        break

                    # 解析 Location 头
                    location = resp.headers.get("location")
                    if not location:
                        break

                    # 解析相对 URL（基于当前请求 URL）
                    next_url = resp.url.join(location)
                    next_url_str = str(next_url)

                    # 校验重定向目标是否安全（同时解析新 IP）
                    next_safe, next_resolved = self._is_url_safe(next_url_str)
                    if not next_safe:
                        logger.warning(
                            f"HttpTool 重定向到不安全 URL 已拦截: {next_url_str}"
                        )
                        return ToolResult.error(
                            f"重定向到不安全的 URL，已拒绝: {next_url_str}"
                        )

                    current_url = next_url_str
                    current_resolved = next_resolved
                    # 303 See Other：强制切换为 GET 且不带 body
                    if resp.status_code == 303:
                        method = "GET"
                        body = None
                else:
                    # for 循环正常结束（未 break），说明重定向次数耗尽
                    return ToolResult.error(
                        f"重定向次数过多（最多 {max_redirects} 次），已中止"
                    )

                # 解析响应
                return self._parse_response(resp)

        except httpx.TimeoutException:
            return ToolResult.error("HTTP 请求超时")
        except Exception as e:
            logger.error(f"HttpTool 执行失败: {e}", exc_info=True)
            return ToolResult.error("HTTP 工具执行失败，请稍后重试")

    async def _stream_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        headers: dict,
        body: Any,
    ) -> "httpx.Response | ToolResult":
        """流式发起请求并增量校验响应大小（DoS 防护）

        成功时返回 httpx.Response（已读取全部内容到 .content）；
        失败时返回 ToolResult.error（响应过大等）。
        """
        async with client.stream(
            method=method,
            url=url,
            headers=headers,
            json=(body if method in ("POST", "PUT", "PATCH") and body else None),
        ) as resp:
            # 快速失败：检查 Content-Length 头
            content_length = resp.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > _MAX_RESPONSE_SIZE:
                        return ToolResult.error(
                            f"响应过大 ({content_length} bytes > {_MAX_RESPONSE_SIZE})"
                        )
                except ValueError:
                    pass  # 非法 Content-Length 忽略，走流式校验

            # 流式下载 + 增量大小校验
            chunks: list[bytes] = []
            total = 0
            async for chunk in resp.aiter_bytes():
                total += len(chunk)
                if total > _MAX_RESPONSE_SIZE:
                    return ToolResult.error(
                        f"响应过大 ({total} bytes > {_MAX_RESPONSE_SIZE})"
                    )
                chunks.append(chunk)

            # 拼装为类 Response 对象供后续 _parse_response 使用
            content = b"".join(chunks)
            return _BufferedResponse(
                status_code=resp.status_code,
                headers=resp.headers,
                content=content,
                url=resp.url,
            )

    async def execute_stream(
        self, args: dict, ctx: ToolContext
    ) -> AsyncIterator[ToolEvent]:
        result = await self.execute(args, ctx)
        yield ToolEvent(type="result", payload=result)

    # ---- 模板渲染 ----

    def _render_string(self, template: str, args: dict, ctx: ToolContext) -> str:
        """渲染字符串模板"""
        if not isinstance(template, str):
            return template

        def replace(match):
            key = match.group(1).strip()
            return str(self._resolve_variable(key, args, ctx))

        return _TEMPLATE_PATTERN.sub(replace, template)

    def _render_value(self, value: Any, args: dict, ctx: ToolContext) -> Any:
        """递归渲染值（dict / list / str）"""
        if isinstance(value, str):
            return self._render_string(value, args, ctx)
        if isinstance(value, dict):
            return {k: self._render_value(v, args, ctx) for k, v in value.items()}
        if isinstance(value, list):
            return [self._render_value(v, args, ctx) for v in value]
        return value

    def _resolve_variable(self, key: str, args: dict, ctx: ToolContext) -> Any:
        """解析模板变量"""
        if key.startswith("args."):
            return args.get(key[5:])
        if key.startswith("ctx."):
            attr = key[4:]
            return getattr(ctx, attr, "")
        if key.startswith("secrets."):
            env_key = key[8:]
            return os.environ.get(env_key, "")
        if key == "timestamp":
            return str(int(time.time()))
        return ""

    # ---- SSRF 防护 ----

    def _is_url_safe(self, url: str) -> tuple[bool, str]:
        """检查 URL 是否安全（非内网地址）

        通过 DNS 解析 hostname，检查解析后的所有 IP（IPv4 + IPv6）是否在黑名单网段。
        对 IPv4 映射的 IPv6 地址（如 ::ffff:127.0.0.1）会提取嵌入的 IPv4 进行检查。

        Returns:
            (is_safe, resolved_ip_or_original_url)
            - is_safe: 是否安全
            - resolved_ip_or_original_url: 解析后的 IP 地址（用于 TOCTOU 防护直连），
              若为 IP 字面量则返回原始值，失败时返回空字符串
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False, ""
            hostname = parsed.hostname
            if not hostname:
                return False, ""

            def _check_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
                """检查单个 IP 是否在黑名单中，返回 True 表示安全"""
                # IPv4 映射的 IPv6 地址：提取嵌入的 IPv4 进行检查
                if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
                    ip = ip.ipv4_mapped
                for network in _BLOCKED_NETWORKS:
                    if ip in network:
                        return False
                return True

            # 先尝试直接解析为 IP 地址（处理 IP 字面量情况）
            try:
                ip = ipaddress.ip_address(hostname)
                if not _check_ip(ip):
                    return False, ""
                return True, hostname
            except ValueError:
                pass  # 不是 IP 字面量，需要 DNS 解析

            # DNS 解析：使用 getaddrinfo 获取所有地址族（IPv4 + IPv6）
            try:
                infos = socket.getaddrinfo(hostname, None)
            except Exception:
                return False, ""

            # 检查所有解析出的地址
            first_ipv4 = None
            for info in infos:
                addr = info[4][0]  # sockaddr[0] 是地址字符串
                try:
                    ip = ipaddress.ip_address(addr)
                except ValueError:
                    continue
                if not _check_ip(ip):
                    return False, ""
                if isinstance(ip, ipaddress.IPv4Address) and first_ipv4 is None:
                    first_ipv4 = addr

            # 所有地址均安全，优先返回 IPv4 地址（向后兼容）
            if first_ipv4:
                return True, first_ipv4
            return True, infos[0][4][0]
        except Exception as e:
            logger.warning(f"URL 安全检查失败: {e}")
            return False, ""

    # ---- 响应解析 ----

    def _parse_response(self, resp) -> ToolResult:
        """按 response_parser 配置解析响应"""
        parser = self._config.get("response_parser", {}) or {}

        try:
            if resp.headers.get("content-type", "").startswith("application/json"):
                data = resp.json()
            else:
                data = {"text": resp.text}
        except Exception:
            data = {"text": resp.text}

        # 错误检查
        error_path = parser.get("error_path")
        if error_path and resp.status_code >= 400:
            error_msg = (
                self._extract_by_path(data, error_path) or f"HTTP {resp.status_code}"
            )
            return ToolResult.error(str(error_msg))

        if resp.status_code >= 400:
            return ToolResult.error(f"HTTP {resp.status_code}: {resp.text[:500]}")

        # 提取结果
        result_path = parser.get("result_path")
        if result_path:
            result = self._extract_by_path(data, result_path)
        else:
            result = data

        if isinstance(result, (dict, list)):
            return ToolResult.json(
                result, metadata={"status_code": resp.status_code}
            )
        return ToolResult.text(str(result), metadata={"status_code": resp.status_code})

    def _extract_by_path(self, data: Any, path: str) -> Any:
        """JSONPath-like 提取（简化版，支持 $.a.b.c）"""
        if not path or not path.startswith("$"):
            return data

        parts = path.lstrip("$").lstrip(".").split(".")
        current = data
        for part in parts:
            if not part:
                continue
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current
