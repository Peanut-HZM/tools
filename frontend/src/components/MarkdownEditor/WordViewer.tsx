/**
 * WordViewer - Word 文件查看器
 *
 * 使用 mammoth 将 Word 文档转换为 HTML 并渲染。
 * content 接收 base64 编码的 Word 数据（来自 FileRawContent.data）。
 */
import React, { useState, useEffect } from 'react';
import mammoth from 'mammoth';

/** WordViewer 组件接口 */
interface WordViewerProps {
  /** base64 编码的 Word 数据（来自 FileRawContent.data） */
  content: string | null;
  /** 文件名（可选，显示在工具栏） */
  fileName?: string;
}

/**
 * 将 base64 字符串解码为 ArrayBuffer
 * mammoth 需要以 ArrayBuffer 形式接收数据
 */
function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binaryStr = atob(base64);
  const bytes = new Uint8Array(binaryStr.length);
  for (let i = 0; i < binaryStr.length; i++) {
    bytes[i] = binaryStr.charCodeAt(i);
  }
  return bytes.buffer;
}

const WordViewer: React.FC<WordViewerProps> = ({ content, fileName }) => {
  const [html, setHtml] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!content) {
      setHtml('');
      setError(null);
      return;
    }

    const loadDocument = async () => {
      try {
        // 解码 base64 为 ArrayBuffer
        const arrayBuffer = base64ToArrayBuffer(content);

        // 使用 mammoth 将 Word 转换为 HTML
        const result = await mammoth.convertToHtml({ arrayBuffer });
        setHtml(result.value);

        if (result.messages.length > 0) {
          // 记录转换过程中的警告信息（如不支持的样式等）
          // eslint-disable-next-line no-console
          console.warn('Word 转换警告:', result.messages);
        }
      } catch (e) {
        setError(`Word 解析失败：${e instanceof Error ? e.message : '未知错误'}`);
        setHtml('');
      }
    };

    loadDocument();
  }, [content]);

  // 无内容时显示占位提示
  if (!content) {
    return (
      <div className="flex items-center justify-center h-full text-ink-muted">
        <div className="text-center">
          <div className="text-lg mb-2">无 Word 内容</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* 顶部工具栏：显示文件名 */}
      <div className="flex items-center px-4 py-2 border-b border-border bg-surface-1">
        <div className="text-sm text-ink-muted">
          {fileName || 'Word 文档'}
        </div>
      </div>

      {/* Word 内容区域 */}
      <div className="flex-1 overflow-auto bg-surface-3 p-6">
        {error ? (
          <div className="text-center text-danger py-8">
            {error}
          </div>
        ) : html ? (
          <div
            className="prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        ) : (
          <div className="text-center text-ink-muted py-8">
            加载 Word 文档中...
          </div>
        )}
      </div>
    </div>
  );
};

export default WordViewer;
