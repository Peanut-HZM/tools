/**
 * 课程导入/导出对话框
 */
import React, { useState, useRef } from 'react';
import {
  X,
  Info,
  GraduationCap,
  FileCode,
  FileArchive,
  Lightbulb,
  Settings as SettingsIcon,
  FileText,
  List,
  AlertTriangle,
  Loader2,
  Download,
  Eye,
  ArrowLeft,
  Check,
  ReactNode,
  Upload,
  CloudUpload,
} from 'lucide-react';
import {
  exportCourseData,
  downloadCourseExport,
  downloadCourseExportZip,
  previewImport,
  importCourseData,
  type ExportData,
  type ImportConflictInfo,
} from '../../../services/coursePlatform';
import { useToast } from '../../../hooks/useToast';
import { generateTimestampFilename } from '../../../utils/filenameUtils';
import { Card } from "@/components/ui/Card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

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
      link.setAttribute('download', generateTimestampFilename('course-export', 'json'));
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
      <Card className="rounded-2xl shadow-lg max-w-2xl w-full max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              mode === 'export'
                ? 'bg-gradient-to-br from-success/20 to-success/20 border border-success/30'
                : mode === 'import'
                ? 'bg-gradient-to-br from-warning/20 to-accent-warm/20 border border-warning/30'
                : 'bg-gradient-to-br from-accent-info/20 to-blue-500/20 border border-accent/30'
            }`}>
              {mode === 'export' ? (
                <Download className="w-5 h-5 text-success" />
              ) : mode === 'import' ? (
                <Upload className="w-5 h-5 text-warning" />
              ) : (
                <Eye className="w-5 h-5 text-accent" />
              )}
            </div>
            <div>
              <h2 className="text-2xl font-bold text-ink">
                {mode === 'export' && '导出课程数据'}
                {mode === 'import' && '导入课程数据'}
                {mode === 'preview' && '导入预览'}
              </h2>
              <p className="text-ink-muted text-sm">
                {mode === 'export' && '将课程数据导出为 JSON 或 Markdown 格式'}
                {mode === 'import' && '从 JSON 或 Markdown 文件导入课程数据'}
                {mode === 'preview' && '预览导入操作，确认变更内容'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-ink-muted hover:text-ink hover:bg-surface-2/50 rounded-lg transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {mode === 'export' && (
            <div className="space-y-6">
              {/* 导出说明卡片 */}
              <div className="bg-gradient-to-br from-success/10 to-success/10 rounded-xl border border-success/20 p-5">
                <h3 className="text-success font-semibold mb-2 flex items-center gap-2">
                  <Info className="w-4 h-4" />
                  导出说明
                </h3>
                <p className="text-ink-muted text-sm leading-relaxed">
                  将当前课程的所有章节、测验和资源数据导出为 <strong className="text-ink">JSON 格式</strong> 文件。
                  导出的文件可用于数据备份或在其他环境中恢复课程数据。
                </p>
              </div>

              {/* 课程信息 */}
              <div className="space-y-3">
                <label className="text-ink-muted text-sm font-medium">当前课程:</label>
                <div className="px-4 py-3 bg-surface-2/50 border border-border/50 rounded-lg flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-accent-hover flex items-center justify-center">
                    <GraduationCap className="w-4 h-4 text-ink" />
                  </div>
                  <span className="text-ink font-medium">{courseTitle || '未命名课程'}</span>
                </div>
              </div>

              {/* 导出格式选项 */}
              <div className="space-y-3">
                <label className="text-ink-muted text-sm font-medium">导出格式:</label>
                <div className="grid grid-cols-2 gap-3">
                  {/* JSON 格式 */}
                  <button
                    onClick={handleExport}
                    disabled={loading}
                    className="px-4 py-3 bg-surface-2/50 border border-border rounded-lg text-ink-muted hover:border-accent/30 hover:bg-accent/10 hover:text-accent transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <FileCode className="w-4 h-4" />
                      <span className="font-medium">JSON 格式</span>
                    </div>
                    <p className="text-xs text-ink-faint text-left">完整数据，包含所有测验和资源</p>
                  </button>

                  {/* Markdown/ZIP 格式 */}
                  <button
                    onClick={handleExportZip}
                    disabled={loading}
                    className="px-4 py-3 bg-surface-2/50 border border-border rounded-lg text-ink-muted hover:border-success/50 hover:bg-success/10 hover:text-success transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <FileArchive className="w-4 h-4" />
                      <span className="font-medium">ZIP 压缩包</span>
                    </div>
                    <p className="text-xs text-ink-faint text-left">JSON + 所有章节 Markdown 文件</p>
                  </button>
                </div>

                {/* 格式说明 */}
                <div className="mt-3 p-4 bg-surface-2/30 rounded-lg border border-border/50">
                  <h4 className="text-ink font-medium text-sm mb-2 flex items-center gap-2">
                    <Info className="w-4 h-4 text-accent" />
                    格式说明
                  </h4>
                  <ul className="text-ink-muted text-xs space-y-1.5">
                    <li className="flex items-start gap-2">
                      <span className="text-accent mt-0.5">•</span>
                      <span><strong className="text-ink">JSON 格式</strong> - 适合程序化处理，完整保留所有数据结构</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-success mt-0.5">•</span>
                      <span><strong className="text-ink">ZIP 压缩包</strong> - 包含 JSON 数据和 Markdown 章节文件，便于手动编辑和版本控制</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {mode === 'import' && (
            <div className="space-y-6">
              {/* 导入说明卡片 */}
              <div className="bg-gradient-to-br from-warning/10 to-accent-warm/10 rounded-xl border border-warning/20 p-5">
                <h3 className="text-warning font-semibold mb-2 flex items-center gap-2">
                  <Lightbulb className="w-4 h-4" />
                  导入说明
                </h3>
                <p className="text-ink-muted text-sm leading-relaxed mb-4">
                  选择之前导出的 <strong className="text-ink">JSON 文件</strong> 进行导入。
                  建议先预览导入内容，确认数据无误后再执行导入操作。
                </p>

                {/* 导入策略 */}
                <div className="space-y-3">
                  <label className="text-ink-muted text-sm font-medium flex items-center gap-2">
                    <SettingsIcon className="w-4 h-4 text-warning" />
                    选择导入策略:
                  </label>
                  <Select
                    value={importStrategy}
                    onValueChange={(v) => setImportStrategy(v as 'merge' | 'replace' | 'skip_existing')}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="replace">🔄 替换（更新已存在的章节 slug）- 推荐</SelectItem>
                      <SelectItem value="merge">🔀 合并（跳过已存在的章节 slug）</SelectItem>
                      <SelectItem value="skip_existing">⏭️ 完全跳过（不导入任何已存在的章节）</SelectItem>
                    </SelectContent>
                  </Select>

                  {/* 策略说明 */}
                  <div className="mt-3 p-3 bg-surface-1/50 rounded-lg border border-border/50">
                    {importStrategy === 'replace' && (
                      <p className="text-ink-muted text-xs">
                        <span className="text-warning font-medium">替换模式（推荐）：</span>
                        对于已存在的章节 slug 将更新内容，同时导入新的章节。适合批量更新课程数据。
                      </p>
                    )}
                    {importStrategy === 'merge' && (
                      <p className="text-ink-muted text-xs">
                        <span className="text-accent font-medium">合并模式：</span>
                        对于已存在的章节 slug 将跳过，只导入新的章节。适合增量添加内容。
                      </p>
                    )}
                    {importStrategy === 'skip_existing' && (
                      <p className="text-ink-muted text-xs">
                        <span className="text-accent-secondary font-medium">跳过模式：</span>
                        完全跳过所有已存在的章节 slug，只导入全新的章节。最保守的策略。
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* 文件选择 */}
              <div className="space-y-3">
                <label className="text-ink-muted text-sm font-medium flex items-center gap-2">
                  <FileText className="w-4 h-4 text-warning" />
                  选择 JSON 文件:
                </label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className={`relative px-6 py-8 border-2 border-dashed rounded-xl transition-all cursor-pointer ${
                    selectedFile
                      ? 'border-accent/30 bg-accent/10'
                      : 'border-border hover:border-warning/50 hover:bg-warning/10'
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
                    <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-surface-2/50 flex items-center justify-center">
                      {selectedFile ? (
                        <FileCode className="w-8 h-8 text-accent" />
                      ) : (
                        <CloudUpload className="w-8 h-8 text-ink-muted" />
                      )}
                    </div>
                    {selectedFile ? (
                      <>
                        <p className="text-ink font-medium mb-1">{selectedFile.name}</p>
                        <p className="text-ink-muted text-xs">
                          {(selectedFile.size / 1024).toFixed(2)} KB
                        </p>
                      </>
                    ) : (
                      <>
                        <p className="text-ink-muted text-sm mb-1">点击选择文件或拖拽文件到此处</p>
                        <p className="text-ink-faint text-xs">仅支持 .json 格式文件</p>
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
                <div className="bg-gradient-to-br from-accent-info/10 to-accent-info/10 rounded-xl border border-accent-info/20 p-4">
                  <div className="text-ink-muted text-sm mb-1">导入章节</div>
                  <div className="text-ink text-3xl font-bold">{previewData.chapters_to_import || 0}</div>
                </div>
                <div className="bg-gradient-to-br from-warning/10 to-accent-warm/10 rounded-xl border border-warning/20 p-4">
                  <div className="text-ink-muted text-sm mb-1">更新章节</div>
                  <div className="text-ink text-3xl font-bold">{previewData.chapters_to_update || 0}</div>
                </div>
                <div className="bg-gradient-to-br from-surface-3/10 to-surface-3/10 rounded-xl border border-border/20 p-4">
                  <div className="text-ink-muted text-sm mb-1">跳过章节</div>
                  <div className="text-ink text-3xl font-bold">{previewData.chapters_to_skip || 0}</div>
                </div>
              </div>

              {/* 章节列表 */}
              <div className="bg-surface-2/30 rounded-xl border border-border/50 p-4">
                <h3 className="text-ink font-semibold mb-3 flex items-center gap-2">
                  <List className="w-4 h-4 text-accent" />
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
                            ? 'bg-success/10 border-success/20'
                            : conflict.conflict_type === 'will_update'
                            ? 'bg-warning/10 border-warning/20'
                            : 'bg-surface-3/10 border-border/20'
                        }`}
                      >
                        <span className="text-lg">{status.icon}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-ink text-sm font-medium truncate">{conflict.chapter_title}</div>
                          <div className="text-ink-muted text-xs truncate">{conflict.chapter_slug}</div>
                        </div>
                        <span className={`text-xs px-2.5 py-1 rounded-full ${
                          conflict.conflict_type === 'new'
                            ? 'bg-success/20 text-success'
                            : conflict.conflict_type === 'will_update'
                            ? 'bg-warning/20 text-warning'
                            : 'bg-surface-3/20 text-ink-muted'
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
                <div className="bg-warning/10 border border-warning/30 rounded-xl p-4">
                  <h3 className="text-warning font-semibold mb-2 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    警告
                  </h3>
                  <ul className="text-ink-muted text-sm space-y-1.5">
                    {previewData.warnings.map((warning: string, index: number) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="text-warning mt-0.5">•</span>
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
        <div className="flex items-center justify-end gap-3 p-6 border-t border-border bg-surface-1/30">
          {mode === 'export' && (
            <>
              <button
                onClick={onClose}
                className="px-5 py-2.5 text-ink-muted hover:text-ink hover:bg-surface-2/50 rounded-lg transition-all"
              >
                取消
              </button>
              <button
                onClick={handleExport}
                disabled={loading}
                className="px-6 py-2.5 bg-gradient-to-r from-success to-success hover:from-success hover:to-success text-ink rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg shadow-success/20 hover:shadow-success/30 hover:-translate-y-0.5 flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>导出中...</span>
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
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
                className="px-5 py-2.5 text-ink-muted hover:text-ink hover:bg-surface-2/50 rounded-lg transition-all"
              >
                取消
              </button>
              <button
                onClick={handlePreviewImport}
                disabled={!selectedFile || loading}
                className="px-6 py-2.5 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-ink rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg shadow-warning/20 hover:shadow-warning/30 hover:-translate-y-0.5 flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>处理中...</span>
                  </>
                ) : (
                  <>
                    <Eye className="w-4 h-4" />
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
                className="px-5 py-2.5 text-ink-muted hover:text-ink hover:bg-surface-2/50 rounded-lg transition-all flex items-center gap-1.5"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>返回</span>
              </button>
              <button
                onClick={handleDoImport}
                disabled={loading}
                className="px-6 py-2.5 bg-gradient-to-r from-success to-success hover:from-success hover:to-success text-ink rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg shadow-success/20 hover:shadow-success/30 hover:-translate-y-0.5 flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>导入中...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    <span>确认导入</span>
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </Card>
    </div>
  );
};

export default ImportExportDialog;
