/**
 * File Store - Manages directory tree and current file state using React Context
 */
import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import * as markdownEditorApi from '../api/markdownEditorApi';
import type { FileNode, FileContent, RootPathResponse } from '../types/markdownEditor';
import type { OssFileInfo } from '../types/offlineCache';
import { getMetadata, saveMetadata } from '../utils/indexedDb';

export interface FileState {
  directoryTree: FileNode | null;
  currentFile: FileContent | null;
  currentFilePath: string;
  rootPath: string;
  hasRootPath: boolean;
  isLoading: boolean;
  error: string | null;
  expandedNodes: Set<string>;
  ossFiles: OssFileInfo[];
  ossFilesLoading: boolean;
  currentOssFile: string | null;
}

export interface FileActions {
  loadRootPath: () => Promise<RootPathResponse>;
  setRootPath: (path: string) => Promise<void>;
  loadDirectoryTree: (subPath?: string, depth?: number) => Promise<void>;
  loadSubDirectory: (path: string) => Promise<void>;
  openFile: (path: string) => Promise<void>;
  saveCurrentFile: (content: string) => Promise<void>;
  createFile: (path: string, content?: string) => Promise<void>;
  deleteFile: (path: string) => Promise<void>;
  renameFile: (oldPath: string, newPath: string) => Promise<void>;
  createDirectory: (path: string) => Promise<void>;
  deleteDirectory: (path: string, recursive?: boolean) => Promise<void>;
  toggleNode: (path: string) => void;
  closeCurrentFile: () => void;
  clearError: () => void;
  loadOssFiles: () => Promise<void>;
  refreshOssFiles: () => Promise<void>;
  setCurrentOssFile: (path: string | null) => void;
}

export type FileContextType = FileState & FileActions;

const FileContext = createContext<FileContextType | null>(null);


/**
 * 合并子目录树到主目录树
 */
function mergeSubTree(root: FileNode, targetPath: string, subTree: FileNode): FileNode {
  if (root.path === targetPath) {
    return { ...root, children: subTree.children };
  }
  
  if (root.children) {
    return {
      ...root,
      children: root.children.map(child => 
        child.type === 'directory' ? mergeSubTree(child, targetPath, subTree) : child
      )
    };
  }
  
  return root;
}

export function FileProvider({ children }: { children: ReactNode }) {
  const [directoryTree, setDirectoryTree] = useState<FileNode | null>(null);
  const [currentFile, setCurrentFile] = useState<FileContent | null>(null);
  const [currentFilePath, setCurrentFilePath] = useState('');
  const [rootPath, setRootPath] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [ossFiles, setOssFiles] = useState<OssFileInfo[]>([]);
  const [ossFilesLoading, setOssFilesLoading] = useState(false);
  const [currentOssFile, setCurrentOssFile] = useState<string | null>(null);

  const loadRootPath = useCallback(async () => {
    try {
      const result = await markdownEditorApi.getRootPath();
      setRootPath(result.path);
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load root path');
      throw e;
    }
  }, []);

  // 缓存过期时间：5 分钟
  const CACHE_TTL = 5 * 60 * 1000;
  
  const loadDirectoryTree = useCallback(async (subPath: string = '', depth: number = -1) => {
    setIsLoading(true);
    setError(null);
    try {
      // 首次加载使用 depth=1 只获取第一层
      const tree = await markdownEditorApi.getDirectoryTree(subPath, depth);
      setDirectoryTree(tree);
      
      // 缓存根目录树（仅当 depth=-1 时，即完整加载）
      if (depth === -1 && !subPath) {
        const cacheKey = 'directory_tree_root';
        const cacheData = {
          tree,
          timestamp: Date.now()
        };
        await saveMetadata(cacheKey, cacheData);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load directory tree');
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 异步加载子目录（用户展开节点时调用）
  const loadSubDirectory = useCallback(async (path: string) => {
    try {
      // 检查缓存
      const cacheKey = `directory_tree_${path}`;
      const cached = await getMetadata<{ tree: FileNode; timestamp: number }>(cacheKey);
      
      if (cached && (Date.now() - cached.timestamp) < CACHE_TTL) {
        // 缓存命中，更新目录树
        setDirectoryTree(prev => {
          if (!prev) return prev;
          return mergeSubTree(prev, path, cached.tree);
        });
        return;
      }
      
      // 缓存未命中或过期，从后端加载
      const subTree = await markdownEditorApi.getDirectoryTree(path, -1);
      
      // 保存缓存
      await saveMetadata(cacheKey, {
        tree: subTree,
        timestamp: Date.now()
      });
      
      // 更新目录树
      setDirectoryTree(prev => {
        if (!prev) return prev;
        return mergeSubTree(prev, path, subTree);
      });
    } catch (e) {
      console.error('Failed to load sub directory:', e);
    }
  }, []);

  const setRootPathAction = useCallback(async (path: string) => {
    try {
      // Update backend config first
      await markdownEditorApi.updateRootPath(path);
      // Then update local state
      setRootPath(path);
      // Reload tree with new root (passing empty string because root is now set on backend)
      await loadDirectoryTree('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to set root path');
      throw e;
    }
  }, [loadDirectoryTree]);

  const openFile = useCallback(async (path: string) => {
    setIsLoading(true);
    setError(null);
    try {
      // 使用 readFileRaw 支持所有文件类型（文本和二进制）
      const file = await markdownEditorApi.readFileRaw(path);

      // 根据文件类型处理内容
      let textContent: string | null = null;

      if (file.text) {
        // 文本文件直接使用 text 字段
        textContent = file.text;
      } else if (file.data) {
        // 二进制文件需要特殊处理（阶段 2/3 实现 PDF/Excel/Word 查看器）
        // 暂时存储 base64 数据，显示占位符（含大小信息）
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        textContent = `[二进制文件：${file.content_type}，${sizeMB} MB]`;
      }

      setCurrentFile({
        path: file.path,
        content: textContent || '',
        size: file.size,
        modified: file.modified
      });
      setCurrentFilePath(path);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to open file');
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const saveCurrentFile = useCallback(async (content: string) => {
    if (!currentFilePath) return;
    
    setIsLoading(true);
    setError(null);
    try {
      await markdownEditorApi.saveFile(currentFilePath, content);
      if (currentFile) {
        setCurrentFile({ ...currentFile, content });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save file');
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, [currentFilePath, currentFile]);

  const createFile = useCallback(async (path: string, content: string = '') => {
    setIsLoading(true);
    setError(null);
    try {
      await markdownEditorApi.createFile(path, content);
      await loadDirectoryTree();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create file');
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, [loadDirectoryTree]);

  const deleteFile = useCallback(async (path: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await markdownEditorApi.deleteFile(path);
      if (currentFilePath === path) {
        setCurrentFile(null);
        setCurrentFilePath('');
      }
      await loadDirectoryTree();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete file');
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, [currentFilePath, loadDirectoryTree]);

  const renameFile = useCallback(async (oldPath: string, newPath: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await markdownEditorApi.renameFile(oldPath, newPath);
      if (currentFilePath === oldPath) {
        setCurrentFilePath(newPath);
      }
      await loadDirectoryTree();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to rename file');
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, [currentFilePath, loadDirectoryTree]);

  const createDirectory = useCallback(async (path: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await markdownEditorApi.createDirectory(path);
      await loadDirectoryTree();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create directory');
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, [loadDirectoryTree]);

  const deleteDirectory = useCallback(async (path: string, recursive: boolean = false) => {
    setIsLoading(true);
    setError(null);
    try {
      await markdownEditorApi.deleteDirectory(path, recursive);
      await loadDirectoryTree();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete directory');
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, [loadDirectoryTree]);

  const toggleNode = useCallback((path: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  const closeCurrentFile = useCallback(() => {
    setCurrentFile(null);
    setCurrentFilePath('');
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const loadOssFiles = useCallback(async () => {
    setOssFilesLoading(true);
    try {
      const files = await markdownEditorApi.listOssFiles();
      setOssFiles(files);
    } catch (e) {
      console.error('Failed to load OSS files:', e);
    } finally {
      setOssFilesLoading(false);
    }
  }, []);

  const refreshOssFiles = useCallback(async () => {
    await loadOssFiles();
  }, [loadOssFiles]);

  const setCurrentOssFileAction = useCallback((path: string | null) => {
    setCurrentOssFile(path);
  }, []);

  const value: FileContextType = {
    directoryTree,
    currentFile,
    currentFilePath,
    rootPath,
    hasRootPath: !!rootPath,
    isLoading,
    error,
    expandedNodes,
    ossFiles,
    ossFilesLoading,
    currentOssFile,
    loadRootPath,
    setRootPath: setRootPathAction,
    loadDirectoryTree,
    openFile,
    saveCurrentFile,
    createFile,
    deleteFile,
    renameFile,
    createDirectory,
    deleteDirectory,
    toggleNode,
    closeCurrentFile,
    clearError,
    loadOssFiles,
    refreshOssFiles,
    setCurrentOssFile: setCurrentOssFileAction
  };

  return (
    <FileContext.Provider value={value}>
      {children}
    </FileContext.Provider>
  );
}

export function useFileStore(): FileContextType {
  const context = useContext(FileContext);
  if (!context) {
    throw new Error('useFileStore must be used within a FileProvider');
  }
  return context;
}

export { FileContext };
