import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import RequestTabs from './RequestTabs';
import type { OpenTab } from '../../../../stores/httpClientStore';
import type { HttpRequest } from '../../../../services/httpClientApi';

const makeTab = (id: string, name: string, isModified = false): OpenTab => ({
  requestId: id,
  request: {
    id,
    collection_id: 'col-1',
    name,
    method: 'GET',
    url: 'https://example.com/api',
    headers: {},
    params: {},
    body_type: 'none',
    auth_type: 'none',
    auth_config: {},
    sort_order: 0,
    created_at: '',
    updated_at: '',
  } as HttpRequest,
  isModified,
});

afterEach(() => {
  cleanup();
});

describe('RequestTabs 内联改名', () => {
  it('点击铅笔图标进入编辑态并显示当前名称', () => {
    render(
      <RequestTabs
        openTabs={[makeTab('req-1', '旧名称')]}
        activeTabId="req-1"
        onTabClick={vi.fn()}
        onTabClose={vi.fn()}
        onRename={vi.fn()}
      />
    );
    fireEvent.click(screen.getByTitle('重命名'));
    const input = screen.getByRole('textbox') as HTMLInputElement;
    expect(input.value).toBe('旧名称');
  });

  it('回车确认应回调 onRename 并退出编辑态', () => {
    const onRename = vi.fn();
    render(
      <RequestTabs
        openTabs={[makeTab('req-1', '旧名称')]}
        activeTabId="req-1"
        onTabClick={vi.fn()}
        onTabClose={vi.fn()}
        onRename={onRename}
      />
    );
    fireEvent.click(screen.getByTitle('重命名'));
    const input = screen.getByRole('textbox') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '新名称' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(onRename).toHaveBeenCalledWith('req-1', '新名称');
    expect(onRename).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('textbox')).toBeNull();
    expect(screen.getByText('旧名称')).toBeTruthy();
  });

  it('Esc 取消应不回调 onRename', () => {
    const onRename = vi.fn();
    render(
      <RequestTabs
        openTabs={[makeTab('req-1', '旧名称')]}
        activeTabId="req-1"
        onTabClick={vi.fn()}
        onTabClose={vi.fn()}
        onRename={onRename}
      />
    );
    fireEvent.click(screen.getByTitle('重命名'));
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Escape' });

    expect(onRename).not.toHaveBeenCalled();
    expect(screen.queryByRole('textbox')).toBeNull();
  });

  it('点击铅笔图标不应触发标签页切换', () => {
    const onTabClick = vi.fn();
    render(
      <RequestTabs
        openTabs={[makeTab('req-1', '名称')]}
        activeTabId={null}
        onTabClick={onTabClick}
        onTabClose={vi.fn()}
        onRename={vi.fn()}
      />
    );
    fireEvent.click(screen.getByTitle('重命名'));
    expect(onTabClick).not.toHaveBeenCalled();
  });

  it('未传 onRename 时不渲染铅笔按钮', () => {
    render(
      <RequestTabs
        openTabs={[makeTab('req-1', '名称')]}
        activeTabId="req-1"
        onTabClick={vi.fn()}
        onTabClose={vi.fn()}
      />
    );
    expect(screen.queryByTitle('重命名')).toBeNull();
  });
});
