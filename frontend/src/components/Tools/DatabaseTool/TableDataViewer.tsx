import React, { useState, useEffect, useCallback } from 'react';
import { useDatabaseTool } from '../../../contexts/DatabaseToolContext';
import { SQLExecutionResult, TableSchema } from '../../../types/databaseTool';
import * as api from '../../../api/databaseToolApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n } from '../../../i18n';
import ResultViewer from './components/ResultViewer';
import { resolveDefaultSort } from '../../../utils/defaultSortResolver';
import {
  Table,
  Play,
  RefreshCw,
  Loader2,
  Download,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
} from '@/components/ui/DropdownMenu';

interface TableDataViewerProps {
  configId: string;
  databaseName?: string;
  tableName: string;
  schemaName?: string;
}

const TableDataViewer: React.FC<TableDataViewerProps> = ({ configId, databaseName, tableName, schemaName }) => {
  const toast = useToast();
  const { t } = useI18n();
  
  // State for query params
  const [whereClause, setWhereClause] = useState('');
  const [orderByClause, setOrderByClause] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  
  // State for data
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SQLExecutionResult | null>(null);
  const [schema, setSchema] = useState<TableSchema | null>(null);

  // Export state
  const [exporting, setExporting] = useState(false);

  const fetchSchema = useCallback(async (): Promise<TableSchema | null> => {
    try {
      const s = await api.getTableSchema(configId, tableName, databaseName, schemaName);
      setSchema(s);
      return s;
    } catch (error) {
      console.error("Failed to fetch table schema", error);
      return null;
    }
  }, [configId, tableName, databaseName, schemaName]);

  const fetchData = useCallback(async (
    pageNum: number,
    newPageSize?: number,
    overrideOrderBy?: string,
  ) => {
    setLoading(true);
    try {
      const data = await api.queryTableData(configId, tableName, {
        database_name: databaseName,
        schema_name: schemaName,
        where: whereClause,
        order_by: overrideOrderBy !== undefined ? overrideOrderBy : orderByClause,
        page: pageNum,
        page_size: newPageSize ?? pageSize
      });

      setResult(data);
      setPage(pageNum);

      if (!data.success) {
        // error_message 可能包含后端传来的中文文案，直接展示
        toast.error(data.error_message || t.database.executor.noResults);
      }
    } catch (error: unknown) {
      // HTTPException.detail 可能是 {error_code, message, raw} 对象
      const err = error as { message?: string; response?: { detail?: { error_code?: string; message?: string } | string } };
      const detail = err?.response?.detail;
      const errorMsg = (typeof detail === 'object' && detail?.error_code && t.database.errors[detail.error_code as keyof typeof t.database.errors])
        || (typeof detail === 'object' && detail?.message)
        || (typeof detail === 'string' && detail)
        || err?.message
        || t.database.status.failed;
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [configId, tableName, databaseName, schemaName, whereClause, orderByClause, pageSize, toast]);

  // Reset page when table changes
  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      setPage(1);
      setWhereClause('');
      setOrderByClause('');
      setResult(null);
      setSchema(null);

      // 先获取 schema,计算默认排序,再发起数据查询
      const s = await fetchSchema();
      if (cancelled) return;

      const defaultSort = s ? resolveDefaultSort(s) : '';
      setOrderByClause(defaultSort);

      // 注意:fetchData 依赖 orderByClause state,但 setState 是异步的。
      // 由于 fetchData 内部通过闭包读取 orderByClause,
      // 我们需要把 defaultSort 直接传给 fetchData 而不是等 state 更新。
      // 见 Step 4 对 fetchData 的改造。
      fetchData(1, undefined, defaultSort);
    };

    init();

    return () => { cancelled = true; };
  }, [configId, databaseName, tableName, schemaName]);

  /** 导出数据 */
  const handleExport = useCallback(async (format: 'csv' | 'excel' | 'json' | 'sql') => {
    if (!result?.success || !tableName) {
      toast.error(t.database.export.noData);
      return;
    }

    setExporting(true);

    try {
      const fullTableName = schemaName
        ? `${schemaName}.${tableName}`
        : tableName;
      const sql = [
        'SELECT *',
        `FROM ${fullTableName}`,
        whereClause ? `WHERE ${whereClause}` : '',
        orderByClause ? `ORDER BY ${orderByClause}` : '',
      ].filter(Boolean).join(' ');

      const response = await api.exportTableData(configId, {
        sql,
        format,
        database_name: databaseName,
      });

      let blob: Blob;
      if (format === 'excel') {
        const byteChars = atob(response.content || '');
        const byteNums = new Uint8Array(byteChars.length);
        for (let i = 0; i < byteChars.length; i++) {
          byteNums[i] = byteChars.charCodeAt(i);
        }
        blob = new Blob([byteNums], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        });
      } else {
        const mimeType = format === 'csv'
          ? 'text/csv;charset=utf-8'
          : format === 'json'
            ? 'application/json;charset=utf-8'
            : 'text/plain;charset=utf-8';
        blob = new Blob([response.content || ''], { type: mimeType });
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = response.file_name;
      a.click();
      URL.revokeObjectURL(url);

      toast.success(t.database.export.success.replace('{count}', String(response.row_count)));
    } catch (error: unknown) {
      const err = error as { detail?: { message?: string } | string; message?: string };
      const detail = err?.detail;
      const errorMsg = (typeof detail === 'object' && detail?.message)
        || (typeof detail === 'string' && detail)
        || err?.message
        || t.database.export.failed;
      toast.error(errorMsg);
    } finally {
      setExporting(false);
    }
  }, [configId, tableName, databaseName, schemaName, whereClause, orderByClause, result, toast, t]);

  const handleQuickExport = useCallback(() => {
    handleExport('csv');
  }, [handleExport]);

  const handleExecute = () => {
    setPage(1);
    fetchData(1);
  };

  const handleRefresh = () => {
    fetchData(page);
  };

  const handlePageChange = (newPage: number) => {
      fetchData(newPage);
  };

  const getFieldsPlaceholder = (includeDesc?: boolean) => {
    if (!schema || schema.columns.length === 0) {
      return includeDesc ? 'id = 1' : 'id desc';
    }
    const fieldNames = schema.columns.slice(0, 3).map(c => c.name).join(', ');
    if (includeDesc) {
      return `${fieldNames} desc`;
    }
    return `${fieldNames}`;
  };

  return (
    <div className="flex flex-col h-full bg-canvas">
      {/* Header / Toolbar */}
      <div className="p-4 border-b border-border bg-surface-1 space-y-4">
        <div className="flex items-center justify-between">
           <div className="flex items-center space-x-2 text-ink">
              <Table className="w-4 h-4 text-accent-info" />
              <span className="font-semibold">{tableName}</span>
              {schemaName && <span className="text-ink-faint text-sm">({schemaName}{databaseName ? `.${databaseName}` : ''})</span>}
              {!schemaName && databaseName && <span className="text-ink-faint text-sm">({databaseName})</span>}
           </div>
           
           <div className="flex items-center space-x-2">
             <button
               onClick={handleExecute}
               disabled={loading}
               className="bg-accent text-ink-inverse px-3 py-1.5 rounded text-sm hover:bg-accent-hover disabled:opacity-50 flex items-center space-x-1"
             >
               <Play className="w-3 h-3" />
               <span>Run</span>
             </button>
             <button
               onClick={handleRefresh}
               disabled={loading}
               className="bg-surface-2 text-ink-muted px-3 py-1.5 rounded text-sm hover:bg-surface-3 disabled:opacity-50"
             >
               <RefreshCw className="w-4 h-4" />
             </button>

             {/* Quick Export button */}
             <button
               onClick={handleQuickExport}
               disabled={exporting || !result?.success}
               className="bg-surface-2 text-ink-muted px-3 py-1.5 rounded text-sm hover:bg-surface-3 disabled:opacity-50 flex items-center space-x-1"
               title={t.database.export.quickExport}
             >
               {exporting ? (
                 <><Loader2 className="w-3 h-3 animate-spin" /><span>{t.database.export.exporting}</span></>
               ) : (
                 <><Download className="w-3 h-3" /><span>{t.database.export.quickExport}</span></>
               )}
             </button>

             {/* Advanced Export dropdown */}
             <DropdownMenu>
               <DropdownMenuTrigger
                 disabled={exporting || !result?.success}
                 aria-label={t.database.export.advancedExport}
                 className="bg-surface-2 text-ink-muted px-2 py-1.5 rounded text-sm hover:bg-surface-3 disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent"
               >
                 <ChevronDown className="w-3 h-3" />
               </DropdownMenuTrigger>
               <DropdownMenuContent align="end" className="w-32">
                 <DropdownMenuLabel className="px-3 py-1 text-xs text-ink-faint">
                   {t.database.export.format}
                 </DropdownMenuLabel>
                 {(['csv', 'excel', 'json', 'sql'] as const).map((fmt) => (
                   <DropdownMenuItem
                     key={fmt}
                     disabled={exporting}
                     onSelect={() => handleExport(fmt)}
                     className="px-3 py-1.5 text-sm text-ink-muted focus:text-ink-inverse"
                   >
                     {fmt.toUpperCase()}
                   </DropdownMenuItem>
                 ))}
               </DropdownMenuContent>
             </DropdownMenu>
           </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* WHERE Clause Input */}
          <div className="relative">
            <label className="absolute -top-2.5 left-2 bg-surface-1 px-1 text-xs text-ink-muted">
              WHERE (e.g. id = 1)
            </label>
            <input
              type="text"
              value={whereClause}
              onChange={(e) => setWhereClause(e.target.value)}
              placeholder={getFieldsPlaceholder()}
              className="w-full bg-canvas border border-border rounded p-2 text-sm text-ink focus:border-accent focus:outline-none"
              onKeyDown={(e) => e.key === 'Enter' && handleExecute()}
            />
          </div>

          {/* ORDER BY Clause Input */}
          <div className="relative">
            <label className="absolute -top-2.5 left-2 bg-surface-1 px-1 text-xs text-ink-muted">
              ORDER BY (e.g. id desc)
            </label>
            <input
              type="text"
              value={orderByClause}
              onChange={(e) => setOrderByClause(e.target.value)}
              placeholder={getFieldsPlaceholder(true)}
              className="w-full bg-canvas border border-border rounded p-2 text-sm text-ink focus:border-accent focus:outline-none"
              onKeyDown={(e) => e.key === 'Enter' && handleExecute()}
            />
          </div>
        </div>
      </div>

      {/* Result Area */}
      <div className="flex-1 overflow-hidden p-4">
        {loading && !result ? (
           <div className="h-full flex items-center justify-center text-ink-faint">
              <Loader2 className="w-8 h-8 mr-2 animate-spin" />
              Loading...
           </div>
        ) : (
           <ResultViewer
             result={result}
             tableName={tableName}
             schema={schema}
             enableSelection={true}
             configId={configId}
             databaseName={databaseName}
             schemaName={schemaName}
             onDeleted={() => fetchData(page)}
           />
        )}
      </div>

      {/* Pagination Footer */}
      <div className="p-2 border-t border-border bg-surface-1 flex items-center justify-between text-sm text-ink-muted">
          <div className="flex items-center space-x-2">
             <span>Page size:</span>
             <select
               value={pageSize}
               onChange={(e) => {
                   const newPageSize = Number(e.target.value);
                   setPageSize(newPageSize);
                   setPage(1);
                   fetchData(1, newPageSize);
               }}
               className="bg-canvas border border-border rounded px-2 py-1 focus:outline-none"
             >
               <option value={10}>10</option>
               <option value={20}>20</option>
               <option value={50}>50</option>
               <option value={100}>100</option>
             </select>
          </div>

          <div className="flex items-center space-x-4">
             <button
               disabled={page <= 1 || loading}
               onClick={() => handlePageChange(page - 1)}
               className="hover:text-ink-inverse disabled:opacity-30"
             >
               <ChevronLeft className="w-4 h-4" /> Previous
             </button>
             <span>Page {page}</span>
             <button
               disabled={!result?.result_data || result.result_data.length < pageSize || loading} 
               // Note: This simple pagination logic assumes if we got less than pageSize items, we are at the end.
               // For exact "Next" button enabling, we'd need total count from backend.
               // Backend currently doesn't return total count in `SQLExecutionResult` (it returns affected_rows).
               // `query_table_data` does execute COUNT(*) but it's not currently returned in `SQLExecutionResult`.
               // We might want to improve `SQLExecutionResult` or return a different structure.
               // For now, let's just allow Next unless we got 0 rows or less than page size.
               onClick={() => handlePageChange(page + 1)}
               className="hover:text-ink-inverse disabled:opacity-30"
             >
               Next <ChevronRight className="w-4 h-4" />
             </button>
          </div>
      </div>
    </div>
  );
};

export default TableDataViewer;
