import { useState, useEffect } from 'react';
import {
  X,
  FileCode,
  Terminal,
  Upload,
  AlertCircle,
  Loader2,
  Download,
  CheckCircle,
  XCircle,
  Folder,
  FolderOpen,
} from 'lucide-react';
import { API_BASE_URL } from '../../../../config/api';
import { Collection, HttpRequest, fetchCollections, fetchCollections as apiFetchCollections, importCurl, exportCollection } from '../../../../services/httpClientApi';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

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
      <Card className="w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold">导入/导出</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* 标签页 */}
        <Tabs
          value={activeTab}
          onValueChange={(v) => {
            const next = v as 'import-postman' | 'import-curl' | 'export';
            if (next === 'import-postman') {
              setImportResult(null);
              setError(null);
            } else if (next === 'import-curl') {
              setCurlResult(null);
              setError(null);
            } else {
              setError(null);
            }
            setActiveTab(next);
          }}
          className="flex flex-col flex-1 overflow-hidden"
        >
          <TabsList className="px-6 w-full justify-start rounded-none border-b border-border bg-transparent">
            <TabsTrigger value="import-postman" className="gap-2">
              <FileCode className="w-4 h-4" />
              Postman
            </TabsTrigger>
            <TabsTrigger value="import-curl" className="gap-2">
              <Terminal className="w-4 h-4" />
              cURL
            </TabsTrigger>
            <TabsTrigger value="export" className="gap-2">
              <Upload className="w-4 h-4" />
              导出
            </TabsTrigger>
          </TabsList>

          {/* 内容区域 */}
          <div className="flex-1 overflow-y-auto p-6">
            {/* Postman 导入 */}
            <TabsContent value="import-postman">
            <div className="space-y-4">
              <div>
                <label className="text-sm text-ink-muted mb-2 block">
                  粘贴 Postman Collection v2.1 JSON
                </label>
                <textarea
                  value={importText}
                  onChange={(e) => setImportText(e.target.value)}
                  placeholder='{"info": {"name": "My API", "schema": "..."}, "item": [...]}'
                  className="w-full h-64 bg-canvas text-ink px-4 py-3 rounded-lg
                             border border-border font-mono text-sm resize-none
                             focus:border-accent-secondary focus:outline-none"
                />
              </div>

              {error && (
                <div className="bg-danger/10 border border-danger text-danger px-4 py-3 rounded-lg text-sm">
                  <AlertCircle className="w-4 h-4 mr-2" />
                  {error}
                </div>
              )}

              {importResult && (
                <div className={`
                  px-4 py-3 rounded-lg text-sm
                  ${importResult.success
                    ? 'bg-success/10 border border-success text-success'
                    : 'bg-danger/10 border border-danger text-danger'
                  }
                `}>
                  <div className="flex items-center mb-2">
                    {importResult.success ? (
                      <CheckCircle className="w-4 h-4 mr-2" />
                    ) : (
                      <XCircle className="w-4 h-4 mr-2" />
                    )}
                    {importResult.success ? '导入成功' : '导入失败'}
                  </div>
                  {importResult.success && (
                    <div>
                      <p>成功导入：{importResult.imported_count} 个请求</p>
                      {importResult.failed_count > 0 && (
                        <p className="text-accent-warning">失败：{importResult.failed_count} 个</p>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-end gap-3">
                <Button
                  variant="ghost"
                  onClick={onClose}
                >
                  取消
                </Button>
                <Button
                  variant="default"
                  onClick={handlePostmanImport}
                  disabled={loading || !importText.trim()}
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      导入中...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4 mr-2" />
                      导入
                    </>
                  )}
                </Button>
              </div>
            </div>
          </TabsContent>

          {/* cURL 导入 */}
          <TabsContent value="import-curl">
            <div className="space-y-4">
              <div>
                <label className="text-sm text-ink-muted mb-2 block">
                  粘贴 cURL 命令
                </label>
                <textarea
                  value={curlText}
                  onChange={(e) => setCurlText(e.target.value)}
                  placeholder={"curl -X POST https://api.example.com/users \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"name\": \"test\"}'"}
                  className="w-full h-48 bg-canvas text-ink px-4 py-3 rounded-lg
                             border border-border font-mono text-sm resize-none
                             focus:border-accent-secondary focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm text-ink-muted mb-1 block">请求名称</label>
                  <Input
                    type="text"
                    value={curlName}
                    onChange={(e) => setCurlName(e.target.value)}
                    placeholder="自动命名"
                    className="w-full text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm text-ink-muted mb-1 block">目标集合</label>
                  <Select value={curlCollectionId} onValueChange={setCurlCollectionId}>
                    <SelectTrigger className="w-full text-sm">
                      <SelectValue placeholder="请选择集合" />
                    </SelectTrigger>
                    <SelectContent>
                      {collections.map(c => (
                        <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {error && (
                <div className="bg-danger/10 border border-danger text-danger px-4 py-3 rounded-lg text-sm">
                  <AlertCircle className="w-4 h-4 mr-2" />
                  {error}
                </div>
              )}

              {curlResult && (
                <div className="bg-success/10 border border-success text-success px-4 py-3 rounded-lg text-sm">
                  <div className="flex items-center mb-2">
                    <CheckCircle className="w-4 h-4 mr-2" />
                    cURL 导入成功
                  </div>
                  <div className="font-mono text-xs space-y-1 mt-2">
                    <p><span className="text-ink-faint">方法：</span>{curlResult.method}</p>
                    <p><span className="text-ink-faint">URL：</span>{curlResult.url}</p>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3">
                <Button
                  variant="ghost"
                  onClick={onClose}
                >
                  取消
                </Button>
                <Button
                  variant="default"
                  onClick={handleCurlImport}
                  disabled={curlLoading || !curlText.trim() || !curlCollectionId}
                >
                  {curlLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      导入中...
                    </>
                  ) : (
                    <>
                      <Terminal className="w-4 h-4 mr-2" />
                      导入 cURL
                    </>
                  )}
                </Button>
              </div>
            </div>
          </TabsContent>

          {/* 导出 */}
          <TabsContent value="export">
            <div className="space-y-4">
              <p className="text-ink-muted text-sm">
                选择要导出的集合，导出为 Postman Collection v2.1 格式
              </p>

              {collections.length === 0 ? (
                <div className="text-center py-8 text-ink-faint">
                  <FolderOpen className="w-8 h-8 mb-2 opacity-50" />
                  <p className="text-sm">暂无集合</p>
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={selectAll}
                      className="text-xs text-accent-secondary hover:text-accent-secondary h-auto px-2 py-0"
                    >
                      全选
                    </Button>
                    <span className="text-ink-faint">|</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={deselectAll}
                      className="text-xs text-ink-muted hover:text-ink-muted h-auto px-2 py-0"
                    >
                      取消全选
                    </Button>
                    <span className="text-xs text-ink-faint ml-auto">
                      已选 {selectedCollections.length}/{collections.length}
                    </span>
                  </div>

                  <div className="max-h-64 overflow-y-auto space-y-1 border border-border rounded-lg p-2">
                    {collections.map(c => (
                      <label
                        key={c.id}
                        className="flex items-center gap-3 px-3 py-2 rounded cursor-pointer
                                   hover:bg-surface-2/50 transition-colors text-sm"
                      >
                        <Input
                          type="checkbox"
                          checked={selectedCollections.includes(c.id)}
                          onChange={() => toggleCollection(c.id)}
                          className="h-4 w-4 p-0 cursor-pointer"
                        />
                        <Folder className="w-3 h-3 text-ink-faint" />
                        <span className="truncate">{c.name}</span>
                      </label>
                    ))}
                  </div>
                </>
              )}

              {error && (
                <div className="bg-danger/10 border border-danger text-danger px-4 py-3 rounded-lg text-sm">
                  <AlertCircle className="w-4 h-4 mr-2" />
                  {error}
                </div>
              )}

              <div className="flex justify-end gap-3">
                <Button
                  variant="ghost"
                  onClick={onClose}
                >
                  取消
                </Button>
                <Button
                  variant="default"
                  onClick={handleExport}
                  disabled={exportLoading || selectedCollections.length === 0}
                >
                  {exportLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      导出中...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4 mr-2" />
                      导出
                    </>
                  )}
                </Button>
              </div>
            </div>
          </TabsContent>
          </div>
        </Tabs>
      </Card>
    </div>
  );
}
