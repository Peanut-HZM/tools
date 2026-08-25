import React, { useState, useEffect, useCallback } from 'react';
import { PRDVersion, prdApi } from '../../services/prdApi';
import { parseMermaidBlocks, renderMermaidToSvg, initMermaid } from '../../utils/mermaidRenderer';

interface PRDPreviewProps {
  conversationId: string;
  versionNumber?: number;
  onVersionChange?: (version: number) => void;
  onExport?: () => void;
}

const PRDPreview: React.FC<PRDPreviewProps> = ({
  conversationId,
  versionNumber,
  onVersionChange,
  onExport,
}) => {
  const [versions, setVersions] = useState<PRDVersion[]>([]);
  const [currentVersion, setCurrentVersion] = useState<number>(versionNumber || 1);
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mermaidSvgs, setMermaidSvgs] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<'preview' | 'source'>('preview');

  // 加载版本列表
  useEffect(() => {
    loadVersions();
    // 初始化 mermaid
    if (typeof window !== 'undefined') {
      initMermaid();
    }
  }, [conversationId]);

  // 加载当前版本内容
  useEffect(() => {
    if (versions.length > 0) {
      loadVersionContent(currentVersion);
    }
  }, [currentVersion, versions]);

  const loadVersions = async () => {
    try {
      setLoading(true);
      const data = await prdApi.getVersions(conversationId);
      setVersions(data);
      
      if (data.length > 0 && !versionNumber) {
        // 默认加载最新版本
        const latestVersion = Math.max(...data.map(v => v.version_number));
        setCurrentVersion(latestVersion);
      }
    } catch (err) {
      console.error('加载版本列表失败:', err);
      setError('加载版本列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadVersionContent = async (version: number) => {
    try {
      setLoading(true);
      const data = await prdApi.getVersion(conversationId, version);
      setContent(data.content);
      
      // 解析并渲染 Mermaid 图表
      const mermaidBlocks = parseMermaidBlocks(data.content);
      const svgMap: Record<string, string> = {};
      
      for (const block of mermaidBlocks) {
        try {
          const svg = await renderMermaidToSvg(block.code, block.type);
          svgMap[block.id] = svg;
        } catch (e) {
          console.error(`渲染图表 ${block.id} 失败:`, e);
          svgMap[block.id] = '<div class="text-red-500">图表渲染失败</div>';
        }
      }
      
      setMermaidSvgs(svgMap);
      setError(null);
    } catch (err) {
      console.error('加载版本内容失败:', err);
      setError('加载版本内容失败');
    } finally {
      setLoading(false);
    }
  };

  // 渲染 Markdown 内容（简单版本）
  const renderMarkdown = useCallback((text: string): React.ReactNode => {
    // 替换 Mermaid 代码块
    let result = text;
    const mermaidBlocks = parseMermaidBlocks(text);
    
    mermaidBlocks.forEach(block => {
      const svg = mermaidSvgs[block.id] || '';
      result = result.replace(
        /```mermaid\n[\s\S]*?```/,
        `<div class="mermaid-container my-4 p-4 bg-surface-1 rounded-lg">${svg}</div>`
      );
    });

    // 简单的 Markdown 渲染
    const lines = result.split('\n');
    const elements: React.ReactNode[] = [];
    let inList = false;
    let listItems: string[] = [];

    const processInline = (text: string): string => {
      // 处理加粗
      text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      // 处理斜体
      text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
      // 处理代码
      text = text.replace(/`(.*?)`/g, '<code class="px-1 py-0.5 bg-surface-2 rounded">$1</code>');
      // 处理链接
      text = text.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" class="text-accent-info hover:underline">$1</a>');
      return text;
    };

    lines.forEach((line, index) => {
      const trimmedLine = line.trim();
      
      // 标题
      if (trimmedLine.startsWith('# ')) {
        if (inList) {
          const listElements = listItems.map((item, i) => <li key={i} dangerouslySetInnerHTML={{ __html: processInline(item) }} />);
          elements.push(<ul key={`list-${index}`} className="list-disc pl-6 mb-2">{listElements}</ul>);
          listItems = [];
          inList = false;
        }
        const processedContent = processInline(trimmedLine.slice(2));
        elements.push(<h1 key={index} className="text-2xl font-bold mt-6 mb-4 text-accent-info" dangerouslySetInnerHTML={{ __html: processedContent }} />);
      } else if (trimmedLine.startsWith('## ')) {
        if (inList) {
          const listElements = listItems.map((item, i) => <li key={i} dangerouslySetInnerHTML={{ __html: processInline(item) }} />);
          elements.push(<ul key={`list-${index}`} className="list-disc pl-6 mb-2">{listElements}</ul>);
          listItems = [];
          inList = false;
        }
        const processedContent = processInline(trimmedLine.slice(3));
        elements.push(<h2 key={index} className="text-xl font-semibold mt-5 mb-3 text-accent-info" dangerouslySetInnerHTML={{ __html: processedContent }} />);
      } else if (trimmedLine.startsWith('### ')) {
        if (inList) {
          const listElements = listItems.map((item, i) => <li key={i} dangerouslySetInnerHTML={{ __html: processInline(item) }} />);
          elements.push(<ul key={`list-${index}`} className="list-disc pl-6 mb-2">{listElements}</ul>);
          listItems = [];
          inList = false;
        }
        const processedContent = processInline(trimmedLine.slice(4));
        elements.push(<h3 key={index} className="text-lg font-medium mt-4 mb-2 text-accent-info" dangerouslySetInnerHTML={{ __html: processedContent }} />);
      } 
      // 列表项
      else if (trimmedLine.startsWith('- ') || trimmedLine.startsWith('* ')) {
        inList = true;
        listItems.push(trimmedLine.slice(2));
      } 
      // 数字列表
      else if (/^\d+\.\s/.test(trimmedLine)) {
        if (inList) {
          const listElements = listItems.map((item, i) => <li key={i} dangerouslySetInnerHTML={{ __html: processInline(item) }} />);
          elements.push(<ul key={`list-${index}`} className="list-disc pl-6 mb-2">{listElements}</ul>);
          listItems = [];
        }
        const match = trimmedLine.match(/^(\d+)\.\s(.*)$/);
        if (match) {
          elements.push(<div key={index} className="flex mb-1"><span className="mr-2 text-ink-muted">{match[1]}.</span><span dangerouslySetInnerHTML={{ __html: processInline(match[2]) }} /></div>);
        }
      }
      // 分割线
      else if (trimmedLine === '---' || trimmedLine === '***') {
        elements.push(<hr key={index} className="my-4 border-border" />);
      }
      // 引用
      else if (trimmedLine.startsWith('> ')) {
        const processedContent = processInline(trimmedLine.slice(2));
        elements.push(<blockquote key={index} className="border-l-4 border-accent-info pl-4 py-1 my-2 text-ink-muted italic" dangerouslySetInnerHTML={{ __html: processedContent }} />);
      }
      // 表格 (简化处理)
      else if (trimmedLine.startsWith('|')) {
        // 简单表格处理
        const cells = trimmedLine.split('|').filter(c => c.trim());
        const isHeader = index > 0 && lines[index - 1]?.trim().startsWith('|') && !lines[index - 1]?.includes('---');
        
        if (!trimmedLine.includes('---')) {
          elements.push(
            <div key={index} className={`flex ${isHeader ? 'font-bold bg-surface-1' : ''} py-1`}>
              {cells.map((cell, i) => (
                <div key={i} className="flex-1 px-2" dangerouslySetInnerHTML={{ __html: processInline(cell.trim()) }} />
              ))}
            </div>
          );
        }
      }
      // 段落
      else if (trimmedLine.length > 0) {
        if (inList) {
          const listElements = listItems.map((item, i) => <li key={i} dangerouslySetInnerHTML={{ __html: processInline(item) }} />);
          elements.push(<ul key={`list-${index}`} className="list-disc pl-6 mb-2">{listElements}</ul>);
          listItems = [];
          inList = false;
        }
        const processedContent = processInline(trimmedLine);
        elements.push(<p key={index} className="my-2 text-ink-muted leading-relaxed" dangerouslySetInnerHTML={{ __html: processedContent }} />);
      }
    });

    // 处理最后剩余的列表
    if (inList && listItems.length > 0) {
      const listElements = listItems.map((item, i) => <li key={i} dangerouslySetInnerHTML={{ __html: processInline(item) }} />);
      elements.push(<ul key="final-list" className="list-disc pl-6 mb-2">{listElements}</ul>);
    }

    return elements;
  }, [mermaidSvgs]);

  if (loading && !content) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-ink-muted">加载中...</div>
      </div>
    );
  }

  if (error && !content) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-danger">{error}</div>
      </div>
    );
  }

  const currentVersionData = versions.find(v => v.version_number === currentVersion);

  return (
    <div className="flex flex-col h-full bg-canvas">
      {/* 头部工具栏 */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-ink-inverse">PRD 预览</h2>
          
          {/* 版本选择 */}
          <select
            value={currentVersion}
            onChange={(e) => {
              const version = parseInt(e.target.value);
              setCurrentVersion(version);
              onVersionChange?.(version);
            }}
            className="px-3 py-1.5 bg-surface-1 text-ink-inverse text-sm rounded border border-border focus:outline-none focus:border-accent-info"
          >
            {versions.map(v => (
              <option key={v.id} value={v.version_number}>
                V{v.version_number} {v.status === 'confirmed' ? '✓' : ''}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          {/* 标签切换 */}
          <div className="flex bg-surface-1 rounded-lg p-1">
            <button
              onClick={() => setActiveTab('preview')}
              className={`px-3 py-1 text-sm rounded ${
                activeTab === 'preview'
                  ? 'bg-accent text-white'
                  : 'text-ink-muted hover:text-ink-inverse'
              }`}
            >
              预览
            </button>
            <button
              onClick={() => setActiveTab('source')}
              className={`px-3 py-1 text-sm rounded ${
                activeTab === 'source'
                  ? 'bg-accent text-white'
                  : 'text-ink-muted hover:text-ink-inverse'
              }`}
            >
              源码
            </button>
          </div>

          {/* 导出按钮 */}
          <button
            onClick={onExport}
            className="px-3 py-1.5 bg-accent text-white text-sm rounded hover:bg-accent-hover flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            导出
          </button>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'preview' ? (
          <div className="prose prose-invert max-w-none">
            {renderMarkdown(content)}
          </div>
        ) : (
          <pre className="text-sm text-ink-muted whitespace-pre-wrap font-mono">
            {content}
          </pre>
        )}
      </div>

      {/* 底部状态栏 */}
      {currentVersionData && (
        <div className="p-3 border-t border-border flex items-center justify-between text-xs text-ink-muted">
          <span>
            状态: {currentVersionData.status === 'confirmed' ? '已确认' : currentVersionData.status === 'draft' ? '草稿' : '已归档'}
          </span>
          <span>
            创建时间: {new Date(currentVersionData.created_at).toLocaleString('zh-CN')}
          </span>
        </div>
      )}
    </div>
  );
};

export default PRDPreview;
