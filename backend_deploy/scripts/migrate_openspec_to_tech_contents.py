#!/usr/bin/env python3
"""
将 OpenSpec VibeCoding 课程数据迁移为技术分析内容

读取 openspec_course_chapters 表的数据，转换为 courses 表的技术分析内容格式。

用法:
    python backend/scripts/migrate_openspec_to_tech_contents.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.config.config import settings
from app.models.base import Base, engine
from app.models.openspec_course import (
    OpenSpecCourseChapter as Branch,
    OpenSpecCourseQuiz as Quiz,
    OpenSpecCourseQuizQuestion as Question,
    OpenSpecCourseQuizOption as Option,
    OpenSpecCourseResource as Resource,
)
from app.models.course_platform import (
    Course, CourseChapter, CourseQuiz, CourseQuizQuestion, CourseQuizOption, CourseResource, CourseStatistics
)


def migrate():
    """执行迁移"""
    print("=" * 60)
    print("OpenSpec VibeCoding 课程迁移为技术分析内容")
    print("=" * 60)
    print()

    # 创建会话
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. 检查是否已有迁移数据
        existing = session.query(Course).filter(Course.slug == "openspec-vibecoding-practice").first()
        if existing:
            print("⚠️  检测到已有迁移数据，是否删除后重新迁移？(y/n)")
            choice = input("> ").strip().lower()
            if choice != 'y':
                print("已取消迁移")
                return

            # 删除现有数据
            print("正在删除现有数据...")
            session.query(Course).filter(Course.slug == "openspec-vibecoding-practice").delete()
            session.commit()

        # 2. 获取 OpenSpec 章节数据
        print("正在读取 OpenSpec 课程数据...")
        branches = session.query(Branch).order_by(Branch.order).all()
        print(f"✅ 找到 {len(branches)} 个章节")

        if not branches:
            print("❌ 没有找到 OpenSpec 课程数据")
            return

        # 3. 计算总阅读时长（估算：每 500 字 1 分钟）
        total_words = sum(len(branch.content) for branch in branches)
        estimated_reading_time = max(1, total_words // 500)

        # 4. 创建技术分析内容
        print("正在创建技术分析内容...")
        tech_content = Course(
            slug="openspec-vibecoding-practice",
            title="OpenSpec VibeCoding 实践指南",
            description="""本文深入分析 VibeCoding（AI 辅助编程）在企业级开发中的最佳实践。

## 内容概要

- **AI 编程心态**：从谨慎使用到高效协作的转变
- **Rules 的力量**：如何规范 AI 的行为模式
- **OpenSpec 方法论**：Spec 驱动的开发流程
- **工具对比**：OpenSpec vs spec-kit vs Superpowers

## 适合读者

- 正在使用或计划使用 AI 辅助编程的开发者
- 对 Spec 驱动开发感兴趣的技术团队
- 希望提升 AI 协作效率的工程师

## 阅读建议

本文包含 5 个章节，预计阅读时间 15 分钟。建议按顺序阅读，每个章节后有相关测验巩固知识点。""",
            content_type="analysis",
            author="OpenSpec Team",
            reading_time=estimated_reading_time,
            tags=json.dumps(["AI 编程", "VibeCoding", "OpenSpec", "工程实践", "Spec 驱动"], ensure_ascii=False),
            status="published",
        )
        session.add(tech_content)
        session.flush()
        print(f"✅ 创建技术分析内容：{tech_content.title}")

        # 5. 创建统计数据
        stats = CourseStatistics(
            course_id=tech_content.id,
            view_count=0,
            enroll_count=0,
            like_count=0,
            bookmark_count=0,
            review_count=0,
            avg_rating=0,
            completed_count=0,
        )
        session.add(stats)

        # 6. 迁移章节
        print("正在迁移章节...")
        branch_id_map = {}  # 原章节 ID -> 新章节 ID

        for idx, branch in enumerate(branches, 1):
            # 映射章节类型
            chapter_type_map = {
                "story": "section",
                "code": "section",
                "quiz": "section",
                "video": "video",
            }
            new_chapter_type = chapter_type_map.get(branch.chapter_type, "section")

            # 创建新章节
            new_chapter = CourseChapter(
                course_id=tech_content.id,
                slug=branch.slug,
                title=branch.title,
                order=branch.order,
                content=branch.content,
                chapter_type=new_chapter_type,
                duration_minutes=max(1, len(branch.content) // 500),  # 估算阅读时长
            )
            session.add(new_chapter)
            session.flush()
            branch_id_map[branch.id] = new_chapter.id
            print(f"  ✅ 章节 {idx}: {branch.title}")

        # 7. 迁移测验和题目
        print("正在迁移测验和题目...")
        quizzes = session.query(Quiz).all()
        for quiz in quizzes:
            if quiz.chapter_id not in branch_id_map:
                continue

            new_quiz = CourseQuiz(
                chapter_id=branch_id_map[quiz.chapter_id],
                title=quiz.title,
                passing_score=quiz.passing_score,
            )
            session.add(new_quiz)
            session.flush()

            # 迁移题目
            questions = session.query(Question).filter(Question.quiz_id == quiz.id).all()
            for q in questions:
                new_question = CourseQuizQuestion(
                    quiz_id=new_quiz.id,
                    question_text=q.question_text,
                    question_type=q.question_type,
                    correct_answer=q.correct_answer,
                    explanation=q.explanation,
                    order=q.order,
                )
                session.add(new_question)
                session.flush()

                # 迁移选项
                options = session.query(Option).filter(Option.question_id == q.id).all()
                for opt in options:
                    new_option = CourseQuizOption(
                        question_id=new_question.id,
                        option_text=opt.option_text,
                        option_index=opt.option_index,
                    )
                    session.add(new_option)

            print(f"  ✅ 测验：{quiz.title} ({len(questions)} 题目)")

        # 8. 迁移资源
        print("正在迁移资源...")
        resources = session.query(Resource).all()
        for resource in resources:
            if resource.chapter_id not in branch_id_map:
                continue

            new_resource = CourseResource(
                chapter_id=branch_id_map[resource.chapter_id],
                resource_type=resource.resource_type,
                title=resource.title,
                content=resource.content,
                extra_data=resource.extra_data,
            )
            session.add(new_resource)
            print(f"  ✅ 资源：{resource.title}")

        # 9. 提交事务
        session.commit()

        print()
        print("=" * 60)
        print("✅ 迁移完成！")
        print("=" * 60)
        print()
        print(f"迁移结果:")
        print(f"  - 技术分析内容：1 篇")
        print(f"  - 章节：{len(branches)} 个")
        print(f"  - 测验：{len(quizzes)} 个")
        print(f"  - 资源：{len(resources)} 个")
        print()
        print(f"内容标识符：openspec-vibecoding-practice")
        print(f"访问路径：/tech-contents/openspec-vibecoding-practice")
        print()

    except Exception as e:
        session.rollback()
        print(f"❌ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    migrate()
