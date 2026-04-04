import { useState } from 'react';
import { API_BASE_URL } from '../../../../config/api';

interface ImportExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImportSuccess?: (result: any) => void;
}

export default function ImportExportModal({
  isOpen,
  onClose,
  onImportSuccess,
}: ImportExportModalProps) {
  const [activeTab, setActiveTab] = useState<'import' | 'export'>('import');
  const [importText, setImportText] = useState('');
  const [importResult, setImportResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleImport = async () => {
    if (!importText.trim()) {
      setError('请输入 Postman Collection JSON');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const collectionData = JSON.parse(importText);

      const response = await fetch(`${API_BASE_URL}/http-client/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(collectionData),
      });

      if (!response.ok) {
        throw new Error('导入失败');
      }

      const result = await response.json();
      setImportResult(result);

      if (result.success && onImportSuccess) {
        onImportSuccess(result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '导入失败');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (collectionId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/http-client/export/${collectionId}`);
      if (!response.ok) {
        throw new Error('导出失败');
      }

      const data = await response.json();

      // 下载文件
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${data.info?.name || 'collection'}.postman_collection.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : '导出失败');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-lg w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold">导入/导出</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <i className="fas fa-times"></i>
          </button>
        </div>

        {/* 标签页 */}
        <div className="flex items-center gap-1 px-6 border-b border-slate-700">
          <button
            onClick={() => {
              setActiveTab('import');
              setImportResult(null);
              setError(null);
            }}
            className={`
              px-4 py-3 text-sm transition-colors border-b-2
              ${activeTab === 'import'
                ? 'text-purple-400 border-purple-500'
                : 'text-slate-400 border-transparent hover:text-slate-300'
            }
            `}
          >
            <i className="fas fa-download mr-2"></i>
            导入
          </button>
          <button
            onClick={() => {
              setActiveTab('export');
              setError(null);
            }}
            className={`
              px-4 py-3 text-sm transition-colors border-b-2
              ${activeTab === 'export'
                ? 'text-purple-400 border-purple-500'
                : 'text-slate-400 border-transparent hover:text-slate-300'
            }
            `}
          >
            <i className="fas fa-upload mr-2"></i>
            导出
          </button>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'import' ? (
            <div className="space-y-4">
              <div>
                <label className="text-sm text-slate-400 mb-2 block">
                  粘贴 Postman Collection v2.1 JSON
                </label>
                <textarea
                  value={importText}
                  onChange={(e) => setImportText(e.target.value)}
                  placeholder='{"info": {"name": "My API", "schema": "..."}, "item": [...]}'
                  className="w-full h-64 bg-slate-900 text-white px-4 py-3 rounded-lg
                             border border-slate-600 font-mono text-sm resize-none
                             focus:border-purple-500 focus:outline-none"
                />
              </div>

              {error && (
                <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg text-sm">
                  <i className="fas fa-exclamation-circle mr-2"></i>
                  {error}
                </div>
              )}

              {importResult && (
                <div className={`
                  px-4 py-3 rounded-lg text-sm
                  ${importResult.success
                    ? 'bg-green-500/10 border border-green-500 text-green-400'
                    : 'bg-red-500/10 border border-red-500 text-red-400'
                  }
                `}>
                  <div className="flex items-center mb-2">
                    <i className={`fas mr-2 ${importResult.success ? 'fa-check-circle' : 'fa-times-circle'}`}></i>
                    {importResult.success ? '导入成功' : '导入失败'}
                  </div>
                  {importResult.success && (
                    <div>
                      <p>成功导入：{importResult.imported_count} 个请求</p>
                      {importResult.failed_count > 0 && (
                        <p className="text-yellow-400">失败：{importResult.failed_count} 个</p>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-end gap-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleImport}
                  disabled={loading || !importText.trim()}
                  className={`
                    px-6 py-2 rounded-lg font-medium transition-colors
                    ${loading || !importText.trim()
                      ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
                      : 'bg-purple-500 hover:bg-purple-600 text-white'
                    }
                  `}
                >
                  {loading ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i>
                      导入中...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-download mr-2"></i>
                      导入
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-slate-400 text-sm">
                选择一个集合进行导出，导出为 Postman Collection v2.1 格式
              </p>

              {/* TODO: 添加集合选择器 */}
              <div className="text-center py-8 text-slate-500">
                <i className="fas fa-info-circle text-2xl mb-2 opacity-50"></i>
                <p className="text-sm">导出功能开发中...</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
