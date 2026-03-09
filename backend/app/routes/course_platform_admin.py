"""
课程学习平台管理后台 API 路由

提供课程管理 CRUD、发布等功能（管理员专用）。
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query, Body, status
from fastapi.responses import JSONResponse
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
)

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
