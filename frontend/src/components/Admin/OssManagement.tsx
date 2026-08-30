import { useState, useEffect } from 'react';
import { File, Download, Eye, X } from 'lucide-react';
import { listOssFiles, deleteOssFile, OssFile } from '../../api/adminApi';
import { useToast } from '../../hooks/useToast';
import { useAuth } from '../../stores/authStore';
import { Card } from '@/components/ui/Card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog';

export default function OssManagement() {
  const [files, setFiles] = useState<OssFile[]>([]);
  const [loading, setLoading] = useState(true);
  const { success, error } = useToast();
  const { user } = useAuth();

  // 筛选状态
  const [showMyFilesOnly, setShowMyFilesOnly] = useState(false);

  // 文件预览弹窗状态
  const [previewFile, setPreviewFile] = useState<OssFile | null>(null);

  const fetchFiles = async () => {
    try {
      const data = await listOssFiles();
      setFiles(data);
    } catch (e) {
      error('获取文件列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const handleDelete = async (path: string) => {
    if (!confirm('确定要删除该文件吗？')) return;

    try {
      await deleteOssFile(path);
      setFiles(files.filter(f => f.path !== path));
      success('文件删除成功');
    } catch (e) {
      error('文件删除失败');
    }
  };

  // 下载文件
  const handleDownload = async (file: OssFile) => {
    try {
      const response = await fetch(file.url);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      success('文件下载已开始');
    } catch (e) {
      error('文件下载失败');
    }
  };

  // 打开预览弹窗
  const handlePreview = (file: OssFile) => {
    setPreviewFile(file);
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const isImage = (type: string) => type?.startsWith('image/');
  const isPdf = (type: string) => type === 'application/pdf';

  const isPreviewableText = (file: OssFile) => {
    return file.type?.startsWith('text/') ||
      /\.(md|txt|json|xml|yaml|yml|toml|ini|cfg|conf|sh|bash|py|js|ts|tsx|jsx|html|css|scss|less|sql|log|csv)$/i.test(file.name);
  };

  const filteredFiles = showMyFilesOnly && user
    ? files.filter(f => f.uploaded_by === user.user_id)
    : files;

  // 渲染预览内容
  const renderPreviewContent = (file: OssFile) => {
    if (isImage(file.type)) {
      return (
        <div className="flex items-center justify-center max-h-[70vh]">
          <img
            src={file.url}
            alt={file.name}
            className="max-w-full max-h-[70vh] object-contain rounded"
          />
        </div>
      );
    }
    if (isPdf(file.type)) {
      return (
        <div className="w-full h-[70vh]">
          <iframe
            src={file.url}
            className="w-full h-full border-0 rounded"
            title={file.name}
          />
        </div>
      );
    }
    if (isPreviewableText(file)) {
      return (
        <div className="max-h-[70vh] overflow-auto">
          <TextPreview url={file.url} />
        </div>
      );
    }
    // 不可预览的文件类型，显示文件信息
    return (
      <div className="flex flex-col items-center justify-center py-12 text-ink-muted">
        <File className="w-16 h-16 mb-4 text-ink-faint" />
        <p className="text-lg mb-2">该文件类型暂不支持预览</p>
        <p className="text-sm text-ink-faint">文件类型: {file.type || '未知'}</p>
        <button
          onClick={() => handleDownload(file)}
          className="mt-4 flex items-center gap-2 px-4 py-2 bg-accent text-white rounded hover:bg-accent/90 transition-colors"
        >
          <Download className="w-4 h-4" />
          下载文件
        </button>
      </div>
    );
  };

  if (loading) return <div className="text-ink">加载中...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-ink">OSS 文件管理</h2>

        <Card className="flex items-center space-x-2 bg-surface-2 px-3 py-1.5">
          <input
            type="checkbox"
            id="showMyFiles"
            checked={showMyFilesOnly}
            onChange={(e) => setShowMyFilesOnly(e.target.checked)}
            className="w-4 h-4 text-accent-info rounded focus:ring-accent bg-surface-1 border-border"
          />
          <label htmlFor="showMyFiles" className="text-sm text-ink-muted cursor-pointer select-none">
            只看我的文件
          </label>
        </Card>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-ink-muted">
          <thead className="bg-surface-2 text-ink uppercase text-xs">
            <tr>
              <th className="px-6 py-3">预览</th>
              <th className="px-6 py-3">文件名</th>
              <th className="px-6 py-3">类型</th>
              <th className="px-6 py-3">大小</th>
              <th className="px-6 py-3">上传者</th>
              <th className="px-6 py-3">上传时间</th>
              <th className="px-6 py-3">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredFiles.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-4 text-center text-ink-faint">
                  暂无文件
                </td>
              </tr>
            ) : (
              filteredFiles.map((file) => (
                <tr key={file.id} className="hover:bg-surface-2/50">
                  <td className="px-6 py-4">
                    {isImage(file.type) ? (
                      <div className="w-12 h-12 bg-surface-1 rounded overflow-hidden">
                        <img
                          src={file.url}
                          alt={file.name}
                          className="w-full h-full object-cover cursor-pointer hover:opacity-80"
                          onClick={() => handlePreview(file)}
                        />
                      </div>
                    ) : (
                      <div
                        className="w-12 h-12 bg-surface-1 rounded flex items-center justify-center text-ink-faint cursor-pointer hover:bg-surface-2 transition-colors"
                        onClick={() => handlePreview(file)}
                      >
                        <File className="w-6 h-6" />
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 max-w-xs">
                    <div className="truncate" title={file.name}>
                      <button
                        onClick={() => handlePreview(file)}
                        className="text-accent hover:underline text-left"
                      >
                        {file.name}
                      </button>
                    </div>
                    <div className="text-xs text-ink-faint truncate">{file.path}</div>
                  </td>
                  <td className="px-6 py-4 text-sm">{file.type || 'Unknown'}</td>
                  <td className="px-6 py-4 text-sm">{formatSize(file.size)}</td>
                  <td className="px-6 py-4 text-sm">{file.uploaded_by}</td>
                  <td className="px-6 py-4 text-sm">
                    {new Date(file.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => handlePreview(file)}
                        className="text-accent hover:text-accent/80 transition-colors text-sm flex items-center gap-1"
                        title="查看"
                      >
                        <Eye className="w-4 h-4" />
                        查看
                      </button>
                      <button
                        onClick={() => handleDownload(file)}
                        className="text-accent-info hover:text-accent-info/80 transition-colors text-sm flex items-center gap-1"
                        title="下载"
                      >
                        <Download className="w-4 h-4" />
                        下载
                      </button>
                      <button
                        onClick={() => handleDelete(file.path)}
                        className="text-danger hover:text-danger/80 transition-colors text-sm"
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* 文件预览弹窗 */}
      <Dialog open={!!previewFile} onOpenChange={(open) => !open && setPreviewFile(null)}>
        <DialogContent className="max-w-4xl w-[90vw] max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 pr-8">
              <File className="w-5 h-5 text-ink-muted shrink-0" />
              <span className="truncate">{previewFile?.name}</span>
            </DialogTitle>
          </DialogHeader>

          {previewFile && (
            <div className="flex-1 overflow-hidden">
              {/* 文件信息栏 */}
              <div className="flex items-center justify-between mb-3 text-sm text-ink-muted bg-surface-2 rounded px-3 py-2">
                <div className="flex items-center gap-4">
                  <span>类型: {previewFile.type || '未知'}</span>
                  <span>大小: {formatSize(previewFile.size)}</span>
                  <span>上传者: {previewFile.uploaded_by}</span>
                </div>
                <button
                  onClick={() => handleDownload(previewFile)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-accent text-white rounded hover:bg-accent/90 transition-colors text-sm"
                >
                  <Download className="w-4 h-4" />
                  下载
                </button>
              </div>

              {/* 预览内容 */}
              {renderPreviewContent(previewFile)}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// 文本文件预览组件
function TextPreview({ url }: { url: string }) {
  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch(url)
      .then(res => res.text())
      .then(content => {
        if (!cancelled) {
          setText(content);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(true);
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [url]);

  if (loading) return <div className="text-center py-8 text-ink-muted">加载文本内容中...</div>;
  if (error) return <div className="text-center py-8 text-danger">无法加载文本内容</div>;

  return (
    <pre className="bg-surface-2 text-ink text-sm p-4 rounded overflow-auto max-h-[60vh] whitespace-pre-wrap break-words font-mono">
      {text}
    </pre>
  );
}
