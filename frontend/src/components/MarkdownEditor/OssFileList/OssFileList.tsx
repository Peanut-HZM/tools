/**
 * OssFileList Component - Displays OSS file list
 */
import { useState } from 'react';
import { useFileStore } from '../../../stores/fileStore';
import { uploadMarkdownToOss, readMarkdownFromOss, OssFileInfo } from '../../../api/markdownEditorApi';
import { useI18n } from '../../../i18n';
import { useToast } from '../../../hooks/useToast';

interface OssFileListProps {
  onFileOpen?: (filePath: string, content: string) => void;
}

export default function OssFileList({ onFileOpen }: OssFileListProps) {
  const { ossFiles, ossFilesLoading, loadOssFiles, setCurrentOssFile } = useFileStore();
  const { t } = useI18n();
  const { toast, showToast } = useToast();
  const [uploading, setUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleRefresh = async () => {
    await loadOssFiles();
  };

  const handleFileClick = async (fileInfo: OssFileInfo) => {
    try {
      setCurrentOssFile(fileInfo.file_path);
      const result = await readMarkdownFromOss(fileInfo.file_path);
      if (result.success && onFileOpen) {
        onFileOpen(fileInfo.file_path, result.content);
        showToast(t.ossFile.openSuccess || '已打开云端文件', 'success');
      } else {
        showToast(t.ossFile.readFailed || '无法读取文件', 'error');
      }
    } catch (error) {
      console.error('Failed to open OSS file:', error);
      showToast(t.ossFile.readFailed || '无法读取文件', 'error');
    }
  };

  const handleUploadClick = () => {
    setShowUploadModal(true);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Check file type
      if (!file.name.toLowerCase().endsWith('.md') && !file.name.toLowerCase().endsWith('.markdown')) {
        showToast(t.ossFile.fileSupported || '仅支持 .md 和.markdown 格式', 'error');
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    try {
      const result = await uploadMarkdownToOss(selectedFile);
      if (result.success) {
        await loadOssFiles();
        setShowUploadModal(false);
        setSelectedFile(null);
        showToast(t.ossFile.uploadSuccess || '文件上传成功', 'success');
        // Auto open the uploaded file
        const uploadedFileInfo = ossFiles.find(f => f.file_path === result.file_path);
        if (uploadedFileInfo && onFileOpen) {
          handleFileClick(uploadedFileInfo);
        }
      } else {
        showToast(t.ossFile.uploadFailed || '上传失败', 'error');
      }
    } catch (error) {
      console.error('Upload failed:', error);
      showToast(t.ossFile.uploadFailed || '上传失败', 'error');
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('zh-CN');
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50">
        <h3 className="text-sm font-medium text-white flex items-center gap-2">
          <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          {t.ossFile?.title || 'OSS 文件'}
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={handleUploadClick}
            disabled={ossFilesLoading || uploading}
            className="p-1.5 text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title={t.ossFile?.upload || '上传文件'}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </button>
          <button
            onClick={handleRefresh}
            disabled={ossFilesLoading || uploading}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title={t.ossFile?.refresh || '刷新列表'}
          >
            <svg className={`w-4 h-4 ${ossFilesLoading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* File List */}
      <div className="flex-1 overflow-y-auto">
        {ossFilesLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-cyan-500"></div>
          </div>
        ) : ossFiles.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <svg className="w-12 h-12 text-slate-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-slate-400 text-sm mb-2">{t.ossFile?.empty || '暂无 OSS 文件'}</p>
            <p className="text-slate-500 text-xs">{t.ossFile?.emptyDesc || '点击上传按钮上传 Markdown 文件'}</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-700/50">
            {ossFiles.map((file) => (
              <div
                key={file.file_path}
                onClick={() => handleFileClick(file)}
                className="px-4 py-3 hover:bg-slate-700/30 cursor-pointer transition-colors group"
              >
                <div className="flex items-center gap-3">
                  {/* File Icon */}
                  <div className="flex-shrink-0">
                    <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>

                  {/* File Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-white font-medium truncate">{file.filename}</span>
                      <span className="text-xs text-slate-500 flex-shrink-0">
                        {formatFileSize(file.size)}
                      </span>
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {formatDate(file.last_modified)}
                    </div>
                  </div>

                  {/* Open Icon (shown on hover) */}
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                    <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-xl p-6 w-full max-w-md border border-slate-700 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">{t.ossFile?.uploadTitle || '上传 Markdown 文件'}</h3>
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFile(null);
                }}
                className="p-1 text-slate-400 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                {t.ossFile?.selectFile || '选择文件'}
              </label>
              <input
                type="file"
                accept=".md,.markdown"
                onChange={handleFileSelect}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white text-sm file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-cyan-600 file:text-white hover:file:bg-cyan-500 cursor-pointer"
              />
              <p className="text-xs text-slate-500 mt-1">
                {t.ossFile?.fileSupported || '支持 .md 和.markdown 格式'}
              </p>
            </div>

            {selectedFile && (
              <div className="mb-4 p-3 bg-slate-900 rounded-lg border border-slate-700">
                <p className="text-sm text-white truncate">{selectedFile.name}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFile(null);
                }}
                className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
              >
                {t.common?.cancel || '取消'}
              </button>
              <button
                onClick={handleUpload}
                disabled={!selectedFile || uploading}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploading ? (t.ossFile?.uploading || '上传中...') : (t.ossFile?.upload || '上传')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
