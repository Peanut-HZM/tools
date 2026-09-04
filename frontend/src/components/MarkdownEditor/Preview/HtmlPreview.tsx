/**
 * HtmlPreview 组件 - 通过 iframe sandbox 安全渲染 HTML 文件内容
 */

interface HtmlPreviewProps {
  content: string;
  theme: 'light' | 'dark';
}

export default function HtmlPreview({ content, theme }: HtmlPreviewProps) {
  return (
    <div
      className="w-full h-full overflow-auto"
      style={{ backgroundColor: theme === 'dark' ? '#1a1a2e' : '#ffffff' }}
    >
      <iframe
        srcDoc={content}
        sandbox="allow-same-origin"
        className="w-full h-full border-0"
        title="HTML 预览"
        style={{ minHeight: '100%' }}
      />
    </div>
  );
}
