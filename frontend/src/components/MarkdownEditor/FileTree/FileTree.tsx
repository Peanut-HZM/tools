/**
 * FileTree Component - Displays directory tree structure
 */
import { useState, useCallback, useMemo } from 'react';
import type { FileNode } from '../../../types/markdownEditor';
import { getFilePaths } from '../../../api/markdownEditorApi';

/** 文件类型图标与颜色映射 */
const FILE_ICONS: Record<string, { icon: string; color: string }> = {
  markdown: { icon: '📝', color: '#3b82f6' },
  html: { icon: '🌐', color: '#f97316' },
  text: { icon: '📄', color: '#6b7280' },
  image: { icon: '🖼️', color: '#10b981' },
  code: { icon: '💻', color: '#8b5cf6' },
  other: { icon: '📄', color: '#9ca3af' },
};

/** 根据文件类型获取图标 emoji */
function getFileIconEmoji(node: FileNode): string {
  if (node.file_type && FILE_ICONS[node.file_type]) {
    return FILE_ICONS[node.file_type].icon;
  }
  return FILE_ICONS.other.icon;
}

/** 根据文件类型获取图标颜色 */
function getIconColor(node: FileNode): string {
  if (node.file_type && FILE_ICONS[node.file_type]) {
    return FILE_ICONS[node.file_type].color;
  }
  return FILE_ICONS.other.color;
}

interface FileTreeProps {
  tree: FileNode | null;
  currentFilePath: string;
  expandedNodes: Set<string>;
  onFileSelect: (path: string) => void;
  onToggleNode: (path: string) => void;
  onCreateFile?: (path: string) => void;
  onCreateDirectory?: (path: string) => void;
  onDeleteFile?: (path: string) => void;
  onDeleteDirectory?: (path: string) => void;
  onRenameFile?: (oldPath: string, newPath: string) => void;
  onCopyPath?: (message: string) => void;
  rootPath?: string;
}

interface TreeNodeProps {
  node: FileNode;
  level: number;
  currentFilePath: string;
  expandedNodes: Set<string>;
  onFileSelect: (path: string) => void;
  onToggleNode: (path: string) => void;
  onContextMenu?: (e: React.MouseEvent, node: FileNode) => void;
}

/**
 * 递归过滤文件树节点，同时收集需要自动展开的目录路径
 * @param node 当前节点
 * @param query 搜索关键词
 * @param expandPaths 收集需要展开的目录路径
 * @returns 过滤后的节点，如果无匹配则返回 null
 */
function filterTree(
  node: FileNode,
  query: string,
  expandPaths: Set<string>
): FileNode | null {
  if (!query) return node;

  const lowerQuery = query.toLowerCase();
  const nameMatch = node.name.toLowerCase().includes(lowerQuery);

  // 文件节点：名称匹配则保留，否则过滤
  if (node.type === 'file') {
    return nameMatch ? node : null;
  }

  // 目录节点：递归过滤子节点
  const filteredChildren = node.children
    ?.map(child => filterTree(child, query, expandPaths))
    .filter(Boolean) as FileNode[];

  // 如果目录名匹配或子目录有匹配项，保留该目录
  if (nameMatch || (filteredChildren && filteredChildren.length > 0)) {
    // 如果有匹配的子节点，说明此目录需要自动展开
    if (filteredChildren && filteredChildren.length > 0) {
      expandPaths.add(node.path);
    }
    return { ...node, children: filteredChildren || [] };
  }

  return null;
}

function TreeNode({
  node,
  level,
  currentFilePath,
  expandedNodes,
  onFileSelect,
  onToggleNode,
  onContextMenu
}: TreeNodeProps) {
  const isExpanded = expandedNodes.has(node.path);
  const isSelected = node.path === currentFilePath;
  const isDirectory = node.type === 'directory';
  const hasChildren = isDirectory && node.children && node.children.length > 0;

  const handleClick = useCallback(() => {
    if (isDirectory) {
      onToggleNode(node.path);
    } else {
      onFileSelect(node.path);
    }
  }, [isDirectory, node.path, onToggleNode, onFileSelect]);

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    onContextMenu?.(e, node);
  }, [node, onContextMenu]);

  return (
    <div>
      <div
        className={`file-tree-item ${isSelected ? 'active' : ''}`}
        style={{ paddingLeft: `${level * 16 + 12}px` }}
        onClick={handleClick}
        onContextMenu={handleContextMenu}
      >
        {/* Expand/Collapse Icon */}
        {isDirectory && (
          <span className="file-tree-icon text-ink-faint" style={{ fontSize: '10px', marginRight: '4px' }}>
            {hasChildren ? (isExpanded ? '▼' : '▶') : ''}
          </span>
        )}
        
        {/* File/Folder Icon */}
        <span className="file-tree-icon" style={{ color: getIconColor(node) }}>
          {isDirectory ? (
            <svg className="text-warning" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
            </svg>
          ) : (
            <span className="text-xs">{getFileIconEmoji(node)}</span>
          )}
        </span>
        
        {/* Name */}
        <span className="truncate text-sm">{node.name}</span>
      </div>
      
      {/* Children */}
      {isDirectory && isExpanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              level={level + 1}
              currentFilePath={currentFilePath}
              expandedNodes={expandedNodes}
              onFileSelect={onFileSelect}
              onToggleNode={onToggleNode}
              onContextMenu={onContextMenu}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function FileTree({
  tree,
  currentFilePath,
  expandedNodes,
  onFileSelect,
  onToggleNode,
  onCreateFile,
  onCreateDirectory,
  onDeleteFile,
  onDeleteDirectory,
  onRenameFile,
  onCopyPath,
  rootPath,
}: FileTreeProps) {
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    node: FileNode;
  } | null>(null);
  const [showNewFileInput, setShowNewFileInput] = useState(false);
  const [showNewDirInput, setShowNewDirInput] = useState(false);
  const [newItemName, setNewItemName] = useState('');
  const [contextPath, setContextPath] = useState('');
  // 文件搜索关键词
  const [fileSearchQuery, setFileSearchQuery] = useState('');

  const handleContextMenu = useCallback((e: React.MouseEvent, node: FileNode) => {
    setContextMenu({ x: e.clientX, y: e.clientY, node });
  }, []);

  const closeContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  /** 复制绝对路径 */
  const handleCopyAbsolutePath = useCallback(async () => {
    if (contextMenu) {
      try {
        const paths = await getFilePaths(contextMenu.node.path);
        await navigator.clipboard.writeText(paths.absolute_path);
        onCopyPath?.(`已复制绝对路径: ${paths.absolute_path}`);
      } catch {
        onCopyPath?.('复制绝对路径失败');
      }
      closeContextMenu();
    }
  }, [contextMenu, closeContextMenu, onCopyPath]);

  /** 复制相对路径 */
  const handleCopyRelativePath = useCallback(async () => {
    if (contextMenu) {
      try {
        const paths = await getFilePaths(contextMenu.node.path);
        await navigator.clipboard.writeText(paths.relative_path);
        onCopyPath?.(`已复制相对路径: ${paths.relative_path}`);
      } catch {
        // 如果 API 失败，回退使用节点路径
        await navigator.clipboard.writeText(contextMenu.node.path);
        onCopyPath?.(`已复制相对路径: ${contextMenu.node.path}`);
      }
      closeContextMenu();
    }
  }, [contextMenu, closeContextMenu, onCopyPath]);

  /** 复制文件名 */
  const handleCopyFileName = useCallback(() => {
    if (contextMenu) {
      navigator.clipboard.writeText(contextMenu.node.name);
      onCopyPath?.(`已复制文件名: ${contextMenu.node.name}`);
      closeContextMenu();
    }
  }, [contextMenu, closeContextMenu, onCopyPath]);

  const handleNewFile = useCallback(() => {
    if (contextMenu) {
      const basePath = contextMenu.node.type === 'directory' 
        ? contextMenu.node.path 
        : contextMenu.node.path.split('/').slice(0, -1).join('/');
      setContextPath(basePath);
      setShowNewFileInput(true);
      closeContextMenu();
    }
  }, [contextMenu, closeContextMenu]);

  const handleNewDirectory = useCallback(() => {
    if (contextMenu) {
      const basePath = contextMenu.node.type === 'directory' 
        ? contextMenu.node.path 
        : contextMenu.node.path.split('/').slice(0, -1).join('/');
      setContextPath(basePath);
      setShowNewDirInput(true);
      closeContextMenu();
    }
  }, [contextMenu, closeContextMenu]);

  const handleDelete = useCallback(() => {
    if (contextMenu) {
      if (contextMenu.node.type === 'directory') {
        onDeleteDirectory?.(contextMenu.node.path);
      } else {
        onDeleteFile?.(contextMenu.node.path);
      }
      closeContextMenu();
    }
  }, [contextMenu, onDeleteFile, onDeleteDirectory, closeContextMenu]);

  const handleCreateFile = useCallback(() => {
    if (newItemName.trim()) {
      const path = contextPath ? `${contextPath}/${newItemName.trim()}` : newItemName.trim();
      const finalPath = path.endsWith('.md') ? path : `${path}.md`;
      onCreateFile?.(finalPath);
      setNewItemName('');
      setShowNewFileInput(false);
    }
  }, [newItemName, contextPath, onCreateFile]);

  const handleCreateDirectory = useCallback(() => {
    if (newItemName.trim()) {
      const path = contextPath ? `${contextPath}/${newItemName.trim()}` : newItemName.trim();
      onCreateDirectory?.(path);
      setNewItemName('');
      setShowNewDirInput(false);
    }
  }, [newItemName, contextPath, onCreateDirectory]);

  // 使用 useMemo 缓存过滤后的树和自动展开路径（必须在所有条件返回之前）
  const { filteredTree, autoExpandPaths } = useMemo(() => {
    if (!tree) return { filteredTree: null, autoExpandPaths: new Set<string>() };
    const expandPaths = new Set<string>();
    const filtered = filterTree(tree, fileSearchQuery, expandPaths);
    return { filteredTree: filtered, autoExpandPaths: expandPaths };
  }, [tree, fileSearchQuery]);

  // 搜索时合并用户手动展开和自动展开的路径
  const effectiveExpandedNodes = useMemo(() => {
    if (!fileSearchQuery || autoExpandPaths.size === 0) {
      return expandedNodes;
    }
    return new Set([...expandedNodes, ...autoExpandPaths]);
  }, [expandedNodes, fileSearchQuery, autoExpandPaths]);

  // 清除搜索
  const handleClearSearch = useCallback(() => {
    setFileSearchQuery('');
  }, []);

  // 搜索框按键处理
  const handleSearchKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      setFileSearchQuery('');
      e.currentTarget.blur();
    }
  }, []);

  if (!tree) {
    return (
      <div className="p-4 text-ink-muted text-sm">
        加载中...
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto flex flex-col" onClick={closeContextMenu}>
      {/* 搜索框 */}
      <div className="file-tree-search px-3 py-2 border-b border-border shrink-0">
        <div className="relative">
          <input
            type="text"
            placeholder="搜索文件名..."
            value={fileSearchQuery}
            onChange={(e) => setFileSearchQuery(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            className="w-full px-2 py-1 pr-7 text-sm bg-surface-2 border border-border rounded text-ink"
          />
          {fileSearchQuery && (
            <button
              onClick={handleClearSearch}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 text-ink-faint hover:text-ink text-xs cursor-pointer"
              title="清除搜索 (Esc)"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Tree Content */}
      <div className="flex-1 overflow-auto">
        {filteredTree && filteredTree.children && filteredTree.children.length > 0 ? (
          filteredTree.children.map((node) => (
            <TreeNode
              key={node.path}
              node={node}
              level={0}
              currentFilePath={currentFilePath}
              expandedNodes={effectiveExpandedNodes}
              onFileSelect={onFileSelect}
              onToggleNode={onToggleNode}
              onContextMenu={handleContextMenu}
            />
          ))
        ) : (
          <div className="p-4 text-ink-muted text-sm text-center">
            {fileSearchQuery ? '无匹配文件' : '暂无文件'}
          </div>
        )}
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <div
          className="fixed bg-surface-1 border border-border rounded-lg shadow-md py-1 z-50"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* 复制路径菜单项（仅文件节点显示） */}
          {contextMenu.node.type === 'file' && (
            <>
              <button
                className="w-full px-4 py-2 text-left text-sm text-ink-muted hover:bg-surface-2 cursor-pointer"
                onClick={handleCopyAbsolutePath}
              >
                复制绝对路径
              </button>
              <button
                className="w-full px-4 py-2 text-left text-sm text-ink-muted hover:bg-surface-2 cursor-pointer"
                onClick={handleCopyRelativePath}
              >
                复制相对路径
              </button>
              <button
                className="w-full px-4 py-2 text-left text-sm text-ink-muted hover:bg-surface-2 cursor-pointer"
                onClick={handleCopyFileName}
              >
                复制文件名
              </button>
              <div className="border-t border-border my-1" />
            </>
          )}
          <button
            className="w-full px-4 py-2 text-left text-sm text-ink-muted hover:bg-surface-2 cursor-pointer"
            onClick={handleNewFile}
          >
            新建文件
          </button>
          <button
            className="w-full px-4 py-2 text-left text-sm text-ink-muted hover:bg-surface-2 cursor-pointer"
            onClick={handleNewDirectory}
          >
            新建文件夹
          </button>
          <div className="border-t border-border my-1" />
          <button
            className="w-full px-4 py-2 text-left text-sm text-danger hover:bg-surface-2 cursor-pointer"
            onClick={handleDelete}
          >
            删除
          </button>
        </div>
      )}

      {/* New File Input Modal */}
      {showNewFileInput && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface-1 rounded-lg p-4 w-80">
            <h3 className="text-ink font-medium mb-3">新建文件</h3>
            <input
              type="text"
              value={newItemName}
              onChange={(e) => setNewItemName(e.target.value)}
              placeholder="文件名.md"
              className="w-full px-3 py-2 bg-surface-2 border border-border rounded text-ink text-sm mb-3"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreateFile();
                if (e.key === 'Escape') setShowNewFileInput(false);
              }}
            />
            <div className="flex justify-end gap-2">
              <button
                className="px-3 py-1 text-sm text-ink-muted hover:text-ink cursor-pointer"
                onClick={() => setShowNewFileInput(false)}
              >
                取消
              </button>
              <button
                className="px-3 py-1 text-sm bg-accent text-ink-inverse rounded hover:bg-accent-hover cursor-pointer"
                onClick={handleCreateFile}
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Directory Input Modal */}
      {showNewDirInput && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface-1 rounded-lg p-4 w-80">
            <h3 className="text-ink font-medium mb-3">新建文件夹</h3>
            <input
              type="text"
              value={newItemName}
              onChange={(e) => setNewItemName(e.target.value)}
              placeholder="文件夹名称"
              className="w-full px-3 py-2 bg-surface-2 border border-border rounded text-ink text-sm mb-3"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreateDirectory();
                if (e.key === 'Escape') setShowNewDirInput(false);
              }}
            />
            <div className="flex justify-end gap-2">
              <button
                className="px-3 py-1 text-sm text-ink-muted hover:text-ink cursor-pointer"
                onClick={() => setShowNewDirInput(false)}
              >
                取消
              </button>
              <button
                className="px-3 py-1 text-sm bg-accent text-ink-inverse rounded hover:bg-accent-hover cursor-pointer"
                onClick={handleCreateDirectory}
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
