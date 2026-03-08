#!/usr/bin/env python3
"""
OpenSpec 课程数据导出脚本

将数据库中的课程数据导出为 Markdown 文档，方便人工编辑和版本管理。

## 功能特性

- 导出 OpenSpec VibeCoding 课程的所有章节、测验、题目、选项和资源
- 生成结构化的 Markdown 文档，使用 YAML Frontmatter 格式
- 支持自定义输出文件路径
- 导出报告详细统计

## 使用方法

### 基本用法
```bash
python3 scripts/course_export.py
```

### 指定输出文件
```bash
python3 scripts/course_export.py --output my-course.md
```

## 输出文件格式

导出的 Markdown 文件包含以下部分：

1. **文件头**：导出时间和说明
2. **章节**：每个章节包含 slug、order、title、chapter_type、is_locked 等元数据
3. **测验**：每个测验包含 passing_score 和题目列表
4. **题目**：每道题目包含 type、correct_answer、explanation 和选项
5. **资源**：每个资源包含 type 和内容

示例格式：
```markdown
# OpenSpec VibeCoding 课程数据

> 导出时间：2026-03-09 10:00:00

---

## 章节：intro-vibe-coding

```yaml
order: 1
title: 第一章：最初的我 - 谨慎使用 AI 😰
chapter_type: story
is_locked: false
```

## 内容

章节内容...

---

## 测验：VibeCoding 入门测验

```yaml
passing_score: 60
```

### 题目 1

```yaml
question_type: single
correct_answer: 2
explanation: 答案解析
```

**题目内容：** 题目文本...

- A) 选项 A
- B) 选项 B
- C) 选项 C
- D) 选项 D
```

## 依赖

- Python 3.10+
- SQLAlchemy
- 数据库连接配置（从 backend/app/config/config.py 读取）

## 注意事项

1. 确保数据库连接配置正确
2. 确保有读取数据库的权限
3. 导出文件默认保存在 course_data/openspec-vibecoding.md
4. 如果数据库中没有课程数据，脚本会提示并退出

## 常见问题

**Q: 提示数据库连接失败？**
A: 检查 backend/app/config/config.py 中的 DATABASE_URL 配置

**Q: 导出的内容为空？**
A: 数据库中可能没有课程数据，先运行 init_openspec_course.py 初始化数据

**Q: 如何自定义导出路径？**
A: 使用 --output 参数指定输出文件路径
"""

import sys
import os
import argparse
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
    parser = argparse.ArgumentParser(
        description="OpenSpec 课程数据导出工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 scripts/course_export.py                    # 导出到默认路径
  python3 scripts/course_export.py -o my-course.md    # 导出到指定文件

详细说明:
  本脚本将数据库中的课程数据导出为 Markdown 文档，支持：
  - 章节数据（slug, title, content, chapter_type 等）
  - 测验数据（题目、选项、答案、解析）
  - 资源数据（code_sample, template 等）

  导出的 Markdown 文件可以直接编辑，然后通过 course_import.py 重新导入数据库。
        """
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="输出文件路径（默认：course_data/openspec-vibecoding.md）"
    )
    args = parser.parse_args()

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

        # 确定输出路径
        if args.output:
            output_path = Path(args.output)
        else:
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
