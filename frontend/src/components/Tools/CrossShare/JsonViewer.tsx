/**
 * JSON 查看器组件
 * 支持语法高亮、折叠/展开
 */
import React, { useState, useMemo } from 'react';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vs2015 } from 'react-syntax-highlighter/dist/cjs/styles/hljs';

interface JsonViewerProps {
  content: string;
}

const JsonViewer: React.FC<JsonViewerProps> = ({ content }) => {
  const [expanded, setExpanded] = useState(false);

  const { formattedJson, lineCount, displayContent } = useMemo(() => {
    try {
      const parsed = JSON.parse(content);
      const formatted = JSON.stringify(parsed, null, 2);
      const lines = formatted.split('\n');
      const lineCount = lines.length;

      // 如果未展开且超过 10 行，只显示前 10 行
      const displayLines = !expanded && lineCount > 10
        ? lines.slice(0, 10)
        : lines;

      return {
        formattedJson: formatted,
        lineCount,
        displayContent: displayLines.join('\n'),
      };
    } catch {
      return {
        formattedJson: content,
        lineCount: content.split('\n').length,
        displayContent: content,
      };
    }
  }, [content, expanded]);

  const handleToggle = () => {
    setExpanded(!expanded);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formattedJson);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-lg">📋</span>
          <span className="text-sm font-medium text-slate-300">JSON</span>
          {lineCount > 10 && (
            <span className="text-xs text-slate-500">
              {expanded ? `共 ${lineCount} 行` : `前 10 行 / 共 ${lineCount} 行`}
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleCopy}
            className="px-2 py-1 text-xs bg-slate-600 hover:bg-slate-500 text-slate-200 rounded transition-colors"
            title="复制 JSON"
          >
            📋 复制
          </button>
          {lineCount > 10 && (
            <button
              onClick={handleToggle}
              className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
            >
              {expanded ? '▲ 折叠' : '▼ 展开'}
            </button>
          )}
        </div>
      </div>
      <div className={`rounded-lg overflow-hidden border border-slate-600 ${!expanded && lineCount > 10 ? 'max-h-64 overflow-hidden' : ''}`}>
        <SyntaxHighlighter
          language="json"
          style={vs2015}
          customStyle={{
            margin: 0,
            borderRadius: '0.5rem',
            fontSize: '0.875rem',
          }}
          showLineNumbers={true}
          wrapLines={true}
        >
          {displayContent}
        </SyntaxHighlighter>
      </div>
      {!expanded && lineCount > 10 && (
        <div className="mt-2 text-center">
          <button
            onClick={handleToggle}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            点击展开查看完整内容 ({lineCount} 行)
          </button>
        </div>
      )}
    </div>
  );
};

export default JsonViewer;
