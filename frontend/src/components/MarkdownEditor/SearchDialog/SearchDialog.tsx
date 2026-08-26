/**
 * SearchDialog Component - File and content search
 */
import { useState, useCallback } from 'react';
import * as markdownEditorApi from '../../../api/markdownEditorApi';
import type { FileSearchResult, ContentSearchResult } from '../../../types/markdownEditor';

interface SearchDialogProps {
  open: boolean;
  onClose: () => void;
  onFileSelect: (path: string) => void;
}

type SearchType = 'file' | 'content';

export default function SearchDialog({ open, onClose, onFileSelect }: SearchDialogProps) {
  const [searchType, setSearchType] = useState<SearchType>('file');
  const [keyword, setKeyword] = useState('');
  const [useRegex, setUseRegex] = useState(false);
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [fileResults, setFileResults] = useState<FileSearchResult[]>([]);
  const [contentResults, setContentResults] = useState<ContentSearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async () => {
    if (!keyword.trim()) return;

    setIsSearching(true);
    setError(null);
    setFileResults([]);
    setContentResults([]);

    try {
      if (searchType === 'file') {
        const results = await markdownEditorApi.searchFiles(keyword);
        setFileResults(results);
      } else {
        const results = await markdownEditorApi.searchContent(keyword, useRegex, caseSensitive);
        setContentResults(results);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setIsSearching(false);
    }
  }, [keyword, searchType, useRegex, caseSensitive]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
    if (e.key === 'Escape') {
      onClose();
    }
  }, [handleSearch, onClose]);

  const handleFileClick = useCallback((path: string) => {
    onFileSelect(path);
    onClose();
  }, [onFileSelect, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-start justify-center pt-20 z-50">
      <div className="bg-surface-1 rounded-xl shadow-lg w-full max-w-2xl max-h-[70vh] flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-ink">搜索</h2>
            <button
              onClick={onClose}
              className="text-ink-muted hover:text-ink cursor-pointer"
            >
              ✕
            </button>
          </div>

          {/* Search Type Tabs */}
          <div className="flex gap-2 mb-3">
            <button
              onClick={() => setSearchType('file')}
              className={`px-3 py-1 rounded text-sm cursor-pointer ${
                searchType === 'file'
                  ? 'bg-accent text-ink-inverse'
                  : 'bg-surface-2 text-ink-muted hover:bg-surface-3'
              }`}
            >
              文件名搜索
            </button>
            <button
              onClick={() => setSearchType('content')}
              className={`px-3 py-1 rounded text-sm cursor-pointer ${
                searchType === 'content'
                  ? 'bg-accent text-ink-inverse'
                  : 'bg-surface-2 text-ink-muted hover:bg-surface-3'
              }`}
            >
              内容搜索
            </button>
          </div>

          {/* Search Input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={searchType === 'file' ? '输入文件名...' : '输入搜索内容...'}
              className="flex-1 px-3 py-2 bg-surface-2 border border-border rounded text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent-cyan"
              autoFocus
            />
            <button
              onClick={handleSearch}
              disabled={isSearching || !keyword.trim()}
              className="px-4 py-2 bg-accent hover:bg-accent-hover disabled:bg-accent/50 text-ink-inverse rounded text-sm cursor-pointer"
            >
              {isSearching ? '搜索中...' : '搜索'}
            </button>
          </div>

          {/* Content Search Options */}
          {searchType === 'content' && (
            <div className="flex gap-4 mt-3">
              <label className="flex items-center gap-2 text-sm text-ink-muted cursor-pointer">
                <input
                  type="checkbox"
                  checked={useRegex}
                  onChange={(e) => setUseRegex(e.target.checked)}
                  className="rounded"
                />
                正则表达式
              </label>
              <label className="flex items-center gap-2 text-sm text-ink-muted cursor-pointer">
                <input
                  type="checkbox"
                  checked={caseSensitive}
                  onChange={(e) => setCaseSensitive(e.target.checked)}
                  className="rounded"
                />
                区分大小写
              </label>
            </div>
          )}
        </div>

        {/* Results */}
        <div className="flex-1 overflow-auto p-4">
          {error && (
            <div className="text-danger text-sm mb-4">{error}</div>
          )}

          {/* File Search Results */}
          {searchType === 'file' && fileResults.length > 0 && (
            <div className="space-y-2">
              {fileResults.map((result) => (
                <div
                  key={result.path}
                  onClick={() => handleFileClick(result.path)}
                  className="p-3 bg-surface-2/50 rounded-lg hover:bg-surface-2 cursor-pointer"
                >
                  <div className="text-ink text-sm font-medium">{result.name}</div>
                  <div className="text-ink-muted text-xs mt-1">{result.path}</div>
                </div>
              ))}
            </div>
          )}

          {/* Content Search Results */}
          {searchType === 'content' && contentResults.length > 0 && (
            <div className="space-y-4">
              {contentResults.map((result) => (
                <div key={result.file} className="bg-surface-2/50 rounded-lg overflow-hidden">
                  <div
                    onClick={() => handleFileClick(result.file)}
                    className="p-3 bg-surface-2 cursor-pointer hover:bg-surface-3"
                  >
                    <div className="text-ink text-sm font-medium">{result.file}</div>
                    <div className="text-ink-muted text-xs mt-1">
                      {result.matches.length} 个匹配
                    </div>
                  </div>
                  <div className="p-3 space-y-2">
                    {result.matches.slice(0, 5).map((match, idx) => (
                      <div key={idx} className="text-sm">
                        <span className="text-ink-faint">行 {match.line}: </span>
                        <span className="text-ink-muted">{match.content}</span>
                      </div>
                    ))}
                    {result.matches.length > 5 && (
                      <div className="text-ink-faint text-xs">
                        还有 {result.matches.length - 5} 个匹配...
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* No Results */}
          {!isSearching && keyword && fileResults.length === 0 && contentResults.length === 0 && !error && (
            <div className="text-center text-ink-muted py-8">
              未找到匹配结果
            </div>
          )}

          {/* Initial State */}
          {!keyword && (
            <div className="text-center text-ink-muted py-8">
              输入关键词开始搜索
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
