import React, { useState, useEffect } from 'react';
import { SQLExecutionResult, TableSchema } from '../../../../types/databaseTool';
import { useI18n, interpolate } from '../../../../i18n';
import { TruncatedText } from '../../../Common/TruncatedText';
import JsonViewModal from './JsonViewModal';
import { generateInsertStatements, generateUpdateStatements } from '../../../../utils/sqlGenerator';
import * as api from '../../../../api/databaseToolApi';
import { useToast } from '../../../../hooks/useToast';

interface ResultViewerProps {
  result: SQLExecutionResult | null;
  tableName?: string;
  schema?: TableSchema | null;
  enableSelection?: boolean;
  onSelectionChange?: (selectedIndices: number[]) => void;
  configId?: string;
  databaseName?: string;
  onDeleted?: () => void;
}

const ResultViewer: React.FC<ResultViewerProps> = ({ 
  result, 
  tableName, 
  schema, 
  enableSelection = false,
  onSelectionChange,
  configId,
  databaseName,
  onDeleted
}) => {
  const { t } = useI18n();
  const toast = useToast();
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const [viewingRow, setViewingRow] = useState<any | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  // Inline editing state
  const [cellEdits, setCellEdits] = useState<Map<string, { oldValue: any; newValue: any }>>(new Map());
  const [newRows, setNewRows] = useState<Record<string, any>[]>([]);
  const [editingCell, setEditingCell] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const primaryKey = schema?.primary_key;

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
    let sql: string;
    
    if (rows.length === 0 && schema?.columns) {
      const columns = schema.columns.map((c: any) => c.name);
      const values = columns.map(() => 'NULL').join(', ');
      const cols = columns.map((c: string) => `\`${c}\``).join(', ');
      sql = `INSERT INTO \`${tableName || 'table_name'}\` (${cols}) VALUES (${values});`;
    } else {
      sql = generateInsertStatements(tableName || 'table_name', rows);
    }
    
    try {
      await navigator.clipboard.writeText(sql);
      setCopyFeedback('insert');
      setTimeout(() => setCopyFeedback(null), 2000);
    } catch (err) {
      console.error('复制失败', err);
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
    setViewingRow(rows.length > 0 ? rows : result?.result_data);
  };

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleBatchDelete = () => {
    if (!primaryKey || primaryKey.length === 0) return;
    setShowDeleteConfirm(true);
  };

  const confirmDelete = async () => {
    if (!configId || !tableName) return;
    
    setDeleting(true);
    try {
      const selectedRows = getSelectedRows();
      const keyValues = selectedRows.map(row => {
        const keyObj: Record<string, any> = {};
        primaryKey.forEach(pk => { keyObj[pk] = row[pk]; });
        return keyObj;
      });
      
      const deleteResult = await api.batchDeleteRows(configId, tableName, {
        database_name: databaseName,
        primary_keys: primaryKey,
        key_values: keyValues
      });
      
      if (deleteResult.success) {
        toast.success(interpolate(t.database.batchDelete.success, { count: String(deleteResult.deleted_count) }));
        setShowDeleteConfirm(false);
        if (onDeleted) onDeleted();
      } else {
        toast.error(interpolate(t.database.batchDelete.failed, { error: deleteResult.error_message || 'Unknown error' }));
      }
    } catch (error: any) {
      toast.error(error.message || 'Delete failed');
    } finally {
      setDeleting(false);
    }
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

  // --- Inline editing helpers ---

  const getEditKey = (rowIndex: number, colName: string) => `${rowIndex}:${colName}`;

  const handleCellDoubleClick = (rowIndex: number, colName: string) => {
    if (!primaryKey || primaryKey.length === 0) return;
    const key = getEditKey(rowIndex, colName);
    if (!cellEdits.has(key)) {
      const row = result?.result_data?.[rowIndex];
      if (row) {
        setCellEdits(prev => new Map(prev).set(key, {
          oldValue: row[colName],
          newValue: row[colName]
        }));
      }
    }
    setEditingCell(key);
  };

  const handleCellChange = (rowIndex: number, colName: string, value: string) => {
    const key = getEditKey(rowIndex, colName);
    setCellEdits(prev => {
      const next = new Map(prev);
      const existing = next.get(key);
      if (existing) {
        const colDef = schema?.columns?.find((c: any) => c.name === colName);
        let converted: any = value;
        if (value === '' || value.toLowerCase() === 'null') {
          converted = null;
        } else if (colDef?.type?.toLowerCase().includes('bigint')) {
          converted = value;
        } else if (colDef?.type?.toLowerCase().includes('int') || colDef?.type?.toLowerCase().includes('float') || colDef?.type?.toLowerCase().includes('decimal')) {
          const numValue = Number(value);
          converted = isNaN(numValue) || Math.abs(numValue) > Number.MAX_SAFE_INTEGER ? value : numValue;
        }
        next.set(key, { ...existing, newValue: converted });
      }
      return next;
    });
  };

  const handleNewRowChange = (rowIndex: number, colName: string, value: string) => {
    setNewRows(prev => {
      const next = [...prev];
      const row = { ...next[rowIndex] };
      let converted: any = value;
      if (value === '' || value.toLowerCase() === 'null') {
        converted = null;
      } else {
        const colDef = schema?.columns?.find((c: any) => c.name === colName);
        if (colDef?.type?.toLowerCase().includes('bigint')) {
          converted = value;
        } else if (colDef?.type?.toLowerCase().includes('int') || colDef?.type?.toLowerCase().includes('float') || colDef?.type?.toLowerCase().includes('decimal')) {
          const numValue = Number(value);
          converted = isNaN(numValue) || Math.abs(numValue) > Number.MAX_SAFE_INTEGER ? value : numValue;
        }
      }
      row[colName] = converted;
      next[rowIndex] = row;
      return next;
    });
  };

  const finishEdit = () => setEditingCell(null);

  const handleAddRow = () => {
    if (!schema?.columns) return;
    const emptyRow: Record<string, any> = {};
    schema.columns.forEach((col: any) => { emptyRow[col.name] = null; });
    setNewRows(prev => [emptyRow, ...prev]);
  };

  const handleRemoveNewRow = (index: number) => {
    setNewRows(prev => prev.filter((_, i) => i !== index));
  };

  const handleDiscardChanges = () => {
    setCellEdits(new Map());
    setNewRows([]);
    setEditingCell(null);
  };

  const handleSave = async () => {
    if (!configId || !tableName) return;
    
    setSaving(true);
    try {
      for (const newRow of newRows) {
        const insertResult = await api.insertRow(configId, tableName, {
          database_name: databaseName,
          columns: newRow
        });
        if (!insertResult.success) {
          toast.error(interpolate(t.database.executor.saveFailed, { error: insertResult.error_message || 'Unknown error' }));
          return;
        }
      }
      
      for (const [key, { newValue }] of cellEdits) {
        const [rowIndexStr, colName] = key.split(':');
        const rowIndex = parseInt(rowIndexStr);
        const row = result?.result_data?.[rowIndex];
        if (!row || !primaryKey || primaryKey.length === 0) continue;
        
        const keyValues: Record<string, any> = {};
        primaryKey.forEach(pk => { keyValues[pk] = row[pk]; });
        
        const updateResult = await api.updateRow(configId, tableName, {
          database_name: databaseName,
          primary_keys: primaryKey,
          key_values: keyValues,
          columns: { [colName]: newValue }
        });
        
        if (!updateResult.success) {
          toast.error(interpolate(t.database.executor.saveFailed, { error: updateResult.error_message || 'Unknown error' }));
          return;
        }
      }
      
      toast.success(t.database.executor.saveSuccess);
      setCellEdits(new Map());
      setNewRows([]);
      setEditingCell(null);
      if (onDeleted) onDeleted();
    } catch (error: any) {
      toast.error(error.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const getColumnInputType = (colDef: any): string => {
    if (!colDef?.type) return 'text';
    const type = colDef.type.toLowerCase();
    // bigint 使用 text 输入，避免 HTML number input 的精度丢失
    if (type.includes('bigint')) return 'text';
    if (type.includes('int') || type.includes('float') || type.includes('double') || type.includes('decimal') || type.includes('numeric')) return 'number';
    if (type === 'date') return 'date';
    if (type === 'datetime' || type.includes('timestamp')) return 'datetime-local';
    if (type === 'boolean' || type === 'tinyint(1)') return 'checkbox';
    return 'text';
  };

  const totalChanges = cellEdits.size + newRows.length;

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

  const renderCell = (row: Record<string, any>, idx: number, col: string, isNewRow: boolean, newRowIdx?: number) => {
    const colDef = schema?.columns?.find((c: any) => c.name === col);
    const editKey = isNewRow ? `new-${newRowIdx}:${col}` : getEditKey(idx, col);
    const edit = cellEdits.get(editKey);
    const isEditing = editingCell === editKey;
    const isDirty = cellEdits.has(editKey);
    const displayValue = isNewRow ? row[col] : (edit?.newValue !== undefined ? edit.newValue : row[col]);

    if (isEditing) {
      return (
        <input
          type={getColumnInputType(colDef)}
          value={displayValue ?? ''}
          onChange={(e) => isNewRow
            ? handleNewRowChange(newRowIdx!, col, e.target.value)
            : handleCellChange(idx, col, e.target.value)}
          onBlur={finishEdit}
          onKeyDown={(e) => { if (e.key === 'Enter') finishEdit(); }}
          className="w-full bg-slate-700 border border-blue-500 rounded px-1 py-0.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
          autoFocus
        />
      );
    }

    return (
      <span
        onDoubleClick={() => {
          if (primaryKey && primaryKey.length > 0 && !isNewRow) {
            handleCellDoubleClick(idx, col);
          }
        }}
        className={`block ${primaryKey && primaryKey.length > 0 && !isNewRow ? 'cursor-text' : ''}`}
        title={primaryKey && primaryKey.length > 0 && !isNewRow ? '双击编辑' : undefined}
      >
        {displayValue === null ? (
          <span className="text-slate-600 italic">NULL</span>
        ) : (
          <TruncatedText text={String(displayValue)} />
        )}
      </span>
    );
  };

  return (
    <div className="h-full flex flex-col bg-slate-800 border border-slate-700 rounded-md shadow-sm overflow-hidden">
      <div className="bg-slate-900/50 px-4 py-2 border-b border-slate-700 flex justify-between items-center">
        <span className="text-xs font-medium text-slate-400 flex gap-4 items-center">
          <span>{interpolate(t.database.executor.affectedRows, { count: String(result.affected_rows || 0) })}</span>
          <span>{interpolate(t.database.executor.duration, { time: result.execution_time_ms.toFixed(2) })}</span>
          {selectedIndices.size > 0 && (
             <span className="text-blue-400 border-l border-slate-600 pl-4">{interpolate(t.database.executor.selectedCount, { count: String(selectedIndices.size) })}</span>
          )}
          <div className="flex gap-2 ml-2">
            <button 
              onClick={handleCopyInsert}
              className="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded flex items-center gap-1 transition-colors"
              title={t.database.executor.copyInsert}
            >
              <i className={`fas ${copyFeedback === 'insert' ? 'fa-check text-green-400' : 'fa-copy'}`}></i>
              {t.database.executor.copyInsert}
            </button>
            <button 
              onClick={handleCopyUpdate}
              disabled={!primaryKey || primaryKey.length === 0 || selectedIndices.size === 0}
              className={`px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded flex items-center gap-1 transition-colors ${(!primaryKey || primaryKey.length === 0 || selectedIndices.size === 0) ? 'opacity-50 cursor-not-allowed' : ''}`}
              title={selectedIndices.size === 0 
                ? t.database.executor.noDataSelected 
                : (!primaryKey || primaryKey.length === 0) 
                  ? t.database.batchDelete.noPrimaryKey 
                  : t.database.executor.copyUpdate}
            >
              <i className={`fas ${copyFeedback === 'update' ? 'fa-check text-green-400' : 'fa-pen-to-square'}`}></i>
              {t.database.executor.copyUpdate}
            </button>
             <button 
               onClick={handleBatchViewJson}
               className="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded flex items-center gap-1 transition-colors"
               title={selectedIndices.size === 0 ? t.database.executor.viewJson : (t.database.executor.viewSelectedJson || t.database.executor.viewJson)}
             >
               <i className="fas fa-code"></i>
               {t.database.executor.viewJson}
             </button>
             <button 
               onClick={handleBatchDelete}
               disabled={!primaryKey || primaryKey.length === 0 || selectedIndices.size === 0}
               className={`px-2 py-1 text-xs rounded flex items-center gap-1 transition-colors ${
                 (!primaryKey || primaryKey.length === 0 || selectedIndices.size === 0)
                   ? 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
                   : 'bg-red-600/80 hover:bg-red-600 text-white'
               }`}
               title={selectedIndices.size === 0 
                 ? t.database.executor.noDataSelected 
                 : (!primaryKey || primaryKey.length === 0) 
                   ? t.database.batchDelete.noPrimaryKey 
                   : t.database.executor.deleteRows}
             >
               <i className={`fas ${(!primaryKey || primaryKey.length === 0) ? 'fa-ban' : 'fa-trash'}`}></i>
               {t.database.executor.deleteRows}
             </button>
            {/* Edit buttons */}
            {primaryKey && primaryKey.length > 0 && (
              <>
                <button
                  onClick={handleAddRow}
                  className="px-2 py-1 bg-green-700/80 hover:bg-green-600 text-white text-xs rounded flex items-center gap-1 transition-colors"
                  title={t.database.executor.addRow}
                >
                  <i className="fas fa-plus"></i>
                  {t.database.executor.addRow}
                </button>
                {totalChanges > 0 && (
                  <>
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded flex items-center gap-1 transition-colors disabled:opacity-50"
                      title={t.database.executor.saveChanges}
                    >
                      <i className={`fas ${saving ? 'fa-spinner fa-spin' : 'fa-save'}`}></i>
                      {interpolate(t.database.executor.saveChanges, { count: String(totalChanges) })}
                    </button>
                    <button
                      onClick={handleDiscardChanges}
                      disabled={saving}
                      className="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded flex items-center gap-1 transition-colors disabled:opacity-50"
                      title={t.database.executor.discardChanges}
                    >
                      <i className="fas fa-undo"></i>
                      {t.database.executor.discardChanges}
                    </button>
                  </>
                )}
              </>
            )}
          </div>
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
                    title={comment || undefined}
                  >
                    {col}
                    {primaryKey?.includes(col) && <i className="fas fa-key text-yellow-500/70 ml-1 text-[10px]" title="Primary Key"></i>}
                    
                    {comment && (
                       <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block whitespace-nowrap bg-slate-800 text-slate-200 text-xs px-2 py-1 rounded border border-slate-600 shadow-lg z-50 pointer-events-none">
                           {comment}
                           <div className="absolute -bottom-1 left-4 w-2 h-2 bg-slate-800 border-r border-b border-slate-600 transform rotate-45"></div>
                       </div>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="bg-slate-800 divide-y divide-slate-700">
            {/* New rows */}
            {newRows.map((newRow, newRowIdx) => (
              <tr key={`new-${newRowIdx}`} className="bg-green-900/10 hover:bg-green-900/20 transition-colors">
                {enableSelection && (
                  <td className="px-4 py-2 w-10">
                    <span className="text-xs text-green-400 font-medium">{t.database.executor.newRow}</span>
                  </td>
                )}
                {enableSelection && (
                  <td className="px-4 py-2 w-16">
                    <button
                      onClick={() => handleRemoveNewRow(newRowIdx)}
                      className="text-slate-400 hover:text-red-400 transition-colors p-1"
                      title="Remove row"
                    >
                      <i className="fas fa-times"></i>
                    </button>
                  </td>
                )}
                {columns.map((col) => (
                  <td key={`new-${newRowIdx}-${col}`} className="px-6 py-2 whitespace-nowrap text-sm text-slate-300 max-w-xs">
                    {renderCell(newRow, 0, col, true, newRowIdx)}
                  </td>
                ))}
              </tr>
            ))}
            
            {/* Existing rows */}
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
                {columns.map((col) => {
                  const isDirty = cellEdits.has(getEditKey(idx, col));
                  return (
                    <td key={`${idx}-${col}`} className={`px-6 py-4 whitespace-nowrap text-sm max-w-xs ${isDirty ? 'bg-yellow-900/20' : 'text-slate-300'}`}>
                      {renderCell(row, idx, col, false)}
                    </td>
                  );
                })}
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

      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="px-6 py-4 border-b border-slate-700 flex items-center gap-3">
              <i className="fas fa-exclamation-triangle text-yellow-400 text-xl"></i>
              <h3 className="text-lg font-semibold text-slate-100">{t.database.batchDelete.confirmTitle}</h3>
            </div>
            
            <div className="px-6 py-4 space-y-3">
              <p className="text-slate-300">
                {interpolate(t.database.batchDelete.confirmMessage, { count: String(selectedIndices.size) })}
              </p>
              
              <div className="bg-slate-900 rounded p-3 space-y-2 text-sm">
                <div className="flex gap-2">
                  <span className="text-slate-500 min-w-[60px]">{t.database.batchDelete.table}:</span>
                  <span className="text-slate-200">{tableName}</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-slate-500 min-w-[60px]">{t.database.batchDelete.primaryKey}:</span>
                  <span className="text-slate-200">{primaryKey?.join(', ')}</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-slate-500 min-w-[60px]">{t.database.batchDelete.condition}:</span>
                  <span className="text-slate-200 font-mono text-xs break-all">
                    {(() => {
                      const rows = getSelectedRows();
                      if (primaryKey && primaryKey.length === 1) {
                        const pk = primaryKey[0];
                        const vals = rows.map(r => String(r[pk]));
                        return `${pk} IN (${vals.join(', ')})`;
                      } else if (primaryKey && primaryKey.length > 1) {
                        return rows.map(r => 
                          `(${primaryKey.map(pk => `${pk}=${String(r[pk])}`).join(', ')})`
                        ).join(', ');
                      }
                      return '';
                    })()}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="px-6 py-4 border-t border-slate-700 flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleting}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-sm disabled:opacity-50"
              >
                {t.database.batchDelete.cancelButton}
              </button>
              <button
                onClick={confirmDelete}
                disabled={deleting}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded text-sm disabled:opacity-50 flex items-center gap-2"
              >
                {deleting && <i className="fas fa-spinner fa-spin"></i>}
                {t.database.batchDelete.deleteButton}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResultViewer;
