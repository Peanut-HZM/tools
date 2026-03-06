/**
 * 代码查看器组件
 * 支持语法高亮、折叠/展开、语言检测
 */
import React, { useState, useMemo } from 'react';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vs2015 } from 'react-syntax-highlighter/dist/cjs/styles/hljs';

// 支持的语言
import javascript from 'react-syntax-highlighter/dist/cjs/languages/hljs/javascript';
import typescript from 'react-syntax-highlighter/dist/cjs/languages/hljs/typescript';
import python from 'react-syntax-highlighter/dist/cjs/languages/hljs/python';
import java from 'react-syntax-highlighter/dist/cjs/languages/hljs/java';
import go from 'react-syntax-highlighter/dist/cjs/languages/hljs/go';
import bash from 'react-syntax-highlighter/dist/cjs/languages/hljs/bash';
import json from 'react-syntax-highlighter/dist/cjs/languages/hljs/json';
import plaintext from 'react-syntax-highlighter/dist/cjs/languages/hljs/plaintext';

SyntaxHighlighter.registerLanguage('javascript', javascript);
SyntaxHighlighter.registerLanguage('typescript', typescript);
SyntaxHighlighter.registerLanguage('python', python);
SyntaxHighlighter.registerLanguage('java', java);
SyntaxHighlighter.registerLanguage('go', go);
SyntaxHighlighter.registerLanguage('bash', bash);
SyntaxHighlighter.registerLanguage('json', json);
SyntaxHighlighter.registerLanguage('plaintext', plaintext);

interface CodeViewerProps {
  content: string;
  detectedLanguage?: string;
}

// 语言名称映射
const languageNames: Record<string, string> = {
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  python: 'Python',
  java: 'Java',
  go: 'Go',
  bash: 'Bash',
  json: 'JSON',
  plaintext: 'Plain Text',
};

const CodeViewer: React.FC<CodeViewerProps> = ({ content, detectedLanguage = 'plaintext' }) => {
  const [expanded, setExpanded] = useState(false);

  const { language, code, lineCount, displayContent } = useMemo(() => {
    // 解析代码块
    const codeBlockMatch = content.match(/^```(\w*)\n([\s\S]*?)```$/);
    let lang = detectedLanguage;
    let codeContent = content;

    if (codeBlockMatch) {
      lang = codeBlockMatch[1] || detectedLanguage;
      codeContent = codeBlockMatch[2].trim();
    }

    // 移除可能的结尾反引号
    codeContent = codeContent.replace(/```$/, '').trim();

    const lines = codeContent.split('\n');
    const linesCount = lines.length;

    // 如果未展开且超过 10 行，只显示前 10 行
    const displayLines = !expanded && linesCount > 10
      ? lines.slice(0, 10)
      : lines;

    return {
      language: lang || 'plaintext',
      code: codeContent,
      lineCount: linesCount,
      displayContent: displayLines.join('\n'),
    };
  }, [content, detectedLanguage, expanded]);

  const handleToggle = () => {
    setExpanded(!expanded);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const languageName = languageNames[language] || language;

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-lg">💻</span>
          <span className="text-sm font-medium text-slate-300">{languageName}</span>
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
            title="复制代码"
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
          language={language}
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

export default CodeViewer;
