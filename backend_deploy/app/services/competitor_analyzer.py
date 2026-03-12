"""
竞品分析服务
处理竞品搜索、分析和对比
"""

from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy.orm import Session

from app.models import CompetitorAnalysis
from app.core.logging import get_pm_agent_logger

logger = get_pm_agent_logger(__name__)


class CompetitorAnalyzerService:
    """竞品分析服务"""

    def __init__(self, db: Session):
        self.db = db
        self.serpapi_key = None  # 可以从配置中获取

    async def search_competitors(
        self, keyword: str, num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索竞品

        Args:
            keyword: 搜索关键词
            num_results: 返回结果数量

        Returns:
            竞品列表
        """
        logger.info(f"Searching competitors for: {keyword}")

        # 如果配置了 SerpAPI，使用它进行搜索
        if self.serpapi_key:
            return await self._search_with_serpapi(keyword, num_results)

        # 否则使用通用搜索
        return await self._generic_search(keyword, num_results)

    async def _search_with_serpapi(
        self, keyword: str, num_results: int
    ) -> List[Dict[str, Any]]:
        """使用 SerpAPI 搜索"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "q": keyword,
                        "api_key": self.serpapi_key,
                        "num": num_results,
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("organic_results", [])

                    competitors = []
                    for result in results[:num_results]:
                        competitors.append(
                            {
                                "name": result.get("title", ""),
                                "url": result.get("link", ""),
                                "snippet": result.get("snippet", ""),
                            }
                        )

                    return competitors
                else:
                    logger.warning(f"SerpAPI error: {response.status_code}")
                    return await self._generic_search(keyword, num_results)

        except Exception as e:
            logger.error(f"SerpAPI search failed: {str(e)}")
            return await self._generic_search(keyword, num_results)

    async def _generic_search(
        self, keyword: str, num_results: int
    ) -> List[Dict[str, Any]]:
        """通用搜索（返回模拟数据）"""
        # 在没有真实搜索 API 时，返回基于关键词的模拟结果
        # 实际生产环境应该接入真实的搜索 API

        keyword_lower = keyword.lower()

        # 基于关键词生成模拟竞品列表
        mock_competitors = [
            {
                "name": f"{keyword.title()} 竞品A",
                "url": "https://example-competitor-a.com",
                "snippet": f"提供{keyword}相关服务的领先平台",
            },
            {
                "name": f"{keyword.title()} 竞品B",
                "url": "https://example-competitor-b.com",
                "snippet": f"专注{keyword}领域的创新产品",
            },
            {
                "name": f"{keyword.title()} 竞品C",
                "url": "https://example-competitor-c.com",
                "snippet": f"企业级{keyword}解决方案",
            },
        ]

        return mock_competitors[:num_results]

    async def analyze_features(
        self, competitors: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        分析竞品功能特征

        Args:
            competitors: 竞品列表

        Returns:
            带功能分析的竞品列表
        """
        logger.info(f"Analyzing features for {len(competitors)} competitors")

        analyzed = []

        for competitor in competitors:
            # 模拟功能分析
            # 实际应该使用 LLM 进行更深入的分析

            analyzed.append(
                {
                    "name": competitor.get("name", ""),
                    "url": competitor.get("url", ""),
                    "core_features": [
                        "功能特性1",
                        "功能特性2",
                        "功能特性3",
                    ],
                    "pros": [
                        "优势1",
                        "优势2",
                    ],
                    "cons": [
                        "劣势1",
                        "劣势2",
                    ],
                    "opportunity": f"针对{competitor.get('name', '竞品')}的差异化机会",
                }
            )

        return analyzed

    def generate_comparison_table(
        self, competitors: List[Dict[str, Any]], features: List[str]
    ) -> str:
        """
        生成对比表格

        Args:
            competitors: 竞品列表
            features: 对比特性列表

        Returns:
            Markdown 格式的对比表格
        """
        logger.info(f"Generating comparison table for {len(competitors)} competitors")

        # 表头
        header = (
            "| 特性 | "
            + " | ".join([c.get("name", "竞品") for c in competitors])
            + " |"
        )
        separator = (
            "| " + "-" * 20 + " | " + " | ".join(["---"] * len(competitors)) + " |"
        )

        rows = []
        for feature in features:
            row_values = [feature]
            for competitor in competitors:
                # 简化的对比逻辑
                feature_lower = feature.lower()
                competitor_name = competitor.get("name", "").lower()

                if feature_lower in competitor.get("core_features", []):
                    row_values.append("✓ 支持")
                elif feature_lower in competitor.get("pros", []):
                    row_values.append("△ 优势")
                elif feature_lower in competitor.get("cons", []):
                    row_values.append("✗ 劣势")
                else:
                    row_values.append("-")

            rows.append("| " + " | ".join(row_values) + " |")

        # 构建表格
        table = "\n".join([header, separator] + rows)

        return table

    async def analyze_and_save(
        self,
        conversation_id: str,
        keyword: str,
    ) -> CompetitorAnalysis:
        """
        完整分析并保存

        Args:
            conversation_id: 会话ID
            keyword: 分析关键词

        Returns:
            保存的竞品分析结果
        """
        logger.info(
            f"Starting full competitor analysis for conversation {conversation_id}"
        )

        # 1. 搜索竞品
        competitors = await self.search_competitors(keyword)

        # 2. 分析功能
        analyzed = await self.analyze_features(competitors)

        # 3. 生成差异化建议
        suggestions = self._generate_differentiation_suggestions(analyzed)

        # 4. 保存结果
        analysis = CompetitorAnalysis(
            conversation_id=conversation_id,
            competitors=analyzed,
            differentiation_suggestions=suggestions,
        )

        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        logger.info(f"Competitor analysis saved: id={analysis.id}")

        return analysis

    def _generate_differentiation_suggestions(
        self, competitors: List[Dict[str, Any]]
    ) -> str:
        """生成差异化建议"""
        suggestions = []

        for competitor in competitors:
            if "opportunity" in competitor:
                suggestions.append(
                    f"针对{competitor.get('name')}：{competitor.get('opportunity')}"
                )

        return "\n".join(suggestions)

    def get_analysis(self, conversation_id: str) -> Optional[CompetitorAnalysis]:
        """获取竞品分析结果"""
        return (
            self.db.query(CompetitorAnalysis)
            .filter(CompetitorAnalysis.conversation_id == conversation_id)
            .first()
        )
