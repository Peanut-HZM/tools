"""
OpenSpec 课程导出/导入服务

提供课程数据的 JSON 导出、导入，以及 Markdown 导出/导入功能。
"""
import json
import logging
import re
import zipfile
import io
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.openspec_course import (
    OpenSpecCourseChapter,
    OpenSpecCourseQuiz,
    OpenSpecCourseQuizQuestion,
    OpenSpecCourseQuizOption,
    OpenSpecCourseResource,
)
from app.schemas.openspec_course import (
    CourseExportData,
    ExportedChapter,
    ExportedQuiz,
    ExportedQuizQuestion,
    ExportedQuizOption,
    ExportedResource,
    ImportStrategy,
    ImportPreviewResponse,
    ImportConflictInfo,
    ImportResponse,
    MarkdownImportPreview,
)

logger = logging.getLogger(__name__)


class CourseExportService:
    """课程导出服务"""

    def __init__(self, db: Session):
        self.db = db

    def export_to_json(self, course_id: Optional[int] = None, course_title: Optional[str] = None) -> CourseExportData:
        """
        导出课程数据为 JSON 格式

        Args:
            course_id: 课程 ID（可选，用于元数据）
            course_title: 课程标题（可选，用于元数据）

        Returns:
            CourseExportData: 导出数据对象
        """
        logger.info(f"开始导出课程数据，course_id={course_id}")

        # 获取所有章节（按顺序）
        chapters = self.db.query(OpenSpecCourseChapter).order_by(OpenSpecCourseChapter.order).all()

        exported_chapters = []
        total_quizzes = 0
        total_questions = 0
        total_options = 0
        total_resources = 0

        for chapter in chapters:
            # 导出章节
            exported_chapter = self._export_chapter(chapter)
            exported_chapters.append(exported_chapter)

            # 统计
            if chapter.required_quiz_id:
                quiz = self.db.query(OpenSpecCourseQuiz).filter(
                    OpenSpecCourseQuiz.id == chapter.required_quiz_id
                ).first()
                if quiz:
                    total_quizzes += 1
                    questions = self.db.query(OpenSpecCourseQuizQuestion).filter(
                        OpenSpecCourseQuizQuestion.quiz_id == quiz.id
                    ).all()
                    total_questions += len(questions)
                    for q in questions:
                        options = self.db.query(OpenSpecCourseQuizOption).filter(
                            OpenSpecCourseQuizOption.question_id == q.id
                        ).all()
                        total_options += len(options)

            # 统计章节资源
            resources = self.db.query(OpenSpecCourseResource).filter(
                OpenSpecCourseResource.chapter_id == chapter.id
            ).all()
            total_resources += len(resources)

        export_data = CourseExportData(
            version="1.0",
            export_timestamp=datetime.now().isoformat(),
            course_id=course_id,
            course_title=course_title,
            chapters=exported_chapters,
            export_stats={
                "chapters_count": len(exported_chapters),
                "quizzes_count": total_quizzes,
                "questions_count": total_questions,
                "options_count": total_options,
                "resources_count": total_resources,
            }
        )

        logger.info(f"导出完成：{len(exported_chapters)} 个章节，{total_quizzes} 个测验，{total_questions} 个问题")
        return export_data

    def _export_chapter(self, chapter: OpenSpecCourseChapter) -> ExportedChapter:
        """导出单个章节"""
        # 获取关联的测验
        quiz = None
        required_quiz_slug = None
        quizzes = []

        if chapter.required_quiz_id:
            quiz = self.db.query(OpenSpecCourseQuiz).filter(
                OpenSpecCourseQuiz.id == chapter.required_quiz_id
            ).first()

        if quiz:
            # 为测验生成 slug（用于导入时匹配）
            quiz_slug = f"quiz-{quiz.chapter_id}-{quiz.id}"
            required_quiz_slug = quiz_slug

            exported_quiz = self._export_quiz(quiz, quiz_slug)
            quizzes.append(exported_quiz)

        # 获取资源
        resources = self.db.query(OpenSpecCourseResource).filter(
            OpenSpecCourseResource.chapter_id == chapter.id
        ).all()
        exported_resources = [self._export_resource(r) for r in resources]

        return ExportedChapter(
            slug=chapter.slug,
            title=chapter.title,
            order=chapter.order,
            content=chapter.content,
            chapter_type=chapter.chapter_type,
            video_url=chapter.video_url,
            is_locked=chapter.is_locked,
            required_quiz_slug=required_quiz_slug,
            quizzes=quizzes,
            resources=exported_resources,
        )

    def _export_quiz(self, quiz: OpenSpecCourseQuiz, slug: Optional[str] = None) -> ExportedQuiz:
        """导出测验"""
        questions = self.db.query(OpenSpecCourseQuizQuestion).filter(
            OpenSpecCourseQuizQuestion.quiz_id == quiz.id
        ).order_by(OpenSpecCourseQuizQuestion.order).all()

        exported_questions = []
        for q in questions:
            options = self.db.query(OpenSpecCourseQuizOption).filter(
                OpenSpecCourseQuizOption.question_id == q.id
            ).all()
            exported_options = [
                ExportedQuizOption(
                    option_text=opt.option_text,
                    option_index=opt.option_index,
                )
                for opt in options
            ]
            exported_questions.append(ExportedQuizQuestion(
                question_text=q.question_text,
                question_type=q.question_type,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
                order=q.order,
                options=exported_options,
            ))

        return ExportedQuiz(
            slug=slug,
            title=quiz.title,
            passing_score=quiz.passing_score,
            questions=exported_questions,
        )

    def _export_resource(self, resource: OpenSpecCourseResource) -> ExportedResource:
        """导出资源"""
        extra_data = None
        if resource.extra_data:
            try:
                extra_data = json.loads(resource.extra_data) if isinstance(resource.extra_data, str) else resource.extra_data
            except Exception:
                logger.warning(f"解析资源 extra_data 失败：{resource.id}")

        return ExportedResource(
            resource_type=resource.resource_type,
            title=resource.title,
            content=resource.content,
            extra_data=extra_data,
        )

    def export_chapter_to_markdown(self, chapter_id: int) -> Tuple[str, str]:
        """
        导出单个章节为 Markdown 格式

        Args:
            chapter_id: 章节 ID

        Returns:
            Tuple[str, str]: (markdown 内容，文件名)
        """
        chapter = self.db.query(OpenSpecCourseChapter).filter(
            OpenSpecCourseChapter.id == chapter_id
        ).first()

        if not chapter:
            raise ValueError(f"章节不存在：{chapter_id}")

        # 构建 Frontmatter
        frontmatter = f"""---
slug: {chapter.slug}
title: {chapter.title}
order: {chapter.order}
chapter_type: {chapter.chapter_type}
is_locked: {str(chapter.is_locked).lower()}
"""
        if chapter.video_url:
            frontmatter += f"video_url: {chapter.video_url}\n"
        if chapter.required_quiz_id:
            # 获取测验 slug
            quiz = self.db.query(OpenSpecCourseQuiz).filter(
                OpenSpecCourseQuiz.id == chapter.required_quiz_id
            ).first()
            if quiz:
                frontmatter += f"required_quiz_slug: quiz-{quiz.chapter_id}-{quiz.id}\n"
        frontmatter += "---\n\n"

        # 构建正文
        markdown = frontmatter + chapter.content

        # 添加测验部分
        if chapter.required_quiz_id:
            quiz = self.db.query(OpenSpecCourseQuiz).filter(
                OpenSpecCourseQuiz.id == chapter.required_quiz_id
            ).first()
            if quiz:
                markdown += "\n\n---\n\n## 测验：" + quiz.title
                markdown += f"\n\n**及格分数**: {quiz.passing_score}\n"

                questions = self.db.query(OpenSpecCourseQuizQuestion).filter(
                    OpenSpecCourseQuizQuestion.quiz_id == quiz.id
                ).order_by(OpenSpecCourseQuizQuestion.order).all()

                for i, q in enumerate(questions, 1):
                    markdown += f"\n\n### 问题 {i}\n\n"
                    markdown += f"{q.question_text}\n"

                    options = self.db.query(OpenSpecCourseQuizOption).filter(
                        OpenSpecCourseQuizOption.question_id == q.id
                    ).all()
                    correct_answers = [int(x) for x in q.correct_answer.split(",")]

                    for opt in options:
                        checkbox = "[x]" if opt.option_index in correct_answers else "[ ]"
                        markdown += f"- {checkbox} {opt.option_text}\n"

                    if q.explanation:
                        markdown += f"\n**答案**: {q.correct_answer}\n"
                        markdown += f"**解析**: {q.explanation}\n"

        # 添加资源部分
        resources = self.db.query(OpenSpecCourseResource).filter(
            OpenSpecCourseResource.chapter_id == chapter.id
        ).all()

        if resources:
            markdown += "\n\n---\n\n## 资源\n"
            for r in resources:
                markdown += f"\n\n### {r.title}\n\n"
                markdown += f"**类型**: {r.resource_type}\n\n"
                markdown += f"{r.content}\n"

                if r.extra_data:
                    try:
                        extra_data = json.loads(r.extra_data) if isinstance(r.extra_data, str) else r.extra_data
                        markdown += f"\n**元数据**:\n```json\n{json.dumps(extra_data, ensure_ascii=False, indent=2)}\n```\n"
                    except Exception:
                        pass

        filename = f"{chapter.slug}.md"
        return markdown, filename

    def export_to_zip(self, course_id: Optional[int] = None, course_title: Optional[str] = None) -> Tuple[bytes, str]:
        """
        导出课程数据为 ZIP 格式（包含 JSON + 所有章节 Markdown 文件）

        Args:
            course_id: 课程 ID（可选，用于元数据）
            course_title: 课程标题（可选，用于元数据）

        Returns:
            Tuple[bytes, str]: (ZIP 文件字节，文件名)
        """
        logger.info(f"开始导出课程 ZIP 包，course_id={course_id}")

        # 创建 ZIP 文件到内存
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 1. 导出 JSON 数据
            export_data = self.export_to_json(course_id=course_id, course_title=course_title)
            json_filename = "course-export.json"
            json_content = json.dumps(export_data.model_dump(), ensure_ascii=False, indent=2)
            zip_file.writestr(json_filename, json_content)

            # 2. 导出所有章节为 Markdown 文件
            chapters = self.db.query(OpenSpecCourseChapter).order_by(OpenSpecCourseChapter.order).all()

            for chapter in chapters:
                # 复用 export_chapter_to_markdown 方法
                markdown_content, md_filename = self.export_chapter_to_markdown(chapter.id)

                # 将 Markdown 文件写入 zip 的 markdowns/ 目录
                zip_file.writestr(f"markdowns/{md_filename}", markdown_content)

            # 3. 添加 README 文件
            readme_content = self._generate_readme(export_data)
            zip_file.writestr("README.md", readme_content)

        # 获取 ZIP 文件字节
        zip_bytes = zip_buffer.getvalue()
        zip_buffer.close()

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_title = (course_title or "course").lower().replace(" ", "-").replace("/", "-")
        filename = f"{safe_title}-export-{timestamp}.zip"

        logger.info(f"ZIP 导出完成：{filename}, 包含 {len(chapters)} 个章节 Markdown 文件")
        return zip_bytes, filename

    def _generate_readme(self, export_data: CourseExportData) -> str:
        """
        生成 ZIP 包的 README 文件

        Args:
            export_data: 导出数据对象

        Returns:
            str: README Markdown 内容
        """
        readme = f"""# {export_data.course_title or 'Course'} - 导出包

**导出时间**: {export_data.export_timestamp}
**导出版本**: {export_data.version}

## 统计信息

- 章节数量：{export_data.export_stats['chapters_count']}
- 测验数量：{export_data.export_stats['quizzes_count']}
- 问题数量：{export_data.export_stats['questions_count']}
- 选项数量：{export_data.export_stats['options_count']}
- 资源数量：{export_data.export_stats['resources_count']}

## 文件结构

```
{export_data.course_title or 'course'}-export/
├── README.md                  # 本文件
├── course-export.json         # 完整课程数据（JSON 格式）
└── markdowns/                 # 章节 Markdown 文件目录
    ├── chapter-1.md           # 第 1 章
    ├── chapter-2.md           # 第 2 章
    └── ...
```

## 使用说明

### 导入 JSON 文件

1. 在管理后台点击"导入课程"
2. 选择 `course-export.json` 文件
3. 选择导入策略（合并/替换/跳过）
4. 确认导入

### 导入 Markdown 文件

Markdown 文件包含完整的章节内容、测验和资源数据，可直接用于版本控制或手动编辑。

每个 Markdown 文件包含：
- Frontmatter 元数据（slug, title, order, chapter_type 等）
- 章节正文内容
- 测验部分（如果有）
- 资源部分（如果有）

## 注意事项

- 导入前建议先备份现有数据
- Markdown 文件的 Frontmatter 必须保持有效的 YAML 格式
- 测验和资源部分由分隔符 `---` 标识，不要手动修改这些区域
"""
        return readme


class CourseImportService:
    """课程导入服务"""

    def __init__(self, db: Session):
        self.db = db

    def preview_import(self, export_data: CourseExportData, strategy: ImportStrategy) -> ImportPreviewResponse:
        """
        预览导入结果

        Args:
            export_data: 导出数据对象
            strategy: 导入策略

        Returns:
            ImportPreviewResponse: 预览响应
        """
        logger.info(f"预览导入，策略={strategy}, 章节数={len(export_data.chapters)}")

        conflicts = []
        chapters_to_import = 0
        chapters_to_update = 0
        chapters_to_skip = 0
        warnings = []

        for exported_chapter in export_data.chapters:
            # 检查是否已存在
            existing = self.db.query(OpenSpecCourseChapter).filter(
                OpenSpecCourseChapter.slug == exported_chapter.slug
            ).first()

            if existing:
                if strategy == ImportStrategy.SKIP_EXISTING:
                    chapters_to_skip += 1
                    conflicts.append(ImportConflictInfo(
                        chapter_slug=exported_chapter.slug,
                        chapter_title=exported_chapter.title,
                        conflict_type="exists",
                        exists_in_db=True,
                    ))
                elif strategy == ImportStrategy.MERGE:
                    # 合并策略：跳过已存在的
                    chapters_to_skip += 1
                    conflicts.append(ImportConflictInfo(
                        chapter_slug=exported_chapter.slug,
                        chapter_title=exported_chapter.title,
                        conflict_type="exists",
                        exists_in_db=True,
                    ))
                elif strategy == ImportStrategy.REPLACE:
                    # 替换策略：更新已存在的
                    chapters_to_update += 1
                    conflicts.append(ImportConflictInfo(
                        chapter_slug=exported_chapter.slug,
                        chapter_title=exported_chapter.title,
                        conflict_type="will_update",
                        exists_in_db=True,
                    ))
            else:
                chapters_to_import += 1
                conflicts.append(ImportConflictInfo(
                    chapter_slug=exported_chapter.slug,
                    chapter_title=exported_chapter.title,
                    conflict_type="new",
                    exists_in_db=False,
                ))

        return ImportPreviewResponse(
            success=True,
            preview=True,
            strategy=strategy.value,
            chapters_to_import=chapters_to_import,
            chapters_to_update=chapters_to_update,
            chapters_to_skip=chapters_to_skip,
            conflicts=conflicts,
            warnings=warnings,
        )

    def import_from_json(self, export_data: CourseExportData, strategy: ImportStrategy) -> ImportResponse:
        """
        从 JSON 导入课程数据

        Args:
            export_data: 导出数据对象
            strategy: 导入策略

        Returns:
            ImportResponse: 导入响应
        """
        logger.info(f"开始导入课程数据，策略={strategy}")

        warnings = []
        errors = []
        stats = {
            "chapters_imported": 0,
            "chapters_updated": 0,
            "chapters_skipped": 0,
            "quizzes_imported": 0,
            "questions_imported": 0,
            "options_imported": 0,
            "resources_imported": 0,
        }

        try:
            for exported_chapter in export_data.chapters:
                result = self._import_chapter(exported_chapter, strategy, warnings)
                stats["chapters_imported"] += result.get("imported", 0)
                stats["chapters_updated"] += result.get("updated", 0)
                stats["chapters_skipped"] += result.get("skipped", 0)
                stats["quizzes_imported"] += result.get("quizzes", 0)
                stats["questions_imported"] += result.get("questions", 0)
                stats["options_imported"] += result.get("options", 0)
                stats["resources_imported"] += result.get("resources", 0)

            logger.info(f"导入完成：{stats}")
            return ImportResponse(
                success=True,
                message=f"成功导入 {stats['chapters_imported']} 个章节，{stats['quizzes_imported']} 个测验",
                imported_stats=stats,
                warnings=warnings,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"导入失败：{e}", exc_info=True)
            errors.append(str(e))
            return ImportResponse(
                success=False,
                message="导入失败",
                imported_stats=stats,
                warnings=warnings,
                errors=errors,
            )

    def _import_chapter(
        self, exported_chapter: ExportedChapter, strategy: ImportStrategy, warnings: List[str]
    ) -> Dict[str, int]:
        """导入单个章节"""
        result = {"imported": 0, "updated": 0, "skipped": 0, "quizzes": 0, "questions": 0, "options": 0, "resources": 0}

        # 检查是否已存在
        existing = self.db.query(OpenSpecCourseChapter).filter(
            OpenSpecCourseChapter.slug == exported_chapter.slug
        ).first()

        if existing:
            if strategy == ImportStrategy.SKIP_EXISTING:
                result["skipped"] = 1
                return result
            elif strategy == ImportStrategy.MERGE:
                result["skipped"] = 1
                return result
            elif strategy == ImportStrategy.REPLACE:
                # 更新现有章节
                existing.title = exported_chapter.title
                existing.order = exported_chapter.order
                existing.content = exported_chapter.content
                existing.chapter_type = exported_chapter.chapter_type
                existing.video_url = exported_chapter.video_url
                existing.is_locked = exported_chapter.is_locked
                # 清除 required_quiz_id 引用
                existing.required_quiz_id = None
                self.db.flush()
                result["updated"] = 1
                chapter_id = existing.id

                # 删除旧的资源和测验（级联删除）
                self.db.query(OpenSpecCourseResource).filter(
                    OpenSpecCourseResource.chapter_id == chapter_id
                ).delete(synchronize_session=False)
                # 获取章节的测验 ID
                quizzes = self.db.query(OpenSpecCourseQuiz).filter(
                    OpenSpecCourseQuiz.chapter_id == chapter_id
                ).all()
                for quiz in quizzes:
                    # 删除问题和选项（通过级联或手动）
                    questions = self.db.query(OpenSpecCourseQuizQuestion).filter(
                        OpenSpecCourseQuizQuestion.quiz_id == quiz.id
                    ).all()
                    for question in questions:
                        self.db.query(OpenSpecCourseQuizOption).filter(
                            OpenSpecCourseQuizOption.question_id == question.id
                        ).delete(synchronize_session=False)
                    self.db.query(OpenSpecCourseQuizQuestion).filter(
                        OpenSpecCourseQuizQuestion.quiz_id == quiz.id
                    ).delete(synchronize_session=False)
                self.db.query(OpenSpecCourseQuiz).filter(
                    OpenSpecCourseQuiz.chapter_id == chapter_id
                ).delete(synchronize_session=False)
            else:
                result["skipped"] = 1
                return result
        else:
            # 创建新章节
            new_chapter = OpenSpecCourseChapter(
                slug=exported_chapter.slug,
                title=exported_chapter.title,
                order=exported_chapter.order,
                content=exported_chapter.content,
                chapter_type=exported_chapter.chapter_type,
                video_url=exported_chapter.video_url,
                is_locked=exported_chapter.is_locked,
            )
            self.db.add(new_chapter)
            self.db.flush()
            result["imported"] = 1
            chapter_id = new_chapter.id

        # 导入资源
        for exported_resource in exported_chapter.resources:
            resource = OpenSpecCourseResource(
                chapter_id=chapter_id,
                resource_type=exported_resource.resource_type,
                title=exported_resource.title,
                content=exported_resource.content,
                extra_data=json.dumps(exported_resource.extra_data, ensure_ascii=False) if exported_resource.extra_data else None,
            )
            self.db.add(resource)
            result["resources"] += 1

        # 导入测验
        for exported_quiz in exported_chapter.quizzes:
            quiz = OpenSpecCourseQuiz(
                chapter_id=chapter_id,
                title=exported_quiz.title,
                passing_score=exported_quiz.passing_score,
            )
            self.db.add(quiz)
            self.db.flush()
            result["quizzes"] += 1

            # 导入问题
            for exported_question in exported_quiz.questions:
                question = OpenSpecCourseQuizQuestion(
                    quiz_id=quiz.id,
                    question_text=exported_question.question_text,
                    question_type=exported_question.question_type,
                    correct_answer=exported_question.correct_answer,
                    explanation=exported_question.explanation,
                    order=exported_question.order,
                )
                self.db.add(question)
                self.db.flush()
                result["questions"] += 1

                # 导入选项
                for exported_option in exported_question.options:
                    option = OpenSpecCourseQuizOption(
                        question_id=question.id,
                        option_text=exported_option.option_text,
                        option_index=exported_option.option_index,
                    )
                    self.db.add(option)
                    result["options"] += 1

        self.db.commit()
        return result

    def parse_markdown_import(self, markdown_content: str, chapter_id: int) -> MarkdownImportPreview:
        """
        解析 Markdown 导入内容并生成预览

        Args:
            markdown_content: Markdown 内容
            chapter_id: 章节 ID

        Returns:
            MarkdownImportPreview: 预览对象
        """
        # 获取原章节
        chapter = self.db.query(OpenSpecCourseChapter).filter(
            OpenSpecCourseChapter.id == chapter_id
        ).first()

        if not chapter:
            raise ValueError(f"章节不存在：{chapter_id}")

        # 解析 Frontmatter
        frontmatter = {}
        content = markdown_content

        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', markdown_content, re.DOTALL)
        if frontmatter_match:
            frontmatter_text = frontmatter_match.group(1)
            content = markdown_content[frontmatter_match.end():]

            # 解析 YAML-like frontmatter
            for line in frontmatter_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    frontmatter[key] = value

        # 提取正文（移除测验和资源部分）
        body = self._extract_body_content(content)

        # 计算变更
        changes = []
        if frontmatter.get('title') and frontmatter['title'] != chapter.title:
            changes.append(f"title 将从 '{chapter.title}' 更新为 '{frontmatter['title']}'")
        if body != chapter.content:
            changes.append("content 内容已更新")
        if frontmatter.get('chapter_type') and frontmatter['chapter_type'] != chapter.chapter_type:
            changes.append(f"chapter_type 将从 '{chapter.chapter_type}' 更新为 '{frontmatter['chapter_type']}'")

        return MarkdownImportPreview(
            original_title=chapter.title,
            original_content=chapter.content,
            proposed_title=frontmatter.get('title', chapter.title),
            proposed_content=body,
            changes=changes if changes else ["无变更"],
        )

    def _extract_body_content(self, content: str) -> str:
        """提取正文内容，移除测验和资源部分"""
        # 移除测验部分
        quiz_match = re.search(r'\n---\n\n## 测验：', content)
        if quiz_match:
            content = content[:quiz_match.start()]

        # 移除资源部分
        resources_match = re.search(r'\n---\n\n## 资源\n', content)
        if resources_match:
            content = content[:resources_match.start()]

        return content.strip()

    def import_from_markdown(self, markdown_content: str, chapter_id: int, apply_changes: bool = True) -> Dict[str, Any]:
        """
        从 Markdown 导入章节更新

        Args:
            markdown_content: Markdown 内容
            chapter_id: 章节 ID
            apply_changes: 是否应用变更

        Returns:
            Dict: 导入结果
        """
        preview = self.parse_markdown_import(markdown_content, chapter_id)

        if not apply_changes:
            return {"preview": True, "data": preview}

        # 更新章节
        chapter = self.db.query(OpenSpecCourseChapter).filter(
            OpenSpecCourseChapter.id == chapter_id
        ).first()

        if not chapter:
            raise ValueError(f"章节不存在：{chapter_id}")

        # 解析 Frontmatter
        frontmatter = {}
        content = markdown_content

        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', markdown_content, re.DOTALL)
        if frontmatter_match:
            frontmatter_text = frontmatter_match.group(1)
            content = markdown_content[frontmatter_match.end():]

            for line in frontmatter_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    frontmatter[key] = value

        # 提取正文
        body = self._extract_body_content(content)

        # 应用更新
        if frontmatter.get('title'):
            chapter.title = frontmatter['title']
        if frontmatter.get('order'):
            chapter.order = frontmatter['order']
        if frontmatter.get('chapter_type'):
            chapter.chapter_type = frontmatter['chapter_type']
        if frontmatter.get('video_url'):
            chapter.video_url = frontmatter['video_url']
        if 'is_locked' in frontmatter:
            chapter.is_locked = frontmatter['is_locked']

        chapter.content = body

        self.db.commit()

        logger.info(f"从 Markdown 更新章节：{chapter_id}")
        return {
            "success": True,
            "chapter_id": chapter_id,
            "chapter_slug": chapter.slug,
            "changes_applied": len(preview.changes),
        }
