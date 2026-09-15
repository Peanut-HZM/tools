/**
 * File Store - Manages directory tree and current file state using React Context
 */
import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { flushSync } from 'react-dom';
import * as markdownEditorApi from '../api/markdownEditorApi';
import { ApiError } from '../api/markdownEditorApi';
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
  // 正在刷新的子树路径（null 表示没有子树在刷新）
  refreshingPath: string | null;
  // 是否正在刷新整棵树
  refreshingAll: boolean;
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
  // 刷新文件树：path 为空刷新整树，否则递归刷新该子树（绕过缓存）
  refreshTree: (path?: string) => Promise<void>;
}

export type FileContextType = FileState & FileActions;

const FileContext = createContext<FileContextType | null>(null);


/**
 * 不可变替换树中指定路径节点的 children
 * 路径不存在时返回原树引用（不做拷贝）
 */
export function replaceSubtree(root: FileNode, targetPath: string, subTree: FileNode): FileNode {
  if (root.path === targetPath) {
    return { ...root, children: subTree.children };
  }

  if (root.children) {
    let changed = false;
    const children = root.children.map((child) => {
      if (child.type !== 'directory') return child;
      const nextChild = replaceSubtree(child, targetPath, subTree);
      if (nextChild !== child) changed = true;
      return nextChild;
    });
    // 目标路径不存在（未产生任何变化）时，返回原引用，避免无意义的重新渲染
    if (!changed) return root;
    return { ...root, children };
  }

  return root;
}

/**
 * 不可变移除树中指定路径的节点
 * 路径不存在或目标为根节点时返回原树引用
 */
export function removeSubtree(root: FileNode, targetPath: string): FileNode {
  if (root.path === targetPath || !root.children) {
    return root;
  }

  let changed = false;
  const children: FileNode[] = [];
  for (const child of root.children) {
    if (child.path === targetPath) {
      changed = true;
      continue;
    }
    const nextChild = removeSubtree(child, targetPath);
    if (nextChild !== child) changed = true;
    children.push(nextChild);
  }

  // 目标路径不存在（未产生任何变化）时，返回原引用，避免无意义的重新渲染
  if (!changed) return root;
  return { ...root, children };
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
  // 文件树刷新状态：分别标记子树刷新与整树刷新
  const [refreshingPath, setRefreshingPath] = useState<string | null>(null);
  const [refreshingAll, setRefreshingAll] = useState(false);

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
          return replaceSubtree(prev, path, cached.tree);
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
        return replaceSubtree(prev, path, subTree);
      });
    } catch (e) {
      console.error('Failed to load sub directory:', e);
    }
  }, []);

  /**
   * 刷新文件树（绕过子树缓存，一次性请求，不做轮询）
   * @param path 空字符串刷新整树；否则递归刷新该路径子树的所有层级
   */
  const refreshTree = useCallback(async (path: string = '') => {
    if (!path) {
      setRefreshingAll(true);
      try {
        await loadDirectoryTree('', -1);
      } finally {
        setRefreshingAll(false);
      }
      return;
    }
    setRefreshingPath(path);
    try {
      const subTree = await markdownEditorApi.getDirectoryTree(path, -1);
      // 更新缓存，避免刷新结果被旧缓存覆盖
      await saveMetadata(`directory_tree_${path}`, {
        tree: subTree,
        timestamp: Date.now(),
      });
      setDirectoryTree((prev) => (prev ? replaceSubtree(prev, path, subTree) : prev));
    } catch (e) {
      // 后端对 FileNotFoundError 返回 404，按状态码判断而非错误文案
      if (e instanceof ApiError && e.status === 404) {
        // 文件夹已被外部删除：从树中移除该节点
        // 同步 flush，保证调用方捕获异常时 UI 已反映节点移除
        flushSync(() => {
          setDirectoryTree((prev) => (prev ? removeSubtree(prev, path) : prev));
        });
      }
      throw e;
    } finally {
      setRefreshingPath(null);
    }
  }, [loadDirectoryTree]);

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
        // 二进制文件：直接传递 base64 数据，由具体查看器（如 PdfViewer）负责渲染
        textContent = file.data;
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

  const toggleNode = useCallback(async (path: string) => {
    // 先判断是否要展开（当前未展开）
    const willExpand = !expandedNodes.has(path);

    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });

    // 展开时加载子目录内容
    if (willExpand) {
      await loadSubDirectory(path);
    }
  }, [expandedNodes, loadSubDirectory]);

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
    setCurrentOssFile: setCurrentOssFileAction,
    refreshingPath,
    refreshingAll,
    refreshTree
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
