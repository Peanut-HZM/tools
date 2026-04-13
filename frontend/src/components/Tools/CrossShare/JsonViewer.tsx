/**
 * JSON 查看器组件
 * 支持语法高亮、折叠/展开，操作按钮集成在头部（文本、MD、展开/折叠、删除）
 */
import React, { useState, useMemo } from 'react';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vs2015 } from 'react-syntax-highlighter/dist/cjs/styles/hljs';
import MessageActions from './MessageActions';

interface JsonViewerProps {
  content: string;
  messageId: string;
  onDelete: (messageId: string) => void;
  onCopySuccess: () => void;
}

const JsonViewer: React.FC<JsonViewerProps> = ({
  content,
  messageId,
  onDelete,
  onCopySuccess,
}) => {
  // 内部展开状态（用于控制代码区域的折叠）
  const [codeExpanded, setCodeExpanded] = useState(false);

  const { formattedJson, lineCount, displayContent } = useMemo(() => {
    try {
      const parsed = JSON.parse(content);
      const formatted = JSON.stringify(parsed, null, 2);
      const lines = formatted.split('\n');
      const count = lines.length;

      // 代码区域折叠：未展开且超过 10 行，只显示前 10 行
      const displayLines = !codeExpanded && count > 10
        ? lines.slice(0, 10)
        : lines;

      return {
        formattedJson: formatted,
        lineCount: count,
        displayContent: displayLines.join('\n'),
      };
    } catch {
      return {
        formattedJson: content,
        lineCount: content.split('\n').length,
        displayContent: content,
      };
    }
  }, [content, codeExpanded]);

  // 切换代码区域的展开/折叠
  const handleCodeToggle = () => {
    setCodeExpanded(!codeExpanded);
  };

  return (
    <div>
      {/* 头部：标题 + 操作按钮 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-slate-300">JSON</span>
          {lineCount > 10 && (
            <span className="text-xs text-slate-500">
              {codeExpanded ? `共 ${lineCount} 行` : `前 10 行 / 共 ${lineCount} 行`}
            </span>
          )}
        </div>
        <MessageActions
          content={content}
          messageId={messageId}
          onDelete={onDelete}
          onCopySuccess={onCopySuccess}
          isExpanded={codeExpanded}
          needsCollapse={lineCount > 10}
          onToggleExpand={handleCodeToggle}
        />
      </div>
      {/* 代码内容 */}
      <div className={`rounded-lg overflow-hidden border border-slate-600 ${!codeExpanded && lineCount > 10 ? 'max-h-64 overflow-hidden' : ''}`}>
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
      {/* 底部展开按钮 - 仅当代码区域折叠时显示 */}
      {!codeExpanded && lineCount > 10 && (
        <div className="mt-2 text-center">
          <button
            onClick={handleCodeToggle}
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
