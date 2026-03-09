/**
 * 课程管理状态管理
 */
import { create } from 'zustand';
import {
  getChapters,
  createChapter,
  updateChapter,
  deleteChapter,
  reorderChapters,
  getQuizByChapter,
  createQuiz,
  updateQuiz,
  deleteQuiz,
  getChapterResources,
  createResource,
  updateResource,
  deleteResource,
  type Chapter,
  type ChapterCreate,
  type ChapterUpdate,
  type Quiz,
  type QuizCreate,
  type QuizUpdate,
  type Resource,
  type ResourceCreate,
  type ResourceUpdate,
} from '../services/openspecCourseAdmin';
import {
  getAdminCourses,
  createCourse,
  updateCourse,
  deleteCourse,
  publishCourse,
  type Course,
} from '../services/coursePlatform';

interface ChapterState {
  chapters: Chapter[];
  loading: boolean;
  error: string | null;
  selectedChapterId: number | null;

  // Actions
  fetchChapters: () => Promise<void>;
  createChapter: (data: ChapterCreate) => Promise<Chapter>;
  updateChapter: (chapterId: number, data: ChapterUpdate) => Promise<Chapter>;
  deleteChapter: (chapterId: number) => Promise<void>;
  reorderChapters: (chapters: Array<{ id: number; order: number }>) => Promise<void>;
  selectChapter: (chapterId: number | null) => void;
  clearError: () => void;
}

interface QuizState {
  quizzes: Record<number, Quiz>; // chapterId -> Quiz
  loading: boolean;
  error: string | null;

  // Actions
  fetchQuiz: (chapterId: number) => Promise<Quiz>;
  createQuiz: (chapterId: number, data: QuizCreate) => Promise<Quiz>;
  updateQuiz: (quizId: number, data: QuizUpdate) => Promise<Quiz>;
  deleteQuiz: (quizId: number) => Promise<void>;
  clearError: () => void;
}

interface ResourceState {
  resources: Record<number, Resource[]>; // chapterId -> Resource[]
  loading: boolean;
  error: string | null;

  // Actions
  fetchResources: (chapterId: number) => Promise<Resource[]>;
  createResource: (data: ResourceCreate) => Promise<Resource>;
  updateResource: (resourceId: number, data: ResourceUpdate) => Promise<Resource>;
  deleteResource: (resourceId: number) => Promise<void>;
  clearError: () => void;
}

// ============ 章节 Store ============

export const useChapterStore = create<ChapterState>((set, get) => ({
  chapters: [],
  loading: false,
  error: null,
  selectedChapterId: null,

  fetchChapters: async () => {
    set({ loading: true, error: null });
    try {
      const chapters = await getChapters();
      set({ chapters, loading: false });
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : '获取章节列表失败'
      });
    }
  },

  createChapter: async (data) => {
    const chapter = await createChapter(data);
    set((state) => ({ chapters: [...state.chapters, chapter] }));
    return chapter;
  },

  updateChapter: async (chapterId, data) => {
    const chapter = await updateChapter(chapterId, data);
    set((state) => ({
      chapters: state.chapters.map((c) => (c.id === chapterId ? chapter : c)),
    }));
    return chapter;
  },

  deleteChapter: async (chapterId) => {
    await deleteChapter(chapterId);
    set((state) => ({
      chapters: state.chapters.filter((c) => c.id !== chapterId),
      selectedChapterId: state.selectedChapterId === chapterId ? null : state.selectedChapterId,
    }));
  },

  reorderChapters: async (chapters) => {
    await reorderChapters({ chapters });
    // Optimistic update
    set((state) => ({
      chapters: state.chapters.map((chapter) => {
        const reorder = chapters.find((r) => r.id === chapter.id);
        return reorder ? { ...chapter, order: reorder.order } : chapter;
      }),
    }));
  },

  selectChapter: (chapterId) => {
    set({ selectedChapterId: chapterId });
  },

  clearError: () => {
    set({ error: null });
  },
}));

// ============ 测验 Store ============

export const useQuizStore = create<QuizState>((set, get) => ({
  quizzes: {},
  loading: false,
  error: null,

  fetchQuiz: async (chapterId) => {
    set({ loading: true, error: null });
    try {
      const quiz = await getQuizByChapter(chapterId);
      set((state) => ({
        quizzes: { ...state.quizzes, [chapterId]: quiz },
        loading: false
      }));
      return quiz;
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : '获取测验失败'
      });
      throw error;
    }
  },

  createQuiz: async (chapterId, data) => {
    const quiz = await createQuiz(data);
    set((state) => ({
      quizzes: { ...state.quizzes, [chapterId]: quiz },
    }));
    return quiz;
  },

  updateQuiz: async (quizId, data) => {
    const quiz = await updateQuiz(quizId, data);
    set((state) => ({
      quizzes: Object.fromEntries(
        Object.entries(state.quizzes).map(([key, value]) =>
          value.id === quizId ? [key, quiz] : [key, value]
        )
      ),
    }));
    return quiz;
  },

  deleteQuiz: async (quizId) => {
    await deleteQuiz(quizId);
    set((state) => {
      const newQuizzes = { ...state.quizzes };
      Object.keys(newQuizzes).forEach((key) => {
        if (newQuizzes[parseInt(key)]?.id === quizId) {
          delete newQuizzes[parseInt(key)];
        }
      });
      return { quizzes: newQuizzes };
    });
  },

  clearError: () => {
    set({ error: null });
  },
}));

// ============ 资源 Store ============

export const useResourceStore = create<ResourceState>((set, get) => ({
  resources: {},
  loading: false,
  error: null,

  fetchResources: async (chapterId) => {
    set({ loading: true, error: null });
    try {
      const resources = await getChapterResources(chapterId);
      set((state) => ({
        resources: { ...state.resources, [chapterId]: resources },
        loading: false
      }));
      return resources;
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : '获取资源失败'
      });
      throw error;
    }
  },

  createResource: async (data) => {
    const resource = await createResource(data);
    set((state) => ({
      resources: {
        ...state.resources,
        [data.chapter_id]: [...(state.resources[data.chapter_id] || []), resource],
      },
    }));
    return resource;
  },

  updateResource: async (resourceId, data) => {
    const resource = await updateResource(resourceId, data);
    set((state) => ({
      resources: Object.fromEntries(
        Object.entries(state.resources).map(([key, value]) =>
          [key, value.map((r) => (r.id === resourceId ? resource : r))]
        )
      ),
    }));
    return resource;
  },

  deleteResource: async (resourceId) => {
    await deleteResource(resourceId);
    set((state) => ({
      resources: Object.fromEntries(
        Object.entries(state.resources).map(([key, value]) =>
          [key, value.filter((r) => r.id !== resourceId)]
        )
      ),
    }));
  },

  clearError: () => {
    set({ error: null });
  },
}));

// ============ 课程 Store ============

interface CourseState {
  courses: Course[];
  loading: boolean;
  error: string | null;
  total: number;
  page: number;
  limit: number;
  statusFilter: string;
  searchKeyword: string;

  // Actions
  fetchCourses: (params?: {
    status?: string;
    search?: string;
    page?: number;
    limit?: number;
  }) => Promise<void>;
  saveCourse: (courseData: Partial<Course>, courseId?: number) => Promise<Course>;
  deleteCourse: (courseId: number) => Promise<void>;
  togglePublish: (courseId: number, publish: boolean) => Promise<void>;
  setPage: (page: number) => void;
  setLimit: (limit: number) => void;
  setStatusFilter: (status: string) => void;
  setSearchKeyword: (keyword: string) => void;
  clearError: () => void;
}

export const useCourseAdminStore = create<CourseState>((set, get) => ({
  courses: [],
  loading: false,
  error: null,
  total: 0,
  page: 1,
  limit: 9,
  statusFilter: 'all',
  searchKeyword: '',

  fetchCourses: async (params) => {
    set({ loading: true, error: null });
    try {
      const data = await getAdminCourses(params);
      set({
        courses: data.courses,
        total: data.total,
        page: data.page,
        limit: data.limit,
        loading: false
      });
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : '获取课程列表失败',
      });
    }
  },

  saveCourse: async (courseData, courseId) => {
    let course: Course;
    if (courseId) {
      course = await updateCourse(courseId, courseData);
      set((state) => ({
        courses: state.courses.map((c) => (c.id === courseId ? course : c)),
      }));
    } else {
      course = await createCourse(courseData);
      set((state) => ({ courses: [...state.courses, course] }));
    }
    return course;
  },

  deleteCourse: async (courseId) => {
    await deleteCourse(courseId);
    set((state) => ({
      courses: state.courses.filter((c) => c.id !== courseId),
      total: state.total - 1,
    }));
  },

  togglePublish: async (courseId, publish) => {
    await publishCourse(courseId, publish);
    set((state) => ({
      courses: state.courses.map((c) =>
        c.id === courseId ? { ...c, is_published: publish } : c
      ),
    }));
  },

  setPage: (page) => {
    set({ page });
  },

  setLimit: (limit) => {
    set({ limit, page: 1 }); // Reset page to 1 when changing limit
  },

  setStatusFilter: (status) => {
    set({ statusFilter: status });
  },

  setSearchKeyword: (keyword) => {
    set({ searchKeyword: keyword });
  },

  clearError: () => {
    set({ error: null });
  },
}));
