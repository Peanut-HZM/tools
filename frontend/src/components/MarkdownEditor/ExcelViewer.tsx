/**
 * ExcelViewer - Excel 文件查看器 / 编辑器
 *
 * 只读模式（默认）：使用 SheetJS (xlsx) 解析 Excel 文件并渲染为 HTML 表格。
 *   content 接收 base64 编码的 Excel 数据（来自 FileRawContent.data），支持多 Sheet 切换。
 *   预览模式、OSS 文件、.xls/.csv/.tsv 均走此路径，行为与历史版本一致。
 *
 * 编辑模式（filePath 以 .xlsx 结尾且 readOnly=false）：
 *   渲染为可编辑表格。编辑不直接改写文件内容，而是记录 ExcelOperation 操作日志
 *   （excelEditorStore），保存时由 MarkdownEditor 统一提交后端 /files/save-excel，
 *   后端基于原文件（openpyxl）顺序应用，保留内嵌图片、样式等原文件内容。
 */
import React, { useState, useEffect, useRef } from 'react';
import * as XLSX from 'xlsx';
import { useExcelEditorStore } from '../../stores/excelEditorStore';
import type { ExcelOperation } from '../../types/markdownEditor';

/** ExcelViewer 组件接口 */
interface ExcelViewerProps {
  /** base64 编码的 Excel 数据（来自 FileRawContent.data） */
  content: string | null;
  /** 文件名（可选，显示在工具栏） */
  fileName?: string;
  /** 文件完整路径（编辑模式用于判定 .xlsx 与记录操作日志归属） */
  filePath?: string;
  /** 只读（预览模式 / OSS 文件强制只读） */
  readOnly?: boolean;
}

/** 单个 Sheet 的解析结果（只读模式） */
interface SheetData {
  /** Sheet 名称 */
  name: string;
  /** 二维数组形式的单元格数据 */
  data: (string | number | boolean | null)[][];
}

/** 单个 Sheet 的可编辑矩阵 */
interface EditableSheet {
  name: string;
  /** 二维字符串矩阵（显示/编辑值；公式格为 '=' + 公式文本） */
  rows: string[][];
}

/**
 * 将 base64 字符串解码为 Uint8Array
 * xlsx 需要以 ArrayBuffer 形式接收数据
 */
function base64ToUint8Array(base64: string): Uint8Array {
  const binaryStr = atob(base64);
  const bytes = new Uint8Array(binaryStr.length);
  for (let i = 0; i < binaryStr.length; i++) {
    bytes[i] = binaryStr.charCodeAt(i);
  }
  return bytes;
}

/**
 * 判断当前文件是否可编辑：仅 .xlsx（.xls/.csv/.tsv 保持只读，避免二进制/文本格式误写）
 */
export function isEditableExcel(filePath?: string, readOnly?: boolean): boolean {
  if (!filePath || readOnly) return false;
  const lower = filePath.toLowerCase();
  // 去除查询串后按扩展名判断
  const path = lower.split('?')[0];
  return path.endsWith('.xlsx');
}

/**
 * 将单元格原始值转为可编辑的字符串
 */
function cellValueToText(cell: XLSX.CellObject | undefined): string {
  if (!cell || cell.t === 'z') return '';
  // 公式格：编辑值用公式本身（显示缓存结果的意义不大且无法编辑）
  if (cell.f) return '=' + cell.f;
  const v = cell.v;
  if (v === undefined || v === null) return cell.w || '';
  if (typeof v === 'boolean') return v ? 'TRUE' : 'FALSE';
  return String(v);
}

/**
 * 解析 workbook 中指定 sheet 为补齐的矩形字符串矩阵
 */
function sheetToEditableRows(worksheet: XLSX.WorkSheet): string[][] {
  const ref = worksheet['!ref'];
  if (!ref) return [['']];
  const range = XLSX.utils.decode_range(ref);
  const rows: string[][] = [];
  for (let r = range.s.r; r <= range.e.r; r++) {
    const row: string[] = [];
    for (let c = range.s.c; c <= range.e.c; c++) {
      const addr = XLSX.utils.encode_cell({ r, c });
      row.push(cellValueToText(worksheet[addr] as XLSX.CellObject | undefined));
    }
    rows.push(row);
  }
  return rows.length > 0 ? rows : [['']];
}

/**
 * 根据输入文本推断单元格写入类型（与后端 _parse_cell_value 的 kind 语义对应）
 *
 * 规则（尽量与 Excel 桌面端输入行为一致）：
 * - '=' 开头 → 公式
 * - TRUE/FALSE（不区分大小写）→ 布尔
 * - 带前导零的数字串（如 0012）→ 文本（避免前导零丢失）
 * - 普通数字 → 数字
 * - 其余 → 文本
 */
export function inferCellValue(text: string): { value: string; kind: ExcelOperation['kind'] } {
  const s = text.trim();
  if (s === '') return { value: '', kind: 'str' };
  if (s.startsWith('=')) return { value: s, kind: 'formula' };
  if (/^(true|false)$/i.test(s)) return { value: s, kind: 'bool' };
  // 前导零编号按文本保存，防止 0012 → 12 的数据丢失
  if (/^-?0\d+$/.test(s)) return { value: text, kind: 'str' };
  if (/^-?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(s)) return { value: s, kind: 'number' };
  return { value: text, kind: 'str' };
}

/** 列号（0-based）转 Excel 列字母（0→A, 25→Z, 26→AA） */
function colLabel(c: number): string {
  return XLSX.utils.encode_col(c);
}

// ============================================================================
// 只读模式（保持历史行为不变）
// ============================================================================
const ExcelReadOnlyView: React.FC<{
  sheets: SheetData[];
  activeSheet: number;
  error: string | null;
  onSheetChange: (idx: number) => void;
}> = ({ sheets, activeSheet, error, onSheetChange }) => {
  const currentSheet = sheets[activeSheet];

  return (
    <>
      {/* Sheet 标签栏：多 Sheet 时显示切换标签 */}
      {sheets.length > 1 && (
        <div className="flex border-b border-border bg-surface-1 overflow-x-auto">
          {sheets.map((sheet, idx) => (
            <button
              key={sheet.name}
              onClick={() => onSheetChange(idx)}
              className={`px-4 py-2 text-sm whitespace-nowrap ${
                idx === activeSheet
                  ? 'bg-surface-2 text-ink border-b-2 border-accent-info'
                  : 'text-ink-muted hover:bg-surface-2'
              }`}
            >
              {sheet.name}
            </button>
          ))}
        </div>
      )}

      {/* 表格内容区域 */}
      <div className="flex-1 overflow-auto bg-surface-3">
        {error ? (
          <div className="text-center text-danger py-8">
            {error}
          </div>
        ) : currentSheet && currentSheet.data.length > 0 ? (
          <table className="w-full text-sm">
            <thead className="bg-surface-2 sticky top-0">
              <tr>
                {currentSheet.data[0]?.map((cell, idx) => (
                  <th
                    key={idx}
                    className="px-3 py-2 text-left border border-border font-medium text-ink"
                  >
                    {cell ?? ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {currentSheet.data.slice(1).map((row, rowIdx) => (
                <tr key={rowIdx} className="hover:bg-surface-2/50">
                  {row.map((cell, cellIdx) => (
                    <td
                      key={cellIdx}
                      className="px-3 py-1.5 border border-border text-ink-muted"
                    >
                      {cell ?? ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : currentSheet ? (
          <div className="text-center text-ink-muted py-8">
            当前 Sheet 无数据
          </div>
        ) : null}
      </div>
    </>
  );
};

// ============================================================================
// 编辑模式
// ============================================================================
const ExcelEditorGrid: React.FC<{
  sheets: EditableSheet[];
  activeSheet: number;
  onSheetChange: (idx: number) => void;
  onCommitCell: (row: number, col: number, text: string) => void;
  onInsertRow: (beforeIdx: number) => void;
  onDeleteRow: (idx: number) => void;
  onInsertCol: (beforeIdx: number) => void;
  onDeleteCol: (idx: number) => void;
  onAddRow: () => void;
  onAddCol: () => void;
  onAddSheet: (name: string) => void;
  onRenameSheet: (idx: number, name: string) => void;
  onRemoveSheet: (idx: number) => void;
}> = ({
  sheets,
  activeSheet,
  onSheetChange,
  onCommitCell,
  onInsertRow,
  onDeleteRow,
  onInsertCol,
  onDeleteCol,
  onAddRow,
  onAddCol,
  onAddSheet,
  onRenameSheet,
  onRemoveSheet,
}) => {
  const [selected, setSelected] = useState<{ r: number; c: number } | null>(null);
  // 正在编辑的单元格草稿（受控输入：onChange 存草稿，失焦提交并清除）
  const [draft, setDraft] = useState<{ r: number; c: number; text: string } | null>(null);
  // Escape 取消标记：Escape 触发的 blur 不提交草稿
  const cancelEditRef = useRef(false);
  const current = sheets[activeSheet];

  const toolbarButtonCls = 'px-2 py-1 text-xs rounded border border-border text-ink-muted hover:text-ink hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap';

  if (!current) return null;

  const rows = current.rows;
  const colCount = rows[0]?.length || 1;

  return (
    <>
      {/* 编辑工具栏 */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border bg-surface-1 overflow-x-auto">
        <span className="text-xs text-ink-muted whitespace-nowrap" data-testid="excel-selected-pos">
          {selected ? `${colLabel(selected.c)}${selected.r + 1}` : '未选中'}
        </span>
        <span className="w-px h-4 bg-border" />
        <button
          className={toolbarButtonCls}
          onClick={() => onInsertRow(selected!.r)}
          disabled={!selected}
          title="在选中单元格上方插入行"
        >
          + 上方插入行
        </button>
        <button
          className={toolbarButtonCls}
          onClick={() => onDeleteRow(selected!.r)}
          disabled={!selected}
          title="删除选中单元格所在行"
        >
          − 删除行
        </button>
        <button
          className={toolbarButtonCls}
          onClick={() => onInsertCol(selected!.c)}
          disabled={!selected}
          title="在选中单元格左侧插入列"
        >
          + 左侧插入列
        </button>
        <button
          className={toolbarButtonCls}
          onClick={() => onDeleteCol(selected!.c)}
          disabled={!selected}
          title="删除选中单元格所在列"
        >
          − 删除列
        </button>
        <button className={toolbarButtonCls} onClick={onAddRow} title="在末尾添加一行">
          + 行（末尾）
        </button>
        <button className={toolbarButtonCls} onClick={onAddCol} title="在末尾添加一列">
          + 列（末尾）
        </button>
      </div>

      {/* Sheet 标签栏 */}
      <div className="flex items-center border-b border-border bg-surface-1 overflow-x-auto">
        {sheets.map((sheet, idx) => (
          <div
            key={idx}
            className={`flex items-center group ${idx === activeSheet ? 'bg-surface-2' : ''}`}
          >
            <button
              onClick={() => onSheetChange(idx)}
              onDoubleClick={() => {
                const name = window.prompt('重命名工作表', sheet.name);
                if (name && name.trim() && name.trim() !== sheet.name) {
                  onRenameSheet(idx, name.trim());
                }
              }}
              title="单击切换，双击重命名"
              className={`px-4 py-2 text-sm whitespace-nowrap ${
                idx === activeSheet
                  ? 'text-ink border-b-2 border-accent-info'
                  : 'text-ink-muted hover:bg-surface-2'
              }`}
            >
              {sheet.name}
            </button>
            {sheets.length > 1 && (
              <button
                onClick={() => {
                  if (window.confirm(`确定删除工作表「${sheet.name}」吗？`)) {
                    onRemoveSheet(idx);
                  }
                }}
                className="ml-0.5 mr-1 text-ink-faint hover:text-danger text-xs opacity-0 group-hover:opacity-100"
                title="删除工作表"
              >
                ✕
              </button>
            )}
          </div>
        ))}
        <button
          onClick={() => {
            const name = window.prompt('新工作表名称', `Sheet${sheets.length + 1}`);
            if (name && name.trim()) {
              onAddSheet(name.trim());
            }
          }}
          className="px-3 py-2 text-sm text-ink-muted hover:text-ink hover:bg-surface-2"
          title="新增工作表"
        >
          +
        </button>
      </div>

      {/* 可编辑表格区域 */}
      <div className="flex-1 overflow-auto bg-surface-3">
        <table className="border-collapse text-sm">
          <thead className="bg-surface-2 sticky top-0 z-10">
            <tr>
              <th className="w-12 min-w-12 px-2 py-1.5 border border-border text-ink-faint font-normal text-xs">#</th>
              {Array.from({ length: colCount }, (_, c) => (
                <th
                  key={c}
                  className="min-w-32 px-2 py-1.5 border border-border text-ink font-medium text-xs whitespace-nowrap"
                >
                  {colLabel(c)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, r) => (
              <tr key={r}>
                <td className="px-2 py-0 border border-border text-ink-faint text-xs text-center bg-surface-2 sticky left-0">
                  {r + 1}
                </td>
                {row.map((cellText, c) => {
                  const isDrafting = draft?.r === r && draft?.c === c;
                  return (
                    <td key={c} className="border border-border p-0">
                      <input
                        type="text"
                        value={isDrafting ? draft!.text : cellText}
                        data-testid={`excel-cell-${r}-${c}`}
                        onClick={() => setSelected({ r, c })}
                        onFocus={() => setSelected({ r, c })}
                        onChange={(e) => setDraft({ r, c, text: e.target.value })}
                        onBlur={() => {
                          if (cancelEditRef.current) {
                            cancelEditRef.current = false;
                            setDraft(null);
                            return;
                          }
                          setDraft(null);
                          const text = draft?.text ?? cellText;
                          if (text !== cellText) {
                            onCommitCell(r, c, text);
                          }
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            (e.target as HTMLInputElement).blur();
                          } else if (e.key === 'Escape') {
                            e.preventDefault();
                            cancelEditRef.current = true;
                            setDraft(null);
                            e.currentTarget.blur();
                          }
                        }}
                        className={`w-full min-w-32 px-2 py-1.5 bg-transparent outline-none text-ink focus:bg-surface-2 focus:ring-1 focus:ring-inset ring-accent-cyan ${
                          selected && selected.r === r && selected.c === c ? 'bg-surface-2' : ''
                        }`}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
};

// ============================================================================
// 主组件
// ============================================================================
const ExcelViewer: React.FC<ExcelViewerProps> = ({ content, fileName, filePath, readOnly }) => {
  const { beginEdit, pushOperation } = useExcelEditorStore();
  const editable = isEditableExcel(filePath, readOnly);

  // 只读模式状态
  const [sheets, setSheets] = useState<SheetData[]>([]);
  const [activeSheet, setActiveSheet] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // 编辑模式状态：可编辑矩阵
  const [editSheets, setEditSheets] = useState<EditableSheet[]>([]);

  useEffect(() => {
    if (!content) {
      setSheets([]);
      setEditSheets([]);
      setActiveSheet(0);
      setError(null);
      return;
    }

    try {
      const bytes = base64ToUint8Array(content);
      const workbook = XLSX.read(bytes, { type: 'array', cellText: true });

      if (editable) {
        // 编辑模式：构建可编辑矩阵
        const parsed: EditableSheet[] = workbook.SheetNames.map((name) => ({
          name,
          rows: sheetToEditableRows(workbook.Sheets[name]),
        }));
        setEditSheets(parsed);
        setSheets([]);
        setActiveSheet((prev) => (prev < parsed.length ? prev : 0));
        setError(null);
      } else {
        // 只读模式：保持原有解析方式
        const sheetData: SheetData[] = workbook.SheetNames.map((name) => {
          const worksheet = workbook.Sheets[name];
          const data = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as (string | number | boolean | null)[][];
          return { name, data };
        });
        setSheets(sheetData);
        setEditSheets([]);
        setActiveSheet(0);
        setError(null);
      }
    } catch (e) {
      setError(`Excel 解析失败：${e instanceof Error ? e.message : '未知错误'}`);
      setSheets([]);
      setEditSheets([]);
    }
  }, [content, editable]);

  // 编辑模式：文件切换时清空操作日志并记录新文件（保存后重载 content 不清日志，
  // 由 MarkdownEditor 在保存成功后统一 clearOperations）
  useEffect(() => {
    if (editable && filePath) {
      beginEdit(filePath);
    }
  }, [editable, filePath, beginEdit]);

  const onSheetChange = (idx: number) => setActiveSheet(idx);

  // ---------------- 编辑操作 ----------------
  const mutateActiveSheet = (fn: (rows: string[][]) => string[][]) => {
    setEditSheets((prev) => prev.map((s, idx) => (idx === activeSheet ? { ...s, rows: fn(s.rows) } : s)));
  };

  const handleCommitCell = (r: number, c: number, text: string) => {
    const sheet = editSheets[activeSheet];
    if (!sheet) return;
    const original = sheet.rows[r]?.[c] ?? '';
    if (text === original) return;
    mutateActiveSheet((rows) =>
      rows.map((row, ri) => (ri === r ? row.map((cell, ci) => (ci === c ? text : cell)) : row))
    );
    const { value, kind } = inferCellValue(text);
    pushOperation({ op: 'set_cell', sheet: sheet.name, row: r + 1, col: c + 1, value, kind });
  };

  const handleInsertRow = (beforeIdx: number) => {
    const sheet = editSheets[activeSheet];
    if (!sheet) return;
    const colCount = sheet.rows[0]?.length || 1;
    mutateActiveSheet((rows) => {
      const next = [...rows];
      next.splice(beforeIdx, 0, new Array(colCount).fill(''));
      return next;
    });
    pushOperation({ op: 'insert_row', sheet: sheet.name, index: beforeIdx + 1, count: 1 });
  };

  const handleDeleteRow = (idx: number) => {
    const sheet = editSheets[activeSheet];
    if (!sheet || sheet.rows.length <= 1) return;
    mutateActiveSheet((rows) => {
      const next = [...rows];
      next.splice(idx, 1);
      return next;
    });
    pushOperation({ op: 'delete_row', sheet: sheet.name, index: idx + 1, count: 1 });
  };

  const handleInsertCol = (beforeIdx: number) => {
    const sheet = editSheets[activeSheet];
    if (!sheet) return;
    mutateActiveSheet((rows) => rows.map((row) => {
      const next = [...row];
      next.splice(beforeIdx, 0, '');
      return next;
    }));
    pushOperation({ op: 'insert_col', sheet: sheet.name, index: beforeIdx + 1, count: 1 });
  };

  const handleDeleteCol = (idx: number) => {
    const sheet = editSheets[activeSheet];
    if (!sheet) return;
    const colCount = sheet.rows[0]?.length || 1;
    if (colCount <= 1) return;
    mutateActiveSheet((rows) => rows.map((row) => {
      const next = [...row];
      next.splice(idx, 1);
      return next;
    }));
    pushOperation({ op: 'delete_col', sheet: sheet.name, index: idx + 1, count: 1 });
  };

  const handleAddRow = () => {
    const sheet = editSheets[activeSheet];
    if (!sheet) return;
    const colCount = sheet.rows[0]?.length || 1;
    // 追加到末尾 = 在"原行数+1"行前插入
    pushOperation({ op: 'insert_row', sheet: sheet.name, index: sheet.rows.length + 1, count: 1 });
    mutateActiveSheet((rows) => [...rows, new Array(colCount).fill('')]);
  };

  const handleAddCol = () => {
    const sheet = editSheets[activeSheet];
    if (!sheet) return;
    const colCount = sheet.rows[0]?.length || 1;
    pushOperation({ op: 'insert_col', sheet: sheet.name, index: colCount + 1, count: 1 });
    mutateActiveSheet((rows) => rows.map((row) => [...row, '']));
  };

  const handleAddSheet = (name: string) => {
    if (editSheets.some((s) => s.name === name)) {
      window.alert(`工作表「${name}」已存在`);
      return;
    }
    setEditSheets((prev) => [...prev, { name, rows: [['']] }]);
    setActiveSheet(editSheets.length);
    pushOperation({ op: 'add_sheet', title: name });
  };

  const handleRenameSheet = (idx: number, name: string) => {
    if (editSheets.some((s, i) => i !== idx && s.name === name)) {
      window.alert(`工作表「${name}」已存在`);
      return;
    }
    setEditSheets((prev) => prev.map((s, i) => (i === idx ? { ...s, name } : s)));
    pushOperation({ op: 'rename_sheet', from_sheet: editSheets[idx].name, to_title: name });
  };

  const handleRemoveSheet = (idx: number) => {
    if (editSheets.length <= 1) return;
    const removed = editSheets[idx];
    setEditSheets((prev) => prev.filter((_, i) => i !== idx));
    setActiveSheet((prev) => (prev >= idx && prev > 0 ? prev - 1 : prev));
    pushOperation({ op: 'remove_sheet', sheet: removed.name });
  };

  // 无内容时显示占位提示
  if (!content) {
    return (
      <div className="flex items-center justify-center h-full text-ink-muted">
        <div className="text-center">
          <div className="text-lg mb-2">无 Excel 内容</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* 顶部工具栏：显示文件名 + 编辑状态 */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface-1">
        <div className="text-sm text-ink-muted">
          {fileName || 'Excel 文档'}
          {editable && <span className="ml-2 text-xs text-accent-info">编辑模式（保存保留图片与样式）</span>}
        </div>
      </div>

      {editable ? (
        <ExcelEditorGrid
          sheets={editSheets}
          activeSheet={activeSheet}
          onSheetChange={onSheetChange}
          onCommitCell={handleCommitCell}
          onInsertRow={handleInsertRow}
          onDeleteRow={handleDeleteRow}
          onInsertCol={handleInsertCol}
          onDeleteCol={handleDeleteCol}
          onAddRow={handleAddRow}
          onAddCol={handleAddCol}
          onAddSheet={handleAddSheet}
          onRenameSheet={handleRenameSheet}
          onRemoveSheet={handleRemoveSheet}
        />
      ) : (
        <ExcelReadOnlyView
          sheets={sheets}
          activeSheet={activeSheet}
          error={error}
          onSheetChange={onSheetChange}
        />
      )}

      {/* 编辑模式解析错误兜底展示 */}
      {editable && error && (
        <div className="text-center text-danger py-2 text-sm">{error}</div>
      )}
    </div>
  );
};

export default ExcelViewer;
