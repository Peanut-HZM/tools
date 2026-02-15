/**
 * Version History API Client
 * 
 * API functions for managing file version history.
 */
import { getAuthHeaders } from './authApi';
import { MARKDOWN_EDITOR_API_BASE_URL } from '../config/api';

const API_BASE_URL = MARKDOWN_EDITOR_API_BASE_URL;

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }
  return response.json();
}

export interface FileVersion {
  version_id: string;
  created_at: string;
  size: number;
  content_preview: string;
}

export interface ListVersionsResponse {
  success: boolean;
  file_path: string;
  versions: FileVersion[];
  total: number;
  limit: number;
  offset: number;
}

export interface ReadVersionResponse {
  success: boolean;
  version_id: string;
  file_path: string;
  content: string;
  created_at: string;
  size: number;
}

export interface RollbackResponse {
  success: boolean;
  file_path: string;
  rolled_to_version: string;
  new_version_id: string;
  message: string;
}

export async function listFileVersions(
  filePath: string,
  limit: number = 20,
  offset: number = 0
): Promise<ListVersionsResponse> {
  const params = new URLSearchParams({
    file_path: filePath,
    limit: limit.toString(),
    offset: offset.toString(),
  });

  const response = await fetch(`${API_BASE_URL}/oss/versions?${params}`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  return handleResponse<ListVersionsResponse>(response);
}

export async function readFileVersion(
  filePath: string,
  versionId: string
): Promise<ReadVersionResponse> {
  const params = new URLSearchParams({
    file_path: filePath,
    version_id: versionId,
  });

  const response = await fetch(`${API_BASE_URL}/oss/versions/read?${params}`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  return handleResponse<ReadVersionResponse>(response);
}

export async function rollbackToVersion(
  filePath: string,
  versionId: string
): Promise<RollbackResponse> {
  const response = await fetch(`${API_BASE_URL}/oss/versions/rollback`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      file_path: filePath,
      version_id: versionId,
    }),
  });

  return handleResponse<RollbackResponse>(response);
}

export async function deleteFileVersion(
  filePath: string,
  versionId: string
): Promise<{ success: boolean; message: string }> {
  const params = new URLSearchParams({
    file_path: filePath,
    version_id: versionId,
  });

  const response = await fetch(`${API_BASE_URL}/oss/versions/delete?${params}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });

  return handleResponse<{ success: boolean; message: string }>(response);
}

export default {
  listFileVersions,
  readFileVersion,
  rollbackToVersion,
  deleteFileVersion,
};
