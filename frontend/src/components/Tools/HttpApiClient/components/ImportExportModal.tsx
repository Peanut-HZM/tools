import { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../../../config/api';
import { Collection, HttpRequest, fetchCollections, fetchCollections as apiFetchCollections, importCurl, exportCollection } from '../../../../services/httpClientApi';

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
  const [activeTab, setActiveTab] = useState<'import-postman' | 'import-curl' | 'export'>('import-postman');
  const [importText, setImportText] = useState('');
  const [curlText, setCurlText] = useState('');
  const [importResult, setImportResult] = useState<any>(null);
  const [curlResult, setCurlResult] = useState<HttpRequest | null>(null);
  const [curlCollectionId, setCurlCollectionId] = useState<string>('');
  const [curlName, setCurlName] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [curlLoading, setCurlLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollections, setSelectedCollections] = useState<string[]>([]);
  const [exportLoading, setExportLoading] = useState(false);

  // 加载集合列表
  useEffect(() => {
    if (isOpen && activeTab === 'export') {
      fetchCollections().then(setCollections).catch(console.error);
    }
  }, [isOpen, activeTab]);

  const handlePostmanImport = async () => {
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

  const handleCurlImport = async () => {
    if (!curlText.trim()) {
      setError('请输入 cURL 命令');
      return;
    }
    if (!curlCollectionId) {
      setError('请选择目标集合');
      return;
    }

    setCurlLoading(true);
    setError(null);

    try {
      const name = curlName.trim() || `cURL_${new Date().toLocaleTimeString()}`;
      const created = await importCurl(curlText, curlCollectionId, name);
      setCurlResult(created);

      if (onImportSuccess) {
        onImportSuccess({ success: true, imported_count: 1, failed_count: 0 });
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'cURL 解析失败');
    } finally {
      setCurlLoading(false);
    }
  };

  const handleExport = async () => {
    if (selectedCollections.length === 0) {
      setError('请选择至少一个集合');
      return;
    }

    setExportLoading(true);
    setError(null);

    try {
      for (const collectionId of selectedCollections) {
        const data = await exportCollection(collectionId);
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${data.info?.name || 'collection'}.postman_collection.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '导出失败');
    } finally {
      setExportLoading(false);
    }
  };

  const toggleCollection = (id: string) => {
    setSelectedCollections(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    setSelectedCollections(collections.map(c => c.id));
  };

  const deselectAll = () => {
    setSelectedCollections([]);
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
              setActiveTab('import-postman');
              setImportResult(null);
              setError(null);
            }}
            className={`
              px-4 py-3 text-sm transition-colors border-b-2
              ${activeTab === 'import-postman'
                ? 'text-purple-400 border-purple-500'
                : 'text-slate-400 border-transparent hover:text-slate-300'
            }
            `}
          >
            <i className="fas fa-file-code mr-2"></i>
            Postman
          </button>
          <button
            onClick={() => {
              setActiveTab('import-curl');
              setCurlResult(null);
              setError(null);
            }}
            className={`
              px-4 py-3 text-sm transition-colors border-b-2
              ${activeTab === 'import-curl'
                ? 'text-purple-400 border-purple-500'
                : 'text-slate-400 border-transparent hover:text-slate-300'
            }
            `}
          >
            <i className="fas fa-terminal mr-2"></i>
            cURL
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
          {/* Postman 导入 */}
          {activeTab === 'import-postman' && (
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
                  onClick={handlePostmanImport}
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
          )}

          {/* cURL 导入 */}
          {activeTab === 'import-curl' && (
            <div className="space-y-4">
              <div>
                <label className="text-sm text-slate-400 mb-2 block">
                  粘贴 cURL 命令
                </label>
                <textarea
                  value={curlText}
                  onChange={(e) => setCurlText(e.target.value)}
                  placeholder={"curl -X POST https://api.example.com/users \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"name\": \"test\"}'"}
                  className="w-full h-48 bg-slate-900 text-white px-4 py-3 rounded-lg
                             border border-slate-600 font-mono text-sm resize-none
                             focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm text-slate-400 mb-1 block">请求名称</label>
                  <input
                    type="text"
                    value={curlName}
                    onChange={(e) => setCurlName(e.target.value)}
                    placeholder="自动命名"
                    className="w-full bg-slate-700 text-white px-3 py-2 rounded border border-slate-600 text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-400 mb-1 block">目标集合</label>
                  <select
                    value={curlCollectionId}
                    onChange={(e) => setCurlCollectionId(e.target.value)}
                    className="w-full bg-slate-700 text-white px-3 py-2 rounded border border-slate-600 text-sm"
                  >
                    <option value="">请选择集合</option>
                    {collections.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              {error && (
                <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg text-sm">
                  <i className="fas fa-exclamation-circle mr-2"></i>
                  {error}
                </div>
              )}

              {curlResult && (
                <div className="bg-green-500/10 border border-green-500 text-green-400 px-4 py-3 rounded-lg text-sm">
                  <div className="flex items-center mb-2">
                    <i className="fas fa-check-circle mr-2"></i>
                    cURL 导入成功
                  </div>
                  <div className="font-mono text-xs space-y-1 mt-2">
                    <p><span className="text-slate-500">方法：</span>{curlResult.method}</p>
                    <p><span className="text-slate-500">URL：</span>{curlResult.url}</p>
                  </div>
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
                  onClick={handleCurlImport}
                  disabled={curlLoading || !curlText.trim() || !curlCollectionId}
                  className={`
                    px-6 py-2 rounded-lg font-medium transition-colors
                    ${curlLoading || !curlText.trim() || !curlCollectionId
                      ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
                      : 'bg-purple-500 hover:bg-purple-600 text-white'
                    }
                  `}
                >
                  {curlLoading ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i>
                      导入中...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-terminal mr-2"></i>
                      导入 cURL
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* 导出 */}
          {activeTab === 'export' && (
            <div className="space-y-4">
              <p className="text-slate-400 text-sm">
                选择要导出的集合，导出为 Postman Collection v2.1 格式
              </p>

              {collections.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <i className="fas fa-folder-open text-2xl mb-2 opacity-50"></i>
                  <p className="text-sm">暂无集合</p>
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={selectAll}
                      className="text-xs text-purple-400 hover:text-purple-300"
                    >
                      全选
                    </button>
                    <span className="text-slate-600">|</span>
                    <button
                      onClick={deselectAll}
                      className="text-xs text-slate-400 hover:text-slate-300"
                    >
                      取消全选
                    </button>
                    <span className="text-xs text-slate-500 ml-auto">
                      已选 {selectedCollections.length}/{collections.length}
                    </span>
                  </div>

                  <div className="max-h-64 overflow-y-auto space-y-1 border border-slate-700 rounded-lg p-2">
                    {collections.map(c => (
                      <label
                        key={c.id}
                        className="flex items-center gap-3 px-3 py-2 rounded cursor-pointer
                                   hover:bg-slate-700/50 transition-colors text-sm"
                      >
                        <input
                          type="checkbox"
                          checked={selectedCollections.includes(c.id)}
                          onChange={() => toggleCollection(c.id)}
                          className="rounded border-slate-600 bg-slate-700 text-purple-500"
                        />
                        <i className="fas fa-folder text-slate-500 text-xs"></i>
                        <span className="truncate">{c.name}</span>
                      </label>
                    ))}
                  </div>
                </>
              )}

              {error && (
                <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg text-sm">
                  <i className="fas fa-exclamation-circle mr-2"></i>
                  {error}
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
                  onClick={handleExport}
                  disabled={exportLoading || selectedCollections.length === 0}
                  className={`
                    px-6 py-2 rounded-lg font-medium transition-colors
                    ${exportLoading || selectedCollections.length === 0
                      ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
                      : 'bg-purple-500 hover:bg-purple-600 text-white'
                    }
                  `}
                >
                  {exportLoading ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i>
                      导出中...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-upload mr-2"></i>
                      导出
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
