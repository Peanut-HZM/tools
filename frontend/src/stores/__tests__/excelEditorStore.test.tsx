/**
 * excelEditorStore 单元测试
 *
 * 覆盖操作日志生命周期：
 * - beginEdit 文件切换时清空操作日志
 * - beginEdit 同一文件重复调用不清空（保存后重载场景）
 * - pushOperation 追加顺序保持
 * - clearOperations 清空与 hasPendingOperations 派生
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, cleanup, act } from '@testing-library/react';
import { ExcelEditorProvider, useExcelEditorStore } from '../excelEditorStore';
import type { ExcelOperation } from '../../types/markdownEditor';

/** 探针组件：把 store 状态渲染到 DOM 便于断言 */
function Probe() {
  const store = useExcelEditorStore();
  return (
    <div>
      <span data-testid="file">{store.filePath}</span>
      <span data-testid="pending">{String(store.hasPendingOperations)}</span>
      <span data-testid="count">{store.operations.length}</span>
      <button onClick={() => store.beginEdit('a.xlsx')}>begin-a</button>
      <button onClick={() => store.beginEdit('b.xlsx')}>begin-b</button>
      <button
        onClick={() =>
          store.pushOperation({
            op: 'set_cell',
            sheet: 'S1',
            row: 1,
            col: 1,
            value: 'x',
            kind: 'str',
          } as ExcelOperation)
        }
      >
        push
      </button>
      <button onClick={() => store.clearOperations()}>clear</button>
    </div>
  );
}

function renderStore() {
  return render(
    <ExcelEditorProvider>
      <Probe />
    </ExcelEditorProvider>
  );
}

describe('excelEditorStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('初始状态无待保存操作', () => {
    renderStore();
    expect(screen.getByTestId('pending').textContent).toBe('false');
    expect(screen.getByTestId('file').textContent).toBe('');
  });

  it('beginEdit 记录文件路径，pushOperation 置脏并保持顺序', () => {
    renderStore();
    fireEvent.click(screen.getByText('begin-a'));
    fireEvent.click(screen.getByText('push'));
    fireEvent.click(screen.getByText('push'));

    expect(screen.getByTestId('file').textContent).toBe('a.xlsx');
    expect(screen.getByTestId('count').textContent).toBe('2');
    expect(screen.getByTestId('pending').textContent).toBe('true');
  });

  it('切换文件时清空操作日志', () => {
    renderStore();
    fireEvent.click(screen.getByText('begin-a'));
    fireEvent.click(screen.getByText('push'));
    expect(screen.getByTestId('pending').textContent).toBe('true');

    fireEvent.click(screen.getByText('begin-b'));
    expect(screen.getByTestId('pending').textContent).toBe('false');
    expect(screen.getByTestId('count').textContent).toBe('0');
  });

  it('同一文件重复 beginEdit 不清空（保存后重载场景）', () => {
    renderStore();
    fireEvent.click(screen.getByText('begin-a'));
    fireEvent.click(screen.getByText('push'));

    act(() => {
      // 模拟保存成功后组件重新挂载/重渲染再次调用 beginEdit
    });
    fireEvent.click(screen.getByText('begin-a'));
    expect(screen.getByTestId('count').textContent).toBe('1');
    expect(screen.getByTestId('pending').textContent).toBe('true');
  });

  it('clearOperations 清空日志', () => {
    renderStore();
    fireEvent.click(screen.getByText('begin-a'));
    fireEvent.click(screen.getByText('push'));
    fireEvent.click(screen.getByText('clear'));

    expect(screen.getByTestId('pending').textContent).toBe('false');
    expect(screen.getByTestId('count').textContent).toBe('0');
  });
});
