"""
技术分析内容平台 API 路由

提供技术分析内容的查询、列表、详情等接口。
"""
import json
import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.base import get_db
from app.models.course_platform import (
    Course, CourseCategory, CourseStatistics, CourseInteraction,
    CourseChapter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tech-contents", tags=["tech-contents"])


def get_content_type_label(content_type: str) -> str:
    """获取内容类型标签"""
    labels = {
        "analysis": "技术分析",
        "sharing": "技术分享",
        "case_study": "项目案例",
    }
    return labels.get(content_type, content_type)


@router.get("", summary="获取技术分析内容列表")
async def get_tech_contents(
    content_type: Optional[str] = Query(None, description="内容类型筛选：analysis/sharing/case_study"),
    tag: Optional[str] = Query(None, description="标签筛选"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=50, description="每页数量"),
    db: Session = Depends(get_db),
):
    """
    获取技术分析内容列表

    - **content_type**: 内容类型筛选（analysis/sharing/case_study）
    - **tag**: 标签筛选
    - **page**: 页码
    - **limit**: 每页数量
    """
    try:
        # 基础查询：只查询 published 状态的内容
        query = db.query(Course).filter(
            Course.status == "published",
            Course.content_type.in_(["analysis", "sharing", "case_study"]),
        )

        # 类型筛选
        if content_type:
            if content_type not in ["analysis", "sharing", "case_study"]:
                raise HTTPException(
                    status_code=400,
                    detail="无效的内容类型，必须是 analysis/sharing/case_study 之一"
                )
            query = query.filter(Course.content_type == content_type)

        # 标签筛选
        if tag:
            query = query.filter(Course.tags.ilike(f'%{tag}%'))

        # 分页
        offset = (page - 1) * limit
        courses = query.order_by(Course.created_at.desc()).offset(offset).limit(limit).all()

        # 总数
        total = query.count()

        # 序列化响应
        contents = []
        for course in courses:
            # 解析标签
            tags = []
            if course.tags:
                try:
                    tags = json.loads(course.tags) if isinstance(course.tags, str) else course.tags
                except:
                    tags = []

            # 获取统计数据
            stats = db.query(CourseStatistics).filter(
                CourseStatistics.course_id == course.id
            ).first()

            contents.append({
                "id": course.id,
                "slug": course.slug,
                "content_type": course.content_type,
                "content_type_label": get_content_type_label(course.content_type),
                "title": course.title,
                "description": course.description,
                "cover_image": course.cover_image,
                "author": course.author,
                "reading_time": course.reading_time,
                "tags": tags,
                "published_at": course.created_at.isoformat() if course.created_at else None,
                "views": stats.view_count if stats else 0,
                "likes": stats.like_count if stats else 0,
            })

        return {
            "contents": contents,
            "total": total,
            "page": page,
            "limit": limit,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取技术内容列表失败：{e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("/types", summary="获取内容类型列表")
async def get_content_types():
    """获取所有可用的内容类型"""
    return {
        "types": [
            {"value": "analysis", "label": "技术分析"},
            {"value": "sharing", "label": "技术分享"},
            {"value": "case_study", "label": "项目案例"},
        ]
    }


@router.get("/{slug}", summary="获取技术分析内容详情")
async def get_tech_content(
    slug: str,
    db: Session = Depends(get_db),
):
    """
    获取技术分析内容详情

    - **slug**: 内容标识符
    """
    try:
        # 查询内容
        course = db.query(Course).filter(
            Course.slug == slug,
            Course.status == "published",
            Course.content_type.in_(["analysis", "sharing", "case_study"]),
        ).first()

        if not course:
            raise HTTPException(status_code=404, detail="内容不存在")

        # 解析标签
        tags = []
        if course.tags:
            try:
                tags = json.loads(course.tags) if isinstance(course.tags, str) else course.tags
            except:
                tags = []

        # 获取统计数据
        stats = db.query(CourseStatistics).filter(
            CourseStatistics.course_id == course.id
        ).first()

        # 获取章节列表
        chapters = db.query(CourseChapter).filter(
            CourseChapter.course_id == course.id
        ).order_by(CourseChapter.order).all()

        chapter_list = []
        for chapter in chapters:
            chapter_list.append({
                "id": chapter.id,
                "slug": chapter.slug,
                "title": chapter.title,
                "order": chapter.order,
                "chapter_type": chapter.chapter_type,
                "reading_time": chapter.duration_minutes,  # 使用 duration_minutes 作为章节阅读时长
            })

        # 增加浏览次数
        if not stats:
            stats = CourseStatistics(course_id=course.id)
            db.add(stats)
        stats.view_count += 1
        db.commit()

        return {
            "id": course.id,
            "slug": course.slug,
            "content_type": course.content_type,
            "content_type_label": get_content_type_label(course.content_type),
            "title": course.title,
            "description": course.description,
            "cover_image": course.cover_image,
            "author": course.author,
            "reading_time": course.reading_time,
            "tags": tags,
            "published_at": course.created_at.isoformat() if course.created_at else None,
            "updated_at": course.updated_at.isoformat() if course.updated_at else None,
            "views": stats.view_count,
            "likes": stats.like_count if stats else 0,
            "bookmarks": stats.bookmark_count if stats else 0,
            "chapters": chapter_list,
            "content": course.description,  # 简介内容
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取技术内容详情失败：{e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("/tags/popular", summary="获取热门标签")
async def get_popular_tags(
    limit: int = Query(10, ge=1, le=50, description="返回标签数量"),
    db: Session = Depends(get_db),
):
    """获取热门标签列表"""
    try:
        # 查询所有有标签的内容
        courses = db.query(Course.tags).filter(
            Course.tags.isnot(None),
            Course.content_type.in_(["analysis", "sharing", "case_study"]),
        ).all()

        # 统计标签频率
        tag_counts = {}
        for (tags_json,) in courses:
            if tags_json:
                try:
                    tags = json.loads(tags_json) if isinstance(tags_json, str) else tags_json
                    for tag in tags:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
                except:
                    continue

        # 排序并返回
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

        return {
            "tags": [
                {"name": tag, "count": count}
                for tag, count in sorted_tags
            ]
        }

    except Exception as e:
        logger.error(f"获取热门标签失败：{e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")
