/**
 * K8s 控制台 - 命名空间过滤器
 *
 * 多选下拉，支持 "所有命名空间" 选项
 * 选中的命名空间用于过滤资源查询
 */
import React, { useState, useRef, useEffect } from 'react';
import { useK8sStore } from '../../../../stores/k8sStore';
import { useK8sNamespaces } from '../../../../hooks/useK8sClient';
import { useI18n } from '../../../../i18n';

export const NamespaceFilter: React.FC = () => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const { activeConnectionId, namespaces, selectedNamespaces, setSelectedNamespaces, connections } = useK8sStore();

  const [isOpen, setIsOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

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

  // 点击外部关闭下拉
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
    <div ref={dropdownRef} className="relative">
      {/* 触发按钮 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 border border-slate-600 rounded-md text-sm text-slate-200 hover:border-slate-500 transition-colors min-w-[150px] max-w-[240px]"
      >
        <i className="fas fa-filter text-xs text-slate-400"></i>
        <span className="truncate">{displayText}</span>
        <i className={`fas fa-chevron-down ml-auto text-xs text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}></i>
      </button>

      {/* 下拉菜单 */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-64 max-h-72 overflow-y-auto bg-slate-800 border border-slate-600 rounded-md shadow-lg z-50">
          {/* 搜索框 */}
          <div className="sticky top-0 bg-slate-800 border-b border-slate-700 p-2">
            <div className="flex items-center gap-2 px-2 py-1 bg-slate-900 border border-slate-700 rounded">
              <i className="fas fa-search text-xs text-slate-500"></i>
              <input
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="搜索命名空间..."
                className="flex-1 bg-transparent text-sm text-slate-300 placeholder-slate-600 focus:outline-none"
                onClick={(e) => e.stopPropagation()}
              />
              {searchText && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSearchText('');
                  }}
                  className="text-slate-500 hover:text-slate-300"
                >
                  <i className="fas fa-times text-xs"></i>
                </button>
              )}
            </div>
          </div>

          {/* "所有命名空间"选项 */}
          <div
            onClick={toggleAll}
            className={`flex items-center gap-2 px-3 py-2 cursor-pointer border-b border-slate-700 transition-colors ${
              isAllSelected
                ? 'bg-blue-600/20 text-blue-300'
                : 'text-slate-300 hover:bg-slate-700 hover:text-white'
            }`}
          >
            <div className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
              isAllSelected ? 'bg-blue-500 border-blue-400' : 'border-slate-500'
            }`}>
              {isAllSelected && <i className="fas fa-check text-[10px] text-white"></i>}
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
                    ? 'bg-blue-600/20 text-blue-300'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                }`}
              >
                <div className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
                  isChecked ? 'bg-blue-500 border-blue-400' : 'border-slate-500'
                }`}>
                  {isChecked && <i className="fas fa-check text-[10px] text-white"></i>}
                </div>
                <span className="text-sm truncate">{ns}</span>
              </div>
            );
          })}

          {filteredNamespaces.length === 0 && searchText && (
            <div className="px-3 py-4 text-sm text-slate-500 text-center">
              未找到匹配的命名空间
            </div>
          )}

          {namespaces.length === 0 && (
            <div className="px-3 py-4 text-sm text-center">
              {isError ? (
                <div className="text-yellow-400">
                  <i className="fas fa-exclamation-triangle mr-2"></i>
                  无法获取命名空间列表
                  <br />
                  <span className="text-xs text-slate-500">
                    请在编辑配置时指定命名空间过滤
                  </span>
                </div>
              ) : (
                k8sT.emptyConnections
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
