import axios from 'axios';
import { getAuthToken } from '../api/authApi';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const getAuthHeaders = () => {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export interface PRDVersion {
  id: string;
  conversation_id: string;
  version_number: number;
  content: string;
  status: 'draft' | 'confirmed' | 'archived';
  created_at: string;
}

export interface PRDCompareResult {
  from_version: number;
  to_version: number;
  from_content: string;
  to_content: string;
  diff: string;
}

export const prdApi = {
  // 获取 PRD 版本列表
  getVersions: async (conversationId: string): Promise<PRDVersion[]> => {
    const response = await axios.get(
      `${API_BASE_URL}/conversations/${conversationId}/prd`,
      { headers: getAuthHeaders() }
    );
    return response.data;
  },

  // 创建新版本
  createVersion: async (
    conversationId: string,
    sections?: string[]
  ): Promise<PRDVersion> => {
    const response = await axios.post(
      `${API_BASE_URL}/conversations/${conversationId}/prd`,
      { sections },
      { headers: getAuthHeaders() }
    );
    return response.data;
  },

  // 获取指定版本
  getVersion: async (
    conversationId: string,
    versionNumber: number
  ): Promise<PRDVersion> => {
    const response = await axios.get(
      `${API_BASE_URL}/conversations/${conversationId}/prd/${versionNumber}`,
      { headers: getAuthHeaders() }
    );
    return response.data;
  },

  // 确认版本
  confirmVersion: async (
    conversationId: string,
    versionNumber: number
  ): Promise<PRDVersion> => {
    const response = await axios.post(
      `${API_BASE_URL}/conversations/${conversationId}/prd/${versionNumber}/confirm`,
      {},
      { headers: getAuthHeaders() }
    );
    return response.data;
  },

  // 比较版本
  compareVersions: async (
    conversationId: string,
    fromVersion: number,
    toVersion: number
  ): Promise<PRDCompareResult> => {
    const response = await axios.get(
      `${API_BASE_URL}/conversations/${conversationId}/prd/compare`,
      {
        params: { from_version: fromVersion, to_version: toVersion },
        headers: getAuthHeaders(),
      }
    );
    return response.data;
  },

  // 导出 PRD
  exportPRD: async (
    conversationId: string,
    format: 'markdown' | 'pdf' | 'word' = 'markdown',
    versionNumber?: number
  ): Promise<Blob> => {
    const response = await axios.get(
      `${API_BASE_URL}/conversations/${conversationId}/prd/export`,
      {
        params: { format, version_number: versionNumber },
        headers: getAuthHeaders(),
        responseType: 'blob',
      }
    );
    return response.data;
  },

  // 回滚到指定版本
  rollbackToVersion: async (
    conversationId: string,
    targetVersion: number
  ): Promise<PRDVersion> => {
    const response = await axios.post(
      `${API_BASE_URL}/conversations/${conversationId}/prd/rollback`,
      { target_version: targetVersion },
      { headers: getAuthHeaders() }
    );
    return response.data;
  },

  // 更新章节
  updateSection: async (
    conversationId: string,
    sectionTitle: string,
    sectionContent: string
  ): Promise<PRDVersion> => {
    const response = await axios.post(
      `${API_BASE_URL}/conversations/${conversationId}/prd/section/update`,
      { section_title: sectionTitle, section_content: sectionContent },
      { headers: getAuthHeaders() }
    );
    return response.data;
  },
};
