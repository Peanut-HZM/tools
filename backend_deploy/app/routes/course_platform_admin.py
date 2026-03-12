"""
课程学习平台管理后台 API 路由

提供课程管理 CRUD、发布、导入导出等功能（管理员专用）。
"""
import logging
import io
import json
from fastapi import APIRouter, HTTPException, Depends, Query, Body, status
from fastapi.responses import JSONResponse, Response, StreamingResponse
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.models.base import get_db
from app.models.course_platform import (
    Course, CourseCategory, CourseChapter, CourseStatistics,
    CourseEnrollment, CourseInteraction, CourseReview,
    CourseQuiz, CourseQuizQuestion, CourseQuizOption, CourseResource,
)
from app.schemas.course_platform import (
    CourseCreate, CourseUpdate, CourseResponse, CourseListItem,
    CourseChapterCreate, CourseChapterUpdate, CourseChapterResponse,
    CourseExportData, ImportStrategy, ImportPreviewRequest, ImportResponse,
    CourseQuizCreate, CourseQuizUpdate, CourseQuizResponse,
    CourseQuizQuestionCreate, CourseQuizOptionCreate,
    CourseResourceCreate, CourseResourceUpdate, CourseResourceResponse,
)
from app.services.course_import_export_service import CourseExportService, CourseImportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["course-platform-admin"])


def get_current_user_id() -> str:
    """获取当前用户 ID（简化版本）"""
    return "admin-user"


def is_admin() -> bool:
    """检查用户是否有管理员权限（简化版本）"""
    return True


# ============ 课程管理接口 ============

@router.get(
    "/courses",
    summary="获取课程管理列表",
    description="获取所有课程列表（管理员专用）",
)
async def get_admin_courses(
    status_filter: Optional[str] = Query(None, alias="status", description="状态筛选：draft/published/archived"),
    search: Optional[str] = Query(None, description="搜索关键词（课程标题/描述/章节内容）"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """获取课程管理列表（Admin）"""
    try:
        query = db.query(Course)

        # 状态筛选
        if status_filter:
            query = query.filter(Course.status == status_filter)

        # 搜索：课程标题、描述或章节内容
        if search:
            search_filter = f"%{search}%"
            # 搜索课程标题和描述
            course_match = Course.title.ilike(search_filter) | Course.description.ilike(search_filter)

            # 搜索章节内容（通过子查询）
            chapter_subquery = db.query(CourseChapter.course_id).filter(
                CourseChapter.title.ilike(search_filter) | CourseChapter.content.ilike(search_filter)
            ).distinct()

            chapter_match = Course.id.in_(chapter_subquery)

            query = query.filter(course_match | chapter_match)

        total = query.count()
        courses = query.order_by(Course.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

        return {
            "courses": courses,
            "total": total,
            "page": page,
            "limit": limit,
        }

    except Exception as e:
        logger.error(f"获取课程管理列表失败：{e}")
        raise HTTPException(status_code=500, detail="获取课程列表失败")


@router.get(
    "/courses/{id}",
    response_model=CourseResponse,
    summary="获取课程详情",
    description="获取指定课程详情（管理员专用）",
)
async def get_admin_course(
    id: int,
    db: Session = Depends(get_db),
):
    """获取课程详情（Admin）"""
    try:
        course = db.query(Course).filter_by(id=id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")
        return course

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取课程详情失败 (course_id={id}): {e}")
        raise HTTPException(status_code=500, detail="获取课程详情失败")


@router.post(
    "/courses",
    response_model=CourseResponse,
    summary="创建课程",
    description="创建新课程（管理员专用）",
)
async def create_admin_course(
    course_data: CourseCreate,
    db: Session = Depends(get_db),
):
    """创建课程（Admin）"""
    try:
        # 检查 slug 是否已存在
        existing = db.query(Course).filter_by(slug=course_data.slug).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"课程标识符 '{course_data.slug}' 已存在")

        course = Course(
            title=course_data.title,
            slug=course_data.slug,
            description=course_data.description,
            cover_image=course_data.cover_image,
            category_id=course_data.category_id,
            instructor_id=course_data.instructor_id,
            price=course_data.price,
            status=course_data.status,
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        # 初始化统计数据
        stats = CourseStatistics(course_id=course.id)
        db.add(stats)
        db.commit()

        return course

    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"创建课程 - 参数验证失败：{e}")
        raise HTTPException(status_code=400, detail=f"参数验证失败：{str(e)}")
    except Exception as e:
        logger.error(f"创建课程失败：{e}")
        raise HTTPException(status_code=500, detail="创建课程失败")


@router.put(
    "/courses/{id}",
    response_model=CourseResponse,
    summary="更新课程",
    description="更新课程信息（管理员专用）",
)
async def update_admin_course(
    id: int,
    course_data: CourseUpdate,
    db: Session = Depends(get_db),
):
    """更新课程（Admin）"""
    try:
        course = db.query(Course).filter_by(id=id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")

        # 更新字段
        update_data = course_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(course, field, value)

        db.commit()
        db.refresh(course)
        return course

    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"更新课程 - 参数验证失败 (course_id={id}): {e}")
        raise HTTPException(status_code=400, detail=f"参数验证失败：{str(e)}")
    except Exception as e:
        logger.error(f"更新课程失败 (course_id={id}): {e}")
        raise HTTPException(status_code=500, detail="更新课程失败")


@router.delete(
    "/courses/{id}",
    summary="删除课程",
    description="删除课程（管理员专用）",
)
async def delete_admin_course(
    id: int,
    db: Session = Depends(get_db),
):
    """删除课程（Admin）"""
    try:
        course = db.query(Course).filter_by(id=id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")

        db.delete(course)
        db.commit()
        return {"message": "删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除课程失败 (course_id={id}): {e}")
        raise HTTPException(status_code=500, detail="删除课程失败")


@router.post(
    "/courses/{id}/publish",
    summary="发布课程",
    description="发布/取消发布课程（管理员专用）",
)
async def publish_admin_course(
    id: int,
    publish: bool = Query(True, description="是否发布"),
    db: Session = Depends(get_db),
):
    """发布课程（Admin）"""
    try:
        course = db.query(Course).filter_by(id=id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")

        course.status = "published" if publish else "draft"
        db.commit()
        return {"message": f"课程已{'发布' if publish else '取消发布'}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发布课程失败 (course_id={id}): {e}")
        raise HTTPException(status_code=500, detail="发布课程失败")


# ============ 章节管理接口 ============

@router.get(
    "/courses/{course_id}/chapters",
    response_model=List[CourseChapterResponse],
    summary="获取章节列表",
    description="获取指定课程的所有章节（管理员专用）",
)
async def get_admin_chapters(
    course_id: int,
    db: Session = Depends(get_db),
):
    """获取章节列表（Admin）"""
    try:
        # 验证课程存在
        course = db.query(Course).filter_by(id=course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")

        # 获取章节列表，按 order 排序
        chapters = db.query(CourseChapter).filter_by(course_id=course_id).order_by(CourseChapter.order).all()
        return chapters

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取章节列表失败 (course_id={course_id}): {e}")
        raise HTTPException(status_code=500, detail="获取章节列表失败")


@router.post(
    "/courses/{course_id}/chapters",
    response_model=CourseChapterResponse,
    summary="创建章节",
    description="为课程创建新章节（管理员专用）",
)
async def create_admin_chapter(
    course_id: int,
    chapter_data: CourseChapterCreate,
    db: Session = Depends(get_db),
):
    """创建章节（Admin）"""
    try:
        course = db.query(Course).filter_by(id=course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")

        chapter = CourseChapter(
            course_id=course_id,
            slug=chapter_data.slug,
            title=chapter_data.title,
            order=chapter_data.order,
            content=chapter_data.content,
            chapter_type=chapter_data.chapter_type,
            video_url=chapter_data.video_url,
            is_locked=chapter_data.is_locked,
            duration_minutes=chapter_data.duration_minutes,
        )
        db.add(chapter)
        db.commit()
        db.refresh(chapter)
        return chapter

    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"创建章节 - 参数验证失败：{e}")
        raise HTTPException(status_code=400, detail=f"参数验证失败：{str(e)}")
    except Exception as e:
        logger.error(f"创建章节失败：{e}")
        raise HTTPException(status_code=500, detail="创建章节失败")


@router.put(
    "/courses/{course_id}/chapters/{chapter_id}",
    response_model=CourseChapterResponse,
    summary="更新章节",
    description="更新章节信息（管理员专用）",
)
async def update_admin_chapter(
    course_id: int,
    chapter_id: int,
    chapter_data: CourseChapterUpdate,
    db: Session = Depends(get_db),
):
    """更新章节（Admin）"""
    try:
        chapter = db.query(CourseChapter).filter_by(id=chapter_id, course_id=course_id).first()
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        update_data = chapter_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(chapter, field, value)

        db.commit()
        db.refresh(chapter)
        return chapter

    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"更新章节 - 参数验证失败：{e}")
        raise HTTPException(status_code=400, detail=f"参数验证失败：{str(e)}")
    except Exception as e:
        logger.error(f"更新章节失败：{e}")
        raise HTTPException(status_code=500, detail="更新章节失败")


@router.delete(
    "/courses/{course_id}/chapters/{chapter_id}",
    summary="删除章节",
    description="删除章节（管理员专用）",
)
async def delete_admin_chapter(
    course_id: int,
    chapter_id: int,
    db: Session = Depends(get_db),
):
    """删除章节（Admin）"""
    try:
        chapter = db.query(CourseChapter).filter_by(id=chapter_id, course_id=course_id).first()
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        db.delete(chapter)
        db.commit()
        return {"message": "删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除章节失败：{e}")
        raise HTTPException(status_code=500, detail="删除章节失败")


@router.put(
    "/courses/{course_id}/chapters/reorder",
    summary="重新排序章节",
    description="批量更新章节顺序（管理员专用）",
)
async def reorder_admin_chapters(
    course_id: int,
    chapter_orders: List[Dict[str, int]],
    db: Session = Depends(get_db),
):
    """重新排序章节（Admin）"""
    try:
        # chapter_orders: [{"id": 1, "order": 0}, {"id": 2, "order": 1}, ...]
        for item in chapter_orders:
            chapter = db.query(CourseChapter).filter_by(id=item["id"], course_id=course_id).first()
            if chapter:
                chapter.order = item["order"]

        db.commit()
        return {"message": "排序已更新"}

    except Exception as e:
        logger.error(f"重新排序章节失败：{e}")
        raise HTTPException(status_code=500, detail="重新排序失败")


# ============ 课程导入导出接口 ============

@router.post(
    "/courses/export",
    summary="导出课程数据",
    description="导出课程数据为 JSON 格式（管理员专用）",
)
async def export_course_data(
    course_id: Optional[int] = Query(None, description="课程 ID，不传则导出所有课程"),
    db: Session = Depends(get_db),
):
    """导出课程数据（Admin）"""
    try:
        export_service = CourseExportService(db)
        export_data = export_service.export_to_json(course_id=course_id)
        return export_data
    except Exception as e:
        logger.error(f"导出课程数据失败：{e}")
        raise HTTPException(status_code=500, detail="导出失败")


@router.post(
    "/courses/export-download",
    summary="下载课程 JSON 文件",
    description="下载课程数据 JSON 文件（管理员专用）",
)
async def download_course_export(
    course_id: Optional[int] = Query(None, description="课程 ID"),
    db: Session = Depends(get_db),
):
    """下载课程 JSON 文件"""
    try:
        export_service = CourseExportService(db)
        export_data = export_service.export_to_json(course_id=course_id)

        # 生成文件名
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"course_export_{timestamp}.json"

        # 创建 JSON 响应
        json_content = json.dumps(export_data.model_dump(), ensure_ascii=False, indent=2)

        response = StreamingResponse(
            io.BytesIO(json_content.encode('utf-8')),
            media_type="application/json",
        )
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response
    except Exception as e:
        logger.error(f"下载课程导出文件失败：{e}")
        raise HTTPException(status_code=500, detail="下载失败")


@router.post(
    "/courses/import/preview",
    summary="预览课程导入",
    description="预览课程导入数据，检查冲突（管理员专用）",
)
async def preview_course_import(
    request: ImportPreviewRequest,
    db: Session = Depends(get_db),
):
    """预览课程导入（Admin）"""
    try:
        import_service = CourseImportService(db)
        preview = import_service.preview_import(request.import_data, request.strategy)
        return preview
    except Exception as e:
        logger.error(f"预览导入失败：{e}")
        raise HTTPException(status_code=500, detail="预览失败")


@router.post(
    "/courses/import",
    summary="导入课程数据",
    description="导入课程数据（管理员专用）",
)
async def import_course_data(
    import_data: CourseExportData,
    strategy: ImportStrategy = Query(ImportStrategy.REPLACE, description="导入策略"),
    db: Session = Depends(get_db),
):
    """导入课程数据（Admin）"""
    try:
        import_service = CourseImportService(db)
        result = import_service.import_from_json(import_data, strategy)
        return result
    except Exception as e:
        logger.error(f"导入课程数据失败：{e}")
        raise HTTPException(status_code=500, detail="导入失败")


@router.post(
    "/courses/{course_id}/chapters/{chapter_id}/export-md",
    summary="导出章节 Markdown",
    description="导出单个章节为 Markdown 格式（管理员专用）",
)
async def export_chapter_markdown(
    course_id: int,
    chapter_id: int,
    db: Session = Depends(get_db),
):
    """导出章节 Markdown"""
    try:
        export_service = CourseExportService(db)
        markdown = export_service.export_chapter_to_markdown(chapter_id)
        return {"markdown": markdown}
    except Exception as e:
        logger.error(f"导出章节 Markdown 失败：{e}")
        raise HTTPException(status_code=500, detail="导出失败")


@router.post(
    "/courses/{course_id}/chapters/{chapter_id}/import-md/preview",
    summary="预览 Markdown 导入",
    description="预览 Markdown 导入章节更新（管理员专用）",
)
async def preview_markdown_import(
    course_id: int,
    chapter_id: int,
    markdown_content: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """预览 Markdown 导入（Admin）"""
    try:
        import_service = CourseImportService(db)
        preview = import_service.parse_markdown_import(markdown_content, chapter_id)
        return preview
    except Exception as e:
        logger.error(f"预览 Markdown 导入失败：{e}")
        raise HTTPException(status_code=500, detail="预览失败")


@router.post(
    "/courses/{course_id}/chapters/{chapter_id}/import-md",
    summary="导入 Markdown 更新",
    description="从 Markdown 导入章节更新（管理员专用）",
)
async def import_markdown_update(
    course_id: int,
    chapter_id: int,
    markdown_content: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """导入 Markdown 更新（Admin）"""
    try:
        import_service = CourseImportService(db)
        result = import_service.import_from_markdown(markdown_content, chapter_id, apply_changes=True)
        return result
    except Exception as e:
        logger.error(f"导入 Markdown 失败：{e}")
        raise HTTPException(status_code=500, detail="导入失败")


# ============ 测验管理接口 ============

@router.get(
    "/courses/{course_id}/chapters/{chapter_id}/quiz",
    response_model=CourseQuizResponse,
    summary="获取章节测验",
    description="获取指定章节的测验（包含题目和选项）",
)
async def get_chapter_quiz(
    course_id: int,
    chapter_id: int,
    db: Session = Depends(get_db),
):
    """获取章节测验（Admin）"""
    try:
        # 验证章节属于该课程
        chapter = db.query(CourseChapter).filter_by(id=chapter_id, course_id=course_id).first()
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        # 获取测验
        quiz = db.query(CourseQuiz).filter_by(chapter_id=chapter_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="该章节没有测验")

        # 加载问题
        questions = db.query(CourseQuizQuestion).filter_by(quiz_id=quiz.id).order_by(CourseQuizQuestion.order).all()

        # 为每个问题加载选项
        questions_with_options = []
        for question in questions:
            options = db.query(CourseQuizOption).filter_by(question_id=question.id).order_by(CourseQuizOption.option_index).all()
            question.options = options
            questions_with_options.append(question)

        quiz.questions = questions_with_options

        return quiz
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取章节测验失败：{e}")
        raise HTTPException(status_code=500, detail="获取测验失败")


@router.post(
    "/courses/{course_id}/chapters/{chapter_id}/quiz",
    response_model=CourseQuizResponse,
    summary="创建章节测验",
    description="为指定章节创建测验",
)
async def create_chapter_quiz(
    course_id: int,
    chapter_id: int,
    quiz_data: CourseQuizCreate,
    db: Session = Depends(get_db),
):
    """创建章节测验（Admin）"""
    try:
        # 验证章节属于该课程
        chapter = db.query(CourseChapter).filter_by(id=chapter_id, course_id=course_id).first()
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        # 检查是否已存在测验
        existing_quiz = db.query(CourseQuiz).filter_by(chapter_id=chapter_id).first()
        if existing_quiz:
            raise HTTPException(status_code=409, detail="该章节已有测验")

        # 创建测验
        quiz = CourseQuiz(
            chapter_id=chapter_id,
            title=quiz_data.title,
            passing_score=quiz_data.passing_score,
        )
        db.add(quiz)
        db.flush()

        # 创建问题和选项
        if quiz_data.questions:
            for q_data in quiz_data.questions:
                question = CourseQuizQuestion(
                    quiz_id=quiz.id,
                    question_text=q_data.question_text,
                    question_type=q_data.question_type,
                    correct_answer=q_data.correct_answer,
                    explanation=q_data.explanation,
                    order=q_data.order,
                )
                db.add(question)
                db.flush()

                # 创建选项
                if hasattr(q_data, 'options') and q_data.options:
                    for opt_data in q_data.options:
                        option = CourseQuizOption(
                            question_id=question.id,
                            option_text=opt_data.option_text,
                            option_index=opt_data.option_index,
                        )
                        db.add(option)

        db.commit()
        db.refresh(quiz)
        return quiz
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建章节测验失败：{e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="创建测验失败")


@router.put(
    "/courses/quizzes/{quiz_id}",
    response_model=CourseQuizResponse,
    summary="更新测验",
    description="更新测验信息",
)
async def update_quiz(
    quiz_id: int,
    quiz_data: CourseQuizUpdate,
    db: Session = Depends(get_db),
):
    """更新测验（Admin）"""
    try:
        quiz = db.query(CourseQuiz).filter_by(id=quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="测验不存在")

        update_data = quiz_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(quiz, field, value)

        db.commit()
        db.refresh(quiz)
        return quiz
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新测验失败：{e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="更新测验失败")


@router.delete(
    "/courses/quizzes/{quiz_id}",
    summary="删除测验",
    description="删除测验及其所有题目和选项",
)
async def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
):
    """删除测验（Admin）"""
    try:
        quiz = db.query(CourseQuiz).filter_by(id=quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="测验不存在")

        db.delete(quiz)
        db.commit()
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除测验失败：{e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="删除测验失败")


# ============ 资源管理接口 ============

@router.get(
    "/courses/{course_id}/chapters/{chapter_id}/resources",
    response_model=List[CourseResourceResponse],
    summary="获取章节资源",
    description="获取指定章节的所有资源",
)
async def get_chapter_resources(
    course_id: int,
    chapter_id: int,
    db: Session = Depends(get_db),
):
    """获取章节资源（Admin）"""
    try:
        # 验证章节属于该课程
        chapter = db.query(CourseChapter).filter_by(id=chapter_id, course_id=course_id).first()
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        # 获取资源
        resources = db.query(CourseResource).filter_by(chapter_id=chapter_id).all()
        return resources
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取章节资源失败：{e}")
        raise HTTPException(status_code=500, detail="获取资源失败")


@router.post(
    "/courses/resources",
    response_model=CourseResourceResponse,
    summary="创建资源",
    description="为章节创建新资源",
)
async def create_resource(
    resource_data: CourseResourceCreate,
    db: Session = Depends(get_db),
):
    """创建资源（Admin）"""
    try:
        # 验证章节存在
        chapter = db.query(CourseChapter).filter_by(id=resource_data.chapter_id).first()
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        resource = CourseResource(
            chapter_id=resource_data.chapter_id,
            resource_type=resource_data.resource_type,
            title=resource_data.title,
            content=resource_data.content,
            file_url=resource_data.file_url,
            file_size=resource_data.file_size,
            extra_data=resource_data.extra_data,
        )
        db.add(resource)
        db.commit()
        db.refresh(resource)
        return resource
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建资源失败：{e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="创建资源失败")


@router.put(
    "/courses/resources/{resource_id}",
    response_model=CourseResourceResponse,
    summary="更新资源",
    description="更新资源信息",
)
async def update_resource(
    resource_id: int,
    resource_data: CourseResourceUpdate,
    db: Session = Depends(get_db),
):
    """更新资源（Admin）"""
    try:
        resource = db.query(CourseResource).filter_by(id=resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="资源不存在")

        update_data = resource_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(resource, field, value)

        db.commit()
        db.refresh(resource)
        return resource
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新资源失败：{e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="更新资源失败")


@router.delete(
    "/courses/resources/{resource_id}",
    summary="删除资源",
    description="删除资源",
)
async def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
):
    """删除资源（Admin）"""
    try:
        resource = db.query(CourseResource).filter_by(id=resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="资源不存在")

        db.delete(resource)
        db.commit()
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除资源失败：{e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="删除资源失败")
