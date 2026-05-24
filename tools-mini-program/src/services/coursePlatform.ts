import { request } from './request';

export interface Course {
  id: number;
  title: string;
  slug: string;
  description: string;
  cover_image?: string;
  status: string;
  price: number;
  category_id?: number;
  instructor_id?: number;
  created_at: string;
  updated_at: string;
}

export interface CourseChapter {
  id: number;
  title: string;
  order: number;
  content?: string;
  video_url?: string;
}

export interface CourseDetail extends Course {
  chapters: CourseChapter[];
  statistics?: {
    view_count: number;
    enroll_count: number;
    like_count: number;
    avg_rating: number;
  };
}

export interface CourseListResponse {
  courses: Course[];
  total: number;
  page: number;
  limit: number;
}

export interface CourseCategory {
  id: number;
  name: string;
  slug: string;
  icon?: string;
  children: CourseCategory[];
}

export interface EnrollmentResponse {
  id: number;
  user_id: string;
  course_id: number;
  status: string;
  progress_percent: number;
  enrolled_at: string;
  completed_at?: string;
}

export const coursePlatformApi = {
  getCourses: async (params: {
    category?: string;
    search?: string;
    sort?: string;
    page?: number;
    limit?: number;
  } = {}): Promise<CourseListResponse> => {
    const qs = new URLSearchParams();
    if (params.category) qs.append('category', params.category);
    if (params.search) qs.append('search', params.search);
    if (params.sort) qs.append('sort', params.sort);
    if (params.page) qs.append('page', String(params.page));
    if (params.limit) qs.append('limit', String(params.limit));
    return request(`/courses?${qs.toString()}`, { needAuth: false });
  },

  getCourseDetail: async (slug: string): Promise<CourseDetail> => {
    return request(`/courses/${slug}`, { needAuth: false });
  },

  getCategories: async (): Promise<{ categories: CourseCategory[] }> => {
    return request('/course-categories', { needAuth: false });
  },

  enroll: async (courseId: number): Promise<EnrollmentResponse> => {
    return request(`/courses/${courseId}/enroll`, {
      method: 'POST',
      needAuth: true,
    });
  },

  getMyCourses: async (): Promise<{
    courses: { course: Course; enrollment: EnrollmentResponse; completed_chapters: number; total_chapters: number }[];
    total: number;
  }> => {
    return request('/my-courses', { needAuth: true });
  },

  likeCourse: async (courseId: number): Promise<any> => {
    return request(`/courses/${courseId}/like`, {
      method: 'POST',
      needAuth: true,
    });
  },

  bookmarkCourse: async (courseId: number): Promise<any> => {
    return request(`/courses/${courseId}/bookmark`, {
      method: 'POST',
      needAuth: true,
    });
  },
};
