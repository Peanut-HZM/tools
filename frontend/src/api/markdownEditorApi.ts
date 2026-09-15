/**
 * Markdown Editor API Client
 */
import { getAuthHeaders } from './authApi';
import type {
  FileNode,
  FileRawContent,
  SaveResult,
  CreateResult,
  RenameResult,
  DeleteResult,
  RootPathResponse,
  EditorConfig,
  FileSearchResult,
  ContentSearchResult,
  DirectoryBrowseData,
  FilePathData,
  FileManagerBrowseResponse,
  FileManagerItem,
  FileOperationResult,
} from '../types/markdownEditor';

import { MARKDOWN_EDITOR_API_BASE_URL } from '../config/api';
import { authedFetch } from './http';

const API_BASE_URL = MARKDOWN_EDITOR_API_BASE_URL;

/**
 * API 错误类，携带 HTTP 状态码，便于调用方按状态区分处理
 */
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/**
 * Handle API response errors
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(error.detail || `HTTP error ${response.status}`, response.status);
  }
  return response.json();
}

// ==================== File Operations ====================

/**
 * Get the user's root directory path
 */
export async function getRootPath(): Promise<RootPathResponse> {
  const response = await authedFetch(`${API_BASE_URL}/files/root`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  return handleResponse<RootPathResponse>(response);
}

/**
 * Update the user's root directory path
 */
export async function updateRootPath(path: string): Promise<RootPathResponse> {
  const response = await authedFetch(`${API_BASE_URL}/files/root`, {
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
 * @param root - 相对路径
 * @param depth - 扫描深度，-1 表示无限制，0 表示只返回第一层
 */
export async function getDirectoryTree(root: string = '', depth: number = -1): Promise<FileNode> {
  const params = new URLSearchParams();
  if (root) params.append('root', root);
  params.append('depth', depth.toString());
  
  const response = await authedFetch(`${API_BASE_URL}/files/tree?${params}`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  return handleResponse<FileNode>(response);
}

/**
 * 读取文件原始内容（支持二进制文件）
 * 对于文本文件：返回 text 字段
 * 对于二进制文件：返回 base64 编码的 data 字段
 */
export async function readFileRaw(path: string): Promise<FileRawContent> {
  const params = new URLSearchParams({ path });

  const response = await authedFetch(`${API_BASE_URL}/files/read-raw?${params}`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  return handleResponse<FileRawContent>(response);
}

/**
 * Save file content
 */
export async function saveFile(path: string, content: string): Promise<SaveResult> {
  const response = await authedFetch(`${API_BASE_URL}/files/save`, {
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

  const response = await authedFetch(`${API_BASE_URL}/files/upload?path=${encodeURIComponent(path)}`, {
    method: 'POST',
    headers: {
      'Authorization': (getAuthHeaders() as Record<string, string>)['Authorization'] || ''
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
  const response = await authedFetch(`${API_BASE_URL}/files/create`, {
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
  
  const response = await authedFetch(`${API_BASE_URL}/files/delete?${params}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  return handleResponse<DeleteResult>(response);
}

/**
 * Rename a file
 */
export async function renameFile(oldPath: string, newPath: string): Promise<RenameResult> {
  const response = await authedFetch(`${API_BASE_URL}/files/rename`, {
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
  
  const response = await authedFetch(`${API_BASE_URL}/files/directory/create?${params}`, {
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

  const response = await authedFetch(`${API_BASE_URL}/files/directory/delete?${params}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  return handleResponse<DeleteResult>(response);
}

/**
 * Browse directory contents for folder browser dialog
 */
export async function browseDirectories(parentPath: string = ''): Promise<DirectoryBrowseData> {
  const params = new URLSearchParams();
  if (parentPath) params.append('parent_path', parentPath);

  const response = await authedFetch(`${API_BASE_URL}/files/directories?${params}`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  const result = await handleResponse<{ success: boolean; data: DirectoryBrowseData }>(response);
  return result.data;
}

/**
 * Get absolute and relative paths for a file
 */
export async function getFilePaths(path: string): Promise<FilePathData> {
  const params = new URLSearchParams({ path });

  const response = await authedFetch(`${API_BASE_URL}/files/paths?${params}`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  const result = await handleResponse<{ success: boolean; data: FilePathData }>(response);
  return result.data;
}

// ==================== Config Operations ====================

/**
 * Get user configuration
 */
export async function getConfig(): Promise<EditorConfig> {
  const response = await authedFetch(`${API_BASE_URL}/config`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  return handleResponse<EditorConfig>(response);
}

/**
 * Save user configuration
 */
export async function saveConfig(config: EditorConfig): Promise<EditorConfig> {
  const response = await authedFetch(`${API_BASE_URL}/config`, {
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
  
  const response = await authedFetch(`${API_BASE_URL}/search/files?${params}`, {
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
  
  const response = await authedFetch(`${API_BASE_URL}/search/content?${params}`, {
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

  const response = await authedFetch(`${API_BASE_URL}/oss/upload`, {
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
  
  const response = await authedFetch(`${API_BASE_URL}/oss/read?${params}`, {
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
  const response = await authedFetch(`${API_BASE_URL}/oss/save`, {
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
  const response = await authedFetch(`${API_BASE_URL}/oss/list`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  
  return handleResponse<OssFileInfo[]>(response);
}

export const listOssFiles = listOssMarkdownFiles;

// ==================== File Manager Operations (任意路径浏览 + 文件操作) ====================

/**
 * 浏览任意目录（支持分页）
 */
export async function browseFileManager(
  path: string = '',
  page: number = 1,
  pageSize: number = 100
): Promise<FileManagerBrowseResponse> {
  const params = new URLSearchParams();
  if (path) params.append('path', path);
  params.append('page', page.toString());
  params.append('page_size', pageSize.toString());

  const response = await authedFetch(`${API_BASE_URL}/files/browse?${params}`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  return handleResponse<FileManagerBrowseResponse>(response);
}

/**
 * 复制文件或文件夹
 */
export async function copyFileItem(sourcePath: string, targetPath: string): Promise<FileOperationResult> {
  const response = await authedFetch(`${API_BASE_URL}/files/copy`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ source_path: sourcePath, target_path: targetPath })
  });
  return handleResponse<FileOperationResult>(response);
}

/**
 * 移动文件或文件夹
 */
export async function moveFileItem(sourcePath: string, targetPath: string): Promise<FileOperationResult> {
  const response = await authedFetch(`${API_BASE_URL}/files/move`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ source_path: sourcePath, target_path: targetPath })
  });
  return handleResponse<FileOperationResult>(response);
}

/**
 * 重命名文件或文件夹
 */
export async function renameFileManagerItem(path: string, newName: string): Promise<FileOperationResult> {
  const response = await authedFetch(`${API_BASE_URL}/files/rename-item`, {
    method: 'POST',
    headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, new_name: newName })
  });
  return handleResponse<FileOperationResult>(response);
}

/**
 * 删除文件或文件夹
 */
export async function deleteFileManagerItem(path: string): Promise<FileOperationResult> {
  const response = await authedFetch(`${API_BASE_URL}/files/delete-item`, {
    method: 'POST',
    headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ path })
  });
  return handleResponse<FileOperationResult>(response);
}

/**
 * 新建文件或文件夹
 */
export async function createFileManagerItem(
  parentPath: string,
  name: string,
  type: 'file' | 'directory'
): Promise<FileOperationResult> {
  const response = await authedFetch(`${API_BASE_URL}/files/create-item`, {
    method: 'POST',
    headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ parent_path: parentPath, name, type })
  });
  return handleResponse<FileOperationResult>(response);
}

/**
 * 上传文件到指定目录
 */
export async function uploadFileToPath(file: File, parentPath: string): Promise<FileOperationResult> {
  const formData = new FormData();
  formData.append('file', file);
  const headers = getAuthHeaders() as Record<string, string>;
  delete headers['Content-Type'];

  const response = await authedFetch(
    `${API_BASE_URL}/files/upload-any?parent_path=${encodeURIComponent(parentPath)}`,
    {
      method: 'POST',
      headers,
      body: formData
    }
  );
  return handleResponse<FileOperationResult>(response);
}

/**
 * 获取文件下载 URL（不发起请求，仅拼接地址）
 */
export function getDownloadUrl(path: string): string {
  return `${API_BASE_URL}/files/download?path=${encodeURIComponent(path)}`;
}

/**
 * 获取文件或文件夹详细信息
 */
export async function getFileManagerInfo(path: string): Promise<FileManagerItem> {
  const params = new URLSearchParams({ path });
  const response = await authedFetch(`${API_BASE_URL}/files/info?${params}`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  return handleResponse<FileManagerItem>(response);
}
