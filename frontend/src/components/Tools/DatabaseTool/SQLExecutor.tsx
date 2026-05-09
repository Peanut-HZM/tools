import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useDatabaseTool } from '../../../contexts/DatabaseToolContext';
import * as api from '../../../api/databaseToolApi';
import { useToast } from '../../../hooks/useToast';
import { SQLExecutionResult } from '../../../types/databaseTool';
import SQLEditor from './components/SQLEditor';
import ResultViewer from './components/ResultViewer';
import { useI18n } from '../../../i18n';

interface SQLExecutorProps {
  configId: string;
  database: string;
  sql: string;
  onStateChange: (state: { configId: string; database: string; sql: string }) => void;
}

const SQLExecutor: React.FC<SQLExecutorProps> = ({ 
  configId, 
  database,
  sql,
  onStateChange
}) => {
  const { configs, refreshHistory } = useDatabaseTool();
  const toast = useToast();
  const { t } = useI18n();
  
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
  const [tables, setTables] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  useEffect(() => {
    const fetchAll = async () => {
      if (!currentConfig) {
        setDatabases([]);
        setTables([]);
        return;
      }

      setDbLoading(true);
      try {
        const targetDb = currentDatabase || currentConfig.database_name;
        const [dbs, structure] = await Promise.allSettled([
          api.getDatabasesList(currentConfig.id),
          targetDb ? api.getDatabaseStructure(currentConfig.id, targetDb) : Promise.resolve(null)
        ]);

        if (dbs.status === 'fulfilled') {
          setDatabases(dbs.value);
        } else {
          setDatabases([]);
        }

        if (structure.status === 'fulfilled' && structure.value) {
          setTables([
            ...structure.value.tables.map(t => t.name),
            ...structure.value.views.map(v => v.name)
          ]);
        }
      } catch (err) {
        console.error("Failed to load databases", err);
        setDatabases([]);
      } finally {
        setDbLoading(false);
      }
    };

    fetchAll();
  }, [currentConfig?.id, currentDatabase]);

  useEffect(() => {
    setResult(null);
  }, [configId]);

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
      sql
    });
  }, [configs, sql, onStateChange]);

  const handleDatabaseChange = useCallback((newDatabase: string) => {
    onStateChange({
      configId,
      database: newDatabase,
      sql
    });
  }, [configId, sql, onStateChange]);

  const handleSqlChange = useCallback((newSql: string) => {
    onStateChange({
      configId,
      database,
      sql: newSql
    });
  }, [configId, database, onStateChange]);

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
      </div>

      {!configId ? (
        <div className="flex-1 flex items-center justify-center text-slate-500 bg-slate-900 flex-col gap-4">
           <i className="fas fa-database text-4xl opacity-50"></i>
           <p>{t.database.status.disconnected}</p>
        </div>
      ) : (
        <>
          <div className="h-1/3 min-h-[200px]">
            <SQLEditor 
              value={sql} 
              onChange={handleSqlChange} 
              onExecute={handleExecute} 
              loading={loading}
              tables={tables}
            />
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
        </>
      )}
    </div>
  );
};

export default SQLExecutor;