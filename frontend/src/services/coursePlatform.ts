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
  page?: number;
  limit?: number;
}): Promise<{ courses: Course[]; total: number }> => {
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

export const deleteChapter = async (courseId: number, chapterId: number): Promise<void> => {
  await axios.delete(`${API_BASE}/admin/courses/${courseId}/chapters/${chapterId}`);
};

export const reorderChapters = async (
  courseId: number,
  chapterOrders: { id: number; order: number }[]
): Promise<void> => {
  await axios.put(`${API_BASE}/admin/courses/${courseId}/chapters/reorder`, chapterOrders);
};
