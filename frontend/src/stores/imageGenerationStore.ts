/**
 * 图像生成 Zustand Store
 *
 * 管理表单状态、生成结果、历史记录、配额
 */

import { create } from 'zustand';
import * as api from '../api/imageGenerationApi';
import type {
  Operation,
  ImageSize,
  ModelPreference,
  EditType,
  GenerateResponse,
  HistoryItem,
  QuotaInfo,
} from '../api/imageGenerationApi';

/* ================================================================
 * 类型定义
 * ================================================================ */

export interface ImageGenParams {
  size: ImageSize;
  n: number;
  style: string;
  strength: number;
  model_preference: ModelPreference;
  polish_prompt: boolean;
  edit_type: EditType;
}

interface ImageGenState {
  // 表单状态
  operation: Operation;
  prompt: string;
  params: ImageGenParams;
  referenceImage: File | null;
  referenceImagePreview: string | null;
  maskImage: File | null;
  maskImagePreview: string | null;

  // 生成结果
  currentResult: GenerateResponse | null;

  // 历史
  history: HistoryItem[];
  historyTotal: number;
  historyLoading: boolean;

  // 配额
  quota: QuotaInfo | null;
  quotaLoadError: boolean;

  // UI 状态
  loading: boolean;
  error: string | null;
  abortController: AbortController | null;
  historyDrawerOpen: boolean;

  // 选中历史项（查看详情）
  selectedHistory: HistoryItem | null;
}

interface ImageGenActions {
  setOperation: (op: Operation) => void;
  setPrompt: (prompt: string) => void;
  setParams: (partial: Partial<ImageGenParams>) => void;
  setReferenceImage: (file: File | null, preview: string | null) => void;
  setMaskImage: (file: File | null, preview: string | null) => void;

  generate: () => Promise<void>;
  abort: () => void;
  reset: () => void;
  setError: (error: string | null) => void;

  polishPrompt: () => Promise<void>;

  loadHistory: (skip?: number, limit?: number) => Promise<void>;
  loadQuota: () => Promise<void>;
  deleteHistory: (id: string) => Promise<void>;
  selectHistory: (item: HistoryItem | null) => void;

  setHistoryDrawerOpen: (open: boolean) => void;
  setCurrentResult: (result: GenerateResponse | null) => void;

  /** 将一张已有图片 URL 设为参考图（"以此图为参考"功能） */
  useImageAsReference: (imageUrl: string) => Promise<void>;
}

/* ================================================================
 * 默认参数
 * ================================================================ */

const DEFAULT_PARAMS: ImageGenParams = {
  size: '1024x1024',
  n: 1,
  style: '',
  strength: 0.6,
  model_preference: 'auto',
  polish_prompt: false,
  edit_type: 'upscale',
};

const INITIAL_STATE: ImageGenState = {
  operation: 'text2img',
  prompt: '',
  params: { ...DEFAULT_PARAMS },
  referenceImage: null,
  referenceImagePreview: null,
  maskImage: null,
  maskImagePreview: null,
  currentResult: null,
  history: [],
  historyTotal: 0,
  historyLoading: false,
  quota: null,
  quotaLoadError: false,
  loading: false,
  error: null,
  abortController: null,
  historyDrawerOpen: false,
  selectedHistory: null,
};

/* ================================================================
 * Store
 * ================================================================ */

export const useImageGenStore = create<ImageGenState & ImageGenActions>()((set, get) => ({
  ...INITIAL_STATE,

  setOperation: (op) => set({ operation: op, error: null }),
  setPrompt: (prompt) => set({ prompt }),
  setParams: (partial) =>
    set((state) => ({ params: { ...state.params, ...partial } })),
  setReferenceImage: (file, preview) =>
    set({ referenceImage: file, referenceImagePreview: preview }),
  setMaskImage: (file, preview) =>
    set({ maskImage: file, maskImagePreview: preview }),
  setError: (error) => set({ error }),
  setHistoryDrawerOpen: (open) => set({ historyDrawerOpen: open }),
  setCurrentResult: (result) => set({ currentResult: result }),
  selectHistory: (item) => set({ selectedHistory: item }),

  generate: async () => {
    const state = get();
    const { operation, prompt, params, referenceImage, maskImage } = state;

    // 前置校验
    if (!prompt.trim()) {
      set({ error: '请输入提示词' });
      return;
    }
    if ((operation === 'img2img' || operation === 'inpaint' || operation === 'upload_edit') && !referenceImage) {
      set({ error: '请上传参考图片' });
      return;
    }
    if (operation === 'inpaint' && !maskImage) {
      set({ error: '请上传蒙版图片' });
      return;
    }

    // 取消之前的请求
    if (state.abortController) {
      state.abortController.abort();
    }

    const abortController = new AbortController();

    set({
      loading: true,
      error: null,
      abortController,
      currentResult: null,
    });

    try {
      const result = await api.generate(
        {
          operation,
          prompt: prompt.trim(),
          size: params.size,
          n: params.n,
          style: params.style || undefined,
          strength: params.strength,
          model_preference: params.model_preference,
          polish_prompt: params.polish_prompt,
          reference_image: referenceImage,
          mask_image: maskImage,
          edit_type: operation === 'upload_edit' ? params.edit_type : undefined,
        },
        abortController.signal,
      );
      set({ currentResult: result, loading: false });
      // 生成成功后刷新配额和历史
      get().loadQuota().catch(() => {});
      get().loadHistory(0, 20).catch(() => {});
    } catch (err: any) {
      if (err.name === 'AbortError' || err.name === 'CanceledError') {
        set({ loading: false, error: null });
      } else {
        set({ loading: false, error: err.message || '生成失败' });
      }
    }
  },

  abort: () => {
    const state = get();
    if (state.abortController) {
      state.abortController.abort();
      set({ abortController: null, loading: false, error: null });
    }
  },

  reset: () => {
    const state = get();
    if (state.abortController) {
      state.abortController.abort();
    }
    // 清理预览 URL
    if (state.referenceImagePreview) URL.revokeObjectURL(state.referenceImagePreview);
    if (state.maskImagePreview) URL.revokeObjectURL(state.maskImagePreview);
    set({ ...INITIAL_STATE });
  },

  polishPrompt: async () => {
    const state = get();
    if (!state.prompt.trim()) {
      set({ error: '请先输入提示词' });
      return;
    }
    try {
      const resp = await api.polishPrompt(state.prompt.trim(), state.operation);
      if (resp.was_polished) {
        set({ prompt: resp.polished_prompt, error: null });
      } else {
        // 未润色（Phase 8 占位），不做修改
        set({ error: null });
      }
    } catch (err: any) {
      set({ error: err.message || '提示词润色失败' });
    }
  },

  loadHistory: async (skip = 0, limit = 20) => {
    set({ historyLoading: true });
    try {
      const resp = await api.getHistory(skip, limit);
      set({
        history: resp.items,
        historyTotal: resp.count,
        historyLoading: false,
      });
    } catch (err: any) {
      set({ historyLoading: false, error: err.message || '加载历史失败' });
    }
  },

  loadQuota: async () => {
    try {
      const quota = await api.getMyQuota();
      set({ quota, quotaLoadError: false });
    } catch {
      // 配额加载失败不阻塞主流程，标记错误以便 QuotaBadge 隐藏
      set({ quotaLoadError: true });
    }
  },

  deleteHistory: async (id) => {
    try {
      await api.deleteHistory(id);
      // 从列表中移除
      set((state) => ({
        history: state.history.filter((h) => h.id !== id),
        historyTotal: Math.max(0, state.historyTotal - 1),
        selectedHistory: state.selectedHistory?.id === id ? null : state.selectedHistory,
      }));
    } catch (err: any) {
      set({ error: err.message || '删除失败' });
    }
  },

  useImageAsReference: async (imageUrl) => {
    try {
      // 下载图片并转为 File 对象
      const resp = await fetch(imageUrl);
      const blob = await resp.blob();
      const file = new File([blob], 'reference.png', { type: blob.type || 'image/png' });
      const preview = URL.createObjectURL(file);
      // 切换到 img2img 模式并设置参考图
      set({
        operation: 'img2img',
        referenceImage: file,
        referenceImagePreview: preview,
        error: null,
      });
    } catch (err: any) {
      set({ error: '加载参考图失败' });
    }
  },
}));
