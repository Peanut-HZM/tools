import { useState, useEffect, useCallback } from 'react';
import { listToolsPaginated, updateToolStatus, updateTool, uploadToolIcon, deleteToolIcon, deleteTool, batchUpdateToolStatus, batchDeleteTools, Tool, listCategories, createCategory, updateCategory, deleteCategory, ToolCategory, ToolsListParams } from '../../api/adminApi';
import { useToast } from '../../hooks/useToast';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
export default function ToolManagement() {
  const [activeTab, setActiveTab] = useState<'tools' | 'categories'>('tools');
  const [tools, setTools] = useState<Tool[]>([]);
  const [categories, setCategories] = useState<ToolCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const { success, error  } = useToast();

  // Tool Edit Modal State
  const [editingTool, setEditingTool] = useState<Tool | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [toolForm, setToolForm] = useState<Partial<Tool>>({});
  const [iconFile, setIconFile] = useState<File | null>(null);
  const [iconPreview, setIconPreview] = useState<string | null>(null);
  const [uploadingIcon, setUploadingIcon] = useState(false);
  const [saving, setSaving] = useState(false);

  // Pagination & Search State
  const [toolPage, setToolPage] = useState(1);
  const [toolPageSize, setToolPageSize] = useState(20);
  const [toolTotal, setToolTotal] = useState(0);
  const [toolTotalPages, setToolTotalPages] = useState(0);
  const [toolSearch, setToolSearch] = useState('');
  const [toolStatusFilter, setToolStatusFilter] = useState<string>('');
  const [toolCategoryFilter, setToolCategoryFilter] = useState<string>('');
  const [toolSortBy, setToolSortBy] = useState('usage_count');
  const [toolSortOrder, setToolSortOrder] = useState<'asc' | 'desc'>('desc');
  const [showPcFilter, setShowPcFilter] = useState<string>('all');
  const [showMobileFilter, setShowMobileFilter] = useState<string>('all');
  const [requireLoginFilter, setRequireLoginFilter] = useState<string>('all');

  // 批量选择状态
  const [selectedToolIds, setSelectedToolIds] = useState<Set<string>>(new Set());

  // Category Form State
  const [isEditingCategory, setIsEditingCategory] = useState(false);
  const [categoryForm, setCategoryForm] = useState<Partial<ToolCategory>>({
    name: '',
    description: '',
    icon: '',
    sort_order: 0
  });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params: ToolsListParams = {
        page: toolPage,
        page_size: toolPageSize,
        search: toolSearch || undefined,
        status: toolStatusFilter || undefined,
        category: toolCategoryFilter || undefined,
        sort_by: toolSortBy,
        sort_order: toolSortOrder,
        show_pc: showPcFilter === 'all' ? undefined : showPcFilter === 'true',
        show_mobile: showMobileFilter === 'all' ? undefined : showMobileFilter === 'true',
        require_login: requireLoginFilter === 'all' ? undefined : requireLoginFilter === 'true',
      };

      const [toolsData, categoriesData] = await Promise.all([
        listToolsPaginated(params),
        listCategories()
      ]);

      setTools(toolsData.tools);
      setToolTotal(toolsData.total);
      setToolTotalPages(toolsData.total_pages);
      setCategories(categoriesData);
    } catch (e) {
      error('获取数据失败');
    } finally {
      setLoading(false);
    }
  }, [toolPage, toolPageSize, toolSearch, toolStatusFilter, toolCategoryFilter, toolSortBy, toolSortOrder, showPcFilter, showMobileFilter, requireLoginFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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

  const handlePcToggle = async (toolId: string, currentValue: boolean) => {
    try {
      await updateTool(toolId, { show_pc: !currentValue });
      setTools(tools.map(t => t.id === toolId ? { ...t, show_pc: !currentValue } : t));
      success(`PC 展示已${!currentValue ? '开启' : '关闭'}`);
    } catch (e) {
      error('更新失败');
    }
  };

  const handleMobileToggle = async (toolId: string, currentValue: boolean) => {
    try {
      await updateTool(toolId, { show_mobile: !currentValue });
      setTools(tools.map(t => t.id === toolId ? { ...t, show_mobile: !currentValue } : t));
      success(`移动展示已${!currentValue ? '开启' : '关闭'}`);
    } catch (e) {
      error('更新失败');
    }
  };

  const handleLoginToggle = async (toolId: string, currentValue: boolean) => {
    try {
      await updateTool(toolId, { require_login: !currentValue });
      setTools(tools.map(t => t.id === toolId ? { ...t, require_login: !currentValue } : t));
      success(`登录要求已${!currentValue ? '开启' : '关闭'}`);
    } catch (e) {
      error('更新失败');
    }
  };

  // Tool Edit Modal Handlers
  const handleEditTool = (tool: Tool) => {
    setEditingTool(tool);
    setToolForm({ ...tool });
    setIconFile(null);
    setIconPreview(tool.custom_icon_url || null);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingTool(null);
    setToolForm({});
    setIconFile(null);
    setIconPreview(null);
  };

  const handleIconFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      error('图标文件大小不能超过 2MB');
      return;
    }

    setIconFile(file);
    const reader = new FileReader();
    reader.onload = (ev) => setIconPreview(ev.target?.result as string);
    reader.readAsDataURL(file);
  };

  const handleSaveTool = async () => {
    if (!editingTool) return;

    if (!toolForm.title?.trim()) {
      error('工具名称不能为空');
      return;
    }

    setSaving(true);
    try {
      const updateData: Partial<Tool> = {};
      const fields: (keyof Tool)[] = ['title', 'description', 'icon', 'iconColor', 'category', 'status', 'show_pc', 'show_mobile'];
      for (const field of fields) {
        if (toolForm[field] !== undefined && toolForm[field] !== editingTool[field]) {
          (updateData as any)[field] = toolForm[field];
        }
      }

      if (Object.keys(updateData).length > 0) {
        await updateTool(editingTool.id, updateData);
      }

      if (iconFile) {
        await uploadToolIcon(editingTool.id, iconFile);
      }

      success('工具信息已更新');
      handleCloseModal();
      await fetchData();
    } catch (e: any) {
      error(e.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteIcon = async () => {
    if (!editingTool) return;
    try {
      await deleteToolIcon(editingTool.id);
      success('图标已删除');
      setIconPreview(null);
      setIconFile(null);
      await fetchData();
    } catch (e) {
      error('删除图标失败');
    }
  };


  // 行删除
  const handleDeleteTool = async (toolId: string) => {
    if (!confirm('确定要删除此工具吗？删除后不可恢复。')) return;
    try {
      await deleteTool(toolId);
      success('工具已删除');
      await fetchData();
    } catch (e) {
      error('删除失败');
    }
  };

  // 行启用/停用
  const handleRowStatusChange = async (toolId: string, currentStatus: string) => {
    const newStatus = currentStatus === 'online' ? 'offline' : 'online';
    try {
      await updateToolStatus(toolId, newStatus);
      setTools(tools.map(t => t.id === toolId ? { ...t, status: newStatus } : t));
      success(`工具已${newStatus === 'online' ? '启用' : '停用'}`);
    } catch (e) {
      error('状态更新失败');
    }
  };

  // 批量操作
  const handleBatchEnable = async () => {
    const ids = Array.from(selectedToolIds);
    if (ids.length === 0) return;
    try {
      const result = await batchUpdateToolStatus(ids, 'online');
      success(`已启用 ${result.success_count} 个工具`);
      setSelectedToolIds(new Set());
      await fetchData();
    } catch (e) {
      error('批量启用失败');
    }
  };

  const handleBatchDisable = async () => {
    const ids = Array.from(selectedToolIds);
    if (ids.length === 0) return;
    try {
      const result = await batchUpdateToolStatus(ids, 'offline');
      success(`已停用 ${result.success_count} 个工具`);
      setSelectedToolIds(new Set());
      await fetchData();
    } catch (e) {
      error('批量停用失败');
    }
  };

  const handleBatchDelete = async () => {
    const ids = Array.from(selectedToolIds);
    if (ids.length === 0) return;
    if (!confirm(`确定要删除选中的 ${ids.length} 个工具吗？删除后不可恢复。`)) return;
    try {
      const result = await batchDeleteTools(ids);
      success(`已删除 ${result.success_count} 个工具`);
      setSelectedToolIds(new Set());
      await fetchData();
    } catch (e) {
      error('批量删除失败');
    }
  };

  // 选择相关
  const toggleToolSelection = (toolId: string) => {
    setSelectedToolIds(prev => {
      const next = new Set(prev);
      if (next.has(toolId)) {
        next.delete(toolId);
      } else {
        next.add(toolId);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedToolIds.size === tools.length) {
      setSelectedToolIds(new Set());
    } else {
      setSelectedToolIds(new Set(tools.map(t => t.id)));
    }
  };

  const clearSelection = () => setSelectedToolIds(new Set());

  const handleCategorySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isEditingCategory && categoryForm.id) {
        await updateCategory(categoryForm.id, categoryForm, false);
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
    } catch (e: any) {
      const msg = e?.message || '';
      if (msg.startsWith('409:') && isEditingCategory && categoryForm.id) {
        const confirmed = window.confirm('该分类下有工具正在使用，是否一并更新工具的 category 字段？');
        if (confirmed) {
          try {
            await updateCategory(categoryForm.id, categoryForm, true);
            success('分类已更新（工具的 category 已级联）');
            setCategoryForm({ name: '', description: '', icon: '', sort_order: 0 });
            setIsEditingCategory(false);
            const cats = await listCategories();
            setCategories(cats);
          } catch (e2: any) {
            error('级联更新失败：' + (e2?.message || ''));
          }
        }
      } else {
        error(isEditingCategory ? '分类更新失败' : '分类创建失败');
      }
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
    } catch (e: any) {
      const msg = e?.message || '';
      if (msg.startsWith('409:')) {
        error('该分类下仍有工具，请先迁移后再删除');
      } else {
        error('分类删除失败');
      }
    }
  };

  const handleCancelCategoryEdit = () => {
    setCategoryForm({ name: '', description: '', icon: '', sort_order: 0 });
    setIsEditingCategory(false);
  };

  // 重置所有筛选条件
  const handleResetFilters = () => {
    setToolSearch('');
    setToolStatusFilter('');
    setToolCategoryFilter('');
    setToolSortBy('usage_count');
    setToolSortOrder('desc');
    setShowPcFilter('all');
    setShowMobileFilter('all');
    setRequireLoginFilter('all');
    setToolPage(1);
  };

  // 检查是否有激活的筛选条件
  const hasActiveFilters = toolSearch || toolStatusFilter || toolCategoryFilter ||
    showPcFilter !== 'all' || showMobileFilter !== 'all' || requireLoginFilter !== 'all';

  if (loading) return <div className="text-ink-inverse">加载中...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-ink-inverse">后台管理</h2>
        <div className="flex space-x-2">
          <Button
            variant={activeTab === 'tools' ? 'default' : 'secondary'}
            onClick={() => setActiveTab('tools')}
          >
            工具管理
          </Button>
          <Button
            variant={activeTab === 'categories' ? 'default' : 'secondary'}
            onClick={() => setActiveTab('categories')}
          >
            分类管理
          </Button>
        </div>
      </div>
      
      {activeTab === 'tools' ? (
        <div>
          {/* 激活筛选提示 */}
          {hasActiveFilters && (
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              <span className="text-xs text-ink-faint">已筛选:</span>
              {toolSearch && (
                <Badge variant="default">
                  搜索: {toolSearch}
                </Badge>
              )}
              {toolStatusFilter && (
                <Badge variant="default">
                  状态: {toolStatusFilter === 'online' ? '在线' : '离线'}
                </Badge>
              )}
              {toolCategoryFilter && (
                <Badge variant="default">
                  分类: {toolCategoryFilter}
                </Badge>
              )}
              {showPcFilter !== 'all' && (
                <Badge variant="default">
                  PC: {showPcFilter === 'true' ? '展示' : '隐藏'}
                </Badge>
              )}
              {showMobileFilter !== 'all' && (
                <Badge variant="default">
                  移动: {showMobileFilter === 'true' ? '展示' : '隐藏'}
                </Badge>
              )}
              {requireLoginFilter !== 'all' && (
                <Badge variant="default">
                  登录: {requireLoginFilter === 'true' ? '需登录' : '免登录'}
                </Badge>
              )}
              <button
                onClick={handleResetFilters}
                className="text-xs text-danger hover:text-red-300 ml-2 transition-colors cursor-pointer"
              >
                <i className="fas fa-times-circle mr-1"></i>重置
              </button>
            </div>
          )}

          {/* 批量操作栏 */}
          {selectedToolIds.size > 0 && (
            <div className="bg-accent/10 border border-blue-500/30 rounded-xl px-4 py-3 mb-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-sm text-blue-300">
                  已选择 <strong className="text-blue-200">{selectedToolIds.size}</strong> 个工具
                </span>
                <button onClick={clearSelection} className="text-xs text-ink-muted hover:text-ink-muted cursor-pointer">
                  取消选择
                </button>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleBatchEnable}
                  className="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-ink-inverse text-sm rounded-md transition-colors cursor-pointer"
                >
                  <i className="fas fa-check-circle mr-1"></i>批量启用
                </button>
                <button
                  onClick={handleBatchDisable}
                  className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-ink-inverse text-sm rounded-md transition-colors cursor-pointer"
                >
                  <i className="fas fa-pause-circle mr-1"></i>批量停用
                </button>
                <button
                  onClick={handleBatchDelete}
                  className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-ink-inverse text-sm rounded-md transition-colors cursor-pointer"
                >
                  <i className="fas fa-trash-alt mr-1"></i>批量删除
                </button>
              </div>
            </div>
          )}

          {/* 筛选工具栏 */}
          <div className="bg-surface-1/50 p-3 rounded-xl mb-4 border border-border/50">
            <div className="flex flex-wrap gap-2 items-center">
              {/* 搜索框 */}
              <div className={`flex items-center bg-surface-1 border rounded-lg px-3 py-2 gap-2 min-w-[200px] flex-1 max-w-[320px] transition-colors duration-200 ${toolSearch ? 'border-blue-500' : 'border-border hover:border-border'}`}>
                <i className="fas fa-search text-ink-faint text-xs"></i>
                <input
                  type="text"
                  placeholder="搜索名称/描述..."
                  value={toolSearch}
                  onChange={(e) => { setToolSearch(e.target.value); setToolPage(1); }}
                  className="bg-transparent text-ink-inverse text-sm outline-none w-full placeholder-slate-500"
                />
              </div>

              {/* 状态筛选 */}
              <div className={`flex items-center bg-surface-1 border rounded-lg px-3 py-2 gap-2 transition-colors duration-200 cursor-pointer ${toolStatusFilter ? 'border-blue-500' : 'border-border hover:border-border'}`}>
                <i className="fas fa-circle-dot text-ink-faint text-xs"></i>
                <select
                  value={toolStatusFilter}
                  onChange={(e) => { setToolStatusFilter(e.target.value); setToolPage(1); }}
                  className="bg-transparent text-ink-inverse text-sm outline-none appearance-none pr-2 cursor-pointer"
                >
                  <option value="" className="bg-surface-1">全部状态</option>
                  <option value="online" className="bg-surface-1">在线</option>
                  <option value="offline" className="bg-surface-1">离线</option>
                </select>
              </div>

              {/* 分类筛选 */}
              <div className={`flex items-center bg-surface-1 border rounded-lg px-3 py-2 gap-2 transition-colors duration-200 cursor-pointer ${toolCategoryFilter ? 'border-blue-500' : 'border-border hover:border-border'}`}>
                <i className="fas fa-folder text-ink-faint text-xs"></i>
                <select
                  value={toolCategoryFilter}
                  onChange={(e) => { setToolCategoryFilter(e.target.value); setToolPage(1); }}
                  className="bg-transparent text-ink-inverse text-sm outline-none appearance-none pr-2 cursor-pointer"
                >
                  <option value="" className="bg-surface-1">全部分类</option>
                  {categories.map(cat => (
                    <option key={cat.id} value={cat.name} className="bg-surface-1">{cat.name}</option>
                  ))}
                </select>
              </div>

              {/* 排序 */}
              <div className={`flex items-center bg-surface-1 border rounded-lg px-3 py-2 gap-2 transition-colors duration-200 cursor-pointer ${(toolSortBy !== 'usage_count' || toolSortOrder !== 'desc') ? 'border-blue-500' : 'border-border hover:border-border'}`}>
                <i className="fas fa-arrow-down-a-z text-ink-faint text-xs"></i>
                <select
                  value={`${toolSortBy}-${toolSortOrder}`}
                  onChange={(e) => { const [by, order] = e.target.value.split('-'); setToolSortBy(by); setToolSortOrder(order as 'asc'|'desc'); }}
                  className="bg-transparent text-ink-inverse text-sm outline-none appearance-none pr-2 cursor-pointer"
                >
                  <option value="title-asc" className="bg-surface-1">名称 A-Z</option>
                  <option value="title-desc" className="bg-surface-1">名称 Z-A</option>
                  <option value="rating-desc" className="bg-surface-1">评分 高→低</option>
                  <option value="rating-asc" className="bg-surface-1">评分 低→高</option>
                  <option value="usage_count-desc" className="bg-surface-1">使用次数 多→少</option>
                  <option value="usage_count-asc" className="bg-surface-1">使用次数 少→多</option>
                  <option value="created_at-desc" className="bg-surface-1">最新创建</option>
                  <option value="created_at-asc" className="bg-surface-1">最早创建</option>
                </select>
              </div>

              {/* PC 展示筛选 */}
              <div className={`flex items-center bg-surface-1 border rounded-lg px-3 py-2 gap-2 transition-colors duration-200 cursor-pointer ${showPcFilter !== 'all' ? 'border-blue-500' : 'border-border hover:border-border'}`}>
                <i className="fas fa-desktop text-ink-faint text-xs"></i>
                <span className="text-xs text-ink-muted">PC</span>
                <select
                  value={showPcFilter}
                  onChange={(e) => { setShowPcFilter(e.target.value); setToolPage(1); }}
                  className="bg-transparent text-ink-inverse text-sm outline-none appearance-none pr-2 cursor-pointer w-[60px]"
                >
                  <option value="all" className="bg-surface-1">全部</option>
                  <option value="true" className="bg-surface-1">展示</option>
                  <option value="false" className="bg-surface-1">隐藏</option>
                </select>
              </div>

              {/* 移动端展示筛选 */}
              <div className={`flex items-center bg-surface-1 border rounded-lg px-3 py-2 gap-2 transition-colors duration-200 cursor-pointer ${showMobileFilter !== 'all' ? 'border-blue-500' : 'border-border hover:border-border'}`}>
                <i className="fas fa-mobile text-ink-faint text-xs"></i>
                <span className="text-xs text-ink-muted">移动</span>
                <select
                  value={showMobileFilter}
                  onChange={(e) => { setShowMobileFilter(e.target.value); setToolPage(1); }}
                  className="bg-transparent text-ink-inverse text-sm outline-none appearance-none pr-2 cursor-pointer w-[60px]"
                >
                  <option value="all" className="bg-surface-1">全部</option>
                  <option value="true" className="bg-surface-1">展示</option>
                  <option value="false" className="bg-surface-1">隐藏</option>
                </select>
              </div>

              {/* 登录要求筛选 */}
              <div className={`flex items-center bg-surface-1 border rounded-lg px-3 py-2 gap-2 transition-colors duration-200 cursor-pointer ${requireLoginFilter !== 'all' ? 'border-blue-500' : 'border-border hover:border-border'}`}>
                <i className="fas fa-lock text-ink-faint text-xs"></i>
                <span className="text-xs text-ink-muted">登录</span>
                <select
                  value={requireLoginFilter}
                  onChange={(e) => { setRequireLoginFilter(e.target.value); setToolPage(1); }}
                  className="bg-transparent text-ink-inverse text-sm outline-none appearance-none pr-2 cursor-pointer w-[60px]"
                >
                  <option value="all" className="bg-surface-1">全部</option>
                  <option value="true" className="bg-surface-1">需登录</option>
                  <option value="false" className="bg-surface-1">免登录</option>
                </select>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
          <table className="w-full text-left text-ink-muted">
            <thead className="bg-surface-2 text-ink uppercase text-xs">
              <tr>
                <th className="px-6 py-3 w-[40px]">
                  <input
                    type="checkbox"
                    checked={tools.length > 0 && selectedToolIds.size === tools.length}
                    onChange={toggleSelectAll}
                    className="sr-only peer"
                  />
                  <label className="flex items-center justify-center cursor-pointer">
                    <div className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
                      tools.length > 0 && selectedToolIds.size === tools.length
                        ? 'bg-accent border-blue-500'
                        : 'border-border hover:border-border'
                    }`}>
                      {tools.length > 0 && selectedToolIds.size === tools.length && (
                        <i className="fas fa-check text-ink-inverse text-[10px]"></i>
                      )}
                    </div>
                  </label>
                </th>
                <th className="px-6 py-3">工具名称</th>
                <th className="px-6 py-3">分类</th>
                <th className="px-6 py-3 text-center w-[100px]">使用次数</th>
                <th className="px-6 py-3 text-center w-[100px]">上线状态</th>
                <th className="px-6 py-3 text-center w-[100px]">PC 展示</th>
                <th className="px-6 py-3 text-center w-[100px]">移动展示</th>
                <th className="px-6 py-3 text-center w-[100px]">登录要求</th>
                <th className="px-6 py-3 w-[80px]">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {tools.map((tool) => (
                <tr key={tool.id} className={`hover:bg-surface-2/50 ${selectedToolIds.has(tool.id) ? 'bg-accent/5' : ''}`}>
                  <td className="px-6 py-4">
                    <input
                      type="checkbox"
                      checked={selectedToolIds.has(tool.id)}
                      onChange={() => toggleToolSelection(tool.id)}
                      className="sr-only peer"
                    />
                    <label className="flex items-center justify-center cursor-pointer">
                      <div className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
                        selectedToolIds.has(tool.id)
                          ? 'bg-accent border-blue-500'
                          : 'border-border hover:border-border'
                      }`}>
                        {selectedToolIds.has(tool.id) && (
                          <i className="fas fa-check text-ink-inverse text-[10px]"></i>
                        )}
                      </div>
                    </label>
                  </td>
                  <td className="px-6 py-4 flex items-center">
                    {tool.custom_icon_url ? (
                      <img src={tool.custom_icon_url} alt={tool.title} className="w-8 h-8 rounded object-contain mr-3 bg-surface-3" />
                    ) : (
                      <i className={`fa-solid ${tool.icon} w-8 h-8 flex items-center justify-center rounded-lg ${tool.iconColor} text-ink-inverse mr-3`}></i>
                    )}
                    <div>
                      <div className="font-medium text-ink-inverse">{tool.title}</div>
                      <div className="text-xs text-ink-faint">{tool.id}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4">{tool.category}</td>
                  {/* 使用次数 */}
                  <td className="px-6 py-4 text-center">
                    <Badge variant={
                      parseInt(tool.usageCount) >= 1000
                        ? 'success'
                        : parseInt(tool.usageCount) >= 100
                          ? 'default'
                          : 'secondary'
                    }>
                      {parseInt(tool.usageCount) >= 1000
                        ? (parseInt(tool.usageCount) / 1000).toFixed(1) + 'K'
                        : tool.usageCount}
                    </Badge>
                  </td>
                  {/* 上线状态 */}
                  <td className="px-6 py-4 text-center">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={tool.status === 'online'}
                        onChange={() => handleStatusChange(tool.id, tool.status)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-green-500"></div>
                    </label>
                  </td>

                  {/* PC 展示 */}
                  <td className="px-6 py-4 text-center">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={tool.show_pc !== false}
                        onChange={() => handlePcToggle(tool.id, tool.show_pc !== false)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent"></div>
                    </label>
                  </td>

                  {/* 移动展示 */}
                  <td className="px-6 py-4 text-center">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={tool.show_mobile !== false}
                        onChange={() => handleMobileToggle(tool.id, tool.show_mobile !== false)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-purple-500"></div>
                    </label>
                  </td>

                  {/* 登录要求 */}
                  <td className="px-6 py-4 text-center">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={tool.require_login ?? false}
                        onChange={() => handleLoginToggle(tool.id, tool.require_login ?? false)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-orange-500"></div>
                    </label>
                  </td>

                  {/* 操作 */}
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleEditTool(tool)}
                        className="text-accent-info hover:text-blue-300 text-sm font-medium transition-colors cursor-pointer"
                        title="编辑"
                      >
                        <i className="fas fa-edit"></i>
                      </button>
                      <button
                        onClick={() => handleRowStatusChange(tool.id, tool.status)}
                        className={`text-sm font-medium transition-colors cursor-pointer ${
                          tool.status === 'online'
                            ? 'text-amber-400 hover:text-amber-300'
                            : 'text-green-400 hover:text-green-300'
                        }`}
                        title={tool.status === 'online' ? '停用' : '启用'}
                      >
                        <i className={`fas ${tool.status === 'online' ? 'fa-pause-circle' : 'fa-check-circle'}`}></i>
                      </button>
                      <button
                        onClick={() => handleDeleteTool(tool.id)}
                        className="text-danger hover:text-red-300 text-sm font-medium transition-colors cursor-pointer"
                        title="删除"
                      >
                        <i className="fas fa-trash-alt"></i>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          {/* 分页控件 */}
          {toolTotalPages > 1 && (
            <div className="flex items-center justify-between mt-4 text-sm text-ink-muted">
              <div className="flex items-center gap-3">
                <span>共 {toolTotal} 条记录，第 {toolPage}/{toolTotalPages} 页</span>
                <div className="flex items-center gap-1">
                  <span className="text-xs">每页</span>
                  <select
                    value={toolPageSize}
                    onChange={(e) => { setToolPageSize(Number(e.target.value)); setToolPage(1); }}
                    className="bg-surface-1 border border-border rounded px-2 py-1 text-xs text-ink-inverse focus:outline-none focus:border-blue-500 cursor-pointer"
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                  </select>
                </div>
              </div>
              <div className="flex space-x-1">
                <button
                  onClick={() => setToolPage(1)}
                  disabled={toolPage === 1}
                  className="px-3 py-1 rounded bg-surface-2 disabled:opacity-50 hover:bg-surface-3"
                >
                  首页
                </button>
                <button
                  onClick={() => setToolPage(p => Math.max(1, p - 1))}
                  disabled={toolPage === 1}
                  className="px-3 py-1 rounded bg-surface-2 disabled:opacity-50 hover:bg-surface-3"
                >
                  上一页
                </button>
                {Array.from({ length: Math.min(5, toolTotalPages) }, (_, i) => {
                  let pageNum = Math.max(1, Math.min(toolPage - 2, toolTotalPages - 4));
                  pageNum = i + pageNum;
                  if (pageNum > toolTotalPages) return null;
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setToolPage(pageNum)}
                      className={`px-3 py-1 rounded ${pageNum === toolPage ? 'bg-accent text-white' : 'bg-surface-2 hover:bg-surface-3'}`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
                <button
                  onClick={() => setToolPage(p => Math.min(toolTotalPages, p + 1))}
                  disabled={toolPage >= toolTotalPages}
                  className="px-3 py-1 rounded bg-surface-2 disabled:opacity-50 hover:bg-surface-3"
                >
                  下一页
                </button>
                <button
                  onClick={() => setToolPage(toolTotalPages)}
                  disabled={toolPage >= toolTotalPages}
                  className="px-3 py-1 rounded bg-surface-2 disabled:opacity-50 hover:bg-surface-3"
                >
                  末页
                </button>
              </div>
            </div>
          )}
          {toolTotalPages <= 1 && toolTotal > 0 && (
            <div className="mt-4 text-sm text-ink-muted">共 {toolTotal} 条记录</div>
          )}

        {/* 编辑工具弹窗 */}
        {isModalOpen && editingTool && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={handleCloseModal}>
            <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto mx-4" onClick={(e) => e.stopPropagation()}>
              <CardContent className="p-6">
                <h3 className="text-xl font-semibold text-ink-inverse mb-6">编辑工具：{editingTool.title}</h3>

                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-ink-muted mb-1">工具名称</label>
                    <input
                      type="text"
                      value={toolForm.title || ''}
                      onChange={(e) => setToolForm({...toolForm, title: e.target.value})}
                      className="w-full bg-surface-2 border border-border rounded px-3 py-2 text-ink-inverse focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-ink-muted mb-1">描述</label>
                    <textarea
                      value={toolForm.description || ''}
                      onChange={(e) => setToolForm({...toolForm, description: e.target.value})}
                      className="w-full bg-surface-2 border border-border rounded px-3 py-2 text-ink-inverse focus:outline-none focus:border-blue-500"
                      rows={3}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-ink-muted mb-1">分类</label>
                    <select
                      value={toolForm.category || ''}
                      onChange={(e) => setToolForm({...toolForm, category: e.target.value})}
                      className="w-full bg-surface-2 border border-border rounded px-3 py-2 text-ink-inverse focus:outline-none focus:border-blue-500"
                    >
                      {categories.map(cat => (
                        <option key={cat.id} value={cat.name}>{cat.name}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-ink-muted mb-1">图标颜色</label>
                    <input
                      type="text"
                      value={toolForm.iconColor || ''}
                      onChange={(e) => setToolForm({...toolForm, iconColor: e.target.value})}
                      className="w-full bg-surface-2 border border-border rounded px-3 py-2 text-ink-inverse focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  {/* 图标上传区域 */}
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-ink-muted mb-1">自定义图标</label>
                    <div className="bg-surface-2 border border-border rounded p-4">
                      {iconPreview ? (
                        <div className="flex items-center space-x-4">
                          <img src={iconPreview} alt="图标预览" className="w-16 h-16 rounded object-contain bg-surface-3" />
                          <div className="flex-1">
                            <p className="text-sm text-ink-muted">已上传自定义图标</p>
                            <button
                              onClick={handleDeleteIcon}
                              className="text-xs text-danger hover:text-red-300 mt-1"
                            >
                              删除自定义图标（恢复默认）
                            </button>
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm text-ink-muted mb-2">当前使用默认 FontAwesome 图标</p>
                      )}
                      <div className="mt-3">
                        <label className="inline-block px-4 py-2 bg-accent text-white text-sm rounded cursor-pointer hover:bg-accent-hover">
                          选择文件
                          <input
                            type="file"
                            accept="image/png,image/jpeg,image/gif,image/svg+xml,image/webp"
                            onChange={handleIconFileChange}
                            className="hidden"
                          />
                        </label>
                        <span className="text-xs text-ink-faint ml-2">JPG/PNG/SVG，≤2MB</span>
                      </div>
                    </div>
                  </div>

                  {/* Toggle 开关 */}
                  <div className="col-span-2 grid grid-cols-4 gap-3">
                    <div className="flex items-center justify-between bg-surface-2 rounded p-3">
                      <span className="text-sm text-ink-muted">PC 端展示</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={toolForm.show_pc ?? true}
                          onChange={(e) => setToolForm({...toolForm, show_pc: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accent"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between bg-surface-2 rounded p-3">
                      <span className="text-sm text-ink-muted">移动端展示</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={toolForm.show_mobile ?? true}
                          onChange={(e) => setToolForm({...toolForm, show_mobile: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accent"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between bg-surface-2 rounded p-3">
                      <span className="text-sm text-ink-muted">上线状态</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={toolForm.status === 'online'}
                          onChange={(e) => setToolForm({...toolForm, status: e.target.checked ? 'online' : 'offline'})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between bg-surface-2 rounded p-3">
                      <span className="text-sm text-ink-muted">需要登录</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={toolForm.require_login ?? false}
                          onChange={(e) => setToolForm({...toolForm, require_login: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange-500"></div>
                      </label>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end space-x-3 mt-6 pt-4 border-t border-border">
                  <Button
                    variant="secondary"
                    onClick={handleCloseModal}
                  >
                    取消
                  </Button>
                  <Button
                    onClick={handleSaveTool}
                    disabled={saving}
                  >
                    {saving ? '保存中...' : '保存'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
        </div>
      ) : (
        <div>
          <Card className="p-6 mb-8">
            <CardContent className="p-0">
            <h3 className="text-xl font-semibold text-ink-inverse mb-4">
              {isEditingCategory ? '编辑分类' : '新建分类'}
            </h3>
            <form onSubmit={handleCategorySubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-ink-muted mb-1">分类名称</label>
                  <input
                    type="text"
                    value={categoryForm.name}
                    onChange={(e) => setCategoryForm({...categoryForm, name: e.target.value})}
                    className="w-full bg-surface-2 border border-border rounded px-3 py-2 text-ink-inverse focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink-muted mb-1">排序 (越小越前)</label>
                  <input
                    type="number"
                    value={categoryForm.sort_order}
                    onChange={(e) => setCategoryForm({...categoryForm, sort_order: parseInt(e.target.value) || 0})}
                    className="w-full bg-surface-2 border border-border rounded px-3 py-2 text-ink-inverse focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink-muted mb-1">描述</label>
                  <input
                    type="text"
                    value={categoryForm.description || ''}
                    onChange={(e) => setCategoryForm({...categoryForm, description: e.target.value})}
                    className="w-full bg-surface-2 border border-border rounded px-3 py-2 text-ink-inverse focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink-muted mb-1">图标 (FontAwesome)</label>
                  <input
                    type="text"
                    value={categoryForm.icon || ''}
                    onChange={(e) => setCategoryForm({...categoryForm, icon: e.target.value})}
                    className="w-full bg-surface-2 border border-border rounded px-3 py-2 text-ink-inverse focus:outline-none focus:border-blue-500"
                    placeholder="fa-folder"
                  />
                </div>
              </div>
              <div className="flex space-x-3">
                <Button
                  type="submit"
                >
                  {isEditingCategory ? '更新' : '创建'}
                </Button>
                {isEditingCategory && (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={handleCancelCategoryEdit}
                  >
                    取消
                  </Button>
                )}
              </div>
            </form>
            </CardContent>
          </Card>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-ink-muted">
              <thead className="bg-surface-2 text-ink uppercase text-xs">
                <tr>
                  <th className="px-6 py-3">分类名称</th>
                  <th className="px-6 py-3">使用计数</th>
                  <th className="px-6 py-3">排序</th>
                  <th className="px-6 py-3">描述</th>
                  <th className="px-6 py-3">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {categories.map((cat) => (
                  <tr key={cat.id} className="hover:bg-surface-2/50">
                    <td className="px-6 py-4 flex items-center">
                       {cat.icon && <i className={`fa-solid ${cat.icon} mr-2 text-ink-muted`}></i>}
                       <span className="font-medium text-ink-inverse">{cat.name}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={cat.tool_count ? 'text-green-400' : 'text-ink-faint'}>
                        {cat.tool_count || 0}
                      </span>
                      {!cat.tool_count && <span className="ml-2 text-xs text-ink-faint">未使用</span>}
                    </td>
                    <td className="px-6 py-4">{cat.sort_order}</td>
                    <td className="px-6 py-4 text-sm text-ink-muted">{cat.description || '-'}</td>
                    <td className="px-6 py-4 flex space-x-3">
                      <button
                        onClick={() => handleEditCategory(cat)}
                        className="text-accent-info hover:text-blue-300 text-sm font-medium"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDeleteCategory(cat.id)}
                        className="text-danger hover:text-red-300 text-sm font-medium"
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
      )}    </div>
  );
}
