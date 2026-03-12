"""
PRD 路由
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.services.prd_generator import PRDGeneratorService
from app.services.prd_version_service import PRDVersionService
from app.models import PRDDocument


router = APIRouter(tags=["prd"])


class PRDCreate(BaseModel):
    """创建 PRD 请求"""

    sections: Optional[List[str]] = Field(None, description="指定要生成的章节")


class PRDSectionUpdate(BaseModel):
    """更新 PRD 章节请求"""
    
    section_title: str = Field(..., description="章节标题")
    section_content: str = Field(..., description="章节内容")


class PRDPartialGenerate(BaseModel):
    """部分生成 PRD 请求"""
    
    sections: List[str] = Field(..., description="要生成的章节列表")
    """创建 PRD 请求"""

    sections: Optional[List[str]] = Field(None, description="指定要生成的章节")


class PRDResponse(BaseModel):
    """PRD 响应"""

    id: str
    conversation_id: str
    version_number: int
    content: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


class PRDCompareRequest(BaseModel):
    """对比 PRD 请求"""

    from_version: int
    to_version: int


class PRDRollbackRequest(BaseModel):
    """回滚 PRD 请求"""

    target_version: int


class PRDExportRequest(BaseModel):
    """导出 PRD 请求"""

    version_number: int
    format: str = Field(..., pattern="^(markdown|pdf|word)$")


@router.get("/conversations/{conversation_id}/prd", response_model=List[PRDResponse])
async def list_prd_versions(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取 PRD 版本列表"""
    service = PRDVersionService(db)
    versions = service.get_versions(conversation_id)
    return versions


@router.post(
    "/conversations/{conversation_id}/prd",
    response_model=PRDResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prd(
    conversation_id: str,
    data: PRDCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """生成新 PRD 版本"""
    # TODO: 调用 LLM 生成内容
    content = "# PRD 文档\n\n正在生成中..."

    service = PRDVersionService(db)
    prd = service.create_version(conversation_id, content)
    return prd


@router.get(
    "/conversations/{conversation_id}/prd/{version_number}", response_model=PRDResponse
)
async def get_prd_version(
    conversation_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取指定版本 PRD"""
    service = PRDVersionService(db)
    versions = service.get_versions(conversation_id)

    for v in versions:
        if v.version_number == version_number:
            return v

    raise HTTPException(status_code=404, detail="版本不存在")


@router.put("/prd/{prd_id}/status")
async def update_prd_status(
    prd_id: str,
    status: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """更新 PRD 状态"""
    service = PRDGeneratorService(db)
    prd = service.update_status(prd_id, status)

    if not prd:
        raise HTTPException(status_code=404, detail="PRD 不存在")

    return prd


@router.post("/conversations/{conversation_id}/prd/compare")
async def compare_prd_versions(
    conversation_id: str,
    data: PRDCompareRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """对比两个 PRD 版本"""
    from app.utils.diff_generator import generate_diff, format_diff_view
    
    service = PRDVersionService(db)
    
    # 获取两个版本
    from_prd = (
        db.query(PRDDocument)
        .filter(
            PRDDocument.conversation_id == conversation_id,
            PRDDocument.version_number == data.from_version,
        )
        .first()
    )
    
    to_prd = (
        db.query(PRDDocument)
        .filter(
            PRDDocument.conversation_id == conversation_id,
            PRDDocument.version_number == data.to_version,
        )
        .first()
    )
    
    if not from_prd or not to_prd:
        raise HTTPException(status_code=404, detail="版本不存在")
    
    # 生成差异
    diff_text = generate_diff(from_prd.content, to_prd.content)
    diff_view = format_diff_view(diff_text)
    
    return {
        "from_version": data.from_version,
        "to_version": data.to_version,
        "from_content": from_prd.content,
        "to_content": to_prd.content,
        "diff": diff_text,
        "diff_view": diff_view,
        "summary": diff_view.get("summary", "")
    }
async def compare_prd_versions(
    conversation_id: str,
    data: PRDCompareRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """对比两个 PRD 版本"""
    service = PRDVersionService(db)
    result = service.compare_versions(
        data.from_version, data.to_version, conversation_id
    )

    if not result:
        raise HTTPException(status_code=404, detail="版本不存在")

    return result


@router.post(
    "/conversations/{conversation_id}/prd/rollback", response_model=PRDResponse
)
async def rollback_prd(
    conversation_id: str,
    data: PRDRollbackRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """回滚到指定版本"""
    service = PRDVersionService(db)
    prd = service.rollback_to_version(conversation_id, data.target_version)

    if not prd:
        raise HTTPException(status_code=404, detail="目标版本不存在")

    return prd

@router.post("/conversations/{conversation_id}/prd/section/update")
async def update_prd_section(
    conversation_id: str,
    data: PRDSectionUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """更新 PRD 的指定章节"""
    service = PRDGeneratorService(db)
    
    # 获取最新版本的 PRD
    versions = service.list_prds(conversation_id, limit=1)
    if not versions:
        raise HTTPException(status_code=404, detail="PRD 不存在")
    
    latest_prd = versions[0]
    
    # 更新章节
    updated_prd = service.update_section(
        prd_id=str(latest_prd.id),
        section_title=data.section_title,
        section_content=data.section_content
    )
    
    return updated_prd


@router.post("/conversations/{conversation_id}/prd/generate-partial", response_model=PRDResponse)
async def generate_partial_prd(
    conversation_id: str,
    data: PRDPartialGenerate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """生成 PRD 的指定章节"""
    # TODO: 集成 LLM 服务
    # 这里先返回模板
    content = "\n\n".join([f"## {section}\n\n[待生成内容]" for section in data.sections])
    
    service = PRDVersionService(db)
    prd = service.create_version(conversation_id, content)
    return prd
@router.post("/conversations/{conversation_id}/prd/export")
async def export_prd(
    conversation_id: str,
    data: PRDExportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """导出 PRD"""
    # TODO: 实现导出逻辑
    return {
        "message": "导出功能开发中",
        "format": data.format,
        "version": data.version_number,
    }
