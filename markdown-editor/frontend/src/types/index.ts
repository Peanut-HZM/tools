/**
 * Frontend type definitions for Markdown Editor
 */

export interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  size?: number
  modified?: string
  children?: FileNode[]
}

export interface FileContent {
  path: string
  content: string
  size: number
  modified: string
}

export interface EditorConfig {
  theme: 'light' | 'dark'
  fontSize: number
  autoSaveInterval: number
  previewTheme: string
  showLineNumbers: boolean
  tabSize: number
  useSpaces: boolean
  language: 'zh-CN' | 'en-US'
}

export interface SearchResult {
  file: string
  matches: ContentMatch[]
}

export interface ContentMatch {
  line: number
  content: string
  column: number
}

export interface FileSearchResult {
  name: string
  path: string
  match: string
}

export interface SaveResult {
  success: boolean
  message: string
  modified?: string
}

export interface ApiError {
  status: number
  message: string
  details?: string
}
