import React, { useState } from 'react';
import { prdApi } from '../../services/prdApi';

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  conversationId: string;
  currentVersion?: number;
  onExportSuccess?: () => void;
}

type ExportFormat = 'markdown' | 'pdf' | 'word';

const ExportDialog: React.FC<ExportDialogProps> = ({
  isOpen,
  onClose,
  conversationId,
  currentVersion,
  onExportSuccess,
}) => {
  const [format, setFormat] = useState<ExportFormat>('markdown');
  const [version, setVersion] = useState<number>(currentVersion || 1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleExport = async () => {
    try {
      setLoading(true);
      setError(null);

      const blob = await prdApi.exportPRD(conversationId, format, version);
      
      // 创建下载链接
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // 设置文件名
      const extension = format === 'markdown' ? 'md' : format === 'word' ? 'docx' : 'pdf';
      const filename = `PRD-V${version}.${extension}`;
      link.download = filename;
      
      // 触发下载
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // 释放 URL
      URL.revokeObjectURL(url);
      
      onExportSuccess?.();
      onClose();
    } catch (err) {
      console.error('导出失败:', err);
      setError('导出失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const formatOptions: Array<{ value: ExportFormat; label: string; description: string; icon: string }> = [
    {
      value: 'markdown',
      label: 'Markdown',
      description: '导出为 .md 文件，便于编辑和版本控制',
      icon: '📝',
    },
    {
      value: 'word',
      label: 'Word',
      description: '导出为 .docx 文件，适合团队协作',
      icon: '📄',
    },
    {
      value: 'pdf',
      label: 'PDF',
      description: '导出为 PDF 文件，适合正式交付',
      icon: '📕',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 背景遮罩 */}
      <div 
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />
      
      {/* 对话框 */}
      <div className="relative bg-surface-1 rounded-xl shadow-lg w-full max-w-lg mx-4">
        {/* 头部 */}
        <div className="flex items-center justify-between p-5 border-b border-border">
          <h2 className="text-lg font-semibold text-ink-inverse">导出 PRD 文档</h2>
          <button
            onClick={onClose}
            className="p-1 text-ink-muted hover:text-ink-inverse transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 内容 */}
        <div className="p-5">
          {/* 导出格式选择 */}
          <div className="mb-5">
            <label className="block text-sm font-medium text-ink-muted mb-3">
              导出格式
            </label>
            <div className="space-y-2">
              {formatOptions.map((option) => (
                <label
                  key={option.value}
                  className={`flex items-start p-3 rounded-lg cursor-pointer transition-all ${
                    format === option.value
                      ? 'bg-accent-info/20 border-2 border-accent-info'
                      : 'bg-surface-2/50 border-2 border-transparent hover:border-border'
                  }`}
                >
                  <input
                    type="radio"
                    name="format"
                    value={option.value}
                    checked={format === option.value}
                    onChange={(e) => setFormat(e.target.value as ExportFormat)}
                    className="sr-only"
                  />
                  <span className="text-xl mr-3">{option.icon}</span>
                  <div className="flex-1">
                    <div className="text-ink-inverse font-medium">{option.label}</div>
                    <div className="text-sm text-ink-muted">{option.description}</div>
                  </div>
                  {format === option.value && (
                    <svg className="w-5 h-5 text-accent-info" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  )}
                </label>
              ))}
            </div>
          </div>

          {/* 版本选择 */}
          <div className="mb-5">
            <label className="block text-sm font-medium text-ink-muted mb-2">
              导出版本
            </label>
            <input
              type="number"
              min={1}
              value={version}
              onChange={(e) => setVersion(parseInt(e.target.value) || 1)}
              className="w-full px-4 py-2 bg-surface-2 text-ink-inverse rounded-lg border border-border focus:outline-none focus:border-accent-info"
            />
            <p className="mt-1 text-xs text-ink-muted">
              输入要导出的版本号，默认为当前版本
            </p>
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="mb-4 p-3 bg-danger/20 border border-danger rounded-lg">
              <p className="text-sm text-danger">{error}</p>
            </div>
          )}
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-end gap-3 p-5 border-t border-border">
          <button
            onClick={onClose}
            className="px-4 py-2 text-ink-muted hover:text-ink-inverse transition-colors"
            disabled={loading}
          >
            取消
          </button>
          <button
            onClick={handleExport}
            disabled={loading}
            className="px-6 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                导出中...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                导出
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExportDialog;
