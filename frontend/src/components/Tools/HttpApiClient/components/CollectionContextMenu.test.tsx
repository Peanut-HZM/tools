import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import CollectionContextMenu from './CollectionContextMenu';
import type { Collection } from '../../../../services/httpClientApi';

const mockCollection: Collection = {
  id: 'col-1',
  name: 'Glodon-SAP',
  sort_order: 0,
  created_at: '',
  updated_at: '',
};

afterEach(() => {
  cleanup();
});

describe('CollectionContextMenu', () => {
  it('应渲染重命名与删除菜单项', () => {
    render(
      <CollectionContextMenu
        collection={mockCollection}
        x={0}
        y={0}
        onRename={vi.fn()}
        onDelete={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('重命名')).toBeTruthy();
    expect(screen.getByText('删除集合')).toBeTruthy();
  });

  it('点击重命名应回调 onRename 并关闭菜单', () => {
    const onRename = vi.fn();
    const onClose = vi.fn();
    render(
      <CollectionContextMenu
        collection={mockCollection}
        x={0}
        y={0}
        onRename={onRename}
        onDelete={vi.fn()}
        onClose={onClose}
      />
    );
    fireEvent.click(screen.getByText('重命名'));
    expect(onRename).toHaveBeenCalledWith(mockCollection);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('点击删除集合应回调 onDelete 并关闭菜单', () => {
    const onDelete = vi.fn();
    const onClose = vi.fn();
    render(
      <CollectionContextMenu
        collection={mockCollection}
        x={0}
        y={0}
        onRename={vi.fn()}
        onDelete={onDelete}
        onClose={onClose}
      />
    );
    fireEvent.click(screen.getByText('删除集合'));
    expect(onDelete).toHaveBeenCalledWith(mockCollection);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('点击菜单外部应触发 onClose', () => {
    const onClose = vi.fn();
    render(
      <CollectionContextMenu
        collection={mockCollection}
        x={0}
        y={0}
        onRename={vi.fn()}
        onDelete={vi.fn()}
        onClose={onClose}
      />
    );
    fireEvent.mouseDown(document.body);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
