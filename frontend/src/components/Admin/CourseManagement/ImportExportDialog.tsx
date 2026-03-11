/**
 * 课程导入/导出对话框
 */
import React, { useState, useRef } from 'react';
import {
  exportCourseData,
  downloadCourseExport,
  downloadCourseExportZip,
  previewImport,
  importCourseData,
  type ExportData,
  type ImportConflictInfo,
} from '../../../services/openspecCourseAdmin';
import { useToast } from '../../../hooks/useToast';

interface ImportExportDialogProps {
  courseId?: number;
  courseTitle?: string;
  mode?: 'import' | 'export';  // 新增 mode 属性
  onClose: () => void;
  onImportSuccess?: () => void;
}

type ImportStrategy = 'merge' | 'replace' | 'skip_existing';

export const ImportExportDialog: React.FC<ImportExportDialogProps> = ({
  courseId,
  courseTitle,
  mode: initialMode = 'export',  // 默认导出模式
  onClose,
  onImportSuccess,
}) => {
  const { success, error, addToast } = useToast();
  const [mode, setMode] = useState<'export' | 'import' | 'preview'>(initialMode);
  const [loading, setLoading] = useState(false);
  const [exportData, setExportData] = useState<ExportData | null>(null);
  const [importStrategy, setImportStrategy] = useState<'merge' | 'replace' | 'skip_existing'>('replace');
  const [previewData, setPreviewData] = useState<any | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 当 mode 属性变化时，更新内部状态
  React.useEffect(() => {
    setMode(initialMode);
  }, [initialMode]);

  // 导出课程数据（JSON）
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

  // 导出课程数据为 ZIP 包（JSON + Markdown 文件）
  const handleExportZip = async () => {
    setLoading(true);
    try {
      await downloadCourseExportZip(courseId, courseTitle);
      success('导出成功！已下载 ZIP 包，包含 JSON 数据和所有章节 Markdown 文件。');
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
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              mode === 'export'
                ? 'bg-gradient-to-br from-emerald-500/20 to-green-500/20 border border-emerald-500/30'
                : mode === 'import'
                ? 'bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/30'
                : 'bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/30'
            }`}>
              <i className={`fas text-lg ${
                mode === 'export' ? 'fa-download text-emerald-400' :
                mode === 'import' ? 'fa-upload text-amber-400' :
                'fa-eye text-cyan-400'
              }`}></i>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">
                {mode === 'export' && '导出课程数据'}
                {mode === 'import' && '导入课程数据'}
                {mode === 'preview' && '导入预览'}
              </h2>
              <p className="text-slate-400 text-sm">
                {mode === 'export' && '将课程数据导出为 JSON 或 Markdown 格式'}
                {mode === 'import' && '从 JSON 或 Markdown 文件导入课程数据'}
                {mode === 'preview' && '预览导入操作，确认变更内容'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-all"
          >
            <i className="fas fa-times text-xl"></i>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {mode === 'export' && (
            <div className="space-y-6">
              {/* 导出说明卡片 */}
              <div className="bg-gradient-to-br from-emerald-500/10 to-green-500/10 rounded-xl border border-emerald-500/20 p-5">
                <h3 className="text-emerald-400 font-semibold mb-2 flex items-center gap-2">
                  <i className="fas fa-info-circle"></i>
                  导出说明
                </h3>
                <p className="text-slate-300 text-sm leading-relaxed">
                  将当前课程的所有章节、测验和资源数据导出为 <strong className="text-white">JSON 格式</strong> 文件。
                  导出的文件可用于数据备份或在其他环境中恢复课程数据。
                </p>
              </div>

              {/* 课程信息 */}
              <div className="space-y-3">
                <label className="text-slate-300 text-sm font-medium">当前课程:</label>
                <div className="px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
                    <i className="fas fa-graduation-cap text-white text-sm"></i>
                  </div>
                  <span className="text-white font-medium">{courseTitle || '未命名课程'}</span>
                </div>
              </div>

              {/* 导出格式选项 */}
              <div className="space-y-3">
                <label className="text-slate-300 text-sm font-medium">导出格式:</label>
                <div className="grid grid-cols-2 gap-3">
                  {/* JSON 格式 */}
                  <button
                    onClick={handleExport}
                    disabled={loading}
                    className="px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-300 hover:border-cyan-500/50 hover:bg-cyan-500/10 hover:text-cyan-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <i className="fas fa-file-code"></i>
                      <span className="font-medium">JSON 格式</span>
                    </div>
                    <p className="text-xs text-slate-500 text-left">完整数据，包含所有测验和资源</p>
                  </button>

                  {/* Markdown/ZIP 格式 */}
                  <button
                    onClick={handleExportZip}
                    disabled={loading}
                    className="px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-300 hover:border-emerald-500/50 hover:bg-emerald-500/10 hover:text-emerald-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <i className="fas fa-file-archive"></i>
                      <span className="font-medium">ZIP 压缩包</span>
                    </div>
                    <p className="text-xs text-slate-500 text-left">JSON + 所有章节 Markdown 文件</p>
                  </button>
                </div>

                {/* 格式说明 */}
                <div className="mt-3 p-4 bg-slate-700/30 rounded-lg border border-slate-600/50">
                  <h4 className="text-white font-medium text-sm mb-2 flex items-center gap-2">
                    <i className="fas fa-info-circle text-cyan-400"></i>
                    格式说明
                  </h4>
                  <ul className="text-slate-400 text-xs space-y-1.5">
                    <li className="flex items-start gap-2">
                      <span className="text-cyan-400 mt-0.5">•</span>
                      <span><strong className="text-white">JSON 格式</strong> - 适合程序化处理，完整保留所有数据结构</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400 mt-0.5">•</span>
                      <span><strong className="text-white">ZIP 压缩包</strong> - 包含 JSON 数据和 Markdown 章节文件，便于手动编辑和版本控制</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {mode === 'import' && (
            <div className="space-y-6">
              {/* 导入说明卡片 */}
              <div className="bg-gradient-to-br from-amber-500/10 to-orange-500/10 rounded-xl border border-amber-500/20 p-5">
                <h3 className="text-amber-400 font-semibold mb-2 flex items-center gap-2">
                  <i className="fas fa-lightbulb"></i>
                  导入说明
                </h3>
                <p className="text-slate-300 text-sm leading-relaxed mb-4">
                  选择之前导出的 <strong className="text-white">JSON 文件</strong> 进行导入。
                  建议先预览导入内容，确认数据无误后再执行导入操作。
                </p>

                {/* 导入策略 */}
                <div className="space-y-3">
                  <label className="text-slate-300 text-sm font-medium flex items-center gap-2">
                    <i className="fas fa-cog text-amber-400"></i>
                    选择导入策略:
                  </label>
                  <select
                    value={importStrategy}
                    onChange={(e) => setImportStrategy(e.target.value as 'merge' | 'replace' | 'skip_existing')}
                    className="w-full px-4 py-2.5 bg-slate-700/80 border border-slate-600 rounded-lg text-white text-sm focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/20 transition-all cursor-pointer"
                  >
                    <option value="replace">🔄 替换（更新已存在的章节 slug）- 推荐</option>
                    <option value="merge">🔀 合并（跳过已存在的章节 slug）</option>
                    <option value="skip_existing">⏭️ 完全跳过（不导入任何已存在的章节）</option>
                  </select>

                  {/* 策略说明 */}
                  <div className="mt-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
                    {importStrategy === 'replace' && (
                      <p className="text-slate-400 text-xs">
                        <span className="text-amber-400 font-medium">替换模式（推荐）：</span>
                        对于已存在的章节 slug 将更新内容，同时导入新的章节。适合批量更新课程数据。
                      </p>
                    )}
                    {importStrategy === 'merge' && (
                      <p className="text-slate-400 text-xs">
                        <span className="text-cyan-400 font-medium">合并模式：</span>
                        对于已存在的章节 slug 将跳过，只导入新的章节。适合增量添加内容。
                      </p>
                    )}
                    {importStrategy === 'skip_existing' && (
                      <p className="text-slate-400 text-xs">
                        <span className="text-purple-400 font-medium">跳过模式：</span>
                        完全跳过所有已存在的章节 slug，只导入全新的章节。最保守的策略。
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* 文件选择 */}
              <div className="space-y-3">
                <label className="text-slate-300 text-sm font-medium flex items-center gap-2">
                  <i className="fas fa-file-import text-amber-400"></i>
                  选择 JSON 文件:
                </label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className={`relative px-6 py-8 border-2 border-dashed rounded-xl transition-all cursor-pointer ${
                    selectedFile
                      ? 'border-cyan-500/50 bg-cyan-500/10'
                      : 'border-slate-600 hover:border-amber-500/50 hover:bg-amber-500/10'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".json"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <div className="text-center">
                    <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-slate-700/50 flex items-center justify-center">
                      <i className={`fas text-2xl ${
                        selectedFile ? 'fa-file-code text-cyan-400' : 'fa-cloud-upload-alt text-slate-400'
                      }`}></i>
                    </div>
                    {selectedFile ? (
                      <>
                        <p className="text-white font-medium mb-1">{selectedFile.name}</p>
                        <p className="text-slate-400 text-xs">
                          {(selectedFile.size / 1024).toFixed(2)} KB
                        </p>
                      </>
                    ) : (
                      <>
                        <p className="text-slate-300 text-sm mb-1">点击选择文件或拖拽文件到此处</p>
                        <p className="text-slate-500 text-xs">仅支持 .json 格式文件</p>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {mode === 'preview' && previewData && (
            <div className="space-y-5">
              {/* 统计卡片 */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-cyan-500/10 to-blue-500/10 rounded-xl border border-cyan-500/20 p-4">
                  <div className="text-slate-400 text-sm mb-1">导入章节</div>
                  <div className="text-white text-3xl font-bold">{previewData.chapters_to_import || 0}</div>
                </div>
                <div className="bg-gradient-to-br from-amber-500/10 to-orange-500/10 rounded-xl border border-amber-500/20 p-4">
                  <div className="text-slate-400 text-sm mb-1">更新章节</div>
                  <div className="text-white text-3xl font-bold">{previewData.chapters_to_update || 0}</div>
                </div>
                <div className="bg-gradient-to-br from-slate-500/10 to-gray-500/10 rounded-xl border border-slate-500/20 p-4">
                  <div className="text-slate-400 text-sm mb-1">跳过章节</div>
                  <div className="text-white text-3xl font-bold">{previewData.chapters_to_skip || 0}</div>
                </div>
              </div>

              {/* 章节列表 */}
              <div className="bg-slate-700/30 rounded-xl border border-slate-600/50 p-4">
                <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                  <i className="fas fa-list text-cyan-400"></i>
                  章节变更列表
                </h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {previewData.conflicts?.map((conflict: ImportConflictInfo, index: number) => {
                    const status = getConflictStatus(conflict);
                    return (
                      <div
                        key={index}
                        className={`flex items-center gap-3 p-3 rounded-lg border ${
                          conflict.conflict_type === 'new'
                            ? 'bg-emerald-500/10 border-emerald-500/20'
                            : conflict.conflict_type === 'will_update'
                            ? 'bg-amber-500/10 border-amber-500/20'
                            : 'bg-slate-500/10 border-slate-500/20'
                        }`}
                      >
                        <span className="text-lg">{status.icon}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-white text-sm font-medium truncate">{conflict.chapter_title}</div>
                          <div className="text-slate-400 text-xs truncate">{conflict.chapter_slug}</div>
                        </div>
                        <span className={`text-xs px-2.5 py-1 rounded-full ${
                          conflict.conflict_type === 'new'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : conflict.conflict_type === 'will_update'
                            ? 'bg-amber-500/20 text-amber-400'
                            : 'bg-slate-500/20 text-slate-400'
                        }`}>
                          {status.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 警告信息 */}
              {previewData.warnings?.length > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4">
                  <h3 className="text-amber-400 font-semibold mb-2 flex items-center gap-2">
                    <i className="fas fa-exclamation-triangle"></i>
                    警告
                  </h3>
                  <ul className="text-slate-300 text-sm space-y-1.5">
                    {previewData.warnings.map((warning: string, index: number) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="text-amber-400 mt-0.5">•</span>
                        <span>{warning}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-slate-700 bg-slate-800/30">
          {mode === 'export' && (
            <>
              <button
                onClick={onClose}
                className="px-5 py-2.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-all"
              >
                取消
              </button>
              <button
                onClick={handleExport}
                disabled={loading}
                className="px-6 py-2.5 bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 text-white rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 hover:-translate-y-0.5 flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <i className="fas fa-spinner fa-spin"></i>
                    <span>导出中...</span>
                  </>
                ) : (
                  <>
                    <i className="fas fa-download"></i>
                    <span>导出数据</span>
                  </>
                )}
              </button>
            </>
          )}

          {mode === 'import' && (
            <>
              <button
                onClick={onClose}
                className="px-5 py-2.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-all"
              >
                取消
              </button>
              <button
                onClick={handlePreviewImport}
                disabled={!selectedFile || loading}
                className="px-6 py-2.5 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg shadow-amber-500/20 hover:shadow-amber-500/30 hover:-translate-y-0.5 flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <i className="fas fa-spinner fa-spin"></i>
                    <span>处理中...</span>
                  </>
                ) : (
                  <>
                    <i className="fas fa-eye"></i>
                    <span>预览导入</span>
                  </>
                )}
              </button>
            </>
          )}

          {mode === 'preview' && (
            <>
              <button
                onClick={() => {
                  setMode(initialMode === 'export' ? 'import' : 'import');
                  setPreviewData(null);
                }}
                className="px-5 py-2.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-all flex items-center gap-1.5"
              >
                <i className="fas fa-arrow-left"></i>
                <span>返回</span>
              </button>
              <button
                onClick={handleDoImport}
                disabled={loading}
                className="px-6 py-2.5 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg shadow-green-500/20 hover:shadow-green-500/30 hover:-translate-y-0.5 flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <i className="fas fa-spinner fa-spin"></i>
                    <span>导入中...</span>
                  </>
                ) : (
                  <>
                    <i className="fas fa-check"></i>
                    <span>确认导入</span>
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
