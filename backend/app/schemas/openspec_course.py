"""
OpenSpec 课程 Schemas
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re
from enum import Enum


class ImportStrategy(str, Enum):
    """导入策略"""
    MERGE = "merge"  # 合并：跳过已存在的 slug，导入新的
    REPLACE = "replace"  # 替换：更新已存在的 slug，导入新的
    SKIP_EXISTING = "skip_existing"  # 完全跳过已存在的 slug


# ============ 章节相关 Schemas ============

class ChapterBase(BaseModel):
    """章节基础模型"""
    slug: str = Field(..., description="章节标识符（唯一，用于 URL）", min_length=1, max_length=100)
    title: str = Field(..., description="章节标题", min_length=1, max_length=200)
    order: int = Field(default=0, description="章节顺序", ge=0)
    content: str = Field(..., description="章节内容（Markdown 格式）", min_length=1)
    chapter_type: str = Field(default="story", description="章节类型：story-故事章，lesson-课程章，quiz-only-纯测验章，code-代码章，video-视频章")
    video_url: Optional[str] = Field(default=None, description="视频外链 URL", max_length=500)
    is_locked: bool = Field(default=False, description="是否锁定（锁定后用户无法学习）")
    required_quiz_id: Optional[int] = Field(default=None, description="关联的测验 ID")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """验证 slug 格式：只允许小写字母、数字、连字符和下划线"""
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError("slug 只允许包含小写字母、数字、连字符 (-) 和下划线 (_)")
        return v

    @field_validator("chapter_type")
    @classmethod
    def validate_chapter_type(cls, v: str) -> str:
        """验证章节类型"""
        allowed_types = ["story", "lesson", "quiz-only", "code", "video"]
        if v not in allowed_types:
            raise ValueError(f"章节类型必须是 {', '.join(allowed_types)} 之一")
        return v


class ChapterCreate(ChapterBase):
    """创建章节请求"""
    pass


class ChapterUpdate(BaseModel):
    """更新章节请求"""
    title: Optional[str] = None
    content: Optional[str] = None
    order: Optional[int] = None
    chapter_type: Optional[str] = None
    video_url: Optional[str] = None
    is_locked: Optional[bool] = None
    required_quiz_id: Optional[int] = None


class ChapterResponse(ChapterBase):
    """章节响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 测验相关 Schemas ============

class QuizOptionBase(BaseModel):
    """选项基础模型"""
    option_text: str = Field(..., description="选项内容", min_length=1)
    option_index: int = Field(..., description="选项索引 (0=A, 1=B, 2=C, 3=D)", ge=0, le=25)

    @field_validator("option_text")
    @classmethod
    def validate_option_text(cls, v: str) -> str:
        """验证选项内容"""
        if not v.strip():
            raise ValueError("选项内容不能为空")
        return v.strip()


class QuizOptionCreate(QuizOptionBase):
    """创建选项请求"""
    pass


class QuizOptionResponse(QuizOptionBase):
    """选项响应"""
    id: int
    question_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class QuizQuestionBase(BaseModel):
    """题目基础模型"""
    question_text: str = Field(..., description="题目内容", min_length=1)
    question_type: str = Field(default="single", description="题目类型：single-单选题，multiple-多选题")
    correct_answer: str = Field(..., description="正确答案（选项索引，逗号分隔）")
    explanation: Optional[str] = Field(default=None, description="答案解析")
    order: int = Field(default=0, description="题目顺序", ge=0)

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, v: str) -> str:
        """验证题目类型"""
        allowed_types = ["single", "multiple"]
        if v not in allowed_types:
            raise ValueError(f"题目类型必须是 {', '.join(allowed_types)} 之一")
        return v

    @field_validator("correct_answer")
    @classmethod
    def validate_correct_answer(cls, v: str) -> str:
        """验证正确答案格式"""
        if not v.strip():
            raise ValueError("正确答案不能为空")
        # 验证格式：应该是逗号分隔的数字
        parts = v.split(",")
        for part in parts:
            try:
                int(part.strip())
            except ValueError:
                raise ValueError("正确答案必须是逗号分隔的数字索引")
        return v


class QuizQuestionCreate(QuizQuestionBase):
    """创建题目请求"""
    options: List[QuizOptionCreate]


class QuizQuestionResponse(QuizQuestionBase):
    """题目响应"""
    id: int
    quiz_id: int
    created_at: datetime
    options: List[QuizOptionResponse] = []

    class Config:
        from_attributes = True


class QuizBase(BaseModel):
    """测验基础模型"""
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


class QuizCreate(QuizBase):
    """创建测验请求"""
    questions: List[QuizQuestionCreate] = []


class QuizUpdate(BaseModel):
    """更新测验请求"""
    title: Optional[str] = None
    passing_score: Optional[int] = None


class QuizResponse(QuizBase):
    """测验响应"""
    id: int
    created_at: datetime
    updated_at: datetime
    questions: List[QuizQuestionResponse] = []

    class Config:
        from_attributes = True


class QuizSubmitRequest(BaseModel):
    """提交测验请求"""
    answers: Dict[int, List[int]]  # question_id -> [option_index, ...]


class QuizResult(BaseModel):
    """测验结果"""
    quiz_id: int
    total_questions: int
    correct_count: int
    score: float
    passed: bool
    details: List[Dict[str, Any]]  # 每道题的详情


# ============ 进度相关 Schemas ============

class UserProgressBase(BaseModel):
    """进度基础模型"""
    status: str = Field(default="not_started", description="学习状态：not_started-未开始，in_progress-进行中，completed-已完成")
    quiz_score: Optional[float] = Field(default=None, description="测验得分 (0-100)", ge=0, le=100)
    quiz_passed: bool = Field(default=False, description="是否通过测验")
    video_progress: int = Field(default=0, description="视频观看进度 (百分比 0-100)", ge=0, le=100)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """验证学习状态"""
        allowed_statuses = ["not_started", "in_progress", "completed"]
        if v not in allowed_statuses:
            raise ValueError(f"学习状态必须是 {', '.join(allowed_statuses)} 之一")
        return v


class UserProgressCreate(UserProgressBase):
    """创建进度请求"""
    user_id: str
    chapter_id: int


class UserProgressUpdate(BaseModel):
    """更新进度请求"""
    status: Optional[str] = None
    quiz_score: Optional[float] = None
    quiz_passed: Optional[bool] = None
    completed_at: Optional[datetime] = None
    video_progress: Optional[int] = None


class UserProgressResponse(UserProgressBase):
    """进度响应"""
    id: Optional[int] = None
    user_id: str
    chapter_id: int
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CourseProgressSummary(BaseModel):
    """课程进度汇总"""
    total_chapters: int
    completed_chapters: int
    progress_percentage: float
    chapters: List[UserProgressResponse]


# ============ 资源相关 Schemas ============

class ResourceBase(BaseModel):
    """资源基础模型"""
    chapter_id: int = Field(..., description="关联的章节 ID", gt=0)
    resource_type: str = Field(..., description="资源类型：code-代码示例，contrast-对比材料，video-视频，template-模板")
    title: str = Field(..., description="资源标题", min_length=1, max_length=200)
    content: str = Field(..., description="资源内容（Markdown 格式）", min_length=1)
    extra_data: Optional[Dict[str, Any]] = Field(default=None, description="额外元数据（JSON 对象）")

    @field_validator("resource_type")
    @classmethod
    def validate_resource_type(cls, v: str) -> str:
        """验证资源类型"""
        allowed_types = ["code", "contrast", "video", "template", "code_sample"]
        if v not in allowed_types:
            raise ValueError(f"资源类型必须是 {', '.join(allowed_types)} 之一")
        return v


class ResourceCreate(ResourceBase):
    """创建资源请求"""
    pass


class ResourceUpdate(BaseModel):
    """更新资源请求"""
    title: Optional[str] = None
    content: Optional[str] = None
    resource_type: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class ResourceResponse(ResourceBase):
    """资源响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 组合响应 ============

class ChapterDetailResponse(ChapterResponse):
    """章节详情响应（包含测验和资源）"""
    quiz: Optional[QuizResponse] = None
    resources: List[ResourceResponse] = []
    user_progress: Optional[UserProgressResponse] = None


class CourseListResponse(BaseModel):
    """课程列表响应"""
    chapters: List[ChapterResponse]
    total: int


class ChapterReorderRequest(BaseModel):
    """批量更新章节顺序请求"""
    chapters: List[Dict[str, int]] = Field(..., description="章节顺序列表，每项包含 id 和 order")

    @field_validator("chapters")
    @classmethod
    def validate_chapters(cls, v: List[Dict[str, int]]) -> List[Dict[str, int]]:
        """验证章节顺序列表"""
        if not v:
            raise ValueError("章节列表不能为空")
        for item in v:
            if "id" not in item or "order" not in item:
                raise ValueError("每项必须包含 id 和 order 字段")
            if item["id"] <= 0:
                raise ValueError("章节 ID 必须大于 0")
            if item["order"] < 0:
                raise ValueError("章节顺序必须大于等于 0")
        return v


# ============ 导入/导出相关 Schemas ============

class ExportedQuizOption(BaseModel):
    """导出的测验选项"""
    option_text: str
    option_index: int


class ExportedQuizQuestion(BaseModel):
    """导出的测验题目"""
    question_text: str
    question_type: str
    correct_answer: str
    explanation: Optional[str] = None
    order: int = 0
    options: List[ExportedQuizOption]


class ExportedQuiz(BaseModel):
    """导出的测验"""
    slug: Optional[str] = None  # 用于导入时匹配
    title: str
    passing_score: int = 60
    questions: List[ExportedQuizQuestion] = []


class ExportedResource(BaseModel):
    """导出的资源"""
    resource_type: str
    title: str
    content: str
    extra_data: Optional[Dict[str, Any]] = None


class ExportedChapter(BaseModel):
    """导出的章节"""
    slug: str
    title: str
    order: int
    content: str
    chapter_type: str = "story"
    video_url: Optional[str] = None
    is_locked: bool = False
    required_quiz_slug: Optional[str] = None  # 使用 slug 而非 ID 进行导入时匹配
    quizzes: List[ExportedQuiz] = []
    resources: List[ExportedResource] = []


class CourseExportData(BaseModel):
    """课程导出数据"""
    version: str = "1.0"
    export_timestamp: str
    course_id: Optional[int] = None
    course_title: Optional[str] = None
    chapters: List[ExportedChapter]
    export_stats: Dict[str, int]


class CourseExportResponse(BaseModel):
    """导出响应"""
    success: bool
    data: CourseExportData
    filename: str


class ChapterReorderItem(BaseModel):
    """章节顺序项"""
    id: int
    order: int


class ImportPreviewRequest(BaseModel):
    """导入预览请求"""
    import_data: CourseExportData
    strategy: ImportStrategy = ImportStrategy.MERGE


class ImportConflictInfo(BaseModel):
    """冲突信息"""
    chapter_slug: str
    chapter_title: str
    conflict_type: str  # "exists" | "new"
    exists_in_db: bool


class ImportPreviewResponse(BaseModel):
    """导入预览响应"""
    success: bool
    preview: bool = True
    strategy: str
    chapters_to_import: int
    chapters_to_update: int
    chapters_to_skip: int
    conflicts: List[ImportConflictInfo] = []
    warnings: List[str] = []


class ImportResponse(BaseModel):
    """导入响应"""
    success: bool
    message: str
    imported_stats: Dict[str, int]
    warnings: List[str] = []
    errors: List[str] = []


class MarkdownImportPreview(BaseModel):
    """Markdown 导入预览"""
    original_title: Optional[str] = None
    original_content: Optional[str] = None
    proposed_title: str
    proposed_content: str
    changes: List[str]
