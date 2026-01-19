/**
 * Markdown Editor API Client
 */
import { getAuthHeaders } from './authApi';
import type {
  FileNode,
  FileContent,
  SaveResult,
  CreateResult,
  RenameResult,
  DeleteResult,
  RootPathResponse,
  EditorConfig,
  FileSearchResult,
  ContentSearchResult
} from '../types/markdownEditor';

import { MARKDOWN_EDITOR_API_BASE_URL } from '../config/api';

const API_BASE_URL = MARKDOWN_EDITOR_API_BASE_URL;

/**
 * Handle API response errors
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }
  return response.json();
}

// ==================== File Operations ====================

/**
 * Get the user's root directory path
 */
export async function getRootPath(): Promise<RootPathResponse> {
  const response = await fetch(`${API_BASE_URL}/files/root`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  return handleResponse<RootPathResponse>(response);
}

/**
 * Update the user's root directory path
 */
export async function updateRootPath(path: string): Promise<RootPathResponse> {
  const response = await fetch(`${API_BASE_URL}/files/root`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ path })
  });
  return handleResponse<RootPathResponse>(response);
}

/**
 * Get directory tree structure
 */
export async function getDirectoryTree(root: string = ''): Promise<FileNode> {
  const params = new URLSearchParams();
  if (root) params.append('root', root);
  
  const response = await fetch(`${API_BASE_URL}/files/tree?${params}`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  return handleResponse<FileNode>(response);
}

/**
 * Read file content
 */
export async function readFile(path: string): Promise<FileContent> {
  const params = new URLSearchParams({ path });
  
  const response = await fetch(`${API_BASE_URL}/files/read?${params}`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  return handleResponse<FileContent>(response);
}

/**
 * Save file content
 */
export async function saveFile(path: string, content: string): Promise<SaveResult> {
  const response = await fetch(`${API_BASE_URL}/files/save`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ path, content })
  });
  return handleResponse<SaveResult>(response);
}

/**
 * Save file content to OSS
 */
export async function saveMarkdownToOss(path: string, content: string): Promise<SaveResult> {
  // Currently saveFile handles OSS upload in backend
  return saveFile(path, content);
}

/**
 * Upload a markdown file
 */
export async function uploadMarkdownFile(file: File, path: string = ''): Promise<SaveResult> {
  const formData = new FormData();
  formData.append('file', file);
  if (path) {
    formData.append('path', path);
  }

  const response = await fetch(`${API_BASE_URL}/files/upload?path=${encodeURIComponent(path)}`, {
    method: 'POST',
    headers: {
      'Authorization': getAuthHeaders().Authorization as string
      // Do NOT set Content-Type header when sending FormData, 
      // browser will set it automatically with boundary
    },
    body: formData
  });
  return handleResponse<SaveResult>(response);
}

/**
 * Create a new file
 */
export async function createFile(path: string, content: string = ''): Promise<CreateResult> {
  const response = await fetch(`${API_BASE_URL}/files/create`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ path, content })
  });
  return handleResponse<CreateResult>(response);
}

/**
 * Delete a file
 */
export async function deleteFile(path: string): Promise<DeleteResult> {
  const params = new URLSearchParams({ path });
  
  const response = await fetch(`${API_BASE_URL}/files/delete?${params}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  return handleResponse<DeleteResult>(response);
}

/**
 * Rename a file
 */
export async function renameFile(oldPath: string, newPath: string): Promise<RenameResult> {
  const response = await fetch(`${API_BASE_URL}/files/rename`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ old_path: oldPath, new_path: newPath })
  });
  return handleResponse<RenameResult>(response);
}

/**
 * Create a new directory
 */
export async function createDirectory(path: string): Promise<CreateResult> {
  const params = new URLSearchParams({ path });
  
  const response = await fetch(`${API_BASE_URL}/files/directory/create?${params}`, {
    method: 'POST',
    headers: getAuthHeaders()
  });
  return handleResponse<CreateResult>(response);
}

/**
 * Delete a directory
 */
export async function deleteDirectory(path: string, recursive: boolean = false): Promise<DeleteResult> {
  const params = new URLSearchParams({ path, recursive: String(recursive) });
  
  const response = await fetch(`${API_BASE_URL}/files/directory/delete?${params}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  return handleResponse<DeleteResult>(response);
}

// ==================== Config Operations ====================

/**
 * Get user configuration
 */
export async function getConfig(): Promise<EditorConfig> {
  const response = await fetch(`${API_BASE_URL}/config`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  return handleResponse<EditorConfig>(response);
}

/**
 * Save user configuration
 */
export async function saveConfig(config: EditorConfig): Promise<EditorConfig> {
  const response = await fetch(`${API_BASE_URL}/config`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(config)
  });
  return handleResponse<EditorConfig>(response);
}

// ==================== Search Operations ====================

/**
 * Search files by name
 */
export async function searchFiles(keyword: string): Promise<FileSearchResult[]> {
  const params = new URLSearchParams({ keyword });
  
  const response = await fetch(`${API_BASE_URL}/search/files?${params}`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  return handleResponse<FileSearchResult[]>(response);
}

/**
 * Search content in files
 */
export async function searchContent(
  keyword: string,
  regex: boolean = false,
  caseSensitive: boolean = false
): Promise<ContentSearchResult[]> {
  const params = new URLSearchParams({
    keyword,
    regex: String(regex),
    case_sensitive: String(caseSensitive)
  });
  
  const response = await fetch(`${API_BASE_URL}/search/content?${params}`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  return handleResponse<ContentSearchResult[]>(response);
}

// ==================== OSS Operations ====================

export interface OssUploadMarkdownResponse {
  success: boolean;
  file_path: string;
  url: string;
  filename: string;
  message: string;
}

export interface OssReadMarkdownResponse {
  success: boolean;
  content: string;
  filename: string;
  message: string;
}

export interface OssSaveMarkdownRequest {
  file_path: string;
  content: string;
}

export interface OssSaveMarkdownResponse {
  success: boolean;
  message: string;
}

export interface OssFileInfo {
  file_path: string;
  filename: string;
  size: number;
  last_modified: string | null;
}

/**
 * Upload a Markdown file to OSS
 */
export async function uploadMarkdownToOss(file: File): Promise<OssUploadMarkdownResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const headers = getAuthHeaders() as Record<string, string>;
  delete headers['Content-Type'];

  const response = await fetch(`${API_BASE_URL}/oss/upload`, {
    method: 'POST',
    headers: {
      ...headers,
    },
    body: formData,
  });

  return handleResponse<OssUploadMarkdownResponse>(response);
}

/**
 * Read a Markdown file from OSS
 */
export async function readMarkdownFromOss(filePath: string): Promise<OssReadMarkdownResponse> {
  const params = new URLSearchParams({ file_path: filePath });
  
  const response = await fetch(`${API_BASE_URL}/oss/read?${params}`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  
  return handleResponse<OssReadMarkdownResponse>(response);
}

/**
 * Save Markdown content to OSS
 */
export async function saveMarkdownToOssLegacy(
  filePath: string,
  content: string
): Promise<OssSaveMarkdownResponse> {
  const response = await fetch(`${API_BASE_URL}/oss/save`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ file_path: filePath, content })
  });
  
  return handleResponse<OssSaveMarkdownResponse>(response);
}

/**
 * List all Markdown files in OSS for the current user
 */
export async function listOssMarkdownFiles(): Promise<OssFileInfo[]> {
  const response = await fetch(`${API_BASE_URL}/oss/list`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  
  return handleResponse<OssFileInfo[]>(response);
}
