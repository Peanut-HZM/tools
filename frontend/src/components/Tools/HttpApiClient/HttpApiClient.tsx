import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Plug,
  FileInput,
  History,
  Plus,
  Loader2,
  FolderOpen,
  X,
  AlertTriangle,
} from 'lucide-react';
import { useHttpClientStore } from '../../../stores/httpClientStore';
import { useAuth } from '../../../stores/authStore';
import RequireAuthNotice from '../../Common/RequireAuthNotice';
import { Collection, HttpRequest, Environment, createRequest, createCollection, updateCollection, deleteCollection, FormDataEntry } from '../../../services/httpClientApi';
import { useToast } from '../../../contexts/ToastContext';

/** Form-data 单文件大小上限（25MB），防止前端 base64 编码耗尽内存 */
const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024;

/** 将 File 对象读取为 base64 data URL（用于通过 JSON 传递文件）
 *  在编码前先检查大小，超出阈值立即抛出，避免占用大量内存
 */
const fileToDataUrl = (file: File): Promise<string> => {
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return Promise.reject(
      new Error(`文件过大（${(file.size / 1024 / 1024).toFixed(1)}MB），单文件上限 ${MAX_FILE_SIZE_BYTES / 1024 / 1024}MB`),
    );
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(reader.error || new Error('FileReader error'));
    reader.readAsDataURL(file);
  });
};
import CollectionTree from './components/CollectionTree';
import RequestTabs from './components/RequestTabs';
import RequestEditor from './components/RequestEditor/RequestEditor';
import ResponseViewer from './components/ResponseViewer/ResponseViewer';
import EnvironmentSelector from './components/EnvironmentSelector';
import ImportExportModal from './components/ImportExportModal';
import HistoryPanel from './components/HistoryPanel';
import RequestContextMenu from './components/RequestContextMenu';
import CollectionContextMenu from './components/CollectionContextMenu';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

export default function HttpApiClient() {
  const navigate = useNavigate();
  const toast = useToast();
  const { isAuthenticated, authVersion } = useAuth();
  const {
    collections,
    loadingCollections,
    loadCollections,
    loadRequests,
    loadEnvironments,
    environments,
    activeEnvironment,
    openTabs,
    activeTabId,
    setActiveTab,
    openTab,
    closeTab,
    updateTabRequest,
    currentResponse,
    sendingRequest,
    sendRequest,
    clearResponse,
    loadHistory,
    clearHistory,
    replayFromHistory,
    duplicateRequest,
    deleteRequest,
    saveRequest,
    renameRequest,
    history,
  } = useHttpClientStore();

  const [selectedCollectionId, setSelectedCollectionId] = useState<string | null>(null);
  const [sidebarWidth, setSidebarWidth] = useState(280);
  const [responseHeight, setResponseHeight] = useState(300);
  const [isImportExportModalOpen, setIsImportExportModalOpen] = useState(false);
  const [showNewRequestForm, setShowNewRequestForm] = useState(false);
  const [newRequestCollectionId, setNewRequestCollectionId] = useState<string>('');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [showHistoryPanel, setShowHistoryPanel] = useState(false);
  const [collectionModal, setCollectionModal] = useState<
    | { mode: 'create' }
    | { mode: 'rename'; collection: Collection }
    | null
  >(null);
  const [collectionModalName, setCollectionModalName] = useState('');
  const [collectionContextMenu, setCollectionContextMenu] = useState<{
    x: number; y: number; collection: Collection;
  } | null>(null);
  const [contextMenu, setContextMenu] = useState<{
    x: number; y: number; request: HttpRequest;
  } | null>(null);
  const [renameRequestTrigger, setRenameRequestTrigger] = useState<{
    request: HttpRequest;
    nonce: number;
  } | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  // 新建请求表单状态
  const [newCollectionName, setNewCollectionName] = useState('');
  const [newRequestName, setNewRequestName] = useState('');
  const [newRequestUrl, setNewRequestUrl] = useState('');
  const [newRequestMethod, setNewRequestMethod] = useState('GET');

  // 加载数据（未登录时不发请求；登录成功/authVersion 变化后自动重载）
  useEffect(() => {
    if (!isAuthenticated) return;
    loadCollections();
    loadEnvironments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, authVersion]);

  // 获取当前激活的标签页
  const activeTab = openTabs.find(tab => tab.requestId === activeTabId);

  // 历史回放标签页（requestId 以 history_ 开头）不支持保存/删除
  const isHistoryReplay = activeTab ? activeTab.requestId.startsWith('history_') : false;

  // 处理新建集合
  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) return;

    try {
      await createCollection({ name: newCollectionName, workspace_id: 'default' });
      setNewCollectionName('');
      loadCollections();
    } catch (error) {
      console.error('Failed to create collection:', error);
    }
  };

  // 处理新建请求
  const handleCreateRequest = async () => {
    if (!newRequestName.trim()) {
      toast.warning('请输入请求名称');
      return;
    }
    if (!newRequestUrl.trim()) {
      toast.warning('请输入请求 URL');
      return;
    }
    if (!newRequestCollectionId) {
      toast.warning('请选择目标集合');
      return;
    }

    try {
      const newRequest = await createRequest({
        collection_id: newRequestCollectionId,
        name: newRequestName,
        method: newRequestMethod,
        url: newRequestUrl,
        headers: {},
        params: {},
        body_type: 'none',
        body: '',
        auth_type: 'none',
        auth_config: {},
        sort_order: 0,
      });

      toast.success('请求创建成功');
      setNewRequestName('');
      setNewRequestUrl('');
      setNewRequestCollectionId('');
      setShowNewRequestForm(false);

      // 刷新集合树
      setRefreshTrigger(prev => prev + 1);
      loadRequests(newRequestCollectionId);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || error?.message || '创建请求失败');
    }
  };

  // 处理集合选择
  const handleCollectionSelect = (collection: Collection | null) => {
    setSelectedCollectionId(collection?.id || null);
  };

  // 集合弹窗提交（新建/重命名共用）
  const handleCollectionModalSubmit = async () => {
    const name = collectionModalName.trim();
    if (!name || !collectionModal) return;
    try {
      if (collectionModal.mode === 'create') {
        await createCollection({ name, workspace_id: 'default' });
        toast.success('集合创建成功');
      } else {
        await updateCollection(collectionModal.collection.id, { name });
        toast.success('集合已重命名');
      }
      setCollectionModal(null);
      setCollectionModalName('');
      loadCollections();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || error?.message || '操作失败');
    }
  };

  // 删除集合：确认后级联删除，并关闭该集合下已打开的请求标签页
  const handleCollectionDelete = async (collection: Collection) => {
    if (!confirm(`确定删除集合 "${collection.name}"？其中的所有请求将一并删除。`)) return;
    try {
      await deleteCollection(collection.id);
      toast.success('集合已删除');
      openTabs
        .filter(tab => tab.request.collection_id === collection.id)
        .forEach(tab => closeTab(tab.requestId));
      if (selectedCollectionId === collection.id) {
        setSelectedCollectionId(null);
      }
      setCollectionContextMenu(null);
      loadCollections();
      setRefreshTrigger(prev => prev + 1);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || error?.message || '删除失败');
    }
  };

  // 保存当前激活请求
  const handleSaveActiveRequest = async () => {
    if (!activeTabId) return;
    try {
      await saveRequest(activeTabId);
      toast.success('保存成功');
      setRefreshTrigger(prev => prev + 1);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || error?.message || '保存失败');
    }
  };

  // 删除当前激活请求：确认后删除并关闭标签页
  const handleDeleteActiveRequest = async () => {
    if (!activeTab) return;
    if (!confirm(`确定删除请求 "${activeTab.request.name}" 吗？`)) return;
    try {
      await deleteRequest(activeTab.requestId, '');
      closeTab(activeTab.requestId);
      toast.success('请求已删除');
      setRefreshTrigger(prev => prev + 1);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || error?.message || '删除失败');
    }
  };

  // 关闭标签页拦截：有未保存修改时二次确认
  const handleTabClose = (requestId: string) => {
    const tab = openTabs.find(t => t.requestId === requestId);
    if (tab?.isModified && !confirm('有未保存的修改，确定关闭？')) {
      return;
    }
    closeTab(requestId);
  };

  // 处理请求打开
  const handleRequestOpen = (request: HttpRequest) => {
    openTab(request);
  };

  // 处理发送请求
  const handleSendRequest = async (request: HttpRequest) => {
    try {
      // form-data 类型：将 File 对象转换为 base64 data URL，以便通过 JSON 发送给后端
      let formDataPayload: FormDataEntry[] | undefined = request.form_data;
      if (request.body_type === 'form-data' && request.form_data?.length) {
        formDataPayload = await Promise.all(
          request.form_data.map(async (entry): Promise<FormDataEntry> => {
            if (entry.type === 'file' && entry.file) {
              const dataUrl = await fileToDataUrl(entry.file);
              return {
                key: entry.key,
                value: dataUrl,
                type: 'file',
                description: entry.description,
              };
            }
            return {
              key: entry.key,
              value: entry.value,
              type: entry.type,
              description: entry.description,
            };
          })
        );
      }

      const response = await sendRequest({
        method: request.method,
        url: request.url,
        headers: request.headers,
        params: request.params,
        body_type: request.body_type,
        body: request.body,
        form_data: formDataPayload,
        timeout: 30000,
        follow_redirects: true,
      });
      toast.success(`请求成功 ${response.status_code} · ${response.response_time}ms`);
    } catch (error: any) {
      const message = error?.response?.data?.detail || error?.message || '请求失败';
      toast.error(message);
    }
  };

  // 处理历史面板
  const handleToggleHistory = useCallback(async () => {
    if (!showHistoryPanel) {
      setHistoryLoading(true);
      await loadHistory();
      setHistoryLoading(false);
    }
    setShowHistoryPanel(prev => !prev);
  }, [showHistoryPanel, loadHistory]);

  const handleHistoryReplay = useCallback((item: any) => {
    replayFromHistory(item);
    setShowHistoryPanel(false);
  }, [replayFromHistory]);

  const handleHistoryClear = useCallback(async () => {
    await clearHistory();
    toast.success('历史已清空');
  }, [clearHistory, toast]);

  // 处理右键菜单
  const handleContextMenu = useCallback((e: React.MouseEvent, request: HttpRequest) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, request });
  }, []);

  const handleCloseContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  const handleDuplicateRequest = useCallback(async (request: HttpRequest, targetCollectionId: string) => {
    try {
      await duplicateRequest(request, targetCollectionId);
      toast.success('请求已复制');
      setRefreshTrigger(prev => prev + 1);
    } catch (error: any) {
      toast.error(error?.message || '复制失败');
    }
  }, [duplicateRequest, toast]);

  // 树内改名：直接持久化并刷新集合树
  const handleRequestRename = useCallback(async (request: HttpRequest, name: string) => {
    try {
      await renameRequest(request.id, name);
      toast.success('请求已重命名');
      setRefreshTrigger(prev => prev + 1);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || error?.message || '重命名失败');
    }
  }, [renameRequest, toast]);

  const handleDeleteRequest = useCallback(async (requestId: string) => {
    try {
      await deleteRequest(requestId, '');
      // 同步关闭已打开的同请求标签页，避免残留失效页
      closeTab(requestId);
      toast.success('请求已删除');
      setRefreshTrigger(prev => prev + 1);
    } catch (error: any) {
      toast.error(error?.message || '删除失败');
    }
  }, [deleteRequest, closeTab, toast]);

  // Ctrl+S / Cmd+S 保存当前请求
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        const tab = openTabs.find(t => t.requestId === activeTabId);
        if (tab?.isModified && !isHistoryReplay) {
          handleSaveActiveRequest();
        }
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTabId, openTabs, isHistoryReplay]);

  // 拖拽调整侧边栏宽度
  const handleSidebarResize = (e: React.MouseEvent) => {
    const startX = e.clientX;
    const startWidth = sidebarWidth;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientX - startX;
      const newWidth = Math.max(200, Math.min(400, startWidth + delta));
      setSidebarWidth(newWidth);
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  // 拖拽调整响应面板高度
  const handleResponseResize = (e: React.MouseEvent) => {
    const startY = e.clientY;
    const startHeight = responseHeight;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const delta = startY - moveEvent.clientY;
      const newHeight = Math.max(150, Math.min(600, startHeight + delta));
      setResponseHeight(newHeight);
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  // 未登录：不发请求，显示登录提示
  if (!isAuthenticated) {
    return <RequireAuthNotice />;
  }

  return (
    <div className="flex-1 text-ink flex flex-col overflow-hidden">
      {/* 顶部工具栏 */}
      <div className="bg-surface-1 border-b border-border px-4 py-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/')}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">返回</span>
          </Button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-accent-secondary rounded flex items-center justify-center">
              <Plug className="w-4 h-4 text-ink-inverse" />
            </div>
            <h1 className="text-lg font-bold">HTTP API 客户端</h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* 环境选择器 */}
          <EnvironmentSelector
            environments={environments}
            activeEnvironment={activeEnvironment}
          />

          {/* 导入/导出按钮 */}
          <Button
            variant="ghost"
            size="sm"
            title="导入/导出"
            onClick={() => setIsImportExportModalOpen(true)}
          >
            <FileInput className="w-4 h-4 mr-1" />
            导入/导出
          </Button>

          {/* 历史按钮 */}
          <Button
            variant="ghost"
            size="sm"
            title="请求历史"
            onClick={handleToggleHistory}
          >
            <History className="w-4 h-4 mr-1" />
            历史
          </Button>

          {/* 新建请求按钮 */}
          <Button
            variant="default"
            size="sm"
            onClick={() => setShowNewRequestForm(true)}
          >
            <Plus className="w-4 h-4 mr-1" />
            新建请求
          </Button>
        </div>
      </div>

      {/* 主体内容 - 三栏布局 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧：集合导航 */}
        <div
          className="bg-surface-1 border-r border-border flex flex-col overflow-hidden flex-shrink-0"
          style={{ width: sidebarWidth }}
        >
          <div className="p-3 border-b border-border flex items-center justify-between">
            <h2 className="font-semibold text-sm">请求集合</h2>
            <Button
              variant="ghost"
              size="icon"
              title="新建集合"
              onClick={() => {
                setCollectionModal({ mode: 'create' });
                setCollectionModalName('');
              }}
            >
              <Plus className="w-4 h-4" />
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loadingCollections ? (
              <div className="text-center py-8 text-ink-faint text-sm">
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                加载中...
              </div>
            ) : collections.length === 0 ? (
              <div className="text-center py-8 text-ink-faint text-xs">
                <FolderOpen className="w-8 h-8 mb-2 opacity-50" />
                <p>暂无集合</p>
                <p className="mt-1">点击"+"创建</p>
              </div>
            ) : (
              <CollectionTree
                collections={collections}
                selectedCollectionId={selectedCollectionId}
                onCollectionSelect={handleCollectionSelect}
                onRequestOpen={handleRequestOpen}
                onRequestContextMenu={handleContextMenu}
                refreshTrigger={refreshTrigger}
                onCollectionRename={(collection) => {
                  setCollectionModal({ mode: 'rename', collection });
                  setCollectionModalName(collection.name);
                }}
                onCollectionDelete={handleCollectionDelete}
                onCollectionContextMenu={(e, collection) => {
                  e.preventDefault();
                  setCollectionContextMenu({ x: e.clientX, y: e.clientY, collection });
                }}
                onRequestRename={handleRequestRename}
                onRequestDelete={(request) => {
                  if (confirm(`确定删除请求 "${request.name}" 吗？`)) {
                    handleDeleteRequest(request.id);
                  }
                }}
                renameTrigger={renameRequestTrigger}
              />
            )}
          </div>
        </div>

        {/* 拖拽手柄 - 调整侧边栏 */}
        <div
          className="w-1 bg-surface-2 hover:bg-accent-secondary cursor-col-resize flex-shrink-0 transition-colors"
          onMouseDown={handleSidebarResize}
        ></div>

        {/* 中间：标签页 + 请求编辑器 */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* 标签页栏 */}
          <RequestTabs
            openTabs={openTabs}
            activeTabId={activeTabId}
            onTabClick={setActiveTab}
            onTabClose={handleTabClose}
            onCreateNewRequest={() => setShowNewRequestForm(true)}
            onRename={(requestId, name) => updateTabRequest(requestId, { name })}
          />

          {/* 请求编辑器 */}
          <div className="flex-1 overflow-hidden flex flex-col">
            {activeTab ? (
              <RequestEditor
                request={activeTab.request}
                isModified={activeTab.isModified}
                onUpdate={(updatedRequest) => {
                  updateTabRequest(activeTab.requestId, updatedRequest);
                }}
                onSend={() => handleSendRequest(activeTab.request)}
                sending={sendingRequest}
                envVariables={activeEnvironment?.variables || {}}
                onSave={isHistoryReplay ? undefined : handleSaveActiveRequest}
                onDelete={isHistoryReplay ? undefined : handleDeleteActiveRequest}
              />
            ) : (
              <div className="flex-1 flex items-center justify-center text-ink-faint">
                <div className="text-center">
                  <Plug className="w-16 h-16 mb-4 opacity-20" />
                  <p>选择一个请求或创建新请求</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 底部：响应面板 */}
      {currentResponse && (
        <>
          <div
            className="h-2 bg-surface-2 hover:bg-accent-secondary cursor-row-resize flex-shrink-0 transition-colors"
            onMouseDown={handleResponseResize}
          ></div>
          <div
            className="border-t border-border flex flex-col overflow-hidden flex-shrink-0"
            style={{ height: responseHeight }}
          >
            <ResponseViewer
              response={currentResponse}
              request={activeTab?.request}
              envVariables={activeEnvironment?.variables}
            />
          </div>
        </>
      )}

      {/* 导入/导出弹窗 */}
      <ImportExportModal
        isOpen={isImportExportModalOpen}
        onClose={() => setIsImportExportModalOpen(false)}
        onImportSuccess={() => {
          loadCollections();
        }}
      />

      {/* 历史面板弹窗 */}
      {showHistoryPanel && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-surface-1 rounded-lg w-full max-w-2xl max-h-[70vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h2 className="text-lg font-semibold">请求历史</h2>
              <Button variant="ghost" size="icon" onClick={() => setShowHistoryPanel(false)}>
                <X className="w-4 h-4" />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <HistoryPanel
                history={history}
                loading={historyLoading}
                onReplay={handleHistoryReplay}
                onClear={handleHistoryClear}
              />
            </div>
          </div>
        </div>
      )}

      {/* 右键菜单 */}
      {contextMenu && (
        <RequestContextMenu
          request={contextMenu.request}
          collections={collections}
          x={contextMenu.x}
          y={contextMenu.y}
          onRename={(request) => {
            setRenameRequestTrigger({ request, nonce: Date.now() });
          }}
          onDuplicate={handleDuplicateRequest}
          onDelete={handleDeleteRequest}
          onClose={handleCloseContextMenu}
        />
      )}

      {/* 集合新建/重命名弹窗 */}
      {collectionModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-surface-1 rounded-lg w-full max-w-md p-6">
            <h3 className="text-lg font-semibold mb-4">
              {collectionModal.mode === 'create' ? '新建集合' : '重命名集合'}
            </h3>
            <div>
              <label className="text-sm text-ink-muted mb-1 block">集合名称</label>
              <Input
                type="text"
                value={collectionModalName}
                onChange={(e) => setCollectionModalName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleCollectionModalSubmit();
                }}
                placeholder="例如：Glodon-SAP"
                className="w-full"
                autoFocus
              />
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button
                variant="ghost"
                onClick={() => setCollectionModal(null)}
              >
                取消
              </Button>
              <Button
                variant="default"
                onClick={handleCollectionModalSubmit}
                disabled={!collectionModalName.trim()}
              >
                确定
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 集合右键菜单 */}
      {collectionContextMenu && (
        <CollectionContextMenu
          collection={collectionContextMenu.collection}
          x={collectionContextMenu.x}
          y={collectionContextMenu.y}
          onRename={(collection) => {
            setCollectionContextMenu(null);
            setCollectionModal({ mode: 'rename', collection });
            setCollectionModalName(collection.name);
          }}
          onDelete={handleCollectionDelete}
          onClose={() => setCollectionContextMenu(null)}
        />
      )}

      {/* 新建集合弹窗 */}
      {showNewRequestForm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-surface-1 rounded-lg w-full max-w-md p-6">
            <h3 className="text-lg font-semibold mb-4">新建请求</h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-ink-muted mb-1 block">请求名称</label>
                <Input
                  type="text"
                  value={newRequestName}
                  onChange={(e) => setNewRequestName(e.target.value)}
                  placeholder="My Request"
                  className="w-full"
                />
              </div>
              <div>
                <label className="text-sm text-ink-muted mb-1 block">目标集合</label>
                {collections.length === 0 ? (
                  <div className="text-sm text-warning bg-warning/10 px-3 py-2 rounded border border-warning/30">
                    <AlertTriangle className="w-4 h-4 mr-2" />
                    暂无集合，请先创建集合
                  </div>
                ) : (
                  <Select value={newRequestCollectionId} onValueChange={setNewRequestCollectionId}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="请选择集合" />
                    </SelectTrigger>
                    <SelectContent>
                      {collections.map(c => (
                        <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
              <div>
                <label className="text-sm text-ink-muted mb-1 block">方法</label>
                <Select value={newRequestMethod} onValueChange={setNewRequestMethod}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="GET">GET</SelectItem>
                    <SelectItem value="POST">POST</SelectItem>
                    <SelectItem value="PUT">PUT</SelectItem>
                    <SelectItem value="DELETE">DELETE</SelectItem>
                    <SelectItem value="PATCH">PATCH</SelectItem>
                    <SelectItem value="HEAD">HEAD</SelectItem>
                    <SelectItem value="OPTIONS">OPTIONS</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm text-ink-muted mb-1 block">URL</label>
                <Input
                  type="text"
                  value={newRequestUrl}
                  onChange={(e) => setNewRequestUrl(e.target.value)}
                  placeholder="https://api.example.com/users"
                  className="w-full"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button
                variant="ghost"
                onClick={() => setShowNewRequestForm(false)}
              >
                取消
              </Button>
              <Button
                variant="default"
                onClick={handleCreateRequest}
                disabled={!newRequestName.trim() || !newRequestUrl.trim() || !newRequestCollectionId}
              >
                创建
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
