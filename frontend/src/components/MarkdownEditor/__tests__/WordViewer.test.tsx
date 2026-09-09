/**
 * WordViewer 单元测试
 *
 * 验证 WordViewer 在不同输入下的渲染行为：
 * - 无内容时显示占位提示
 * - 有内容时调用 mammoth 解析并渲染 HTML
 * - 工具栏显示文件名
 * - 解析失败时显示错误信息
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import WordViewer from '../WordViewer';

/**
 * Mock mammoth 模块
 * 默认返回包含标题和段落的 HTML，每个测试可按需覆盖
 */
vi.mock('mammoth', () => ({
  __esModule: true,
  default: {
    convertToHtml: vi.fn().mockResolvedValue({
      value: '<h1>标题</h1><p>段落内容</p>',
      messages: [],
    }),
  },
}));

// 获取 mock 函数引用，方便在测试中修改返回值
import mammoth from 'mammoth';
const mockConvertToHtml = vi.mocked(mammoth.convertToHtml);

describe('WordViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // 恢复默认 mock 行为
    mockConvertToHtml.mockResolvedValue({
      value: '<h1>标题</h1><p>段落内容</p>',
      messages: [],
    });
  });

  afterEach(() => {
    cleanup();
  });

  describe('无内容场景', () => {
    it('显示占位提示当 content 为 null', () => {
      render(<WordViewer content={null} />);
      expect(screen.getByText('无 Word 内容')).toBeTruthy();
    });

    it('不渲染工具栏当 content 为 null', () => {
      render(<WordViewer content={null} />);
      expect(screen.queryByText('Word 文档')).toBeNull();
    });

    it('不调用 mammoth 当 content 为 null', () => {
      render(<WordViewer content={null} />);
      expect(mockConvertToHtml).not.toHaveBeenCalled();
    });
  });

  describe('有内容场景', () => {
    it('调用 mammoth.convertToHtml 解析 base64 数据', async () => {
      render(<WordViewer content="base64data" fileName="doc.docx" />);
      await waitFor(() => {
        expect(mockConvertToHtml).toHaveBeenCalledTimes(1);
      });
      // 验证传入的是包含 ArrayBuffer 的对象
      const callArg = mockConvertToHtml.mock.calls[0][0] as { arrayBuffer: ArrayBuffer };
      expect(callArg.arrayBuffer).toBeInstanceOf(ArrayBuffer);
    });

    it('渲染 Word 转换后的 HTML 内容', async () => {
      render(<WordViewer content="base64data" fileName="doc.docx" />);
      await waitFor(() => {
        expect(screen.getByText('标题')).toBeTruthy();
      });
      expect(screen.getByText('段落内容')).toBeTruthy();
    });

    it('显示文件名', async () => {
      render(<WordViewer content="base64data" fileName="report.docx" />);
      // 文件名在工具栏中同步渲染
      expect(screen.getByText('report.docx')).toBeTruthy();
    });

    it('未提供文件名时显示默认标签', async () => {
      render(<WordViewer content="base64data" />);
      expect(screen.getByText('Word 文档')).toBeTruthy();
    });

    it('显示加载状态直到 mammoth 完成转换', () => {
      // 让 mock 返回一个永远不 resolve 的 Promise，模拟加载中
      mockConvertToHtml.mockReturnValue(new Promise(() => {}));
      render(<WordViewer content="base64data" />);
      expect(screen.getByText('加载 Word 文档中...')).toBeTruthy();
    });
  });

  describe('错误处理', () => {
    it('解析失败时显示错误信息', async () => {
      mockConvertToHtml.mockRejectedValue(new Error('Invalid file format'));
      render(<WordViewer content="baddata" />);
      await waitFor(() => {
        expect(screen.getByText(/Word 解析失败/)).toBeTruthy();
      });
      expect(screen.getByText(/Invalid file format/)).toBeTruthy();
    });

    it('解析失败时不渲染 HTML 内容', async () => {
      mockConvertToHtml.mockRejectedValue(new Error('Corrupted'));
      render(<WordViewer content="baddata" />);
      await waitFor(() => {
        expect(screen.getByText(/Word 解析失败/)).toBeTruthy();
      });
      expect(screen.queryByText('标题')).toBeNull();
    });

    it('非 Error 异常显示未知错误', async () => {
      mockConvertToHtml.mockRejectedValue('string error');
      render(<WordViewer content="baddata" />);
      await waitFor(() => {
        expect(screen.getByText(/Word 解析失败：未知错误/)).toBeTruthy();
      });
    });
  });

  describe('转换警告', () => {
    it('mammoth 返回警告时记录到 console.warn', async () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      mockConvertToHtml.mockResolvedValue({
        value: '<p>内容</p>',
        messages: [{ type: 'warning', message: '不支持的样式' } as unknown as never],
      });

      render(<WordViewer content="base64data" />);

      await waitFor(() => {
        expect(screen.getByText('内容')).toBeTruthy();
      });
      expect(warnSpy).toHaveBeenCalledWith('Word 转换警告:', expect.any(Array));

      warnSpy.mockRestore();
    });
  });
});
