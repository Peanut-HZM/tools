import { useState, useEffect, useCallback } from 'react';
import { DatabaseConfig } from '../../../../types/databaseTool';
import { Environment } from '../../../../types/databaseTool';
import { useI18n } from '../../../../i18n';
import * as api from '../../../../api/databaseToolApi';

interface DisplayPreferences {
  visible_connections: string[] | null;
  visible_databases: Record<string, string[]>;
}

interface DisplaySettingsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  configs: DatabaseConfig[];
  currentPreferences: DisplayPreferences | null;
  onSave: (preferences: DisplayPreferences) => Promise<void>;
}

/** 获取环境标签颜色 */
function getEnvBadgeClass(env?: Environment): string {
  switch (env) {
    case Environment.PROD: return 'bg-red-900/30 text-red-400 border border-red-800/50';
    case Environment.TEST: return 'bg-yellow-900/30 text-yellow-400 border border-yellow-800/50';
    case Environment.DEV: return 'bg-green-900/30 text-green-400 border border-green-800/50';
    default: return 'bg-slate-700 text-slate-400 border border-slate-600';
  }
}

export default function DisplaySettingsDialog({
  isOpen,
  onClose,
  configs,
  currentPreferences,
  onSave,
}: DisplaySettingsDialogProps) {
  const { t } = useI18n();

  // 本地勾选状态
  const [selectedConnections, setSelectedConnections] = useState<Set<string>>(new Set());
  const [selectedDatabases, setSelectedDatabases] = useState<Record<string, Set<string>>>({});

  // 每个连接的数据库列表加载状态
  const [databasesMap, setDatabasesMap] = useState<Record<string, string[]>>({});
  const [loadingConnections, setLoadingConnections] = useState<Set<string>>(new Set());

  // 展开的连接
  const [expandedConnections, setExpandedConnections] = useState<Set<string>>(new Set());

  // 搜索
  const [searchTerm, setSearchTerm] = useState('');

  // 保存中
  const [saving, setSaving] = useState(false);

  // 弹窗打开时初始化
  useEffect(() => {
    if (!isOpen) return;
    setSearchTerm('');
    setExpandedConnections(new Set());
    setDatabasesMap({});
    setLoadingConnections(new Set());

    // 初始化连接选择
    if (currentPreferences?.visible_connections) {
      setSelectedConnections(new Set(currentPreferences.visible_connections));
    } else {
      // null = 全部选中
      setSelectedConnections(new Set(configs.map(c => c.id)));
    }

    // 初始化数据库选择
    const dbSelection: Record<string, Set<string>> = {};
    if (currentPreferences?.visible_databases) {
      for (const [configId, dbs] of Object.entries(currentPreferences.visible_databases)) {
        dbSelection[configId] = new Set(dbs);
      }
    }
    setSelectedDatabases(dbSelection);
  }, [isOpen, configs, currentPreferences]);

  // 加载单个连接的数据库列表
  const loadDatabases = useCallback(async (configId: string) => {
    if (databasesMap[configId]) return; // 已加载过
    setLoadingConnections(prev => new Set(prev).add(configId));
    try {
      const dbs = await api.getDatabasesList(configId);
      setDatabasesMap(prev => ({ ...prev, [configId]: dbs }));
      // 初始化该连接的数据库选择
      if (!selectedDatabases[configId]) {
        if (currentPreferences?.visible_databases?.[configId]) {
          setSelectedDatabases(prev => ({
            ...prev,
            [configId]: new Set(currentPreferences.visible_databases[configId]),
          }));
        } else {
          setSelectedDatabases(prev => ({ ...prev, [configId]: new Set(dbs) }));
        }
      }
    } catch (err) {
      console.error(`Failed to load databases for ${configId}:`, err);
    } finally {
      setLoadingConnections(prev => {
        const next = new Set(prev);
        next.delete(configId);
        return next;
      });
    }
  }, [databasesMap, selectedDatabases, currentPreferences]);

  // 切换连接展开
  const toggleExpand = useCallback(async (configId: string) => {
    setExpandedConnections(prev => {
      const next = new Set(prev);
      if (next.has(configId)) {
        next.delete(configId);
      } else {
        next.add(configId);
        // 展开时加载数据库列表
        loadDatabases(configId);
      }
      return next;
    });
  }, [loadDatabases]);

  // 切换连接选中
  const toggleConnection = useCallback((configId: string) => {
    setSelectedConnections(prev => {
      const next = new Set(prev);
      if (next.has(configId)) {
        next.delete(configId);
      } else {
        next.add(configId);
      }
      return next;
    });
  }, []);

  // 切换数据库选中
  const toggleDatabase = useCallback((configId: string, dbName: string) => {
    setSelectedDatabases(prev => {
      const current = prev[configId] || new Set();
      const next = new Set(current);
      if (next.has(dbName)) {
        next.delete(dbName);
      } else {
        next.add(dbName);
      }
      return { ...prev, [configId]: next };
    });
  }, []);

  // 全选/取消全选当前连接的数据库
  const toggleAllDatabases = useCallback((configId: string, allDbs: string[]) => {
    setSelectedDatabases(prev => {
      const current = prev[configId] || new Set();
      const allSelected = allDbs.every(db => current.has(db));
      if (allSelected) {
        const { [configId]: _, ...rest } = prev;
        return rest;
      }
      return { ...prev, [configId]: new Set(allDbs) };
    });
  }, []);

  // 全选/取消全选连接
  const allSelected = selectedConnections.size === configs.length;
  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedConnections(new Set());
    } else {
      setSelectedConnections(new Set(configs.map(c => c.id)));
    }
  };

  // 重置
  const handleReset = () => {
    setSelectedConnections(new Set(configs.map(c => c.id)));
    setSelectedDatabases({});
    setExpandedConnections(new Set());
  };

  // 保存
  const handleSave = async () => {
    setSaving(true);
    try {
      // 如果全部选中，visible_connections 设为 null
      const allIds = configs.map(c => c.id);
      const visibleConn = selectedConnections.size === allIds.length && allIds.every(id => selectedConnections.has(id))
        ? null
        : Array.from(selectedConnections);

      // 构建 visible_databases
      const visibleDbs: Record<string, string[]> = {};
      for (const [configId, dbs] of Object.entries(selectedDatabases)) {
        const allDbs = databasesMap[configId];
        if (allDbs && dbs.size === allDbs.length) {
          // 全部选中则不存（表示显示全部）
          continue;
        }
        if (dbs.size > 0) {
          visibleDbs[configId] = Array.from(dbs);
        }
      }

      await onSave({ visible_connections: visibleConn, visible_databases: visibleDbs });
      onClose();
    } catch (err) {
      console.error('Failed to save preferences:', err);
    } finally {
      setSaving(false);
    }
  };

  // 搜索过滤
  const filteredConfigs = configs.filter(config =>
    config.alias.toLowerCase().includes(searchTerm.toLowerCase()) ||
    config.host.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // ESC 关闭
  useEffect(() => {
    if (!isOpen) return;
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[100]">
      <div
        className="bg-slate-800 rounded-lg shadow-xl w-full max-w-lg border border-slate-700 flex flex-col max-h-[85vh]"
        role="dialog"
        aria-label="显示设置"
      >
        {/* 标题栏 */}
        <div className="flex justify-between items-center p-4 border-b border-slate-700">
          <h3 className="text-lg font-medium text-slate-100">
            <i className="fas fa-cog mr-2 text-slate-400"></i>
            显示设置
          </h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 transition-colors p-1"
            aria-label="关闭"
          >
            <i className="fas fa-times"></i>
          </button>
        </div>

        {/* 搜索框 */}
        <div className="px-4 pt-3">
          <div className="relative">
            <i className="fas fa-search absolute left-3 top-2.5 text-slate-500 text-sm"></i>
            <input
              type="text"
              placeholder="搜索连接名称或主机..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-md py-2 pl-9 pr-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="搜索连接"
            />
          </div>
        </div>

        {/* 连接列表 */}
        <div className="flex-1 overflow-y-auto p-4 pt-2 space-y-1">
          {/* 全选 */}
          <div className="flex items-center space-x-2 pb-2 mb-2 border-b border-slate-700/50">
            <input
              type="checkbox"
              id="select-all-conn"
              checked={allSelected}
              onChange={toggleSelectAll}
              className="rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-800"
            />
            <label htmlFor="select-all-conn" className="text-sm font-medium text-slate-300 cursor-pointer select-none">
              全选
            </label>
            <span className="text-xs text-slate-500 ml-auto">
              {selectedConnections.size} / {configs.length}
            </span>
          </div>

          {filteredConfigs.length === 0 ? (
            <div className="text-center text-slate-500 py-8 text-sm">
              <i className="fas fa-search mb-2 block text-lg opacity-50"></i>
              未找到匹配的连接
            </div>
          ) : (
            filteredConfigs.map(config => {
              const isConnSelected = selectedConnections.has(config.id);
              const isExpanded = expandedConnections.has(config.id);
              const allDbs = databasesMap[config.id];
              const isLoading = loadingConnections.has(config.id);
              const connDbSelection = selectedDatabases[config.id];
              const allDbsSelected = allDbs ? allDbs.every(db => connDbSelection?.has(db)) : false;
              const someDbsSelected = allDbs ? allDbs.some(db => connDbSelection?.has(db)) : false;

              return (
                <div key={config.id}>
                  {/* 连接行 */}
                  <div
                    className={`
                      flex items-center gap-2 px-2 py-2 rounded-md cursor-pointer transition-colors duration-200
                      ${isConnSelected
                        ? 'bg-blue-500/10 border border-blue-500/30'
                        : 'hover:bg-slate-700/50 border border-transparent'
                      }
                    `}
                  >
                    {/* 展开箭头 */}
                    <button
                      onClick={(e) => { e.stopPropagation(); toggleExpand(config.id); }}
                      className="text-slate-500 hover:text-slate-300 transition-colors p-0.5"
                      aria-label={isExpanded ? '收起' : '展开'}
                    >
                      <i
                        className={`fas fa-chevron-right text-xs transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
                      ></i>
                    </button>

                    {/* 连接复选框 */}
                    <input
                      type="checkbox"
                      checked={isConnSelected}
                      onChange={() => toggleConnection(config.id)}
                      className="rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-800 cursor-pointer"
                    />

                    {/* 连接信息 */}
                    <span className="text-sm text-slate-300 flex-1 truncate">{config.alias}</span>

                    {/* 环境标签 */}
                    {config.environment && (
                      <span className={`text-xs px-1.5 py-0.5 rounded ${getEnvBadgeClass(config.environment)}`}>
                        {config.environment}
                      </span>
                    )}
                  </div>

                  {/* 数据库列表（展开时） */}
                  {isExpanded && (
                    <div className="ml-8 mt-1 mb-1 space-y-0.5">
                      {isLoading ? (
                        <div className="py-2 text-xs text-slate-500">
                          <i className="fas fa-spinner fa-spin mr-1"></i>
                          加载中...
                        </div>
                      ) : allDbs ? (
                        <>
                          {/* 数据库全选 */}
                          <div className="flex items-center space-x-2 px-2 py-1">
                            <input
                              type="checkbox"
                              id={`db-all-${config.id}`}
                              checked={allDbsSelected}
                              ref={input => { if (input) input.indeterminate = someDbsSelected && !allDbsSelected; }}
                              onChange={() => toggleAllDatabases(config.id, allDbs)}
                              className="rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-800"
                            />
                            <label htmlFor={`db-all-${config.id}`} className="text-xs text-slate-400 cursor-pointer select-none">
                              全选
                            </label>
                            <span className="text-xs text-slate-600 ml-auto">
                              {connDbSelection?.size || 0} / {allDbs.length}
                            </span>
                          </div>

                          {/* 数据库项 */}
                          {allDbs.map(db => (
                            <div
                              key={db}
                              className="flex items-center space-x-2 px-2 py-1 rounded hover:bg-slate-700/30 cursor-pointer transition-colors"
                              onClick={() => toggleDatabase(config.id, db)}
                            >
                              <input
                                type="checkbox"
                                checked={connDbSelection?.has(db) || false}
                                onChange={() => {}}
                                className="rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-800 pointer-events-none"
                              />
                              <span className="text-xs text-slate-400 truncate flex-1">{db}</span>
                              <i className="fas fa-database text-slate-600 text-xs"></i>
                            </div>
                          ))}
                        </>
                      ) : (
                        <div className="py-2 text-xs text-slate-500">
                          暂无数据库
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* 底部按钮 */}
        <div className="p-4 border-t border-slate-700 flex justify-between items-center bg-slate-800/50">
          <button
            onClick={handleReset}
            disabled={saving}
            className="px-3 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors disabled:opacity-50 cursor-pointer"
          >
            <i className="fas fa-undo mr-1"></i>
            重置
          </button>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-700 rounded-md transition-colors disabled:opacity-50"
            >
              {t.common.cancel}
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md shadow-sm transition-colors disabled:opacity-50"
            >
              {saving ? (
                <>
                  <i className="fas fa-spinner fa-spin mr-1"></i>
                  保存中...
                </>
              ) : (
                <>
                  <i className="fas fa-check mr-1"></i>
                  {t.common.confirm}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
