"""
竞品分析路由
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.services.competitor_analyzer import CompetitorAnalyzerService
from app.models import User


router = APIRouter(prefix="/competitors", tags=["竞品分析"])


class CompetitorAnalysisRequest(BaseModel):
    """竞品分析请求"""

    keyword: str = Field(..., description="分析关键词")


class Competitor(BaseModel):
    """竞品信息"""

    name: str
    url: Optional[str] = None
    core_features: Optional[List[str]] = Field(default_factory=list)
    pros: Optional[List[str]] = Field(default_factory=list)
    cons: Optional[List[str]] = Field(default_factory=list)
    opportunity: Optional[str] = None


class CompetitorAnalysisResponse(BaseModel):
    """竞品分析响应"""

    id: str
    conversation_id: str
    competitors: List[Competitor]
    differentiation_suggestions: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


@router.get("/{conversation_id}", response_model=CompetitorAnalysisResponse)
async def get_competitor_analysis(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取竞品分析结果
    """
    service = CompetitorAnalyzerService(db)
    analysis = service.get_analysis(conversation_id)

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="竞品分析结果不存在"
        )

    return {
        "id": str(analysis.id),
        "conversation_id": str(analysis.conversation_id),
        "competitors": analysis.competitors,
        "differentiation_suggestions": analysis.differentiation_suggestions,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
    }


@router.post("/{conversation_id}", status_code=status.HTTP_201_CREATED)
async def create_competitor_analysis(
    conversation_id: str,
    request: CompetitorAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    执行竞品分析
    """
    service = CompetitorAnalyzerService(db)

    analysis = await service.analyze_and_save(
        conversation_id=conversation_id,
        keyword=request.keyword,
    )

    return {
        "id": str(analysis.id),
        "conversation_id": str(analysis.competitors),
        "status": "completed",
    }
