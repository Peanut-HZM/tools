import React, { useState, useEffect, useRef } from 'react';
import { Columns, Key, Link, ArrowRight, Loader2, ChevronRight, Folder, Table, Eye, Terminal, RefreshCw, Archive, History, Search, FileCode, Pencil, Trash2 } from 'lucide-react';
import { DatabaseStructure, TableItem } from '../../../../types/databaseTool';
import { useI18n } from '../../../../i18n';
import * as api from '../../../../api/databaseToolApi';
import { ContextMenu, MenuItem } from '../../../Common/ContextMenu';
import { toast } from 'sonner';
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

  const fetchStructure = async (skipCache = false) => {
    setLoading(true);
    try {
      const data = await api.getDatabaseStructure(configId, dbName, schemaName, skipCache);
      setStructure(data);
      return data;
    } catch (err) {
      console.error("Failed to load schema structure", err);
    } finally {
      setLoading(false);
    }
  };

  // 监听后台缓存刷新事件（stale-while-revalidate 触发），自动更新显示
  useEffect(() => {
    const expectedKey = `structure:${configId}:${dbName}${schemaName ? ':' + schemaName : ''}`;
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.cacheKey === expectedKey && structure) {
        // 缓存已更新，重新从 IndexedDB 拉取新数据（此时瞬间返回）
        fetchStructure();
      }
    };
    window.addEventListener('db-cache-updated', handler);
    return () => window.removeEventListener('db-cache-updated', handler);
  }, [configId, dbName, schemaName, structure]);

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
        icon: <Terminal className="w-4 h-4" />,
        action: () => {
          if (onOpenSqlConsole) {
            onOpenSqlConsole('', dbName, configId);
          }
        }
      },
      {
        label: t.database.contextMenu.refresh,
        icon: <RefreshCw className="w-4 h-4" />,
        action: async () => {
          setStructure(null);
          await fetchStructure(true); // skipCache=true 强制刷新
        }
      },
      {
        separator: true,
        label: '',
        action: () => {}
      },
      {
        label: t.database.contextMenu.backupDatabase,
        icon: <Archive className="w-4 h-4" />,
        action: () => onOpenBackup(dbName)
      },
      {
        label: t.database.contextMenu.backupHistory,
        icon: <History className="w-4 h-4" />,
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
        icon: <Search className="w-4 h-4" />,
        action: () => {
          if (onOpenSqlConsole) {
            onOpenSqlConsole(`SELECT * FROM "${schemaName}"."${item.name}" LIMIT 100;`, dbName, configId);
          }
        }
      },
      {
        label: t.database.contextMenu.viewData,
        icon: <Table className="w-4 h-4" />,
        action: () => handleTableClick(item.name)
      },
      {
        label: t.database.contextMenu.viewStructure,
        icon: <Code className="w-4 h-4" />,
        action: () => {
          handleTableClick(item.name);
        }
      },
      {
        label: t.database.contextMenu.refreshTableStructure || '刷新表结构',
        icon: <RefreshCw className="w-4 h-4" />,
        action: async () => {
          setStructure(null);
          const data = await fetchStructure(true); // skipCache=true 强制刷新
          // 如果当前表详情已展开，同步刷新详情
          if (data && expandedDetails[item.name]) {
            toggleTableDetail(item.name);
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
        icon: <FileCode className="w-4 h-4" />,
        action: () => setDdlTable(item.name)
      },
      {
        label: t.database.contextMenu.modifyStructure,
        icon: <Pencil className="w-4 h-4" />,
        action: () => setModifyTable(item.name)
      },
      {
        separator: true,
        label: '',
        action: () => {}
      },
      {
        label: t.database.contextMenu.emptyData,
        icon: <Trash2 className="w-4 h-4" />,
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
        icon: <Trash2 className="w-4 h-4" />,
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
      <div className="ml-5 pl-2.5 border-l border-border/40 py-1.5 space-y-3">
        {detail.columns && detail.columns.length > 0 && (
          <div className="bg-canvas/40 rounded-md border border-border/30 overflow-hidden">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-surface-1/60 border-b border-border/30">
              <Columns className="w-2 h-2 text-accent/70" />
              <span className="text-[10px] text-ink-muted font-medium tracking-wide uppercase">{t.database.dialog.tableDetail.columns}</span>
              <span className="text-[9px] text-ink-faint ml-auto">{detail.columns.length}</span>
            </div>
            <div className="px-2 py-1 space-y-0">
              {detail.columns.map((col: any) => (
                <div key={col.name} className="flex items-center gap-1.5 py-0.5 text-[10.5px] leading-relaxed">
                  <span className="text-ink font-medium min-w-[72px] truncate">{col.name}</span>
                  <span className="text-accent/70 font-mono text-[10px]">{col.type}{col.length ? `(${col.length})` : ''}</span>
                  <span className="flex gap-0.5 shrink-0">
                    {col.primary_key && <span className="text-amber-400 text-[8px] px-1 py-px bg-amber-500/10 rounded border border-amber-500/20 font-bold leading-none">PK</span>}
                    {col.auto_increment && <span className="text-success text-[8px] px-1 py-px bg-success/10 rounded border border-emerald-500/20 font-bold leading-none">AI</span>}
                    {!col.nullable && !col.primary_key && <span className="text-rose-400/60 text-[8px] px-1 py-px bg-rose-500/10 rounded border border-rose-500/15 font-medium leading-none">NN</span>}
                  </span>
                  {col.comment && <span className="text-ink-faint italic truncate max-w-[90px] text-[9.5px]" title={col.comment}>{col.comment}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {detail.indexes && detail.indexes.length > 0 && (
          <div className="bg-canvas/40 rounded-md border border-border/30 overflow-hidden">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-surface-1/60 border-b border-border/30">
              <Key className="w-2 h-2 text-violet-400/70" />
              <span className="text-[10px] text-ink-muted font-medium tracking-wide uppercase">{t.database.dialog.tableDetail.indexes}</span>
              <span className="text-[9px] text-ink-faint ml-auto">{detail.indexes.length}</span>
            </div>
            <div className="px-2 py-1 space-y-0.5">
              {detail.indexes.map((idx: any) => (
                <div key={idx.name} className="flex items-center gap-1.5 py-0.5 text-[10.5px]">
                  <span className="text-ink font-mono text-[10px] min-w-[60px] truncate">{idx.name}</span>
                  <span className="flex gap-0.5 shrink-0">
                    {idx.primary && <span className="text-amber-400 text-[8px] px-1 py-px bg-amber-500/10 rounded border border-amber-500/20 font-bold leading-none">PRI</span>}
                    {idx.unique && !idx.primary && <span className="text-violet-400 text-[8px] px-1 py-px bg-violet-500/10 rounded border border-violet-500/20 font-bold leading-none">UQ</span>}
                  </span>
                  <span className="text-ink-faint font-mono text-[9.5px]">({idx.columns.join(', ')})</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {detail.foreign_keys && detail.foreign_keys.length > 0 && (
          <div className="bg-canvas/40 rounded-md border border-border/30 overflow-hidden">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-surface-1/60 border-b border-border/30">
              <Link className="w-2 h-2 text-orange-400/70" />
              <span className="text-[10px] text-ink-muted font-medium tracking-wide uppercase">{t.database.dialog.tableDetail.foreignKeys}</span>
              <span className="text-[9px] text-ink-faint ml-auto">{detail.foreign_keys.length}</span>
            </div>
            <div className="px-2 py-1 space-y-0.5">
              {detail.foreign_keys.map((fk: any) => (
                <div key={fk.name} className="flex items-center gap-1.5 py-0.5 text-[10.5px]">
                  <span className="text-ink font-mono text-[10px] min-w-[60px] truncate">{fk.name}</span>
                  <span className="text-ink-muted font-mono text-[9.5px]">{fk.constrained_columns.join(', ')}</span>
                  <ArrowRight className="w-1.5 h-1.5 text-ink-faint" />
                  <span className="text-orange-400/80 font-mono text-[9.5px]">{fk.referred_table}</span>
                  <span className="text-ink-faint font-mono text-[9.5px]">({fk.referred_columns.join(', ')})</span>
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
          isActive ? 'bg-accent/20 text-accent-info' : 'text-ink-muted hover:bg-surface-2/50'
        }`}
        onClick={handleToggle}
        onContextMenu={handleContextMenu}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <span className="w-4 h-4 flex items-center justify-center">
          {loading ? (
            <Loader2 className="w-2.5 h-2.5 animate-spin" />
          ) : (
            <ChevronRight className={`w-2.5 h-2.5 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
          )}
        </span>
        <Folder className="w-3 h-3 text-accent/80" />
        <span className="truncate">{schemaName}</span>
      </div>

      {isExpanded && structure && (
        <div className="ml-4 pl-2 border-l border-border mt-1 space-y-1">
          {/* Tables Folder */}
          {filteredTables.length > 0 && (
            <div>
              <div className="flex items-center space-x-2 py-1 px-2 hover:bg-surface-2/50 rounded cursor-pointer text-ink-muted">
                <Table className="w-3 h-3 text-accent-info" />
                <span className="truncate text-xs font-medium">Tables</span>
                <span className="text-[10px] bg-surface-2 px-1 rounded-full">{filteredTables.length}</span>
              </div>
              <div className="ml-4 pl-2 border-l border-border mt-1 space-y-0.5">
                {filteredTables.map(item => (
                  <div key={item.name}>
                    <div
                      className="flex items-center space-x-2 py-0.5 px-2 hover:bg-surface-2/50 rounded cursor-pointer text-ink-muted group/item relative"
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
                        className="w-4 h-4 flex items-center justify-center text-ink-faint hover:text-ink shrink-0"
                        title="查看表字段"
                      >
                        {loadingDetails.has(item.name) ? (
                          <Loader2 className="w-2 h-2 animate-spin" />
                        ) : (
                          <ChevronRight className={`w-2 h-2 transition-transform ${expandedDetails[item.name] ? 'rotate-90' : ''}`} />
                        )}
                      </button>

                      <Table className="w-2.5 h-2.5 text-ink-faint" />
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
                          <div className="text-[10px] text-ink-faint truncate" title={item.comment}>
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
              <div className="flex items-center space-x-2 py-1 px-2 hover:bg-surface-2/50 rounded cursor-pointer text-ink-muted">
                <Eye className="w-3 h-3 text-accent-secondary" />
                <span className="truncate text-xs font-medium">Views</span>
                <span className="text-[10px] bg-surface-2 px-1 rounded-full">{filteredViews.length}</span>
              </div>
              <div className="ml-4 pl-2 border-l border-border mt-1 space-y-0.5">
                {filteredViews.map(item => (
                  <div
                    key={item.name}
                    className="flex items-center space-x-2 py-0.5 px-2 hover:bg-surface-2/50 rounded cursor-pointer text-ink-muted"
                    onClick={() => handleTableClick(item.name)}
                  >
                    <Eye className="w-2.5 h-2.5 text-ink-faint" />
                    <span className="truncate text-xs">{item.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {structure.tables.length === 0 && structure.views.length === 0 && (
            <div className="text-xs text-ink-faint py-1 px-2 italic">{t.search.noResults || 'No tables or views'}</div>
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
