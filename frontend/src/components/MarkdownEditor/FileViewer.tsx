/**
 * FileViewer - 文件查看器路由组件
 *
 * 根据文件扩展名将文件路由到不同的查看器：
 * - 代码文件（.py/.js/.ts/...）→ Editor（当前 textarea，后续替换为 Monaco）
 * - 文本文件（.md/.txt/...）→ Editor
 * - PDF / Excel / Word / 图片 → PlaceholderViewer（阶段 2/3 实现具体查看器）
 * - 未知类型 → PlaceholderViewer
 *
 * 类型判断逻辑统一由 utils/fileType.ts 提供，FileViewer 仅负责路由。
 *
 * 注意: getFileLanguage 在阶段 2 接入 Monaco 时使用，用于设置语法高亮语言
 */
import React from 'react';
import { getFileCategory } from '../../utils/fileType';
import Editor from './Editor/Editor';
import type { EditorConfig } from '../../types/markdownEditor';

/** FileViewer 对外接口 */
interface FileViewerProps {
  /** 文件路径（含或不含路径前缀均可，按扩展名判断） */
  filePath: string;
  /** 文件文本内容；二进制文件通常为 null */
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
 * 占位查看器 - 用于尚未实现的查看器类型（PDF / Excel / Word / 图片等）
 * 阶段 2/3 会替换为具体实现
 */
const PlaceholderViewer: React.FC<{ fileType: string }> = ({ fileType }) => (
  <div className="flex items-center justify-center h-full text-ink-muted">
    <div className="text-center">
      <div className="text-lg mb-2">不支持的文件类型</div>
      <div className="text-sm">文件类型：{fileType}</div>
    </div>
  </div>
);

/** 文件分类到展示名称的映射（用于 PlaceholderViewer 显示） */
const CATEGORY_LABEL: Record<string, string> = {
  pdf: 'PDF',
  excel: 'Excel',
  word: 'Word',
  image: '图片',
};

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
    case 'code':
    case 'text': {
      // 代码与文本文件复用现有 Editor（后续 code 分支会替换为 Monaco）
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
    case 'excel':
    case 'word':
    case 'image':
      // 阶段 2/3 实现具体的二进制文件查看器
      return <PlaceholderViewer fileType={CATEGORY_LABEL[category] || category} />;

    case 'unknown':
    default:
      return <PlaceholderViewer fileType={category} />;
  }
};

export default FileViewer;
