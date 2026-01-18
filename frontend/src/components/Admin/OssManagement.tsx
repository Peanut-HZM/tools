import { useState, useEffect } from 'react';
import { listOssFiles, deleteOssFile, OssFile } from '../../api/adminApi';
import { useToast } from '../../hooks/useToast';
import Toast from '../MarkdownEditor/Toast/Toast';
import { useAuth } from '../../stores/authStore';

export default function OssManagement() {
  const [files, setFiles] = useState<OssFile[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast, showToast } = useToast();
  const { user } = useAuth();
  
  // Filter state
  const [showMyFilesOnly, setShowMyFilesOnly] = useState(false);

  const fetchFiles = async () => {
    try {
      const data = await listOssFiles();
      setFiles(data);
    } catch (error) {
      showToast('获取文件列表失败', 'error');
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
      showToast('文件删除成功', 'success');
    } catch (error) {
      showToast('文件删除失败', 'error');
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const isImage = (type: string) => type?.startsWith('image/');
  
  const filteredFiles = showMyFilesOnly && user 
    ? files.filter(f => f.uploaded_by === user.user_id)
    : files;

  if (loading) return <div className="text-white">加载中...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">OSS 文件管理</h2>
        
        <div className="flex items-center space-x-2 bg-slate-700 px-3 py-1.5 rounded-lg border border-slate-600">
          <input
            type="checkbox"
            id="showMyFiles"
            checked={showMyFilesOnly}
            onChange={(e) => setShowMyFilesOnly(e.target.checked)}
            className="w-4 h-4 text-cyan-500 rounded focus:ring-cyan-500 bg-slate-800 border-slate-500"
          />
          <label htmlFor="showMyFiles" className="text-sm text-slate-300 cursor-pointer select-none">
            只看我的文件
          </label>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left text-slate-300">
          <thead className="bg-slate-700 text-slate-100 uppercase text-xs">
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
          <tbody className="divide-y divide-slate-700">
            {filteredFiles.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-4 text-center text-slate-500">
                  暂无文件
                </td>
              </tr>
            ) : (
              filteredFiles.map((file) => (
                <tr key={file.id} className="hover:bg-slate-700/50">
                  <td className="px-6 py-4">
                    {isImage(file.type) ? (
                      <div className="w-12 h-12 bg-slate-800 rounded overflow-hidden">
                        <img 
                          src={file.url} 
                          alt={file.name} 
                          className="w-full h-full object-cover cursor-pointer hover:opacity-80"
                          onClick={() => window.open(file.url, '_blank')} 
                        />
                      </div>
                    ) : (
                      <div className="w-12 h-12 bg-slate-800 rounded flex items-center justify-center text-slate-500">
                        <i className="fa-solid fa-file"></i>
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 max-w-xs truncate" title={file.name}>
                    <a href={file.url} target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline">
                      {file.name}
                    </a>
                    <div className="text-xs text-slate-500 truncate">{file.path}</div>
                  </td>
                  <td className="px-6 py-4 text-sm">{file.type || 'Unknown'}</td>
                  <td className="px-6 py-4 text-sm">{formatSize(file.size)}</td>
                  <td className="px-6 py-4 text-sm">{file.uploaded_by}</td>
                  <td className="px-6 py-4 text-sm">
                    {new Date(file.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4">
                    <button
                      onClick={() => handleDelete(file.path)}
                      className="text-red-400 hover:text-red-300 transition-colors text-sm"
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => {}}
        />
      )}
    </div>
  );
}
