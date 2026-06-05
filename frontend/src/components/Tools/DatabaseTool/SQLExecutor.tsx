import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useDatabaseTool } from '../../../contexts/DatabaseToolContext';
import * as api from '../../../api/databaseToolApi';
import { useToast } from '../../../hooks/useToast';
import { SQLExecutionResult, TableItem } from '../../../types/databaseTool';
import SQLEditor from './components/SQLEditor';
import ResultViewer from './components/ResultViewer';
import SQLHistoryPanel from './components/SQLHistoryPanel';
import { useI18n } from '../../../i18n';

const MIN_EDITOR_H = 200;
const MAX_EDITOR_RATIO = 0.9;
const STORAGE_KEY = 'db-tool:sqlEditorHeight';

interface SQLExecutorProps {
  configId: string;
  database: string;
  schema: string;
  sql: string;
  onStateChange: (state: { configId: string; database: string; schema?: string; sql: string }) => void;
}

const SQLExecutor: React.FC<SQLExecutorProps> = ({
  configId,
  database,
  schema,
  sql,
  onStateChange
}) => {
  const { configs, refreshHistory } = useDatabaseTool();
  const toast = useToast();
  const { t } = useI18n();

  const leftColumnRef = useRef<HTMLDivElement>(null);
  const [editorHeight, setEditorHeight] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [columnHeight, setColumnHeight] = useState(0);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = Number(stored);
        if (Number.isFinite(parsed) && parsed >= MIN_EDITOR_H) {
          setEditorHeight(parsed);
        }
      }
    } catch (e) {
      console.error('Failed to load editor height:', e);
    }
  }, []);

  useEffect(() => {
    if (editorHeight === null) return;
    try {
      localStorage.setItem(STORAGE_KEY, String(editorHeight));
    } catch (e) {
      console.error('Failed to save editor height:', e);
    }
  }, [editorHeight]);

  useEffect(() => {
    const el = leftColumnRef.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      const h = entries[0].contentRect.height;
      setColumnHeight(h);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    setResult(null);
  }, [configId]);

  // 受控组件：连接/数据库/SQL状态由父组件管理，通过onStateChange回调上报变更
  const currentConfig = useMemo(
    () => configs.find(c => c.id === configId) || null,
    [configs, configId]
  );
  const currentDatabase = database || currentConfig?.database_name || '';

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SQLExecutionResult | null>(null);
  const [databases, setDatabases] = useState<string[]>([]);
  const [dbLoading, setDbLoading] = useState(false);
  const [schemas, setSchemas] = useState<string[]>([]);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [tables, setTables] = useState<TableItem[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [showHistoryPanel, setShowHistoryPanel] = useState(false);

  useEffect(() => {
    const fetchAll = async () => {
      if (!currentConfig) {
        setDatabases([]);
        setTables([]);
        setSchemas([]);
        return;
      }

      setDbLoading(true);
      try {
        const targetDb = currentDatabase || currentConfig.database_name;
        const isPostgres = currentConfig.db_type === 'postgresql';

        const dbsPromise = api.getDatabasesList(currentConfig.id);

        let schemasPromise: Promise<string[]> = Promise.resolve([]);
        if (isPostgres && targetDb) {
          schemasPromise = api.getSchemasList(currentConfig.id, targetDb).catch(() => []);
        }

        const structurePromise = targetDb
          ? api.getDatabaseStructure(currentConfig.id, targetDb).catch(() => null)
          : Promise.resolve(null);

        const [dbs, structure, schemasResult] = await Promise.allSettled([
          dbsPromise,
          structurePromise,
          schemasPromise,
        ]);

        if (dbs.status === 'fulfilled') {
          // PostgreSQL: 如果返回的是 "database:schema" 格式，提取唯一的数据库名
          if (isPostgres && dbs.value.length > 0 && dbs.value.some(d => d.includes(':'))) {
            const uniqueDbs = [...new Set(dbs.value.map(d => d.split(':')[0]))];
            setDatabases(uniqueDbs);
          } else {
            setDatabases(dbs.value);
          }
        } else {
          setDatabases([]);
        }

        if (structure.status === 'fulfilled' && structure.value) {
          const tablesAndViews: TableItem[] = [
            ...structure.value.tables,
            ...structure.value.views
          ];
          setTables(tablesAndViews);
        } else {
          setTables([]);
        }

        if (schemasPromise && schemasResult.status === 'fulfilled') {
          setSchemas(schemasResult.value);
        } else {
          setSchemas([]);
        }
      } catch (err) {
        console.error("Failed to load databases", err);
        setDatabases([]);
        setSchemas([]);
      } finally {
        setDbLoading(false);
      }
    };

    fetchAll();
  }, [currentConfig?.id, currentDatabase]);

  const handleExecute = async (pageOverride?: number) => {
    if (!configId || !sql.trim()) return;

    const targetPage = typeof pageOverride === 'number' ? pageOverride : 1;
    if (typeof pageOverride !== 'number') {
      setPage(1);
    }

    setLoading(true);
    setResult(null);
    try {
      const res = await api.executeSQL({
        db_config_id: configId,
        sql: sql,
        database_name: currentDatabase || undefined,
        schema_name: (currentConfig?.db_type === 'postgresql' && schema) ? schema : undefined,
        page: targetPage,
        page_size: pageSize
      });
      setResult(res);
      await refreshHistory();
    } catch (error: any) {
      toast.error(error.message || t.errors.executionFailed || 'Execution failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    handleExecute(newPage);
  };

  const handleConfigChange = useCallback((newConfigId: string) => {
    const newConfig = configs.find(c => c.id === newConfigId);
    onStateChange({
      configId: newConfigId,
      database: newConfig?.database_name || '',
      schema: '',
      sql
    });
  }, [configs, sql, onStateChange]);

  const handleDatabaseChange = useCallback((newDatabase: string) => {
    onStateChange({
      configId,
      database: newDatabase,
      schema: '',
      sql
    });
  }, [configId, sql, onStateChange]);

  const handleSchemaChange = useCallback((newSchema: string) => {
    onStateChange({
      configId,
      database,
      schema: newSchema,
      sql
    });
  }, [configId, database, sql, onStateChange]);

  const handleSqlChange = useCallback((newSql: string) => {
    onStateChange({
      configId,
      database,
      sql: newSql
    });
  }, [configId, database, onStateChange]);

  const handleReuseHistory = useCallback((sql: string) => {
    onStateChange({
      configId,
      database,
      schema,
      sql
    });
    setShowHistoryPanel(false);
  }, [configId, database, schema, onStateChange]);

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);

    const startY = e.clientY;
    const startH = editorHeight ?? MIN_EDITOR_H;
    const observedMax = Math.floor(columnHeight * MAX_EDITOR_RATIO);
    const refMax = leftColumnRef.current
      ? Math.floor(leftColumnRef.current.getBoundingClientRect().height * MAX_EDITOR_RATIO)
      : 0;
    const maxH = Math.max(observedMax, refMax, MIN_EDITOR_H * 2);

    let rafId: number | null = null;
    let nextHeight = startH;

    const onMove = (ev: MouseEvent) => {
      const delta = ev.clientY - startY;
      nextHeight = Math.max(MIN_EDITOR_H, Math.min(startH + delta, maxH));
      if (rafId === null) {
        rafId = requestAnimationFrame(() => {
          setEditorHeight(nextHeight);
          rafId = null;
        });
      }
    };
    const onUp = () => {
      if (rafId !== null) cancelAnimationFrame(rafId);
      setIsDragging(false);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };

    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [editorHeight, columnHeight]);

  return (
    <div className="flex flex-col h-full gap-4 p-4 bg-slate-900">
        <div className="flex items-center space-x-4 bg-slate-800 p-2 rounded-md border border-slate-700">
        <div className="flex items-center space-x-2">
          <label className="text-sm text-slate-400">Connection:</label>
          <select 
            className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200 focus:outline-none focus:border-blue-500 min-w-[150px]"
            value={configId || ''}
            onChange={(e) => handleConfigChange(e.target.value)}
          >
            <option value="" disabled>Select Connection</option>
            {configs.map(c => (
              <option key={c.id} value={c.id}>{c.alias}</option>
            ))}
          </select>
        </div>

        {currentConfig && (
          <div className="flex items-center space-x-2">
            <label className="text-sm text-slate-400">Database:</label>
            <div className="relative">
              <select 
                className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200 focus:outline-none focus:border-blue-500 min-w-[150px] appearance-none pr-8"
                value={database || ''}
                onChange={(e) => handleDatabaseChange(e.target.value)}
                disabled={dbLoading}
              >
                <option value="">Default ({currentConfig.database_name || 'None'})</option>
                {databases.map(db => (
                  <option key={db} value={db}>{db}</option>
                ))}
              </select>
              {dbLoading && (
                <div className="absolute right-2 top-1.5 pointer-events-none">
                  <i className="fas fa-spinner fa-spin text-xs text-slate-400"></i>
                </div>
              )}
            </div>
          </div>
        )}

        {currentConfig && currentConfig.db_type === 'postgresql' && schemas.length > 0 && (
          <div className="flex items-center space-x-2">
            <label className="text-sm text-slate-400">Schema:</label>
            <div className="relative">
              <select
                className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200 focus:outline-none focus:border-blue-500 min-w-[150px] appearance-none pr-8"
                value={schema || ''}
                onChange={(e) => handleSchemaChange(e.target.value)}
                disabled={schemaLoading}
              >
                <option value="">Default (public)</option>
                {schemas.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              {schemaLoading && (
                <div className="absolute right-2 top-1.5 pointer-events-none">
                  <i className="fas fa-spinner fa-spin text-xs text-slate-400"></i>
                </div>
              )}
            </div>
          </div>
        )}
        
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setShowHistoryPanel(!showHistoryPanel)}
            className={`p-1.5 rounded transition-colors ${
              showHistoryPanel 
                ? 'bg-blue-600 text-white' 
                : 'text-slate-400 hover:text-white hover:bg-slate-700'
            }`}
            title="SQL 历史记录"
          >
            <i className="fas fa-history text-sm"></i>
          </button>
        </div>
      </div>

      {!configId ? (
        <div className="flex-1 flex items-center justify-center text-slate-500 bg-slate-900 flex-col gap-4">
           <i className="fas fa-database text-4xl opacity-50"></i>
           <p>{t.database.status.disconnected}</p>
        </div>
      ) : (
        <div className="flex flex-1 gap-4 overflow-hidden">
          <div
            ref={leftColumnRef}
            className={`flex flex-col gap-4 transition-all min-w-0 ${isDragging ? 'select-none' : ''} ${showHistoryPanel ? 'flex-1' : 'flex-[1_1_0%]'}`}
          >
            <div
              data-testid="editor-wrapper"
              className={editorHeight === null ? 'h-1/3 min-h-[200px]' : 'shrink-0'}
              style={editorHeight !== null ? { height: `${editorHeight}px` } : undefined}
            >
              <SQLEditor
                value={sql}
                onChange={handleSqlChange}
                onExecute={handleExecute}
                loading={loading}
                tables={tables}
              />
            </div>
            <div
              data-testid="drag-handle"
              role="separator"
              aria-orientation="horizontal"
              aria-label={t.database.executor.dragHandleHint}
              onMouseDown={handleDragStart}
              className="h-1.5 bg-slate-700 hover:bg-blue-500 active:bg-blue-400 cursor-ns-resize transition-colors rounded flex items-center justify-center group"
            >
              <div className="w-12 h-0.5 bg-slate-500 group-hover:bg-white/80 rounded" />
            </div>
            <div className="flex-1 min-h-0 flex flex-col gap-2">
              <div className="flex justify-between items-center">
                <h3 className="text-slate-300 text-sm font-medium">{t.database.executor.results}</h3>
                {result && result.success && result.result_data && (
                  <div className="flex items-center gap-2 text-xs">
                    <button
                      disabled={page <= 1 || loading}
                      onClick={() => handlePageChange(page - 1)}
                      className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-slate-300 hover:bg-slate-700 disabled:opacity-50 transition-colors"
                    >
                      <i className="fas fa-chevron-left"></i>
                    </button>
                    <span className="text-slate-400 bg-slate-800 border border-slate-700 px-2 py-1 rounded">
                      Page {page}
                    </span>
                    <button
                      disabled={(!result.result_data || result.result_data.length < pageSize) || loading}
                      onClick={() => handlePageChange(page + 1)}
                      className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-slate-300 hover:bg-slate-700 disabled:opacity-50 transition-colors"
                    >
                      <i className="fas fa-chevron-right"></i>
                    </button>
                  </div>
                )}
              </div>
              <ResultViewer result={result} />
            </div>
          </div>
          
          {showHistoryPanel && (
            <div className="w-80 shrink-0">
              <SQLHistoryPanel
                isOpen={showHistoryPanel}
                onClose={() => setShowHistoryPanel(false)}
                onReuseSql={handleReuseHistory}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SQLExecutor;