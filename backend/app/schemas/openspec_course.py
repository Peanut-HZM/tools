"""
OpenSpec 课程 Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============ 章节相关 Schemas ============

class ChapterBase(BaseModel):
    """章节基础模型"""
    slug: str
    title: str
    order: int = 0
    content: str
    chapter_type: str = "story"
    video_url: Optional[str] = None
    is_locked: bool = False
    required_quiz_id: Optional[int] = None


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
    option_text: str
    option_index: int


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
    question_text: str
    question_type: str = "single"
    correct_answer: str
    explanation: Optional[str] = None
    order: int = 0


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
    chapter_id: int
    title: str
    passing_score: int = 60


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
    status: str = "not_started"
    quiz_score: Optional[float] = None
    quiz_passed: bool = False
    video_progress: int = 0


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
    id: int
    user_id: str
    chapter_id: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

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
    chapter_id: int
    resource_type: str
    title: str
    content: str
    extra_data: Optional[Dict[str, Any]] = None


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
