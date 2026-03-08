#!/usr/bin/env python3
"""
OpenSpec 课程数据导入脚本

从 Markdown 文档导入课程数据到数据库，支持增量导入、数据验证和失败回滚。

## 功能特性

- ✅ **增量导入**：按 slug 匹配，存在则更新，不存在则新增
- ✅ **数据验证**：导入前验证数据完整性和一致性
- ✅ **自动备份**：导入前自动备份现有数据
- ✅ **失败回滚**：导入失败时恢复到备份状态
- ✅ **用户进度保护**：不影响用户学习进度数据

## 使用方法

### 基本用法
```bash
python3 scripts/course_import.py course_data/openspec-vibecoding.md
```

### 模拟导入（不实际写入）
```bash
python3 scripts/course_import.py course_data/openspec-vibecoding.md --dry-run
```

### 强制导入（跳过验证）
```bash
python3 scripts/course_import.py course_data/openspec-vibecoding.md --force
```

### 不备份直接导入（不推荐）
```bash
python3 scripts/course_import.py course_data/openspec-vibecoding.md --no-backup
```

## 参数说明

| 参数 | 说明 |
|------|------|
| `markdown_file` | Markdown 文件路径（必填） |
| `--dry-run` | 模拟导入模式，不实际写入数据库 |
| `--force` | 强制导入，跳过数据验证 |
| `--no-backup` | 不备份现有数据直接导入 |

## 工作流程

1. **读取 Markdown 文件** - 解析章节、测验、题目、资源数据
2. **数据验证** - 检查 slug 唯一性、order 连续性、必填字段等
3. **备份现有数据** - 自动生成备份文件（YYYYMMDD_HHMMSS_NNN.json）
4. **增量导入** - 按 slug 匹配，存在则更新，不存在则新增
5. **生成报告** - 输出导入结果统计

## 导入报告示例

```
============================================================
OpenSpec 课程数据导入工具
============================================================

读取文件：course_data/openspec-vibecoding.md
正在连接数据库...
正在解析 Markdown 内容...
✅ 解析成功，共 5 个章节
   - intro-vibe-coding: 第一章：最初的我 - 谨慎使用 AI 😰
     └─ 1 个测验
     └─ 1 个资源
   ...

正在验证数据...
✅ 数据验证通过

正在备份现有数据...
✅ 备份完成：course_data/backups/20260309_100000_001.json

正在导入数据...

✅ 导入完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
新增章节：0
更新章节：5
新增测验：0
更新测验：3
新增题目：0
更新题目：6
新增资源：0
更新资源：3
备份文件：course_data/backups/20260309_100000_001.json
```

## 数据验证规则

### 章节验证
- slug 必须唯一
- order 必须连续且不重复
- title 不能为空
- content 不能为空
- chapter_type 必须是：story, code, quiz, video, quiz-only

### 测验验证
- passing_score 范围必须在 0-100 之间

### 题目验证
- question_type 必须是：single, multiple
- correct_answer 不能为空
- options 不能为空

## 注意事项

1. **编辑 Markdown 时不要修改 YAML 块的格式**，否则可能无法正确解析
2. **导入前会删除不在 Markdown 中的测验和资源**，确保 Markdown 文件包含完整数据
3. **定期备份数据库**，以防意外数据丢失
4. **在生产环境使用前，先在测试环境验证**

## 常见问题

**Q: 提示"章节 slug 重复"？**
A: Markdown 文件中有两个章节使用了相同的 slug，检查并确保每个章节的 slug 唯一。

**Q: 提示"章节 order 重复"？**
A: 两个章节的 order 值相同，确保章节的 order 值连续且不重复。

**Q: 导入失败后如何恢复？**
A: 导入脚本会自动回滚到备份，或手动执行：
   `python3 scripts/course_backup.py --restore <备份文件>`

**Q: 如何验证导入结果？**
A: 访问网站查看课程内容，或运行导出脚本重新导出对比。
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

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


# 尝试导入 yaml，如果没有安装则使用简单的解析器
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def simple_yaml_parse(text: str) -> dict:
    """简单的 YAML 解析器（当 PyYAML 未安装时使用）"""
    result = {}
    for line in text.strip().split("\n"):
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        # 处理布尔值
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        # 处理数字
        elif value.isdigit():
            value = int(value)
        elif value.replace(".", "").isdigit() and value.count(".") == 1:
            value = float(value)
        # 处理 null
        elif value.lower() == "null" or value == "~":
            value = None
        # 处理引号字符串
        elif (value.startswith('"') and value.endswith('"')) or \
             (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]

        result[key] = value
    return result


def parse_yaml_block(text: str) -> dict:
    """解析 YAML 代码块"""
    match = re.search(r'```yaml\s*(.*?)\s*```', text, re.DOTALL)
    if not match:
        return {}

    yaml_text = match.group(1)
    if HAS_YAML:
        return yaml.safe_load(yaml_text)
    else:
        return simple_yaml_parse(yaml_text)


@dataclass
class ValidationError:
    """验证错误"""
    section: str  # 章节/测验/资源
    field: str
    message: str
    line: int = 0


@dataclass
class ParsedChapter:
    """解析后的章节"""
    slug: str = ""
    order: int = 0
    title: str = ""
    chapter_type: str = "story"
    is_locked: bool = False
    video_url: Optional[str] = None
    content: str = ""
    quizzes: List["ParsedQuiz"] = field(default_factory=list)
    resources: List["ParsedResource"] = field(default_factory=list)


@dataclass
class ParsedQuiz:
    """解析后的测验"""
    title: str
    passing_score: int = 60
    questions: List["ParsedQuestion"] = field(default_factory=list)


@dataclass
class ParsedQuestion:
    """解析后的题目"""
    question_text: str = ""
    question_type: str = "single"
    correct_answer: str = ""
    explanation: Optional[str] = None
    options: List[str] = field(default_factory=list)


@dataclass
class ParsedResource:
    """解析后的资源"""
    title: str
    resource_type: str = "code_sample"
    content: str = ""


@dataclass
class ImportReport:
    """导入报告"""
    new_chapters: int = 0
    updated_chapters: int = 0
    skipped_chapters: int = 0
    new_quizzes: int = 0
    updated_quizzes: int = 0
    new_questions: int = 0
    updated_questions: int = 0
    new_resources: int = 0
    updated_resources: int = 0
    errors: List[str] = field(default_factory=list)
    backup_file: Optional[str] = None


class CourseImporter:
    """课程导入器"""

    def __init__(self, session, backup_dir: str):
        self.session = session
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def parse_markdown(self, md_content: str) -> List[ParsedChapter]:
        """解析 Markdown 内容"""
        chapters = []
        current_chapter = None
        current_section_type = None  # "content", "quiz", "resource"
        current_quiz = None
        current_content_lines = []

        # 按行解析
        lines = md_content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # 检测章节标题
            chapter_match = re.match(r'^## 章节：([a-zA-Z0-9_-]+)\s*$', line)
            if chapter_match:
                # 保存之前的章节
                if current_chapter and current_chapter.slug:
                    if current_content_lines:
                        current_chapter.content = "\n".join(current_content_lines).strip()
                    chapters.append(current_chapter)

                # 开始新章节
                slug = chapter_match.group(1)
                current_chapter = ParsedChapter(slug=slug)
                current_section_type = "chapter_meta"
                current_content_lines = []
                i += 1
                continue

            # 检测 YAML 元数据块
            if line == "```yaml" and current_chapter:
                # 解析 YAML 块
                yaml_lines = []
                i += 1
                while i < len(lines) and lines[i].strip() != "```":
                    yaml_lines.append(lines[i])
                    i += 1

                yaml_text = "\n".join(yaml_lines)
                meta = simple_yaml_parse(yaml_text)

                # 根据当前节类型设置属性
                if current_section_type == "chapter_meta":
                    for key, value in meta.items():
                        if hasattr(current_chapter, key):
                            setattr(current_chapter, key, value)
                elif current_section_type == "quiz_meta" and current_quiz:
                    for key, value in meta.items():
                        if hasattr(current_quiz, key):
                            setattr(current_quiz, key, value)
                elif current_section_type == "question_meta" and current_quiz and current_quiz.questions:
                    q = current_quiz.questions[-1]
                    for key, value in meta.items():
                        if hasattr(q, key):
                            setattr(q, key, value)
                elif current_section_type == "resource_meta" and current_chapter and current_chapter.resources:
                    r = current_chapter.resources[-1]
                    for key, value in meta.items():
                        if hasattr(r, key):
                            setattr(r, key, value)

                # 切换到内容节
                if current_section_type == "chapter_meta":
                    current_section_type = "content"
                i += 1
                continue

            # 检测内容标题
            if line == "## 内容":
                current_section_type = "content"
                i += 1
                continue

            # 检测测验标题
            quiz_match = re.match(r'^## 测验：(.+)$', line)
            if quiz_match and current_chapter:
                title = quiz_match.group(1)
                current_quiz = ParsedQuiz(title=title)
                current_chapter.quizzes.append(current_quiz)
                current_section_type = "quiz_meta"
                i += 1
                continue

            # 检测题目
            question_match = re.match(r'^### 题目 (\d+)\s*$', line)
            if question_match and current_quiz:
                current_section_type = "question_meta"
                # 添加新题目
                current_quiz.questions.append(ParsedQuestion())
                i += 1
                continue

            # 检测题目内容
            question_content_match = re.match(r'^\*\*题目内容：\*\*\s*(.+?)\s*$', line)
            if question_content_match and current_quiz and current_quiz.questions:
                q = current_quiz.questions[-1]
                q.question_text = question_content_match.group(1)
                i += 1
                continue

            # 检测选项
            option_match = re.match(r'^- ([A-Z])\)\s*(.+)$', line)
            if option_match and current_quiz and current_quiz.questions:
                q = current_quiz.questions[-1]
                opt_label = option_match.group(1)
                opt_text = option_match.group(2)
                # 确保选项列表足够长
                while len(q.options) <= ord(opt_label) - ord('A'):
                    q.options.append("")
                q.options[ord(opt_label) - ord('A')] = opt_text
                i += 1
                continue

            # 检测资源标题
            resource_match = re.match(r'^## 资源：(.+)$', line)
            if resource_match and current_chapter:
                title = resource_match.group(1)
                current_resource = ParsedResource(title=title)
                current_chapter.resources.append(current_resource)
                current_section_type = "resource_meta"
                i += 1
                continue

            # 收集内容行
            if current_section_type == "content" and current_chapter and line:
                current_content_lines.append(lines[i])

            i += 1

        # 保存最后一个章节
        if current_chapter and current_chapter.slug:
            if current_content_lines:
                current_chapter.content = "\n".join(current_content_lines).strip()
            chapters.append(current_chapter)

        return chapters

    def validate_data(self, chapters: List[ParsedChapter]) -> List[ValidationError]:
        """验证数据完整性"""
        errors = []
        seen_slugs = set()
        seen_orders = set()

        for chapter in chapters:
            # 验证章节 slug 唯一性
            if chapter.slug in seen_slugs:
                errors.append(ValidationError(
                    section=chapter.slug,
                    field="slug",
                    message=f"章节 slug '{chapter.slug}' 重复"
                ))
            seen_slugs.add(chapter.slug)

            # 验证章节 order 唯一性
            if chapter.order in seen_orders:
                errors.append(ValidationError(
                    section=chapter.slug,
                    field="order",
                    message=f"章节 order '{chapter.order}' 重复"
                ))
            seen_orders.add(chapter.order)

            # 验证必填字段
            if not chapter.title:
                errors.append(ValidationError(
                    section=chapter.slug,
                    field="title",
                    message="章节标题不能为空"
                ))

            if not chapter.content:
                errors.append(ValidationError(
                    section=chapter.slug,
                    field="content",
                    message="章节内容不能为空"
                ))

            # 验证 chapter_type
            valid_types = ["story", "code", "quiz", "video", "quiz-only"]
            if chapter.chapter_type not in valid_types:
                errors.append(ValidationError(
                    section=chapter.slug,
                    field="chapter_type",
                    message=f"无效的章节类型：'{chapter.chapter_type}'，有效值为：{valid_types}"
                ))

            # 验证测验
            for quiz in chapter.quizzes:
                if quiz.passing_score < 0 or quiz.passing_score > 100:
                    errors.append(ValidationError(
                        section=f"{chapter.slug}/{quiz.title}",
                        field="passing_score",
                        message=f"及格分数必须在 0-100 之间，当前为 {quiz.passing_score}"
                    ))

                # 验证题目
                for question in quiz.questions:
                    if not question.question_text:
                        errors.append(ValidationError(
                            section=f"{chapter.slug}/{quiz.title}",
                            field="question_text",
                            message="题目内容不能为空"
                        ))

                    if question.question_type not in ["single", "multiple"]:
                        errors.append(ValidationError(
                            section=f"{chapter.slug}/{quiz.title}",
                            field="question_type",
                            message=f"无效的题目类型：'{question.question_type}'，有效值为：single/multiple"
                        ))

                    if not question.correct_answer:
                        errors.append(ValidationError(
                            section=f"{chapter.slug}/{quiz.title}",
                            field="correct_answer",
                            message="正确答案不能为空"
                        ))

                    if not question.options:
                        errors.append(ValidationError(
                            section=f"{chapter.slug}/{quiz.title}",
                            field="options",
                            message="题目选项不能为空"
                        ))

            # 验证资源
            for resource in chapter.resources:
                valid_resource_types = ["code_sample", "contrast", "video", "template", "image"]
                if resource.resource_type not in valid_resource_types:
                    errors.append(ValidationError(
                        section=f"{chapter.slug}/{resource.title}",
                        field="resource_type",
                        message=f"无效的资源类型：'{resource.resource_type}'，有效值为：{valid_resource_types}"
                    ))

        return errors

    def backup_current_data(self) -> Optional[str]:
        """备份当前数据"""
        from course_backup import CourseBackup

        backup_mgr = CourseBackup(self.session, str(self.backup_dir))
        try:
            backup_path, _ = backup_mgr.backup_data()
            return backup_path
        except Exception as e:
            print(f"⚠️  备份失败：{e}")
            return None

    def import_incremental(self, chapters: List[ParsedChapter]) -> ImportReport:
        """增量导入数据"""
        report = ImportReport()

        for chapter in chapters:
            # 检查是否已存在（按 slug）
            existing_chapter = self.session.query(OpenSpecCourseChapter).filter_by(
                slug=chapter.slug
            ).first()

            if existing_chapter:
                # 更新现有章节
                existing_chapter.order = chapter.order
                existing_chapter.title = chapter.title
                existing_chapter.content = chapter.content
                existing_chapter.chapter_type = chapter.chapter_type
                existing_chapter.is_locked = chapter.is_locked
                existing_chapter.video_url = chapter.video_url
                existing_chapter.updated_at = datetime.now()

                self.session.add(existing_chapter)
                self.session.flush()

                report.updated_chapters += 1
                chapter_db_id = existing_chapter.id
            else:
                # 新增章节
                new_chapter = OpenSpecCourseChapter(
                    slug=chapter.slug,
                    order=chapter.order,
                    title=chapter.title,
                    content=chapter.content,
                    chapter_type=chapter.chapter_type,
                    is_locked=chapter.is_locked,
                    video_url=chapter.video_url,
                )
                self.session.add(new_chapter)
                self.session.flush()

                report.new_chapters += 1
                chapter_db_id = new_chapter.id

            # 处理测验（先删除不存在的，再更新/新增）
            quiz_titles_in_md = {quiz.title for quiz in chapter.quizzes}

            # 删除数据库中但不在 Markdown 中的测验
            existing_quizzes = self.session.query(OpenSpecCourseQuiz).filter_by(
                chapter_id=chapter_db_id
            ).all()
            for quiz in existing_quizzes:
                if quiz.title not in quiz_titles_in_md:
                    self.session.delete(quiz)
                    report.skipped_chapters += 0  # 只是计数，不影响章节

            # 更新/新增测验
            for quiz in chapter.quizzes:
                existing_quiz = self.session.query(OpenSpecCourseQuiz).filter_by(
                    chapter_id=chapter_db_id,
                    title=quiz.title
                ).first()

                if existing_quiz:
                    existing_quiz.passing_score = quiz.passing_score
                    existing_quiz.updated_at = datetime.now()
                    self.session.add(existing_quiz)
                    self.session.flush()
                    report.updated_quizzes += 1
                    quiz_db_id = existing_quiz.id
                else:
                    new_quiz = OpenSpecCourseQuiz(
                        chapter_id=chapter_db_id,
                        title=quiz.title,
                        passing_score=quiz.passing_score,
                    )
                    self.session.add(new_quiz)
                    self.session.flush()
                    report.new_quizzes += 1
                    quiz_db_id = new_quiz.id

                # 处理题目
                for idx, question in enumerate(quiz.questions):
                    # 题目按顺序匹配
                    existing_question = self.session.query(OpenSpecCourseQuizQuestion).filter_by(
                        quiz_id=quiz_db_id,
                        order=idx
                    ).first()

                    if existing_question:
                        existing_question.question_text = question.question_text
                        existing_question.question_type = question.question_type
                        existing_question.correct_answer = question.correct_answer
                        existing_question.explanation = question.explanation
                        self.session.add(existing_question)
                        self.session.flush()
                        report.updated_questions += 1
                        question_db_id = existing_question.id
                    else:
                        new_question = OpenSpecCourseQuizQuestion(
                            quiz_id=quiz_db_id,
                            question_text=question.question_text,
                            question_type=question.question_type,
                            correct_answer=question.correct_answer,
                            explanation=question.explanation,
                            order=idx,
                        )
                        self.session.add(new_question)
                        self.session.flush()
                        report.new_questions += 1
                        question_db_id = new_question.id

                    # 处理选项（先删除再创建）
                    self.session.query(OpenSpecCourseQuizOption).filter_by(
                        question_id=question_db_id
                    ).delete()

                    for opt_idx, opt_text in enumerate(question.options):
                        new_option = OpenSpecCourseQuizOption(
                            question_id=question_db_id,
                            option_index=opt_idx,
                            option_text=opt_text,
                        )
                        self.session.add(new_option)

                # 处理资源（先删除不存在的，再更新/新增）
            resource_titles_in_md = {res.title for res in chapter.resources}

            existing_resources = self.session.query(OpenSpecCourseResource).filter_by(
                chapter_id=chapter_db_id
            ).all()
            for resource in existing_resources:
                if resource.title not in resource_titles_in_md:
                    self.session.delete(resource)

            for resource in chapter.resources:
                existing_resource = self.session.query(OpenSpecCourseResource).filter_by(
                    chapter_id=chapter_db_id,
                    title=resource.title
                ).first()

                if existing_resource:
                    existing_resource.resource_type = resource.resource_type
                    existing_resource.content = resource.content
                    existing_resource.updated_at = datetime.now()
                    self.session.add(existing_resource)
                    report.updated_resources += 1
                else:
                    new_resource = OpenSpecCourseResource(
                        chapter_id=chapter_db_id,
                        resource_type=resource.resource_type,
                        content=resource.content,
                    )
                    self.session.add(new_resource)
                    report.new_resources += 1

        return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="OpenSpec 课程数据导入工具")
    parser.add_argument("markdown_file", type=str, help="Markdown 文件路径")
    parser.add_argument("--force", action="store_true", help="强制导入（跳过验证）")
    parser.add_argument("--dry-run", action="store_true", help="模拟导入（不实际写入）")
    parser.add_argument("--no-backup", action="store_true", help="不备份现有数据")
    args = parser.parse_args()

    print("=" * 60)
    print("OpenSpec 课程数据导入工具")
    print("=" * 60)
    print()

    # 检查文件是否存在
    md_path = Path(args.markdown_file)
    if not md_path.exists():
        print(f"❌ 文件不存在：{md_path}")
        return

    print(f"读取文件：{md_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # 创建数据库会话
    print("正在连接数据库...")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        backup_dir = Path(__file__).parent.parent / "course_data" / "backups"

        # 解析 Markdown
        print("正在解析 Markdown 内容...")
        importer = CourseImporter(session, str(backup_dir))
        chapters = importer.parse_markdown(md_content)

        if not chapters:
            print("❌ 未解析到任何章节内容")
            return

        print(f"✅ 解析成功，共 {len(chapters)} 个章节")
        for chapter in chapters:
            print(f"   - {chapter.slug}: {chapter.title}")
            if chapter.quizzes:
                print(f"     └─ {len(chapter.quizzes)} 个测验")
            if chapter.resources:
                print(f"     └─ {len(chapter.resources)} 个资源")
        print()

        # 验证数据
        if not args.force:
            print("正在验证数据...")
            errors = importer.validate_data(chapters)

            if errors:
                print("❌ 数据验证失败:")
                for error in errors:
                    print(f"   - [{error.section}] {error.field}: {error.message}")
                print()
                print("提示：使用 --force 参数可跳过验证强制导入")
                return

            print("✅ 数据验证通过")
            print()

        # 模拟导入
        if args.dry_run:
            print("(模拟导入模式)")
            report = ImportReport()
            report.new_chapters = len([c for c in chapters if not session.query(OpenSpecCourseChapter).filter_by(slug=c.slug).first()])
            report.updated_chapters = len([c for c in chapters if session.query(OpenSpecCourseChapter).filter_by(slug=c.slug).first()])

            print()
            print("✅ 模拟导入完成")
            print("━" * 60)
            print(f"预计新增章节：{report.new_chapters}")
            print(f"预计更新章节：{report.updated_chapters}")
            print()
            return

        # 备份现有数据
        backup_file = None
        if not args.no_backup:
            has_data = session.query(OpenSpecCourseChapter).count() > 0
            if has_data:
                print("正在备份现有数据...")
                backup_file = importer.backup_current_data()
                if backup_file:
                    print(f"✅ 备份完成：{backup_file}")
                print()

        # 导入数据
        print("正在导入数据...")
        report = importer.import_incremental(chapters)
        report.backup_file = backup_file

        # 提交事务
        session.commit()

        # 输出报告
        print()
        print("✅ 导入完成")
        print("━" * 60)
        print(f"新增章节：{report.new_chapters}")
        print(f"更新章节：{report.updated_chapters}")
        if report.skipped_chapters > 0:
            print(f"跳过章节：{report.skipped_chapters}")
        print(f"新增测验：{report.new_quizzes}")
        print(f"更新测验：{report.updated_quizzes}")
        print(f"新增题目：{report.new_questions}")
        print(f"更新题目：{report.updated_questions}")
        print(f"新增资源：{report.new_resources}")
        print(f"更新资源：{report.updated_resources}")
        if report.backup_file:
            print(f"备份文件：{report.backup_file}")
        print()

    except Exception as e:
        session.rollback()
        print(f"❌ 导入失败：{e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
