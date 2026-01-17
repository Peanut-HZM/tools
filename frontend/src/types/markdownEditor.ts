/**
 * TypeScript type definitions for Markdown Editor
 */

// ==================== File Types ====================

export interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  modified?: string;
  children?: FileNode[];
}

export interface FileContent {
  path: string;
  content: string;
  size: number;
  modified: string;
}

export interface SaveResult {
  success: boolean;
  message: string;
  modified?: string;
}

export interface CreateResult {
  success: boolean;
  path: string;
  message?: string;
}

export interface RenameResult {
  success: boolean;
  message: string;
  old_path: string;
  new_path: string;
}

export interface DeleteResult {
  success: boolean;
  message: string;
  path: string;
}

export interface RootPathResponse {
  path: string;
  exists: boolean;
}

// ==================== Config Types ====================

export interface EditorConfig {
  theme: 'light' | 'dark';
  fontSize: number;
  autoSaveInterval: number;
  previewTheme: string;
  showLineNumbers: boolean;
  tabSize: number;
  useSpaces: boolean;
  wordWrap?: boolean;
  showMinimap?: boolean;
  language: 'zh-CN' | 'en-US';
  rootPath?: string;
}

// ==================== Search Types ====================

export interface FileSearchResult {
  name: string;
  path: string;
  match: string;
}

export interface ContentMatch {
  line: number;
  content: string;
  column: number;
}

export interface ContentSearchResult {
  file: string;
  matches: ContentMatch[];
}

// ==================== Editor State Types ====================

export type SaveStatus = 'saved' | 'unsaved' | 'saving' | 'error';

export interface EditorState {
  content: string;
  originalContent: string;
  cursorLine: number;
  cursorColumn: number;
  isSaving: boolean;
  lastSaveTime: Date | null;
  saveError: string | null;
}

// ==================== File Store Types ====================

export interface FileState {
  directoryTree: FileNode | null;
  currentFile: FileContent | null;
  currentFilePath: string;
  rootPath: string;
  isLoading: boolean;
  error: string | null;
  expandedNodes: Set<string>;
}

// ==================== API Error Types ====================

export interface ApiError {
  status: number;
  message: string;
  details?: string;
}
