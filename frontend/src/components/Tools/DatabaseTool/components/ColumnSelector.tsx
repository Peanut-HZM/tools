import React, { useState, useEffect, useRef } from 'react';
import { TableSchema } from '../../../../types/databaseTool';
import { useI18n } from '../../../../i18n';

interface ColumnSelectorProps {
  columns: string[];
  schema: TableSchema | null;
  visibleColumns: string[];
  onColumnChange: (columns: string[]) => void;
}

const ColumnSelector: React.FC<ColumnSelectorProps> = ({
  columns,
  schema,
  visibleColumns,
  onColumnChange
}) => {
  const { t } = useI18n();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  // 使用 useId 生成唯一 id，避免页面上出现重复 id 导致的 label-htmlFor 错乱
  const uniqueId = React.useId();
  const selectAllId = `col-select-all-${uniqueId}`;

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // ESC 关闭
  useEffect(() => {
    if (!isOpen) return;
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen]);

  const getColumnComment = (colName: string): string | undefined => {
    return schema?.columns?.find((c: any) => c.name === colName)?.comment;
  };

  const isAllSelected = columns.length === visibleColumns.length;
  const isSomeSelected = visibleColumns.length > 0 && visibleColumns.length < columns.length;

  const handleToggleAll = () => {
    if (isAllSelected) {
      // 保留一个列
      onColumnChange(columns.slice(0, 1));
    } else {
      onColumnChange([...columns]);
    }
  };

  const handleToggleColumn = (colName: string) => {
    if (visibleColumns.includes(colName)) {
      // 如果只剩一个列且要取消，不允许
      if (visibleColumns.length === 1) return;
      onColumnChange(visibleColumns.filter(c => c !== colName));
    } else {
      onColumnChange([...visibleColumns, colName]);
    }
  };

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        className={`p-1.5 rounded transition-colors ${
          isOpen 
            ? 'bg-blue-600 text-white' 
            : 'text-slate-400 hover:text-white hover:bg-slate-700'
        }`}
        title={t.database.dialog.tableDetail.columns || '列'}
      >
        <i className="fas fa-columns text-sm"></i>
      </button>

      {isOpen && (
        <div
          ref={dropdownRef}
          className="absolute top-full right-0 mt-2 w-72 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 max-h-[400px] flex flex-col"
        >
          {/* 全选控制 */}
          <div className="flex items-center gap-2 px-3 py-2.5 border-b border-slate-700 bg-slate-800/50 rounded-t-lg">
            <input
              type="checkbox"
              id={selectAllId}
              checked={isAllSelected}
              ref={input => { if (input) input.indeterminate = isSomeSelected; }}
              onChange={handleToggleAll}
              className="rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-800"
            />
            <label htmlFor={selectAllId} className="text-xs font-medium text-slate-300 cursor-pointer select-none flex-1">
              {t.database.dialog.columns.selectAll || '全选'}
            </label>
            <span className="text-[10px] text-slate-500">
              {visibleColumns.length} / {columns.length}
            </span>
          </div>

          {/* 列列表 */}
          <div className="flex-1 overflow-y-auto py-1">
            {columns.map(col => {
              const isSelected = visibleColumns.includes(col);
              const comment = getColumnComment(col);
              
              return (
                <div
                  key={col}
                  className={`flex items-center gap-2 px-3 py-1.5 cursor-pointer transition-colors ${
                    isSelected 
                      ? 'hover:bg-slate-700/50' 
                      : 'bg-slate-800/30 hover:bg-slate-700/30'
                  }`}
                  onClick={() => handleToggleColumn(col)}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => {}}
                    className="rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-800 pointer-events-none"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-slate-300 truncate font-mono">{col}</div>
                    {comment && (
                      <div className="text-[10px] text-slate-500 truncate">{comment}</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* 提示 */}
          <div className="px-3 py-2 border-t border-slate-700 text-[10px] text-slate-600 rounded-b-lg">
            {t.database.dialog.columns.minOneRequired || '至少需要显示一列'}
          </div>
        </div>
      )}
    </div>
  );
};

export default ColumnSelector;
