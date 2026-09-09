/**
 * PdfViewer 单元测试
 *
 * 验证 PdfViewer 在不同输入下的渲染行为：
 * - 无内容时显示占位提示
 * - 有内容时渲染 react-pdf Document
 * - 工具栏显示文件名
 * - 翻页按钮可正常切换页码
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import PdfViewer from '../PdfViewer';

/** 模拟加载成功时传递给 onLoadSuccess 的文档对象 */
const mockDocumentProxy = { numPages: 5 };

/** Mock react-pdf：Document 在挂载时调用 onLoadSuccess，Page 渲染页码 */
vi.mock('react-pdf', () => ({
  Document: ({
    children,
    onLoadSuccess,
    file,
  }: {
    children: React.ReactNode;
    onLoadSuccess?: (doc: { numPages: number }) => void;
    file: string | null;
  }) => {
    // 模拟异步加载成功
    React.useEffect(() => {
      if (onLoadSuccess) {
        onLoadSuccess(mockDocumentProxy);
      }
    }, [onLoadSuccess]);
    return (
      <div data-testid="pdf-document" data-file={file || ''}>
        {children}
      </div>
    );
  },
  Page: ({ pageNumber }: { pageNumber: number }) => (
    <div data-testid="pdf-page">Page {pageNumber}</div>
  ),
  pdfjs: {
    GlobalWorkerOptions: { workerSrc: '' },
    version: '5.4.296',
  },
}));

describe('PdfViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('显示占位提示当无内容时', () => {
    render(<PdfViewer content={null} />);
    expect(screen.getByText('无 PDF 内容')).toBeTruthy();
  });

  it('无内容时不渲染 Document 组件', () => {
    render(<PdfViewer content={null} />);
    expect(screen.queryByTestId('pdf-document')).toBeNull();
  });

  it('渲染 PDF 文档当有内容时', () => {
    render(<PdfViewer content="base64data" fileName="test.pdf" />);
    expect(screen.getByTestId('pdf-document')).toBeTruthy();
  });

  it('将 base64 数据包装为 data URL 传递给 Document', () => {
    render(<PdfViewer content="base64data" />);
    const doc = screen.getByTestId('pdf-document');
    expect(doc.getAttribute('data-file')).toBe('data:application/pdf;base64,base64data');
  });

  it('显示文件名', () => {
    render(<PdfViewer content="base64data" fileName="report.pdf" />);
    expect(screen.getByText('report.pdf')).toBeTruthy();
  });

  it('未提供文件名时显示默认标签', () => {
    render(<PdfViewer content="base64data" />);
    expect(screen.getByText('PDF 文档')).toBeTruthy();
  });

  it('显示首页 Page 1', () => {
    render(<PdfViewer content="base64data" />);
    expect(screen.getByTestId('pdf-page').textContent).toBe('Page 1');
  });

  it('加载成功后显示总页数', async () => {
    render(<PdfViewer content="base64data" />);
    // useEffect 触发 onLoadSuccess → numPages 更新为 5
    expect(await screen.findByText('1 / 5')).toBeTruthy();
  });

  it('点击下一页按钮切换到 Page 2', async () => {
    render(<PdfViewer content="base64data" />);
    // 等待加载完成，显示 "1 / 5"
    await screen.findByText('1 / 5');

    fireEvent.click(screen.getByText('下一页'));
    expect(screen.getByTestId('pdf-page').textContent).toBe('Page 2');
    expect(screen.getByText('2 / 5')).toBeTruthy();
  });

  it('首页时上一页按钮禁用', () => {
    render(<PdfViewer content="base64data" />);
    const prevBtn = screen.getByText('上一页');
    expect(prevBtn.getAttribute('disabled')).not.toBeNull();
  });

  it('最后一页时下一页按钮禁用', async () => {
    render(<PdfViewer content="base64data" />);
    await screen.findByText('1 / 5');

    // 连续点击 4 次下一页到达第 5 页
    const nextBtn = screen.getByText('下一页');
    for (let i = 0; i < 4; i++) {
      fireEvent.click(nextBtn);
    }
    expect(screen.getByText('5 / 5')).toBeTruthy();
    expect(nextBtn.getAttribute('disabled')).not.toBeNull();
  });
});
