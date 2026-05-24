import Taro from '@tarojs/taro';
import { request, uploadFile } from './request';

export interface OssFileInfo {
  file_path: string;
  filename: string;
  size: number;
  last_modified?: string;
}

export interface OssReadResponse {
  success: boolean;
  content: string;
  filename: string;
  message?: string;
}

export interface OssSaveResponse {
  success: boolean;
  message: string;
}

export interface OssUploadResponse {
  success: boolean;
  file_path: string;
  url: string;
  filename: string;
  message?: string;
}

const DRAFT_KEY = 'markdown_editor_draft';

export const markdownEditorApi = {
  // 本地草稿
  saveDraft: (content: string): void => {
    try {
      Taro.setStorageSync(DRAFT_KEY, content);
    } catch {
      // ignore
    }
  },

  loadDraft: (): string => {
    try {
      return Taro.getStorageSync(DRAFT_KEY) || '';
    } catch {
      return '';
    }
  },

  clearDraft: (): void => {
    try {
      Taro.removeStorageSync(DRAFT_KEY);
    } catch {
      // ignore
    }
  },

  // OSS 文件列表
  listOssFiles: async (): Promise<OssFileInfo[]> => {
    return request('/markdown-editor/oss/list', {
      needAuth: true,
    });
  },

  // 读取 OSS 文件
  readOssFile: async (filePath: string): Promise<OssReadResponse> => {
    return request(`/markdown-editor/oss/read?file_path=${encodeURIComponent(filePath)}`, {
      needAuth: true,
    });
  },

  // 保存到 OSS
  saveOssFile: async (filePath: string, content: string): Promise<OssSaveResponse> => {
    return request('/markdown-editor/oss/save', {
      method: 'POST',
      data: { file_path: filePath, content },
      needAuth: true,
    });
  },

  // 上传新文件到 OSS
  uploadOssFile: async (filePath: string): Promise<OssUploadResponse> => {
    return uploadFile('/markdown-editor/oss/upload', filePath, 'file', {}, true);
  },
};
