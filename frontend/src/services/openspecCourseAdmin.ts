/**
 * OpenSpec 课程后台管理 API 服务
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

export interface ChapterCreate {
  slug: string;
  title: string;
  order?: number;
  content: string;
  chapter_type?: string;
  video_url?: string;
  is_locked?: boolean;
  required_quiz_id?: number;
}

export interface ChapterUpdate {
  title?: string;
  content?: string;
  order?: number;
  chapter_type?: string;
  video_url?: string;
  is_locked?: boolean;
  required_quiz_id?: number;
}

export interface ChapterReorderRequest {
  chapters: Array<{ id: number; order: number }>;
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

export interface QuizQuestionCreate {
  question_text: string;
  question_type?: string;
  correct_answer: string;
  explanation?: string;
  order?: number;
  options: QuizOptionCreate[];
}

export interface QuizQuestionUpdate {
  question_text?: string;
  question_type?: string;
  correct_answer?: string;
  explanation?: string;
  order?: number;
}

export interface QuizOption {
  id: number;
  question_id: number;
  option_text: string;
  option_index: number;
  created_at: string;
}

export interface QuizOptionCreate {
  option_text: string;
  option_index: number;
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

export interface ResourceCreate {
  chapter_id: number;
  resource_type: string;
  title: string;
  content: string;
  extra_data?: Record<string, any>;
}

export interface ResourceUpdate {
  title?: string;
  content?: string;
  resource_type?: string;
  extra_data?: Record<string, any>;
}

// ============ 章节管理 API ============

/**
 * 获取所有章节列表
 */
export const getChapters = async (): Promise<Chapter[]> => {
  const response = await axios.get(`${API_BASE_URL}/chapters`);
  return response.data.chapters;
};

/**
 * 创建章节
 */
export const createChapter = async (data: ChapterCreate): Promise<Chapter> => {
  const response = await axios.post(`${API_BASE_URL}/chapters`, data);
  return response.data;
};

/**
 * 更新章节
 */
export const updateChapter = async (chapterId: number, data: ChapterUpdate): Promise<Chapter> => {
  const response = await axios.put(`${API_BASE_URL}/chapters/${chapterId}`, data);
  return response.data;
};

/**
 * 删除章节
 */
export const deleteChapter = async (chapterId: number): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/chapters/${chapterId}`);
};

/**
 * 批量更新章节顺序
 */
export const reorderChapters = async (data: ChapterReorderRequest): Promise<void> => {
  await axios.put(`${API_BASE_URL}/chapters/reorder`, data);
};

// ============ 测验管理 API ============

/**
 * 获取章节对应的测验
 */
export const getQuizByChapter = async (chapterId: number): Promise<Quiz> => {
  const response = await axios.get(`${API_BASE_URL}/quizzes/chapter/${chapterId}`);
  return response.data;
};

/**
 * 创建测验
 */
export const createQuiz = async (data: QuizCreate): Promise<Quiz> => {
  const response = await axios.post(`${API_BASE_URL}/quizzes`, data);
  return response.data;
};

/**
 * 更新测验
 */
export const updateQuiz = async (quizId: number, data: QuizUpdate): Promise<Quiz> => {
  const response = await axios.put(`${API_BASE_URL}/quizzes/${quizId}`, data);
  return response.data;
};

/**
 * 删除测验
 */
export const deleteQuiz = async (quizId: number): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/quizzes/${quizId}`);
};

// ============ 资源管理 API ============

/**
 * 获取章节的所有资源
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

/**
 * 创建资源
 */
export const createResource = async (data: ResourceCreate): Promise<Resource> => {
  const response = await axios.post(`${API_BASE_URL}/resources`, data);
  return response.data;
};

/**
 * 更新资源
 */
export const updateResource = async (resourceId: number, data: ResourceUpdate): Promise<Resource> => {
  const response = await axios.put(`${API_BASE_URL}/resources/${resourceId}`, data);
  return response.data;
};

/**
 * 删除资源
 */
export const deleteResource = async (resourceId: number): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/resources/${resourceId}`);
};

// ============ 导入/导出管理 API ============

export interface ImportStrategy {
  MERGE: 'merge';
  REPLACE: 'replace';
  SKIP_EXISTING: 'skip_existing';
}

export interface ExportData {
  version: string;
  export_timestamp: string;
  course_id?: number;
  course_title?: string;
  chapters: ExportChapter[];
  export_stats: Record<string, number>;
}

export interface ExportChapter {
  slug: string;
  title: string;
  order: number;
  content: string;
  chapter_type: string;
  video_url?: string;
  is_locked: boolean;
  required_quiz_slug?: string;
  quizzes: ExportQuiz[];
  resources: ExportResource[];
}

export interface ExportQuiz {
  slug?: string;
  title: string;
  passing_score: number;
  questions: ExportQuizQuestion[];
}

export interface ExportQuizQuestion {
  question_text: string;
  question_type: string;
  correct_answer: string;
  explanation?: string;
  order: number;
  options: ExportQuizOption[];
}

export interface ExportQuizOption {
  option_text: string;
  option_index: number;
}

export interface ExportResource {
  resource_type: string;
  title: string;
  content: string;
  extra_data?: Record<string, any>;
}

export interface ImportConflictInfo {
  chapter_slug: string;
  chapter_title: string;
  conflict_type: 'exists' | 'will_update' | 'new';
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
  warnings: string[];
}

export interface ImportResponse {
  success: boolean;
  message: string;
  imported_stats: Record<string, number>;
  warnings: string[];
  errors: string[];
}

export interface MarkdownImportPreview {
  original_title?: string;
  original_content?: string;
  proposed_title: string;
  proposed_content: string;
  changes: string[];
}

/**
 * 导出课程数据为 JSON
 */
export const exportCourseData = async (courseId?: number, courseTitle?: string): Promise<ExportData> => {
  const response = await axios.post(`${API_BASE_URL}/export`, {
    course_id: courseId,
    course_title: courseTitle,
  });
  return response.data.data;
};

/**
 * 导出课程数据为 JSON 文件（下载）
 */
export const downloadCourseExport = async (courseId?: number, courseTitle?: string): Promise<void> => {
  const response = await axios.post(`${API_BASE_URL}/export`, {
    course_id: courseId,
    course_title: courseTitle,
  }, {
    responseType: 'blob',
  });

  const url = window.URL.createObjectURL(new Blob([JSON.stringify(response.data, null, 2)]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `course-export-${new Date().toISOString().split('T')[0]}.json`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

/**
 * 预览导入
 */
export const previewImport = async (importData: ExportData, strategy: 'merge' | 'replace' | 'skip_existing'): Promise<ImportPreviewResponse> => {
  const response = await axios.post(`${API_BASE_URL}/import/preview`, {
    import_data: importData,
    strategy,
  });
  return response.data;
};

/**
 * 导入课程数据
 */
export const importCourseData = async (importData: ExportData, strategy: 'merge' | 'replace' | 'skip_existing'): Promise<ImportResponse> => {
  const response = await axios.post(`${API_BASE_URL}/import`, importData, {
    params: { strategy },
  });
  return response.data;
};

/**
 * 导出章节为 Markdown
 */
export const exportChapterMarkdown = async (chapterId: number): Promise<string> => {
  const response = await axios.get(`${API_BASE_URL}/chapters/${chapterId}/export-md`, {
    responseType: 'text',
  });
  return response.data;
};

/**
 * 导出章节为 Markdown 文件（下载）
 */
export const downloadChapterMarkdown = async (chapterId: number): Promise<void> => {
  const response = await axios.get(`${API_BASE_URL}/chapters/${chapterId}/export-md`, {
    responseType: 'blob',
  });

  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `chapter-${chapterId}.md`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

/**
 * 预览 Markdown 导入
 */
export const previewMarkdownImport = async (chapterId: number, markdownContent: string): Promise<MarkdownImportPreview> => {
  const response = await axios.post(`${API_BASE_URL}/chapters/${chapterId}/import-md/preview`, {
    markdown_content: markdownContent,
  });
  return response.data.preview;
};

/**
 * 从 Markdown 导入章节更新
 */
export const importMarkdownUpdate = async (chapterId: number, markdownContent: string): Promise<any> => {
  const response = await axios.put(`${API_BASE_URL}/chapters/${chapterId}/import-md`, {
    markdown_content: markdownContent,
  });
  return response.data;
};

/**
 * 导出课程数据为 ZIP 文件（包含 JSON + 所有章节 Markdown 文件）
 */
export const downloadCourseExportZip = async (courseId?: number, courseTitle?: string): Promise<void> => {
  const response = await axios.get(`${API_BASE_URL}/export-zip`, {
    params: {
      course_id: courseId,
      course_title: courseTitle,
    },
    responseType: 'blob',
  });

  const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/zip' }));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `course-export-${new Date().toISOString().split('T')[0]}.zip`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
