"""WebSearchTool — 网络搜索工具

Phase 1 第一个 BuiltinTool 实现，用于验证 ToolProtocol 完整性。
实际搜索通过 httpx 调用搜索 API（可配置后端）。
"""
import logging
from typing import List

import httpx

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool

logger = logging.getLogger(__name__)


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
            logger.error(f"WebSearchTool 搜索失败: {e}", exc_info=True)
            return ToolResult.error(f"搜索失败: {e}")

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
                    logger.warning(f"DuckDuckGo 返回 HTTP {resp.status_code}")
                    return []

                return self._parse_ddg_html(resp.text, max_results)
        except Exception as e:
            logger.warning(f"DuckDuckGo 请求失败: {e}")
            return []

    def _parse_ddg_html(self, html: str, max_results: int) -> List[dict]:
        """解析 DuckDuckGo HTML 搜索结果（轻量解析，不依赖 lxml）"""
        import re

        results = []

        # 简单正则提取（DuckDuckGo HTML 结构稳定）
        # 每个结果块包含 result__title / result__snippet / result__url
        title_pattern = re.compile(r'class="result__a"[^>]*>(.*?)</a>', re.DOTALL)
        snippet_pattern = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)
        url_pattern = re.compile(r'class="result__url"[^>]*href="([^"]+)"')

        titles = title_pattern.findall(html)
        snippets = snippet_pattern.findall(html)
        urls = url_pattern.findall(html)

        for i in range(min(len(titles), len(snippets), len(urls), max_results)):
            # 清理 HTML 标签
            title = re.sub(r'<[^>]+>', '', titles[i]).strip()
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            url = urls[i]

            if title and snippet and url:
                results.append({"title": title, "snippet": snippet, "url": url})

        return results