import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import RequestContextMenu from './RequestContextMenu';
import type { HttpRequest } from '../../../../services/httpClientApi';

const mockRequest: HttpRequest = {
  id: 'req-1',
  collection_id: 'col-1',
  name: '获取SAP数据',
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
};

afterEach(() => {
  cleanup();
});

describe('RequestContextMenu', () => {
  it('应渲染重命名/复制请求/删除请求菜单项', () => {
    render(
      <RequestContextMenu
        request={mockRequest}
        collections={[]}
        x={0}
        y={0}
        onRename={vi.fn()}
        onDuplicate={vi.fn()}
        onDelete={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('重命名')).toBeTruthy();
    expect(screen.getByText('复制请求')).toBeTruthy();
    expect(screen.getByText('删除请求')).toBeTruthy();
  });

  it('点击重命名应回调 onRename 并关闭菜单', () => {
    const onRename = vi.fn();
    const onClose = vi.fn();
    render(
      <RequestContextMenu
        request={mockRequest}
        collections={[]}
        x={0}
        y={0}
        onRename={onRename}
        onDuplicate={vi.fn()}
        onDelete={vi.fn()}
        onClose={onClose}
      />
    );
    fireEvent.click(screen.getByText('重命名'));
    expect(onRename).toHaveBeenCalledWith(mockRequest);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
