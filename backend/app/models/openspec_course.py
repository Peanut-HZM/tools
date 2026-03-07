"""
OpenSpec VibeCoding 互动课程模型
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Boolean, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import json

from .base import Base


class OpenSpecCourseChapter(Base):
    """OpenSpec 课程章节表"""

    __tablename__ = "openspec_course_chapters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # 章节标识符
    title = Column(String(200), nullable=False)  # 章节标题
    order = Column(Integer, nullable=False, default=0)  # 章节顺序
    content = Column(Text, nullable=False)  # 章节内容 (Markdown)
    chapter_type = Column(String(50), nullable=False, default="story")  # 类型：story/code/quiz/video
    video_url = Column(String(500), nullable=True)  # 视频链接
    is_locked = Column(Boolean, default=False)  # 是否锁定
    required_quiz_id = Column(Integer, ForeignKey("openspec_course_quizzes.id"), nullable=True)  # 解锁所需的测验 ID
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<OpenSpecCourseChapter(id={self.id}, slug={self.slug}, title={self.title})>"


class OpenSpecCourseQuiz(Base):
    """OpenSpec 课程测验表"""

    __tablename__ = "openspec_course_quizzes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_id = Column(Integer, ForeignKey("openspec_course_chapters.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)  # 测验标题
    passing_score = Column(Integer, default=60)  # 及格分数 (百分比)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<OpenSpecCourseQuiz(id={self.id}, chapter_id={self.chapter_id}, title={self.title})>"


class OpenSpecCourseQuizQuestion(Base):
    """OpenSpec 课程测验题目表"""

    __tablename__ = "openspec_course_quiz_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("openspec_course_quizzes.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)  # 题目内容
    question_type = Column(String(20), nullable=False, default="single")  # single/multiple/true_false
    correct_answer = Column(String(100), nullable=False)  # 正确答案索引，逗号分隔如 "1" 或 "1,3"
    explanation = Column(Text, nullable=True)  # 答案解析
    order = Column(Integer, default=0)  # 题目顺序
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<OpenSpecCourseQuizQuestion(id={self.id}, quiz_id={self.quiz_id}, question={self.question_text[:50]}...)"


class OpenSpecCourseQuizOption(Base):
    """OpenSpec 课程测验选项表"""

    __tablename__ = "openspec_course_quiz_options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("openspec_course_quiz_questions.id", ondelete="CASCADE"), nullable=False)
    option_text = Column(Text, nullable=False)  # 选项内容
    option_index = Column(Integer, nullable=False)  # 选项索引 (0=A, 1=B, 2=C, 3=D)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<OpenSpecCourseQuizOption(id={self.id}, question_id={self.question_id}, index={self.option_index})>"


class UserCourseProgress(Base):
    """用户课程进度表"""

    __tablename__ = "openspec_user_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)  # 用户 ID
    chapter_id = Column(Integer, ForeignKey("openspec_course_chapters.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="not_started")  # not_started/in_progress/completed
    quiz_score = Column(Float, nullable=True)  # 测验分数
    quiz_passed = Column(Boolean, default=False)  # 测验是否通过
    completed_at = Column(DateTime(timezone=True), nullable=True)  # 完成时间
    video_progress = Column(Integer, default=0)  # 视频播放进度 (秒)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 同一用户对同一章节只有一条进度记录
    __table_args__ = (
        UniqueConstraint("user_id", "chapter_id", name="uq_user_chapter"),
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<UserCourseProgress(id={self.id}, user_id={self.user_id}, chapter_id={self.chapter_id}, status={self.status})>"


class OpenSpecCourseResource(Base):
    """OpenSpec 课程资源表"""

    __tablename__ = "openspec_course_resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_id = Column(Integer, ForeignKey("openspec_course_chapters.id", ondelete="CASCADE"), nullable=False)
    resource_type = Column(String(50), nullable=False, default="code_sample")  # code_sample/contrast/video/template
    title = Column(String(200), nullable=False)  # 资源标题
    content = Column(Text, nullable=False)  # 资源内容
    extra_data = Column(Text, nullable=True)  # 额外元数据 (JSON 格式)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<OpenSpecCourseResource(id={self.id}, chapter_id={self.chapter_id}, type={self.resource_type})>"

    def get_metadata(self):
        """解析元数据为字典"""
        if self.extra_data:
            return json.loads(self.extra_data)
        return {}

    def set_metadata(self, data: dict):
        """设置元数据"""
        self.extra_data = json.dumps(data, ensure_ascii=False)
