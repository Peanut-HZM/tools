"""WebSearchTool — 网络搜索工具

Phase 1 第一个 BuiltinTool 实现，用于验证 ToolProtocol 完整性。
实际搜索通过 httpx 调用搜索 API（可配置后端）。

安全说明（Task 4 安全加固）：
- 解析层使用 BeautifulSoup 而非正则，避免 DDG 改版导致的解析错位
- title/snippet 经 html.unescape + 控制字符剥离 + 长度截断 + Markdown 转义
- URL 严格校验 scheme（仅 http/https），阻断 javascript:/data:/vbscript:
- 异常信息脱敏：详细 traceback 写入日志，LLM 上下文只暴露通用提示
"""
import html
import logging
import re
from typing import List
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool

logger = logging.getLogger(__name__)


# Markdown 中可能被用于 prompt injection 的特殊字符
# 在用户可控文本（标题、摘要、URL）中转义以避免格式混淆与指令注入
_MD_ESCAPE_RE = re.compile(r"([*_`\[\]>])")

# 控制字符（ASCII < 32，含 \n/\r/\t 之外的不可见字符），用于剥离潜在注入
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# 文本长度上限（防御 prompt bomb）
_MAX_TEXT_LEN = 300

# URL 长度上限
_MAX_URL_LEN = 2048

# 允许的 URL scheme
_ALLOWED_URL_SCHEMES = ("http", "https")


def _sanitize_text(raw: str, max_len: int = _MAX_TEXT_LEN) -> str:
    """对用户可控文本做安全处理

    步骤：
    1. html.unescape 解码 HTML 实体（&amp; → & 等）
    2. 剥离控制字符
    3. 转义 Markdown 特殊字符，避免破坏 prompt 结构或注入指令
    4. 截断长度，防止 prompt bomb
    """
    if not raw:
        return ""
    text = html.unescape(raw)
    text = _CONTROL_CHARS_RE.sub("", text)
    text = _MD_ESCAPE_RE.sub(r"\\\1", text)
    text = text.strip()
    if len(text) > max_len:
        text = text[:max_len] + "…"
    return text


def _sanitize_url(raw: str) -> str:
    """校验并规范化 URL

    仅允许 http/https scheme，丢弃 javascript: / data: / vbscript: 等危险 scheme。
    """
    if not raw:
        return ""
    try:
        parsed = urlparse(raw.strip())
    except Exception:
        return ""
    if parsed.scheme.lower() not in _ALLOWED_URL_SCHEMES:
        return ""
    # 强制要求 host，避免接受 'http:' 这种非法但通过 scheme 检查的串
    if not parsed.netloc:
        return ""
    normalized = parsed.geturl()
    if len(normalized) > _MAX_URL_LEN:
        normalized = normalized[:_MAX_URL_LEN]
    return normalized


class WebSearchTool(BuiltinTool):
    """网络搜索工具"""

    name = "web_search"
    display_name = "网络搜索"
    description = "在网络上搜索信息，返回相关结果摘要。用于获取最新信息、事实核查、研究主题。"
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词",
            },
            "max_results": {
                "type": "integer",
                "description": "最大返回结果数",
                "default": 5,
                "minimum": 1,
                "maximum": 10,
            },
        },
        "required": ["query"],
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "snippet": {"type": "string"},
                    },
                },
            },
        },
    }

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        query = args.get("query", "").strip()
        if not query:
            return ToolResult.error("query 不能为空")

        max_results = min(max(int(args.get("max_results", 5)), 1), 10)

        try:
            results = await self._do_search(query, max_results)
            if not results:
                return ToolResult.text(f"未找到与 '{query}' 相关的结果。")

            text = "\n\n".join(
                f"**{i+1}. {r['title']}**\n{r['snippet']}\n[{r['url']}]"
                for i, r in enumerate(results)
            )
            return ToolResult.text(text, metadata={"query": query, "count": len(results)})

        except Exception as e:
            # 仅记录详细 traceback 到日志，不向 LLM 泄露内部信息
            logger.exception("WebSearchTool 搜索失败: %s", e)
            # 通用用户提示，避免 stack frame / 内部路径泄露到 LLM 上下文
            return ToolResult.error("搜索失败，请稍后重试")

    async def _do_search(self, query: str, max_results: int) -> List[dict]:
        """执行实际搜索

        Phase 1：使用 DuckDuckGo HTML 接口（无需 API key）
        未来可替换为其他后端（Google、Bing、Serper 等）。
        """
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; AgentHarness/1.0)"}
        data = {"q": query}

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.post(url, headers=headers, data=data)
                if resp.status_code != 200:
                    logger.warning("DuckDuckGo 返回 HTTP %s", resp.status_code)
                    return []

                return self._parse_ddg_html(resp.text, max_results)
        except Exception as e:
            logger.warning("DuckDuckGo 请求失败: %s", e)
            return []

    def _parse_ddg_html(self, html_text: str, max_results: int) -> List[dict]:
        """解析 DuckDuckGo HTML 搜索结果

        使用 BeautifulSoup CSS 选择器按 .result 块整体提取，
        保证 title/snippet/url 来自同一结果块，避免正则错位。
        """
        soup = BeautifulSoup(html_text, "html.parser")
        results: List[dict] = []

        for r in soup.select(".result"):
            a = r.select_one(".result__a")
            s = r.select_one(".result__snippet")
            u = r.select_one(".result__url")

            if not (a and s and u):
                continue

            href = u.get("href")
            if not href:
                continue

            url = _sanitize_url(href)
            if not url:
                # 丢弃 javascript:/data:/vbscript:/空 host 等危险/非法 URL
                continue

            title = _sanitize_text(a.get_text(" ", strip=True))
            snippet = _sanitize_text(s.get_text(" ", strip=True))

            if title and snippet:
                results.append({
                    "title": title,
                    "snippet": snippet,
                    "url": url,
                })

            if len(results) >= max_results:
                break

        return results