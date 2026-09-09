/**
 * SearchPanel Component - 内联搜索面板（文件名搜索 + 内容搜索）
 * 从 SearchDialog 重构而来，改为可折叠的内联面板，嵌入在顶部工具栏下方
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import './SearchPanel.css';
import * as markdownEditorApi from '../../../api/markdownEditorApi';
import type { FileSearchResult, ContentSearchResult } from '../../../types/markdownEditor';

interface SearchPanelProps {
  onClose: () => void;
  onFileSelect: (path: string) => void;
}

type SearchType = 'file' | 'content';

export default function SearchPanel({ onClose, onFileSelect }: SearchPanelProps) {
  const [searchType, setSearchType] = useState<SearchType>('file');
  const [keyword, setKeyword] = useState('');
  const [useRegex, setUseRegex] = useState(false);
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [fileResults, setFileResults] = useState<FileSearchResult[]>([]);
  const [contentResults, setContentResults] = useState<ContentSearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  // 搜索框自动聚焦
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    // 使用 setTimeout 等待面板渲染完成后再聚焦
    const timer = setTimeout(() => {
      inputRef.current?.focus();
    }, 50);
    return () => clearTimeout(timer);
  }, []);

  // 执行搜索
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
      setError(e instanceof Error ? e.message : '搜索失败');
    } finally {
      setIsSearching(false);
    }
  }, [keyword, searchType, useRegex, caseSensitive]);

  // 键盘事件：Enter 搜索，Escape 关闭
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  }, [handleSearch, onClose]);

  // 点击搜索结果中的文件
  const handleFileClick = useCallback((path: string) => {
    onFileSelect(path);
    onClose();
  }, [onFileSelect, onClose]);

  return (
    <div className="search-panel">
      <div className="search-panel-inner">
        {/* 左侧：搜索类型标签 */}
        <div className="search-panel-controls">
          <div className="search-type-tabs">
            <button
              onClick={() => setSearchType('file')}
              className={`search-type-tab ${searchType === 'file' ? 'active' : ''}`}
              title="按文件名搜索"
            >
              文件名
            </button>
            <button
              onClick={() => setSearchType('content')}
              className={`search-type-tab ${searchType === 'content' ? 'active' : ''}`}
              title="按文件内容搜索"
            >
              内容
            </button>
          </div>

          {/* 内容搜索选项 */}
          {searchType === 'content' && (
            <div className="search-options">
              <label className="search-option" title="使用正则表达式匹配">
                <input
                  type="checkbox"
                  checked={useRegex}
                  onChange={(e) => setUseRegex(e.target.checked)}
                />
                <span>正则</span>
              </label>
              <label className="search-option" title="区分大小写">
                <input
                  type="checkbox"
                  checked={caseSensitive}
                  onChange={(e) => setCaseSensitive(e.target.checked)}
                />
                <span>大小写</span>
              </label>
            </div>
          )}
        </div>

        {/* 中间：搜索输入框 */}
        <div className="search-panel-input-wrapper">
          <input
            ref={inputRef}
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={searchType === 'file' ? '输入文件名...' : '输入搜索内容...'}
            className="search-panel-input"
          />
        </div>

        {/* 右侧：操作按钮 */}
        <div className="search-panel-actions">
          <button
            onClick={handleSearch}
            disabled={isSearching || !keyword.trim()}
            className="search-panel-btn primary"
            title="开始搜索 (Enter)"
          >
            {isSearching ? '搜索中...' : '搜索'}
          </button>
          <button
            onClick={onClose}
            className="search-panel-btn"
            title="关闭搜索面板 (Escape)"
          >
            ✕
          </button>
        </div>
      </div>

      {/* 搜索结果区域 */}
      {(fileResults.length > 0 || contentResults.length > 0 || error || (keyword && !isSearching && fileResults.length === 0 && contentResults.length === 0)) && (
        <div className="search-panel-results">
          {error && (
            <div className="search-panel-error">{error}</div>
          )}

          {/* 文件名搜索结果 */}
          {searchType === 'file' && fileResults.length > 0 && (
            <div className="search-results-list">
              {fileResults.map((result) => (
                <div
                  key={result.path}
                  onClick={() => handleFileClick(result.path)}
                  className="search-result-item"
                >
                  <div className="search-result-name">{result.name}</div>
                  <div className="search-result-path">{result.path}</div>
                </div>
              ))}
            </div>
          )}

          {/* 内容搜索结果 */}
          {searchType === 'content' && contentResults.length > 0 && (
            <div className="search-results-list">
              {contentResults.map((result) => (
                <div key={result.file} className="search-result-group">
                  <div
                    onClick={() => handleFileClick(result.file)}
                    className="search-result-file"
                  >
                    <span className="search-result-name">{result.file}</span>
                    <span className="search-result-count">{result.matches.length} 个匹配</span>
                  </div>
                  <div className="search-result-matches">
                    {result.matches.slice(0, 3).map((match, idx) => (
                      <div key={idx} className="search-result-match">
                        <span className="match-line">行 {match.line}:</span>
                        <span className="match-content">{match.content}</span>
                      </div>
                    ))}
                    {result.matches.length > 3 && (
                      <div className="search-result-more">
                        还有 {result.matches.length - 3} 个匹配...
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 无结果 */}
          {!isSearching && keyword && fileResults.length === 0 && contentResults.length === 0 && !error && (
            <div className="search-panel-empty">未找到匹配结果</div>
          )}
        </div>
      )}
    </div>
  );
}
