"""
课程学习平台 API 路由

提供课程列表、详情、分类、报名、互动、评价等功能。
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
    CourseEnrollment, CourseInteraction, CourseReview
)
from app.schemas.course_platform import (
    CourseListResponse, CourseListItem, CourseDetailResponse,
    CourseResponse, CourseChapterResponse, CourseStatisticsResponse,
    CourseCategoryResponse, CourseCategoryTree,
    CourseEnrollmentCreate, CourseEnrollmentResponse,
    CourseInteractionCreate, CourseInteractionResponse,
    CourseReviewCreate, CourseReviewResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["course-platform"])


def get_current_user_id() -> str:
    """获取当前用户 ID（简化版本）"""
    return "default-user"


# ============ 课程列表接口 ============

@router.get(
    "/courses",
    response_model=CourseListResponse,
    summary="获取课程列表",
    description="获取课程列表，支持分页、筛选、排序",
)
async def get_course_list(
    category: Optional[str] = Query(None, description="分类 slug"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort: Optional[str] = Query("latest", description="排序方式：latest/hot/rating"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(12, ge=1, le=50, description="每页数量"),
    db: Session = Depends(get_db),
):
    """获取课程列表（支持分页、筛选、排序）"""
    try:
        # 构建查询
        query = db.query(Course).filter(Course.status == "published")

        # 分类筛选
        if category:
            cat = db.query(CourseCategory).filter_by(slug=category).first()
            if cat:
                query = query.filter_by(category_id=cat.id)

        # 搜索
        if search:
            query = query.filter(
                (Course.title.ilike(f"%{search}%")) |
                (Course.description.ilike(f"%{search}%"))
            )

        # 排序
        if sort == "hot":
            # 按浏览量排序（需要关联 statistics 表）
            query = query.join(CourseStatistics).order_by(CourseStatistics.view_count.desc())
        elif sort == "rating":
            # 按评分排序
            query = query.join(CourseStatistics).order_by(CourseStatistics.avg_rating.desc())
        else:
            # 默认按最新排序
            query = query.order_by(Course.created_at.desc())

        # 分页
        total = query.count()
        courses = query.offset((page - 1) * limit).limit(limit).all()

        # 构建响应
        items = []
        for course in courses:
            item = CourseListItem(
                id=course.id,
                slug=course.slug,
                title=course.title,
                description=course.description,
                cover_image=course.cover_image,
            )
            if course.category:
                item.category = CourseCategoryResponse(
                    id=course.category.id,
                    name=course.category.name,
                    slug=course.category.slug,
                    sort_order=course.category.sort_order,
                    icon=course.category.icon,
                    created_at=course.category.created_at,
                )
            if course.statistics:
                item.statistics = CourseStatisticsResponse(
                    id=course.statistics.id,
                    course_id=course.statistics.course_id,
                    view_count=course.statistics.view_count,
                    enroll_count=course.statistics.enroll_count,
                    like_count=course.statistics.like_count,
                    bookmark_count=course.statistics.bookmark_count,
                    review_count=course.statistics.review_count,
                    avg_rating=course.statistics.avg_rating,
                    completed_count=course.statistics.completed_count,
                    updated_at=course.statistics.updated_at,
                )
            items.append(item)

        return {
            "courses": items,
            "total": total,
            "page": page,
            "limit": limit,
        }

    except Exception as e:
        logger.error(f"获取课程列表失败：{e}")
        raise HTTPException(status_code=500, detail="获取课程列表失败")


# ============ 课程详情接口 ============

@router.get(
    "/courses/{slug}",
    response_model=CourseDetailResponse,
    summary="获取课程详情",
    description="获取课程详细信息，包含章节列表和统计数据",
)
async def get_course_detail(
    slug: str,
    db: Session = Depends(get_db),
):
    """获取课程详情"""
    try:
        course = db.query(Course).filter_by(slug=slug).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")

        # 累加浏览次数
        if not course.statistics:
            stats = CourseStatistics(course_id=course.id)
            db.add(stats)
            db.flush()
        course.statistics.view_count += 1
        db.flush()

        # 获取章节列表
        chapters = db.query(CourseChapter).filter_by(course_id=course.id).order_by(CourseChapter.order).all()

        # 构建响应
        return CourseDetailResponse(
            id=course.id,
            title=course.title,
            slug=course.slug,
            description=course.description,
            cover_image=course.cover_image,
            status=course.status,
            price=float(course.price) if course.price else 0,
            category_id=course.category_id,
            instructor_id=course.instructor_id,
            created_at=course.created_at,
            updated_at=course.updated_at,
            chapters=[
                CourseChapterResponse(
                    id=ch.id,
                    slug=ch.slug,
                    title=ch.title,
                    order=ch.order,
                    content=ch.content,
                    chapter_type=ch.chapter_type,
                    video_url=ch.video_url,
                    is_locked=False,  # 所有章节都开放学习
                    duration_minutes=ch.duration_minutes,
                    created_at=ch.created_at,
                    updated_at=ch.updated_at,
                    course_id=ch.course_id,
                ) for ch in chapters
            ],
            statistics=CourseStatisticsResponse(
                id=course.statistics.id,
                course_id=course.statistics.course_id,
                view_count=course.statistics.view_count,
                enroll_count=course.statistics.enroll_count,
                like_count=course.statistics.like_count,
                bookmark_count=course.statistics.bookmark_count,
                review_count=course.statistics.review_count,
                avg_rating=course.statistics.avg_rating,
                completed_count=course.statistics.completed_count,
                updated_at=course.statistics.updated_at,
            ) if course.statistics else None,
            category=CourseCategoryResponse(
                id=course.category.id,
                name=course.category.name,
                slug=course.category.slug,
                sort_order=course.category.sort_order,
                icon=course.category.icon,
                created_at=course.category.created_at,
            ) if course.category else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取课程详情失败 (slug={slug}): {e}")
        raise HTTPException(status_code=500, detail="获取课程详情失败")


# ============ 课程分类接口 ============

@router.get(
    "/course-categories",
    response_model=List[CourseCategoryTree],
    summary="获取课程分类",
    description="获取课程分类树形结构",
)
async def get_course_categories(
    db: Session = Depends(get_db),
):
    """获取课程分类树形结构"""
    try:
        # 获取所有一级分类
        parent_categories = db.query(CourseCategory).filter_by(parent_id=None).order_by(CourseCategory.sort_order).all()

        def build_tree(category):
            children = db.query(CourseCategory).filter_by(parent_id=category.id).order_by(CourseCategory.sort_order).all()
            return CourseCategoryTree(
                id=category.id,
                name=category.name,
                slug=category.slug,
                icon=category.icon,
                children=[build_tree(child) for child in children],
            )

        return [build_tree(cat) for cat in parent_categories]

    except Exception as e:
        logger.error(f"获取课程分类失败：{e}")
        raise HTTPException(status_code=500, detail="获取课程分类失败")


# ============ 用户课程接口 ============

@router.post(
    "/courses/{id}/enroll",
    response_model=CourseEnrollmentResponse,
    summary="报名课程",
    description="用户报名课程",
)
async def enroll_course(
    id: int,
    db: Session = Depends(get_db),
):
    """报名课程"""
    try:
        user_id = get_current_user_id()

        # 检查课程是否存在
        course = db.query(Course).filter_by(id=id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")

        # 检查是否已经报名
        existing = db.query(CourseEnrollment).filter_by(user_id=user_id, course_id=id).first()
        if existing:
            return CourseEnrollmentResponse(
                id=existing.id,
                user_id=existing.user_id,
                course_id=existing.course_id,
                status=existing.status,
                progress_percent=existing.progress_percent,
                enrolled_at=existing.enrolled_at,
                completed_at=existing.completed_at,
            )

        # 创建报名记录
        enrollment = CourseEnrollment(user_id=user_id, course_id=id)
        db.add(enrollment)

        # 更新统计
        if not course.statistics:
            course.statistics = CourseStatistics(course_id=id)
        course.statistics.enroll_count += 1

        db.commit()
        db.refresh(enrollment)

        return CourseEnrollmentResponse(
            id=enrollment.id,
            user_id=enrollment.user_id,
            course_id=enrollment.course_id,
            status=enrollment.status,
            progress_percent=enrollment.progress_percent,
            enrolled_at=enrollment.enrolled_at,
            completed_at=enrollment.completed_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"报名课程失败 (course_id={id}): {e}")
        raise HTTPException(status_code=500, detail="报名失败")


@router.get(
    "/my-courses",
    summary="获取我的课程",
    description="获取用户已报名的课程列表",
)
async def get_my_courses(
    db: Session = Depends(get_db),
):
    """获取我的课程"""
    try:
        user_id = get_current_user_id()

        enrollments = db.query(CourseEnrollment).filter_by(user_id=user_id).all()

        result = []
        for enrollment in enrollments:
            course = db.query(Course).filter_by(id=enrollment.course_id).first()
            if course:
                # 计算完成的章节数
                completed_chapters = db.query(CourseChapter).filter_by(course_id=course.id).count()

                result.append({
                    "course": CourseListItem(
                        id=course.id,
                        slug=course.slug,
                        title=course.title,
                        description=course.description,
                        cover_image=course.cover_image,
                    ),
                    "enrollment": CourseEnrollmentResponse(
                        id=enrollment.id,
                        user_id=enrollment.user_id,
                        course_id=enrollment.course_id,
                        status=enrollment.status,
                        progress_percent=enrollment.progress_percent,
                        enrolled_at=enrollment.enrolled_at,
                        completed_at=enrollment.completed_at,
                    ),
                    "completed_chapters": completed_chapters,
                    "total_chapters": completed_chapters,  # 简化处理
                })

        return {"courses": result, "total": len(result)}

    except Exception as e:
        logger.error(f"获取我的课程失败：{e}")
        raise HTTPException(status_code=500, detail="获取我的课程失败")


# ============ 互动统计接口 ============

@router.post(
    "/courses/{id}/like",
    response_model=CourseInteractionResponse,
    summary="点赞课程",
    description="用户点赞课程",
)
async def like_course(
    id: int,
    db: Session = Depends(get_db),
):
    """点赞课程"""
    try:
        user_id = get_current_user_id()

        # 检查课程是否存在
        course = db.query(Course).filter_by(id=id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")

        # 检查是否已经点赞
        existing = db.query(CourseInteraction).filter_by(
            user_id=user_id, course_id=id, interaction_type="like"
        ).first()
        if existing:
            return CourseInteractionResponse(
                id=existing.id,
                user_id=existing.user_id,
                course_id=existing.course_id,
                interaction_type=existing.interaction_type,
                created_at=existing.created_at,
            )

        # 创建点赞记录
        interaction = CourseInteraction(user_id=user_id, course_id=id, interaction_type="like")
        db.add(interaction)

        # 更新统计
        if not course.statistics:
            course.statistics = CourseStatistics(course_id=id)
        course.statistics.like_count += 1

        db.commit()
        db.refresh(interaction)

        return CourseInteractionResponse(
            id=interaction.id,
            user_id=interaction.user_id,
            course_id=interaction.course_id,
            interaction_type=interaction.interaction_type,
            created_at=interaction.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"点赞课程失败 (course_id={id}): {e}")
        raise HTTPException(status_code=500, detail="点赞失败")


@router.post(
    "/courses/{id}/bookmark",
    response_model=CourseInteractionResponse,
    summary="收藏课程",
    description="用户收藏课程",
)
async def bookmark_course(
    id: int,
    db: Session = Depends(get_db),
):
    """收藏课程"""
    try:
        user_id = get_current_user_id()

        # 检查课程是否存在
        course = db.query(Course).filter_by(id=id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")

        # 检查是否已经收藏
        existing = db.query(CourseInteraction).filter_by(
            user_id=user_id, course_id=id, interaction_type="bookmark"
        ).first()
        if existing:
            return CourseInteractionResponse(
                id=existing.id,
                user_id=existing.user_id,
                course_id=existing.course_id,
                interaction_type=existing.interaction_type,
                created_at=existing.created_at,
            )

        # 创建收藏记录
        interaction = CourseInteraction(user_id=user_id, course_id=id, interaction_type="bookmark")
        db.add(interaction)

        # 更新统计
        if not course.statistics:
            course.statistics = CourseStatistics(course_id=id)
        course.statistics.bookmark_count += 1

        db.commit()
        db.refresh(interaction)

        return CourseInteractionResponse(
            id=interaction.id,
            user_id=interaction.user_id,
            course_id=interaction.course_id,
            interaction_type=interaction.interaction_type,
            created_at=interaction.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"收藏课程失败 (course_id={id}): {e}")
        raise HTTPException(status_code=500, detail="收藏失败")


@router.get(
    "/courses/{id}/statistics",
    response_model=CourseStatisticsResponse,
    summary="获取课程统计",
    description="获取课程统计数据",
)
async def get_course_statistics(
    id: int,
    db: Session = Depends(get_db),
):
    """获取课程统计数据"""
    try:
        course = db.query(Course).filter_by(id=id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")

        if not course.statistics:
            course.statistics = CourseStatistics(course_id=id)
            db.add(course.statistics)
            db.commit()
            db.refresh(course.statistics)

        return CourseStatisticsResponse(
            id=course.statistics.id,
            course_id=course.statistics.course_id,
            view_count=course.statistics.view_count,
            enroll_count=course.statistics.enroll_count,
            like_count=course.statistics.like_count,
            bookmark_count=course.statistics.bookmark_count,
            review_count=course.statistics.review_count,
            avg_rating=course.statistics.avg_rating,
            completed_count=course.statistics.completed_count,
            updated_at=course.statistics.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取课程统计失败 (course_id={id}): {e}")
        raise HTTPException(status_code=500, detail="获取统计数据失败")


# ============ 课程评价接口 ============

@router.get(
    "/courses/{id}/reviews",
    response_model=List[CourseReviewResponse],
    summary="获取课程评价",
    description="获取课程评价列表（分页）",
)
async def get_course_reviews(
    id: int,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=50, description="每页数量"),
    db: Session = Depends(get_db),
):
    """获取课程评价列表"""
    try:
        reviews = db.query(CourseReview).filter_by(course_id=id).order_by(
            CourseReview.created_at.desc()
        ).offset((page - 1) * limit).limit(limit).all()

        return [
            CourseReviewResponse(
                id=r.id,
                user_id=r.user_id,
                course_id=r.course_id,
                rating=r.rating,
                comment=r.comment,
                created_at=r.created_at,
                updated_at=r.updated_at,
            ) for r in reviews
        ]

    except Exception as e:
        logger.error(f"获取课程评价失败 (course_id={id}): {e}")
        raise HTTPException(status_code=500, detail="获取评价列表失败")


@router.post(
    "/courses/{id}/reviews",
    response_model=CourseReviewResponse,
    summary="提交课程评价",
    description="用户提交课程评价",
)
async def create_course_review(
    id: int,
    review_data: CourseReviewCreate,
    db: Session = Depends(get_db),
):
    """提交课程评价"""
    try:
        user_id = get_current_user_id()

        # 检查课程是否存在
        course = db.query(Course).filter_by(id=id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")

        # 检查是否已经评价
        existing = db.query(CourseReview).filter_by(user_id=user_id, course_id=id).first()
        if existing:
            # 更新现有评价
            existing.rating = review_data.rating
            existing.comment = review_data.comment
            db.flush()

            # 重新计算平均评分
            avg = db.query(CourseReview).filter_by(course_id=id).all()
            if avg:
                course.statistics.avg_rating = sum(r.rating for r in avg) / len(avg)
                course.statistics.review_count = len(avg)

            db.commit()
            db.refresh(existing)

            return CourseReviewResponse(
                id=existing.id,
                user_id=existing.user_id,
                course_id=existing.course_id,
                rating=existing.rating,
                comment=existing.comment,
                created_at=existing.created_at,
                updated_at=existing.updated_at,
            )

        # 创建新评价
        review = CourseReview(
            user_id=user_id,
            course_id=id,
            rating=review_data.rating,
            comment=review_data.comment,
        )
        db.add(review)

        # 更新统计
        if not course.statistics:
            course.statistics = CourseStatistics(course_id=id)

        # 重新计算平均评分
        avg = db.query(CourseReview).filter_by(course_id=id).all()
        if avg:
            course.statistics.avg_rating = sum(r.rating for r in avg) / len(avg)
            course.statistics.review_count = len(avg)

        db.commit()
        db.refresh(review)

        return CourseReviewResponse(
            id=review.id,
            user_id=review.user_id,
            course_id=review.course_id,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
            updated_at=review.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交课程评价失败 (course_id={id}): {e}")
        raise HTTPException(status_code=500, detail="提交评价失败")
