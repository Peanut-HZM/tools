#!/usr/bin/env python3
"""
OpenSpec 课程数据导出脚本

将数据库中的课程数据导出为 Markdown 文档，方便人工编辑和版本管理。

用法:
    python scripts/course_export.py

输出:
    - course_data/openspec-vibecoding.md
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base, engine
from app.models.openspec_course import (
    OpenSpecCourseChapter,
    OpenSpecCourseQuiz,
    OpenSpecCourseQuizQuestion,
    OpenSpecCourseQuizOption,
    OpenSpecCourseResource,
)
from app.config.config import settings


def yaml_block(data: dict, indent: int = 0) -> str:
    """生成 YAML 格式的代码块"""
    prefix = " " * indent
    lines = []
    for key, value in data.items():
        if isinstance(value, bool):
            lines.append(f"{prefix}{key}: {str(value).lower()}")
        elif isinstance(value, (int, float)) or value is None:
            lines.append(f"{prefix}{key}: {value}")
        else:
            # 字符串需要引号的情况
            str_val = str(value)
            if any(c in str_val for c in [":", "#", "{", "}", "[", "]", "&", "*", "!", "|", ">", "'", "\"", "%", "@", "`"]):
                lines.append(f"{prefix}{key}: \"{str_val.replace(chr(92), chr(92)*2).replace('\"', chr(92)+'\"')}\"")
            else:
                lines.append(f"{prefix}{key}: {str_val}")
    return "\n".join(lines)


class CourseExporter:
    """课程导出器"""

    def __init__(self, session):
        self.session = session

    def fetch_all_data(self) -> dict:
        """获取所有课程数据"""
        # 按 order 排序获取所有章节
        chapters = self.session.query(OpenSpecCourseChapter).order_by(OpenSpecCourseChapter.order).all()

        data = {
            "chapters": chapters,
            "quizzes": {},
            "questions": {},
            "options": {},
            "resources": {},
        }

        # 获取所有章节的测验
        for chapter in chapters:
            data["options"][chapter.id] = {}  # 初始化 options

            quizzes = self.session.query(OpenSpecCourseQuiz).filter(
                OpenSpecCourseQuiz.chapter_id == chapter.id
            ).all()
            data["quizzes"][chapter.id] = quizzes

            # 获取每个测验的题目
            data["questions"][chapter.id] = {}
            for quiz in quizzes:
                questions = self.session.query(OpenSpecCourseQuizQuestion).filter(
                    OpenSpecCourseQuizQuestion.quiz_id == quiz.id
                ).order_by(OpenSpecCourseQuizQuestion.order).all()
                data["questions"][chapter.id][quiz.id] = questions

                # 获取每个题目的选项
                data["options"][chapter.id][quiz.id] = {}
                for question in questions:
                    options = self.session.query(OpenSpecCourseQuizOption).filter(
                        OpenSpecCourseQuizOption.question_id == question.id
                    ).order_by(OpenSpecCourseQuizOption.option_index).all()
                    data["options"][chapter.id][quiz.id][question.id] = options

        # 获取所有章节的资源
        for chapter in chapters:
            resources = self.session.query(OpenSpecCourseResource).filter(
                OpenSpecCourseResource.chapter_id == chapter.id
            ).all()
            data["resources"][chapter.id] = resources

        return data

    def format_chapter(self, chapter) -> str:
        """格式化章节为 Markdown"""
        lines = []

        # 章节标题
        lines.append(f"## 章节：{chapter.slug}\n")

        # 章节元数据
        meta = {
            "order": chapter.order,
            "title": chapter.title,
            "chapter_type": chapter.chapter_type,
            "is_locked": chapter.is_locked,
        }
        if chapter.video_url:
            meta["video_url"] = chapter.video_url

        lines.append("```yaml")
        lines.append(yaml_block(meta))
        lines.append("```\n")

        # 章节内容
        lines.append("## 内容\n")
        lines.append(chapter.content)
        lines.append("")

        return "\n".join(lines)

    def format_quiz(self, quiz, questions: list, options_map: dict) -> str:
        """格式化测验为 Markdown"""
        lines = []

        # 测验标题
        lines.append(f"## 测验：{quiz.title}\n")

        # 测验元数据
        meta = {
            "passing_score": quiz.passing_score,
        }
        lines.append("```yaml")
        lines.append(yaml_block(meta))
        lines.append("```\n")

        # 题目列表
        for idx, question in enumerate(questions, 1):
            lines.append(f"### 题目 {idx}\n")

            # 题目元数据
            q_meta = {
                "question_type": question.question_type,
                "correct_answer": question.correct_answer,
            }
            if question.explanation:
                q_meta["explanation"] = question.explanation

            lines.append("```yaml")
            lines.append(yaml_block(q_meta))
            lines.append("```\n")

            # 题目内容
            lines.append(f"**题目内容：** {question.question_text}\n")

            # 选项列表
            if question.id in options_map:
                for option in options_map[question.id]:
                    option_label = chr(ord('A') + option.option_index)
                    lines.append(f"- {option_label}) {option.option_text}")

            lines.append("")

        return "\n".join(lines)

    def format_resource(self, resource) -> str:
        """格式化资源为 Markdown"""
        lines = []

        # 资源标题
        lines.append(f"## 资源：{resource.title}\n")

        # 资源元数据
        meta = {
            "resource_type": resource.resource_type,
        }

        lines.append("```yaml")
        lines.append(yaml_block(meta))
        lines.append("```\n")

        # 资源内容
        lines.append(resource.content)
        lines.append("")

        return "\n".join(lines)

    def export_to_md(self, output_path: str) -> dict:
        """导出到 Markdown 文件"""
        # 获取所有数据
        data = self.fetch_all_data()

        # 统计
        stats = {
            "chapters_count": len(data["chapters"]),
            "quizzes_count": 0,
            "questions_count": 0,
            "options_count": 0,
            "resources_count": 0,
        }

        # 生成 Markdown 内容
        md_lines = []

        # 文件头
        md_lines.append("# OpenSpec VibeCoding 课程数据")
        md_lines.append("")
        md_lines.append(f"> 导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # 导出章节
        for chapter in data["chapters"]:
            md_lines.append(self.format_chapter(chapter))

            # 导出章节的测验
            if chapter.id in data["quizzes"] and data["quizzes"][chapter.id]:
                for quiz in data["quizzes"][chapter.id]:
                    stats["quizzes_count"] += 1
                    questions = data["questions"][chapter.id].get(quiz.id, [])
                    stats["questions_count"] += len(questions)

                    options_for_quiz = {}
                    for q in questions:
                        opts = data["options"][chapter.id].get(quiz.id, {}).get(q.id, [])
                        options_for_quiz[q.id] = opts
                        stats["options_count"] += len(opts)

                    md_lines.append(self.format_quiz(quiz, questions, options_for_quiz))
                    md_lines.append("---")
                    md_lines.append("")

            # 导出章节的资源
            if chapter.id in data["resources"] and data["resources"][chapter.id]:
                for resource in data["resources"][chapter.id]:
                    stats["resources_count"] += 1
                    md_lines.append(self.format_resource(resource))

            md_lines.append("---")
            md_lines.append("")

        # 写入文件
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        stats["output_file"] = str(output_file)

        return stats


def main():
    """主函数"""
    print("=" * 60)
    print("OpenSpec 课程数据导出工具")
    print("=" * 60)
    print()

    # 创建数据库会话
    print("正在连接数据库...")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 检查是否有数据
        chapters_count = session.query(OpenSpecCourseChapter).count()
        if chapters_count == 0:
            print("⚠️  数据库中没有课程数据，无法导出")
            return

        print(f"✅ 数据库连接成功，共有 {chapters_count} 个章节")
        print()

        # 创建导出器
        exporter = CourseExporter(session)

        # 导出到 Markdown
        output_path = Path(__file__).parent.parent / "course_data" / "openspec-vibecoding.md"
        print(f"正在导出课程数据到：{output_path}")

        stats = exporter.export_to_md(str(output_path))

        # 输出报告
        print()
        print("✅ 导出完成")
        print("━" * 60)
        print(f"章节数：{stats['chapters_count']}")
        print(f"测验数：{stats['quizzes_count']}")
        print(f"题目数：{stats['questions_count']}")
        print(f"选项数：{stats['options_count']}")
        print(f"资源数：{stats['resources_count']}")
        print(f"输出文件：{stats['output_file']}")
        print()

    except Exception as e:
        print(f"❌ 导出失败：{e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
