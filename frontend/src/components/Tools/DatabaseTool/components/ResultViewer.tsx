import React, { useState, useEffect } from 'react';
import { Table, AlertCircle, CheckCircle, Check, Copy, Pencil, Code, Trash2, Ban, Plus, Save, Undo2, Key, X, Eye, AlertTriangle, Loader2 } from 'lucide-react';
import { SQLExecutionResult, TableSchema } from '../../../../types/databaseTool';
import { useI18n, interpolate } from '../../../../i18n';
import { TruncatedText } from '../../../Common/TruncatedText';
import JsonViewModal from './JsonViewModal';
import { generateInsertStatements, generateUpdateStatements } from '../../../../utils/sqlGenerator';
import { formatCellValue } from '../../../../utils/cellFormatter';
import * as api from '../../../../api/databaseToolApi';
import { useToast } from '../../../../hooks/useToast';
import ColumnSelector from './ColumnSelector';
import { Button } from '@/components/ui/Button';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

interface ResultViewerProps {
  result: SQLExecutionResult | null;
  tableName?: string;
  schema?: TableSchema | null;
  enableSelection?: boolean;
  onSelectionChange?: (selectedIndices: number[]) => void;
  configId?: string;
  databaseName?: string;
  schemaName?: string;
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
  schemaName,
  onDeleted
}) => {
  const { t } = useI18n();
  const toast = useToast();
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const [viewingRow, setViewingRow] = useState<any | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const [errorCopied, setErrorCopied] = useState(false);

  // 列显示状态（按表名持久化到 localStorage）
  const storageKey = tableName ? `db-column-visibility-${configId}-${databaseName || ''}-${schemaName || ''}-${tableName}` : null;

  const [visibleColumns, setVisibleColumns] = useState<string[]>([]);

  useEffect(() => {
    if (!storageKey) {
      setVisibleColumns([]);
      return;
    }
    try {
      const saved = localStorage.getItem(storageKey);
      if (!saved) {
        setVisibleColumns([]);
        return;
      }
      const parsed: string[] = JSON.parse(saved);
      setVisibleColumns(Array.isArray(parsed) ? parsed : []);
    } catch {
      setVisibleColumns([]);
    }
  }, [storageKey]);

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
  const [showTruncateConfirm, setShowTruncateConfirm] = useState(false);
  const [truncating, setTruncating] = useState(false);

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
        schema_name: schemaName,
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

  const handleTruncate = async () => {
    if (!configId || !tableName) return;

    setTruncating(true);
    try {
      const success = await api.truncateTableInstance(
        configId,
        tableName,
        databaseName || '',
        schemaName
      );

      if (success) {
        toast.success('表数据已清空');
        setShowTruncateConfirm(false);
        if (onDeleted) onDeleted();
      } else {
        toast.error('清空表失败');
      }
    } catch (error: any) {
      toast.error(error.message || '清空表失败');
    } finally {
      setTruncating(false);
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
          schema_name: schemaName,
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
          schema_name: schemaName,
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
      <div className="h-full flex items-center justify-center text-ink-faint bg-surface-1 rounded-md border border-dashed border-border flex-col gap-2">
        <Table className="w-8 h-8 opacity-50" />
        <span className="text-sm">{t.database.executor.noResults}</span>
      </div>
    );
  }

  if (!result.success) {
    return (
      <div className="h-full flex flex-col bg-red-900/20 border border-red-800/50 rounded-md overflow-hidden">
        <div className="px-4 py-2 border-b border-red-800/30 flex items-center justify-between">
          <h3 className="text-danger font-medium flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {t.common.error}
          </h3>
          <button
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(result.error_message || '');
                setErrorCopied(true);
                setTimeout(() => setErrorCopied(false), 2000);
              } catch (err) {
                console.error('复制失败', err);
              }
            }}
            className="px-2 py-1 bg-red-800/50 hover:bg-red-700/50 text-red-300 text-xs rounded flex items-center gap-1 transition-colors"
            title="复制错误信息"
          >
            {errorCopied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
            {errorCopied ? '已复制' : '复制错误'}
          </button>
        </div>
        <div className="flex-1 overflow-auto p-4">
          <pre className="text-red-300 text-sm font-mono whitespace-pre-wrap">
            {result.error_message}
          </pre>
        </div>
        <div className="px-4 py-2 border-t border-red-800/30 text-xs text-red-500/70">
          {interpolate(t.database.executor.duration, { time: result.execution_time_ms.toFixed(2) })}
        </div>
      </div>
    );
  }

  if (!result.result_data && result.affected_rows !== undefined) {
    return (
      <div className="h-full p-4 bg-green-900/20 border border-green-800/50 rounded-md flex flex-col items-center justify-center">
        <div className="text-green-400 font-medium text-lg mb-2 flex items-center gap-2">
          <CheckCircle className="w-4 h-4" />
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

  const validStoredColumns = visibleColumns.filter((col) => columns.includes(col));
  const effectiveVisibleColumns = validStoredColumns.length > 0 ? validStoredColumns : columns;

  const handleColumnChange = (cols: string[]) => {
    setVisibleColumns(cols);
    if (storageKey) {
      try {
        localStorage.setItem(storageKey, JSON.stringify(cols));
      } catch (e) {
        console.error('Failed to save column visibility:', e);
      }
    }
  };

  if (columns.length === 0) {
    return (
      <div className="h-full p-4 bg-surface-1 border border-border rounded-md flex flex-col items-center justify-center">
         <div className="text-ink-muted">{t.database.executor.noResults}</div>
         <div className="mt-2 text-xs text-ink-faint">
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
          className="w-full bg-surface-2 border border-accent-info rounded px-1 py-0.5 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
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
          <span className="text-ink-faint italic">NULL</span>
        ) : (
          <TruncatedText text={formatCellValue(displayValue, colDef)} />
        )}
      </span>
    );
  };

  return (
    <div className="h-full flex flex-col bg-surface-1 border border-border rounded-md shadow-sm overflow-hidden">
      <div className="bg-canvas/50 px-4 py-2 border-b border-border flex justify-between items-center">
        <span className="text-xs font-medium text-ink-muted flex gap-4 items-center">
          <span>{interpolate(t.database.executor.affectedRows, { count: String(result.affected_rows || 0) })}</span>
          <span>{interpolate(t.database.executor.duration, { time: result.execution_time_ms.toFixed(2) })}</span>
          {selectedIndices.size > 0 && (
             <span className="text-accent-info border-l border-border pl-4">{interpolate(t.database.executor.selectedCount, { count: String(selectedIndices.size) })}</span>
          )}
          <div className="flex gap-2 ml-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleCopyInsert}
              className="flex items-center gap-1"
              title={t.database.executor.copyInsert}
            >
              {copyFeedback === 'insert' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
              {t.database.executor.copyInsert}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleCopyUpdate}
              disabled={!primaryKey || primaryKey.length === 0 || selectedIndices.size === 0}
              className="flex items-center gap-1"
              title={selectedIndices.size === 0
                ? t.database.executor.noDataSelected
                : (!primaryKey || primaryKey.length === 0)
                  ? t.database.batchDelete.noPrimaryKey
                  : t.database.executor.copyUpdate}
            >
              {copyFeedback === 'update' ? <Check className="w-4 h-4 text-green-400" /> : <Pencil className="w-4 h-4" />}
              {t.database.executor.copyUpdate}
            </Button>
             <Button
               variant="secondary"
               size="sm"
               onClick={handleBatchViewJson}
               className="flex items-center gap-1"
               title={selectedIndices.size === 0 ? t.database.executor.viewJson : (t.database.executor.viewSelectedJson || t.database.executor.viewJson)}
             >
               <Code className="w-4 h-4" />
               {t.database.executor.viewJson}
             </Button>
              {columns.length > 0 && (
                <ColumnSelector
                  columns={columns}
                  schema={schema}
                  visibleColumns={effectiveVisibleColumns}
                  onColumnChange={handleColumnChange}
                />
              )}
              <Button
                size="sm"
                variant={(!primaryKey || primaryKey.length === 0 || selectedIndices.size === 0) ? 'secondary' : 'destructive'}
                onClick={handleBatchDelete}
                disabled={!primaryKey || primaryKey.length === 0 || selectedIndices.size === 0}
                className="flex items-center gap-1"
                title={selectedIndices.size === 0
                  ? t.database.executor.noDataSelected
                  : (!primaryKey || primaryKey.length === 0)
                    ? t.database.batchDelete.noPrimaryKey
                    : t.database.executor.deleteRows}
              >
                {(!primaryKey || primaryKey.length === 0) ? <Ban className="w-4 h-4" /> : <Trash2 className="w-4 h-4" />}
                {t.database.executor.deleteRows}
              </Button>
            {/* Edit buttons */}
            {primaryKey && primaryKey.length > 0 && (
              <>
                <Button
                  size="sm"
                  onClick={handleAddRow}
                  className="flex items-center gap-1"
                  title={t.database.executor.addRow}
                >
                  <Plus className="w-4 h-4" />
                  {t.database.executor.addRow}
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => setShowTruncateConfirm(true)}
                  className="flex items-center gap-1"
                  title="清空表数据"
                >
                  <Trash2 className="w-4 h-4" />
                  清空表
                </Button>
                {totalChanges > 0 && (
                  <>
                    <Button
                      size="sm"
                      onClick={handleSave}
                      disabled={saving}
                      className="flex items-center gap-1"
                      title={t.database.executor.saveChanges}
                    >
                      {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                      {interpolate(t.database.executor.saveChanges, { count: String(totalChanges) })}
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={handleDiscardChanges}
                      disabled={saving}
                      className="flex items-center gap-1"
                      title={t.database.executor.discardChanges}
                    >
                      <Undo2 className="w-4 h-4" />
                      {t.database.executor.discardChanges}
                    </Button>
                  </>
                )}
              </>
            )}
          </div>
        </span>
      </div>
      <div className="flex-1 overflow-auto">
        <table className="min-w-full divide-y divide-slate-700">
          <thead className="bg-canvas/80 sticky top-0 z-10">
            <tr>
              {enableSelection && (
                <th scope="col" className="px-4 py-3 text-left w-10">
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    ref={input => { if (input) input.indeterminate = !!isIndeterminate; }}
                    onChange={handleSelectAll}
                    className="rounded border-border bg-surface-2 text-accent-info focus:ring-accent focus:ring-offset-canvas"
                  />
                </th>
              )}
              {enableSelection && (
                 <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-ink-muted uppercase w-16">
                    Action
                 </th>
              )}
               {effectiveVisibleColumns.map((col) => {
                 const colDef = schema?.columns?.find((c: any) => c.name === col);
                 const comment = colDef?.comment;

                 return (
                   <th
                     key={col}
                     scope="col"
                     className="px-6 py-3 text-left text-xs font-medium text-ink-muted uppercase tracking-wider whitespace-nowrap group relative"
                     title={comment || undefined}
                   >
                     <div>
                       {col}
                       {primaryKey?.includes(col) && <Key className="w-2.5 h-2.5 text-yellow-500/70 ml-1" title="Primary Key" />}
                     </div>
                     {comment && (
                       <div className="text-[10px] text-ink-faint font-normal normal-case tracking-normal mt-0.5 truncate">
                         {comment}
                       </div>
                     )}
                   </th>
                 );
               })}
            </tr>
          </thead>
          <tbody className="bg-surface-1 divide-y divide-slate-700">
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
                      className="text-ink-muted hover:text-danger transition-colors p-1"
                      title="Remove row"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </td>
                )}
                {effectiveVisibleColumns.map((col) => (
                  <td key={`new-${newRowIdx}-${col}`} className="px-6 py-2 whitespace-nowrap text-sm text-ink-muted max-w-xs">
                    {renderCell(newRow, 0, col, true, newRowIdx)}
                  </td>
                ))}
              </tr>
            ))}

            {/* Existing rows */}
            {result.result_data?.map((row, idx) => (
              <tr key={idx} className={`hover:bg-surface-2/50 transition-colors ${selectedIndices.has(idx) ? 'bg-accent-info/10' : ''}`}>
                {enableSelection && (
                  <td className="px-4 py-4 w-10">
                    <input
                      type="checkbox"
                      checked={selectedIndices.has(idx)}
                      onChange={() => handleSelectRow(idx)}
                      className="rounded border-border bg-surface-2 text-accent-info focus:ring-accent focus:ring-offset-canvas"
                    />
                  </td>
                )}
                {enableSelection && (
                   <td className="px-4 py-4 w-16">
                      <button
                        onClick={() => setViewingRow(row)}
                        className="text-ink-muted hover:text-accent-info transition-colors p-1"
                        title="View JSON"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                   </td>
                )}
                {effectiveVisibleColumns.map((col) => {
                  const isDirty = cellEdits.has(getEditKey(idx, col));
                  return (
                    <td key={`${idx}-${col}`} className={`px-6 py-4 whitespace-nowrap text-sm max-w-xs ${isDirty ? 'bg-yellow-900/20' : 'text-ink-muted'}`}>
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
          <div className="bg-surface-1 border border-border rounded-lg shadow-md max-w-md w-full mx-4">
            <div className="px-6 py-4 border-b border-border flex items-center gap-3">
              <AlertTriangle className="w-6 h-6 text-accent-warning" />
              <h3 className="text-lg font-semibold text-ink">{t.database.batchDelete.confirmTitle}</h3>
            </div>

            <div className="px-6 py-4 space-y-3">
              <p className="text-ink-muted">
                {interpolate(t.database.batchDelete.confirmMessage, { count: String(selectedIndices.size) })}
              </p>

              <div className="bg-canvas rounded p-3 space-y-2 text-sm">
                <div className="flex gap-2">
                  <span className="text-ink-faint min-w-[60px]">{t.database.batchDelete.table}:</span>
                  <span className="text-ink">{tableName}</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-ink-faint min-w-[60px]">{t.database.batchDelete.primaryKey}:</span>
                  <span className="text-ink">{primaryKey?.join(', ')}</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-ink-faint min-w-[60px]">{t.database.batchDelete.condition}:</span>
                  <span className="text-ink font-mono text-xs break-all">
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

            <div className="px-6 py-4 border-t border-border flex justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleting}
              >
                {t.database.batchDelete.cancelButton}
              </Button>
              <Button
                variant="destructive"
                onClick={confirmDelete}
                disabled={deleting}
                className="flex items-center gap-2"
              >
                {deleting && <Loader2 className="w-4 h-4 animate-spin" />}
                {t.database.batchDelete.deleteButton}
              </Button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={showTruncateConfirm}
        onOpenChange={(open) => { if (!open) setShowTruncateConfirm(false); }}
        title="确认清空表"
        description={`确定要清空表 ${tableName || ''} 的所有数据吗？此操作不可撤销，表中的所有数据将被删除。`}
        confirmText="确认清空"
        variant="destructive"
        onConfirm={handleTruncate}
      />
    </div>
  );
};

export default ResultViewer;
