/**
 * WordViewer 单元测试
 *
 * 验证 WordViewer 按文件真实格式分流的行为：
 * - 无内容时显示占位提示
 * - .docx（zip）调用 mammoth 解析并内联渲染 HTML
 * - MHTML 形式的 .doc（Confluence / Outlook 导出）提取 HTML 并用 sandbox iframe 渲染
 * - 旧版二进制 .doc（OLE2）显示明确的不可预览提示，且不会误调用 mammoth
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

/** 构造带真实 zip 文件头的 docx base64（mammoth 本身被 mock，无需完整 zip） */
function docxBase64(): string {
  return btoa(String.fromCharCode(0x50, 0x4b, 0x03, 0x04, 0x14, 0x00, 0x00, 0x00));
}

/** 构造旧版二进制 doc（OLE2 复合文档头）base64 */
function legacyDocBase64(): string {
  return btoa(
    String.fromCharCode(0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1, 0x00, 0x00),
  );
}

/** MHTML 形式的 .doc 样本（Confluence 导出），内容全 ASCII，中文用 QP 编码 */
const MHTML_SAMPLE = [
  'MIME-Version: 1.0',
  'Content-Type: multipart/related; boundary="BOUND"',
  '',
  '--BOUND',
  'Content-Type: text/html; charset=UTF-8',
  'Content-Transfer-Encoding: quoted-printable',
  'Content-Location: file:///C:/exported.html',
  '',
  '<html><body><h1>=E6=A0=87=E9=A2=98</h1><p>=E6=AE=B5=E8=90=BD</p></body></html>',
  '--BOUND--',
  '',
].join('\r\n');

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

  describe('docx 场景', () => {
    it('调用 mammoth.convertToHtml 解析 docx 数据', async () => {
      render(<WordViewer content={docxBase64()} fileName="doc.docx" />);
      await waitFor(() => {
        expect(mockConvertToHtml).toHaveBeenCalledTimes(1);
      });
      // 验证传入的是包含 ArrayBuffer 的对象
      const callArg = mockConvertToHtml.mock.calls[0][0] as { arrayBuffer: ArrayBuffer };
      expect(callArg.arrayBuffer).toBeInstanceOf(ArrayBuffer);
    });

    it('渲染 Word 转换后的 HTML 内容', async () => {
      render(<WordViewer content={docxBase64()} fileName="doc.docx" />);
      await waitFor(() => {
        expect(screen.getByText('标题')).toBeTruthy();
      });
      expect(screen.getByText('段落内容')).toBeTruthy();
    });

    it('显示文件名', async () => {
      render(<WordViewer content={docxBase64()} fileName="report.docx" />);
      // 文件名在工具栏中同步渲染
      expect(screen.getByText('report.docx')).toBeTruthy();
    });

    it('未提供文件名时显示默认标签', async () => {
      render(<WordViewer content={docxBase64()} />);
      expect(screen.getByText('Word 文档')).toBeTruthy();
    });

    it('显示加载状态直到 mammoth 完成转换', () => {
      // 让 mock 返回一个永远不 resolve 的 Promise，模拟加载中
      mockConvertToHtml.mockReturnValue(new Promise(() => {}));
      render(<WordViewer content={docxBase64()} />);
      expect(screen.getByText('加载 Word 文档中...')).toBeTruthy();
    });
  });

  describe('MHTML 形式的 .doc', () => {
    it('提取 HTML 并用 iframe 渲染，不调用 mammoth', async () => {
      const { container } = render(
        <WordViewer content={btoa(MHTML_SAMPLE)} fileName="export.doc" />,
      );

      const iframe = await waitFor(() => {
        const el = container.querySelector('iframe');
        expect(el).toBeTruthy();
        return el as HTMLIFrameElement;
      });

      expect(mockConvertToHtml).not.toHaveBeenCalled();
      // sandbox 为空串：禁止脚本执行，仅允许同源样式渲染
      expect(iframe.getAttribute('sandbox')).toBe('');
      expect(iframe.getAttribute('srcdoc')).toContain('<h1>标题</h1>');
      expect(iframe.getAttribute('srcdoc')).toContain('<p>段落</p>');
      // 工具栏显示文件名
      expect(screen.getByText('export.doc')).toBeTruthy();
    });

    it('清洗掉脚本标签后再渲染', async () => {
      const withScript = MHTML_SAMPLE.replace(
        '<h1>=E6=A0=87=E9=A2=98</h1>',
        '<script>alert(1)</script><h1>=E6=A0=87=E9=A2=98</h1>',
      );
      const { container } = render(<WordViewer content={btoa(withScript)} />);

      const iframe = await waitFor(() => {
        const el = container.querySelector('iframe');
        expect(el).toBeTruthy();
        return el as HTMLIFrameElement;
      });

      expect(iframe.getAttribute('srcdoc')).not.toContain('<script');
    });
  });

  describe('旧版二进制 .doc', () => {
    it('显示不可预览提示且不调用 mammoth', async () => {
      render(<WordViewer content={legacyDocBase64()} fileName="legacy.doc" />);

      await waitFor(() => {
        expect(screen.getByText('无法预览该 Word 文件')).toBeTruthy();
      });
      expect(screen.getByText(/旧版二进制 Word/)).toBeTruthy();
      expect(mockConvertToHtml).not.toHaveBeenCalled();
    });
  });

  describe('错误处理', () => {
    it('解析失败时显示错误信息', async () => {
      mockConvertToHtml.mockRejectedValue(new Error('Invalid file format'));
      render(<WordViewer content={docxBase64()} />);
      await waitFor(() => {
        expect(screen.getByText(/Word 解析失败/)).toBeTruthy();
      });
      expect(screen.getByText(/Invalid file format/)).toBeTruthy();
    });

    it('解析失败时不渲染 HTML 内容', async () => {
      mockConvertToHtml.mockRejectedValue(new Error('Corrupted'));
      render(<WordViewer content={docxBase64()} />);
      await waitFor(() => {
        expect(screen.getByText(/Word 解析失败/)).toBeTruthy();
      });
      expect(screen.queryByText('标题')).toBeNull();
    });

    it('非 Error 异常显示未知错误', async () => {
      mockConvertToHtml.mockRejectedValue('string error');
      render(<WordViewer content={docxBase64()} />);
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

      render(<WordViewer content={docxBase64()} />);

      await waitFor(() => {
        expect(screen.getByText('内容')).toBeTruthy();
      });
      expect(warnSpy).toHaveBeenCalledWith('Word 转换警告:', expect.any(Array));

      warnSpy.mockRestore();
    });
  });
});
