/**
 * FileTree 刷新菜单测试：文件夹/文件/空白区右键刷新、刷新中禁用
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import FileTree from '../FileTree/FileTree';
import type { FileNode } from '../../../types/markdownEditor';

/* jsdom 兼容：polyfill scrollIntoView */
if (typeof Element !== 'undefined' && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function () { /* jsdom no-op */ };
}

const tree: FileNode = {
  name: 'root',
  path: '',
  type: 'directory',
  children: [
    {
      name: 'docs',
      path: 'docs',
      type: 'directory',
      children: [
        {
          name: 'guide',
          path: 'docs/guide',
          type: 'directory',
          children: [{ name: 'a.md', path: 'docs/guide/a.md', type: 'file' }],
        },
      ],
    },
    { name: 'a.md', path: 'a.md', type: 'file' },
  ],
};

function renderTree(props: Partial<React.ComponentProps<typeof FileTree>> = {}) {
  return render(
    <FileTree
      tree={tree}
      currentFilePath=""
      expandedNodes={new Set<string>()}
      onFileSelect={vi.fn()}
      onToggleNode={vi.fn()}
      {...props}
    />
  );
}

afterEach(cleanup);

describe('FileTree 刷新菜单', () => {
  it('右键文件夹显示刷新，点击后刷新该文件夹', () => {
    const onRefresh = vi.fn();
    const { container } = renderTree({ onRefresh });
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[0]);
    fireEvent.click(screen.getByText('刷新'));
    expect(onRefresh).toHaveBeenCalledWith('docs');
  });

  it('右键文件显示刷新，点击后刷新整树', () => {
    const onRefresh = vi.fn();
    const { container } = renderTree({ onRefresh });
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[1]);
    fireEvent.click(screen.getByText('刷新'));
    expect(onRefresh).toHaveBeenCalledWith(null);
  });

  it('右键空白区域显示仅含刷新的菜单', () => {
    const onRefresh = vi.fn();
    const { container } = renderTree({ onRefresh });
    const content = container.querySelector('.flex-1.overflow-auto')!;
    fireEvent.contextMenu(content);
    fireEvent.click(screen.getByText('刷新'));
    expect(onRefresh).toHaveBeenCalledWith(null);
  });

  it('刷新进行中刷新按钮禁用', () => {
    const { container } = renderTree({ refreshingPath: 'docs' });
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[0]);
    expect((screen.getByText('刷新') as HTMLButtonElement).disabled).toBe(true);
  });

  it('空白菜单打开后右键节点，仅显示节点菜单', () => {
    const onRefresh = vi.fn();
    const { container } = renderTree({ onRefresh });
    const content = container.querySelector('.flex-1.overflow-auto')!;
    fireEvent.contextMenu(content);
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[0]);
    expect(screen.getAllByText('刷新')).toHaveLength(1);
  });
});

describe('FileTree 文件定位', () => {
  it('当前打开的文件滚动到可视区域', () => {
    const scrollIntoView = vi.fn();
    const original = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = scrollIntoView;
    try {
      const { container } = renderTree({
        currentFilePath: 'docs/guide/a.md',
        expandedNodes: new Set(['docs', 'docs/guide']),
      });
      const target = container.querySelector('[data-path="docs/guide/a.md"]');
      expect(target).not.toBeNull();
      expect(scrollIntoView).toHaveBeenCalled();
    } finally {
      Element.prototype.scrollIntoView = original;
    }
  });

  it('搜索清除后祖先目录已展开时当前文件依然可见', () => {
    const { container } = renderTree({
      currentFilePath: 'docs/guide/a.md',
      expandedNodes: new Set(['docs', 'docs/guide']),
    });
    expect(container.querySelector('[data-path="docs/guide/a.md"]')).not.toBeNull();
  });

  it('祖先目录未展开时当前文件不在树中（等待 store 展开）', () => {
    const { container } = renderTree({
      currentFilePath: 'docs/guide/a.md',
      expandedNodes: new Set<string>(),
    });
    expect(container.querySelector('[data-path="docs/guide/a.md"]')).toBeNull();
  });
});
