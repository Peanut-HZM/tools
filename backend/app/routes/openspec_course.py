"""
OpenSpec VibeCoding 互动课程 API 路由

提供课程章节、测验、资源和学习进度的管理功能。
"""
import json
import logging
import io
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, Body, status
from fastapi.responses import JSONResponse, Response
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.models.base import get_db
from app.services.openspec_course_service import OpenSpecCourseService
from app.services.course_import_export_service import CourseExportService, CourseImportService, CourseImportService
from app.schemas.openspec_course import (
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    ChapterDetailResponse,
    CourseListResponse,
    ChapterReorderRequest,
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
    CourseExportData,
    ImportStrategy,
    ImportPreviewRequest,
    ImportResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/openspec-course", tags=["openspec-course"])


def get_course_service(db: Session = Depends(get_db)) -> OpenSpecCourseService:
    """获取课程服务实例"""
    return OpenSpecCourseService(db)


def get_current_user_id() -> str:
    """获取当前用户 ID（简化版本）"""
    return "default-user"


# ============ 章节接口 ============

@router.get(
    "/chapters",
    response_model=CourseListResponse,
    summary="获取章节列表",
    description="获取所有课程章节的列表，按章节顺序（order）升序排列",
    responses={
        200: {"description": "成功获取章节列表"},
        500: {"description": "服务器内部错误"},
    },
)
async def get_chapters(
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """获取所有章节列表"""
    try:
        chapters = service.get_chapters()
        return {
            "chapters": chapters,
            "total": len(chapters),
        }
    except Exception as e:
        logger.error(f"获取章节列表失败：{e}")
        raise HTTPException(status_code=500, detail="获取章节列表失败")


@router.get(
    "/chapters/{chapter_id}",
    response_model=ChapterDetailResponse,
    summary="获取章节详情",
    description="获取指定章节的详细信息，包括章节内容、关联测验、学习资源和用户进度",
    responses={
        200: {"description": "成功获取章节详情"},
        404: {"description": "章节不存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def get_chapter(
    chapter_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """获取章节详情（包含测验、资源和用户进度）"""
    try:
        chapter = service.get_chapter_by_id(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        # 获取关联的测验
        quiz = service.get_quiz_by_chapter_id(chapter_id)

        # 获取资源
        resources = service.get_resources_by_chapter_id(chapter_id)

        # 处理资源的 extra_data 字段（从 JSON 字符串解析为 dict）
        processed_resources = []
        for r in resources:
            r_data = {
                "id": r.id,
                "chapter_id": r.chapter_id,
                "resource_type": r.resource_type,
                "title": r.title,
                "content": r.content,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            # 解析 extra_data
            if r.extra_data:
                try:
                    r_data["extra_data"] = json.loads(r.extra_data) if isinstance(r.extra_data, str) else r.extra_data
                except Exception:
                    r_data["extra_data"] = None
            else:
                r_data["extra_data"] = None
            processed_resources.append(r_data)

        # 处理测验数据（手动构建 questions）
        quiz_data = None
        if quiz:
            questions = service.get_quiz_questions(quiz.id)
            quiz_data = {
                "id": quiz.id,
                "chapter_id": quiz.chapter_id,
                "title": quiz.title,
                "passing_score": quiz.passing_score,
                "created_at": quiz.created_at,
                "updated_at": quiz.updated_at,
                "questions": questions or [],
            }

        # 构建响应数据 - 直接使用 ORM 对象，让 Pydantic 的 from_attributes 处理
        result = {
            "id": chapter.id,
            "slug": chapter.slug,
            "title": chapter.title,
            "order": chapter.order,
            "content": chapter.content,
            "chapter_type": chapter.chapter_type,
            "video_url": chapter.video_url,
            "is_locked": chapter.is_locked,
            "required_quiz_id": chapter.required_quiz_id,
            "created_at": chapter.created_at,
            "updated_at": chapter.updated_at,
            "quiz": quiz_data,
            "resources": processed_resources,
        }

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取章节详情失败 (chapter_id={chapter_id}): {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="获取章节详情失败")


@router.post(
    "/chapters",
    response_model=ChapterResponse,
    summary="创建章节",
    description="创建新的课程章节（管理员专用）",
    responses={
        200: {"description": "章节创建成功"},
        400: {"description": "请求参数验证失败"},
        409: {"description": "章节标识符（slug）已存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def create_chapter(
    chapter: ChapterCreate,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """创建章节（Admin）"""
    try:
        # 检查 slug 是否已存在
        existing = service.get_chapter_by_slug(chapter.slug)
        if existing:
            raise HTTPException(status_code=409, detail=f"章节标识符 '{chapter.slug}' 已存在")

        return service.create_chapter(chapter)
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"创建章节 - 参数验证失败：{e}")
        raise HTTPException(status_code=400, detail=f"参数验证失败：{str(e)}")
    except Exception as e:
        logger.error(f"创建章节失败：{e}")
        raise HTTPException(status_code=500, detail="创建章节失败")


@router.put(
    "/chapters/{chapter_id}",
    response_model=ChapterResponse,
    summary="更新章节",
    description="更新指定章节的信息（管理员专用）",
    responses={
        200: {"description": "章节更新成功"},
        404: {"description": "章节不存在"},
        400: {"description": "请求参数验证失败"},
        500: {"description": "服务器内部错误"},
    },
)
async def update_chapter(
    chapter_id: int,
    chapter: ChapterUpdate,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """更新章节（Admin）"""
    try:
        updated = service.update_chapter(chapter_id, chapter)
        if not updated:
            raise HTTPException(status_code=404, detail="章节不存在")
        return updated
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"更新章节 (chapter_id={chapter_id}) - 参数验证失败：{e}")
        raise HTTPException(status_code=400, detail=f"参数验证失败：{str(e)}")
    except Exception as e:
        logger.error(f"更新章节失败 (chapter_id={chapter_id}): {e}")
        raise HTTPException(status_code=500, detail="更新章节失败")


@router.delete(
    "/chapters/{chapter_id}",
    summary="删除章节",
    description="删除指定章节及其关联的测验和资源（管理员专用）",
    responses={
        200: {"description": "删除成功"},
        404: {"description": "章节不存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def delete_chapter(
    chapter_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """删除章节（Admin）"""
    try:
        if not service.delete_chapter(chapter_id):
            raise HTTPException(status_code=404, detail="章节不存在")
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除章节失败 (chapter_id={chapter_id}): {e}")
        raise HTTPException(status_code=500, detail="删除章节失败")


@router.put(
    "/chapters/reorder",
    response_model=Dict[str, Any],
    summary="批量更新章节顺序",
    description="批量更新多个章节的顺序（管理员专用）",
    responses={
        200: {"description": "更新成功"},
        400: {"description": "请求参数验证失败"},
        500: {"description": "更新失败"},
    },
)
async def reorder_chapters(
    request: ChapterReorderRequest,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """批量更新章节顺序（Admin）"""
    try:
        success = service.reorder_chapters(request)
        if not success:
            raise HTTPException(status_code=500, detail="更新章节顺序失败")
        return {"message": "更新成功"}
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"批量更新章节顺序 - 参数验证失败：{e}")
        raise HTTPException(status_code=400, detail=f"参数验证失败：{str(e)}")
    except Exception as e:
        logger.error(f"批量更新章节顺序失败：{e}")
        raise HTTPException(status_code=500, detail="更新章节顺序失败")


# ============ 测验接口 ============

@router.get(
    "/quizzes/chapter/{chapter_id}",
    response_model=QuizResponse,
    summary="获取章节测验",
    description="获取指定章节对应的测验",
    responses={
        200: {"description": "成功获取测验"},
        404: {"description": "该章节没有测验"},
        500: {"description": "服务器内部错误"},
    },
)
async def get_quiz_by_chapter(
    chapter_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """获取章节对应的测验（包含题目和选项）"""
    try:
        quiz = service.get_quiz_by_chapter_id(chapter_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="该章节没有测验")

        # 手动构建包含题目的响应
        questions = service.get_quiz_questions(quiz.id)
        quiz_data = {
            "id": quiz.id,
            "chapter_id": quiz.chapter_id,
            "title": quiz.title,
            "passing_score": quiz.passing_score,
            "created_at": quiz.created_at,
            "updated_at": quiz.updated_at,
            "questions": questions or [],
        }
        return quiz_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取章节测验失败 (chapter_id={chapter_id}): {e}")
        raise HTTPException(status_code=500, detail="获取测验失败")


@router.post(
    "/quizzes/{quiz_id}/submit",
    response_model=QuizResult,
    summary="提交测验答案",
    description="提交测验答案并获取评分结果",
    responses={
        200: {"description": "成功提交并获取结果"},
        404: {"description": "测验不存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def submit_quiz(
    quiz_id: int,
    request: QuizSubmitRequest,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """提交测验答案"""
    try:
        result = service.submit_quiz(quiz_id, "default-user", request.answers)
        return result
    except ValueError as e:
        logger.warning(f"提交测验失败 - 测验不存在 (quiz_id={quiz_id})")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"提交测验失败 (quiz_id={quiz_id}): {e}")
        raise HTTPException(status_code=500, detail="提交测验失败")


@router.post(
    "/quizzes",
    response_model=QuizResponse,
    summary="创建测验",
    description="创建新的测验，可同时创建题目和选项（管理员专用）",
    responses={
        200: {"description": "测验创建成功"},
        400: {"description": "请求参数验证失败"},
        404: {"description": "关联的章节不存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def create_quiz(
    quiz: QuizCreate,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """创建测验（Admin）"""
    try:
        # 验证章节是否存在
        chapter = service.get_chapter_by_id(quiz.chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail=f"章节 {quiz.chapter_id} 不存在")

        return service.create_quiz(quiz)
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"创建测验 - 参数验证失败：{e}")
        raise HTTPException(status_code=400, detail=f"参数验证失败：{str(e)}")
    except Exception as e:
        logger.error(f"创建测验失败：{e}")
        raise HTTPException(status_code=500, detail="创建测验失败")


@router.put(
    "/quizzes/{quiz_id}",
    response_model=QuizResponse,
    summary="更新测验",
    description="更新指定测验的信息（管理员专用）",
    responses={
        200: {"description": "测验更新成功"},
        404: {"description": "测验不存在"},
        400: {"description": "请求参数验证失败"},
        500: {"description": "服务器内部错误"},
    },
)
async def update_quiz(
    quiz_id: int,
    quiz: QuizUpdate,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """更新测验（Admin）"""
    try:
        updated = service.update_quiz(quiz_id, quiz)
        if not updated:
            raise HTTPException(status_code=404, detail="测验不存在")
        return updated
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"更新测验 (quiz_id={quiz_id}) - 参数验证失败：{e}")
        raise HTTPException(status_code=400, detail=f"参数验证失败：{str(e)}")
    except Exception as e:
        logger.error(f"更新测验失败 (quiz_id={quiz_id}): {e}")
        raise HTTPException(status_code=500, detail="更新测验失败")


@router.delete(
    "/quizzes/{quiz_id}",
    summary="删除测验",
    description="删除指定测验及其所有题目和选项（管理员专用）",
    responses={
        200: {"description": "删除成功"},
        404: {"description": "测验不存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def delete_quiz(
    quiz_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """删除测验（Admin）"""
    try:
        if not service.delete_quiz(quiz_id):
            raise HTTPException(status_code=404, detail="测验不存在")
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除测验失败 (quiz_id={quiz_id}): {e}")
        raise HTTPException(status_code=500, detail="删除测验失败")


# ============ 进度接口 ============

@router.get(
    "/progress",
    response_model=CourseProgressSummary,
    summary="获取用户课程进度",
    description="获取当前用户的课程学习进度汇总",
    responses={
        200: {"description": "成功获取进度汇总"},
        500: {"description": "服务器内部错误"},
    },
)
async def get_user_progress(
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """获取用户课程进度汇总"""
    try:
        summary = service.get_course_progress_summary("default-user")
        return summary
    except Exception as e:
        logger.error(f"获取用户进度汇总失败：{e}")
        raise HTTPException(status_code=500, detail="获取用户进度汇总失败")


@router.get(
    "/progress/chapter/{chapter_id}",
    response_model=UserProgressResponse,
    summary="获取章节学习进度",
    description="获取用户在指定章节的学习进度",
    responses={
        200: {"description": "成功获取进度"},
        500: {"description": "服务器内部错误"},
    },
)
async def get_chapter_progress(
    chapter_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """获取用户在特定章节的进度"""
    try:
        progress = service.get_user_progress("default-user", chapter_id)
        if not progress:
            # 返回默认进度（未开始状态）
            return UserProgressResponse(
                id=0,
                user_id="default-user",
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
    except Exception as e:
        logger.error(f"获取章节进度失败 (chapter_id={chapter_id}): {e}")
        raise HTTPException(status_code=500, detail="获取章节进度失败")


@router.put(
    "/progress/chapter/{chapter_id}",
    response_model=UserProgressResponse,
    summary="更新章节学习进度",
    description="更新用户在指定章节的学习进度",
    responses={
        200: {"description": "成功更新进度"},
        400: {"description": "请求参数验证失败"},
        500: {"description": "服务器内部错误"},
    },
)
async def update_chapter_progress(
    chapter_id: int,
    progress_data: UserProgressUpdate,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """更新用户在特定章节的进度"""
    try:
        progress = service.create_or_update_progress("default-user", chapter_id, progress_data)
        return progress
    except ValidationError as e:
        logger.error(f"更新章节进度 - 参数验证失败 (chapter_id={chapter_id}): {e}")
        raise HTTPException(status_code=400, detail=f"参数验证失败：{str(e)}")
    except Exception as e:
        logger.error(f"更新章节进度失败 (chapter_id={chapter_id}): {e}")
        raise HTTPException(status_code=500, detail="更新章节进度失败")


# ============ 资源接口 ============

@router.get(
    "/resources/chapter/{chapter_id}",
    response_model=List[ResourceResponse],
    summary="获取章节资源列表",
    description="获取指定章节的所有学习资源",
    responses={
        200: {"description": "成功获取资源列表"},
        404: {"description": "章节不存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def get_chapter_resources(
    chapter_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """获取章节的所有资源"""
    try:
        chapter = service.get_chapter_by_id(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        resources = service.get_resources_by_chapter_id(chapter_id)
        return resources
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取章节资源失败 (chapter_id={chapter_id}): {e}")
        raise HTTPException(status_code=500, detail="获取资源列表失败")


@router.get(
    "/resources/{resource_id}",
    response_model=ResourceResponse,
    summary="获取资源详情",
    description="获取指定学习资源的详细信息",
    responses={
        200: {"description": "成功获取资源详情"},
        404: {"description": "资源不存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def get_resource(
    resource_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """获取资源详情"""
    try:
        resource = service.get_resource_by_id(resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="资源不存在")
        return resource
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取资源详情失败 (resource_id={resource_id}): {e}")
        raise HTTPException(status_code=500, detail="获取资源详情失败")


@router.post(
    "/resources",
    response_model=ResourceResponse,
    summary="创建资源",
    description="为指定章节创建新的学习资源（管理员专用）",
    responses={
        200: {"description": "资源创建成功"},
        400: {"description": "请求参数验证失败"},
        404: {"description": "章节不存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def create_resource(
    resource: ResourceCreate,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """创建资源（Admin）"""
    try:
        chapter = service.get_chapter_by_id(resource.chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        return service.create_resource(resource)
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"创建资源 - 参数验证失败：{e}")
        raise HTTPException(status_code=400, detail=f"参数验证失败：{str(e)}")
    except Exception as e:
        logger.error(f"创建资源失败：{e}")
        raise HTTPException(status_code=500, detail="创建资源失败")


@router.put(
    "/resources/{resource_id}",
    response_model=ResourceResponse,
    summary="更新资源",
    description="更新指定学习资源的信息（管理员专用）",
    responses={
        200: {"description": "资源更新成功"},
        404: {"description": "资源不存在"},
        400: {"description": "请求参数验证失败"},
        500: {"description": "服务器内部错误"},
    },
)
async def update_resource(
    resource_id: int,
    resource: ResourceUpdate,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """更新资源（Admin）"""
    try:
        updated = service.update_resource(resource_id, resource)
        if not updated:
            raise HTTPException(status_code=404, detail="资源不存在")
        return updated
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"更新资源 - 参数验证失败 (resource_id={resource_id}): {e}")
        raise HTTPException(status_code=400, detail=f"参数验证失败：{str(e)}")
    except Exception as e:
        logger.error(f"更新资源失败 (resource_id={resource_id}): {e}")
        raise HTTPException(status_code=500, detail="更新资源失败")


@router.delete(
    "/resources/{resource_id}",
    summary="删除资源",
    description="删除指定的学习资源（管理员专用）",
    responses={
        200: {"description": "删除成功"},
        404: {"description": "资源不存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def delete_resource(
    resource_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """删除资源（Admin）"""
    try:
        if not service.delete_resource(resource_id):
            raise HTTPException(status_code=404, detail="资源不存在")
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除资源失败 (resource_id={resource_id}): {e}")
        raise HTTPException(status_code=500, detail="删除资源失败")


# ============ 导入/导出接口 ============

@router.post(
    "/export",
    response_model=Dict[str, Any],
    summary="导出课程数据",
    description="导出课程数据为 JSON 格式（管理员专用）",
    responses={
        200: {"description": "导出成功"},
        500: {"description": "服务器内部错误"},
    },
)
async def export_course_data(
    course_id: Optional[int] = Body(None, description="课程 ID（可选，用于元数据）"),
    course_title: Optional[str] = Body(None, description="课程标题（可选，用于元数据）"),
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """导出课程数据为 JSON（Admin）"""
    try:
        export_service = CourseExportService(db)
        export_data = export_service.export_to_json(course_id=course_id, course_title=course_title)

        return {
            "success": True,
            "data": export_data.model_dump(),
            "filename": f"course-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json",
        }
    except Exception as e:
        logger.error(f"导出课程数据失败：{e}")
        raise HTTPException(status_code=500, detail=f"导出失败：{str(e)}")


@router.post(
    "/import/preview",
    summary="预览导入",
    description="预览导入结果，不实际执行导入（管理员专用）",
    responses={
        200: {"description": "预览成功"},
        400: {"description": "请求参数验证失败"},
        500: {"description": "服务器内部错误"},
    },
)
async def preview_import(
    request: ImportPreviewRequest,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """预览导入结果（Admin）"""
    try:
        import_service = CourseImportService(db)
        preview = import_service.preview_import(request.import_data, request.strategy)
        return preview
    except Exception as e:
        logger.error(f"预览导入失败：{e}")
        raise HTTPException(status_code=500, detail=f"预览失败：{str(e)}")


@router.post(
    "/import",
    response_model=ImportResponse,
    summary="导入课程数据",
    description="从 JSON 导入课程数据（管理员专用）",
    responses={
        200: {"description": "导入成功"},
        400: {"description": "请求参数验证失败"},
        500: {"description": "服务器内部错误"},
    },
)
async def import_course_data(
    import_data: CourseExportData,
    strategy: ImportStrategy = Body(ImportStrategy.MERGE, description="导入策略"),
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """从 JSON 导入课程数据（Admin）"""
    try:
        import_service = CourseImportService(db)
        result = import_service.import_from_json(import_data, strategy)
        return result
    except Exception as e:
        logger.error(f"导入课程数据失败：{e}")
        raise HTTPException(status_code=500, detail=f"导入失败：{str(e)}")


@router.get(
    "/chapters/{chapter_id}/export-md",
    summary="导出章节为 Markdown",
    description="导出指定章节为 Markdown 格式",
    responses={
        200: {"description": "导出成功", "content": {"text/markdown": {}}},
        404: {"description": "章节不存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def export_chapter_markdown(
    chapter_id: int,
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """导出章节为 Markdown"""
    try:
        export_service = CourseExportService(db)
        markdown_content, filename = export_service.export_chapter_to_markdown(chapter_id)

        from fastapi.responses import Response
        return Response(
            content=markdown_content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"导出章节 Markdown 失败 (chapter_id={chapter_id}): {e}")
        raise HTTPException(status_code=500, detail=f"导出失败：{str(e)}")


@router.post(
    "/chapters/{chapter_id}/import-md/preview",
    summary="预览 Markdown 导入",
    description="预览 Markdown 导入的变更（管理员专用）",
    responses={
        200: {"description": "预览成功"},
        404: {"description": "章节不存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def preview_markdown_import(
    chapter_id: int,
    markdown_content: str = Body(..., embed=True, description="Markdown 内容"),
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """预览 Markdown 导入（Admin）"""
    try:
        import_service = CourseImportService(db)
        preview = import_service.parse_markdown_import(markdown_content, chapter_id)
        return {"success": True, "preview": preview.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"预览 Markdown 导入失败 (chapter_id={chapter_id}): {e}")
        raise HTTPException(status_code=500, detail=f"预览失败：{str(e)}")


@router.put(
    "/chapters/{chapter_id}/import-md",
    summary="从 Markdown 导入更新",
    description="从 Markdown 文件更新章节内容（管理员专用）",
    responses={
        200: {"description": "导入成功"},
        404: {"description": "章节不存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def import_markdown_update(
    chapter_id: int,
    markdown_content: str = Body(..., embed=True, description="Markdown 内容"),
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """从 Markdown 导入章节更新（Admin）"""
    try:
        import_service = CourseImportService(db)
        result = import_service.import_from_markdown(markdown_content, chapter_id, apply_changes=True)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"从 Markdown 导入失败 (chapter_id={chapter_id}): {e}")
        raise HTTPException(status_code=500, detail=f"导入失败：{str(e)}")


@router.get(
    "/export-zip",
    summary="导出课程为 ZIP 包",
    description="导出课程数据为 ZIP 格式，包含 JSON 数据和所有章节 Markdown 文件（管理员专用）",
    responses={
        200: {"description": "导出成功", "content": {"application/zip": {}}},
        500: {"description": "服务器内部错误"},
    },
)
async def export_course_zip(
    course_id: Optional[int] = Query(None, description="课程 ID（可选，用于元数据）"),
    course_title: Optional[str] = Query(None, description="课程标题（可选，用于元数据）"),
    service: OpenSpecCourseService = Depends(get_course_service),
    db: Session = Depends(get_db),
):
    """导出课程为 ZIP 包（Admin）"""
    try:
        export_service = CourseExportService(db)
        zip_bytes, filename = export_service.export_to_zip(course_id=course_id, course_title=course_title)

        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )
    except Exception as e:
        logger.error(f"导出课程 ZIP 包失败：{e}")
        raise HTTPException(status_code=500, detail=f"导出失败：{str(e)}")
