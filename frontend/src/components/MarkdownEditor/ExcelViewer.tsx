/**
 * ExcelViewer - Excel 文件查看器
 *
 * 使用 SheetJS (xlsx) 解析 Excel 文件并渲染为 HTML 表格。
 * content 接收 base64 编码的 Excel 数据（来自 FileRawContent.data）。
 * 支持多 Sheet 切换。
 */
import React, { useState, useEffect } from 'react';
import * as XLSX from 'xlsx';

/** ExcelViewer 组件接口 */
interface ExcelViewerProps {
  /** base64 编码的 Excel 数据（来自 FileRawContent.data） */
  content: string | null;
  /** 文件名（可选，显示在工具栏） */
  fileName?: string;
}

/** 单个 Sheet 的解析结果 */
interface SheetData {
  /** Sheet 名称 */
  name: string;
  /** 二维数组形式的单元格数据 */
  data: (string | number | boolean | null)[][];
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

const ExcelViewer: React.FC<ExcelViewerProps> = ({ content, fileName }) => {
  const [sheets, setSheets] = useState<SheetData[]>([]);
  const [activeSheet, setActiveSheet] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!content) {
      setSheets([]);
      setActiveSheet(0);
      setError(null);
      return;
    }

    try {
      // 解码 base64 为字节数组
      const bytes = base64ToUint8Array(content);

      // 使用 SheetJS 解析 Excel
      const workbook = XLSX.read(bytes, { type: 'array' });

      // 将每个 Sheet 转换为二维数组
      const sheetData: SheetData[] = workbook.SheetNames.map((name) => {
        const worksheet = workbook.Sheets[name];
        const data = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as (string | number | boolean | null)[][];
        return { name, data };
      });

      setSheets(sheetData);
      setActiveSheet(0);
      setError(null);
    } catch (e) {
      setError(`Excel 解析失败：${e instanceof Error ? e.message : '未知错误'}`);
      setSheets([]);
    }
  }, [content]);

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

  const currentSheet = sheets[activeSheet];

  return (
    <div className="h-full flex flex-col">
      {/* 顶部工具栏：显示文件名 */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface-1">
        <div className="text-sm text-ink-muted">
          {fileName || 'Excel 文档'}
        </div>
      </div>

      {/* Sheet 标签栏：多 Sheet 时显示切换标签 */}
      {sheets.length > 1 && (
        <div className="flex border-b border-border bg-surface-1 overflow-x-auto">
          {sheets.map((sheet, idx) => (
            <button
              key={sheet.name}
              onClick={() => setActiveSheet(idx)}
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
    </div>
  );
};

export default ExcelViewer;
