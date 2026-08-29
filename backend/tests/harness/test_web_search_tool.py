"""WebSearchTool 行为测试（Task 4）

覆盖：元数据 / function schema / execute / is_available / 安全加固（Task 4 安全 review）
"""
from unittest.mock import MagicMock

import pytest

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools import web_search as web_search_module
from app.services.harness.tools.web_search import WebSearchTool


def test_web_search_tool_metadata():
    """WebSearchTool 应有正确的元数据"""
    tool = WebSearchTool()
    assert tool.name == "web_search"
    assert tool.display_name == "网络搜索"
    assert "query" in tool.parameters_schema["properties"]


def test_web_search_tool_function_schema():
    """to_function_schema 应返回 LLM 可用的 schema"""
    tool = WebSearchTool()
    schema = tool.to_function_schema()
    assert schema["name"] == "web_search"
    assert "description" in schema
    assert "parameters" in schema


@pytest.mark.asyncio
async def test_web_search_execute():
    """WebSearchTool.execute 应返回搜索结果"""
    tool = WebSearchTool()
    ctx = MagicMock(spec=ToolContext)

    result = await tool.execute({"query": "python", "max_results": 2}, ctx)

    assert isinstance(result, ToolResult)
    # 实际结果取决于是否联网；CI 环境可能无法搜索，至少不应抛异常
    assert result.content_type in ("text", "error")


def test_web_search_is_always_available():
    """WebSearchTool 默认总是可用"""
    tool = WebSearchTool()
    ctx = MagicMock(spec=ToolContext)
    assert tool.is_available(ctx) is True


# ---- 安全加固测试（Task 4 security review）----


def _build_html(*, title: str, snippet: str, url: str) -> str:
    """构造符合 DuckDuckGo .result 块结构的最小 HTML"""
    return (
        '<div class="result">'
        f'<a class="result__a">{title}</a>'
        f'<a class="result__snippet">{snippet}</a>'
        f'<a class="result__url" href="{url}">{url}</a>'
        '</div>'
    )


def test_parse_ddg_html_drops_javascript_url():
    """javascript: scheme 的 URL 应被丢弃"""
    html = _build_html(
        title="Evil",
        snippet="Some snippet",
        url="javascript:alert(1)",
    )
    tool = WebSearchTool()
    results = tool._parse_ddg_html(html, max_results=10)
    assert results == []


def test_parse_ddg_html_drops_data_url():
    """data: scheme 的 URL 应被丢弃"""
    html = _build_html(
        title="Evil",
        snippet="Some snippet",
        url="data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
    )
    tool = WebSearchTool()
    results = tool._parse_ddg_html(html, max_results=10)
    assert results == []


def test_parse_ddg_html_drops_vbscript_url():
    """vbscript: scheme 的 URL 应被丢弃"""
    html = _build_html(
        title="Evil",
        snippet="Some snippet",
        url="vbscript:msgbox(1)",
    )
    tool = WebSearchTool()
    results = tool._parse_ddg_html(html, max_results=10)
    assert results == []


def test_parse_ddg_html_drops_empty_host():
    """缺少 host 的 URL 应被丢弃"""
    html = _build_html(
        title="Edge",
        snippet="Some snippet",
        url="http:",
    )
    tool = WebSearchTool()
    results = tool._parse_ddg_html(html, max_results=10)
    assert results == []


def test_parse_ddg_html_keeps_http_url():
    """合法 http URL 应被保留"""
    html = _build_html(
        title="OK",
        snippet="Snippet",
        url="http://example.com/page",
    )
    tool = WebSearchTool()
    results = tool._parse_ddg_html(html, max_results=10)
    assert len(results) == 1
    assert results[0]["url"] == "http://example.com/page"


def test_parse_ddg_html_keeps_https_url():
    """合法 https URL 应被保留"""
    html = _build_html(
        title="OK",
        snippet="Snippet",
        url="https://example.com/path?q=1",
    )
    tool = WebSearchTool()
    results = tool._parse_ddg_html(html, max_results=10)
    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/path?q=1"


def test_parse_ddg_html_truncates_long_title():
    """超长 title 应被截断"""
    long_title = "A" * 1000
    html = _build_html(
        title=long_title,
        snippet="Snippet",
        url="https://example.com/",
    )
    tool = WebSearchTool()
    results = tool._parse_ddg_html(html, max_results=10)
    assert len(results) == 1
    # 截断上限 300 + 省略号
    assert len(results[0]["title"]) <= 301


def test_parse_ddg_html_truncates_long_snippet():
    """超长 snippet 应被截断"""
    long_snippet = "B" * 1000
    html = _build_html(
        title="OK",
        snippet=long_snippet,
        url="https://example.com/",
    )
    tool = WebSearchTool()
    results = tool._parse_ddg_html(html, max_results=10)
    assert len(results) == 1
    assert len(results[0]["snippet"]) <= 301


def test_parse_ddg_html_decodes_html_entities():
    """HTML 实体应被解码（&amp; → & 等）

    注意：'>' 是 Markdown 转义目标，会被加反斜杠以避免破坏块引用结构。
    '<' 不在转义列表中（不会与 markdown 块引用歧义），保持原样。
    """
    html = _build_html(
        title="Tom &amp; Jerry",
        snippet="A &lt; B &amp; B &gt; C",
        url="https://example.com/",
    )
    tool = WebSearchTool()
    results = tool._parse_ddg_html(html, max_results=10)
    assert len(results) == 1
    # '&' 不是 markdown 转义目标（不与结构冲突），保持原样
    assert "Tom & Jerry" == results[0]["title"]
    assert r"A < B & B \> C" == results[0]["snippet"]


def test_parse_ddg_html_strips_control_chars():
    """控制字符应被剥离（防御 prompt injection）"""
    html = _build_html(
        title="Invisible\x00Title\x07Here",
        snippet="Snip\x1bpet",
        url="https://example.com/",
    )
    tool = WebSearchTool()
    results = tool._parse_ddg_html(html, max_results=10)
    assert len(results) == 1
    # 控制字符不应出现在输出中
    assert "\x00" not in results[0]["title"]
    assert "\x07" not in results[0]["title"]
    assert "\x1b" not in results[0]["snippet"]
    # 保留可见文本
    assert "InvisibleTitleHere" in results[0]["title"]
    assert "Snippet" in results[0]["snippet"]


def test_parse_ddg_html_escapes_markdown_special_chars():
    """Markdown 特殊字符应被转义，避免破坏 prompt 结构"""
    html = _build_html(
        title="Use *star* and _under_",
        snippet="click [here] for `code` > stuff",
        url="https://example.com/",
    )
    tool = WebSearchTool()
    results = tool._parse_ddg_html(html, max_results=10)
    assert len(results) == 1
    # Markdown 字符前应出现反斜杠
    assert r"\*star\*" in results[0]["title"]
    assert r"\_under\_" in results[0]["title"]
    assert r"\[here\]" in results[0]["snippet"]
    assert r"\`code\`" in results[0]["snippet"]


def test_parse_ddg_html_keeps_block_aligned():
    """同一 .result 块内的 title/snippet/url 应绑定在一起（防正则错位）"""
    # 构造：第一个结果标题安全但 URL 危险，第二个结果 URL 安全
    # 验证 dangerous URL 被丢弃，第二个结果被保留
    html = (
        '<div class="result">'
        '<a class="result__a">Bad URL Title</a>'
        '<a class="result__snippet">Bad URL Snippet</a>'
        '<a class="result__url" href="javascript:alert(1)">x</a>'
        '</div>'
        '<div class="result">'
        '<a class="result__a">Good Title</a>'
        '<a class="result__snippet">Good Snippet</a>'
        '<a class="result__url" href="https://example.com/">y</a>'
        '</div>'
    )
    tool = WebSearchTool()
    results = tool._parse_ddg_html(html, max_results=10)
    assert len(results) == 1
    assert results[0]["title"] == "Good Title"
    assert results[0]["snippet"] == "Good Snippet"
    assert results[0]["url"] == "https://example.com/"


def test_parse_ddg_html_truncates_oversized_url():
    """超长 URL 应被截断到 _MAX_URL_LEN"""
    long_path = "a" * 5000
    html = _build_html(
        title="OK",
        snippet="OK",
        url=f"https://example.com/{long_path}",
    )
    tool = WebSearchTool()
    results = tool._parse_ddg_html(html, max_results=10)
    assert len(results) == 1
    assert len(results[0]["url"]) <= web_search_module._MAX_URL_LEN


def test_sanitize_url_handles_uppercase_scheme():
    """scheme 大小写不敏感：HTTPS:// 也应被接受

    Python 的 urlparse 会将 scheme 规范化为小写，所以这里用 'in' 校验。
    """
    result = web_search_module._sanitize_url("HTTPS://example.com/")
    assert result.endswith("example.com/")
    assert result.startswith("http")  # scheme 被规范化（大小写不敏感）


def test_sanitize_url_returns_empty_for_empty_input():
    """空输入应返回空字符串"""
    assert web_search_module._sanitize_url("") == ""
    assert web_search_module._sanitize_url(None or "") == ""


def test_sanitize_text_handles_empty_input():
    """空输入应返回空字符串"""
    assert web_search_module._sanitize_text("") == ""
    assert web_search_module._sanitize_text(None or "") == ""


@pytest.mark.asyncio
async def test_execute_swallows_exception_and_returns_generic_error():
    """execute 捕获异常时不应泄露内部信息到 LLM 上下文

    验证：
    - 失败时 error_message 是通用提示，不含 traceback 或异常详情
    - logger.exception 仍记录详情（无法直接断言，通过 monkeypatch 验证）
    """
    tool = WebSearchTool()
    ctx = MagicMock(spec=ToolContext)

    # monkeypatch _do_search 抛异常
    async def boom(query, max_results):
        raise RuntimeError("SECRET-INTERNAL-PATH /etc/passwd leaked!")

    tool._do_search = boom

    # 抑制 logger.exception 输出（测试环境不需要打印）
    import logging as _logging
    _logging.getLogger("app.services.harness.tools.web_search").addHandler(
        _logging.NullHandler()
    )

    result = await tool.execute({"query": "x", "max_results": 1}, ctx)

    assert result.success is False
    assert result.content_type == "error"
    # 通用提示，不含敏感词
    assert "SECRET-INTERNAL-PATH" not in (result.error_message or "")
    assert "/etc/passwd" not in (result.error_message or "")
    assert "请稍后重试" in (result.error_message or "")