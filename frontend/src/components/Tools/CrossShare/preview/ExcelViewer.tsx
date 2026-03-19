/**
 * Excel 预览器
 */
import React from 'react';
import * as XLSX from 'xlsx';
import { PreviewProps } from './types';

export const ExcelViewer: React.FC<PreviewProps> = ({ url }) => {
  const [data, setData] = React.useState<Record<string, any>[][]>([]);
  const [sheetNames, setSheetNames] = React.useState<string[]>([]);
  const [currentSheet, setCurrentSheet] = React.useState<string>('');
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);

  React.useEffect(() => {
    const fetchExcel = async () => {
      try {
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error('Failed to fetch Excel file');
        }
        const arrayBuffer = await response.arrayBuffer();
        const workbook = XLSX.read(arrayBuffer, { type: 'array' });

        setSheetNames(workbook.SheetNames);
        if (workbook.SheetNames.length > 0) {
          const firstSheet = workbook.SheetNames[0];
          setCurrentSheet(firstSheet);
          const worksheet = workbook.Sheets[firstSheet];
          const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
          setData(jsonData as Record<string, any>[][]);
        }
      } catch (err) {
        console.error('Failed to load Excel:', err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchExcel();
  }, [url]);

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center text-slate-400">
        加载中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center text-red-400">
        <div className="text-center">
          <div className="text-4xl mb-2">❌</div>
          <div>Excel 加载失败</div>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center text-slate-400">
        空文件
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col bg-slate-800">
      {/* Sheet 选择器 */}
      {sheetNames.length > 1 && (
        <div className="flex-shrink-0 p-4 border-b border-slate-700">
          <select
            value={currentSheet}
            onChange={(e) => {
              setCurrentSheet(e.target.value);
            }}
            className="px-4 py-2 bg-slate-700 border border-slate-600 rounded text-slate-200 focus:outline-none"
          >
            {sheetNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* 表格内容 */}
      <div className="flex-1 overflow-auto">
        <table className="w-full border-collapse">
          <thead className="bg-slate-700 sticky top-0">
            <tr>
              {data[0]?.map((cell, colIndex) => (
                <th
                  key={colIndex}
                  className="px-4 py-2 text-left text-sm font-medium text-slate-200 border border-slate-600"
                >
                  {cell || colIndex}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.slice(1).map((row, rowIndex) => (
              <tr key={rowIndex} className="hover:bg-slate-700/30">
                {row.map((cell, colIndex) => (
                  <td
                    key={colIndex}
                    className="px-4 py-2 text-sm text-slate-300 border border-slate-600"
                  >
                    {cell ?? ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
