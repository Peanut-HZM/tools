import { useState, useEffect } from 'react';
import { Collection, HttpRequest, fetchRequests } from '../../../../services/httpClientApi';

interface CollectionTreeProps {
  collections: Collection[];
  selectedCollectionId: string | null;
  onCollectionSelect: (collection: Collection | null) => void;
  onRequestOpen: (request: HttpRequest) => void;
  onRequestContextMenu?: (e: React.MouseEvent, request: HttpRequest) => void;
  refreshTrigger?: number;
  /** 集合重命名（行内悬停按钮/右键菜单） */
  onCollectionRename?: (collection: Collection) => void;
  /** 集合删除（行内悬停按钮/右键菜单） */
  onCollectionDelete?: (collection: Collection) => void;
  /** 集合右键菜单回调 */
  onCollectionContextMenu?: (e: React.MouseEvent, collection: Collection) => void;
  /** 请求重命名（行内编辑确认后回调） */
  onRequestRename?: (request: HttpRequest, name: string) => void;
  /** 请求删除（行内悬停按钮） */
  onRequestDelete?: (request: HttpRequest) => void;
  /** 外部触发的重命名目标（右键菜单"重命名"路径），值变化即进入编辑态 */
  renameTrigger?: { request: HttpRequest; nonce: number } | null;
}

export default function CollectionTree({
  collections,
  selectedCollectionId,
  onCollectionSelect,
  onRequestOpen,
  onRequestContextMenu,
  onCollectionRename,
  onCollectionDelete,
  onCollectionContextMenu,
  onRequestRename,
  onRequestDelete,
  renameTrigger,
  refreshTrigger = 0,
}: CollectionTreeProps) {
  const [expandedCollections, setExpandedCollections] = useState<Set<string>>(new Set());
  const [collectionRequests, setCollectionRequests] = useState<Record<string, HttpRequest[]>>({});
  const [loadingRequests, setLoadingRequests] = useState<Set<string>>(new Set());
  const [editingRequest, setEditingRequest] = useState<HttpRequest | null>(null);
  const [editingRequestName, setEditingRequestName] = useState('');

  // 当 refreshTrigger 变化时，清除已展开集合的缓存并重新加载
  useEffect(() => {
    if (refreshTrigger === 0) return;
    const expandedArray = Array.from(expandedCollections);
    if (expandedArray.length === 0) return;

    // 清除缓存并重新加载
    setCollectionRequests(prev => {
      const next = { ...prev };
      expandedArray.forEach(id => delete next[id]);
      return next;
    });

    // 重新加载每个展开集合的请求
    expandedArray.forEach(async (collectionId) => {
      try {
        const requests = await fetchRequests(collectionId);
        setCollectionRequests(prev => ({ ...prev, [collectionId]: requests }));
      } catch (error) {
        console.error('Failed to reload requests:', error);
      }
    });
  }, [refreshTrigger]);

  // 外部触发改名（右键菜单路径）：进入编辑态
  useEffect(() => {
    if (renameTrigger) {
      setEditingRequest(renameTrigger.request);
      setEditingRequestName(renameTrigger.request.name);
    }
  }, [renameTrigger]);

  const toggleExpand = async (collectionId: string) => {
    const newExpanded = new Set(expandedCollections);
    const isExpanding = !newExpanded.has(collectionId);

    if (isExpanding) {
      newExpanded.add(collectionId);
      // 加载请求列表
      if (!collectionRequests[collectionId]) {
        setLoadingRequests(prev => new Set(prev).add(collectionId));
        try {
          const requests = await fetchRequests(collectionId);
          setCollectionRequests(prev => ({ ...prev, [collectionId]: requests }));
        } catch (error) {
          console.error('Failed to load requests:', error);
        } finally {
          setLoadingRequests(prev => {
            const next = new Set(prev);
            next.delete(collectionId);
            return next;
          });
        }
      }
    } else {
      newExpanded.delete(collectionId);
    }
    setExpandedCollections(newExpanded);
  };

  const handleCollectionClick = (collection: Collection) => {
    onCollectionSelect(collection);
    toggleExpand(collection.id);
  };

  const handleRequestClick = (request: HttpRequest) => {
    onRequestOpen(request);
  };

  // 确认请求改名：非空才回调父组件
  const handleConfirmRequestRename = () => {
    if (editingRequest) {
      const trimmed = editingRequestName.trim();
      if (trimmed) {
        onRequestRename?.(editingRequest, trimmed);
      }
    }
    setEditingRequest(null);
    setEditingRequestName('');
  };

  // 构建层级结构
  const buildTree = () => {
    const rootCollections = collections.filter(c => !c.parent_id);
    const childrenMap = new Map<string, Collection[]>();

    collections.forEach(c => {
      if (c.parent_id) {
        if (!childrenMap.has(c.parent_id)) {
          childrenMap.set(c.parent_id, []);
        }
        childrenMap.get(c.parent_id)!.push(c);
      }
    });

    return { rootCollections, childrenMap };
  };

  const { rootCollections, childrenMap } = buildTree();

  const renderCollection = (collection: Collection, level = 0) => {
    const children = childrenMap.get(collection.id) || [];
    const isExpanded = expandedCollections.has(collection.id);
    const isSelected = selectedCollectionId === collection.id;
    const requests = collectionRequests[collection.id] || [];
    const isLoading = loadingRequests.has(collection.id);

    return (
      <div key={collection.id}>
        <div
          className={`
            group flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors text-sm
            ${isSelected
              ? 'bg-purple-500/20 border border-purple-500 text-purple-400'
              : 'hover:bg-slate-700/50 border border-transparent text-slate-300'
            }
          `}
          style={{ paddingLeft: level * 16 + 12 }}
          onClick={() => handleCollectionClick(collection)}
          onContextMenu={(e) => {
            e.preventDefault();
            onCollectionContextMenu?.(e, collection);
          }}
        >
          <button
            title="展开/折叠"
            onClick={(e) => {
              e.stopPropagation();
              handleCollectionClick(collection);
            }}
            className="text-slate-500 hover:text-slate-300 transition-colors"
          >
            <i
              className={`fas fa-chevron-right text-xs transition-transform ${
                isExpanded ? 'rotate-90' : ''
              }`}
            ></i>
          </button>
          <i className="fas fa-folder text-slate-500 text-xs"></i>
          <span className="truncate flex-1">{collection.name}</span>
          {onCollectionRename && (
            <button
              title="重命名"
              onClick={(e) => {
                e.stopPropagation();
                onCollectionRename(collection);
              }}
              className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-slate-500 hover:text-slate-300 transition-opacity text-xs flex-shrink-0"
            >
              <i className="fas fa-pencil"></i>
            </button>
          )}
          {onCollectionDelete && (
            <button
              title="删除"
              onClick={(e) => {
                e.stopPropagation();
                onCollectionDelete(collection);
              }}
              className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-slate-500 hover:text-red-400 transition-opacity text-xs flex-shrink-0"
            >
              <i className="fas fa-trash"></i>
            </button>
          )}
        </div>

        {/* 请求列表 */}
        {isExpanded && (
          <div className="ml-4">
            {isLoading ? (
              <div className="py-2 text-xs text-slate-500">
                <i className="fas fa-spinner fa-spin mr-2"></i>
                加载中...
              </div>
            ) : requests.length === 0 ? (
              <div className="py-2 text-xs text-slate-500">
                暂无请求
              </div>
            ) : (
              <div className="mt-1 space-y-1">
                {requests.map(request => (
                  <div
                    key={request.id}
                    className="group flex items-center gap-2 px-3 py-1.5 cursor-pointer
                               hover:bg-slate-700/50 rounded text-xs text-slate-400"
                    onClick={() => handleRequestClick(request)}
                    onContextMenu={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      onRequestContextMenu?.(e, request);
                    }}
                  >
                    <span className={`
                      font-mono font-bold w-12 flex-shrink-0
                      ${request.method === 'GET' ? 'text-green-400' :
                        request.method === 'POST' ? 'text-blue-400' :
                        request.method === 'PUT' ? 'text-yellow-400' :
                        request.method === 'DELETE' ? 'text-red-400' :
                        'text-slate-400'}
                    `}>
                      {request.method}
                    </span>
                    {editingRequest?.id === request.id ? (
                      <input
                        autoFocus
                        value={editingRequestName}
                        onChange={(e) => setEditingRequestName(e.target.value)}
                        onBlur={handleConfirmRequestRename}
                        onClick={(e) => e.stopPropagation()}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.stopPropagation();
                            handleConfirmRequestRename();
                          }
                          if (e.key === 'Escape') {
                            e.stopPropagation();
                            setEditingRequest(null);
                            setEditingRequestName('');
                          }
                        }}
                        className="flex-1 bg-slate-900 text-white text-xs px-1 py-0.5 rounded
                                   border border-purple-500 focus:outline-none min-w-0"
                      />
                    ) : (
                      <>
                        <span className="truncate flex-1">{request.name}</span>
                        {onRequestRename && (
                          <button
                            title="重命名"
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingRequest(request);
                              setEditingRequestName(request.name);
                            }}
                            className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-slate-500 hover:text-slate-300 transition-opacity text-xs flex-shrink-0"
                          >
                            <i className="fas fa-pencil"></i>
                          </button>
                        )}
                        {onRequestDelete && (
                          <button
                            title="删除"
                            onClick={(e) => {
                              e.stopPropagation();
                              onRequestDelete(request);
                            }}
                            className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-slate-500 hover:text-red-400 transition-opacity text-xs flex-shrink-0"
                          >
                            <i className="fas fa-trash"></i>
                          </button>
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {isExpanded && children.map(child => renderCollection(child, level + 1))}
      </div>
    );
  };

  return (
    <div className="py-2">
      {rootCollections.map(collection => renderCollection(collection))}
    </div>
  );
}
