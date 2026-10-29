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
  it('触发定位信号后当前打开的文件滚动到可视区域', () => {
    const scrollIntoView = vi.fn();
    const original = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = scrollIntoView;
    try {
      const { container } = renderTree({
        currentFilePath: 'docs/guide/a.md',
        expandedNodes: new Set(['docs', 'docs/guide']),
        locateNonce: 1,
      });
      const target = container.querySelector('[data-path="docs/guide/a.md"]');
      expect(target).not.toBeNull();
      expect(scrollIntoView).toHaveBeenCalled();
    } finally {
      Element.prototype.scrollIntoView = original;
    }
  });

  it('未触发定位信号时不强制滚动（避免浏览目录时被拉回）', () => {
    const scrollIntoView = vi.fn();
    const original = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = scrollIntoView;
    try {
      renderTree({
        currentFilePath: 'docs/guide/a.md',
        expandedNodes: new Set(['docs', 'docs/guide']),
      });
      expect(scrollIntoView).not.toHaveBeenCalled();
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

describe('FileTree 新建文件扩展名处理', () => {
  it('文件名没有扩展名时默认补 .md', () => {
    const onCreateFile = vi.fn();
    const { container } = renderTree({ onCreateFile });
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[0]);
    fireEvent.click(screen.getByText('新建文件'));
    const input = screen.getByPlaceholderText(/不填扩展名默认/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'README' } });
    fireEvent.click(screen.getByText('创建'));
    expect(onCreateFile).toHaveBeenCalledWith('docs/README.md');
  });

  it('文件名已有扩展名时保持原样，不追加 .md', () => {
    const onCreateFile = vi.fn();
    const { container } = renderTree({ onCreateFile });
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[0]);
    fireEvent.click(screen.getByText('新建文件'));
    const input = screen.getByPlaceholderText(/不填扩展名默认/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'example.kubeconfig' } });
    fireEvent.click(screen.getByText('创建'));
    expect(onCreateFile).toHaveBeenCalledWith('docs/example.kubeconfig');
  });
});

describe('FileTree 重命名', () => {
  it('未传 onRenameFile 时右键菜单不显示重命名', () => {
    const { container } = renderTree();
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[1]);
    expect(screen.queryByText('重命名')).toBeNull();
  });

  it('右键文件可打开重命名弹窗并预填原名', () => {
    const onRenameFile = vi.fn();
    const { container } = renderTree({ onRenameFile });
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[1]);
    fireEvent.click(screen.getByText('重命名'));
    const input = screen.getByPlaceholderText('文件名称') as HTMLInputElement;
    expect(input.value).toBe('a.md');
  });

  it('重命名文件时调用 onRenameFile（旧路径，新路径）', () => {
    const onRenameFile = vi.fn();
    const { container } = renderTree({ onRenameFile });
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[1]);
    fireEvent.click(screen.getByText('重命名'));
    const input = screen.getByPlaceholderText('文件名称');
    fireEvent.change(input, { target: { value: 'b' } });
    fireEvent.click(screen.getByText('确定'));
    // 新名不带扩展名时沿用原扩展名
    expect(onRenameFile).toHaveBeenCalledWith('a.md', 'b.md');
  });

  it('重命名文件时可显式修改扩展名', () => {
    const onRenameFile = vi.fn();
    const { container } = renderTree({ onRenameFile });
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[1]);
    fireEvent.click(screen.getByText('重命名'));
    fireEvent.change(screen.getByPlaceholderText('文件名称'), {
      target: { value: 'b.txt' },
    });
    fireEvent.click(screen.getByText('确定'));
    expect(onRenameFile).toHaveBeenCalledWith('a.md', 'b.txt');
  });

  it('重命名文件夹时不追加扩展名', () => {
    const onRenameFile = vi.fn();
    const { container } = renderTree({ onRenameFile });
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[0]);
    fireEvent.click(screen.getByText('重命名'));
    const input = screen.getByPlaceholderText('文件夹名称') as HTMLInputElement;
    expect(input.value).toBe('docs');
    fireEvent.change(input, { target: { value: 'guide' } });
    fireEvent.click(screen.getByText('确定'));
    expect(onRenameFile).toHaveBeenCalledWith('docs', 'guide');
  });

  it('名称为空时报错且不调用 onRenameFile', () => {
    const onRenameFile = vi.fn();
    const { container } = renderTree({ onRenameFile });
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[1]);
    fireEvent.click(screen.getByText('重命名'));
    fireEvent.change(screen.getByPlaceholderText('文件名称'), { target: { value: '  ' } });
    fireEvent.click(screen.getByText('确定'));
    expect(onRenameFile).not.toHaveBeenCalled();
    expect(screen.getByText('名称不能为空')).toBeTruthy();
  });

  it('名称含路径分隔符时报错且不调用 onRenameFile', () => {
    const onRenameFile = vi.fn();
    const { container } = renderTree({ onRenameFile });
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[1]);
    fireEvent.click(screen.getByText('重命名'));
    fireEvent.change(screen.getByPlaceholderText('文件名称'), {
      target: { value: 'a/b' },
    });
    fireEvent.click(screen.getByText('确定'));
    expect(onRenameFile).not.toHaveBeenCalled();
    expect(screen.getByText('名称不能包含路径分隔符')).toBeTruthy();
  });

  it('重命名失败时展示错误信息', async () => {
    const onRenameFile = vi.fn().mockRejectedValue(new Error('目标文件已存在'));
    const { container } = renderTree({ onRenameFile });
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[1]);
    fireEvent.click(screen.getByText('重命名'));
    fireEvent.change(screen.getByPlaceholderText('文件名称'), {
      target: { value: 'b.md' },
    });
    fireEvent.click(screen.getByText('确定'));
    expect(await screen.findByText('目标文件已存在')).toBeTruthy();
  });

  it('名称未变化时不调用 onRenameFile', () => {
    const onRenameFile = vi.fn();
    const { container } = renderTree({ onRenameFile });
    const items = container.querySelectorAll('.file-tree-item');
    fireEvent.contextMenu(items[1]);
    fireEvent.click(screen.getByText('重命名'));
    fireEvent.click(screen.getByText('确定'));
    expect(onRenameFile).not.toHaveBeenCalled();
  });
});
