"""HttpTool 行为测试（Task 6）

覆盖：元数据 / 模板渲染 / SSRF 防护 / 响应解析 / JSONPath 提取
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.harness.tools.http_tool import HttpTool
from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.models.harness_models import Tool


def _make_db_tool(**config_overrides):
    """构造测试用 DB Tool 实体"""
    defaults = {
        "name": "test_http",
        "display_name": "测试HTTP",
        "description": "测试用HTTP工具",
        "type": "http",
        "config": {
            "url": "https://api.example.com/data",
            "method": "GET",
            "response_parser": {},
        },
        "parameters_schema": {
            "type": "object",
            "properties": {"q": {"type": "string"}},
        },
    }
    if "config" in config_overrides:
        defaults["config"] = {**defaults["config"], **config_overrides.pop("config")}
    defaults.update(config_overrides)
    return Tool(**defaults)


# ---- 元数据 ----


def test_http_tool_metadata_from_db_entity():
    """HttpTool 应从 DB Tool 实体读取元数据"""
    db_tool = Tool(
        name="weather_api",
        display_name="天气查询",
        description="查询天气",
        type="http",
        config={
            "url": "https://api.example.com/weather?city={{args.city}}",
            "method": "GET",
            "response_parser": {"result_path": "$.data"},
        },
        parameters_schema={
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    )
    tool = HttpTool(db_tool)

    assert tool.name == "weather_api"
    assert tool.display_name == "天气查询"
    assert tool.description == "查询天气"
    assert tool.parameters_schema["properties"]["city"]["type"] == "string"


def test_http_tool_to_function_schema():
    """to_function_schema 应返回 LLM 可用的 schema"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    schema = tool.to_function_schema()
    assert schema["name"] == "test_http"
    assert "description" in schema
    assert "parameters" in schema


def test_http_tool_is_available():
    """HttpTool.is_available 应委托到 db_tool.is_active"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)
    # 默认 is_active=True
    assert tool.is_available(ctx) is True

    db_tool.is_active = False
    assert tool.is_available(ctx) is False


# ---- 模板渲染 ----


def test_http_tool_template_rendering_args():
    """HttpTool 应渲染 {{args.*}} 模板"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    rendered = tool._render_string(
        "https://api.example.com/{{args.resource}}",
        args={"resource": "users"},
        ctx=ctx,
    )
    assert rendered == "https://api.example.com/users"


def test_http_tool_template_rendering_ctx():
    """HttpTool 应渲染 {{ctx.*}} 模板"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)
    ctx.user_id = "user-123"

    rendered = tool._render_string(
        "X-User: {{ctx.user_id}}",
        args={},
        ctx=ctx,
    )
    assert rendered == "X-User: user-123"


def test_http_tool_template_rendering_timestamp():
    """HttpTool 应渲染 {{timestamp}} 模板"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    rendered = tool._render_string("t={{timestamp}}", args={}, ctx=ctx)
    assert rendered.startswith("t=")
    # timestamp 应是数字
    ts = rendered.split("=")[1]
    assert ts.isdigit()


def test_http_tool_template_rendering_secrets():
    """HttpTool 应渲染 {{secrets.*}} 从环境变量"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    import os
    os.environ["TEST_API_KEY"] = "sk-test-123"
    try:
        rendered = tool._render_string(
            "Bearer {{secrets.TEST_API_KEY}}",
            args={},
            ctx=ctx,
        )
        assert rendered == "Bearer sk-test-123"
    finally:
        del os.environ["TEST_API_KEY"]


def test_http_tool_template_rendering_combined():
    """HttpTool 应支持多种模板变量组合"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)
    ctx.user_id = "user-456"

    rendered = tool._render_string(
        "https://api.example.com/{{args.resource}}/{{ctx.user_id}}",
        args={"resource": "users"},
        ctx=ctx,
    )
    assert rendered == "https://api.example.com/users/user-456"


def test_http_tool_render_value_dict():
    """_render_value 应递归渲染 dict"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)
    ctx.user_id = "u1"

    result = tool._render_value(
        {"key": "{{ctx.user_id}}", "nested": {"v": "{{args.x}}"}},
        args={"x": "hello"},
        ctx=ctx,
    )
    assert result == {"key": "u1", "nested": {"v": "hello"}}


def test_http_tool_render_value_list():
    """_render_value 应递归渲染 list"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    result = tool._render_value(
        ["{{args.a}}", "{{args.b}}"],
        args={"a": "1", "b": "2"},
        ctx=ctx,
    )
    assert result == ["1", "2"]


# ---- SSRF 防护 ----


def test_http_tool_rejects_metadata_url():
    """HttpTool 应拒绝云元数据地址（169.254.169.254）"""
    db_tool = _make_db_tool(config={
        "url": "http://169.254.169.254/latest/meta-data",
        "method": "GET",
        "response_parser": {},
    })
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    import asyncio
    result = asyncio.run(tool.execute({}, ctx))
    assert result.success is False


# ---- 重定向 SSRF 防护 ----


def _make_mock_client(responses):
    """构造按顺序返回响应的 mock httpx.AsyncClient

    Args:
        responses: list of (status_code, headers, content, url_str) tuples
    Returns:
        mock_client
    """
    call_count = 0

    async def mock_request(*args, **kwargs):
        nonlocal call_count
        if call_count >= len(responses):
            raise RuntimeError("mock 响应已耗尽")
        status, headers_dict, content, url_str = responses[call_count]
        call_count += 1

        mock_resp = MagicMock()
        mock_resp.status_code = status
        mock_resp.headers = headers_dict
        mock_resp.content = content
        # resp.url.join(location) 需要返回一个 URL-like 对象
        mock_url = MagicMock()

        def mock_join(location):
            # 简单拼接：绝对 URL 直接用，相对 URL 拼到 base
            if location.startswith("http"):
                return MagicMock(__str__=lambda self: location)
            # 相对路径：取当前 url 的 origin
            from urllib.parse import urlparse as _up
            parsed = _up(url_str)
            base = f"{parsed.scheme}://{parsed.netloc}"
            return MagicMock(__str__=lambda self: base + location)

        mock_url.join = mock_join
        mock_resp.url = mock_url

        # JSON 响应自动解析
        if headers_dict.get("content-type", "").startswith("application/json"):
            import json as _json
            try:
                mock_resp.json.return_value = _json.loads(content)
            except Exception:
                mock_resp.json.return_value = {}
        mock_resp.text = content.decode("utf-8", errors="replace")
        return mock_resp

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(side_effect=mock_request)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.mark.asyncio
async def test_execute_redirect_to_safe_url():
    """重定向到安全 URL 应正常跟随并返回最终响应"""
    db_tool = _make_db_tool(config={
        "url": "https://api.example.com/old",
        "method": "GET",
        "response_parser": {},
    })
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    # 第 1 跳：302 重定向到安全地址
    # 第 2 跳：200 正常响应
    mock_client = _make_mock_client([
        (302, {"location": "https://api.example.com/new"}, b"", "https://api.example.com/old"),
        (200, {"content-type": "application/json"}, b'{"ok": true}', "https://api.example.com/new"),
    ])

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch.object(tool, "_is_url_safe", return_value=True):
            result = await tool.execute({}, ctx)

    assert result.success is True
    # 应该发了 2 次请求
    assert mock_client.request.call_count == 2


@pytest.mark.asyncio
async def test_execute_redirect_to_private_network_blocked():
    """重定向到内网地址应被拦截（SSRF via redirect）"""
    db_tool = _make_db_tool(config={
        "url": "https://evil.com/redirect",
        "method": "GET",
        "response_parser": {},
    })
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    # 第 1 跳：302 重定向到云元数据地址
    mock_client = _make_mock_client([
        (302, {"location": "http://169.254.169.254/latest/meta-data"}, b"", "https://evil.com/redirect"),
    ])

    # _is_url_safe 使用真实实现（但我们 patch DNS 解析让它对 169.254 返回 false）
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await tool.execute({}, ctx)

    assert result.success is False
    assert "不安全" in result.error_message or "unsafe" in result.error_message.lower()
    # 只应发 1 次请求（重定向被拦截）
    assert mock_client.request.call_count == 1


@pytest.mark.asyncio
async def test_execute_redirect_loop_detected():
    """重定向循环应被检测并中止"""
    db_tool = _make_db_tool(config={
        "url": "https://example.com/loop",
        "method": "GET",
        "response_parser": {},
    })
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    # 构造 11 次重定向（超过 max_redirects=10）
    responses = []
    for i in range(11):
        responses.append(
            (302, {"location": "https://example.com/loop"}, b"", "https://example.com/loop")
        )

    mock_client = _make_mock_client(responses)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch.object(tool, "_is_url_safe", return_value=True):
            result = await tool.execute({}, ctx)

    assert result.success is False
    assert "重定向" in result.error_message or "redirect" in result.error_message.lower()


@pytest.mark.asyncio
async def test_execute_redirect_303_changes_method_to_get():
    """303 重定向应切换为 GET 方法"""
    db_tool = _make_db_tool(config={
        "url": "https://api.example.com/submit",
        "method": "POST",
        "response_parser": {},
    })
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    captured_kwargs = []

    async def mock_request(*args, **kwargs):
        captured_kwargs.append(kwargs.copy())
        status = 303 if len(captured_kwargs) == 1 else 200
        headers = {"location": "https://api.example.com/result"} if status == 303 else {"content-type": "application/json"}
        content = b"" if status == 303 else b'{"done": true}'
        url_str = "https://api.example.com/submit" if status == 303 else "https://api.example.com/result"

        mock_resp = MagicMock()
        mock_resp.status_code = status
        mock_resp.headers = headers
        mock_resp.content = content

        mock_url = MagicMock()
        def mock_join(location):
            return MagicMock(__str__=lambda self: location if location.startswith("http") else f"https://api.example.com{location}")
        mock_url.join = mock_join
        mock_resp.url = mock_url

        if status == 200:
            import json as _json
            mock_resp.json.return_value = _json.loads(content)
        mock_resp.text = content.decode("utf-8", errors="replace")
        return mock_resp

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(side_effect=mock_request)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch.object(tool, "_is_url_safe", return_value=True):
            result = await tool.execute({}, ctx)

    assert result.success is True
    # 第 1 次请求应该是 POST
    assert captured_kwargs[0].get("method") == "POST"
    # 第 2 次请求应该是 GET（303 切换）
    assert captured_kwargs[1].get("method") == "GET"


def test_http_tool_rejects_localhost():
    """HttpTool 应拒绝 localhost"""
    db_tool = _make_db_tool(config={
        "url": "http://127.0.0.1/admin",
        "method": "GET",
        "response_parser": {},
    })
    tool = HttpTool(db_tool)
    # 直接测试 _is_url_safe
    assert tool._is_url_safe("http://127.0.0.1/admin") is False


def test_http_tool_rejects_private_10():
    """HttpTool 应拒绝 10.0.0.0/8"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    assert tool._is_url_safe("http://10.0.0.1/internal") is False


def test_http_tool_rejects_private_172():
    """HttpTool 应拒绝 172.16.0.0/12"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    assert tool._is_url_safe("http://172.16.0.1/internal") is False


def test_http_tool_rejects_private_192():
    """HttpTool 应拒绝 192.168.0.0/16"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    assert tool._is_url_safe("http://192.168.1.1/admin") is False


def test_http_tool_rejects_non_http_scheme():
    """HttpTool 应拒绝非 http/https scheme"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    assert tool._is_url_safe("file:///etc/passwd") is False
    assert tool._is_url_safe("ftp://example.com/file") is False


def test_http_tool_rejects_empty_hostname():
    """HttpTool 应拒绝空 hostname"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    assert tool._is_url_safe("http://") is False


# ---- 响应解析（JSONPath-like 提取）----


def test_extract_by_path_simple():
    """_extract_by_path 应支持 $.a.b.c 路径"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)

    data = {"data": {"items": [1, 2, 3]}}
    assert tool._extract_by_path(data, "$.data.items") == [1, 2, 3]


def test_extract_by_path_single_key():
    """_extract_by_path 应支持 $.key"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)

    data = {"name": "test"}
    assert tool._extract_by_path(data, "$.name") == "test"


def test_extract_by_path_missing():
    """_extract_by_path 路径不存在应返回 None"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)

    data = {"a": {"b": 1}}
    assert tool._extract_by_path(data, "$.a.c") is None


def test_extract_by_path_root():
    """_extract_by_path $ 应返回整个 data"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)

    data = {"a": 1}
    assert tool._extract_by_path(data, "$") == {"a": 1}


def test_extract_by_path_invalid():
    """_extract_by_path 非 $ 开头应返回 data"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)

    data = {"a": 1}
    assert tool._extract_by_path(data, "invalid") == {"a": 1}


# ---- execute 集成测试（mock httpx）----


@pytest.mark.asyncio
async def test_execute_success_json():
    """execute 成功场景：JSON 响应 + result_path 提取"""
    db_tool = _make_db_tool(config={
        "url": "https://api.example.com/weather?city={{args.city}}",
        "method": "GET",
        "response_parser": {"result_path": "$.data"},
    })
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    # mock httpx 响应
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"data": {"temp": 25}, "code": 0}
    mock_resp.content = b'{"data": {"temp": 25}, "code": 0}'

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        # patch _is_url_safe 绕过 DNS 解析（测试环境无网络）
        with patch.object(tool, "_is_url_safe", return_value=True):
            result = await tool.execute({"city": "北京"}, ctx)

    assert result.success is True
    assert result.content_type == "json"
    assert result.content == {"temp": 25}


@pytest.mark.asyncio
async def test_execute_http_error():
    """execute HTTP 错误状态码应返回 error"""
    db_tool = _make_db_tool(config={
        "url": "https://api.example.com/data",
        "method": "GET",
        "response_parser": {},
    })
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.headers = {"content-type": "text/plain"}
    mock_resp.text = "Internal Server Error"
    mock_resp.content = b"Internal Server Error"

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch.object(tool, "_is_url_safe", return_value=True):
            result = await tool.execute({}, ctx)

    assert result.success is False
    assert "500" in result.error_message


@pytest.mark.asyncio
async def test_execute_timeout():
    """execute 超时应返回 error"""
    import httpx

    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch.object(tool, "_is_url_safe", return_value=True):
            result = await tool.execute({}, ctx)

    assert result.success is False
    assert "超时" in result.error_message


@pytest.mark.asyncio
async def test_execute_response_too_large():
    """execute 响应过大应返回 error"""
    db_tool = _make_db_tool()
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "text/plain"}
    mock_resp.content = b"x" * (1024 * 1024 + 1)  # > 1MB

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch.object(tool, "_is_url_safe", return_value=True):
            result = await tool.execute({}, ctx)

    assert result.success is False
    assert "过大" in result.error_message or "response" in result.error_message.lower()


@pytest.mark.asyncio
async def test_execute_ssrf_blocked():
    """execute 不应发起请求当 URL 不安全时"""
    db_tool = _make_db_tool(config={
        "url": "http://169.254.169.254/meta-data",
        "method": "GET",
        "response_parser": {},
    })
    tool = HttpTool(db_tool)
    ctx = MagicMock(spec=ToolContext)

    # 不应调用 httpx
    with patch("httpx.AsyncClient") as mock_client_cls:
        result = await tool.execute({}, ctx)
        mock_client_cls.assert_not_called()

    assert result.success is False
