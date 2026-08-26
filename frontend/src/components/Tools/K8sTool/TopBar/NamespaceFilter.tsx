/**
 * K8s 控制台 - 命名空间过滤器
 *
 * 多选下拉，支持 "所有命名空间" 选项
 * 选中的命名空间用于过滤资源查询
 */
import React, { useState, useEffect } from 'react';
import { Filter, Search, X, Check, AlertTriangle, ChevronDown } from 'lucide-react';
import { useK8sStore } from '../../../../stores/k8sStore';
import { useK8sNamespaces } from '../../../../hooks/useK8sClient';
import { useI18n } from '../../../../i18n';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/Popover';

export const NamespaceFilter: React.FC = () => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const { activeConnectionId, namespaces, selectedNamespaces, setSelectedNamespaces, connections } = useK8sStore();

  const [isOpen, setIsOpen] = useState(false);
  const [searchText, setSearchText] = useState('');

  // 查询命名空间列表（自动同步到 store）
  const { isError } = useK8sNamespaces(activeConnectionId);

  // 当连接切换时，应用该连接的 namespace_filter 作为默认选择
  useEffect(() => {
    if (!activeConnectionId) return;

    const activeConnection = connections.find(c => c.id === activeConnectionId);
    if (activeConnection?.namespace_filter && activeConnection.namespace_filter.length > 0) {
      // 如果连接配置了 namespace_filter，自动应用它
      setSelectedNamespaces(activeConnection.namespace_filter);
    }
  }, [activeConnectionId, connections, setSelectedNamespaces]);

  /** 检查是否选中了"所有命名空间" */
  const isAllSelected = selectedNamespaces.length === 0;

  /** 切换"所有命名空间" */
  const toggleAll = () => {
    if (isAllSelected) {
      // 已选中"所有"，切换回 default
      setSelectedNamespaces(['default']);
    } else {
      // 选中"所有"
      setSelectedNamespaces([]);
    }
  };

  /** 切换单个命名空间 */
  const toggleNamespace = (ns: string) => {
    if (selectedNamespaces.includes(ns)) {
      const next = selectedNamespaces.filter((n) => n !== ns);
      // 至少保留一个，若取消到空则选所有
      setSelectedNamespaces(next.length === 0 ? [] : next);
    } else {
      setSelectedNamespaces([...selectedNamespaces, ns]);
    }
  };

  /** 显示文本 */
  const displayText = isAllSelected
    ? k8sT.topBar.allNamespaces
    : selectedNamespaces.length <= 2
      ? selectedNamespaces.join(', ')
      : `${selectedNamespaces.length} ${k8sT.topBar.namespaceFilter}`;

  /** 过滤后的命名空间列表 */
  const filteredNamespaces = searchText
    ? namespaces.filter((ns) => ns.toLowerCase().includes(searchText.toLowerCase()))
    : namespaces;

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <button
          aria-label="命名空间过滤"
          className="flex items-center gap-2 px-3 py-1.5 bg-surface-1 border border-border rounded-md text-sm text-ink hover:border-border transition-colors min-w-[150px] max-w-[240px]"
        >
          <Filter className="w-3 h-3 text-ink-muted" />
          <span className="truncate">{displayText}</span>
          <ChevronDown className={`w-3 h-3 ml-auto text-ink-muted transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-64 p-0 max-h-72 overflow-y-auto">
          {/* 搜索框 */}
          <div className="sticky top-0 bg-surface-1 border-b border-border p-2">
            <div className="flex items-center gap-2 px-2 py-1 bg-canvas border border-border rounded">
              <Search className="w-3 h-3 text-ink-faint" />
              <input
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="搜索命名空间..."
                className="flex-1 bg-transparent text-sm text-ink-muted placeholder:text-ink-faint focus:outline-none"
                onClick={(e) => e.stopPropagation()}
              />
              {searchText && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSearchText('');
                  }}
                  className="text-ink-faint hover:text-ink-muted"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          {/* "所有命名空间"选项 */}
          <div
            onClick={toggleAll}
            className={`flex items-center gap-2 px-3 py-2 cursor-pointer border-b border-border transition-colors ${
              isAllSelected
                ? 'bg-accent/20 text-accent-info'
                : 'text-ink-muted hover:bg-surface-2 hover:text-ink'
            }`}
          >
            <div className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
              isAllSelected ? 'bg-accent border-accent' : 'border-border'
            }`}>
              {isAllSelected && <Check className="w-2.5 h-2.5 text-ink-inverse" />}
            </div>
            <span className="text-sm font-medium">{k8sT.topBar.allNamespaces}</span>
          </div>

          {/* 命名空间列表 */}
          {filteredNamespaces.map((ns) => {
            const isChecked = selectedNamespaces.includes(ns);
            return (
              <div
                key={ns}
                onClick={() => toggleNamespace(ns)}
                className={`flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors ${
                  isChecked
                    ? 'bg-accent/20 text-accent-info'
                    : 'text-ink-muted hover:bg-surface-2 hover:text-ink'
                }`}
              >
                <div className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
                  isChecked ? 'bg-accent border-accent' : 'border-border'
                }`}>
                  {isChecked && <Check className="w-2.5 h-2.5 text-ink-inverse" />}
                </div>
                <span className="text-sm truncate">{ns}</span>
              </div>
            );
          })}

          {filteredNamespaces.length === 0 && searchText && (
            <div className="px-3 py-4 text-sm text-ink-faint text-center">
              未找到匹配的命名空间
            </div>
          )}

          {namespaces.length === 0 && (
            <div className="px-3 py-4 text-sm text-center">
              {isError ? (
                <div className="text-accent-warning">
                  <AlertTriangle className="w-4 h-4 mr-2" />
                  无法获取命名空间列表
                  <br />
                  <span className="text-xs text-ink-faint">
                    请在编辑配置时指定命名空间过滤
                  </span>
                </div>
              ) : (
                k8sT.emptyConnections
              )}
            </div>
          )}
      </PopoverContent>
    </Popover>
  );
};
