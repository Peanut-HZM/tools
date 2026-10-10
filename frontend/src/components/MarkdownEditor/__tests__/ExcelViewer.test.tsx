/**
 * ExcelViewer 单元测试
 *
 * 使用真实 xlsx 库构造 base64 数据（不 mock），覆盖：
 * 只读模式：
 * - 无内容占位 / 表格渲染 / 文件名显示 / 多 Sheet 切换 / 解析失败 / 空 Sheet
 * 编辑模式（.xlsx + 非 readOnly）：
 * - 可编辑网格渲染（input）
 * - 单元格编辑 → set_cell 操作（含类型推断：数字/文本/公式/布尔/前导零）
 * - 插入/删除行列 → 对应操作
 * - 新增/重命名/删除 Sheet → 对应操作
 * - readOnly 或非 .xlsx 文件保持只读
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import * as XLSX from 'xlsx';
import ExcelViewer, { inferCellValue } from '../ExcelViewer';
import { ExcelEditorProvider, useExcelEditorStore } from '../../../stores/excelEditorStore';
import type { ExcelOperation } from '../../../types/markdownEditor';

/** 用真实 xlsx 构造 base64 编码的 Excel 数据 */
function makeXlsxBase64(sheets: Record<string, (string | number | boolean)[][]>): string {
  const wb = XLSX.utils.book_new();
  for (const [name, aoa] of Object.entries(sheets)) {
    const ws = XLSX.utils.aoa_to_sheet(aoa);
    XLSX.utils.book_append_sheet(wb, ws, name);
  }
  return XLSX.write(wb, { type: 'base64', bookType: 'xlsx' });
}

const SINGLE_SHEET_B64 = makeXlsxBase64({
  Sheet1: [
    ['Name', 'Age'],
    ['Alice', 25],
    ['Bob', 30],
  ],
});

const MULTI_SHEET_B64 = makeXlsxBase64({
  Users: [
    ['Name', 'Age'],
    ['Alice', 25],
  ],
  Settings: [
    ['Key', 'Value'],
    ['theme', 'dark'],
  ],
});

/**
 * 测试工具：包裹 ExcelEditorProvider，并通过探针组件暴露 store 状态
 */
function renderWithProvider(ui: React.ReactElement) {
  let latest: ReturnType<typeof useExcelEditorStore> | null = null;
  const Probe = () => {
    latest = useExcelEditorStore();
    return null;
  };
  const utils = render(
    <ExcelEditorProvider>
      {ui}
      <Probe />
    </ExcelEditorProvider>
  );
  return {
    ...utils,
    getOperations: (): ExcelOperation[] => latest?.operations ?? [],
    hasPending: (): boolean => latest?.hasPendingOperations ?? false,
  };
}

/** 编辑模式的默认 props（本地 .xlsx 文件） */
const editableProps = {
  filePath: 'docs/data.xlsx',
  fileName: 'data.xlsx',
};

describe('ExcelViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.prompt = vi.fn();
    window.confirm = vi.fn(() => true);
    window.alert = vi.fn();
  });

  afterEach(() => {
    cleanup();
  });

  // ---------------------------------------------------------------------------
  // 只读模式（历史行为保持）
  // ---------------------------------------------------------------------------
  describe('只读模式 - 无内容场景', () => {
    it('显示占位提示当 content 为 null', () => {
      renderWithProvider(<ExcelViewer content={null} />);
      expect(screen.getByText('无 Excel 内容')).toBeTruthy();
    });

    it('不渲染表格当 content 为 null', () => {
      renderWithProvider(<ExcelViewer content={null} />);
      expect(screen.queryByRole('table')).toBeNull();
    });

    it('不显示工具栏当 content 为 null', () => {
      renderWithProvider(<ExcelViewer content={null} />);
      expect(screen.queryByText('Excel 文档')).toBeNull();
    });
  });

  describe('只读模式 - 有内容场景', () => {
    it('解析 base64 数据并渲染表格', () => {
      renderWithProvider(<ExcelViewer content={SINGLE_SHEET_B64} fileName="data.xlsx" />);
      // 表头
      expect(screen.getByText('Name')).toBeTruthy();
      expect(screen.getByText('Age')).toBeTruthy();
      // 数据行
      expect(screen.getByText('Alice')).toBeTruthy();
      expect(screen.getByText('Bob')).toBeTruthy();
    });

    it('显示文件名', () => {
      renderWithProvider(<ExcelViewer content={SINGLE_SHEET_B64} fileName="report.xlsx" />);
      expect(screen.getByText('report.xlsx')).toBeTruthy();
    });

    it('未提供文件名时显示默认标签', () => {
      renderWithProvider(<ExcelViewer content={SINGLE_SHEET_B64} />);
      expect(screen.getByText('Excel 文档')).toBeTruthy();
    });

    it('编辑模式的 .xlsx 通过 readOnly 强制只读时渲染纯表格', () => {
      renderWithProvider(
        <ExcelViewer content={SINGLE_SHEET_B64} {...editableProps} readOnly={true} />
      );
      // 只读表格为纯文本单元格，不渲染 input
      expect(screen.getByText('Alice')).toBeTruthy();
      expect(screen.queryByDisplayValue('Alice')).toBeNull();
    });

    it('非 .xlsx 文件保持只读', () => {
      renderWithProvider(
        <ExcelViewer content={SINGLE_SHEET_B64} filePath="docs/data.csv" readOnly={false} />
      );
      expect(screen.getByText('Alice')).toBeTruthy();
      expect(screen.queryByDisplayValue('Alice')).toBeNull();
    });
  });

  describe('只读模式 - 多 Sheet 切换', () => {
    it('多 Sheet 时显示标签栏并切换', () => {
      renderWithProvider(<ExcelViewer content={MULTI_SHEET_B64} />);
      expect(screen.getByText('Users')).toBeTruthy();
      expect(screen.getByText('Settings')).toBeTruthy();
      expect(screen.getByText('Alice')).toBeTruthy();

      fireEvent.click(screen.getByText('Settings'));
      expect(screen.getByText('theme')).toBeTruthy();
    });

    it('单 Sheet 时不显示标签栏', () => {
      renderWithProvider(<ExcelViewer content={SINGLE_SHEET_B64} />);
      expect(screen.queryByText('Sheet1')).toBeNull();
    });
  });

  describe('只读模式 - 错误处理', () => {
    it('解析失败时显示错误信息', () => {
      // 带 zip 魔数但内容损坏的字节：SheetJS 无法解析
      const brokenZip = btoa('PK\u0003\u0004broken-not-a-zip');
      renderWithProvider(<ExcelViewer content={brokenZip} />);
      expect(screen.getByText(/Excel 解析失败/)).toBeTruthy();
    });

    it('解析失败时不渲染表格', () => {
      const brokenZip = btoa('PK\u0003\u0004broken-not-a-zip');
      renderWithProvider(<ExcelViewer content={brokenZip} />);
      expect(screen.queryByRole('table')).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // 编辑模式
  // ---------------------------------------------------------------------------
  describe('编辑模式 - 渲染', () => {
    it('.xlsx 且非 readOnly 时渲染可编辑网格', () => {
      renderWithProvider(<ExcelViewer content={SINGLE_SHEET_B64} {...editableProps} />);
      // 单元格渲染为 input
      expect(screen.getByDisplayValue('Name')).toBeTruthy();
      expect(screen.getByDisplayValue('Alice')).toBeTruthy();
      expect(screen.getByDisplayValue('25')).toBeTruthy();
    });

    it('编辑模式显示提示与工具栏', () => {
      renderWithProvider(<ExcelViewer content={SINGLE_SHEET_B64} {...editableProps} />);
      expect(screen.getByText(/编辑模式/)).toBeTruthy();
      expect(screen.getByText('+ 上方插入行')).toBeTruthy();
      expect(screen.getByText('+ 行（末尾）')).toBeTruthy();
    });

    it('多 Sheet 显示标签（编辑模式始终显示标签栏）', () => {
      renderWithProvider(<ExcelViewer content={MULTI_SHEET_B64} {...editableProps} />);
      expect(screen.getByText('Users')).toBeTruthy();
      expect(screen.getByText('Settings')).toBeTruthy();
    });
  });

  describe('编辑模式 - 单元格编辑', () => {
    it('修改单元格触发 set_cell 操作（坐标 1-based）', () => {
      const { getOperations, hasPending } = renderWithProvider(
        <ExcelViewer content={SINGLE_SHEET_B64} {...editableProps} />
      );
      const input = screen.getByDisplayValue('Alice') as HTMLInputElement;
      fireEvent.change(input, { target: { value: 'Alice2' } });
      fireEvent.blur(input);

      const ops = getOperations();
      expect(ops.length).toBe(1);
      expect(ops[0]).toMatchObject({
        op: 'set_cell',
        sheet: 'Sheet1',
        row: 2,
        col: 1,
        value: 'Alice2',
        kind: 'str',
      });
      expect(hasPending()).toBe(true);
    });

    it('纯数字输入推断为 number', () => {
      const { getOperations } = renderWithProvider(
        <ExcelViewer content={SINGLE_SHEET_B64} {...editableProps} />
      );
      const input = screen.getByDisplayValue('25') as HTMLInputElement;
      fireEvent.change(input, { target: { value: '30' } });
      fireEvent.blur(input);

      expect(getOperations()[0]).toMatchObject({ value: '30', kind: 'number' });
    });

    it('公式输入推断为 formula', () => {
      const { getOperations } = renderWithProvider(
        <ExcelViewer content={SINGLE_SHEET_B64} {...editableProps} />
      );
      const input = screen.getByDisplayValue('25') as HTMLInputElement;
      fireEvent.change(input, { target: { value: '=SUM(B1:B2)' } });
      fireEvent.blur(input);

      expect(getOperations()[0]).toMatchObject({ value: '=SUM(B1:B2)', kind: 'formula' });
    });

    it('前导零数字保持文本类型', () => {
      const { getOperations } = renderWithProvider(
        <ExcelViewer content={SINGLE_SHEET_B64} {...editableProps} />
      );
      const input = screen.getByDisplayValue('Alice') as HTMLInputElement;
      fireEvent.change(input, { target: { value: '0012' } });
      fireEvent.blur(input);

      expect(getOperations()[0]).toMatchObject({ value: '0012', kind: 'str' });
    });

    it('值未变化时不产生操作', () => {
      const { getOperations, hasPending } = renderWithProvider(
        <ExcelViewer content={SINGLE_SHEET_B64} {...editableProps} />
      );
      const input = screen.getByDisplayValue('Alice') as HTMLInputElement;
      fireEvent.change(input, { target: { value: 'Alice' } });
      fireEvent.blur(input);

      expect(getOperations().length).toBe(0);
      expect(hasPending()).toBe(false);
    });
  });

  describe('编辑模式 - 行列操作', () => {
    function renderGrid() {
      const utils = renderWithProvider(
        <ExcelViewer content={SINGLE_SHEET_B64} {...editableProps} />
      );
      // 选中一个单元格以启用插入/删除按钮
      const cell = screen.getByDisplayValue('Alice');
      fireEvent.click(cell);
      return utils;
    }

    it('上方插入行产生 insert_row 操作（index=2）', () => {
      const { getOperations } = renderGrid();
      fireEvent.click(screen.getByText('+ 上方插入行'));

      const ops = getOperations();
      expect(ops[0]).toMatchObject({ op: 'insert_row', sheet: 'Sheet1', index: 2, count: 1 });
    });

    it('删除行产生 delete_row 操作', () => {
      const { getOperations } = renderGrid();
      fireEvent.click(screen.getByText('− 删除行'));

      expect(getOperations()[0]).toMatchObject({ op: 'delete_row', index: 2, count: 1 });
    });

    it('左侧插入列产生 insert_col 操作', () => {
      const { getOperations } = renderGrid();
      fireEvent.click(screen.getByText('+ 左侧插入列'));

      expect(getOperations()[0]).toMatchObject({ op: 'insert_col', index: 1, count: 1 });
    });

    it('删除列产生 delete_col 操作', () => {
      const { getOperations } = renderGrid();
      fireEvent.click(screen.getByText('− 删除列'));

      expect(getOperations()[0]).toMatchObject({ op: 'delete_col', index: 1, count: 1 });
    });

    it('末尾添加行/列', () => {
      const { getOperations } = renderGrid();
      fireEvent.click(screen.getByText('+ 行（末尾）'));
      fireEvent.click(screen.getByText('+ 列（末尾）'));

      const ops = getOperations();
      expect(ops[0]).toMatchObject({ op: 'insert_row', index: 4 });
      expect(ops[1]).toMatchObject({ op: 'insert_col', index: 3 });
    });

    it('插入行后新行单元格渲染为空 input', () => {
      renderGrid();
      fireEvent.click(screen.getByText('+ 上方插入行'));
      // 第 2 行现在是空行
      expect(screen.getByTestId('excel-cell-1-0')).toBeTruthy();
      expect((screen.getByTestId('excel-cell-1-0') as HTMLInputElement).value).toBe('');
      // 原 Alice 移到第 3 行
      expect((screen.getByTestId('excel-cell-2-0') as HTMLInputElement).value).toBe('Alice');
    });
  });

  describe('编辑模式 - Sheet 操作', () => {
    function renderMulti() {
      return renderWithProvider(
        <ExcelViewer content={MULTI_SHEET_B64} {...editableProps} />
      );
    }

    it('新增 Sheet 产生 add_sheet 操作并切换', () => {
      vi.mocked(window.prompt).mockReturnValue('新页');
      const { getOperations } = renderMulti();

      fireEvent.click(screen.getByTitle('新增工作表'));

      expect(getOperations()[0]).toMatchObject({ op: 'add_sheet', title: '新页' });
      // 已切换到新 sheet：显示空单元格网格
      expect(screen.getByTestId('excel-cell-0-0')).toBeTruthy();
    });

    it('重命名 Sheet 产生 rename_sheet 操作', () => {
      vi.mocked(window.prompt).mockReturnValue('改名');
      const { getOperations } = renderMulti();

      fireEvent.doubleClick(screen.getByText('Settings'));

      expect(getOperations()[0]).toMatchObject({
        op: 'rename_sheet',
        from_sheet: 'Settings',
        to_title: '改名',
      });
    });

    it('删除 Sheet 产生 remove_sheet 操作', () => {
      const { getOperations } = renderMulti();
      const delBtns = screen.getAllByTitle('删除工作表');
      fireEvent.click(delBtns[1]); // 删除 Settings

      expect(getOperations()[0]).toMatchObject({ op: 'remove_sheet', sheet: 'Settings' });
    });

    it('切换单个 Sheet 时不显示删除按钮（至少保留一个）', () => {
      renderWithProvider(<ExcelViewer content={SINGLE_SHEET_B64} {...editableProps} />);
      expect(screen.queryByTitle('删除工作表')).toBeNull();
    });
  });

  describe('inferCellValue 单元测试', () => {
    it('各类型推断', () => {
      expect(inferCellValue('123')).toEqual({ value: '123', kind: 'number' });
      expect(inferCellValue('-4.5')).toEqual({ value: '-4.5', kind: 'number' });
      expect(inferCellValue('1e3')).toEqual({ value: '1e3', kind: 'number' });
      expect(inferCellValue('TRUE')).toEqual({ value: 'TRUE', kind: 'bool' });
      expect(inferCellValue('false')).toEqual({ value: 'false', kind: 'bool' });
      expect(inferCellValue('=A1+B1')).toEqual({ value: '=A1+B1', kind: 'formula' });
      expect(inferCellValue('0012')).toEqual({ value: '0012', kind: 'str' });
      expect(inferCellValue('hello')).toEqual({ value: 'hello', kind: 'str' });
      expect(inferCellValue('')).toEqual({ value: '', kind: 'str' });
      expect(inferCellValue('  spaced  ')).toEqual({ value: '  spaced  ', kind: 'str' });
    });
  });
});
