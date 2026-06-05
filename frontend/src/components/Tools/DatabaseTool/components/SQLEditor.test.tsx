import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import SQLEditor from './SQLEditor';

vi.mock('@monaco-editor/react', () => ({
  default: () => <div data-testid="monaco-mock" />,
  useMonaco: () => null,
}));

vi.mock('../../../../i18n', () => ({
  useI18n: () => ({
    t: {
      database: {
        executor: {
          title: 'SQL 执行器',
          run: '执行',
          executing: '执行中...',
          stop: '停止',
          clear: '清空',
          history: '执行历史',
          results: '执行结果',
          enterFullscreen: '全屏',
          exitFullscreen: '退出全屏',
        },
        status: { testing: '测试中...' },
      },
    },
  }),
}));

const baseProps = {
  value: 'SELECT 1',
  onChange: vi.fn(),
  onExecute: vi.fn(),
  tables: [],
};

describe('SQLEditor 按钮文案', () => {
  it('静态按钮显示"执行"', () => {
    render(<SQLEditor {...baseProps} loading={false} />);
    expect(screen.getByRole('button', { name: '执行' })).toBeTruthy();
  });

  it('loading 状态显示"执行中..."', () => {
    render(<SQLEditor {...baseProps} loading={true} />);
    expect(screen.getByText('执行中...')).toBeTruthy();
    expect(screen.queryByText('测试中...')).toBeNull();
  });
});
