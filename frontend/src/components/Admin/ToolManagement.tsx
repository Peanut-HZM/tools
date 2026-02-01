import { useState, useEffect } from 'react';
import { listAllTools, updateToolStatus, Tool, listCategories, createCategory, updateCategory, deleteCategory, ToolCategory } from '../../api/adminApi';
import { useToast } from '../../hooks/useToast';
import { ToastContainer } from '../MarkdownEditor/Toast/Toast';

export default function ToolManagement() {
  const [activeTab, setActiveTab] = useState<'tools' | 'categories'>('tools');
  const [tools, setTools] = useState<Tool[]>([]);
  const [categories, setCategories] = useState<ToolCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const { toasts, removeToast, success, error } = useToast();

  // Category Form State
  const [isEditingCategory, setIsEditingCategory] = useState(false);
  const [categoryForm, setCategoryForm] = useState<Partial<ToolCategory>>({
    name: '',
    description: '',
    icon: '',
    sort_order: 0
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [toolsData, categoriesData] = await Promise.all([
        listAllTools(),
        listCategories()
      ]);
      setTools(toolsData);
      setCategories(categoriesData);
    } catch (e) {
      error('获取数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleStatusChange = async (toolId: string, currentStatus: string) => {
    const newStatus = currentStatus === 'online' ? 'offline' : 'online';
    try {
      await updateToolStatus(toolId, newStatus);
      setTools(tools.map(t => t.id === toolId ? { ...t, status: newStatus } : t));
      success(`工具已${newStatus === 'online' ? '上线' : '下线'}`);
    } catch (e) {
      error('状态更新失败');
    }
  };

  const handleCategorySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isEditingCategory && categoryForm.id) {
        await updateCategory(categoryForm.id, categoryForm);
        success('分类更新成功');
      } else {
        await createCategory(categoryForm);
        success('分类创建成功');
      }
      setCategoryForm({ name: '', description: '', icon: '', sort_order: 0 });
      setIsEditingCategory(false);
      // Refresh categories
      const cats = await listCategories();
      setCategories(cats);
    } catch (e) {
      error(isEditingCategory ? '分类更新失败' : '分类创建失败');
    }
  };

  const handleEditCategory = (category: ToolCategory) => {
    setCategoryForm(category);
    setIsEditingCategory(true);
  };

  const handleDeleteCategory = async (id: string) => {
    if (!confirm('确定要删除此分类吗？')) return;
    try {
      await deleteCategory(id);
      success('分类删除成功');
      setCategories(categories.filter(c => c.id !== id));
    } catch (e) {
      error('分类删除失败');
    }
  };

  const handleCancelCategoryEdit = () => {
    setCategoryForm({ name: '', description: '', icon: '', sort_order: 0 });
    setIsEditingCategory(false);
  };

  if (loading) return <div className="text-white">加载中...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">后台管理</h2>
        <div className="flex space-x-2">
          <button
            onClick={() => setActiveTab('tools')}
            className={`px-4 py-2 rounded-md transition-colors ${
              activeTab === 'tools'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            工具管理
          </button>
          <button
            onClick={() => setActiveTab('categories')}
            className={`px-4 py-2 rounded-md transition-colors ${
              activeTab === 'categories'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            分类管理
          </button>
        </div>
      </div>
      
      {activeTab === 'tools' ? (
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
      ) : (
        <div>
          <div className="bg-slate-800 p-6 rounded-lg mb-8">
            <h3 className="text-xl font-semibold text-white mb-4">
              {isEditingCategory ? '编辑分类' : '新建分类'}
            </h3>
            <form onSubmit={handleCategorySubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">分类名称</label>
                  <input
                    type="text"
                    value={categoryForm.name}
                    onChange={(e) => setCategoryForm({...categoryForm, name: e.target.value})}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">排序 (越小越前)</label>
                  <input
                    type="number"
                    value={categoryForm.sort_order}
                    onChange={(e) => setCategoryForm({...categoryForm, sort_order: parseInt(e.target.value) || 0})}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">描述</label>
                  <input
                    type="text"
                    value={categoryForm.description || ''}
                    onChange={(e) => setCategoryForm({...categoryForm, description: e.target.value})}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">图标 (FontAwesome)</label>
                  <input
                    type="text"
                    value={categoryForm.icon || ''}
                    onChange={(e) => setCategoryForm({...categoryForm, icon: e.target.value})}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                    placeholder="fa-folder"
                  />
                </div>
              </div>
              <div className="flex space-x-3">
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                >
                  {isEditingCategory ? '更新' : '创建'}
                </button>
                {isEditingCategory && (
                  <button
                    type="button"
                    onClick={handleCancelCategoryEdit}
                    className="px-4 py-2 bg-slate-600 text-white rounded hover:bg-slate-500 transition-colors"
                  >
                    取消
                  </button>
                )}
              </div>
            </form>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-slate-300">
              <thead className="bg-slate-700 text-slate-100 uppercase text-xs">
                <tr>
                  <th className="px-6 py-3">分类名称</th>
                  <th className="px-6 py-3">排序</th>
                  <th className="px-6 py-3">描述</th>
                  <th className="px-6 py-3">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {categories.map((cat) => (
                  <tr key={cat.id} className="hover:bg-slate-700/50">
                    <td className="px-6 py-4 flex items-center">
                       {cat.icon && <i className={`fa-solid ${cat.icon} mr-2 text-slate-400`}></i>}
                       <span className="font-medium text-white">{cat.name}</span>
                    </td>
                    <td className="px-6 py-4">{cat.sort_order}</td>
                    <td className="px-6 py-4 text-sm text-slate-400">{cat.description || '-'}</td>
                    <td className="px-6 py-4 flex space-x-3">
                      <button
                        onClick={() => handleEditCategory(cat)}
                        className="text-blue-400 hover:text-blue-300 text-sm font-medium"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDeleteCategory(cat.id)}
                        className="text-red-400 hover:text-red-300 text-sm font-medium"
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
