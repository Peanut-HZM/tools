/**
 * 文件面板组件
 */
import React, { useState, useEffect } from 'react';
import { fileApi, CrossFile, formatFileSize, formatDateTime, getFileTypeIcon } from '../../../services/crossShare';
import { FilePreviewModal } from './FilePreviewModal';
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";

interface FilePanelProps {
  onStatsUpdate: () => void;
}

const FilePanel: React.FC<FilePanelProps> = ({ onStatsUpdate }) => {
  const [files, setFiles] = useState<CrossFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  // 预览相关状态
  const [previewFile, setPreviewFile] = useState<CrossFile | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    try {
      const data = await fileApi.getFiles(100, 0);
      setFiles(data);
    } catch (error) {
      console.error('Failed to load files:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);

    try {
      // 上传文件到后端
      const result = await fileApi.uploadFile(file, (progress) => {
        setUploadProgress(progress);
      });

      setUploadProgress(100);
      onStatsUpdate();
      loadFiles();
    } catch (error) {
      console.error('Failed to upload file:', error);
    } finally {
      setUploading(false);
      setUploadProgress(0);
      // 清空 input
      e.target.value = '';
    }
  };

  const handleDelete = async (fileId: string) => {
    if (!confirm('确定要删除这个文件吗？')) return;

    try {
      await fileApi.deleteFile(fileId);
      onStatsUpdate();
      loadFiles();
    } catch (error) {
      console.error('Failed to delete file:', error);
    }
  };

  const handleDownload = async (file: CrossFile) => {
    try {
      const { download_url } = await fileApi.getDownloadUrl(file.id);
      // 使用 a 标签的 download 属性强制下载，而不是在新标签页打开
      const link = document.createElement('a');
      link.href = download_url;
      link.download = file.file_name;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Failed to get download URL:', error);
    }
  };

  const handlePreview = async (file: CrossFile) => {
    try {
      const url = await fileApi.getPreviewUrl(file.id);
      setPreviewUrl(url);
      setPreviewFile(file);
      setIsPreviewOpen(true);
    } catch (error) {
      console.error('Failed to get preview URL:', error);
    }
  };

  const handleClosePreview = () => {
    setIsPreviewOpen(false);
    setPreviewFile(null);
    setPreviewUrl(null);
  };

  const filteredFiles = files.filter((f) =>
    f.file_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <Card className="w-full h-full flex items-center justify-center shadow-md">
        <div className="text-ink-muted">加载中...</div>
      </Card>
    );
  }

  return (
    <Card className="w-full h-full flex flex-col shadow-md overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 p-6 border-b border-border">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-ink">📁 文件管理</h2>

          <div className="flex items-center space-x-3">
            {/* Search */}
            <Input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="搜索文件..."
              className="w-64 placeholder-slate-500 focus-visible:border-blue-500"
            />

            {/* Upload Button */}
            <label className="px-4 py-2 bg-accent hover:bg-accent-hover text-white font-semibold rounded-lg transition-colors cursor-pointer inline-flex items-center justify-center whitespace-nowrap text-sm font-medium h-10">
              📤 上传文件
              <input
                type="file"
                onChange={handleFileSelect}
                className="hidden"
                disabled={uploading}
              />
            </label>
          </div>
        </div>

        {/* Upload Progress */}
        {uploading && (
          <div className="mt-4">
            <div className="text-sm text-ink-muted mb-1">上传中... {uploadProgress}%</div>
            <div className="w-full h-2 bg-surface-2 rounded-full overflow-hidden">
              <div
                className="h-full bg-accent transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* File List - 可滚动 */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-700">
        {filteredFiles.length === 0 ? (
          <div className="text-center text-ink-faint py-16">
            <div className="text-6xl mb-4">📭</div>
            <div className="text-ink-muted">暂无文件</div>
            <div className="text-sm mt-2 text-ink-faint">上传一个文件开始跨设备共享</div>
          </div>
        ) : (
          filteredFiles.map((file) => (
            <div
              key={file.id}
              className="flex items-center justify-between p-4 hover:bg-surface-2/30 transition-colors"
            >
              <div className="flex items-center space-x-4">
                <div className="text-3xl">{getFileTypeIcon(file.file_type)}</div>
                <div>
                  <div className="text-ink font-medium">{file.file_name}</div>
                  <div className="text-sm text-ink-muted">
                    {formatFileSize(file.file_size)} • {formatDateTime(file.created_at)}
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handlePreview(file)}
                >
                  👁️ 预览
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleDownload(file)}
                >
                  ⬇️ 下载
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleDelete(file.id)}
                  className="text-accent-danger bg-red-500/10 hover:bg-red-500/20"
                >
                  🗑️ 删除
                </Button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* 预览模态框 */}
      <FilePreviewModal
        file={previewFile}
        previewUrl={previewUrl}
        isOpen={isPreviewOpen}
        onClose={handleClosePreview}
        onDownload={() => previewFile && handleDownload(previewFile)}
      />
    </Card>
  );
};

export default FilePanel;
