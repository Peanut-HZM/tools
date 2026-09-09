/**
 * ExcelViewer 单元测试
 *
 * 验证 ExcelViewer 在不同输入下的渲染行为：
 * - 无内容时显示占位提示
 * - 有内容时解析并渲染表格数据
 * - 工具栏显示文件名
 * - 多 Sheet 切换
 * - 解析失败时显示错误信息
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import ExcelViewer from '../ExcelViewer';

/** 默认 mock 数据：单 Sheet，2 行 2 列 */
const MOCK_SINGLE_SHEET = {
  SheetNames: ['Sheet1'],
  Sheets: {
    Sheet1: { '!ref': 'A1:B2' },
  },
};

/** 默认 mock 数据：sheet_to_json 返回二维数组 */
const MOCK_DATA_SINGLE: (string | number)[][] = [
  ['Name', 'Age'],
  ['Alice', 25],
  ['Bob', 30],
];

/** 多 Sheet mock 数据 */
const MOCK_MULTI_SHEET = {
  SheetNames: ['Users', 'Settings'],
  Sheets: {
    Users: { '!ref': 'A1:B2' },
    Settings: { '!ref': 'A1:B1' },
  },
};

/** 不同 Sheet 返回不同数据 */
const MOCK_DATA_MAP: Record<string, (string | number)[][]> = {
  Users: [
    ['Name', 'Age'],
    ['Alice', 25],
  ],
  Settings: [
    ['Key', 'Value'],
    ['theme', 'dark'],
  ],
};

/** 空 Sheet mock 数据 */
const MOCK_EMPTY_SHEET = {
  SheetNames: ['Empty'],
  Sheets: {
    Empty: { '!ref': 'A1' },
  },
};

/**
 * Mock xlsx 模块
 * read() 返回预设的 workbook，sheet_to_json() 按 Sheet 名返回对应数据
 */
vi.mock('xlsx', () => {
  // 通过全局变量控制 mock 行为（每个测试可覆盖）
  return {
    read: vi.fn(() => MOCK_SINGLE_SHEET),
    utils: {
      sheet_to_json: vi.fn((_sheet: unknown, _opts: unknown) => MOCK_DATA_SINGLE),
    },
  };
});

// 获取 mock 函数的引用，方便在测试中修改返回值
import * as XLSX from 'xlsx';
const mockRead = vi.mocked(XLSX.read);
const mockSheetToJson = vi.mocked(XLSX.utils.sheet_to_json);

/**
 * 配置 mock 行为：根据 Sheet 名返回对应数据
 */
function setupMockSheetData(dataMap: Record<string, (string | number)[][]>) {
  mockSheetToJson.mockImplementation((sheet: unknown) => {
    // 通过 Sheet 的 !ref 或其他标识查找对应的数据
    // 这里简化处理：按 SheetNames 顺序匹配
    for (const [name, data] of Object.entries(dataMap)) {
      // 通过检查 workbook.Sheets[name] 是否等于传入的 sheet 来匹配
      // 由于 mock 中 sheet 是简单对象，使用 JSON 对比
      if (JSON.stringify(sheet) === JSON.stringify(MOCK_MULTI_SHEET.Sheets[name])) {
        return data;
      }
    }
    // 默认返回第一条
    return Object.values(dataMap)[0];
  });
}

describe('ExcelViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // 恢复默认 mock 行为
    mockRead.mockReturnValue(MOCK_SINGLE_SHEET);
    mockSheetToJson.mockReturnValue(MOCK_DATA_SINGLE);
  });

  afterEach(() => {
    cleanup();
  });

  describe('无内容场景', () => {
    it('显示占位提示当 content 为 null', () => {
      render(<ExcelViewer content={null} />);
      expect(screen.getByText('无 Excel 内容')).toBeTruthy();
    });

    it('不渲染表格当 content 为 null', () => {
      render(<ExcelViewer content={null} />);
      expect(screen.queryByRole('table')).toBeNull();
    });

    it('不显示工具栏当 content 为 null', () => {
      render(<ExcelViewer content={null} />);
      expect(screen.queryByText('Excel 文档')).toBeNull();
    });
  });

  describe('有内容场景', () => {
    it('解析 base64 数据并渲染表格', () => {
      render(<ExcelViewer content="base64data" fileName="data.xlsx" />);
      // 表头
      expect(screen.getByText('Name')).toBeTruthy();
      expect(screen.getByText('Age')).toBeTruthy();
      // 数据行
      expect(screen.getByText('Alice')).toBeTruthy();
      expect(screen.getByText('25')).toBeTruthy();
      expect(screen.getByText('Bob')).toBeTruthy();
      expect(screen.getByText('30')).toBeTruthy();
    });

    it('调用 XLSX.read 解析数据', () => {
      render(<ExcelViewer content="base64data" />);
      expect(mockRead).toHaveBeenCalledTimes(1);
      // 验证传入的是 Uint8Array
      const callArg = mockRead.mock.calls[0][0];
      expect(callArg).toBeInstanceOf(Uint8Array);
    });

    it('显示文件名', () => {
      render(<ExcelViewer content="base64data" fileName="report.xlsx" />);
      expect(screen.getByText('report.xlsx')).toBeTruthy();
    });

    it('未提供文件名时显示默认标签', () => {
      render(<ExcelViewer content="base64data" />);
      expect(screen.getByText('Excel 文档')).toBeTruthy();
    });
  });

  describe('多 Sheet 切换', () => {
    it('多 Sheet 时显示标签栏', () => {
      mockRead.mockReturnValue(MOCK_MULTI_SHEET);
      setupMockSheetData(MOCK_DATA_MAP);

      render(<ExcelViewer content="base64data" />);
      expect(screen.getByText('Users')).toBeTruthy();
      expect(screen.getByText('Settings')).toBeTruthy();
    });

    it('默认显示第一个 Sheet 的数据', () => {
      mockRead.mockReturnValue(MOCK_MULTI_SHEET);
      setupMockSheetData(MOCK_DATA_MAP);

      render(<ExcelViewer content="base64data" />);
      // Users sheet 的数据
      expect(screen.getByText('Alice')).toBeTruthy();
    });

    it('点击标签切换到对应 Sheet', () => {
      mockRead.mockReturnValue(MOCK_MULTI_SHEET);
      setupMockSheetData(MOCK_DATA_MAP);

      render(<ExcelViewer content="base64data" />);
      // 初始显示 Users 数据
      expect(screen.getByText('Alice')).toBeTruthy();

      // 点击 Settings 标签
      fireEvent.click(screen.getByText('Settings'));

      // 应显示 Settings 数据
      expect(screen.getByText('Key')).toBeTruthy();
      expect(screen.getByText('theme')).toBeTruthy();
    });

    it('单 Sheet 时不显示标签栏', () => {
      mockRead.mockReturnValue(MOCK_SINGLE_SHEET);
      mockSheetToJson.mockReturnValue(MOCK_DATA_SINGLE);

      render(<ExcelViewer content="base64data" />);
      // 只有 Sheet1 一个 Sheet，不应有切换按钮
      expect(screen.queryByText('Sheet1')).toBeNull();
    });
  });

  describe('错误处理', () => {
    it('解析失败时显示错误信息', () => {
      mockRead.mockImplementation(() => {
        throw new Error('Invalid file format');
      });

      render(<ExcelViewer content="baddata" />);
      expect(screen.getByText(/Excel 解析失败/)).toBeTruthy();
      expect(screen.getByText(/Invalid file format/)).toBeTruthy();
    });

    it('解析失败时不渲染表格', () => {
      mockRead.mockImplementation(() => {
        throw new Error('Corrupted');
      });

      render(<ExcelViewer content="baddata" />);
      expect(screen.queryByRole('table')).toBeNull();
    });
  });

  describe('空数据场景', () => {
    it('Sheet 无数据时显示提示', () => {
      mockRead.mockReturnValue(MOCK_EMPTY_SHEET);
      mockSheetToJson.mockReturnValue([]);

      render(<ExcelViewer content="base64data" />);
      expect(screen.getByText('当前 Sheet 无数据')).toBeTruthy();
    });
  });
});
