/**
 * Excel Editor Store - 管理 Excel 编辑操作与未保存状态（React Context）
 *
 * Excel 编辑保存采用"操作日志"协议：前端记录用户编辑动作（ExcelOperation 列表），
 * 保存时整体提交给后端，由后端基于原 .xlsx 文件顺序应用（openpyxl），
 * 从而保留内嵌图片、单元格样式等前端无法完整回写的内容。
 *
 * operations 的坐标始终基于"当前最新矩阵"，且按产生顺序排列，
 * 与后端顺序应用时的坐标系演化一致。
 */
import { createContext, useContext, useState, useCallback, useMemo, ReactNode } from 'react';
import type { ExcelOperation } from '../types/markdownEditor';

export interface ExcelEditorState {
  /** 当前编辑操作对应的文件路径（用于防止跨文件误用操作日志） */
  filePath: string | null;
  /** 按时间顺序累积的编辑操作 */
  operations: ExcelOperation[];
}

export interface ExcelEditorActions {
  /** 切换编辑目标文件：路径变化时清空操作日志并记录新路径 */
  beginEdit: (filePath: string) => void;
  /** 追加一条编辑操作 */
  pushOperation: (op: ExcelOperation) => void;
  /** 保存成功或放弃编辑后清空操作日志 */
  clearOperations: () => void;
}

export interface ExcelEditorGetters {
  /** 是否存在未保存的 Excel 编辑 */
  hasPendingOperations: boolean;
}

export type ExcelEditorContextType = ExcelEditorState & ExcelEditorActions & ExcelEditorGetters;

const ExcelEditorContext = createContext<ExcelEditorContextType | null>(null);

export function ExcelEditorProvider({ children }: { children: ReactNode }) {
  const [filePath, setFilePath] = useState<string | null>(null);
  const [operations, setOperations] = useState<ExcelOperation[]>([]);

  const beginEdit = useCallback((newPath: string) => {
    setFilePath((prev) => {
      if (prev !== newPath) {
        setOperations([]);
      }
      return newPath;
    });
  }, []);

  const pushOperation = useCallback((op: ExcelOperation) => {
    setOperations((prev) => [...prev, op]);
  }, []);

  const clearOperations = useCallback(() => {
    setOperations([]);
  }, []);

  const hasPendingOperations = useMemo(() => operations.length > 0, [operations]);

  const value: ExcelEditorContextType = {
    filePath,
    operations,
    beginEdit,
    pushOperation,
    clearOperations,
    hasPendingOperations,
  };

  return (
    <ExcelEditorContext.Provider value={value}>
      {children}
    </ExcelEditorContext.Provider>
  );
}

export function useExcelEditorStore(): ExcelEditorContextType {
  const context = useContext(ExcelEditorContext);
  if (!context) {
    throw new Error('useExcelEditorStore must be used within an ExcelEditorProvider');
  }
  return context;
}

export { ExcelEditorContext };
