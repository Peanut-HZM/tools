import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useHttpClientStore } from '../../../stores/httpClientStore';
import { Collection, HttpRequest, Environment, createRequest, createCollection } from '../../../services/httpClientApi';
import CollectionTree from './components/CollectionTree';
import RequestTabs from './components/RequestTabs';
import RequestEditor from './components/RequestEditor/RequestEditor';
import ResponseViewer from './components/ResponseViewer/ResponseViewer';
import EnvironmentSelector from './components/EnvironmentSelector';
import ImportExportModal from './components/ImportExportModal';

export default function HttpApiClient() {
  const navigate = useNavigate();
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
  } = useHttpClientStore();

  const [selectedCollectionId, setSelectedCollectionId] = useState<string | null>(null);
  const [sidebarWidth, setSidebarWidth] = useState(280);
  const [responseHeight, setResponseHeight] = useState(300);
  const [isImportExportModalOpen, setIsImportExportModalOpen] = useState(false);
  const [showNewRequestForm, setShowNewRequestForm] = useState(false);

  // 新建请求表单状态
  const [newCollectionName, setNewCollectionName] = useState('');
  const [newRequestName, setNewRequestName] = useState('');
  const [newRequestUrl, setNewRequestUrl] = useState('');
  const [newRequestMethod, setNewRequestMethod] = useState('GET');

  // 加载数据
  useEffect(() => {
    loadCollections();
    loadEnvironments();
  }, []);

  // 获取当前激活的标签页
  const activeTab = openTabs.find(tab => tab.requestId === activeTabId);

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
    if (!newRequestName.trim() || !selectedCollectionId) return;

    try {
      const newRequest = await createRequest({
        collection_id: selectedCollectionId,
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

      setNewRequestName('');
      setNewRequestUrl('');
      setShowNewRequestForm(false);

      // 打开新标签页
      // TODO: 需要调用 openTab
      loadRequests(selectedCollectionId);
    } catch (error) {
      console.error('Failed to create request:', error);
    }
  };

  // 处理集合选择
  const handleCollectionSelect = (collection: Collection | null) => {
    setSelectedCollectionId(collection?.id || null);
  };

  // 处理请求打开
  const handleRequestOpen = (request: HttpRequest) => {
    openTab(request);
  };

  // 处理发送请求
  const handleSendRequest = async (request: HttpRequest) => {
    try {
      const response = await sendRequest({
        method: request.method,
        url: request.url,
        headers: request.headers,
        params: request.params,
        body_type: request.body_type,
        body: request.body,
        timeout: 30000,
        follow_redirects: true,
      });
      return response;
    } catch (error) {
      throw error;
    }
  };

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

  return (
    <div className="flex-1 text-slate-100 flex flex-col overflow-hidden">
      {/* 顶部工具栏 */}
      <div className="bg-slate-800 border-b border-slate-700 px-4 py-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="text-slate-400 hover:text-white transition-colors flex items-center gap-2"
          >
            <i className="fas fa-arrow-left"></i>
            <span className="hidden sm:inline">返回</span>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-purple-500 rounded flex items-center justify-center">
              <i className="fas fa-plug text-white text-sm"></i>
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
          <button
            className="text-slate-400 hover:text-white transition-colors text-sm"
            title="导入/导出"
            onClick={() => setIsImportExportModalOpen(true)}
          >
            <i className="fas fa-file-import mr-1"></i>
            导入/导出
          </button>

          {/* 新建请求按钮 */}
          <button
            className="bg-purple-500 hover:bg-purple-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
            onClick={() => setShowNewRequestForm(true)}
          >
            <i className="fas fa-plus mr-1"></i>
            新建请求
          </button>
        </div>
      </div>

      {/* 主体内容 - 三栏布局 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧：集合导航 */}
        <div
          className="bg-slate-800 border-r border-slate-700 flex flex-col overflow-hidden flex-shrink-0"
          style={{ width: sidebarWidth }}
        >
          <div className="p-3 border-b border-slate-700 flex items-center justify-between">
            <h2 className="font-semibold text-sm">请求集合</h2>
            <button
              className="text-slate-400 hover:text-white transition-colors text-xs"
              title="新建集合"
              onClick={() => {
                const name = prompt('输入集合名称:');
                if (name) {
                  createCollection({ name, workspace_id: 'default' }).then(() => {
                    loadCollections();
                  });
                }
              }}
            >
              <i className="fas fa-plus"></i>
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loadingCollections ? (
              <div className="text-center py-8 text-slate-500 text-sm">
                <i className="fas fa-spinner fa-spin mr-2"></i>
                加载中...
              </div>
            ) : collections.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-xs">
                <i className="fas fa-folder-open text-2xl mb-2 opacity-50"></i>
                <p>暂无集合</p>
                <p className="mt-1">点击"+"创建</p>
              </div>
            ) : (
              <CollectionTree
                collections={collections}
                selectedCollectionId={selectedCollectionId}
                onCollectionSelect={handleCollectionSelect}
                onRequestOpen={handleRequestOpen}
              />
            )}
          </div>
        </div>

        {/* 拖拽手柄 - 调整侧边栏 */}
        <div
          className="w-1 bg-slate-700 hover:bg-purple-500 cursor-col-resize flex-shrink-0 transition-colors"
          onMouseDown={handleSidebarResize}
        ></div>

        {/* 中间：标签页 + 请求编辑器 */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* 标签页栏 */}
          <RequestTabs
            openTabs={openTabs}
            activeTabId={activeTabId}
            onTabClick={setActiveTab}
            onTabClose={closeTab}
            onCreateNewRequest={() => setShowNewRequestForm(true)}
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
              />
            ) : (
              <div className="flex-1 flex items-center justify-center text-slate-500">
                <div className="text-center">
                  <i className="fas fa-plug text-6xl mb-4 opacity-20"></i>
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
            className="h-2 bg-slate-700 hover:bg-purple-500 cursor-row-resize flex-shrink-0 transition-colors"
            onMouseDown={handleResponseResize}
          ></div>
          <div
            className="border-t border-slate-700 flex flex-col overflow-hidden flex-shrink-0"
            style={{ height: responseHeight }}
          >
            <ResponseViewer response={currentResponse} />
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

      {/* 新建集合弹窗 */}
      {showNewRequestForm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg w-full max-w-md p-6">
            <h3 className="text-lg font-semibold mb-4">新建请求</h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-slate-400 mb-1 block">请求名称</label>
                <input
                  type="text"
                  value={newRequestName}
                  onChange={(e) => setNewRequestName(e.target.value)}
                  placeholder="My Request"
                  className="w-full bg-slate-700 text-white px-3 py-2 rounded border border-slate-600"
                />
              </div>
              <div>
                <label className="text-sm text-slate-400 mb-1 block">方法</label>
                <select
                  value={newRequestMethod}
                  onChange={(e) => setNewRequestMethod(e.target.value)}
                  className="w-full bg-slate-700 text-white px-3 py-2 rounded border border-slate-600"
                >
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                  <option value="PUT">PUT</option>
                  <option value="DELETE">DELETE</option>
                  <option value="PATCH">PATCH</option>
                  <option value="HEAD">HEAD</option>
                  <option value="OPTIONS">OPTIONS</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-slate-400 mb-1 block">URL</label>
                <input
                  type="text"
                  value={newRequestUrl}
                  onChange={(e) => setNewRequestUrl(e.target.value)}
                  placeholder="https://api.example.com/users"
                  className="w-full bg-slate-700 text-white px-3 py-2 rounded border border-slate-600"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowNewRequestForm(false)}
                className="px-4 py-2 text-slate-400 hover:text-white"
              >
                取消
              </button>
              <button
                onClick={handleCreateRequest}
                disabled={!newRequestName.trim()}
                className={`
                  px-6 py-2 rounded-lg font-medium
                  ${!newRequestName.trim()
                    ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
                    : 'bg-purple-500 hover:bg-purple-600 text-white'
                  }
                `}
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
