import { useEffect, useRef } from 'react';

/**
 * HTML 预览组件接口
 */
interface HtmlPreviewProps {
  /** 待渲染的 HTML 字符串 */
  html: string;
}

/**
 * HTML 预览组件
 *
 * 使用 iframe 沙箱隔离渲染 API 响应中的 HTML 内容，避免恶意脚本影响主页面。
 * 仅允许同源访问，禁止执行脚本、表单提交等可能带来安全风险的浏览器行为。
 */
export default function HtmlPreview({ html }: HtmlPreviewProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // 每次 HTML 内容变化时，重新写入 iframe 文档
  useEffect(() => {
    if (iframeRef.current) {
      const doc = iframeRef.current.contentDocument;
      if (doc) {
        doc.open();
        doc.write(html);
        doc.close();
      }
    }
  }, [html]);

  return (
    <div className="w-full h-full bg-white rounded-lg overflow-hidden">
      <iframe
        ref={iframeRef}
        className="w-full h-full border-0"
        sandbox="allow-same-origin"
        title="HTML Preview"
      />
    </div>
  );
}