/**
 * HtmlPreview 组件 - 通过 iframe sandbox 安全渲染 HTML 文件内容
 * 支持 JavaScript 执行和表单提交，同时隔离父页面访问
 *
 * 使用 blob: URL 作为 iframe src（而非 srcDoc），以便 sandbox 中的脚本可以执行。
 * sandbox="allow-scripts allow-forms" 允许脚本和表单但禁止 same-origin，
 * 因此脚本无法访问父页面的 DOM、Cookie 或 localStorage。
 */
import { useEffect, useRef } from 'react';

interface HtmlPreviewProps {
  content: string;
  theme: 'light' | 'dark';
}

export default function HtmlPreview({ content, theme }: HtmlPreviewProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!iframeRef.current) return;

    // 将 HTML 内容包装为 Blob 并生成 blob: URL，iframe 加载后可执行其中的脚本
    const blob = new Blob([content], { type: 'text/html' });
    const url = URL.createObjectURL(blob);

    iframeRef.current.src = url;

    // 组件卸载或内容变化时释放 blob URL，避免内存泄漏
    return () => URL.revokeObjectURL(url);
  }, [content]);

  return (
    <div
      className="w-full h-full overflow-auto"
      style={{ backgroundColor: theme === 'dark' ? '#1a1a2e' : '#ffffff' }}
    >
      <iframe
        ref={iframeRef}
        sandbox="allow-scripts allow-forms"
        className="w-full h-full border-0"
        title="HTML 预览"
        style={{ minHeight: '100%' }}
      />
    </div>
  );
}
