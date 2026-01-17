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

const API_BASE_URL = 'http://localhost:19092/api/markdown-editor';

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
