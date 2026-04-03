import React, { useState, useEffect, useCallback } from 'react';
import { useDatabaseTool } from '../../../contexts/DatabaseToolContext';
import { SQLExecutionResult, TableSchema } from '../../../types/databaseTool';
import * as api from '../../../api/databaseToolApi';
import { useToast } from '../../../hooks/useToast';
import ResultViewer from './components/ResultViewer';

interface TableDataViewerProps {
  configId: string;
  databaseName?: string;
  tableName: string;
}

const TableDataViewer: React.FC<TableDataViewerProps> = ({ configId, databaseName, tableName }) => {
  const toast = useToast();
  
  // State for query params
  const [whereClause, setWhereClause] = useState('');
  const [orderByClause, setOrderByClause] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  
  // State for data
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SQLExecutionResult | null>(null);
  const [schema, setSchema] = useState<TableSchema | null>(null);

  const fetchSchema = useCallback(async () => {
    try {
      const s = await api.getTableSchema(configId, tableName, databaseName);
      setSchema(s);
    } catch (error) {
      console.error("Failed to fetch table schema", error);
    }
  }, [configId, tableName, databaseName]);

  const fetchData = useCallback(async (pageNum: number, newPageSize?: number) => {
    setLoading(true);
    try {
      const data = await api.queryTableData(configId, tableName, {
        database_name: databaseName,
        where: whereClause,
        order_by: orderByClause,
        page: pageNum,
        page_size: newPageSize ?? pageSize
      });

      setResult(data);
      setPage(pageNum);

      if (!data.success) {
        toast.error(data.error_message || "Failed to load data");
      }
    } catch (error: any) {
      toast.error(error.message || "Request failed");
    } finally {
      setLoading(false);
    }
  }, [configId, tableName, databaseName, whereClause, orderByClause, pageSize, toast]);

  // Reset page when table changes
  useEffect(() => {
    setPage(1);
    setWhereClause('');
    setOrderByClause('');
    setResult(null);
    setSchema(null);
    fetchSchema();
    fetchData(1);
  }, [configId, databaseName, tableName]);

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

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Header / Toolbar */}
      <div className="p-4 border-b border-slate-700 bg-slate-800 space-y-4">
        <div className="flex items-center justify-between">
           <div className="flex items-center space-x-2 text-slate-100">
              <i className="fas fa-table text-blue-400"></i>
              <span className="font-semibold">{tableName}</span>
              {databaseName && <span className="text-slate-500 text-sm">({databaseName})</span>}
           </div>
           
           <div className="flex items-center space-x-2">
             <button
               onClick={handleExecute}
               disabled={loading}
               className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-1"
             >
               <i className="fas fa-play text-xs"></i>
               <span>Run</span>
             </button>
             <button
               onClick={handleRefresh}
               disabled={loading}
               className="bg-slate-700 text-slate-300 px-3 py-1.5 rounded text-sm hover:bg-slate-600 disabled:opacity-50"
             >
               <i className="fas fa-sync-alt"></i>
             </button>
           </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* WHERE Clause Input */}
          <div className="relative">
            <label className="absolute -top-2.5 left-2 bg-slate-800 px-1 text-xs text-slate-400">
              WHERE (e.g. id = 1)
            </label>
            <input
              type="text"
              value={whereClause}
              onChange={(e) => setWhereClause(e.target.value)}
              placeholder="id = '' and user in ()"
              className="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              onKeyDown={(e) => e.key === 'Enter' && handleExecute()}
            />
          </div>

          {/* ORDER BY Clause Input */}
          <div className="relative">
            <label className="absolute -top-2.5 left-2 bg-slate-800 px-1 text-xs text-slate-400">
              ORDER BY (e.g. id desc)
            </label>
            <input
              type="text"
              value={orderByClause}
              onChange={(e) => setOrderByClause(e.target.value)}
              placeholder="update_time desc, create_time desc"
              className="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              onKeyDown={(e) => e.key === 'Enter' && handleExecute()}
            />
          </div>
        </div>
      </div>

      {/* Result Area */}
      <div className="flex-1 overflow-hidden p-4">
        {loading && !result ? (
           <div className="h-full flex items-center justify-center text-slate-500">
              <i className="fas fa-spinner fa-spin text-2xl mr-2"></i>
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
             onDeleted={() => fetchData(page)}
           />
        )}
      </div>

      {/* Pagination Footer */}
      <div className="p-2 border-t border-slate-700 bg-slate-800 flex items-center justify-between text-sm text-slate-400">
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
               className="bg-slate-900 border border-slate-600 rounded px-2 py-1 focus:outline-none"
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
               className="hover:text-white disabled:opacity-30"
             >
               <i className="fas fa-chevron-left"></i> Previous
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
               className="hover:text-white disabled:opacity-30"
             >
               Next <i className="fas fa-chevron-right"></i>
             </button>
          </div>
      </div>
    </div>
  );
};

export default TableDataViewer;
