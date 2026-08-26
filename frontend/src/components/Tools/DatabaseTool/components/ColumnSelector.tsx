import React, { useState, useEffect, useRef } from 'react';
import { TableSchema } from '../../../../types/databaseTool';
import { useI18n } from '../../../../i18n';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/Popover';

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
  // 使用 useId 生成唯一 id，避免页面上出现重复 id 导致的 label-htmlFor 错乱
  const uniqueId = React.useId();
  const selectAllId = `col-select-all-${uniqueId}`;

  // ESC 关闭（Radix Popover 默认处理 click-outside，但保留 ESC 以防挂载在外层）
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
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <button
          aria-label={t.database.dialog.tableDetail.columns || '列'}
          className={`p-1.5 rounded transition-colors ${
            isOpen
              ? 'bg-accent text-ink-inverse'
              : 'text-ink-muted hover:text-ink-inverse hover:bg-surface-2'
          }`}
        >
          <i className="fas fa-columns text-sm"></i>
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 p-0 max-h-[400px] flex flex-col">
        {/* 全选控制 */}
        <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border bg-surface-1/50 rounded-t-lg">
          <input
            type="checkbox"
            id={selectAllId}
            checked={isAllSelected}
            ref={input => { if (input) input.indeterminate = isSomeSelected; }}
            onChange={handleToggleAll}
            className="rounded border-border bg-surface-2 text-accent-info focus:ring-accent focus:ring-offset-canvas"
          />
          <label htmlFor={selectAllId} className="text-xs font-medium text-ink-muted cursor-pointer select-none flex-1">
            {t.database.dialog.columns.selectAll || '全选'}
          </label>
          <span className="text-[10px] text-ink-faint">
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
                    ? 'hover:bg-surface-2/50'
                    : 'bg-surface-1/30 hover:bg-surface-2/30'
                }`}
                onClick={() => handleToggleColumn(col)}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => {}}
                  className="rounded border-border bg-surface-2 text-accent-info focus:ring-accent focus:ring-offset-canvas pointer-events-none"
                />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-ink-muted truncate font-mono">{col}</div>
                  {comment && (
                    <div className="text-[10px] text-ink-faint truncate">{comment}</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* 提示 */}
        <div className="px-3 py-2 border-t border-border text-[10px] text-ink-faint rounded-b-lg">
          {t.database.dialog.columns.minOneRequired || '至少需要显示一列'}
        </div>
      </PopoverContent>
    </Popover>
  );
};

export default ColumnSelector;
