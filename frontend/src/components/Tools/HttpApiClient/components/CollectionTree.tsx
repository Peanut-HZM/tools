import { useState, useEffect } from 'react';
import { Collection, HttpRequest, fetchRequests } from '../../../../services/httpClientApi';
import { ChevronRight, Folder, Pencil, Trash2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

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
              ? 'bg-accent-secondary/20 border border-accent-secondary text-accent-secondary'
              : 'hover:bg-surface-2/50 border border-transparent text-ink-muted'
            }
          `}
          style={{ paddingLeft: level * 16 + 12 }}
          onClick={() => handleCollectionClick(collection)}
          onContextMenu={(e) => {
            e.preventDefault();
            onCollectionContextMenu?.(e, collection);
          }}
        >
          <Button
            variant="ghost"
            size="icon"
            title="展开/折叠"
            onClick={(e) => {
              e.stopPropagation();
              handleCollectionClick(collection);
            }}
            className="h-6 w-6 text-ink-faint hover:text-ink-muted"
          >
            <ChevronRight
              className={`w-3 h-3 transition-transform ${
                isExpanded ? 'rotate-90' : ''
              }`}
            />
          </Button>
          <Folder className="w-3 h-3 text-ink-faint" />
          <span className="truncate flex-1">{collection.name}</span>
          {onCollectionRename && (
            <Button
              variant="ghost"
              size="icon"
              title="重命名"
              onClick={(e) => {
                e.stopPropagation();
                onCollectionRename(collection);
              }}
              className="h-6 w-6 opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-ink-faint hover:text-ink-muted"
            >
              <Pencil className="w-3 h-3" />
            </Button>
          )}
          {onCollectionDelete && (
            <Button
              variant="ghost"
              size="icon"
              title="删除"
              onClick={(e) => {
                e.stopPropagation();
                onCollectionDelete(collection);
              }}
              className="h-6 w-6 opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-ink-faint hover:text-danger"
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          )}
        </div>

        {/* 请求列表 */}
        {isExpanded && (
          <div className="ml-4">
            {isLoading ? (
              <div className="py-2 text-xs text-ink-faint">
                <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                加载中...
              </div>
            ) : requests.length === 0 ? (
              <div className="py-2 text-xs text-ink-faint">
                暂无请求
              </div>
            ) : (
              <div className="mt-1 space-y-1">
                {requests.map(request => (
                  <div
                    key={request.id}
                    className="group flex items-center gap-2 px-3 py-1.5 cursor-pointer
                               hover:bg-surface-2/50 rounded text-xs text-ink-muted"
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
                        request.method === 'POST' ? 'text-accent-info' :
                        request.method === 'PUT' ? 'text-accent-warning' :
                        request.method === 'DELETE' ? 'text-danger' :
                        'text-ink-muted'}
                    `}>
                      {request.method}
                    </span>
                    {editingRequest?.id === request.id ? (
                      <Input
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
                        className="flex-1 h-6 text-xs px-1 py-0.5 min-w-0"
                      />
                    ) : (
                      <>
                        <span className="truncate flex-1">{request.name}</span>
                        {onRequestRename && (
                          <Button
                            variant="ghost"
                            size="icon"
                            title="重命名"
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingRequest(request);
                              setEditingRequestName(request.name);
                            }}
                            className="h-6 w-6 opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-ink-faint hover:text-ink-muted"
                          >
                            <Pencil className="w-3 h-3" />
                          </Button>
                        )}
                        {onRequestDelete && (
                          <Button
                            variant="ghost"
                            size="icon"
                            title="删除"
                            onClick={(e) => {
                              e.stopPropagation();
                              onRequestDelete(request);
                            }}
                            className="h-6 w-6 opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-ink-faint hover:text-danger"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
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
