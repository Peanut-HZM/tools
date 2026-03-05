"""
OpenSpec VibeCoding 互动课程 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.base import get_db
from app.services.openspec_course_service import OpenSpecCourseService
from app.schemas.openspec_course import (
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    ChapterDetailResponse,
    CourseListResponse,
    QuizCreate,
    QuizUpdate,
    QuizResponse,
    QuizSubmitRequest,
    QuizResult,
    UserProgressCreate,
    UserProgressUpdate,
    UserProgressResponse,
    CourseProgressSummary,
    ResourceCreate,
    ResourceUpdate,
    ResourceResponse,
)
from app.utils.auth_utils import get_current_user  # 如果有 auth 的话

router = APIRouter(prefix="/api/openspec-course", tags=["openspec-course"])


def get_course_service(db: Session = Depends(get_db)) -> OpenSpecCourseService:
    """获取课程服务实例"""
    return OpenSpecCourseService(db)


# ============ 章节接口 ============

@router.get("/chapters", response_model=CourseListResponse)
async def get_chapters(service: OpenSpecCourseService = Depends(get_course_service)):
    """获取所有章节列表"""
    chapters = service.get_chapters()
    return {
        "chapters": chapters,
        "total": len(chapters),
    }


@router.get("/chapters/{chapter_id}", response_model=ChapterDetailResponse)
async def get_chapter(
    chapter_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
    current_user: Optional[Dict] = None,  # 如果有 auth，可以获取当前用户
):
    """获取章节详情（包含测验、资源和用户进度）"""
    chapter = service.get_chapter_by_id(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    # 获取关联的测验
    quiz = service.get_quiz_by_chapter_id(chapter_id)

    # 获取资源
    resources = service.get_resources_by_chapter_id(chapter_id)

    # 获取用户进度（如果有认证）
    user_progress = None
    if current_user and hasattr(current_user, "get"):
        user_id = current_user.get("user_id") or current_user.get("id")
        if user_id:
            user_progress = service.get_user_progress(user_id, chapter_id)

    return {
        "chapter": chapter,
        "quiz": quiz,
        "resources": resources,
        "user_progress": user_progress,
    }


@router.post("/chapters", response_model=ChapterResponse)
async def create_chapter(
    chapter: ChapterCreate,
    service: OpenSpecCourseService = Depends(get_course_service),
):
    """创建章节（Admin）"""
    # TODO: 添加 admin 权限检查
    return service.create_chapter(chapter)


@router.put("/chapters/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    chapter_id: int,
    chapter: ChapterUpdate,
    service: OpenSpecCourseService = Depends(get_course_service),
):
    """更新章节（Admin）"""
    # TODO: 添加 admin 权限检查
    updated = service.update_chapter(chapter_id, chapter)
    if not updated:
        raise HTTPException(status_code=404, detail="章节不存在")
    return updated


@router.delete("/chapters/{chapter_id}")
async def delete_chapter(
    chapter_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
):
    """删除章节（Admin）"""
    # TODO: 添加 admin 权限检查
    if not service.delete_chapter(chapter_id):
        raise HTTPException(status_code=404, detail="章节不存在")
    return {"message": "删除成功"}


# ============ 测验接口 ============

@router.get("/quizzes/chapter/{chapter_id}", response_model=QuizResponse)
async def get_quiz_by_chapter(
    chapter_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
):
    """获取章节对应的测验"""
    quiz = service.get_quiz_by_chapter_id(chapter_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="该章节没有测验")
    return quiz


@router.post("/quizzes/{quiz_id}/submit", response_model=QuizResult)
async def submit_quiz(
    quiz_id: int,
    request: QuizSubmitRequest,
    service: OpenSpecCourseService = Depends(get_course_service),
    current_user: Optional[Dict] = None,
):
    """提交测验答案"""
    if not current_user or not hasattr(current_user, "get"):
        raise HTTPException(status_code=401, detail="需要登录")

    user_id = current_user.get("user_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的用户信息")

    try:
        result = service.submit_quiz(quiz_id, user_id, request.answers)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/quizzes", response_model=QuizResponse)
async def create_quiz(
    quiz: QuizCreate,
    service: OpenSpecCourseService = Depends(get_course_service),
):
    """创建测验（Admin）"""
    # TODO: 添加 admin 权限检查
    return service.create_quiz(quiz)


@router.put("/quizzes/{quiz_id}", response_model=QuizResponse)
async def update_quiz(
    quiz_id: int,
    quiz: QuizUpdate,
    service: OpenSpecCourseService = Depends(get_course_service),
):
    """更新测验（Admin）"""
    # TODO: 添加 admin 权限检查
    updated = service.update_quiz(quiz_id, quiz)
    if not updated:
        raise HTTPException(status_code=404, detail="测验不存在")
    return updated


@router.delete("/quizzes/{quiz_id}")
async def delete_quiz(
    quiz_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
):
    """删除测验（Admin）"""
    # TODO: 添加 admin 权限检查
    if not service.delete_quiz(quiz_id):
        raise HTTPException(status_code=404, detail="测验不存在")
    return {"message": "删除成功"}


# ============ 进度接口 ============

@router.get("/progress", response_model=CourseProgressSummary)
async def get_user_progress(
    service: OpenSpecCourseService = Depends(get_course_service),
    current_user: Optional[Dict] = None,
):
    """获取用户课程进度汇总"""
    if not current_user or not hasattr(current_user, "get"):
        raise HTTPException(status_code=401, detail="需要登录")

    user_id = current_user.get("user_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的用户信息")

    summary = service.get_course_progress_summary(user_id)
    return summary


@router.get("/progress/chapter/{chapter_id}", response_model=UserProgressResponse)
async def get_chapter_progress(
    chapter_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
    current_user: Optional[Dict] = None,
):
    """获取用户在特定章节的进度"""
    if not current_user or not hasattr(current_user, "get"):
        raise HTTPException(status_code=401, detail="需要登录")

    user_id = current_user.get("user_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的用户信息")

    progress = service.get_user_progress(user_id, chapter_id)
    if not progress:
        # 返回默认进度
        return UserProgressResponse(
            id=0,
            user_id=user_id,
            chapter_id=chapter_id,
            status="not_started",
            quiz_score=None,
            quiz_passed=False,
            video_progress=0,
            completed_at=None,
            created_at=None,
            updated_at=None,
        )
    return progress


@router.put("/progress/chapter/{chapter_id}", response_model=UserProgressResponse)
async def update_chapter_progress(
    chapter_id: int,
    progress_data: UserProgressUpdate,
    service: OpenSpecCourseService = Depends(get_course_service),
    current_user: Optional[Dict] = None,
):
    """更新用户在特定章节的进度"""
    if not current_user or not hasattr(current_user, "get"):
        raise HTTPException(status_code=401, detail="需要登录")

    user_id = current_user.get("user_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的用户信息")

    progress = service.create_or_update_progress(user_id, chapter_id, progress_data)
    return progress


# ============ 资源接口 ============

@router.get("/resources/chapter/{chapter_id}", response_model=List[ResourceResponse])
async def get_chapter_resources(
    chapter_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
):
    """获取章节的所有资源"""
    # 验证章节是否存在
    chapter = service.get_chapter_by_id(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    resources = service.get_resources_by_chapter_id(chapter_id)
    return resources


@router.get("/resources/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
):
    """获取资源详情"""
    resource = service.get_resource_by_id(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    return resource


@router.post("/resources", response_model=ResourceResponse)
async def create_resource(
    resource: ResourceCreate,
    service: OpenSpecCourseService = Depends(get_course_service),
):
    """创建资源（Admin）"""
    # TODO: 添加 admin 权限检查
    # 验证章节是否存在
    chapter = service.get_chapter_by_id(resource.chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return service.create_resource(resource)


@router.put("/resources/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: int,
    resource: ResourceUpdate,
    service: OpenSpecCourseService = Depends(get_course_service),
):
    """更新资源（Admin）"""
    # TODO: 添加 admin 权限检查
    updated = service.update_resource(resource_id, resource)
    if not updated:
        raise HTTPException(status_code=404, detail="资源不存在")
    return updated


@router.delete("/resources/{resource_id}")
async def delete_resource(
    resource_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
):
    """删除资源（Admin）"""
    # TODO: 添加 admin 权限检查
    if not service.delete_resource(resource_id):
        raise HTTPException(status_code=404, detail="资源不存在")
    return {"message": "删除成功"}
