"""
课程学习平台 Pydantic Schemas

为课程平台提供数据验证和序列化。
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


# ============ 课程分类 Schemas ============

class CourseCategoryBase(BaseModel):
    """课程分类基础模型"""
    name: str = Field(..., description="分类名称", min_length=1, max_length=100)
    slug: str = Field(..., description="分类标识符", min_length=1, max_length=50)
    parent_id: Optional[int] = Field(None, description="父分类 ID")
    sort_order: int = Field(default=0, description="排序")
    icon: Optional[str] = Field(None, description="图标")


class CourseCategoryCreate(CourseCategoryBase):
    """创建课程分类请求"""
    pass


class CourseCategoryUpdate(BaseModel):
    """更新课程分类请求"""
    name: Optional[str] = None
    slug: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    icon: Optional[str] = None


class CourseCategoryResponse(CourseCategoryBase):
    """课程分类响应"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 课程 Schemas ============

class CourseBase(BaseModel):
    """课程基础模型"""
    title: str = Field(..., description="课程标题", min_length=1, max_length=200)
    slug: str = Field(..., description="课程标识符", min_length=1, max_length=100)
    description: str = Field(..., description="课程描述")
    cover_image: Optional[str] = Field(None, description="封面图 URL", max_length=500)
    category_id: Optional[int] = Field(None, description="分类 ID")
    instructor_id: Optional[str] = Field(None, description="讲师 ID")
    price: Decimal = Field(default=0, description="价格", ge=0)
    status: str = Field(default="draft", description="状态：draft/published/archived")

    # 技术分析内容新增字段
    content_type: Optional[str] = Field(default="analysis", description="内容类型：analysis/sharing/case_study")
    author: Optional[str] = Field(None, description="作者", max_length=100)
    reading_time: Optional[int] = Field(default=0, description="阅读时长（分钟）", ge=0)
    tags: Optional[List[str]] = Field(None, description="标签列表")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """验证课程状态"""
        allowed_statuses = ["draft", "published", "archived"]
        if v not in allowed_statuses:
            raise ValueError(f"状态必须是 {', '.join(allowed_statuses)} 之一")
        return v

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: Optional[str]) -> Optional[str]:
        """验证内容类型"""
        if v is None:
            return v
        allowed_types = ["analysis", "sharing", "case_study"]
        if v not in allowed_types:
            raise ValueError(f"内容类型必须是 {', '.join(allowed_types)} 之一")
        return v


class CourseCreate(CourseBase):
    """创建课程请求"""
    pass


class CourseUpdate(BaseModel):
    """更新课程请求"""
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    category_id: Optional[int] = None
    instructor_id: Optional[str] = None
    price: Optional[Decimal] = None
    status: Optional[str] = None
    # 技术分析内容字段
    content_type: Optional[str] = None
    author: Optional[str] = None
    reading_time: Optional[int] = None
    tags: Optional[List[str]] = None


class CourseResponse(CourseBase):
    """课程响应"""
    id: int
    created_at: datetime
    updated_at: datetime
    category: Optional[CourseCategoryResponse] = None

    class Config:
        from_attributes = True


class CourseListItem(BaseModel):
    """课程列表项（简化版）"""
    id: int
    slug: str
    title: str
    description: str
    cover_image: Optional[str] = None
    category: Optional[CourseCategoryResponse] = None
    statistics: Optional["CourseStatisticsResponse"] = None
    # 技术分析内容字段
    content_type: Optional[str] = None
    author: Optional[str] = None
    reading_time: Optional[int] = None
    tags: Optional[List[str]] = None


# ============ 课程章节 Schemas ============

class CourseChapterBase(BaseModel):
    """课程章节基础模型"""
    slug: str = Field(..., description="章节标识符", min_length=1, max_length=100)
    title: str = Field(..., description="章节标题", min_length=1, max_length=200)
    order: int = Field(default=0, description="章节顺序", ge=0)
    content: str = Field(..., description="章节内容（Markdown 格式）")
    chapter_type: str = Field(default="story", description="类型：story/lesson/quiz-only/code/video")
    video_url: Optional[str] = Field(None, description="视频链接", max_length=500)
    is_locked: bool = Field(default=False, description="是否锁定")
    duration_minutes: int = Field(default=0, description="学习时长（分钟）", ge=0)

    @field_validator("chapter_type")
    @classmethod
    def validate_chapter_type(cls, v: str) -> str:
        """验证章节类型"""
        allowed_types = ["story", "lesson", "quiz-only", "code", "video"]
        if v not in allowed_types:
            raise ValueError(f"章节类型必须是 {', '.join(allowed_types)} 之一")
        return v


class CourseChapterCreate(CourseChapterBase):
    """创建课程章节请求"""
    pass


class CourseChapterUpdate(BaseModel):
    """更新课程章节请求"""
    title: Optional[str] = None
    content: Optional[str] = None
    order: Optional[int] = None
    chapter_type: Optional[str] = None
    video_url: Optional[str] = None
    is_locked: Optional[bool] = None
    duration_minutes: Optional[int] = None


class CourseChapterResponse(CourseChapterBase):
    """课程章节响应"""
    id: int
    course_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 课程测验 Schemas ============

class CourseQuizBase(BaseModel):
    """课程测验基础模型"""
    chapter_id: int = Field(..., description="关联的章节 ID", gt=0)
    title: str = Field(..., description="测验标题", min_length=1, max_length=200)
    passing_score: int = Field(default=60, description="及格分数 (0-100)", ge=0, le=100)

    @field_validator("passing_score")
    @classmethod
    def validate_passing_score(cls, v: int) -> int:
        """验证及格分数"""
        if v < 0 or v > 100:
            raise ValueError("及格分数必须在 0-100 之间")
        return v


class CourseQuizCreate(CourseQuizBase):
    """创建课程测验请求"""
    pass


class CourseQuizUpdate(BaseModel):
    """更新课程测验请求"""
    title: Optional[str] = None
    passing_score: Optional[int] = None


# ============ 测验题目 Schemas ============

class CourseQuizQuestionBase(BaseModel):
    """测验题目基础模型"""
    question_text: str = Field(..., description="题目内容")
    question_type: str = Field(default="single", description="类型：single/multiple")
    correct_answer: str = Field(..., description="正确答案（逗号分隔）")
    explanation: Optional[str] = Field(None, description="答案解析")
    order: int = Field(default=0, description="题目顺序", ge=0)

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, v: str) -> str:
        """验证题目类型"""
        allowed_types = ["single", "multiple"]
        if v not in allowed_types:
            raise ValueError(f"题目类型必须是 {', '.join(allowed_types)} 之一")
        return v


class CourseQuizQuestionCreate(CourseQuizQuestionBase):
    """创建测验题目请求"""
    pass


class CourseQuizQuestionResponse(CourseQuizQuestionBase):
    """测验题目响应"""
    id: int
    quiz_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 测验选项 Schemas ============

class CourseQuizOptionBase(BaseModel):
    """测验选项基础模型"""
    option_text: str = Field(..., description="选项内容")
    option_index: int = Field(..., description="选项索引 (0=A, 1=B...)", ge=0, le=25)


class CourseQuizOptionCreate(CourseQuizOptionBase):
    """创建测验选项请求"""
    pass


class CourseQuizOptionResponse(CourseQuizOptionBase):
    """测验选项响应"""
    id: int
    question_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CourseQuizQuestionWithOptionResponse(CourseQuizQuestionBase):
    """测验题目响应（包含选项）"""
    id: int
    quiz_id: int
    created_at: datetime
    options: List["CourseQuizOptionResponse"] = []

    class Config:
        from_attributes = True


class CourseQuizResponse(CourseQuizBase):
    """课程测验响应"""
    id: int
    created_at: datetime
    updated_at: datetime
    questions: List[CourseQuizQuestionWithOptionResponse] = []

    class Config:
        from_attributes = True


# ============ 课程资源 Schemas ============

class CourseResourceBase(BaseModel):
    """课程资源基础模型"""
    chapter_id: int = Field(..., description="关联的章节 ID", gt=0)
    resource_type: str = Field(..., description="资源类型：code/contrast/video/template/image")
    title: str = Field(..., description="资源标题", min_length=1, max_length=200)
    content: str = Field(..., description="资源内容")
    file_url: Optional[str] = Field(None, description="文件 URL (OSS)", max_length=500)
    file_size: Optional[int] = Field(None, description="文件大小 (字节)", ge=0)
    extra_data: Optional[Dict[str, Any]] = Field(None, description="额外元数据 (JSON)")

    @field_validator("resource_type")
    @classmethod
    def validate_resource_type(cls, v: str) -> str:
        """验证资源类型"""
        allowed_types = ["code", "contrast", "video", "template", "image"]
        if v not in allowed_types:
            raise ValueError(f"资源类型必须是 {', '.join(allowed_types)} 之一")
        return v


class CourseResourceCreate(CourseResourceBase):
    """创建课程资源请求"""
    pass


class CourseResourceUpdate(BaseModel):
    """更新课程资源请求"""
    title: Optional[str] = None
    content: Optional[str] = None
    resource_type: Optional[str] = None
    file_url: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class CourseResourceResponse(CourseResourceBase):
    """课程资源响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_validator("extra_data", mode="before")
    @classmethod
    def parse_extra_data(cls, v):
        """解析 extra_data 为字典（如果它是 JSON 字符串）"""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except:
                return None
        return v


# ============ 用户报名 Schemas ============

class CourseEnrollmentBase(BaseModel):
    """用户课程关联基础模型"""
    user_id: str = Field(..., description="用户 ID")
    course_id: int = Field(..., description="课程 ID", gt=0)
    status: str = Field(default="active", description="状态：active/completed")
    progress_percent: float = Field(default=0, description="进度百分比 (0-100)", ge=0, le=100)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """验证状态"""
        allowed_statuses = ["active", "completed"]
        if v not in allowed_statuses:
            raise ValueError(f"状态必须是 {', '.join(allowed_statuses)} 之一")
        return v


class CourseEnrollmentCreate(CourseEnrollmentBase):
    """创建用户课程关联请求"""
    pass


class CourseEnrollmentUpdate(BaseModel):
    """更新用户课程关联请求"""
    status: Optional[str] = None
    progress_percent: Optional[float] = None
    completed_at: Optional[datetime] = None


class CourseEnrollmentResponse(CourseEnrollmentBase):
    """用户课程关联响应"""
    id: int
    enrolled_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 学习进度 Schemas ============

class CourseProgressBase(BaseModel):
    """学习进度基础模型"""
    user_id: str = Field(..., description="用户 ID")
    chapter_id: int = Field(..., description="章节 ID", gt=0)
    status: str = Field(default="not_started", description="状态：not_started/in_progress/completed")
    quiz_score: Optional[float] = Field(None, description="测验分数 (0-100)", ge=0, le=100)
    quiz_passed: bool = Field(default=False, description="测验是否通过")
    video_progress: int = Field(default=0, description="视频进度 (秒)", ge=0)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """验证状态"""
        allowed_statuses = ["not_started", "in_progress", "completed"]
        if v not in allowed_statuses:
            raise ValueError(f"状态必须是 {', '.join(allowed_statuses)} 之一")
        return v


class CourseProgressCreate(CourseProgressBase):
    """创建学习进度请求"""
    pass


class CourseProgressUpdate(BaseModel):
    """更新学习进度请求"""
    status: Optional[str] = None
    quiz_score: Optional[float] = None
    quiz_passed: Optional[bool] = None
    video_progress: Optional[int] = None
    last_accessed_at: Optional[datetime] = None


class CourseProgressResponse(CourseProgressBase):
    """学习进度响应"""
    id: int
    last_accessed_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 课程互动 Schemas ============

class CourseInteractionBase(BaseModel):
    """课程互动基础模型"""
    user_id: str = Field(..., description="用户 ID")
    course_id: int = Field(..., description="课程 ID", gt=0)
    interaction_type: str = Field(..., description="类型：like/view/bookmark/favorite")

    @field_validator("interaction_type")
    @classmethod
    def validate_interaction_type(cls, v: str) -> str:
        """验证互动类型"""
        allowed_types = ["like", "view", "bookmark", "favorite"]
        if v not in allowed_types:
            raise ValueError(f"互动类型必须是 {', '.join(allowed_types)} 之一")
        return v


class CourseInteractionCreate(CourseInteractionBase):
    """创建课程互动请求"""
    pass


class CourseInteractionResponse(CourseInteractionBase):
    """课程互动响应"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 课程评价 Schemas ============

class CourseReviewBase(BaseModel):
    """课程评价基础模型"""
    user_id: str = Field(..., description="用户 ID")
    course_id: int = Field(..., description="课程 ID", gt=0)
    rating: int = Field(..., description="评分 (1-5)", ge=1, le=5)
    comment: Optional[str] = Field(None, description="评论内容")

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        """验证评分"""
        if v < 1 or v > 5:
            raise ValueError("评分必须在 1-5 之间")
        return v


class CourseReviewCreate(CourseReviewBase):
    """创建课程评价请求"""
    pass


class CourseReviewUpdate(BaseModel):
    """更新课程评价请求"""
    rating: Optional[int] = None
    comment: Optional[str] = None


class CourseReviewResponse(CourseReviewBase):
    """课程评价响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 课程统计 Schemas ============

class CourseStatisticsBase(BaseModel):
    """课程统计基础模型"""
    course_id: int = Field(..., description="课程 ID", gt=0)
    view_count: int = Field(default=0, description="浏览次数", ge=0)
    enroll_count: int = Field(default=0, description="报名人数", ge=0)
    like_count: int = Field(default=0, description="点赞数", ge=0)
    bookmark_count: int = Field(default=0, description="收藏数", ge=0)
    review_count: int = Field(default=0, description="评价数", ge=0)
    avg_rating: float = Field(default=0, description="平均评分", ge=0, le=5)
    completed_count: int = Field(default=0, description="完成人数", ge=0)


class CourseStatisticsCreate(CourseStatisticsBase):
    """创建课程统计请求"""
    pass


class CourseStatisticsUpdate(BaseModel):
    """更新课程统计请求"""
    view_count: Optional[int] = None
    enroll_count: Optional[int] = None
    like_count: Optional[int] = None
    bookmark_count: Optional[int] = None
    review_count: Optional[int] = None
    avg_rating: Optional[float] = None
    completed_count: Optional[int] = None


class CourseStatisticsResponse(CourseStatisticsBase):
    """课程统计响应"""
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 组合响应 Schemas ============

class CourseDetailResponse(CourseResponse):
    """课程详情响应（包含章节、统计等）"""
    chapters: List[CourseChapterResponse] = []
    statistics: Optional[CourseStatisticsResponse] = None


class CourseListResponse(BaseModel):
    """课程列表响应"""
    courses: List[CourseListItem]
    total: int
    page: int
    limit: int


class CourseCategoryTree(BaseModel):
    """课程分类树响应"""
    id: int
    name: str
    slug: str
    icon: Optional[str] = None
    children: List["CourseCategoryTree"] = []


class MyCourseResponse(BaseModel):
    """我的课程响应"""
    course: CourseListItem
    enrollment: CourseEnrollmentResponse
    completed_chapters: int = 0
    total_chapters: int = 0


# ============ 课程导入导出 Schemas ============

class ExportedQuizOption(BaseModel):
    """导出测验选项"""
    option_text: str
    option_index: int


class ExportedQuizQuestion(BaseModel):
    """导出测验题目"""
    question_text: str
    question_type: str
    correct_answer: str
    explanation: Optional[str] = None
    order: int
    options: List[ExportedQuizOption] = []


class ExportedQuiz(BaseModel):
    """导出测验"""
    title: str
    passing_score: int
    questions: List[ExportedQuizQuestion] = []


class ExportedResource(BaseModel):
    """导出资源"""
    resource_type: str
    title: str
    content: str
    extra_data: Optional[Dict[str, Any]] = None


class ExportedChapter(BaseModel):
    """导出章节"""
    slug: str
    title: str
    order: int
    content: str
    chapter_type: str
    video_url: Optional[str] = None
    is_locked: bool
    quizzes: List[ExportedQuiz] = []
    resources: List[ExportedResource] = []


class CourseExportData(BaseModel):
    """课程导出数据"""
    version: str = "2.0"
    course_id: Optional[int] = None
    course_title: str
    export_timestamp: str
    export_stats: Dict[str, int]
    chapters: List[ExportedChapter]


class ImportStrategy(str, Enum):
    """导入策略"""
    MERGE = "merge"
    REPLACE = "replace"
    SKIP_EXISTING = "skip_existing"


class ImportPreviewRequest(BaseModel):
    """导入预览请求"""
    import_data: CourseExportData
    strategy: ImportStrategy


class ImportConflictInfo(BaseModel):
    """导入冲突信息"""
    chapter_slug: str
    chapter_title: str
    conflict_type: str  # "new", "exists", "will_update"
    exists_in_db: bool


class ImportPreviewResponse(BaseModel):
    """导入预览响应"""
    success: bool
    preview: bool
    strategy: str
    chapters_to_import: int
    chapters_to_update: int
    chapters_to_skip: int
    conflicts: List[ImportConflictInfo]
    warnings: Optional[List[str]] = None


class ImportResponse(BaseModel):
    """导入响应"""
    success: bool
    preview: bool
    message: Optional[str] = None
    imported_stats: Dict[str, int]
    warnings: Optional[List[str]] = None


class MarkdownImportPreview(BaseModel):
    """Markdown 导入预览"""
    original_title: str
    original_content: str
    proposed_title: str
    proposed_content: str
    changes: List[str]
