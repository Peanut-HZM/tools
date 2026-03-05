/**
 * 文件面板组件
 */
import React, { useState, useEffect } from 'react';
import { fileApi, CrossFile, formatFileSize, formatDateTime, getFileTypeIcon } from '../../../services/crossShare';

interface FilePanelProps {
  onStatsUpdate: () => void;
}

const FilePanel: React.FC<FilePanelProps> = ({ onStatsUpdate }) => {
  const [files, setFiles] = useState<CrossFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

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
      // 获取上传令牌
      const tokenData = await fileApi.getUploadToken(file.name, file.size, file.type);

      // 上传到 OSS
      await fileApi.uploadToOSS(file, tokenData.upload_url, tokenData.oss_key);

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
      // 在新窗口打开下载链接
      window.open(download_url, '_blank');
    } catch (error) {
      console.error('Failed to get download URL:', error);
    }
  };

  const filteredFiles = files.filter((f) =>
    f.file_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-white/60">加载中...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white">📁 文件管理</h2>

            <div className="flex items-center space-x-3">
              {/* Search */}
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="搜索文件..."
                className="px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-yellow-500 w-64"
              />

              {/* Upload Button */}
              <label className="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-black font-semibold rounded-lg transition-colors cursor-pointer">
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
              <div className="text-sm text-white/60 mb-1">上传中... {uploadProgress}%</div>
              <div className="w-full h-2 bg-white/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-yellow-500 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* File List */}
        <div className="divide-y divide-white/5">
          {filteredFiles.length === 0 ? (
            <div className="text-center text-white/40 py-16">
              <div className="text-6xl mb-4">📭</div>
              <div>暂无文件</div>
              <div className="text-sm mt-2">上传一个文件开始跨设备共享</div>
            </div>
          ) : (
            filteredFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  <div className="text-3xl">{getFileTypeIcon(file.file_type)}</div>
                  <div>
                    <div className="text-white font-medium">{file.file_name}</div>
                    <div className="text-sm text-white/40">
                      {formatFileSize(file.file_size)} • {formatDateTime(file.created_at)}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleDownload(file)}
                    className="px-3 py-1.5 text-sm bg-white/5 hover:bg-white/10 text-white rounded-lg transition-colors"
                  >
                    ⬇️ 下载
                  </button>
                  <button
                    onClick={() => handleDelete(file.id)}
                    className="px-3 py-1.5 text-sm bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
                  >
                    🗑️ 删除
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default FilePanel;
