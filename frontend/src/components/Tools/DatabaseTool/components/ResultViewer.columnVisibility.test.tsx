import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import ResultViewer from './ResultViewer';
import { SQLExecutionResult } from '../../../../types/databaseTool';

if (typeof globalThis.ResizeObserver === 'undefined') {
  class ResizeObserverPolyfill {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserverPolyfill as unknown as typeof ResizeObserver;
}

vi.mock('../../../../hooks/useToast', () => ({
  useToast: () => ({ addToast: vi.fn() })
}));

vi.mock('../../../../utils/sqlGenerator', () => ({
  generateInsertStatements: vi.fn(() => '-- insert'),
  generateUpdateStatements: vi.fn(() => '-- update')
}));

vi.mock('../../../../api/databaseToolApi', () => ({
  executeSQL: vi.fn(),
  updateRows: vi.fn()
}));

const STORAGE_KEY = 'db-column-visibility-test-cfg-test-db--test_table';

const baseResult: SQLExecutionResult = {
  success: true,
  affected_rows: 2,
  execution_time_ms: 10,
  result_data: [
    { id: 1, name: 'A', description: 'desc-A' },
    { id: 2, name: 'B', description: 'desc-B' }
  ],
  columns: ['id', 'name', 'description']
};

const renderViewer = (props: Record<string, unknown> = {}) =>
  render(
    <ResultViewer
      result={baseResult}
      configId="test-cfg"
      databaseName="test-db"
      tableName="test_table"
      {...props}
    />
  );

const openColumnSelector = (container: HTMLElement) => {
  const colButton = container.querySelector('button[aria-label="列"]')!;
  fireEvent.click(colButton);
  // Radix Popover 使用 Portal，渲染到 document.body
  return document.body.querySelectorAll('[data-radix-popper-content-wrapper] .cursor-pointer, .cursor-pointer');
};

describe('ResultViewer 列可见性管理', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('取消勾选某列后，表格立即移除该列', async () => {
    const { container } = renderViewer();
    const rows = openColumnSelector(container);
    fireEvent.click(rows[2]);

    await waitFor(() => {
      const headers = container.querySelectorAll('thead th');
      const headerTexts = Array.from(headers).map(h => h.textContent);
      expect(headerTexts.some(t => t?.toUpperCase().includes('NAME'))).toBe(false);
    });
  });

  it('取消勾选后，列可见性持久化到 localStorage', async () => {
    const { container } = renderViewer();
    const rows = openColumnSelector(container);
    fireEvent.click(rows[2]);

    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      expect(stored).toEqual(['id', 'description']);
    });
  });

  it('至少保留一列的约束有效', async () => {
    const { container } = renderViewer();
    const rows = openColumnSelector(container);
    fireEvent.click(rows[1]);
    fireEvent.click(rows[2]);

    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      expect(stored.length).toBeGreaterThanOrEqual(1);
    });
  });
});
