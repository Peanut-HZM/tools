"""
课程学习平台 SQLAlchemy 模型

包含 12 张表：
- 核心业务表 (7 张): courses, course_categories, course_chapters, course_quizzes,
  course_quiz_questions, course_quiz_options, course_resources
- 用户交互表 (5 张): course_enrollments, course_progress, course_interactions,
  course_reviews, course_statistics
"""

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Integer, Text, Boolean, Float,
    UniqueConstraint, Numeric, DECIMAL
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class CourseCategory(Base):
    """课程分类表"""

    __tablename__ = "course_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="分类名称")
    slug = Column(String(50), unique=True, nullable=False, comment="分类标识符")
    parent_id = Column(Integer, ForeignKey("course_categories.id"), comment="父分类 ID")
    sort_order = Column(Integer, default=0, comment="排序")
    icon = Column(String(50), comment="图标")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 自关联：父子分类
    parent = relationship("CourseCategory", remote_side=[id], backref="children")

    def __repr__(self):
        return f"<CourseCategory(id={self.id}, name={self.name})>"


class Course(Base):
    """课程主表（支持技术分析内容）"""

    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False, comment="课程标题")
    slug = Column(String(100), unique=True, nullable=False, comment="课程标识符")
    description = Column(Text, nullable=False, comment="课程描述")
    cover_image = Column(String(500), comment="封面图 URL")
    category_id = Column(Integer, ForeignKey("course_categories.id"), comment="分类 ID")
    instructor_id = Column(String(64), comment="讲师 ID")
    price = Column(DECIMAL(10, 2), default=0, comment="价格")
    status = Column(String(20), default="draft", comment="状态：draft/published/archived")

    # 技术分析内容新增字段
    content_type = Column(String(20), default="analysis", comment="内容类型：analysis(技术分析)/sharing(技术分享)/case_study(项目案例)")
    author = Column(String(100), comment="作者")
    reading_time = Column(Integer, default=0, comment="阅读时长（分钟）")
    tags = Column(Text, comment="标签（JSON 数组）")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联
    category = relationship("CourseCategory", backref="courses")
    chapters = relationship("CourseChapter", backref="course", cascade="all, delete-orphan")
    enrollments = relationship("CourseEnrollment", backref="course", cascade="all, delete-orphan")
    statistics = relationship("CourseStatistics", backref="course", uselist=False, cascade="all, delete-orphan")
    reviews = relationship("CourseReview", backref="course", cascade="all, delete-orphan")
    interactions = relationship("CourseInteraction", backref="course", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Course(id={self.id}, slug={self.slug}, title={self.title})>"

    def get_tags(self) -> list:
        """解析标签为列表"""
        if self.tags:
            import json
            try:
                return json.loads(self.tags)
            except:
                return []
        return []

    def set_tags(self, tags: list):
        """设置标签"""
        import json
        self.tags = json.dumps(tags, ensure_ascii=False)


class CourseChapter(Base):
    """课程章节表"""

    __tablename__ = "course_chapters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, comment="课程 ID")
    slug = Column(String(100), nullable=False, comment="章节标识符")
    title = Column(String(200), nullable=False, comment="章节标题")
    order = Column(Integer, default=0, comment="章节顺序")
    content = Column(Text, nullable=False, comment="章节内容 (Markdown)")
    chapter_type = Column(String(50), default="story", comment="类型：story/lesson/quiz-only/code/video/section/slides")
    video_url = Column(String(500), comment="视频链接")
    is_locked = Column(Boolean, default=False, comment="是否锁定")
    duration_minutes = Column(Integer, default=0, comment="学习时长 (分钟)")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联
    quizzes = relationship("CourseQuiz", backref="chapter", cascade="all, delete-orphan")
    resources = relationship("CourseResource", backref="chapter", cascade="all, delete-orphan")
    progress = relationship("CourseProgress", backref="chapter", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CourseChapter(id={self.id}, title={self.title})>"


class CourseQuiz(Base):
    """课程测验表"""

    __tablename__ = "course_quizzes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_id = Column(Integer, ForeignKey("course_chapters.id", ondelete="CASCADE"), nullable=False, comment="章节 ID")
    title = Column(String(200), nullable=False, comment="测验标题")
    passing_score = Column(Integer, default=60, comment="及格分数")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联
    questions = relationship("CourseQuizQuestion", backref="quiz", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CourseQuiz(id={self.id}, title={self.title})>"


class CourseQuizQuestion(Base):
    """课程测验题目表"""

    __tablename__ = "course_quiz_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("course_quizzes.id", ondelete="CASCADE"), nullable=False, comment="测验 ID")
    question_text = Column(Text, nullable=False, comment="题目内容")
    question_type = Column(String(20), default="single", comment="类型：single/multiple")
    correct_answer = Column(String(100), nullable=False, comment="正确答案")
    explanation = Column(Text, comment="答案解析")
    order = Column(Integer, default=0, comment="题目顺序")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联
    options = relationship("CourseQuizOption", backref="question", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CourseQuizQuestion(id={self.id}, question={self.question_text[:50]}...)>"


class CourseQuizOption(Base):
    """课程测验选项表"""

    __tablename__ = "course_quiz_options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("course_quiz_questions.id", ondelete="CASCADE"), nullable=False, comment="题目 ID")
    option_text = Column(Text, nullable=False, comment="选项内容")
    option_index = Column(Integer, nullable=False, comment="选项索引 (0=A, 1=B...)")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<CourseQuizOption(id={self.id}, index={self.option_index})>"


class CourseResource(Base):
    """课程资源表"""

    __tablename__ = "course_resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_id = Column(Integer, ForeignKey("course_chapters.id", ondelete="CASCADE"), nullable=False, comment="章节 ID")
    resource_type = Column(String(50), nullable=False, comment="资源类型：code/contrast/video/template/image")
    title = Column(String(200), nullable=False, comment="资源标题")
    content = Column(Text, nullable=False, comment="资源内容")
    file_url = Column(String(500), comment="文件 URL (OSS)")
    file_size = Column(Integer, comment="文件大小 (字节)")
    extra_data = Column(Text, comment="额外元数据 (JSON)")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CourseResource(id={self.id}, title={self.title})>"


class CourseEnrollment(Base):
    """用户课程关联表"""

    __tablename__ = "course_enrollments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True, comment="用户 ID")
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, comment="课程 ID")
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now(), comment="报名时间")
    completed_at = Column(DateTime(timezone=True), comment="完成时间")
    status = Column(String(20), default="active", comment="状态：active/completed")
    progress_percent = Column(Float, default=0, comment="进度百分比 (0-100)")

    # 唯一约束：同一用户对同一课程只有一条记录
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_user_course"),
    )

    def __repr__(self):
        return f"<CourseEnrollment(user_id={self.user_id}, course_id={self.course_id})>"


class CourseProgress(Base):
    """学习进度表"""

    __tablename__ = "course_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True, comment="用户 ID")
    chapter_id = Column(Integer, ForeignKey("course_chapters.id", ondelete="CASCADE"), nullable=False, comment="章节 ID")
    status = Column(String(20), default="not_started", comment="状态：not_started/in_progress/completed")
    quiz_score = Column(Float, comment="测验分数 (0-100)")
    quiz_passed = Column(Boolean, default=False, comment="测验是否通过")
    video_progress = Column(Integer, default=0, comment="视频进度 (秒)")
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now(), comment="最后访问时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 唯一约束：同一用户对同一章节只有一条记录
    __table_args__ = (
        UniqueConstraint("user_id", "chapter_id", name="uq_user_chapter"),
    )

    def __repr__(self):
        return f"<CourseProgress(user_id={self.user_id}, chapter_id={self.chapter_id})>"


class CourseInteraction(Base):
    """课程互动表（点赞/收藏/浏览）"""

    __tablename__ = "course_interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True, comment="用户 ID")
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, comment="课程 ID")
    interaction_type = Column(String(20), nullable=False, comment="类型：like/view/bookmark/favorite")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 索引
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", "interaction_type", name="uq_user_course_interaction"),
    )

    def __repr__(self):
        return f"<CourseInteraction(user_id={self.user_id}, type={self.interaction_type})>"


class CourseReview(Base):
    """课程评价表"""

    __tablename__ = "course_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True, comment="用户 ID")
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, comment="课程 ID")
    rating = Column(Integer, nullable=False, comment="评分 (1-5)")
    comment = Column(Text, comment="评论内容")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CourseReview(id={self.id}, rating={self.rating})>"


class CourseStatistics(Base):
    """课程统计表"""

    __tablename__ = "course_statistics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), unique=True, nullable=False, comment="课程 ID")
    view_count = Column(Integer, default=0, comment="浏览次数")
    enroll_count = Column(Integer, default=0, comment="报名人数")
    like_count = Column(Integer, default=0, comment="点赞数")
    bookmark_count = Column(Integer, default=0, comment="收藏数")
    review_count = Column(Integer, default=0, comment="评价数")
    avg_rating = Column(Float, default=0, comment="平均评分")
    completed_count = Column(Integer, default=0, comment="完成人数")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CourseStatistics(course_id={self.course_id})>"
