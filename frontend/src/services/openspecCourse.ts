/**
 * OpenSpec 课程 API 服务
 */
import axios from 'axios';

const API_BASE_URL = '/api/openspec-course';

// ============ 类型定义 ============

export interface Chapter {
  id: number;
  slug: string;
  title: string;
  order: number;
  content: string;
  chapter_type: string;
  video_url?: string;
  is_locked: boolean;
  required_quiz_id?: number;
  created_at: string;
  updated_at: string;
}

export interface ChapterDetail extends Chapter {
  quiz?: Quiz;
  resources: Resource[];
  user_progress?: UserProgress;
}

export interface Quiz {
  id: number;
  chapter_id: number;
  title: string;
  passing_score: number;
  created_at: string;
  updated_at: string;
  questions: QuizQuestion[];
}

export interface QuizQuestion {
  id: number;
  quiz_id: number;
  question_text: string;
  question_type: string;
  correct_answer: string;
  explanation?: string;
  order: number;
  created_at: string;
  options: QuizOption[];
}

export interface QuizOption {
  id: number;
  question_id: number;
  option_text: string;
  option_index: number;
  created_at: string;
}

export interface UserProgress {
  id: number;
  user_id: string;
  chapter_id: number;
  status: 'not_started' | 'in_progress' | 'completed';
  quiz_score?: number;
  quiz_passed: boolean;
  completed_at?: string;
  video_progress: number;
  created_at: string;
  updated_at: string;
}

export interface Resource {
  id: number;
  chapter_id: number;
  resource_type: string;
  title: string;
  content: string;
  extra_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CourseProgressSummary {
  total_chapters: number;
  completed_chapters: number;
  progress_percentage: number;
  chapters: UserProgress[];
}

export interface QuizSubmitRequest {
  answers: Record<number, number[]>;
}

export interface QuizResult {
  quiz_id: number;
  total_questions: number;
  correct_count: number;
  score: number;
  passed: boolean;
  details: Array<{
    question_id: number;
    question_text: string;
    correct_answer: number[];
    user_answer: number[];
    is_correct: boolean;
    explanation?: string;
    correct_option_texts: string[];
    user_option_texts: string[];
  }>;
}

// ============ API 方法 ============

/**
 * 获取所有章节列表
 */
export const getChapters = async (): Promise<Chapter[]> => {
  const response = await axios.get(`${API_BASE_URL}/chapters`);
  return response.data.chapters;
};

/**
 * 获取章节详情
 */
export const getChapterDetail = async (chapterId: number): Promise<ChapterDetail> => {
  const response = await axios.get(`${API_BASE_URL}/chapters/${chapterId}`);
  return response.data;
};

/**
 * 获取章节测验
 */
export const getQuizByChapter = async (chapterId: number): Promise<Quiz> => {
  const response = await axios.get(`${API_BASE_URL}/quizzes/chapter/${chapterId}`);
  return response.data;
};

/**
 * 提交测验答案
 */
export const submitQuiz = async (
  quizId: number,
  answers: Record<number, number[]>
): Promise<QuizResult> => {
  const response = await axios.post(`${API_BASE_URL}/quizzes/${quizId}/submit`, {
    answers,
  });
  return response.data;
};

/**
 * 获取用户课程进度汇总
 */
export const getCourseProgress = async (): Promise<CourseProgressSummary> => {
  const response = await axios.get(`${API_BASE_URL}/progress`);
  return response.data;
};

/**
 * 获取章节进度
 */
export const getChapterProgress = async (chapterId: number): Promise<UserProgress> => {
  const response = await axios.get(`${API_BASE_URL}/progress/chapter/${chapterId}`);
  return response.data;
};

/**
 * 更新章节进度
 */
export const updateChapterProgress = async (
  chapterId: number,
  data: Partial<UserProgress>
): Promise<UserProgress> => {
  const response = await axios.put(`${API_BASE_URL}/progress/chapter/${chapterId}`, data);
  return response.data;
};

/**
 * 获取章节资源
 */
export const getChapterResources = async (chapterId: number): Promise<Resource[]> => {
  const response = await axios.get(`${API_BASE_URL}/resources/chapter/${chapterId}`);
  return response.data;
};

/**
 * 获取资源详情
 */
export const getResource = async (resourceId: number): Promise<Resource> => {
  const response = await axios.get(`${API_BASE_URL}/resources/${resourceId}`);
  return response.data;
};
