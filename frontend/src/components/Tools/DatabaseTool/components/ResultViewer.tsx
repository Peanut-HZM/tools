import React, { useState, useEffect } from 'react';
import { SQLExecutionResult, TableSchema } from '../../../../types/databaseTool';
import { useI18n, interpolate } from '../../../../i18n';
import { TruncatedText } from '../../../Common/TruncatedText';
import JsonViewModal from './JsonViewModal';
import { generateInsertStatements, generateUpdateStatements } from '../../../../utils/sqlGenerator';

interface ResultViewerProps {
  result: SQLExecutionResult | null;
  tableName?: string;
  schema?: TableSchema | null;
  enableSelection?: boolean;
  onSelectionChange?: (selectedIndices: number[]) => void;
}

const ResultViewer: React.FC<ResultViewerProps> = ({ 
  result, 
  tableName, 
  schema, 
  enableSelection = false,
  onSelectionChange 
}) => {
  const { t } = useI18n();
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const [viewingRow, setViewingRow] = useState<any | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const primaryKey = schema?.primary_key;

  // Reset selection when result changes
  useEffect(() => {
    setSelectedIndices(new Set());
    if (onSelectionChange) onSelectionChange([]);
  }, [result]);

  const getSelectedRows = () => {
    if (!result?.result_data) return [];
    return result.result_data.filter((_, index) => selectedIndices.has(index));
  };

  const handleCopyInsert = async () => {
    const rows = getSelectedRows();
    const sql = generateInsertStatements(tableName || 'table_name', rows);
    try {
      await navigator.clipboard.writeText(sql);
      setCopyFeedback('insert');
      setTimeout(() => setCopyFeedback(null), 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  const handleCopyUpdate = async () => {
    const rows = getSelectedRows();
    const sql = generateUpdateStatements(tableName || 'table_name', rows, primaryKey || []);
    try {
      await navigator.clipboard.writeText(sql);
      setCopyFeedback('update');
      setTimeout(() => setCopyFeedback(null), 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  const handleBatchViewJson = () => {
    const rows = getSelectedRows();
    setViewingRow(rows);
  };

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!result?.result_data) return;
    
    if (e.target.checked) {
      const allIndices = new Set(result.result_data.map((_, i) => i));
      setSelectedIndices(allIndices);
      if (onSelectionChange) onSelectionChange(Array.from(allIndices));
    } else {
      setSelectedIndices(new Set());
      if (onSelectionChange) onSelectionChange([]);
    }
  };

  const handleSelectRow = (index: number) => {
    const newSelected = new Set(selectedIndices);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedIndices(newSelected);
    if (onSelectionChange) onSelectionChange(Array.from(newSelected));
  };

  if (!result) {
    return (
      <div className="h-full flex items-center justify-center text-slate-500 bg-slate-800 rounded-md border border-dashed border-slate-700 flex-col gap-2">
        <i className="fas fa-table text-2xl opacity-50"></i>
        <span className="text-sm">{t.database.executor.noResults}</span>
      </div>
    );
  }

  if (!result.success) {
    return (
      <div className="h-full p-4 bg-red-900/20 border border-red-800/50 rounded-md overflow-auto">
        <h3 className="text-red-400 font-medium mb-2 flex items-center gap-2">
          <i className="fas fa-exclamation-circle"></i>
          {t.common.error}
        </h3>
        <pre className="text-red-300 text-sm font-mono whitespace-pre-wrap">
          {result.error_message}
        </pre>
        <div className="mt-4 text-xs text-red-500/70">
          {interpolate(t.database.executor.duration, { time: result.execution_time_ms.toFixed(2) })}
        </div>
      </div>
    );
  }

  // DML/DDL Result
  if (!result.result_data && result.affected_rows !== undefined) {
    return (
      <div className="h-full p-4 bg-green-900/20 border border-green-800/50 rounded-md flex flex-col items-center justify-center">
        <div className="text-green-400 font-medium text-lg mb-2 flex items-center gap-2">
          <i className="fas fa-check-circle"></i>
          {t.common.success}
        </div>
        <div className="text-green-300">
          {interpolate(t.database.executor.affectedRows, { count: String(result.affected_rows) })}
        </div>
        <div className="mt-4 text-xs text-green-500/70">
          {interpolate(t.database.executor.duration, { time: result.execution_time_ms.toFixed(2) })}
        </div>
      </div>
    );
  }

  // SELECT Result
  const columns = result.columns || (result.result_data && result.result_data.length > 0 ? Object.keys(result.result_data[0]) : []);
  
  if (columns.length === 0) {
    return (
      <div className="h-full p-4 bg-slate-800 border border-slate-700 rounded-md flex flex-col items-center justify-center">
         <div className="text-slate-400">{t.database.executor.noResults}</div>
         <div className="mt-2 text-xs text-slate-500">
          {interpolate(t.database.executor.duration, { time: result.execution_time_ms.toFixed(2) })}
        </div>
      </div>
    );
  }

  const isAllSelected = result.result_data && result.result_data.length > 0 && selectedIndices.size === result.result_data.length;
  const isIndeterminate = selectedIndices.size > 0 && !isAllSelected;

  return (
    <div className="h-full flex flex-col bg-slate-800 border border-slate-700 rounded-md shadow-sm overflow-hidden">
      <div className="bg-slate-900/50 px-4 py-2 border-b border-slate-700 flex justify-between items-center">
        <span className="text-xs font-medium text-slate-400 flex gap-4 items-center">
          <span>{interpolate(t.database.executor.affectedRows, { count: String(result.affected_rows || 0) })}</span>
          <span>{interpolate(t.database.executor.duration, { time: result.execution_time_ms.toFixed(2) })}</span>
          {selectedIndices.size > 0 && (
             <>
               <span className="text-blue-400 border-l border-slate-600 pl-4">{selectedIndices.size} selected</span>
               <div className="flex gap-2 ml-2">
                 <button 
                   onClick={handleCopyInsert}
                   className="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded flex items-center gap-1 transition-colors"
                   title="Copy INSERT statements"
                 >
                   <i className={`fas ${copyFeedback === 'insert' ? 'fa-check text-green-400' : 'fa-copy'}`}></i>
                   Insert
                 </button>
                 <button 
                   onClick={handleCopyUpdate}
                   disabled={!primaryKey || primaryKey.length === 0}
                   className={`px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded flex items-center gap-1 transition-colors ${(!primaryKey || primaryKey.length === 0) ? 'opacity-50 cursor-not-allowed' : ''}`}
                   title="Copy UPDATE statements (Requires Primary Key)"
                 >
                   <i className={`fas ${copyFeedback === 'update' ? 'fa-check text-green-400' : 'fa-pen-to-square'}`}></i>
                   Update
                 </button>
                 <button 
                   onClick={handleBatchViewJson}
                   className="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded flex items-center gap-1 transition-colors"
                   title="View as JSON"
                 >
                   <i className="fas fa-code"></i>
                   JSON
                 </button>
               </div>
             </>
          )}
        </span>
      </div>
      <div className="flex-1 overflow-auto">
        <table className="min-w-full divide-y divide-slate-700">
          <thead className="bg-slate-900/80 sticky top-0 z-10">
            <tr>
              {enableSelection && (
                <th scope="col" className="px-4 py-3 text-left w-10">
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    ref={input => { if (input) input.indeterminate = !!isIndeterminate; }}
                    onChange={handleSelectAll}
                    className="rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-slate-800"
                  />
                </th>
              )}
              {enableSelection && (
                 <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase w-16">
                    Action
                 </th>
              )}
              {columns.map((col) => {
                const colDef = schema?.columns?.find((c: any) => c.name === col);
                const comment = colDef?.comment;
                
                return (
                  <th
                    key={col}
                    scope="col"
                    className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider whitespace-nowrap group relative"
                    title={comment || undefined} // Native tooltip fallback
                  >
                    {col}
                    {primaryKey?.includes(col) && <i className="fas fa-key text-yellow-500/70 ml-1 text-[10px]" title="Primary Key"></i>}
                    
                    {/* Custom Bubble Tooltip on Hover */}
                    {comment && (
                       <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block whitespace-nowrap bg-slate-800 text-slate-200 text-xs px-2 py-1 rounded border border-slate-600 shadow-lg z-50 pointer-events-none">
                           {comment}
                           {/* Triangle pointer */}
                           <div className="absolute -bottom-1 left-4 w-2 h-2 bg-slate-800 border-r border-b border-slate-600 transform rotate-45"></div>
                       </div>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="bg-slate-800 divide-y divide-slate-700">
            {result.result_data?.map((row, idx) => (
              <tr key={idx} className={`hover:bg-slate-700/50 transition-colors ${selectedIndices.has(idx) ? 'bg-blue-900/10' : ''}`}>
                {enableSelection && (
                  <td className="px-4 py-4 w-10">
                    <input
                      type="checkbox"
                      checked={selectedIndices.has(idx)}
                      onChange={() => handleSelectRow(idx)}
                      className="rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-slate-800"
                    />
                  </td>
                )}
                {enableSelection && (
                   <td className="px-4 py-4 w-16">
                      <button 
                        onClick={() => setViewingRow(row)}
                        className="text-slate-400 hover:text-blue-400 transition-colors p-1"
                        title="View JSON"
                      >
                        <i className="fas fa-eye"></i>
                      </button>
                   </td>
                )}
                {columns.map((col) => (
                  <td key={`${idx}-${col}`} className="px-6 py-4 whitespace-nowrap text-sm text-slate-300 max-w-xs">
                    {row[col] === null ? (
                      <span className="text-slate-600 italic">NULL</span>
                    ) : (
                      <TruncatedText text={String(row[col])} />
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <JsonViewModal 
        isOpen={!!viewingRow}
        onClose={() => setViewingRow(null)}
        data={viewingRow}
        title={Array.isArray(viewingRow) ? `Selected Rows (${viewingRow.length})` : "Row Data"}
      />
    </div>
  );
};

export default ResultViewer;
