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
from socket import gethostbyname
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
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # 云元数据服务
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

_TEMPLATE_PATTERN = re.compile(r"\{\{([^}]+)\}\}")
_MAX_RESPONSE_SIZE = 1024 * 1024  # 1MB


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

            # SSRF 检查
            if not self._is_url_safe(url):
                return ToolResult.error(f"URL 不安全（SSRF 防护）: 已拒绝该请求")

            # 构造 body
            body_template = self._config.get("body_template")
            body = (
                self._render_value(body_template, args, ctx)
                if body_template
                else None
            )

            # 发请求
            timeout = self._config.get("timeout", 30)
            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=True
            ) as client:
                resp = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=(
                        body
                        if method in ("POST", "PUT", "PATCH") and body
                        else None
                    ),
                )

                # 响应大小检查
                content = resp.content
                if len(content) > _MAX_RESPONSE_SIZE:
                    return ToolResult.error(
                        f"响应过大 ({len(content)} bytes > {_MAX_RESPONSE_SIZE})"
                    )

                # 解析响应
                return self._parse_response(resp)

        except httpx.TimeoutException:
            return ToolResult.error("HTTP 请求超时")
        except Exception as e:
            logger.error(f"HttpTool 执行失败: {e}", exc_info=True)
            return ToolResult.error("HTTP 工具执行失败，请稍后重试")

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

    def _is_url_safe(self, url: str) -> bool:
        """检查 URL 是否安全（非内网地址）

        通过 DNS 解析 hostname，检查解析后的 IP 是否在私有/环回/链路本地网段。
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            hostname = parsed.hostname
            if not hostname:
                return False

            # 先尝试直接解析为 IP 地址（处理 IP 字面量情况）
            try:
                ip = ipaddress.ip_address(hostname)
            except ValueError:
                # 不是 IP 字面量，需要 DNS 解析
                try:
                    ip_str = gethostbyname(hostname)
                    ip = ipaddress.ip_address(ip_str)
                except Exception:
                    return False

            # 检查是否在黑名单网段
            for network in _BLOCKED_NETWORKS:
                if ip in network:
                    return False

            return True
        except Exception as e:
            logger.warning(f"URL 安全检查失败: {e}")
            return False

    # ---- 响应解析 ----

    def _parse_response(self, resp: httpx.Response) -> ToolResult:
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
