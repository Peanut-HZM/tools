import React, { useState, useEffect } from 'react';
import { useDatabaseTool } from '../../../../contexts/DatabaseToolContext';
import { DatabaseConfig, Environment, DatabaseStructure, TableItem } from '../../../../types/databaseTool';
import { useI18n } from '../../../../i18n';
import * as api from '../../../../api/databaseToolApi';
import DatabaseFilterDialog from './DatabaseFilterDialog';
import { ContextMenu, MenuItem } from '../../../../components/Common/ContextMenu';
import CreateDatabaseDialog from './CreateDatabaseDialog';
import ModifyTableDialog from './ModifyTableDialog';
import DDLDialog from './DDLDialog';

interface ConnectionListProps {
  onAddConfig: () => void;
  onEditConfig: (id: string) => void;
  onSelectTable: (configId: string, databaseName: string | undefined, tableName: string) => void;
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string) => void;
}

const ConnectionList: React.FC<ConnectionListProps> = ({ onAddConfig, onEditConfig, onSelectTable, onOpenSqlConsole }) => {
  const { configs, currentConfig, selectConfigById, setCurrentDatabase, refreshConfigs } = useDatabaseTool();
  const { t } = useI18n();
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});
  const [searchTerm, setSearchTerm] = useState('');
  
  const toggleExpand = (nodeId: string) => {
    setExpandedNodes(prev => ({ ...prev, [nodeId]: !prev[nodeId] }));
  };

  const handleSelectDatabase = (configId: string, dbName: string) => {
    if (currentConfig?.id !== configId) {
      selectConfigById(configId);
    }
    setCurrentDatabase(dbName);
  };

  const getEnvColor = (env?: Environment) => {
    switch (env) {
      case Environment.PROD: return 'bg-red-900/30 text-red-400 border border-red-800/50';
      case Environment.TEST: return 'bg-yellow-900/30 text-yellow-400 border border-yellow-800/50';
      case Environment.DEV: return 'bg-green-900/30 text-green-400 border border-green-800/50';
      default: return 'bg-slate-700 text-slate-400 border border-slate-600';
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-800 border-r border-slate-700 w-64">
      <div className="p-4 border-b border-slate-700 flex flex-col gap-2 bg-slate-800">
        <div className="flex justify-between items-center">
            <h2 className="font-semibold text-slate-100">{t.database.connections}</h2>
            <div className="flex space-x-1">
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
        {configs.map(config => (
          <ConnectionNode
            key={config.id}
            config={config}
            isExpanded={!!expandedNodes[config.id]}
            onToggleExpand={() => toggleExpand(config.id)}
            isSelected={currentConfig?.id === config.id}
            onSelect={() => selectConfigById(config.id)}
            onEdit={() => onEditConfig(config.id)}
            onSelectTable={onSelectTable}
            onSelectDatabase={handleSelectDatabase}
            getEnvColor={getEnvColor}
            onRefreshConfigs={refreshConfigs}
            onOpenSqlConsole={onOpenSqlConsole}
            searchTerm={searchTerm}
          />
        ))}
        
        {configs.length === 0 && (
          <div className="text-center text-slate-500 py-8 text-sm flex flex-col items-center gap-2">
            <i className="fas fa-database text-2xl mb-2 opacity-50"></i>
            <p>{t.database.status.disconnected}</p>
            <p className="text-xs opacity-70">{t.common.create}</p>
          </div>
        )}
      </div>
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
  onSelectTable: (configId: string, databaseName: string | undefined, tableName: string) => void;
  onSelectDatabase: (configId: string, dbName: string) => void;
  getEnvColor: (env?: Environment) => string;
  onRefreshConfigs: () => Promise<void>;
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string) => void;
  searchTerm: string;
}

const ConnectionNode: React.FC<ConnectionNodeProps> = ({ 
  config, isExpanded, onToggleExpand, isSelected, onSelect, onEdit, onSelectTable, onSelectDatabase, getEnvColor, onRefreshConfigs, onOpenSqlConsole, searchTerm
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

  // Load filter preference from localStorage
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

  // Backend search effect
  useEffect(() => {
      let active = true;
      const search = async () => {
          if (!searchTerm || searchTerm.length < 2) {
              setSearchResults({});
              return;
          }
          
          setSearching(true);
          try {
              // Call backend search
              const results = await api.searchTables(config.id, searchTerm);
              
              if (active) {
                  // Group by database
                  const grouped: Record<string, string[]> = {};
                  results.forEach(r => {
                      if (!grouped[r.database]) {
                          grouped[r.database] = [];
                      }
                      grouped[r.database].push(r.table);
                  });
                  setSearchResults(grouped);
                  
                  // If we found matches, ensure we are expanded
                  if (results.length > 0 && !isExpanded) {
                      onToggleExpand();
                  }
                  
                  // Also if we have results, we might need to ensure databases are loaded
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

      // Debounce
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
    // Ensure databases are loaded before showing filter
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
    
    const items: MenuItem[] = [
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
          separator: true,
          label: '',
          action: () => {}
      },
      {
        label: t.database.contextMenu.newDatabase,
        icon: 'fa-plus',
        action: () => setCreateDbDialogOpen(true),
        disabled: !!config.database_name // Disable if connection is tied to specific DB? Or allow anyway? 
                                        // Usually "New Database" creates a DB on the server. 
                                        // If config is for a specific DB, we might still be able to create another if user has permissions.
                                        // But if we are restricted to one DB, maybe not.
                                        // Let's enable it generally.
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
      await fetchDatabases(); // Refresh list
  };

  // Determine which databases to show
  const databasesToShow = visibleDatabases 
    ? databases.filter(db => visibleDatabases.includes(db))
    : databases;

  const filteredDatabases = searchTerm 
      ? databases.filter(db => {
          // Show if DB name matches
          if (db.toLowerCase().includes(searchTerm.toLowerCase())) return true;
          // OR if DB contains matching tables (from backend search)
          if (searchResults[db] && searchResults[db].length > 0) return true;
          return false;
      })
      : databasesToShow;

  // No longer needed to auto-expand based on simple name match in useEffect here, 
  // because we handle it in search effect.

  return (
    <div className="select-none">
      <div 
        className={`p-2 rounded-md cursor-pointer group flex items-center justify-between transition-colors ${
          isSelected ? 'bg-blue-600/20 text-blue-100 border border-blue-600/50' : 'text-slate-300 hover:bg-slate-700/50 border border-transparent'
        }`}
        onClick={onSelect}
        onContextMenu={handleContextMenu}
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
          {/* Filter Button - Only show if database_name is not set (listing all DBs) */}
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
            title="Edit Connection"
          >
            <i className="fas fa-edit text-xs"></i>
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="ml-4 pl-2 border-l border-slate-700 mt-1 space-y-1">
          {config.database_name ? (
            <DatabaseStructureNode 
                configId={config.id} 
                dbName={config.database_name} 
                onSelectTable={(table) => onSelectTable(config.id, config.database_name, table)}
                onSelectDatabase={() => onSelectDatabase(config.id, config.database_name!)}
                onOpenSqlConsole={onOpenSqlConsole}
                searchTerm={searchTerm}
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
                    searchTerm={searchTerm}
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
        </div>
      )}

      {/* Filter Dialog */}
      <DatabaseFilterDialog 
        isOpen={filterDialogOpen}
        onClose={() => setFilterDialogOpen(false)}
        allDatabases={databases}
        visibleDatabases={visibleDatabases}
        onApply={handleApplyFilter}
      />

      {/* Create DB Dialog */}
      <CreateDatabaseDialog 
        isOpen={createDbDialogOpen}
        onClose={() => setCreateDbDialogOpen(false)}
        onSubmit={handleCreateDatabase}
      />

      {/* Context Menu */}
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
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string) => void;
  searchTerm: string;
}

const DatabaseStructureNode: React.FC<DatabaseStructureNodeProps> = ({ configId, dbName, onSelectTable, onSelectDatabase, onRefreshDatabases, onOpenSqlConsole, searchTerm }) => {
  const { t } = useI18n();
  const [isExpanded, setIsExpanded] = useState(false);
  const [structure, setStructure] = useState<DatabaseStructure | null>(null);
  const [loading, setLoading] = useState(false);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; items: MenuItem[] } | null>(null);
  
  // State for Database DDL Dialog
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
      // If we have a search term, and we are rendered (meaning we matched),
      // we should ensure structure is loaded so we can show matching tables.
      // But we should be careful not to spam.
      // Only load if we are not loaded.
      if (searchTerm && !structure && !loading) {
          fetchStructure().then(() => setIsExpanded(true));
      } else if (searchTerm && structure && !isExpanded) {
          // If loaded but collapsed, expand
          setIsExpanded(true);
      }
  }, [searchTerm]); // Only run when searchTerm changes significantly or on mount

  const handleToggle = async (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectDatabase(); // Set as current database when clicked
    
    const nextState = !isExpanded;
    setIsExpanded(nextState);
    
    if (nextState && !structure) {
        await fetchStructure();
    }
  };

  const handleTableClick = (table: string) => {
    onSelectDatabase(); // Also ensure DB is selected when table is clicked
    onSelectTable(table);
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onSelectDatabase();

    const items: MenuItem[] = [
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
                  onOpenSqlConsole(template, dbName);
             }
        }
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
            label: t.database.contextMenu.newTable,
            icon: 'fa-plus',
            action: () => {
                 if (onOpenSqlConsole) {
                     const template = `CREATE TABLE new_table (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`;
                      onOpenSqlConsole(template, dbName);
                 }
            }
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
        className="flex items-center space-x-2 py-1 px-2 hover:bg-slate-700/50 rounded cursor-pointer text-slate-300"
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
          {/* Tables Folder */}
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
            searchTerm={searchTerm}
            onContextMenu={handleTablesFolderContextMenu}
          />

          {/* Views Folder */}
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
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string) => void;
  onSelectTable?: (tableName: string) => void;
  searchTerm: string;
  onContextMenu?: (e: React.MouseEvent) => void;
}

const FolderNode: React.FC<FolderNodeProps> = ({ name, icon, color, items, itemIcon, onItemClick, configId, dbName, onRefresh, onOpenSqlConsole, onSelectTable, searchTerm, onContextMenu }) => {
  const { t } = useI18n();
  const [isExpanded, setIsExpanded] = useState(false);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; items: MenuItem[] } | null>(null);
  
  // State for Dialogs
  const [ddlTable, setDdlTable] = useState<string | null>(null);
  const [modifyTable, setModifyTable] = useState<string | null>(null);

  const filteredItems = searchTerm 
      ? items.filter(item => item.name.toLowerCase().includes(searchTerm.toLowerCase()))
      : items;
  
  // Auto-expand if items match
  useEffect(() => {
      if (searchTerm && filteredItems.length > 0 && !isExpanded) {
          setIsExpanded(true);
      }
  }, [searchTerm, filteredItems.length, isExpanded]);

  if (searchTerm && filteredItems.length === 0) {
      return null; // Hide folder if no matches
  }

  const handleItemContextMenu = (e: React.MouseEvent, item: TableItem) => {
      e.preventDefault();
      e.stopPropagation();
      
      const menuItems: MenuItem[] = [
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
                      onSelectTable(item.name); // Reusing select table which might open structure depending on implementation, or data. 
                                           // Usually select table opens data/structure tab.
                                           // User asked for "View Structure" specifically.
                                           // Assuming onItemClick opens Data or Structure.
                                           // Let's assume onItemClick is generic "Select".
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
          }
      ];
      
      setContextMenu({ x: e.clientX, y: e.clientY, items: menuItems });
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
            <div 
                key={item.name} 
                className="flex items-center space-x-2 py-0.5 px-2 hover:bg-slate-700/50 rounded cursor-pointer text-slate-300 group/item relative"
                onClick={() => onItemClick(item.name)}
                onContextMenu={(e) => handleItemContextMenu(e, item)}
                title={item.comment || undefined} // Native tooltip fallback
            >
               <i className={`fas ${itemIcon} text-slate-500 text-[10px]`}></i>
               <span className="truncate text-xs">
                 {/* Highlight match */}
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
               
               {/* Custom Bubble Tooltip on Hover */}
               {item.comment && (
                   <div className="absolute left-full ml-2 top-0 z-50 hidden group-hover/item:block whitespace-nowrap bg-slate-800 text-slate-200 text-xs px-2 py-1 rounded border border-slate-600 shadow-lg pointer-events-none">
                       {item.comment}
                       {/* Triangle pointer */}
                       <div className="absolute top-2 -left-1 w-2 h-2 bg-slate-800 border-l border-b border-slate-600 transform rotate-45"></div>
                   </div>
               )}
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

export default ConnectionList;
