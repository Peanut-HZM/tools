#!/usr/bin/env python3
"""
课程中心导入器 v2 — 将标准 Markdown 课程源文件导入 course_platform 模型

背景：scripts/course_import.py 依赖已删除的 openspec_course 模型，已失效。
本脚本按相同的 Markdown 章节格式（## 章节：slug + yaml 元数据 + ## 内容 +
## 测验 + ### 题目 + ## 资源）解析，直接导入当前课程中心标准模型
（courses / course_chapters / course_quizzes / course_quiz_questions /
 course_quiz_options / course_resources），并负责课程本身、分类与统计行。

用法：
  python scripts/course_import_v2.py course_data/ai_awakening/*.md
  python scripts/course_import_v2.py <file.md> --dry-run
  python scripts/course_import_v2.py <file.md> --course-meta meta.json

课程级元数据（标题/描述/作者/标签等）从文件头部的 "# 标题" 与正文首段
之外的 meta.json 读取；未提供时使用 --course-meta 传入的 JSON 文件。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import yaml  # noqa: E402

from app.models.base import SessionLocal  # noqa: E402
from app.models.course_platform import (  # noqa: E402
    Course,
    CourseChapter,
    CourseCategory,
    CourseQuiz,
    CourseQuizOption,
    CourseQuizQuestion,
    CourseResource,
    CourseStatistics,
)

CHAPTER_RE = re.compile(r"^## 章节：([a-zA-Z0-9_-]+)\s*$")
QUIZ_RE = re.compile(r"^## 测验：(.+)$")
QUESTION_RE = re.compile(r"^### 题目 (\d+)\s*$")
RESOURCE_RE = re.compile(r"^## 资源：(.+)$")
CONTENT_RE = re.compile(r"^## 内容\s*$")
QUESTION_TEXT_RE = re.compile(r"^\*\*题目内容：\*\*\s*(.+?)\s*$")
OPTION_RE = re.compile(r"^- ([A-Z])\)\s*(.+)$")
YAML_FENCE_RE = re.compile(r"^```yaml\s*$")

CHAPTER_TYPES = {"story", "lesson", "quiz-only", "code", "video", "section", "slides"}
RESOURCE_TYPES = {"code", "code_sample", "contrast", "video", "template", "image", "reference", "checklist"}


@dataclass
class ParsedQuestion:
    question_text: str = ""
    question_type: str = "single"
    correct_answer: str = ""
    explanation: Optional[str] = None
    options: List[str] = field(default_factory=list)


@dataclass
class ParsedQuiz:
    title: str = ""
    passing_score: int = 60
    questions: List[ParsedQuestion] = field(default_factory=list)


@dataclass
class ParsedResource:
    title: str = ""
    resource_type: str = "template"
    content: str = ""


@dataclass
class ParsedChapter:
    slug: str = ""
    order: int = 0
    title: str = ""
    chapter_type: str = "story"
    is_locked: bool = False
    duration_minutes: int = 0
    video_url: Optional[str] = None
    content: str = ""
    quizzes: List[ParsedQuiz] = field(default_factory=list)
    resources: List[ParsedResource] = field(default_factory=list)


def parse_yaml_block(lines: List[str], start: int) -> tuple[dict, int]:
    """解析从 start 行开始的 ```yaml 围栏块，返回 (data, 结束行号)

    yaml.safe_load 失败（如值中含 ASCII 引号等写法）时，退化为逐行
    "key: value" 解析，value 一律按字符串处理——保证导入不被内容中的
    引号风格卡死。
    """
    assert lines[start].strip() == "```yaml"
    yaml_lines = []
    i = start + 1
    while i < len(lines) and lines[i].strip() != "```":
        yaml_lines.append(lines[i])
        i += 1
    text = "\n".join(yaml_lines)
    try:
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            data = {}
    except yaml.YAMLError:
        data = {}
        for yl in yaml_lines:
            if ":" not in yl:
                continue
            k, v = yl.split(":", 1)
            k, v = k.strip(), v.strip()
            if v.lower() == "true":
                data[k] = True
            elif v.lower() == "false":
                data[k] = False
            else:
                data[k] = v
    return data, i  # i 指向结束围栏行，调用方 +1


def parse_markdown(md_content: str) -> List[ParsedChapter]:
    """解析标准课程 Markdown：只识别结构标记，其余原始行保留（含空行）"""
    lines = md_content.split("\n")
    chapters: List[ParsedChapter] = []
    chapter: Optional[ParsedChapter] = None
    # section: chapter_meta / content / quiz_meta / question_meta / resource_meta
    section = "idle"
    quiz: Optional[ParsedQuiz] = None
    question: Optional[ParsedQuestion] = None
    resource: Optional[ParsedResource] = None
    buf: List[str] = []

    def flush_buf():
        nonlocal section
        text = "\n".join(buf).strip()
        buf.clear()
        if not text:
            return
        if section == "content" and chapter is not None:
            chapter.content = text
        elif section == "resource_meta" and resource is not None:
            resource.content = text
        elif section == "question_meta" and question is not None:
            # 题目正文兜底（正常应由 **题目内容：** 行提供）
            if not question.question_text:
                question.question_text = text

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        m = CHAPTER_RE.match(line)
        if m:
            flush_buf()
            if chapter is not None:
                chapters.append(chapter)
            chapter = ParsedChapter(slug=m.group(1))
            section = "chapter_meta"
            quiz, question, resource = None, None, None
            i += 1
            continue

        if chapter is None:
            i += 1
            continue  # 文件头部（课程标题/说明）跳过

        if YAML_FENCE_RE.match(line):
            data, end = parse_yaml_block(lines, i)
            if section == "chapter_meta":
                for key in ("title", "chapter_type", "video_url"):
                    if key in data and data[key] is not None:
                        setattr(chapter, key, str(data[key]))
                if "order" in data:
                    chapter.order = int(data["order"])
                if "duration_minutes" in data:
                    chapter.duration_minutes = int(data["duration_minutes"])
                if "is_locked" in data:
                    chapter.is_locked = str(data["is_locked"]).lower() == "true"
            elif section == "quiz_meta" and quiz is not None:
                if "passing_score" in data:
                    quiz.passing_score = int(data["passing_score"])
            elif section == "question_meta" and question is not None:
                if "question_type" in data:
                    question.question_type = str(data["question_type"])
                if "correct_answer" in data:
                    ca = data["correct_answer"]
                    question.correct_answer = str(ca)
                if "explanation" in data:
                    question.explanation = data["explanation"]
            elif section == "resource_meta" and resource is not None:
                if "resource_type" in data:
                    resource.resource_type = str(data["resource_type"])
            if section == "chapter_meta":
                section = "content"  # yaml 块之后即章节正文
            i = end + 1
            continue

        if CONTENT_RE.match(line):
            flush_buf()
            section = "content"
            i += 1
            continue

        mq = QUIZ_RE.match(line)
        if mq:
            flush_buf()
            quiz = ParsedQuiz(title=mq.group(1).strip())
            chapter.quizzes.append(quiz)
            question = None
            section = "quiz_meta"
            i += 1
            continue

        mr = RESOURCE_RE.match(line)
        if mr:
            flush_buf()
            resource = ParsedResource(title=mr.group(1).strip())
            chapter.resources.append(resource)
            section = "resource_meta"
            i += 1
            continue

        if section in ("quiz_meta", "question_meta") and QUESTION_RE.match(line):
            flush_buf()
            question = ParsedQuestion()
            quiz.questions.append(question)
            section = "question_meta"
            i += 1
            continue

        mqtext = QUESTION_TEXT_RE.match(line)
        if mqtext and section == "question_meta" and question is not None:
            question.question_text = mqtext.group(1)
            i += 1
            continue

        mo = OPTION_RE.match(line)
        if mo and section == "question_meta" and question is not None:
            idx = ord(mo.group(1)) - ord("A")
            while len(question.options) <= idx:
                question.options.append("")
            question.options[idx] = mo.group(2)
            i += 1
            continue

        if section in ("content", "resource_meta"):
            buf.append(raw)
        i += 1

    flush_buf()
    if chapter is not None:
        chapters.append(chapter)
    return chapters


def validate(chapters: List[ParsedChapter]) -> List[str]:
    errors: List[str] = []
    seen = set()
    orders = set()
    for ch in chapters:
        if ch.slug in seen:
            errors.append(f"章节 slug 重复: {ch.slug}")
        seen.add(ch.slug)
        if ch.order in orders:
            errors.append(f"章节 order 重复: {ch.order} ({ch.slug})")
        orders.add(ch.order)
        if not ch.title:
            errors.append(f"{ch.slug}: title 为空")
        if not ch.content:
            errors.append(f"{ch.slug}: 正文为空")
        if ch.chapter_type not in CHAPTER_TYPES:
            errors.append(f"{ch.slug}: 非法 chapter_type {ch.chapter_type}")
        for q in ch.quizzes:
            if q.passing_score < 0 or q.passing_score > 100:
                errors.append(f"{ch.slug}/{q.title}: passing_score 越界")
            for idx, qn in enumerate(q.questions, 1):
                if not qn.question_text:
                    errors.append(f"{ch.slug}/{q.title}/题{idx}: 题干为空")
                if not qn.correct_answer:
                    errors.append(f"{ch.slug}/{q.title}/题{idx}: 缺 correct_answer")
                if not qn.options or any(not o for o in qn.options):
                    errors.append(f"{ch.slug}/{q.title}/题{idx}: 选项缺失")
                if qn.question_type == "single" and "," in qn.correct_answer:
                    errors.append(f"{ch.slug}/{q.title}/题{idx}: 单选题答案含多个索引")
                for ca in qn.correct_answer.split(","):
                    if ca.strip() and (not ca.strip().isdigit() or int(ca) >= len(qn.options)):
                        errors.append(f"{ch.slug}/{q.title}/题{idx}: 答案索引越界 {ca}")
        for r in ch.resources:
            if r.resource_type not in RESOURCE_TYPES:
                errors.append(f"{ch.slug}/{r.title}: 非法 resource_type {r.resource_type}")
    return errors


def ensure_category(db, name: str, slug: str) -> CourseCategory:
    cat = db.query(CourseCategory).filter_by(slug=slug).first()
    if not cat:
        cat = CourseCategory(name=name, slug=slug, sort_order=1, icon="🤖")
        db.add(cat)
        db.flush()
    return cat


DEFAULT_COURSE_META = {
    "slug": "",
    "title": "",
    "description": "",
    "author": "AI Awakening 系列",
    "content_type": "analysis",
    "category_slug": "ai-agent-learning-path",
    "category_name": "AI 与智能体学习路径",
    "tags": [],
    "status": "published",
    "price": 0,
    "cover_image": "",
}


def import_course(db, md_path: Path, course_meta_path: Optional[str], dry_run: bool) -> dict:
    md_content = md_path.read_text(encoding="utf-8")
    chapters = parse_markdown(md_content)
    errors = validate(chapters)
    if errors:
        return {"ok": False, "errors": errors, "chapters": len(chapters)}

    meta = dict(DEFAULT_COURSE_META)
    if course_meta_path:
        meta.update(json.loads(Path(course_meta_path).read_text(encoding="utf-8")))

    # 课程级元数据支持在 markdown 顶部以 <!-- meta: {"..."} --> 注释覆盖
    m = re.search(r"<!--\s*meta:\s*(\{.*?\})\s*-->", md_content, re.DOTALL)
    if m:
        meta.update(json.loads(m.group(1)))
    if not meta["slug"] or not meta["title"]:
        return {"ok": False, "errors": ["缺少课程 slug/title（用 --course-meta 或 <!-- meta: --> 提供）"], "chapters": 0}

    result = {"course": meta["slug"], "chapters": len(chapters),
              "quizzes": sum(len(c.quizzes) for c in chapters),
              "questions": sum(len(q.questions) for c in chapters for q in c.quizzes),
              "resources": sum(len(c.resources) for c in chapters),
              "reading_time": sum(c.duration_minutes for c in chapters),
              "dry_run": dry_run, "new_course": False}

    if dry_run:
        return {**result, "ok": True}

    cat = ensure_category(db, meta["category_name"], meta["category_slug"])

    course = db.query(Course).filter_by(slug=meta["slug"]).first()
    if not course:
        course = Course(slug=meta["slug"], status=meta["status"])
        db.add(course)
        result["new_course"] = True
    course.title = meta["title"]
    course.description = meta["description"]
    course.author = meta["author"]
    course.content_type = meta["content_type"]
    course.category_id = cat.id
    course.reading_time = result["reading_time"]
    course.tags = json.dumps(meta["tags"], ensure_ascii=False)
    course.price = meta["price"]
    course.status = meta["status"]
    if meta.get("cover_image"):
        course.cover_image = meta["cover_image"]
    db.flush()

    # 课程统计行（列表接口强依赖，必须存在）
    stats = db.query(CourseStatistics).filter_by(course_id=course.id).first()
    if not stats:
        db.add(CourseStatistics(course_id=course.id))

    # 章节 upsert（按 course_id + slug），并删除不在 markdown 中的章节
    existing = {c.slug: c for c in db.query(CourseChapter).filter_by(course_id=course.id).all()}
    for ch in chapters:
        row = existing.pop(ch.slug, None)
        if row is None:
            row = CourseChapter(course_id=course.id, slug=ch.slug)
            db.add(row)
        row.title = ch.title
        row.order = ch.order
        row.chapter_type = ch.chapter_type
        row.is_locked = bool(ch.is_locked)
        row.duration_minutes = ch.duration_minutes
        row.video_url = ch.video_url
        row.content = ch.content
        db.flush()

        # 测验 upsert（按 chapter_id + title）
        eq = {q.title: q for q in db.query(CourseQuiz).filter_by(chapter_id=row.id).all()}
        for q in ch.quizzes:
            qrow = eq.pop(q.title, None)
            if qrow is None:
                qrow = CourseQuiz(chapter_id=row.id, title=q.title)
                db.add(qrow)
            qrow.passing_score = q.passing_score
            db.flush()

            eqn = {n.order: n for n in db.query(CourseQuizQuestion).filter_by(quiz_id=qrow.id).all()}
            for qidx, qn in enumerate(q.questions, 1):
                nrow = eqn.pop(qidx, None)
                if nrow is None:
                    nrow = CourseQuizQuestion(quiz_id=qrow.id, order=qidx)
                    db.add(nrow)
                nrow.question_text = qn.question_text
                nrow.question_type = qn.question_type
                nrow.correct_answer = qn.correct_answer
                nrow.explanation = qn.explanation
                db.flush()

                eopt = {o.option_index: o for o in db.query(CourseQuizOption).filter_by(question_id=nrow.id).all()}
                for oidx, otext in enumerate(qn.options):
                    orow = eopt.pop(oidx, None)
                    if orow is None:
                        orow = CourseQuizOption(question_id=nrow.id, option_index=oidx)
                        db.add(orow)
                    orow.option_text = otext
                for orphan in eopt.values():
                    db.delete(orphan)
            for orphan in eqn.values():
                db.delete(orphan)
        for orphan in eq.values():
            db.delete(orphan)
    for orphan in existing.values():
        db.delete(orphan)

    # 资源 upsert（按 chapter_id + title）
    for ch in chapters:
        chrow = db.query(CourseChapter).filter_by(course_id=course.id, slug=ch.slug).first()
        er = {r.title: r for r in db.query(CourseResource).filter_by(chapter_id=chrow.id).all()}
        for r in ch.resources:
            rrow = er.pop(r.title, None)
            if rrow is None:
                rrow = CourseResource(chapter_id=chrow.id, title=r.title)
                db.add(rrow)
            rrow.resource_type = r.resource_type
            rrow.content = r.content
        for orphan in er.values():
            db.delete(orphan)

    return {**result, "ok": True}


def main() -> None:
    parser = argparse.ArgumentParser(description="课程中心导入器 v2")
    parser.add_argument("files", nargs="+", help="课程 Markdown 文件")
    parser.add_argument("--course-meta", help="课程级元数据 JSON 文件")
    parser.add_argument("--dry-run", action="store_true", help="只解析验证，不写库")
    args = parser.parse_args()

    db = SessionLocal()
    exit_code = 0
    try:
        for f in args.files:
            path = Path(f)
            print(f"==== 导入 {path.name} ====")
            res = import_course(db, path, args.course_meta, args.dry_run)
            if not res.get("ok"):
                print("❌ 校验失败：")
                for e in res["errors"]:
                    print("  -", e)
                exit_code = 1
                continue
            print(f"✅ 课程 {res['course']}: {res['chapters']} 章 / {res['quizzes']} 测验 / "
                  f"{res['questions']} 题 / {res['resources']} 资源 / {res['reading_time']} 分钟"
                  f"{'（dry-run）' if res['dry_run'] else ''}")
        if not args.dry_run:
            db.commit()
            print("已提交数据库。")
        else:
            db.rollback()
    except Exception as e:
        db.rollback()
        print(f"导入失败，已回滚: {e}")
        raise
    finally:
        db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
