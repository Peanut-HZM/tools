/**
 * 课程导入/导出对话框
 */
import React, { useState, useRef } from 'react';
import {
  exportCourseData,
  downloadCourseExport,
  previewImport,
  importCourseData,
  type ExportData,
  type ImportConflictInfo,
} from '../../services/openspecCourseAdmin';
import { useToast } from '../../hooks/useToast';

interface ImportExportDialogProps {
  courseId?: number;
  courseTitle?: string;
  onClose: () => void;
  onImportSuccess?: () => void;
}

type ImportStrategy = 'merge' | 'replace' | 'skip_existing';
type DialogMode = 'export' | 'import' | 'preview';

export const ImportExportDialog: React.FC<ImportExportDialogProps> = ({
  courseId,
  courseTitle,
  onClose,
  onImportSuccess,
}) => {
  const { success, error, addToast } = useToast();
  const [mode, setMode] = useState<DialogMode>('export');
  const [loading, setLoading] = useState(false);
  const [exportData, setExportData] = useState<ExportData | null>(null);
  const [importStrategy, setImportStrategy] = useState<ImportStrategy>('merge');
  const [previewData, setPreviewData] = useState<any | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 导出课程数据
  const handleExport = async () => {
    setLoading(true);
    try {
      const data = await exportCourseData(courseId, courseTitle);
      setExportData(data);

      // 创建下载
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `course-export-${new Date().toISOString().split('T')[0]}.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      success('导出成功！');
    } catch (e) {
      error('导出失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理文件选择
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith('.json')) {
        error('请选择 JSON 文件');
        return;
      }
      setSelectedFile(file);
    }
  };

  // 读取 JSON 文件
  const readJsonFile = (file: File): Promise<ExportData> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = JSON.parse(e.target?.result as string);
          resolve(data);
        } catch (err) {
          reject(new Error('JSON 解析失败'));
        }
      };
      reader.onerror = () => reject(new Error('文件读取失败'));
      reader.readAsText(file);
    });
  };

  // 预览导入
  const handlePreviewImport = async () => {
    if (!selectedFile) {
      error('请选择文件');
      return;
    }

    setLoading(true);
    try {
      const data = await readJsonFile(selectedFile);
      const preview = await previewImport(data, importStrategy);
      setPreviewData(preview);
      setExportData(data);
      setMode('preview');
    } catch (e) {
      error('导入预览失败');
    } finally {
      setLoading(false);
    }
  };

  // 执行导入
  const handleDoImport = async () => {
    if (!exportData) {
      error('没有可导入的数据');
      return;
    }

    setLoading(true);
    try {
      const result = await importCourseData(exportData, importStrategy);
      if (result.success) {
        success(result.message);
        onImportSuccess?.();
        onClose();
      } else {
        error('导入失败：' + (result.errors?.[0] || '未知错误'));
      }
    } catch (e) {
      error('导入失败');
    } finally {
      setLoading(false);
    }
  };

  const getStrategyLabel = (strategy: ImportStrategy) => {
    switch (strategy) {
      case 'merge': return '合并（跳过已存在）';
      case 'replace': return '替换（更新已存在）';
      case 'skip_existing': return '跳过所有已存在';
    }
  };

  const getConflictStatus = (conflict: ImportConflictInfo) => {
    switch (conflict.conflict_type) {
      case 'exists':
        return { icon: '⏭️', label: '已存在（将跳过）' };
      case 'will_update':
        return { icon: '🔄', label: '已存在（将更新）' };
      case 'new':
        return { icon: '✨', label: '新章节' };
      default:
        return { icon: '❓', label: conflict.conflict_type };
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-2xl border border-slate-700 shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <h2 className="text-2xl font-bold text-white">
            {mode === 'export' && '📤 导出课程数据'}
            {mode === 'import' && '📥 导入课程数据'}
            {mode === 'preview' && '📋 导入预览'}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <i className="fas fa-times text-xl"></i>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {mode === 'export' && (
            <div className="space-y-4">
              <div className="bg-slate-700/50 rounded-lg p-4">
                <h3 className="text-white font-semibold mb-2">导出说明</h3>
                <p className="text-slate-300 text-sm">
                  导出所有课程章节、测验和资源数据为 JSON 格式文件。
                  导出的文件可以用于数据备份或在其他环境中恢复课程数据。
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-slate-300 text-sm">课程标题（可选）:</label>
                <input
                  type="text"
                  value={courseTitle || ''}
                  readOnly
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm"
                />
              </div>
            </div>
          )}

          {mode === 'import' && (
            <div className="space-y-4">
              <div className="bg-slate-700/50 rounded-lg p-4">
                <h3 className="text-white font-semibold mb-2">导入说明</h3>
                <p className="text-slate-300 text-sm mb-4">
                  选择之前导出的 JSON 文件进行导入。导入前请先预览，确认数据无误后再执行。
                </p>

                <div className="space-y-3">
                  <div>
                    <label className="text-slate-300 text-sm block mb-2">选择策略:</label>
                    <select
                      value={importStrategy}
                      onChange={(e) => setImportStrategy(e.target.value as ImportStrategy)}
                      className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm cursor-pointer"
                    >
                      <option value="merge">合并（跳过已存在的章节）</option>
                      <option value="replace">替换（更新已存在的章节）</option>
                      <option value="skip_existing">完全跳过（不导入任何已存在的章节）</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-slate-300 text-sm block mb-2">选择 JSON 文件:</label>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".json"
                      onChange={handleFileSelect}
                      className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm"
                    />
                    {selectedFile && (
                      <p className="text-slate-400 text-sm mt-2">
                        <i className="fas fa-file mr-2"></i>
                        {selectedFile.name}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {mode === 'preview' && previewData && (
            <div className="space-y-4">
              <div className="flex items-center gap-4 mb-4">
                <div className="flex-1 bg-slate-700/50 rounded-lg p-3">
                  <div className="text-slate-300 text-sm">导入章节</div>
                  <div className="text-white text-2xl font-bold">{previewData.chapters_to_import}</div>
                </div>
                <div className="flex-1 bg-slate-700/50 rounded-lg p-3">
                  <div className="text-slate-300 text-sm">更新章节</div>
                  <div className="text-white text-2xl font-bold">{previewData.chapters_to_update}</div>
                </div>
                <div className="flex-1 bg-slate-700/50 rounded-lg p-3">
                  <div className="text-slate-300 text-sm">跳过章节</div>
                  <div className="text-white text-2xl font-bold">{previewData.chapters_to_skip}</div>
                </div>
              </div>

              <div className="bg-slate-700/50 rounded-lg p-4">
                <h3 className="text-white font-semibold mb-3">章节列表</h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {previewData.conflicts?.map((conflict: ImportConflictInfo, index: number) => {
                    const status = getConflictStatus(conflict);
                    return (
                      <div
                        key={index}
                        className="flex items-center gap-3 p-2 bg-slate-800 rounded-lg"
                      >
                        <span className="text-lg">{status.icon}</span>
                        <div className="flex-1">
                          <div className="text-white text-sm font-medium">{conflict.chapter_title}</div>
                          <div className="text-slate-400 text-xs">{conflict.chapter_slug}</div>
                        </div>
                        <span className="text-slate-400 text-xs">{status.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {previewData.warnings?.length > 0 && (
                <div className="bg-yellow-500/10 border border-yellow-500/50 rounded-lg p-3">
                  <h3 className="text-yellow-400 font-semibold mb-2">⚠️ 警告</h3>
                  <ul className="text-slate-300 text-sm list-disc list-inside space-y-1">
                    {previewData.warnings.map((warning: string, index: number) => (
                      <li key={index}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-slate-700">
          {mode === 'export' && (
            <>
              <button
                onClick={onClose}
                className="px-6 py-2 text-slate-300 hover:text-white transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleExport}
                disabled={loading}
                className="px-6 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <i className="fas fa-spinner fa-spin mr-2"></i>
                    导出中...
                  </>
                ) : (
                  <>
                    <i className="fas fa-download mr-2"></i>
                    导出数据
                  </>
                )}
              </button>
            </>
          )}

          {mode === 'import' && (
            <>
              <button
                onClick={onClose}
                className="px-6 py-2 text-slate-300 hover:text-white transition-colors"
              >
                取消
              </button>
              <button
                onClick={handlePreviewImport}
                disabled={!selectedFile || loading}
                className="px-6 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <i className="fas fa-spinner fa-spin mr-2"></i>
                    处理中...
                  </>
                ) : (
                  <>
                    <i className="fas fa-eye mr-2"></i>
                    预览导入
                  </>
                )}
              </button>
            </>
          )}

          {mode === 'preview' && (
            <>
              <button
                onClick={() => {
                  setMode('import');
                  setPreviewData(null);
                }}
                className="px-6 py-2 text-slate-300 hover:text-white transition-colors"
              >
                <i className="fas fa-arrow-left mr-2"></i>
                返回
              </button>
              <button
                onClick={handleDoImport}
                disabled={loading}
                className="px-6 py-2 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <i className="fas fa-spinner fa-spin mr-2"></i>
                    导入中...
                  </>
                ) : (
                  <>
                    <i className="fas fa-check mr-2"></i>
                    确认导入
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ImportExportDialog;
