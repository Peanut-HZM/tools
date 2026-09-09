/**
 * FileViewer - 文件查看器路由组件
 *
 * 根据文件扩展名将文件路由到不同的查看器：
 * - 代码文件（.py/.js/.ts/...）→ CodeEditor（Monaco Editor 语法高亮）
 * - HTML 文件（.html/.htm）→ HtmlPreview（iframe 沙箱渲染）
 * - 文本文件（.md/.txt/...）→ Editor（textarea）
 * - PDF → PdfViewer（react-pdf，支持翻页）
 * - Excel → ExcelViewer（SheetJS，渲染表格）
 * - Word → WordViewer（mammoth，转换为 HTML）
 * - 图片 → ImageViewer（base64 渲染 + 缩放）
 * - 未知类型 → PlaceholderViewer
 *
 * 类型判断逻辑统一由 utils/fileType.ts 提供，FileViewer 仅负责路由。
 */
import React from 'react';
import { getFileCategory, getFileLanguage } from '../../utils/fileType';
import Editor from './Editor/Editor';
import CodeEditor from './CodeEditor';
import PdfViewer from './PdfViewer';
import ExcelViewer from './ExcelViewer';
import WordViewer from './WordViewer';
import ImageViewer from './ImageViewer';
import HtmlPreview from './Preview/HtmlPreview';
import type { EditorConfig } from '../../types/markdownEditor';

/** FileViewer 对外接口 */
interface FileViewerProps {
  /** 文件路径（含或不含路径前缀均可，按扩展名判断） */
  filePath: string;
  /** 文件内容；文本文件为文本字符串，二进制文件（如 PDF）为 base64 数据 */
  fileContent: string | null;
  /** 内容变更回调（仅对可编辑文件类型生效） */
  onChange?: (content: string) => void;
  /** 是否只读（当前为预留字段，Editor 暂不支持） */
  readOnly?: boolean;
  /** 透传给 Editor 的配置（代码/文本文件必须提供） */
  editorConfig: EditorConfig;
  /** 透传给 Editor 的保存回调（代码/文本文件必须提供） */
  onSave: () => void;
  /** 透传给 Editor 的光标变化回调 */
  onCursorChange?: (line: number, column: number) => void;
}

/**
 * 占位查看器 - 用于尚未实现的查看器类型
 */
const PlaceholderViewer: React.FC<{ fileType: string }> = ({ fileType }) => (
  <div className="flex items-center justify-center h-full text-ink-muted">
    <div className="text-center">
      <div className="text-lg mb-2">不支持的文件类型</div>
      <div className="text-sm">文件类型：{fileType}</div>
    </div>
  </div>
);

const FileViewer: React.FC<FileViewerProps> = ({
  filePath,
  fileContent,
  onChange,
  readOnly: _readOnly,
  editorConfig,
  onSave,
  onCursorChange,
}) => {
  const category = getFileCategory(filePath);

  switch (category) {
    case 'code': {
      // HTML 文件使用 HtmlPreview（iframe 沙箱渲染），其他代码文件使用 Monaco Editor
      const language = getFileLanguage(filePath);
      if (language === 'html') {
        return (
          <HtmlPreview
            content={fileContent || ''}
            theme={editorConfig.theme}
          />
        );
      }
      return (
        <CodeEditor
          filePath={filePath}
          content={fileContent}
          onChange={onChange}
          readOnly={_readOnly}
          theme={editorConfig.theme}
        />
      );
    }

    case 'text': {
      // 文本文件（Markdown / TXT 等）继续使用现有 Editor
      // 未提供 onChange 时使用空函数，保证 Editor 调用安全
      const noop = () => {};
      return (
        <Editor
          content={fileContent || ''}
          config={editorConfig}
          onChange={onChange || noop}
          onSave={onSave}
          onCursorChange={onCursorChange}
        />
      );
    }

    case 'pdf':
      // PDF 文件使用 PdfViewer（react-pdf）渲染
      return (
        <PdfViewer
          content={fileContent}
          fileName={filePath.split('/').pop()}
        />
      );

    case 'excel':
      // Excel 文件使用 ExcelViewer（SheetJS）渲染表格
      return (
        <ExcelViewer
          content={fileContent}
          fileName={filePath.split('/').pop()}
        />
      );

    case 'word':
      // Word 文件使用 WordViewer（mammoth）转换为 HTML 渲染
      return (
        <WordViewer
          content={fileContent}
          fileName={filePath.split('/').pop()}
        />
      );

    case 'image':
      // 图片文件使用 ImageViewer（base64 渲染 + 缩放控制）
      return (
        <ImageViewer
          content={fileContent}
          fileName={filePath.split('/').pop()}
        />
      );

    case 'unknown':
    default:
      return <PlaceholderViewer fileType={category} />;
  }
};

export default FileViewer;
