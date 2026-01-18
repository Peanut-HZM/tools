import { useState, useEffect } from 'react';
import { listAllTools, updateToolStatus, Tool } from '../../api/adminApi';
import { useToast } from '../../hooks/useToast';
import Toast from '../MarkdownEditor/Toast/Toast';

export default function ToolManagement() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast, showToast } = useToast();

  const fetchTools = async () => {
    try {
      const data = await listAllTools();
      setTools(data);
    } catch (error) {
      showToast('获取工具列表失败', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTools();
  }, []);

  const handleStatusChange = async (toolId: string, currentStatus: string) => {
    const newStatus = currentStatus === 'online' ? 'offline' : 'online';
    try {
      await updateToolStatus(toolId, newStatus);
      setTools(tools.map(t => t.id === toolId ? { ...t, status: newStatus } : t));
      showToast(`工具已${newStatus === 'online' ? '上线' : '下线'}`, 'success');
    } catch (error) {
      showToast('状态更新失败', 'error');
    }
  };

  if (loading) return <div className="text-white">加载中...</div>;

  return (
    <div>
      <h2 className="text-2xl font-bold text-white mb-6">工具管理</h2>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left text-slate-300">
          <thead className="bg-slate-700 text-slate-100 uppercase text-xs">
            <tr>
              <th className="px-6 py-3">工具名称</th>
              <th className="px-6 py-3">分类</th>
              <th className="px-6 py-3">状态</th>
              <th className="px-6 py-3">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {tools.map((tool) => (
              <tr key={tool.id} className="hover:bg-slate-700/50">
                <td className="px-6 py-4 flex items-center">
                  <i className={`fa-solid ${tool.icon} w-8 h-8 flex items-center justify-center rounded-lg ${tool.iconColor} text-white mr-3`}></i>
                  <div>
                    <div className="font-medium text-white">{tool.title}</div>
                    <div className="text-xs text-slate-500">{tool.id}</div>
                  </div>
                </td>
                <td className="px-6 py-4">{tool.category}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    tool.status === 'online' 
                      ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                      : 'bg-slate-600 text-slate-400 border border-slate-500'
                  }`}>
                    {tool.status === 'online' ? '已上线' : '已下线'}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <button
                    onClick={() => handleStatusChange(tool.id, tool.status)}
                    className={`text-sm font-medium transition-colors ${
                      tool.status === 'online'
                        ? 'text-red-400 hover:text-red-300'
                        : 'text-green-400 hover:text-green-300'
                    }`}
                  >
                    {tool.status === 'online' ? '下线' : '上线'}
                  </button>
                </td>
              </tr>
            ))}
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
