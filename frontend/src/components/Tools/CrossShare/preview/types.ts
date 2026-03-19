/**
 * 预览器类型定义
 */

import { CrossFile } from '../../../services/crossShare';

/**
 * 预览器类型枚举
 */
export type ViewerType =
  | 'ImageViewer'
  | 'VideoViewer'
  | 'AudioViewer'
  | 'MarkdownViewer'
  | 'PdfViewer'
  | 'ExcelViewer'
  | 'JsonViewer'
  | 'TextViewer'
  | 'UnsupportedViewer';

/**
 * 预览属性
 */
export interface PreviewProps {
  /** 文件签名 URL */
  url: string;
  /** 文件名 */
  fileName: string;
  /** 文件大小 */
  fileSize: number;
  /** 文件 ID（用于后端代理请求） */
  fileId?: string;
}

/**
 * 根据文件类型获取预览器类型
 */
export function getViewerType(file: CrossFile): ViewerType {
  const ext = file.file_name.toLowerCase().split('.').pop() || '';

  switch (file.file_type) {
    case 'image':
      return 'ImageViewer';
    case 'video':
      return 'VideoViewer';
    case 'audio':
      return 'AudioViewer';
    case 'text':
      if (ext === 'md') return 'MarkdownViewer';
      if (ext === 'json') return 'JsonViewer';
      return 'TextViewer';
    case 'document':
      if (ext === 'pdf') return 'PdfViewer';
      if (ext === 'xlsx' || ext === 'xls') return 'ExcelViewer';
      return 'TextViewer';
    default:
      return 'UnsupportedViewer';
  }
}

/**
 * 获取预览器显示名称
 */
export function getViewerDisplayName(viewerType: ViewerType): string {
  const names: Record<ViewerType, string> = {
    ImageViewer: '图片预览',
    VideoViewer: '视频预览',
    AudioViewer: '音频预览',
    MarkdownViewer: 'Markdown 预览',
    PdfViewer: 'PDF 预览',
    ExcelViewer: 'Excel 预览',
    JsonViewer: 'JSON 预览',
    TextViewer: '文本预览',
    UnsupportedViewer: '不支持预览',
  };
  return names[viewerType];
}
