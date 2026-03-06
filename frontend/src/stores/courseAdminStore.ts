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
