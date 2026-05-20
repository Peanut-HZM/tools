import React, { useState, useEffect, useRef } from 'react';
import { useDatabaseTool } from '../../../../contexts/DatabaseToolContext';
import { DatabaseConfig, Environment, DatabaseStructure, TableItem, TableDetailResponse } from '../../../../types/databaseTool';
import { useI18n } from '../../../../i18n';
import * as api from '../../../../api/databaseToolApi';
import DatabaseFilterDialog from './DatabaseFilterDialog';
import { ContextMenu, MenuItem } from '../../../../components/Common/ContextMenu';
import CreateDatabaseDialog from './CreateDatabaseDialog';
import ModifyTableDialog from './ModifyTableDialog';
import DDLDialog from './DDLDialog';
import BackupDialog from './BackupDialog';
import BackupHistoryDialog from './BackupHistoryDialog';
import DisplaySettingsDialog from './DisplaySettingsDialog';
import SchemaNode from './SchemaNode';
import { DisplayPreferences } from '../../../../types/databaseTool';

interface ConnectionListProps {
  onAddConfig: () => void;
  onEditConfig: (id: string) => void;
  onSelectTable: (configId: string, databaseName: string | undefined, tableName: string, schemaName?: string) => void;
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string, configId?: string) => void;
  activeConfigId?: string;
  activeDatabaseName?: string;
  onConnectionSelect?: (configId: string, databaseName?: string) => void;
}

const ConnectionList: React.FC<ConnectionListProps> = ({ onAddConfig, onEditConfig, onSelectTable, onOpenSqlConsole, activeConfigId, activeDatabaseName, onConnectionSelect }) => {
  const { configs, currentConfig, selectConfigById, setCurrentDatabase, refreshConfigs, isLoading } = useDatabaseTool();
  const { t } = useI18n();
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});
  const [searchTerm, setSearchTerm] = useState('');

  // 右→左联动：活跃Tab连接变化时自动展开
  useEffect(() => {
    if (activeConfigId && !expandedNodes[activeConfigId]) {
      setExpandedNodes(prev => ({ ...prev, [activeConfigId]: true }));
    }
  }, [activeConfigId]);

  // Backup dialog states
  const [backupDialogOpen, setBackupDialogOpen] = useState(false);
  const [backupDialogConfigId, setBackupDialogConfigId] = useState<string>('');
  const [backupDialogDbName, setBackupDialogDbName] = useState<string>('');
  const [backupDialogTables, setBackupDialogTables] = useState<string[] | undefined>(undefined);

  const [backupHistoryOpen, setBackupHistoryOpen] = useState(false);
  const [backupHistoryConfigId, setBackupHistoryConfigId] = useState<string>('');
  const [backupHistoryDbName, setBackupHistoryDbName] = useState<string | undefined>(undefined);

  // 显示偏好
  const [displayPreferences, setDisplayPreferences] = useState<DisplayPreferences | null>(null);
  const [showDisplaySettings, setShowDisplaySettings] = useState(false);

  // 加载显示偏好
  useEffect(() => {
    api.getDisplayPreferences()
      .then(setDisplayPreferences)
      .catch(() => setDisplayPreferences(null));
  }, []);

  // 根据偏好过滤连接
  const filteredConfigs = displayPreferences?.visible_connections
    ? configs.filter(c => displayPreferences.visible_connections!.includes(c.id))
    : configs;

  const toggleExpand = (nodeId: string) => {
    setExpandedNodes(prev => ({ ...prev, [nodeId]: !prev[nodeId] }));
  };

  const handleSelectDatabase = (configId: string, dbName: string) => {
    if (onConnectionSelect) {
      onConnectionSelect(configId, dbName);
    } else {
      if (currentConfig?.id !== configId) {
        selectConfigById(configId);
      }
      setCurrentDatabase(dbName);
    }
  };

  const getEnvColor = (env?: Environment) => {
    switch (env) {
      case Environment.PROD: return 'bg-red-900/30 text-red-400 border border-red-800/50';
      case Environment.TEST: return 'bg-yellow-900/30 text-yellow-400 border border-yellow-800/50';
      case Environment.DEV: return 'bg-green-900/30 text-green-400 border border-green-800/50';
      default: return 'bg-slate-700 text-slate-400 border border-slate-600';
    }
  };

  const handleOpenBackup = (configId: string, dbName: string, tables?: string[]) => {
    setBackupDialogConfigId(configId);
    setBackupDialogDbName(dbName);
    setBackupDialogTables(tables);
    setBackupDialogOpen(true);
  };

  const handleOpenBackupHistory = (configId: string, dbName?: string) => {
    setBackupHistoryConfigId(configId);
    setBackupHistoryDbName(dbName);
    setBackupHistoryOpen(true);
  };

  return (
    <div className="flex flex-col h-full bg-slate-800 border-r border-slate-700">
      <div className="p-4 border-b border-slate-700 flex flex-col gap-2 bg-slate-800">
        <div className="flex justify-between items-center">
            <h2 className="font-semibold text-slate-100">{t.database.connections}</h2>
            <div className="flex space-x-1">
            <button
                onClick={() => setShowDisplaySettings(true)}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
                title="显示设置"
                aria-label="显示设置"
            >
                <i className="fas fa-cog"></i>
            </button>
            {onOpenSqlConsole && (
                <button
                onClick={() => onOpenSqlConsole()}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
                title={t.database.executor.title}
                >
                <i className="fas fa-terminal"></i>
                </button>
            )}
            <button
                onClick={onAddConfig}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
                title={t.database.addConnection}
            >
                <i className="fas fa-plus"></i>
            </button>
            </div>
        </div>

        {/* Search Input */}
        <div className="relative">
             <i className="fas fa-search absolute left-2 top-1/2 transform -translate-y-1/2 text-slate-500 text-xs"></i>
             <input
                 type="text"
                 value={searchTerm}
                 onChange={(e) => setSearchTerm(e.target.value)}
                 placeholder={t.common.search}
                 className="w-full bg-slate-900 border border-slate-700 rounded pl-7 pr-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-blue-500"
             />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {/* Skeleton loading placeholder */}
        {isLoading && configs.length === 0 && (
          <div className="space-y-1">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="p-2 rounded-md flex items-center space-x-2 animate-pulse">
                <div className="w-6 h-6 bg-slate-700 rounded"></div>
                <div className="w-5 h-5 bg-slate-700 rounded"></div>
                <div className="flex-1 h-4 bg-slate-700 rounded"></div>
              </div>
            ))}
          </div>
        )}

        {filteredConfigs.map(config => (
          <ConnectionNode
            key={config.id}
            config={config}
            isExpanded={!!expandedNodes[config.id]}
            onToggleExpand={() => toggleExpand(config.id)}
            isSelected={activeConfigId === config.id || currentConfig?.id === config.id}
            onSelect={() => onConnectionSelect ? onConnectionSelect(config.id) : selectConfigById(config.id)}
            onEdit={() => onEditConfig(config.id)}
            onSelectTable={onSelectTable}
            onSelectDatabase={handleSelectDatabase}
            getEnvColor={getEnvColor}
            onRefreshConfigs={refreshConfigs}
            onOpenSqlConsole={onOpenSqlConsole}
            onOpenBackup={handleOpenBackup}
            onOpenBackupHistory={handleOpenBackupHistory}
            searchTerm={searchTerm}
            displayPreferences={displayPreferences}
            activeDatabaseName={activeDatabaseName}
          />
        ))}

        {configs.length === 0 && !isLoading && (
          <div className="text-center text-slate-500 py-8 text-sm flex flex-col items-center gap-2">
            <i className="fas fa-database text-2xl mb-2 opacity-50"></i>
            <p>{t.database.status.disconnected}</p>
            <p className="text-xs opacity-70">{t.common.create}</p>
          </div>
        )}
      </div>

      {/* Backup Dialog */}
      <BackupDialog
        isOpen={backupDialogOpen}
        onClose={() => setBackupDialogOpen(false)}
        configId={backupDialogConfigId}
        databaseName={backupDialogDbName}
        preselectedTables={backupDialogTables}
      />

      {/* Backup History Dialog */}
      <BackupHistoryDialog
        isOpen={backupHistoryOpen}
        onClose={() => setBackupHistoryOpen(false)}
        configId={backupHistoryConfigId}
        databaseName={backupHistoryDbName}
      />

      {/* 显示设置弹窗 */}
      <DisplaySettingsDialog
        isOpen={showDisplaySettings}
        onClose={() => setShowDisplaySettings(false)}
        configs={configs}
        currentPreferences={displayPreferences}
        onSave={async (prefs) => {
          await api.saveDisplayPreferences(prefs);
          setDisplayPreferences(prefs);
        }}
      />
    </div>
  );
};

interface ConnectionNodeProps {
  config: DatabaseConfig;
  isExpanded: boolean;
  onToggleExpand: () => void;
  isSelected: boolean;
  onSelect: () => void;
  onEdit: () => void;
  onSelectTable: (configId: string, databaseName: string | undefined, tableName: string, schemaName?: string) => void;
  onSelectDatabase: (configId: string, dbName: string) => void;
  getEnvColor: (env?: Environment) => string;
  onRefreshConfigs: () => Promise<void>;
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string, configId?: string) => void;
  onOpenBackup: (configId: string, dbName: string, tables?: string[]) => void;
  onOpenBackupHistory: (configId: string, dbName?: string) => void;
  searchTerm: string;
  displayPreferences?: DisplayPreferences | null;
  activeDatabaseName?: string;
}

const ConnectionNode: React.FC<ConnectionNodeProps> = ({
  config, isExpanded, onToggleExpand, isSelected, onSelect, onEdit, onSelectTable, onSelectDatabase, getEnvColor, onRefreshConfigs, onOpenSqlConsole, onOpenBackup, onOpenBackupHistory, searchTerm, displayPreferences, activeDatabaseName
}) => {
  const { t } = useI18n();
  const [databases, setDatabases] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [filterDialogOpen, setFilterDialogOpen] = useState(false);
  const [visibleDatabases, setVisibleDatabases] = useState<string[] | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; items: MenuItem[] } | null>(null);
  const [createDbDialogOpen, setCreateDbDialogOpen] = useState(false);

  // Search results from backend: { database: table_list }
  const [searchResults, setSearchResults] = useState<Record<string, string[]>>({});
  const [searching, setSearching] = useState(false);

  // Hover prefetch
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prefetchedRef = useRef(false);

  const handleMouseEnter = () => {
    if (prefetchedRef.current || config.database_name) return;
    hoverTimerRef.current = setTimeout(() => {
      prefetchedRef.current = true;
      api.getDatabasesList(config.id).catch(() => {});
    }, 300);
  };

  const handleMouseLeave = () => {
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);
    };
  }, []);

  useEffect(() => {
    const savedFilter = localStorage.getItem(`db_filter_${config.id}`);
    if (savedFilter) {
      try {
        setVisibleDatabases(JSON.parse(savedFilter));
      } catch (e) {
        console.error("Failed to parse saved filter", e);
      }
    }
  }, [config.id]);

  useEffect(() => {
      let active = true;
      const search = async () => {
          if (!searchTerm || searchTerm.length < 2) {
              setSearchResults({});
              return;
          }

          setSearching(true);
          try {
              const results = await api.searchTables(config.id, searchTerm);

              if (active) {
                  const grouped: Record<string, string[]> = {};
                  results.forEach(r => {
                      if (!grouped[r.database]) {
                          grouped[r.database] = [];
                      }
                      grouped[r.database].push(r.table);
                  });
                  setSearchResults(grouped);

                  if (results.length > 0 && !isExpanded) {
                      onToggleExpand();
                  }

                  if (results.length > 0 && !loaded && !config.database_name) {
                      fetchDatabases();
                  }
              }
          } catch (err) {
              console.error("Search failed", err);
          } finally {
              if (active) setSearching(false);
          }
      };

      const timeoutId = setTimeout(search, 500);
      return () => {
          active = false;
          clearTimeout(timeoutId);
      };
  }, [searchTerm, config.id]);

  const fetchDatabases = async () => {
    setLoading(true);
    try {
      const dbs = await api.getDatabasesList(config.id);
      setDatabases(dbs);
      setLoaded(true);
      return dbs;
    } catch (err) {
      console.error("Failed to load databases", err);
      return [];
    } finally {
      setLoading(false);
    }
  };

  const handleExpand = async (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleExpand();

    if (!isExpanded && !loaded && !config.database_name) {
      await fetchDatabases();
    }
  };

  const handleFilterClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!loaded) {
      await fetchDatabases();
    }
    setFilterDialogOpen(true);
  };

  const handleApplyFilter = (visible: string[] | null) => {
    setVisibleDatabases(visible);
    if (visible === null) {
      localStorage.removeItem(`db_filter_${config.id}`);
    } else {
      localStorage.setItem(`db_filter_${config.id}`, JSON.stringify(visible));
    }
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const dbName = config.database_name;

    const items: MenuItem[] = [
      {
        label: t.database.contextMenu.newSqlConsole || 'New SQL Console',
        icon: 'fa-terminal',
        action: () => {
          if (onOpenSqlConsole) {
            onOpenSqlConsole('', undefined, config.id);
          }
        }
      },
      {
        label: t.database.contextMenu.editConnection,
        icon: 'fa-edit',
        action: onEdit
      },
      {
        label: t.database.contextMenu.testConnection,
        icon: 'fa-plug',
        action: async () => {
            const result = await api.testConnectionById(config.id);
            alert(`${result.success ? t.common.success : t.common.error}: ${result.message}`);
        }
      },
      {
        label: t.database.contextMenu.refreshConnection,
        icon: 'fa-sync',
        action: async () => {
            await fetchDatabases();
            await onRefreshConfigs();
        }
      },
      {
          separator: true,
          label: '',
          action: () => {}
      },
      {
        label: t.database.contextMenu.backupDatabase,
        icon: 'fa-archive',
        action: () => {
          if (dbName) {
            onOpenBackup(config.id, dbName);
          }
        },
        disabled: !dbName
      },
      {
        label: t.database.contextMenu.backupHistory,
        icon: 'fa-history',
        action: () => onOpenBackupHistory(config.id, dbName || undefined)
      },
      {
          separator: true,
          label: '',
          action: () => {}
      },
      {
        label: t.database.contextMenu.newDatabase,
        icon: 'fa-plus',
        action: () => setCreateDbDialogOpen(true),
      },
      {
        label: t.database.contextMenu.deleteConnection,
        icon: 'fa-trash',
        danger: true,
        action: async () => {
            if (window.confirm(t.database.contextMenu.confirmDeleteConnection)) {
                await api.deleteDatabase(config.id);
                await onRefreshConfigs();
            }
        }
      }
    ];

    setContextMenu({ x: e.clientX, y: e.clientY, items });
  };

  const handleCreateDatabase = async (name: string, charset: string) => {
      await api.createDatabaseInstance(config.id, name, charset);
      await fetchDatabases();
  };

  // 先应用本地 filter（DatabaseFilterDialog）
  const locallyFiltered = visibleDatabases
    ? databases.filter(db => visibleDatabases.includes(db))
    : databases;

  // 再应用显示偏好过滤
  const prefDbs = displayPreferences?.visible_databases?.[config.id];
  const databasesToShow = prefDbs
    ? locallyFiltered.filter(db => prefDbs.includes(db))
    : locallyFiltered;

  const filteredDatabases = searchTerm
      ? databases.filter(db => {
          if (db.toLowerCase().includes(searchTerm.toLowerCase())) return true;
          if (searchResults[db] && searchResults[db].length > 0) return true;
          return false;
      })
      : databasesToShow;

  return (
    <div className="select-none">
      <div
        className={`p-2 rounded-md cursor-pointer group flex items-center justify-between transition-colors ${
          isSelected ? 'bg-blue-600/20 text-blue-100 border border-blue-600/50' : 'text-slate-300 hover:bg-slate-700/50 border border-transparent'
        }`}
        onClick={onSelect}
        onContextMenu={handleContextMenu}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <div className="flex items-center space-x-2 flex-1 min-w-0">
           <button
             onClick={handleExpand}
             className="p-1 hover:bg-slate-600 rounded text-slate-400 w-6 h-6 flex items-center justify-center"
           >
             {loading ? (
               <i className="fas fa-spinner fa-spin text-xs"></i>
             ) : (
               <i className={`fas fa-chevron-right text-xs transition-transform ${isExpanded ? 'rotate-90' : ''}`}></i>
             )}
           </button>

           <i className="fas fa-database text-slate-400"></i>

           <div className="flex-1 min-w-0">
             <div className="flex items-center space-x-2">
                <span className="font-medium truncate text-sm">{config.alias}</span>
                {config.environment && (
                  <span className={`text-[10px] px-1.5 py-0 rounded font-medium ${getEnvColor(config.environment)}`}>
                    {config.environment}
                  </span>
                )}
             </div>
           </div>
        </div>

        <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {!config.database_name && (
            <button
                onClick={handleFilterClick}
                className={`p-1.5 rounded transition-all ${
                   visibleDatabases ? 'text-blue-400 hover:text-blue-300' : (isSelected ? 'text-blue-100 hover:bg-blue-500' : 'text-slate-400 hover:text-white hover:bg-slate-600')
                }`}
                title={t.common.filter}
              >
                <i className="fas fa-filter text-xs"></i>
              </button>
          )}

          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className={`p-1.5 rounded transition-all ${
              isSelected ? 'text-blue-100 hover:bg-blue-500' : 'text-slate-400 hover:text-white hover:bg-slate-600'
            }`}
            title={t.common.edit}
          >
            <i className="fas fa-edit text-xs"></i>
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="ml-4 pl-2 border-l border-slate-700 mt-1 space-y-1">
          {config.db_type === 'postgresql' ? (
            // PostgreSQL: 渲染 Schema 层级
            <>
              {config.database_name ? (
                // 已指定 database_name，databases 是 schema 列表
                filteredDatabases.map(schema => (
                  <SchemaNode
                    key={schema}
                    configId={config.id}
                    dbName={config.database_name}
                    schemaName={schema}
                    onSelectTable={(table) => onSelectTable(config.id, config.database_name, table, schema)}
                    onSelectSchema={() => onSelectDatabase(config.id, config.database_name!)}
                    onOpenSqlConsole={onOpenSqlConsole}
                    onOpenBackup={(dbName, tables) => onOpenBackup(config.id, dbName, tables)}
                    onOpenBackupHistory={(dbName) => onOpenBackupHistory(config.id, dbName)}
                    searchTerm={searchTerm}
                    activeSchemaName={activeDatabaseName}
                  />
                ))
              ) : (
                // 未指定 database_name，databases 是 "database:schema" 格式
                (() => {
                  // 按数据库分组
                  const grouped: Record<string, string[]> = {};
                  filteredDatabases.forEach(dbEntry => {
                    const parts = dbEntry.split(':');
                    if (parts.length === 2) {
                      const [dbName, schemaName] = parts;
                      if (!grouped[dbName]) grouped[dbName] = [];
                      grouped[dbName].push(schemaName);
                    } else {
                      // 兼容没有冒号的条目
                      const fallbackDb = config.database_name || dbEntry;
                      if (!grouped[fallbackDb]) grouped[fallbackDb] = [];
                      grouped[fallbackDb].push(dbEntry);
                    }
                  });

                  return Object.entries(grouped).map(([dbName, schemas]) => (
                    <PostgresDatabaseNode
                      key={dbName}
                      configId={config.id}
                      dbName={dbName}
                      schemaNames={schemas}
                      onSelectTable={onSelectTable}
                      onSelectDatabase={onSelectDatabase}
                      onOpenSqlConsole={onOpenSqlConsole}
                      onOpenBackup={(d, tables) => onOpenBackup(config.id, d, tables)}
                      onOpenBackupHistory={(d) => onOpenBackupHistory(config.id, d)}
                      searchTerm={searchTerm}
                      activeDatabaseName={activeDatabaseName}
                    />
                  ));
                })()
              )}
              {databases.length === 0 && !loading && (
                <div className="text-xs text-slate-500 py-1 px-2 italic">{t.search.noResults}</div>
              )}
            </>
          ) : (
            // 其他数据库: 保持原有逻辑
            <>
              {config.database_name ? (
                <DatabaseStructureNode
                    configId={config.id}
                    dbName={config.database_name}
                    onSelectTable={(table) => onSelectTable(config.id, config.database_name, table)}
                    onSelectDatabase={() => onSelectDatabase(config.id, config.database_name!)}
                    onOpenSqlConsole={onOpenSqlConsole}
                    onOpenBackup={(dbName, tables) => onOpenBackup(config.id, dbName, tables)}
                    onOpenBackupHistory={(dbName) => onOpenBackupHistory(config.id, dbName)}
                    searchTerm={searchTerm}
                    activeDatabaseName={activeDatabaseName}
                />
              ) : (
                <>
                  {filteredDatabases.map(db => (
                    <DatabaseStructureNode
                        key={db}
                        configId={config.id}
                        dbName={db}
                        onSelectTable={(table) => onSelectTable(config.id, db, table)}
                        onSelectDatabase={() => onSelectDatabase(config.id, db)}
                        onRefreshDatabases={fetchDatabases}
                        onOpenSqlConsole={onOpenSqlConsole}
                        onOpenBackup={(dbName, tables) => onOpenBackup(config.id, dbName, tables)}
                        onOpenBackupHistory={(dbName) => onOpenBackupHistory(config.id, dbName)}
                        searchTerm={searchTerm}
                        activeDatabaseName={activeDatabaseName}
                    />
                  ))}
                  {databases.length === 0 && !loading && (
                     <div className="text-xs text-slate-500 py-1 px-2 italic">{t.search.noResults}</div>
                  )}
                  {databases.length > 0 && databasesToShow.length === 0 && (
                     <div className="text-xs text-slate-500 py-1 px-2 italic">
                       {t.database.status.hiddenByFilter}
                       <button
                         onClick={handleFilterClick}
                         className="ml-2 text-blue-400 hover:underline"
                       >
                         {t.database.executor.clear}
                       </button>
                     </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      )}

      <DatabaseFilterDialog
        isOpen={filterDialogOpen}
        onClose={() => setFilterDialogOpen(false)}
        allDatabases={databases}
        visibleDatabases={visibleDatabases}
        onApply={handleApplyFilter}
      />

      <CreateDatabaseDialog
        isOpen={createDbDialogOpen}
        onClose={() => setCreateDbDialogOpen(false)}
        onSubmit={handleCreateDatabase}
      />

      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={contextMenu.items}
          onClose={() => setContextMenu(null)}
        />
      )}
    </div>
  );
};

interface DatabaseStructureNodeProps {
  configId: string;
  dbName: string;
  onSelectTable: (tableName: string) => void;
  onSelectDatabase: () => void;
  onRefreshDatabases?: () => Promise<string[]>;
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string, configId?: string) => void;
  onOpenBackup: (dbName: string, tables?: string[]) => void;
  onOpenBackupHistory: (dbName: string) => void;
  searchTerm: string;
  activeDatabaseName?: string;
}

const DatabaseStructureNode: React.FC<DatabaseStructureNodeProps> = ({ configId, dbName, onSelectTable, onSelectDatabase, onRefreshDatabases, onOpenSqlConsole, onOpenBackup, onOpenBackupHistory, searchTerm, activeDatabaseName }) => {
  const { t } = useI18n();
  const [isExpanded, setIsExpanded] = useState(false);
  const [structure, setStructure] = useState<DatabaseStructure | null>(null);
  const [loading, setLoading] = useState(false);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; items: MenuItem[] } | null>(null);

  const [dbDdl, setDbDdl] = useState<string | null>(null);

  const fetchStructure = async () => {
    setLoading(true);
    try {
      const data = await api.getDatabaseStructure(configId, dbName);
      setStructure(data);
      return data;
    } catch (err) {
      console.error("Failed to load structure", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
      if (searchTerm && !structure && !loading) {
          fetchStructure().then(() => setIsExpanded(true));
      } else if (searchTerm && structure && !isExpanded) {
          setIsExpanded(true);
      }
  }, [searchTerm]);

  const handleToggle = async (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectDatabase();

    const nextState = !isExpanded;
    setIsExpanded(nextState);

    if (nextState && !structure) {
        await fetchStructure();
    }
  };

  const handleTableClick = (table: string) => {
    onSelectDatabase();
    onSelectTable(table);
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onSelectDatabase();

    const items: MenuItem[] = [
      {
        label: t.database.contextMenu.newSqlConsole || 'New SQL Console',
        icon: 'fa-terminal',
        action: () => {
          if (onOpenSqlConsole) {
            onOpenSqlConsole('', dbName, configId);
          }
        }
      },
      {
        label: t.database.contextMenu.newTable,
        icon: 'fa-plus',
        action: () => {
             if (onOpenSqlConsole) {
                 const template = `CREATE TABLE new_table (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`;
                  onOpenSqlConsole(template, dbName, configId);
             }
        }
      },
      {
          separator: true,
          label: '',
          action: () => {}
      },
      {
        label: t.database.contextMenu.backupDatabase,
        icon: 'fa-archive',
        action: () => onOpenBackup(dbName)
      },
      {
        label: t.database.contextMenu.backupHistory,
        icon: 'fa-history',
        action: () => onOpenBackupHistory(dbName)
      },
      {
          separator: true,
          label: '',
          action: () => {}
      },
      {
        label: t.database.contextMenu.refresh,
        icon: 'fa-sync',
        action: async () => {
            await fetchStructure();
        }
      },
      {
        label: t.database.contextMenu.deleteDatabase,
        icon: 'fa-trash',
        danger: true,
        action: async () => {
            if (window.confirm(t.database.contextMenu.confirmDeleteDatabase.replace('{name}', dbName))) {
                try {
                    await api.dropDatabaseInstance(configId, dbName);
                    if (onRefreshDatabases) {
                        await onRefreshDatabases();
                    }
                } catch (e: any) {
                    alert(`${t.errors.deleteFailed}: ${e.message}`);
                }
            }
        }
      }
    ];

    setContextMenu({ x: e.clientX, y: e.clientY, items });
  };

  const handleTablesFolderContextMenu = (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

const items: MenuItem[] = [
           {
             label: t.database.contextMenu.newSqlConsole || 'New SQL Console',
             icon: 'fa-terminal',
             action: () => {
                  if (onOpenSqlConsole) {
                      onOpenSqlConsole('', dbName, configId);
                  }
             }
           },
           {
             label: t.database.contextMenu.newTable,
             icon: 'fa-plus',
             action: () => {
                  if (onOpenSqlConsole) {
                      const template = `CREATE TABLE new_table (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`;
                      onOpenSqlConsole(template, dbName, configId);
                 }
            }
          },
          {
              separator: true,
              label: '',
              action: () => {}
          },
          {
              label: t.database.contextMenu.backupSelectedTables,
              icon: 'fa-archive',
              action: () => onOpenBackup(dbName)
          },
          {
              label: t.database.contextMenu.backupHistory,
              icon: 'fa-history',
              action: () => onOpenBackupHistory(dbName)
          },
          {
              separator: true,
              label: '',
              action: () => {}
          },
          {
              label: t.database.contextMenu.generateAllDDL,
              icon: 'fa-file-code',
              action: async () => {
                  try {
                      const ddl = await api.getDatabaseDDL(configId, dbName);
                      setDbDdl(ddl);
                  } catch (e: any) {
                      alert(`${t.common.error}: ${e.message}`);
                  }
              }
          },
          {
              label: t.database.contextMenu.truncateAllTables,
              icon: 'fa-eraser',
              danger: true,
              action: async () => {
                  if (window.confirm(t.database.contextMenu.confirmTruncateAllTables.replace('{name}', dbName))) {
                      try {
                          await api.truncateAllTables(configId, dbName);
                          alert(t.common.success);
                          await fetchStructure();
                      } catch (e: any) {
                          alert(`${t.common.error}: ${e.message}`);
                      }
                  }
              }
          },
          {
              label: t.database.contextMenu.deleteAllTables,
              icon: 'fa-trash',
              danger: true,
              action: async () => {
                  if (window.confirm(t.database.contextMenu.confirmDeleteAllTables.replace('{name}', dbName))) {
                      try {
                          await api.deleteAllTables(configId, dbName);
                          alert(t.common.success);
                          await fetchStructure();
                      } catch (e: any) {
                          alert(`${t.common.error}: ${e.message}`);
                      }
                  }
              }
          }
      ];

      setContextMenu({ x: e.clientX, y: e.clientY, items });
  };

  return (
    <div className="text-sm">
      <div
        className={`flex items-center space-x-2 py-1 px-2 rounded cursor-pointer ${
          activeDatabaseName === dbName ? 'bg-blue-600/20 text-blue-300' : 'text-slate-300 hover:bg-slate-700/50'
        }`}
        onClick={handleToggle}
        onContextMenu={handleContextMenu}
      >
        <span className="w-4 h-4 flex items-center justify-center">
          {loading ? (
             <i className="fas fa-spinner fa-spin text-[10px]"></i>
           ) : (
             <i className={`fas fa-chevron-right text-[10px] transition-transform ${isExpanded ? 'rotate-90' : ''}`}></i>
           )}
        </span>
        <i className="fas fa-layer-group text-yellow-500/80 text-xs"></i>
        <span className="truncate">{dbName}</span>
      </div>

      {isExpanded && structure && (
        <div className="ml-4 pl-2 border-l border-slate-700 mt-1 space-y-1">
          <FolderNode
            name="Tables"
            icon="fa-table"
            color="text-blue-400"
            items={structure.tables}
            itemIcon="fa-table"
            onItemClick={handleTableClick}
            configId={configId}
            dbName={dbName}
            onRefresh={fetchStructure}
            onOpenSqlConsole={onOpenSqlConsole}
            onSelectTable={onSelectTable}
            onOpenBackup={(table) => onOpenBackup(dbName, [table])}
            searchTerm={searchTerm}
            onContextMenu={handleTablesFolderContextMenu}
          />

          <FolderNode
            name="Views"
            icon="fa-eye"
            color="text-purple-400"
            items={structure.views}
            itemIcon="fa-eye"
            onItemClick={handleTableClick}
            configId={configId}
            dbName={dbName}
            onRefresh={fetchStructure}
            onOpenSqlConsole={onOpenSqlConsole}
            searchTerm={searchTerm}
          />
        </div>
      )}

      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={contextMenu.items}
          onClose={() => setContextMenu(null)}
        />
      )}

      {dbDdl && (
          <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
            <div className="bg-slate-800 rounded-lg shadow-xl w-3/4 max-w-4xl max-h-[90vh] flex flex-col border border-slate-700">
              <div className="flex justify-between items-center p-4 border-b border-slate-700">
                <h3 className="text-lg font-medium text-slate-100">
                  {t.database.dialog.databaseDDL.replace('{name}', dbName)}
                </h3>
                <button onClick={() => setDbDdl(null)} className="text-slate-400 hover:text-white">
                  <i className="fas fa-times"></i>
                </button>
              </div>

              <div className="flex-1 overflow-auto p-4">
                  <pre className="bg-slate-900 p-4 rounded text-sm text-slate-300 font-mono overflow-auto whitespace-pre-wrap">
                    {dbDdl}
                  </pre>
              </div>

              <div className="p-4 border-t border-slate-700 flex justify-end gap-2">
                <button
                  onClick={() => {
                      if (dbDdl) {
                          navigator.clipboard.writeText(dbDdl);
                          alert(t.common.success);
                      }
                  }}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded text-sm transition-colors"
                >
                  <i className="fas fa-copy mr-2"></i>
                  {t.common.copy}
                </button>
                <button
                  onClick={() => setDbDdl(null)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm transition-colors"
                >
                  {t.common.close}
                </button>
              </div>
            </div>
          </div>
      )}
    </div>
  );
};

interface FolderNodeProps {
  name: string;
  icon: string;
  color: string;
  items: TableItem[];
  itemIcon: string;
  onItemClick: (item: string) => void;
  configId: string;
  dbName: string;
  onRefresh: () => void;
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string, configId?: string) => void;
  onSelectTable?: (tableName: string) => void;
  onOpenBackup?: (tableName: string) => void;
  searchTerm: string;
  onContextMenu?: (e: React.MouseEvent) => void;
}

const FolderNode: React.FC<FolderNodeProps> = ({ name, icon, color, items, itemIcon, onItemClick, configId, dbName, onRefresh, onOpenSqlConsole, onSelectTable, onOpenBackup, searchTerm, onContextMenu }) => {
  const { t } = useI18n();
  const [isExpanded, setIsExpanded] = useState(false);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; items: MenuItem[] } | null>(null);

  // State for Dialogs
  const [ddlTable, setDdlTable] = useState<string | null>(null);
  const [modifyTable, setModifyTable] = useState<string | null>(null);

  // Table detail expansion state
  const [expandedDetails, setExpandedDetails] = useState<Record<string, TableDetailResponse | null>>({});
  const [loadingDetails, setLoadingDetails] = useState<Set<string>>(new Set());

  const filteredItems = searchTerm
      ? items.filter(item => item.name.toLowerCase().includes(searchTerm.toLowerCase()))
      : items;

  useEffect(() => {
      if (searchTerm && filteredItems.length > 0 && !isExpanded) {
          setIsExpanded(true);
      }
  }, [searchTerm, filteredItems.length, isExpanded]);

  if (searchTerm && filteredItems.length === 0) {
      return null;
  }

  const toggleTableDetail = async (tableName: string) => {
    if (expandedDetails[tableName]) {
      setExpandedDetails(prev => {
        const next = { ...prev };
        delete next[tableName];
        return next;
      });
      return;
    }

    setLoadingDetails(prev => new Set(prev).add(tableName));
    try {
      const detail = await api.getTableDetail(configId, tableName, dbName);
      setExpandedDetails(prev => ({ ...prev, [tableName]: detail }));
    } catch (e) {
      console.error('Failed to load table detail', e);
    } finally {
      setLoadingDetails(prev => {
        const next = new Set(prev);
        next.delete(tableName);
        return next;
      });
    }
  };

  const handleItemContextMenu = (e: React.MouseEvent, item: TableItem) => {
      e.preventDefault();
      e.stopPropagation();

      const menuItems: MenuItem[] = [
          {
              label: t.database.contextMenu.newQuery || 'New Query',
              icon: 'fa-search',
              action: () => {
                  if (onOpenSqlConsole) {
                      onOpenSqlConsole(`SELECT * FROM ${item.name} LIMIT 100;`, dbName, configId);
                  }
              }
          },
          {
              label: t.database.contextMenu.viewData,
              icon: 'fa-table',
              action: () => onItemClick(item.name)
          },
          {
              label: t.database.contextMenu.viewStructure,
              icon: 'fa-code',
              action: () => {
                  if (onSelectTable) {
                      onSelectTable(item.name);
                      onItemClick(item.name);
                  }
              }
          },
          {
              separator: true,
              label: '',
              action: () => {}
          },
          {
              label: t.database.contextMenu.backupThisTable,
              icon: 'fa-archive',
              action: () => {
                if (onOpenBackup) onOpenBackup(item.name);
              }
          },
          {
              label: t.database.contextMenu.generateDDL,
              icon: 'fa-file-code',
              action: () => setDdlTable(item.name)
          },
          {
              label: t.database.contextMenu.modifyStructure,
              icon: 'fa-edit',
              action: () => setModifyTable(item.name)
          },
          {
              separator: true,
              label: '',
              action: () => {}
          },
          {
              label: t.database.contextMenu.emptyData,
              icon: 'fa-eraser',
              danger: true,
              action: async () => {
                  if (window.confirm(t.database.contextMenu.confirmTruncateTable.replace('{name}', item.name))) {
                      try {
                          await api.truncateTableInstance(configId, item.name, dbName);
                          onItemClick(item.name);
                      } catch (e: any) {
                          alert(`${t.errors.executionFailed}: ${e.message}`);
                      }
                  }
              }
          },
{
               label: t.database.contextMenu.deleteTable,
               icon: 'fa-trash',
               danger: true,
               action: async () => {
                   if (window.confirm(t.database.contextMenu.confirmDeleteTable.replace('{name}', item.name))) {
                       try {
                           await api.dropTableInstance(configId, item.name, dbName);
                           onRefresh();
                       } catch (e: any) {
                           alert(`${t.errors.deleteFailed}: ${e.message}`);
                       }
                   }
               }
           },
           {
               separator: true,
               label: '',
               action: () => {}
           },
           {
               label: t.database.contextMenu.refreshTableStructure,
               icon: 'fa-sync',
               action: async () => {
                   await onRefresh();
               }
           }
       ];

      setContextMenu({ x: e.clientX, y: e.clientY, items: menuItems });
  };

  const renderTableDetail = (tableName: string, detail: TableDetailResponse) => {
    return (
      <div className="ml-5 pl-2.5 border-l border-slate-700/40 py-1.5 space-y-3">
        {/* Columns */}
        {detail.columns.length > 0 && (
          <div className="bg-slate-900/40 rounded-md border border-slate-700/30 overflow-hidden">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-800/60 border-b border-slate-700/30">
              <i className="fas fa-columns text-[9px] text-cyan-400/70"></i>
              <span className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">{t.database.dialog.tableDetail.columns}</span>
              <span className="text-[9px] text-slate-600 ml-auto">{detail.columns.length}</span>
            </div>
            <div className="px-2 py-1 space-y-0">
              {detail.columns.map((col) => (
                <div key={col.name} className="flex items-center gap-1.5 py-0.5 text-[10.5px] leading-relaxed">
                  <span className="text-slate-200 font-medium min-w-[72px] truncate">{col.name}</span>
                  <span className="text-cyan-400/70 font-mono text-[10px]">{col.type}{col.length ? `(${col.length})` : ''}</span>
                  <span className="flex gap-0.5 shrink-0">
                    {col.primary_key && <span className="text-amber-400 text-[8px] px-1 py-px bg-amber-500/10 rounded border border-amber-500/20 font-bold leading-none">PK</span>}
                    {col.auto_increment && <span className="text-emerald-400 text-[8px] px-1 py-px bg-emerald-500/10 rounded border border-emerald-500/20 font-bold leading-none">AI</span>}
                    {!col.nullable && !col.primary_key && <span className="text-rose-400/60 text-[8px] px-1 py-px bg-rose-500/10 rounded border border-rose-500/15 font-medium leading-none">NN</span>}
                  </span>
                  {col.comment && <span className="text-slate-600 italic truncate max-w-[90px] text-[9.5px]" title={col.comment}>{col.comment}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Indexes */}
        {detail.indexes.length > 0 && (
          <div className="bg-slate-900/40 rounded-md border border-slate-700/30 overflow-hidden">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-800/60 border-b border-slate-700/30">
              <i className="fas fa-key text-[9px] text-violet-400/70"></i>
              <span className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">{t.database.dialog.tableDetail.indexes}</span>
              <span className="text-[9px] text-slate-600 ml-auto">{detail.indexes.length}</span>
            </div>
            <div className="px-2 py-1 space-y-0.5">
              {detail.indexes.map((idx) => (
                <div key={idx.name} className="flex items-center gap-1.5 py-0.5 text-[10.5px]">
                  <span className="text-slate-200 font-mono text-[10px] min-w-[60px] truncate">{idx.name}</span>
                  <span className="flex gap-0.5 shrink-0">
                    {idx.primary && <span className="text-amber-400 text-[8px] px-1 py-px bg-amber-500/10 rounded border border-amber-500/20 font-bold leading-none">PRI</span>}
                    {idx.unique && !idx.primary && <span className="text-violet-400 text-[8px] px-1 py-px bg-violet-500/10 rounded border border-violet-500/20 font-bold leading-none">UQ</span>}
                  </span>
                  <span className="text-slate-500 font-mono text-[9.5px]">({idx.columns.join(', ')})</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Foreign Keys */}
        {detail.foreign_keys.length > 0 && (
          <div className="bg-slate-900/40 rounded-md border border-slate-700/30 overflow-hidden">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-800/60 border-b border-slate-700/30">
              <i className="fas fa-link text-[9px] text-orange-400/70"></i>
              <span className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">{t.database.dialog.tableDetail.foreignKeys}</span>
              <span className="text-[9px] text-slate-600 ml-auto">{detail.foreign_keys.length}</span>
            </div>
            <div className="px-2 py-1 space-y-0.5">
              {detail.foreign_keys.map((fk) => (
                <div key={fk.name} className="flex items-center gap-1.5 py-0.5 text-[10.5px]">
                  <span className="text-slate-200 font-mono text-[10px] min-w-[60px] truncate">{fk.name}</span>
                  <span className="text-slate-400 font-mono text-[9.5px]">{fk.constrained_columns.join(', ')}</span>
                  <i className="fas fa-arrow-right text-[7px] text-slate-600"></i>
                  <span className="text-orange-400/80 font-mono text-[9.5px]">{fk.referred_table}</span>
                  <span className="text-slate-500 font-mono text-[9.5px]">({fk.referred_columns.join(', ')})</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div>
       <div
        className="flex items-center space-x-2 py-1 px-2 hover:bg-slate-700/50 rounded cursor-pointer text-slate-400"
        onClick={() => setIsExpanded(!isExpanded)}
        onContextMenu={onContextMenu}
      >
        <span className="w-4 h-4 flex items-center justify-center">
             <i className={`fas fa-chevron-right text-[10px] transition-transform ${isExpanded ? 'rotate-90' : ''}`}></i>
        </span>
        <i className={`fas ${icon} ${color} text-xs`}></i>
        <span className="truncate text-xs font-medium">{name}</span>
        <span className="text-[10px] bg-slate-700 px-1 rounded-full">{filteredItems.length}</span>
      </div>

      {isExpanded && (
        <div className="ml-4 pl-2 border-l border-slate-700 mt-1 space-y-0.5">
          {filteredItems.map(item => (
            <div key={item.name}>
              <div
                className="flex items-center space-x-2 py-0.5 px-2 hover:bg-slate-700/50 rounded cursor-pointer text-slate-300 group/item relative"
                onContextMenu={(e) => handleItemContextMenu(e, item)}
                title={item.comment || undefined}
              >
                {/* Detail expand toggle */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleTableDetail(item.name);
                  }}
                  className="w-3 h-3 flex items-center justify-center text-slate-600 hover:text-slate-300"
                  title="Show structure detail"
                >
                  {loadingDetails.has(item.name) ? (
                    <i className="fas fa-spinner fa-spin text-[8px]"></i>
                  ) : (
                    <i className={`fas fa-chevron-right text-[8px] transition-transform ${expandedDetails[item.name] ? 'rotate-90' : ''}`}></i>
                  )}
                </button>

                <i className={`fas ${itemIcon} text-slate-500 text-[10px]`}></i>
                <span
                  className="truncate text-xs flex-1"
                  onClick={(e) => {
                    e.stopPropagation();
                    onItemClick(item.name);
                  }}
                >
                  {searchTerm ? (
                      <>
                         {item.name.split(new RegExp(`(${searchTerm})`, 'gi')).map((part, i) =>
                             part.toLowerCase() === searchTerm.toLowerCase()
                                 ? <span key={i} className="bg-yellow-500/30 text-yellow-200">{part}</span>
                                 : part
                         )}
                      </>
                  ) : item.name}
                </span>

                {item.comment && (
                    <div className="absolute left-full ml-2 top-0 z-50 hidden group-hover/item:block whitespace-nowrap bg-slate-800 text-slate-200 text-xs px-2 py-1 rounded border border-slate-600 shadow-lg pointer-events-none">
                        {item.comment}
                        <div className="absolute top-2 -left-1 w-2 h-2 bg-slate-800 border-l border-b border-slate-600 transform rotate-45"></div>
                    </div>
                )}
              </div>

              {/* Table Detail Panel */}
              {expandedDetails[item.name] && renderTableDetail(item.name, expandedDetails[item.name]!)}
            </div>
          ))}
          {filteredItems.length === 0 && (
             <div className="text-[10px] text-slate-600 py-0.5 px-2 italic">{t.search.noResults}</div>
          )}
        </div>
      )}

      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={contextMenu.items}
          onClose={() => setContextMenu(null)}
        />
      )}

      {ddlTable && (
          <DDLDialog
            isOpen={true}
            onClose={() => setDdlTable(null)}
            configId={configId}
            databaseName={dbName}
            tableName={ddlTable}
          />
      )}

      {modifyTable && (
          <ModifyTableDialog
            isOpen={true}
            onClose={() => setModifyTable(null)}
            configId={configId}
            databaseName={dbName}
            tableName={modifyTable}
            onSuccess={onRefresh}
          />
      )}
    </div>
  );
};

interface PostgresDatabaseNodeProps {
  configId: string;
  dbName: string;
  schemaNames: string[];
  onSelectTable: (configId: string, databaseName: string | undefined, tableName: string, schemaName?: string) => void;
  onSelectDatabase: (configId: string, dbName: string) => void;
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string, configId?: string) => void;
  onOpenBackup: (dbName: string, tables?: string[]) => void;
  onOpenBackupHistory: (dbName: string) => void;
  searchTerm: string;
  activeDatabaseName?: string;
}

const PostgresDatabaseNode: React.FC<PostgresDatabaseNodeProps> = ({
  configId, dbName, schemaNames, onSelectTable, onSelectDatabase,
  onOpenSqlConsole, onOpenBackup, onOpenBackupHistory, searchTerm, activeDatabaseName
}) => {
  const { t } = useI18n();
  const [isExpanded, setIsExpanded] = useState(false);

  const filteredSchemas = searchTerm
    ? schemaNames.filter(s => s.toLowerCase().includes(searchTerm.toLowerCase()))
    : schemaNames;

  if (searchTerm && filteredSchemas.length === 0) return null;

  const isActive = activeDatabaseName === dbName;

  return (
    <div className="text-sm select-none">
      <div
        className={`flex items-center space-x-2 py-1 px-2 rounded cursor-pointer ${
          isActive ? 'bg-blue-600/20 text-blue-300' : 'text-slate-300 hover:bg-slate-700/50'
        }`}
        onClick={() => {
          setIsExpanded(!isExpanded);
          onSelectDatabase(configId, dbName);
        }}
      >
        <span className="w-4 h-4 flex items-center justify-center">
          <i className={`fas fa-chevron-right text-[10px] transition-transform ${isExpanded ? 'rotate-90' : ''}`}></i>
        </span>
        <i className="fas fa-database text-blue-500/80 text-xs"></i>
        <span className="truncate font-medium">{dbName}</span>
        <span className="text-[10px] bg-slate-700 px-1 rounded-full">{filteredSchemas.length}</span>
      </div>

      {isExpanded && (
        <div className="ml-4 pl-2 border-l border-slate-700 mt-1 space-y-0.5">
          {filteredSchemas.map(schema => (
            <SchemaNode
              key={schema}
              configId={configId}
              dbName={dbName}
              schemaName={schema}
              onSelectTable={(table) => onSelectTable(configId, dbName, table, schema)}
              onSelectSchema={() => onSelectDatabase(configId, dbName)}
              onOpenSqlConsole={onOpenSqlConsole}
              onOpenBackup={(d, tables) => onOpenBackup(d, tables)}
              onOpenBackupHistory={(d) => onOpenBackupHistory(d)}
              searchTerm={searchTerm}
              activeSchemaName={activeDatabaseName}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default ConnectionList;
