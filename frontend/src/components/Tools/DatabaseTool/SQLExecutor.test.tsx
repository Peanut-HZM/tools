import React from 'react';
import { render, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import SQLExecutor from './SQLExecutor';
import { DatabaseToolProvider } from '../../../contexts/DatabaseToolContext';
import { AuthProvider } from '../../../stores/authStore';

if (typeof globalThis.ResizeObserver === 'undefined') {
  class ResizeObserverPolyfill {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserverPolyfill as unknown as typeof ResizeObserver;
}

vi.mock('@monaco-editor/react', () => ({
  default: () => <div data-testid="monaco-mock" />,
  useMonaco: () => null,
}));

vi.mock('../../../hooks/useToast', () => ({
  useToast: () => ({ error: vi.fn(), success: vi.fn() }),
}));

vi.mock('../../../api/databaseToolApi', () => ({
  executeSQL: vi.fn(() => Promise.resolve({ success: true, result_data: [], columns: [] })),
  getDatabasesList: vi.fn(() => Promise.resolve([])),
  getSchemasList: vi.fn(() => Promise.resolve([])),
  getDatabaseStructure: vi.fn(() => Promise.resolve({ tables: [], views: [] })),
}));

const STORAGE_KEY = 'db-tool:sqlEditorHeight';

const renderWithProvider = (props: any) => {
  return render(
    <AuthProvider>
      <DatabaseToolProvider>
        <SQLExecutor {...props} />
      </DatabaseToolProvider>
    </AuthProvider>
  );
};

describe('SQLExecutor 拖动 + 持久化', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('首次加载无 localStorage 时使用 CSS 1/3 默认布局', () => {
    const { container } = renderWithProvider({
      configId: 'cfg-1',
      database: '',
      schema: '',
      sql: 'SELECT 1',
      onStateChange: () => {},
    });
    const editorWrapper = container.querySelector('[data-testid="editor-wrapper"]');
    expect(editorWrapper).toBeTruthy();
    expect(editorWrapper?.className).toContain('h-1/3');
  });

  it('首次加载有 localStorage 时使用保存的高度', () => {
    localStorage.setItem(STORAGE_KEY, '450');
    const { container } = renderWithProvider({
      configId: 'cfg-1',
      database: '',
      schema: '',
      sql: 'SELECT 1',
      onStateChange: () => {},
    });
    const editorWrapper = container.querySelector('[data-testid="editor-wrapper"]');
    expect(editorWrapper?.getAttribute('style')).toContain('height: 450px');
  });

  it('拖动 mouseup 后高度写入 localStorage', async () => {
    const { container } = renderWithProvider({
      configId: 'cfg-1',
      database: '',
      schema: '',
      sql: 'SELECT 1',
      onStateChange: () => {},
    });
    const handle = container.querySelector('[data-testid="drag-handle"]') as HTMLElement;
    expect(handle).toBeTruthy();

    fireEvent.mouseDown(handle, { clientY: 100 });
    fireEvent.mouseMove(document, { clientY: 400 });
    await act(async () => {
      await new Promise(r => requestAnimationFrame(r));
    });
    fireEvent.mouseUp(document);

    const stored = localStorage.getItem(STORAGE_KEY);
    expect(stored).toBeTruthy();
    expect(Number(stored)).toBeGreaterThanOrEqual(200);
  });

  it('拖动低于 200px 时 clamp 到 200', async () => {
    const { container } = renderWithProvider({
      configId: 'cfg-1',
      database: '',
      schema: '',
      sql: 'SELECT 1',
      onStateChange: () => {},
    });
    const handle = container.querySelector('[data-testid="drag-handle"]') as HTMLElement;

    fireEvent.mouseDown(handle, { clientY: 500 });
    fireEvent.mouseMove(document, { clientY: 10000 });
    await act(async () => {
      await new Promise(r => requestAnimationFrame(r));
    });
    fireEvent.mouseUp(document);

    const stored = Number(localStorage.getItem(STORAGE_KEY));
    expect(stored).toBeLessThanOrEqual(2000);
    expect(stored).toBeGreaterThanOrEqual(200);
  });

  it('localStorage 解析失败时回退到默认', () => {
    localStorage.setItem(STORAGE_KEY, 'not-a-number');
    const { container } = renderWithProvider({
      configId: 'cfg-1',
      database: '',
      schema: '',
      sql: 'SELECT 1',
      onStateChange: () => {},
    });
    const editorWrapper = container.querySelector('[data-testid="editor-wrapper"]');
    expect(editorWrapper?.className).toContain('h-1/3');
  });
});

describe('SQLExecutor 全屏', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('点击全屏按钮后结果区不渲染', () => {
    const { container } = renderWithProvider({
      configId: 'cfg-1',
      database: '',
      schema: '',
      sql: 'SELECT 1',
      onStateChange: () => {},
    });
    const fsBtn = container.querySelector('[data-testid="fullscreen-toggle"]') as HTMLElement;
    expect(fsBtn).toBeTruthy();
    expect(container.querySelector('h3')?.textContent).toContain('执行结果');

    fireEvent.click(fsBtn);

    expect(container.querySelector('h3')).toBeNull();
  });

  it('再次点击全屏按钮恢复结果区', () => {
    const { container } = renderWithProvider({
      configId: 'cfg-1',
      database: '',
      schema: '',
      sql: 'SELECT 1',
      onStateChange: () => {},
    });
    const fsBtn = container.querySelector('[data-testid="fullscreen-toggle"]') as HTMLElement;

    fireEvent.click(fsBtn);
    expect(container.querySelector('h3')).toBeNull();

    fireEvent.click(fsBtn);
    expect(container.querySelector('h3')?.textContent).toContain('执行结果');
  });

  it('全屏状态下按 Esc 恢复', () => {
    const { container } = renderWithProvider({
      configId: 'cfg-1',
      database: '',
      schema: '',
      sql: 'SELECT 1',
      onStateChange: () => {},
    });
    const fsBtn = container.querySelector('[data-testid="fullscreen-toggle"]') as HTMLElement;

    fireEvent.click(fsBtn);
    expect(container.querySelector('h3')).toBeNull();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(container.querySelector('h3')?.textContent).toContain('执行结果');
  });

  it('全屏状态下拖动手柄不渲染', () => {
    const { container } = renderWithProvider({
      configId: 'cfg-1',
      database: '',
      schema: '',
      sql: 'SELECT 1',
      onStateChange: () => {},
    });
    expect(container.querySelector('[data-testid="drag-handle"]')).toBeTruthy();

    const fsBtn = container.querySelector('[data-testid="fullscreen-toggle"]') as HTMLElement;
    fireEvent.click(fsBtn);

    expect(container.querySelector('[data-testid="drag-handle"]')).toBeNull();
  });
});
