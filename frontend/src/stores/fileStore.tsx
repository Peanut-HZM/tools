/**
 * File Store - Manages directory tree and current file state using React Context
 */
import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import * as markdownEditorApi from '../api/markdownEditorApi';
import type { FileNode, FileContent } from '../types/markdownEditor';

export interface FileState {
  directoryTree: FileNode | null;
  currentFile: FileContent | null;
  currentFilePath: string;
  rootPath: string;
  hasRootPath: boolean;
  isLoading: boolean;
  error: string | null;
  expandedNodes: Set<string>;
}

export interface FileActions {
  loadRootPath: () => Promise<RootPathResponse>;
  setRootPath: (path: string) => Promise<void>;
  loadDirectoryTree: (subPath?: string) => Promise<void>;
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
}

export type FileContextType = FileState & FileActions;

const FileContext = createContext<FileContextType | null>(null);

export function FileProvider({ children }: { children: ReactNode }) {
  const [directoryTree, setDirectoryTree] = useState<FileNode | null>(null);
  const [currentFile, setCurrentFile] = useState<FileContent | null>(null);
  const [currentFilePath, setCurrentFilePath] = useState('');
  const [rootPath, setRootPath] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

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

  const loadDirectoryTree = useCallback(async (subPath: string = '') => {
    setIsLoading(true);
    setError(null);
    try {
      const tree = await markdownEditorApi.getDirectoryTree(subPath);
      setDirectoryTree(tree);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load directory tree');
      throw e;
    } finally {
      setIsLoading(false);
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
      const file = await markdownEditorApi.readFile(path);
      setCurrentFile(file);
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

  const value: FileContextType = {
    directoryTree,
    currentFile,
    currentFilePath,
    rootPath,
    hasRootPath: !!rootPath,
    isLoading,
    error,
    expandedNodes,
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
    clearError
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
