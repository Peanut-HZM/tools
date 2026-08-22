import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import CollectionTree from './CollectionTree';
import { fetchRequests } from '../../../../services/httpClientApi';
import type { Collection, HttpRequest } from '../../../../services/httpClientApi';

// Mock fetchRequests，避免真实网络请求
vi.mock('../../../../services/httpClientApi', () => ({
  fetchRequests: vi.fn(),
}));

const mockCollection: Collection = {
  id: 'col-1',
  name: 'Glodon-SAP',
  sort_order: 0,
  created_at: '2026-08-22T00:00:00Z',
  updated_at: '2026-08-22T00:00:00Z',
};

const mockRequests: HttpRequest[] = [
  {
    id: 'req-1',
    collection_id: 'col-1',
    name: '获取SAP数据',
    method: 'GET',
    url: 'https://example.com/api/data',
    headers: {},
    params: {},
    body_type: 'none',
    auth_type: 'none',
    auth_config: {},
    sort_order: 0,
    created_at: '2026-08-22T00:00:00Z',
    updated_at: '2026-08-22T00:00:00Z',
  },
];

describe('CollectionTree', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchRequests).mockResolvedValue(mockRequests);
  });

  afterEach(() => {
    cleanup();
  });

  it('点击集合行应展开请求列表并高亮选中集合', async () => {
    const onCollectionSelect = vi.fn();
    render(
      <CollectionTree
        collections={[mockCollection]}
        selectedCollectionId={null}
        onCollectionSelect={onCollectionSelect}
        onRequestOpen={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText('Glodon-SAP'));

    // 请求列表应加载并展示
    await waitFor(() => {
      expect(screen.getByText('获取SAP数据')).toBeTruthy();
    });
    // 集合应被选中（高亮）
    expect(onCollectionSelect).toHaveBeenCalledWith(mockCollection);
    expect(fetchRequests).toHaveBeenCalledWith('col-1');
  });

  it('再次点击集合行应折叠请求列表', async () => {
    const onCollectionSelect = vi.fn();
    render(
      <CollectionTree
        collections={[mockCollection]}
        selectedCollectionId={null}
        onCollectionSelect={onCollectionSelect}
        onRequestOpen={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText('Glodon-SAP'));
    await waitFor(() => {
      expect(screen.getByText('获取SAP数据')).toBeTruthy();
    });

    fireEvent.click(screen.getByText('Glodon-SAP'));
    await waitFor(() => {
      expect(screen.queryByText('获取SAP数据')).toBeNull();
    });
  });

  it('点击箭头图标应展开并只触发一次集合选中', async () => {
    const onCollectionSelect = vi.fn();
    render(
      <CollectionTree
        collections={[mockCollection]}
        selectedCollectionId={null}
        onCollectionSelect={onCollectionSelect}
        onRequestOpen={vi.fn()}
      />
    );

    // 通过 title 定位箭头按钮（行内另有重命名/删除按钮，getByRole 会产生歧义）
    fireEvent.click(screen.getByTitle('展开/折叠'));

    await waitFor(() => {
      expect(screen.getByText('获取SAP数据')).toBeTruthy();
    });
    // stopPropagation 生效：不会因冒泡二次触发
    expect(onCollectionSelect).toHaveBeenCalledTimes(1);
    expect(onCollectionSelect).toHaveBeenCalledWith(mockCollection);
  });

  it('点击行内重命名按钮应触发 onCollectionRename 且不触发行展开与选中', () => {
    const onCollectionRename = vi.fn();
    const onCollectionSelect = vi.fn();
    render(
      <CollectionTree
        collections={[mockCollection]}
        selectedCollectionId={null}
        onCollectionSelect={onCollectionSelect}
        onRequestOpen={vi.fn()}
        onCollectionRename={onCollectionRename}
      />
    );

    fireEvent.click(screen.getByTitle('重命名'));

    expect(onCollectionRename).toHaveBeenCalledWith(mockCollection);
    // stopPropagation 生效：不触发行点击（不选中、不加载请求）
    expect(onCollectionSelect).not.toHaveBeenCalled();
    expect(fetchRequests).not.toHaveBeenCalled();
  });

  it('点击行内删除按钮应触发 onCollectionDelete 且不触发行展开与选中', () => {
    const onCollectionDelete = vi.fn();
    const onCollectionSelect = vi.fn();
    render(
      <CollectionTree
        collections={[mockCollection]}
        selectedCollectionId={null}
        onCollectionSelect={onCollectionSelect}
        onRequestOpen={vi.fn()}
        onCollectionDelete={onCollectionDelete}
      />
    );

    fireEvent.click(screen.getByTitle('删除'));

    expect(onCollectionDelete).toHaveBeenCalledWith(mockCollection);
    expect(onCollectionSelect).not.toHaveBeenCalled();
    expect(fetchRequests).not.toHaveBeenCalled();
  });

  it('集合行右键应触发 onCollectionContextMenu 并 preventDefault', () => {
    const onCollectionContextMenu = vi.fn();
    render(
      <CollectionTree
        collections={[mockCollection]}
        selectedCollectionId={null}
        onCollectionSelect={vi.fn()}
        onRequestOpen={vi.fn()}
        onCollectionContextMenu={onCollectionContextMenu}
      />
    );

    fireEvent.contextMenu(screen.getByText('Glodon-SAP'));

    expect(onCollectionContextMenu).toHaveBeenCalledTimes(1);
    const [e, collection] = onCollectionContextMenu.mock.calls[0];
    expect(collection).toBe(mockCollection);
    expect(e.defaultPrevented).toBe(true);
  });
});
