/**
 * Unified File Tree Component - Displays local and OSS files
 */
import { useEffect } from 'react';
import { useFileStore } from '../../../stores/fileStore';
import { useOssFiles } from '../../../hooks/useOssFiles';
import FileTree from './FileTree';

export default function UnifiedFileTree() {
  const {
    directoryTree,
    currentFilePath,
    expandedNodes,
    ossFiles,
    ossFilesLoading,
    loadDirectoryTree,
    openFile,
    toggleNode,
    loadOssFiles
  } = useFileStore();

  // Load both local and OSS files
  useEffect(() => {
    loadDirectoryTree();
    loadOssFiles();
  }, [loadDirectoryTree, loadOssFiles]);

  const handleFileSelect = async (path: string) => {
    // Check if it's an OSS file
    const isOssFile = ossFiles.some(f => f.file_path === path);
    
    if (isOssFile) {
      // Handle OSS file opening
      await openFile(path);
    } else {
      // Handle local file
      await openFile(path);
    }
  };

  if (ossFilesLoading) {
    return (
      <div className="h-full flex items-center justify-center text-ink-muted">
        <div className="animate-spin mr-2">⟳</div>
        加载中...
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      {/* OSS Files Section */}
      {ossFiles.length > 0 && (
        <div className="mb-4">
          <div className="px-3 py-2 text-xs font-medium text-ink-faint uppercase tracking-wider">
            云端文件
          </div>
          {ossFiles.map((file) => (
            <div
              key={file.file_path}
              className={`file-tree-item flex items-center px-3 py-1.5 cursor-pointer hover:bg-surface-2 ${
                currentFilePath === file.file_path ? 'bg-accent-info/30 border-l-2 border-accent-cyan' : ''
              }`}
              onClick={() => handleFileSelect(file.file_path)}
            >
              {/* Cloud Icon */}
              <svg 
                className="w-4 h-4 mr-2 text-accent" 
                fill="currentColor" 
                viewBox="0 0 20 20"
              >
                <path d="M5.5 16a3.5 3.5 0 01-.369-6.98 4 4 0 117.753-1.977A4.5 4.5 0 1113.5 16h-8z" />
              </svg>
              <span className="text-sm text-ink-muted truncate">{file.filename}</span>
              <span className="ml-auto text-xs text-ink-faint">
                {(file.size / 1024).toFixed(1)}KB
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Local Files Section */}
      {directoryTree && (
        <div>
          <div className="px-3 py-2 text-xs font-medium text-ink-faint uppercase tracking-wider">
            本地文件
          </div>
          <FileTree
            tree={directoryTree}
            currentFilePath={currentFilePath}
            expandedNodes={expandedNodes}
            onFileSelect={handleFileSelect}
            onToggleNode={toggleNode}
          />
        </div>
      )}

      {/* Empty State */}
      {!ossFilesLoading && ossFiles.length === 0 && !directoryTree && (
        <div className="p-4 text-ink-muted text-sm text-center">
          暂无文件
        </div>
      )}
    </div>
  );
}
