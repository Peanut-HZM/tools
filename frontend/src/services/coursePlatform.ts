/**
 * 课程平台 API 服务
 */
import axios from 'axios';

const API_BASE = '/api';

export interface Course {
  id: number;
  slug: string;
  title: string;
  description: string;
  cover_image?: string | null;
  category?: {
    id: number;
    name: string;
    slug: string;
  } | null;
  statistics?: {
    view_count: number;
    enroll_count: number;
    like_count: number;
    bookmark_count: number;
    review_count: number;
    avg_rating: number;
  } | null;
}

export interface CourseDetail extends Course {
  chapters: CourseChapter[];
  statistics: {
    view_count: number;
    enroll_count: number;
    like_count: number;
    bookmark_count: number;
    review_count: number;
    avg_rating: number;
  };
}

export interface CourseChapter {
  id: number;
  slug: string;
  title: string;
  order: number;
  content: string;
  chapter_type: string;
  video_url?: string | null;
  is_locked: boolean;
  duration_minutes: number;
}

export interface CourseCategory {
  id: number;
  name: string;
  slug: string;
  icon?: string | null;
  children?: CourseCategory[];
}

export interface Enrollment {
  id: number;
  course_id: number;
  status: string;
  progress_percent: number;
  enrolled_at: string;
}

export interface Review {
  id: number;
  user_id: string;
  rating: number;
  comment?: string | null;
  created_at: string;
}

// ============ 课程列表接口 ============

export const getCourseList = async (params?: {
  category?: string;
  search?: string;
  sort?: string;
  page?: number;
  limit?: number;
}): Promise<{ courses: Course[]; total: number; page: number; limit: number }> => {
  const response = await axios.get(`${API_BASE}/courses`, { params });
  return response.data;
};

export const getCourseDetail = async (slug: string): Promise<CourseDetail> => {
  const response = await axios.get(`${API_BASE}/courses/${slug}`);
  return response.data;
};

export const getCourseCategories = async (): Promise<CourseCategory[]> => {
  const response = await axios.get(`${API_BASE}/course-categories`);
  return response.data;
};

// ============ 用户课程接口 ============

export const enrollCourse = async (courseId: number): Promise<Enrollment> => {
  const response = await axios.post(`${API_BASE}/courses/${courseId}/enroll`);
  return response.data;
};

export const getMyCourses = async (): Promise<{ courses: any[]; total: number }> => {
  const response = await axios.get(`${API_BASE}/my-courses`);
  return response.data;
};

// ============ 互动接口 ============

export const likeCourse = async (courseId: number): Promise<any> => {
  const response = await axios.post(`${API_BASE}/courses/${courseId}/like`);
  return response.data;
};

export const bookmarkCourse = async (courseId: number): Promise<any> => {
  const response = await axios.post(`${API_BASE}/courses/${courseId}/bookmark`);
  return response.data;
};

export const getCourseStatistics = async (courseId: number): Promise<any> => {
  const response = await axios.get(`${API_BASE}/courses/${courseId}/statistics`);
  return response.data;
};

// ============ 评价接口 ============

export const getCourseReviews = async (
  courseId: number,
  page?: number,
  limit?: number
): Promise<Review[]> => {
  const response = await axios.get(`${API_BASE}/courses/${courseId}/reviews`, {
    params: { page, limit },
  });
  return response.data;
};

export const submitReview = async (
  courseId: number,
  rating: number,
  comment?: string
): Promise<Review> => {
  const response = await axios.post(`${API_BASE}/courses/${courseId}/reviews`, {
    rating,
    comment,
  });
  return response.data;
};

// ============ 管理后台接口 ============

export const getAdminCourses = async (params?: {
  status?: string;
  search?: string;
  page?: number;
  limit?: number;
}): Promise<{ courses: Course[]; total: number; page: number; limit: number }> => {
  const response = await axios.get(`${API_BASE}/admin/courses`, { params });
  return response.data;
};

export const createCourse = async (courseData: Partial<Course>): Promise<Course> => {
  const response = await axios.post(`${API_BASE}/admin/courses`, courseData);
  return response.data;
};

export const updateCourse = async (
  courseId: number,
  courseData: Partial<Course>
): Promise<Course> => {
  const response = await axios.put(`${API_BASE}/admin/courses/${courseId}`, courseData);
  return response.data;
};

export const deleteCourse = async (courseId: number): Promise<void> => {
  await axios.delete(`${API_BASE}/admin/courses/${courseId}`);
};

export const publishCourse = async (courseId: number, publish: boolean): Promise<void> => {
  await axios.post(`${API_BASE}/admin/courses/${courseId}/publish`, null, {
    params: { publish },
  });
};

/**
 * 获取单个课程详情（管理后台）
 */
export const getCourse = async (courseId: number): Promise<Course> => {
  const response = await axios.get(`${API_BASE}/admin/courses/${courseId}`);
  return response.data;
};

/**
 * 获取章节列表（管理后台）
 */
export const getChapters = async (courseId: number): Promise<CourseChapter[]> => {
  const response = await axios.get(`${API_BASE}/admin/courses/${courseId}/chapters`);
  return response.data;
};

/**
 * 创建章节（管理后台）
 */
export const createChapter = async (
  courseId: number,
  chapterData: Partial<CourseChapter>
): Promise<CourseChapter> => {
  const response = await axios.post(
    `${API_BASE}/admin/courses/${courseId}/chapters`,
    chapterData
  );
  return response.data;
};

/**
 * 更新章节（管理后台）
 */
export const updateChapter = async (
  courseId: number,
  chapterId: number,
  chapterData: Partial<CourseChapter>
): Promise<CourseChapter> => {
  const response = await axios.put(
    `${API_BASE}/admin/courses/${courseId}/chapters/${chapterId}`,
    chapterData
  );
  return response.data;
};

/**
 * 删除章节（管理后台）
 */
export const deleteChapter = async (courseId: number, chapterId: number): Promise<void> => {
  await axios.delete(`${API_BASE}/admin/courses/${courseId}/chapters/${chapterId}`);
};

/**
 * 重新排序章节（管理后台）
 */
export const reorderChapters = async (
  courseId: number,
  chapterOrders: { id: number; order: number }[]
): Promise<void> => {
  await axios.put(`${API_BASE}/admin/courses/${courseId}/chapters/reorder`, chapterOrders);
};

// ============ 课程导入导出接口 ============

export interface ExportData {
  version: string;
  course_id?: number;
  course_title: string;
  export_timestamp: string;
  export_stats: {
    total_chapters: number;
    total_quizzes: number;
    total_questions: number;
    total_resources: number;
  };
  chapters: ExportChapter[];
}

export interface ExportChapter {
  slug: string;
  title: string;
  order: number;
  content: string;
  chapter_type: string;
  video_url?: string | null;
  is_locked: boolean;
  quizzes: ExportQuiz[];
  resources: ExportResource[];
}

export interface ExportQuiz {
  title: string;
  passing_score: number;
  questions: ExportQuestion[];
}

export interface ExportQuestion {
  question_text: string;
  question_type: string;
  correct_answer: string;
  explanation?: string;
  order: number;
  options: ExportOption[];
}

export interface ExportOption {
  option_text: string;
  option_index: number;
}

export interface ExportResource {
  resource_type: string;
  title: string;
  content: string;
  extra_data?: Record<string, any> | null;
}

export interface ImportPreviewRequest {
  import_data: ExportData;
  strategy: 'merge' | 'replace' | 'skip_existing';
}

export interface ImportConflictInfo {
  chapter_slug: string;
  chapter_title: string;
  conflict_type: 'new' | 'exists' | 'will_update';
  exists_in_db: boolean;
}

export interface ImportPreviewResponse {
  success: boolean;
  preview: boolean;
  strategy: string;
  chapters_to_import: number;
  chapters_to_update: number;
  chapters_to_skip: number;
  conflicts: ImportConflictInfo[];
  warnings?: string[];
}

export interface ImportResponse {
  success: boolean;
  preview: boolean;
  message?: string;
  imported_stats: {
    chapters_imported: number;
    chapters_updated: number;
    chapters_skipped: number;
    quizzes_imported: number;
    questions_imported: number;
    options_imported: number;
    resources_imported: number;
  };
  warnings?: string[];
}

/**
 * 导出课程数据
 */
export const exportCourseData = async (courseId?: number): Promise<ExportData> => {
  const response = await axios.post(`${API_BASE}/admin/courses/export`, null, {
    params: { course_id: courseId },
  });
  return response.data;
};

/**
 * 下载课程 JSON 文件
 */
export const downloadCourseExport = async (courseId?: number): Promise<void> => {
  const response = await axios.post(`${API_BASE}/admin/courses/export-download`, null, {
    params: { course_id: courseId },
    responseType: 'blob',
  });

  // 创建下载链接
  const blob = new Blob([response.data], { type: 'application/json' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  const timestamp = new Date().toISOString().split('T')[0];
  link.setAttribute('download', `course-export-${timestamp}.json`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

/**
 * 预览课程导入
 */
export const previewImport = async (
  importData: ExportData,
  strategy: 'merge' | 'replace' | 'skip_existing'
): Promise<ImportPreviewResponse> => {
  const response = await axios.post(`${API_BASE}/admin/courses/import/preview`, {
    import_data: importData,
    strategy: strategy,
  });
  return response.data;
};

/**
 * 导入课程数据
 */
export const importCourseData = async (
  importData: ExportData,
  strategy: 'merge' | 'replace' | 'skip_existing'
): Promise<ImportResponse> => {
  const response = await axios.post(`${API_BASE}/admin/courses/import`, importData, {
    params: { strategy: strategy },
  });
  return response.data;
};

/**
 * 导出章节 Markdown
 */
export const exportChapterMarkdown = async (courseId: number, chapterId: number): Promise<string> => {
  const response = await axios.post(`${API_BASE}/admin/courses/${courseId}/chapters/${chapterId}/export-md`);
  return response.data.markdown;
};

/**
 * 预览 Markdown 导入
 */
export const previewMarkdownImport = async (
  courseId: number,
  chapterId: number,
  markdownContent: string
): Promise<any> => {
  const response = await axios.post(
    `${API_BASE}/admin/courses/${courseId}/chapters/${chapterId}/import-md/preview`,
    markdownContent,
    {
      headers: { 'Content-Type': 'text/plain' },
    }
  );
  return response.data;
};

/**
 * 导入 Markdown 更新
 */
export const importMarkdownUpdate = async (
  courseId: number,
  chapterId: number,
  markdownContent: string
): Promise<any> => {
  const response = await axios.post(
    `${API_BASE}/admin/courses/${courseId}/chapters/${chapterId}/import-md`,
    markdownContent,
    {
      headers: { 'Content-Type': 'text/plain' },
    }
  );
  return response.data;
};

// ============ 测验和资源类型定义 ============

export interface CourseQuiz {
  id: number;
  chapter_id: number;
  title: string;
  passing_score: number;
  created_at: string;
  updated_at: string;
  questions: CourseQuizQuestion[];
}

export interface CourseQuizQuestion {
  id: number;
  quiz_id: number;
  question_text: string;
  question_type: 'single' | 'multiple' | 'true_false';
  correct_answer: string;
  explanation?: string;
  order: number;
  created_at: string;
  options: CourseQuizOption[];
}

export interface CourseQuizOption {
  id: number;
  question_id: number;
  option_text: string;
  option_index: number;
  created_at: string;
}

export interface CourseResource {
  id: number;
  chapter_id: number;
  resource_type: string;
  title: string;
  content: string;
  extra_data?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface QuizCreate {
  chapter_id: number;
  title: string;
  passing_score?: number;
  questions?: QuizQuestionCreate[];
}

export interface QuizUpdate {
  title?: string;
  passing_score?: number;
}

export interface QuizQuestionCreate {
  question_text: string;
  question_type?: string;
  correct_answer: string;
  explanation?: string;
  order?: number;
  options: QuizOptionCreate[];
}

export interface QuizOptionCreate {
  option_text: string;
  option_index: number;
}

export interface ResourceCreate {
  chapter_id: number;
  resource_type: string;
  title: string;
  content: string;
  extra_data?: Record<string, any> | null;
}

export interface ResourceUpdate {
  resource_type?: string;
  title?: string;
  content?: string;
  extra_data?: Record<string, any> | null;
}
