/**
 * WordViewer - Word 文件查看器
 *
 * 按文件真实格式分流（见 utils/wordDocument.ts）：
 * - .docx（OOXML zip）→ mammoth 转 HTML，内联渲染
 * - .doc 实为 MHTML（Confluence / Outlook 导出）→ 提取 HTML，sandbox iframe 渲染
 * - .doc 实为 HTML → sandbox iframe 渲染
 * - 旧版二进制 .doc（OLE2）/ .odt / .rtf → 明确提示无法在浏览器端解析
 *
 * content 接收 base64 编码的 Word 数据（来自 FileRawContent.data）。
 */
import React, { useState, useEffect } from 'react';
import mammoth from 'mammoth';
import DOMPurify from 'dompurify';
import {
  decodeWordDocument,
  UNSUPPORTED_WORD_REASON,
  type DecodedWordDocument,
} from '../../utils/wordDocument';

/** WordViewer 组件接口 */
interface WordViewerProps {
  /** base64 编码的 Word 数据（来自 FileRawContent.data） */
  content: string | null;
  /** 文件名（可选，显示在工具栏） */
  fileName?: string;
}

type ViewState =
  | { status: 'empty' }
  | { status: 'loading' }
  | { status: 'inline'; html: string }
  | { status: 'document'; html: string }
  | { status: 'unsupported'; reason: string }
  | { status: 'error'; message: string };

/**
 * 清洗 Word / MHTML 提取出的 HTML。
 * 保留 style（Word 依赖其排版），移除脚本等可执行内容；
 * 最终还会放进不带 allow-scripts 的 sandbox iframe，双重兜底。
 */
function sanitizeWordHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    WHOLE_DOCUMENT: true,
    ADD_TAGS: ['style'],
    ADD_ATTR: ['style'],
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'link', 'meta'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick'],
  });
}

const WordViewer: React.FC<WordViewerProps> = ({ content, fileName }) => {
  const [state, setState] = useState<ViewState>({ status: 'empty' });

  useEffect(() => {
    if (!content) {
      setState({ status: 'empty' });
      return;
    }

    let cancelled = false;
    setState({ status: 'loading' });

    const loadDocument = async () => {
      try {
        const doc: DecodedWordDocument = decodeWordDocument(content);

        if (doc.kind === 'docx' && doc.arrayBuffer) {
          const result = await mammoth.convertToHtml({ arrayBuffer: doc.arrayBuffer });
          if (cancelled) return;
          setState({ status: 'inline', html: result.value });

          if (result.messages.length > 0) {
            // 记录转换过程中的警告信息（如不支持的样式等）
            // eslint-disable-next-line no-console
            console.warn('Word 转换警告:', result.messages);
          }
          return;
        }

        if ((doc.kind === 'mhtml' || doc.kind === 'html') && doc.html) {
          const html = sanitizeWordHtml(doc.html);
          if (cancelled) return;
          setState({ status: 'document', html });
          return;
        }

        if (cancelled) return;
        setState({
          status: 'unsupported',
          reason: UNSUPPORTED_WORD_REASON[doc.kind] || UNSUPPORTED_WORD_REASON.unknown,
        });
      } catch (e) {
        if (cancelled) return;
        setState({
          status: 'error',
          message: `Word 解析失败：${e instanceof Error ? e.message : '未知错误'}`,
        });
      }
    };

    loadDocument();

    return () => {
      cancelled = true;
    };
  }, [content]);

  // 无内容时显示占位提示
  if (state.status === 'empty') {
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
      {state.status === 'document' ? (
        // MHTML / HTML 形式的 .doc：sandbox iframe 隔离 Word 自带样式，禁止脚本执行
        <div className="flex-1 overflow-hidden bg-white">
          <iframe
            title={fileName || 'Word 文档'}
            className="w-full h-full border-0 bg-white"
            sandbox=""
            referrerPolicy="no-referrer"
            srcDoc={state.html}
          />
        </div>
      ) : (
        <div className="flex-1 overflow-auto bg-surface-3 p-6">
          {state.status === 'error' ? (
            <div className="text-center text-danger py-8">
              {state.message}
            </div>
          ) : state.status === 'unsupported' ? (
            <div className="text-center text-ink-muted py-8 px-4">
              <div className="text-base mb-2 text-ink">无法预览该 Word 文件</div>
              <div className="text-sm">{state.reason}</div>
            </div>
          ) : state.status === 'inline' ? (
            <div
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: state.html }}
            />
          ) : (
            <div className="text-center text-ink-muted py-8">
              加载 Word 文档中...
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default WordViewer;
