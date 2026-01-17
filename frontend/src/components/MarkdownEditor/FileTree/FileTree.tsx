/**
 * FileTree Component - Displays directory tree structure
 */
import { useState, useCallback } from 'react';
import type { FileNode } from '../../../types/markdownEditor';

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
          <span className="file-tree-icon text-slate-500" style={{ fontSize: '10px', marginRight: '4px' }}>
            {hasChildren ? (isExpanded ? '▼' : '▶') : ''}
          </span>
        )}
        
        {/* File/Folder Icon */}
        <span className="file-tree-icon">
          {isDirectory ? (
            <svg className="text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
            </svg>
          ) : (
            <svg className="text-slate-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
            </svg>
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
  onRenameFile
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

  const handleContextMenu = useCallback((e: React.MouseEvent, node: FileNode) => {
    setContextMenu({ x: e.clientX, y: e.clientY, node });
  }, []);

  const closeContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

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

  if (!tree) {
    return (
      <div className="p-4 text-slate-400 text-sm">
        加载中...
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto" onClick={closeContextMenu}>
      {/* Tree Content */}
      {tree.children && tree.children.length > 0 ? (
        tree.children.map((node) => (
          <TreeNode
            key={node.path}
            node={node}
            level={0}
            currentFilePath={currentFilePath}
            expandedNodes={expandedNodes}
            onFileSelect={onFileSelect}
            onToggleNode={onToggleNode}
            onContextMenu={handleContextMenu}
          />
        ))
      ) : (
        <div className="p-4 text-slate-400 text-sm text-center">
          暂无文件
        </div>
      )}

      {/* Context Menu */}
      {contextMenu && (
        <div
          className="fixed bg-slate-800 border border-slate-600 rounded-lg shadow-xl py-1 z-50"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 cursor-pointer"
            onClick={handleNewFile}
          >
            新建文件
          </button>
          <button
            className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 cursor-pointer"
            onClick={handleNewDirectory}
          >
            新建文件夹
          </button>
          <div className="border-t border-slate-600 my-1" />
          <button
            className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-slate-700 cursor-pointer"
            onClick={handleDelete}
          >
            删除
          </button>
        </div>
      )}

      {/* New File Input Modal */}
      {showNewFileInput && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-4 w-80">
            <h3 className="text-white font-medium mb-3">新建文件</h3>
            <input
              type="text"
              value={newItemName}
              onChange={(e) => setNewItemName(e.target.value)}
              placeholder="文件名.md"
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm mb-3"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreateFile();
                if (e.key === 'Escape') setShowNewFileInput(false);
              }}
            />
            <div className="flex justify-end gap-2">
              <button
                className="px-3 py-1 text-sm text-slate-400 hover:text-white cursor-pointer"
                onClick={() => setShowNewFileInput(false)}
              >
                取消
              </button>
              <button
                className="px-3 py-1 text-sm bg-cyan-500 text-white rounded hover:bg-cyan-600 cursor-pointer"
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
          <div className="bg-slate-800 rounded-lg p-4 w-80">
            <h3 className="text-white font-medium mb-3">新建文件夹</h3>
            <input
              type="text"
              value={newItemName}
              onChange={(e) => setNewItemName(e.target.value)}
              placeholder="文件夹名称"
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm mb-3"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreateDirectory();
                if (e.key === 'Escape') setShowNewDirInput(false);
              }}
            />
            <div className="flex justify-end gap-2">
              <button
                className="px-3 py-1 text-sm text-slate-400 hover:text-white cursor-pointer"
                onClick={() => setShowNewDirInput(false)}
              >
                取消
              </button>
              <button
                className="px-3 py-1 text-sm bg-cyan-500 text-white rounded hover:bg-cyan-600 cursor-pointer"
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
