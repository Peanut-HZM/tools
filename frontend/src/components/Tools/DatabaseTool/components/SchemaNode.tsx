import React, { useState, useEffect, useRef } from 'react';
import { DatabaseStructure, TableItem } from '../../../../types/databaseTool';
import { useI18n } from '../../../../i18n';
import * as api from '../../../../api/databaseToolApi';
import { ContextMenu, MenuItem } from '../../../Common/ContextMenu';
import DDLDialog from './DDLDialog';
import BackupDialog from './BackupDialog';
import ModifyTableDialog from './ModifyTableDialog';

interface SchemaNodeProps {
  configId: string;
  dbName: string;
  schemaName: string;
  onSelectTable: (tableName: string) => void;
  onSelectSchema: (schemaName: string) => void;
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string, configId?: string) => void;
  onOpenBackup: (dbName: string, tables?: string[]) => void;
  onOpenBackupHistory: (dbName: string) => void;
  searchTerm: string;
  activeSchemaName?: string;
}

const SchemaNode: React.FC<SchemaNodeProps> = ({
  configId, dbName, schemaName, onSelectTable, onSelectSchema,
  onOpenSqlConsole, onOpenBackup, onOpenBackupHistory, searchTerm, activeSchemaName
}) => {
  const { t } = useI18n();
  const [isExpanded, setIsExpanded] = useState(false);
  const [structure, setStructure] = useState<DatabaseStructure | null>(null);
  const [loading, setLoading] = useState(false);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; items: MenuItem[] } | null>(null);
  const [ddlTable, setDdlTable] = useState<string | null>(null);
  const [modifyTable, setModifyTable] = useState<string | null>(null);

  // Table detail expansion state
  const [expandedDetails, setExpandedDetails] = useState<Record<string, any | null>>({});
  const [loadingDetails, setLoadingDetails] = useState<Set<string>>(new Set());

  const prefetchedRef = useRef(false);

  const fetchStructure = async () => {
    setLoading(true);
    try {
      const data = await api.getDatabaseStructure(configId, dbName, schemaName);
      setStructure(data);
      return data;
    } catch (err) {
      console.error("Failed to load schema structure", err);
    } finally {
      setLoading(false);
    }
  };

  // Hover prefetch
  const handleMouseEnter = () => {
    if (prefetchedRef.current) return;
    prefetchedRef.current = true;
    api.getDatabaseStructure(configId, dbName, schemaName).catch(() => {});
  };

  const handleMouseLeave = () => {};

  useEffect(() => {
    if (searchTerm && !structure && !loading) {
      fetchStructure().then(() => setIsExpanded(true));
    } else if (searchTerm && structure && !isExpanded) {
      setIsExpanded(true);
    }
  }, [searchTerm]);

  const handleToggle = async (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectSchema(schemaName);

    const nextState = !isExpanded;
    setIsExpanded(nextState);

    if (nextState && !structure) {
      await fetchStructure();
    }
  };

  const handleTableClick = (table: string) => {
    onSelectSchema(schemaName);
    onSelectTable(table);
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onSelectSchema(schemaName);

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
        label: t.database.contextMenu.refresh,
        icon: 'fa-sync',
        action: async () => {
          setStructure(null);
          await fetchStructure();
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
      }
    ];

    setContextMenu({ x: e.clientX, y: e.clientY, items });
  };

  const handleTableContextMenu = (e: React.MouseEvent, item: TableItem) => {
    e.preventDefault();
    e.stopPropagation();

    const menuItems: MenuItem[] = [
      {
        label: t.database.contextMenu.newQuery || 'New Query',
        icon: 'fa-search',
        action: () => {
          if (onOpenSqlConsole) {
            onOpenSqlConsole(`SELECT * FROM "${schemaName}"."${item.name}" LIMIT 100;`, dbName, configId);
          }
        }
      },
      {
        label: t.database.contextMenu.viewData,
        icon: 'fa-table',
        action: () => handleTableClick(item.name)
      },
      {
        label: t.database.contextMenu.viewStructure,
        icon: 'fa-code',
        action: () => {
          handleTableClick(item.name);
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
              await api.truncateTableInstance(configId, item.name, dbName, schemaName);
              setStructure(null);
              await fetchStructure();
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
              await api.dropTableInstance(configId, item.name, dbName, schemaName);
              setStructure(null);
              await fetchStructure();
            } catch (e: any) {
              alert(`${t.errors.deleteFailed}: ${e.message}`);
            }
          }
        }
      }
    ];

    setContextMenu({ x: e.clientX, y: e.clientY, items: menuItems });
  };

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
      const detail = await api.getTableDetail(configId, tableName, dbName, schemaName);
      setExpandedDetails(prev => ({ ...prev, [tableName]: detail }));
    } catch (e: any) {
      console.error('Failed to load table detail', e);
      toast.error(`获取表字段详情失败: ${e.message || '未知错误'}`);
    } finally {
      setLoadingDetails(prev => {
        const next = new Set(prev);
        next.delete(tableName);
        return next;
      });
    }
  };

  const renderTableDetail = (tableName: string, detail: any) => {
    return (
      <div className="ml-5 pl-2.5 border-l border-slate-700/40 py-1.5 space-y-3">
        {detail.columns && detail.columns.length > 0 && (
          <div className="bg-slate-900/40 rounded-md border border-slate-700/30 overflow-hidden">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-800/60 border-b border-slate-700/30">
              <i className="fas fa-columns text-[9px] text-cyan-400/70"></i>
              <span className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">{t.database.dialog.tableDetail.columns}</span>
              <span className="text-[9px] text-slate-600 ml-auto">{detail.columns.length}</span>
            </div>
            <div className="px-2 py-1 space-y-0">
              {detail.columns.map((col: any) => (
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

        {detail.indexes && detail.indexes.length > 0 && (
          <div className="bg-slate-900/40 rounded-md border border-slate-700/30 overflow-hidden">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-800/60 border-b border-slate-700/30">
              <i className="fas fa-key text-[9px] text-violet-400/70"></i>
              <span className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">{t.database.dialog.tableDetail.indexes}</span>
              <span className="text-[9px] text-slate-600 ml-auto">{detail.indexes.length}</span>
            </div>
            <div className="px-2 py-1 space-y-0.5">
              {detail.indexes.map((idx: any) => (
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

        {detail.foreign_keys && detail.foreign_keys.length > 0 && (
          <div className="bg-slate-900/40 rounded-md border border-slate-700/30 overflow-hidden">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-800/60 border-b border-slate-700/30">
              <i className="fas fa-link text-[9px] text-orange-400/70"></i>
              <span className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">{t.database.dialog.tableDetail.foreignKeys}</span>
              <span className="text-[9px] text-slate-600 ml-auto">{detail.foreign_keys.length}</span>
            </div>
            <div className="px-2 py-1 space-y-0.5">
              {detail.foreign_keys.map((fk: any) => (
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

  const isActive = activeSchemaName === schemaName;

  // Search filtering
  const filteredTables = searchTerm
    ? structure?.tables.filter(item => item.name.toLowerCase().includes(searchTerm.toLowerCase())) || []
    : structure?.tables || [];

  const filteredViews = searchTerm
    ? structure?.views.filter(item => item.name.toLowerCase().includes(searchTerm.toLowerCase())) || []
    : structure?.views || [];

  if (searchTerm && filteredTables.length === 0 && filteredViews.length === 0) {
    return null;
  }

  return (
    <div className="text-sm select-none">
      <div
        className={`flex items-center space-x-2 py-1 px-2 rounded cursor-pointer ${
          isActive ? 'bg-blue-600/20 text-blue-300' : 'text-slate-300 hover:bg-slate-700/50'
        }`}
        onClick={handleToggle}
        onContextMenu={handleContextMenu}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <span className="w-4 h-4 flex items-center justify-center">
          {loading ? (
            <i className="fas fa-spinner fa-spin text-[10px]"></i>
          ) : (
            <i className={`fas fa-chevron-right text-[10px] transition-transform ${isExpanded ? 'rotate-90' : ''}`}></i>
          )}
        </span>
        <i className="fas fa-folder text-cyan-500/80 text-xs"></i>
        <span className="truncate">{schemaName}</span>
      </div>

      {isExpanded && structure && (
        <div className="ml-4 pl-2 border-l border-slate-700 mt-1 space-y-1">
          {/* Tables Folder */}
          {filteredTables.length > 0 && (
            <div>
              <div className="flex items-center space-x-2 py-1 px-2 hover:bg-slate-700/50 rounded cursor-pointer text-slate-400">
                <i className="fas fa-table text-blue-400 text-xs"></i>
                <span className="truncate text-xs font-medium">Tables</span>
                <span className="text-[10px] bg-slate-700 px-1 rounded-full">{filteredTables.length}</span>
              </div>
              <div className="ml-4 pl-2 border-l border-slate-700 mt-1 space-y-0.5">
                {filteredTables.map(item => (
                  <div key={item.name}>
                    <div
                      className="flex items-center space-x-2 py-0.5 px-2 hover:bg-slate-700/50 rounded cursor-pointer text-slate-300 group/item relative"
                      onContextMenu={(e) => handleTableContextMenu(e, item)}
                      title={item.comment || undefined}
                    >
                      {/* Detail expand toggle */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          e.preventDefault();
                          toggleTableDetail(item.name);
                        }}
                        className="w-4 h-4 flex items-center justify-center text-slate-500 hover:text-slate-200 shrink-0"
                        title="查看表字段"
                      >
                        {loadingDetails.has(item.name) ? (
                          <i className="fas fa-spinner fa-spin text-[8px]"></i>
                        ) : (
                          <i className={`fas fa-chevron-right text-[8px] transition-transform ${expandedDetails[item.name] ? 'rotate-90' : ''}`}></i>
                        )}
                      </button>

                      <i className="fas fa-table text-slate-500 text-[10px]"></i>
                      <div className="flex-1 min-w-0">
                        <span
                          className="truncate text-xs cursor-pointer"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTableClick(item.name);
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
                          <div className="text-[10px] text-slate-600 truncate" title={item.comment}>
                            {item.comment}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Table Detail Panel */}
                    {expandedDetails[item.name] && renderTableDetail(item.name, expandedDetails[item.name]!)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Views Folder */}
          {filteredViews.length > 0 && (
            <div>
              <div className="flex items-center space-x-2 py-1 px-2 hover:bg-slate-700/50 rounded cursor-pointer text-slate-400">
                <i className="fas fa-eye text-purple-400 text-xs"></i>
                <span className="truncate text-xs font-medium">Views</span>
                <span className="text-[10px] bg-slate-700 px-1 rounded-full">{filteredViews.length}</span>
              </div>
              <div className="ml-4 pl-2 border-l border-slate-700 mt-1 space-y-0.5">
                {filteredViews.map(item => (
                  <div
                    key={item.name}
                    className="flex items-center space-x-2 py-0.5 px-2 hover:bg-slate-700/50 rounded cursor-pointer text-slate-300"
                    onClick={() => handleTableClick(item.name)}
                  >
                    <i className="fas fa-eye text-slate-500 text-[10px]"></i>
                    <span className="truncate text-xs">{item.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {structure.tables.length === 0 && structure.views.length === 0 && (
            <div className="text-xs text-slate-500 py-1 px-2 italic">{t.search.noResults || 'No tables or views'}</div>
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
          schemaName={schemaName}
        />
      )}

      {modifyTable && (
        <ModifyTableDialog
          isOpen={true}
          onClose={() => setModifyTable(null)}
          configId={configId}
          databaseName={dbName}
          tableName={modifyTable}
          schemaName={schemaName}
          onSuccess={async () => {
            setStructure(null);
            await fetchStructure();
          }}
        />
      )}
    </div>
  );
};

export default SchemaNode;
