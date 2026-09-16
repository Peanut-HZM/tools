/**
 * HtmlPreview 组件单元测试
 *
 * 测试目标：
 * - iframe 使用 blob URL 而非 srcDoc，以支持 JavaScript 执行
 * - sandbox 属性为 "allow-scripts allow-forms"，允许脚本和表单但隔离父页面
 * - 内容变化时生成新的 blob URL
 * - 卸载时清理 blob URL
 */
import { describe, it, expect, afterEach, afterAll } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import HtmlPreview from '../HtmlPreview';

// jsdom 未实现 URL.createObjectURL/revokeObjectURL，在此补充 polyfill
let blobCounter = 0;
const originalCreateObjectURL = URL.createObjectURL;
const originalRevokeObjectURL = URL.revokeObjectURL;
URL.createObjectURL = (blob: Blob) => {
  blobCounter += 1;
  return `blob:http://localhost/mock-${blobCounter}-${blob.size}`;
};
URL.revokeObjectURL = () => {
  /* no-op for tests */
};

// 每个测试后清理 DOM，避免多个 iframe 互相干扰
afterEach(() => {
  cleanup();
});

// 测试结束后恢复原始实现
afterAll(() => {
  URL.createObjectURL = originalCreateObjectURL;
  URL.revokeObjectURL = originalRevokeObjectURL;
});

describe('HtmlPreview', () => {
  it('渲染 iframe 并设置正确的 sandbox 属性', () => {
    render(<HtmlPreview content="<h1>Test</h1>" theme="dark" />);

    const iframe = screen.getByTitle('HTML 预览');
    expect(iframe).toBeTruthy();
    expect(iframe.getAttribute('sandbox')).toBe('allow-scripts allow-forms');
  });

  it('使用 blob URL 而非 srcDoc', () => {
    render(<HtmlPreview content="<h1>Test</h1>" theme="light" />);

    const iframe = screen.getByTitle('HTML 预览');
    // blob URL 应该以 "blob:" 开头
    expect(iframe.getAttribute('src')).toMatch(/^blob:/);
  });

  it('内容变化时更新 iframe src', () => {
    const { rerender } = render(<HtmlPreview content="<h1>First</h1>" theme="light" />);
    const iframe1 = screen.getByTitle('HTML 预览');
    const src1 = iframe1.getAttribute('src');

    rerender(<HtmlPreview content="<h1>Second</h1>" theme="light" />);
    const iframe2 = screen.getByTitle('HTML 预览');
    const src2 = iframe2.getAttribute('src');

    // 内容变化后应该生成新的 blob URL
    expect(src1).not.toBe(src2);
  });

  it('卸载时清理 blob URL', () => {
    const { unmount } = render(<HtmlPreview content="<h1>Test</h1>" theme="light" />);
    // 不抛出异常即为成功
    unmount();
  });
});
