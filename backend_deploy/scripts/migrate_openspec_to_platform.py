#!/usr/bin/env python3
"""
将 openspec_course 数据迁移到 course_platform

迁移步骤：
1. 将 openspec_course_chapters 数据迁移到 course_chapters
2. 迁移测验、题目、选项、资源数据
3. 保持 slug 不变，确保用户端链接有效
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config.database import DATABASE_URL

# 使用 PostgreSQL 数据库
engine = create_engine(DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://"))
SessionLocal = sessionmaker(bind=engine)

# 动态导入模型，避免循环导入
def import_models():
    from app.models.openspec_course import (
        OpenSpecCourseChapter,
        OpenSpecCourseQuiz,
        OpenSpecCourseQuizQuestion,
        OpenSpecCourseQuizOption,
        OpenSpecCourseResource,
    )
    from app.models.course_platform import (
        Course,
        CourseChapter,
        CourseQuiz,
        CourseQuizQuestion,
        CourseQuizOption,
        CourseResource,
    )
    return (
        OpenSpecCourseChapter,
        OpenSpecCourseQuiz,
        OpenSpecCourseQuizQuestion,
        OpenSpecCourseQuizOption,
        OpenSpecCourseResource,
        Course,
        CourseChapter,
        CourseQuiz,
        CourseQuizQuestion,
        CourseQuizOption,
        CourseResource,
    )


def migrate():
    db = SessionLocal()

    # 导入模型
    (
        OpenSpecCourseChapter,
        OpenSpecCourseQuiz,
        OpenSpecCourseQuizQuestion,
        OpenSpecCourseQuizOption,
        OpenSpecCourseResource,
        Course,
        CourseChapter,
        CourseQuiz,
        CourseQuizQuestion,
        CourseQuizOption,
        CourseResource,
    ) = import_models()

    migrated_chapters = 0
    migrated_quizzes = 0
    migrated_questions = 0
    migrated_options = 0
    migrated_resources = 0

    try:
        # 1. 查找课程（用户端已存在的课程）
        course = db.query(Course).filter_by(slug="openspec-vibecoding-practice").first()
        if not course:
            print("✗ 错误：课程 'openspec-vibecoding-practice' 不存在")
            print("请先在用户端创建该课程")
            return 1

        print(f"✓ 找到课程：ID={course.id}, slug={course.slug}, title={course.title}")

        # 2. 迁移章节数据
        print("\n=== 迁移章节数据 ===")
        openspec_chapters = db.query(OpenSpecCourseChapter).order_by(OpenSpecCourseChapter.order).all()
        print(f"找到 {len(openspec_chapters)} 个章节")

        for os_chapter in openspec_chapters:
            # 检查是否已存在
            existing = db.query(CourseChapter).filter_by(slug=os_chapter.slug).first()

            if existing:
                # 更新现有章节
                existing.title = os_chapter.title
                existing.content = os_chapter.content
                existing.order = os_chapter.order
                existing.chapter_type = os_chapter.chapter_type
                existing.video_url = os_chapter.video_url
                existing.is_locked = os_chapter.is_locked
                existing.course_id = course.id  # 关联到课程
                print(f"  [更新] {os_chapter.slug}: {os_chapter.title[:30]}...")
            else:
                # 创建新章节
                chapter = CourseChapter(
                    course_id=course.id,
                    slug=os_chapter.slug,
                    title=os_chapter.title,
                    order=os_chapter.order,
                    content=os_chapter.content,
                    chapter_type=os_chapter.chapter_type,
                    video_url=os_chapter.video_url,
                    is_locked=os_chapter.is_locked,
                    duration_minutes=10,  # 默认值
                )
                db.add(chapter)
                db.flush()
                print(f"  [创建] {os_chapter.slug}: {os_chapter.title}")

            migrated_chapters += 1

        # 3. 迁移测验数据
        print("\n=== 迁移测验数据 ===")
        openspec_quizzes = db.query(OpenSpecCourseQuiz).all()
        print(f"找到 {len(openspec_quizzes)} 个测验")

        # 构建 openspec_chapter_id 到 course_chapter 的映射
        chapter_slug_map = {}
        for os_chapter in openspec_chapters:
            course_chapter = db.query(CourseChapter).filter_by(slug=os_chapter.slug).first()
            if course_chapter:
                chapter_slug_map[os_chapter.id] = course_chapter

        for os_quiz in openspec_quizzes:
            course_chapter = chapter_slug_map.get(os_quiz.chapter_id)
            if not course_chapter:
                print(f"  [跳过] 测验 ID={os_quiz.id}，章节不存在")
                continue

            # 检查是否已存在
            existing = db.query(CourseQuiz).filter_by(chapter_id=course_chapter.id).first()

            if existing:
                # 更新
                existing.title = os_quiz.title
                existing.passing_score = os_quiz.passing_score
                print(f"  [更新] {os_quiz.title}")
            else:
                # 创建（CourseQuiz 没有 slug 字段）
                quiz = CourseQuiz(
                    chapter_id=course_chapter.id,
                    title=os_quiz.title,
                    passing_score=os_quiz.passing_score,
                )
                db.add(quiz)
                db.flush()
                print(f"  [创建] {os_quiz.title}")

            migrated_quizzes += 1

        # 4. 迁移测验题目和选项
        print("\n=== 迁移测验题目 ===")
        openspec_questions = db.query(OpenSpecCourseQuizQuestion).all()
        print(f"找到 {len(openspec_questions)} 道题目")

        # 构建 openspec_quiz_id 到 course_quiz 的映射
        quiz_chapter_map = {}
        for os_chapter in openspec_chapters:
            course_chapter = db.query(CourseChapter).filter_by(slug=os_chapter.slug).first()
            if course_chapter:
                os_quiz = db.query(OpenSpecCourseQuiz).filter_by(chapter_id=os_chapter.id).first()
                if os_quiz:
                    course_quiz = db.query(CourseQuiz).filter_by(chapter_id=course_chapter.id).first()
                    if course_quiz:
                        quiz_chapter_map[os_quiz.id] = course_quiz

        for os_question in openspec_questions:
            course_quiz = quiz_chapter_map.get(os_question.quiz_id)
            if not course_quiz:
                print(f"  [跳过] 题目 ID={os_question.id}，测验不存在")
                continue

            # 创建题目
            question = CourseQuizQuestion(
                quiz_id=course_quiz.id,
                question_text=os_question.question_text,
                question_type=os_question.question_type,
                correct_answer=os_question.correct_answer,
                explanation=os_question.explanation,
                order=os_question.order,
            )
            db.add(question)
            db.flush()
            migrated_questions += 1

            # 迁移选项
            os_options = db.query(OpenSpecCourseQuizOption).filter_by(question_id=os_question.id).all()
            for os_option in os_options:
                option = CourseQuizOption(
                    question_id=question.id,
                    option_text=os_option.option_text,
                    option_index=os_option.option_index,
                )
                db.add(option)
                migrated_options += 1

        # 5. 迁移资源数据
        print("\n=== 迁移资源数据 ===")
        openspec_resources = db.query(OpenSpecCourseResource).all()
        print(f"找到 {len(openspec_resources)} 个资源")

        # 构建 openspec_chapter_id 到 course_chapter 的映射（复用）
        for os_resource in openspec_resources:
            course_chapter = chapter_slug_map.get(os_resource.chapter_id)
            if not course_chapter:
                print(f"  [跳过] 资源 ID={os_resource.id}，章节不存在")
                continue

            resource = CourseResource(
                chapter_id=course_chapter.id,
                resource_type=os_resource.resource_type,
                title=os_resource.title,
                content=os_resource.content,
                extra_data=os_resource.extra_data,
            )
            db.add(resource)
            migrated_resources += 1

        # 6. 提交
        db.commit()

        print("\n" + "=" * 50)
        print("✓ 迁移完成!")
        print("=" * 50)
        print(f"  章节：   {migrated_chapters}")
        print(f"  测验：   {migrated_quizzes}")
        print(f"  题目：   {migrated_questions}")
        print(f"  选项：   {migrated_options}")
        print(f"  资源：   {migrated_resources}")
        print("=" * 50)

    except Exception as e:
        db.rollback()
        print(f"\n✗ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    exit(migrate())
