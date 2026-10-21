/**
 * replaceSubtree / removeSubtree / upsertNode 纯函数单元测试
 */
import { describe, it, expect } from 'vitest';
import { replaceSubtree, removeSubtree, upsertNode, findNodeByPath } from '../fileStore';
import type { FileNode } from '../../types/markdownEditor';

/** 构造测试树：root → [docs → [a.md], b.md] */
function makeTree(): FileNode {
  return {
    name: 'root',
    path: '',
    type: 'directory',
    children: [
      {
        name: 'docs',
        path: 'docs',
        type: 'directory',
        children: [{ name: 'a.md', path: 'docs/a.md', type: 'file' }],
      },
      { name: 'b.md', path: 'b.md', type: 'file' },
    ],
  };
}

describe('replaceSubtree', () => {
  it('替换深层目标节点的 children', () => {
    const tree = makeTree();
    const subTree: FileNode = {
      name: 'docs',
      path: 'docs',
      type: 'directory',
      children: [
        { name: 'a.md', path: 'docs/a.md', type: 'file' },
        { name: 'new.md', path: 'docs/new.md', type: 'file' },
      ],
    };

    const result = replaceSubtree(tree, 'docs', subTree);

    const docs = result.children!.find((c) => c.path === 'docs')!;
    expect(docs.children).toHaveLength(2);
    expect(docs.children!.map((c) => c.name)).toContain('new.md');
  });

  it('路径不存在时返回原树引用', () => {
    const tree = makeTree();
    const subTree: FileNode = { name: 'x', path: 'x', type: 'directory', children: [] };
    expect(replaceSubtree(tree, 'not/exist', subTree)).toBe(tree);
  });

  it('不修改原树（不可变）', () => {
    const tree = makeTree();
    const subTree: FileNode = { name: 'docs', path: 'docs', type: 'directory', children: [] };
    replaceSubtree(tree, 'docs', subTree);
    expect(tree.children![0].children).toHaveLength(1);
  });
});

describe('removeSubtree', () => {
  it('移除目标路径节点', () => {
    const tree = makeTree();
    const result = removeSubtree(tree, 'docs');
    expect(result.children!.map((c) => c.path)).toEqual(['b.md']);
  });

  it('路径不存在时返回原树引用', () => {
    const tree = makeTree();
    expect(removeSubtree(tree, 'not/exist')).toBe(tree);
  });

  it('目标为根节点时返回原树引用', () => {
    const tree = makeTree();
    expect(removeSubtree(tree, '')).toBe(tree);
  });

  it('不修改原树（不可变）', () => {
    const tree = makeTree();
    removeSubtree(tree, 'docs');
    expect(tree.children).toHaveLength(2);
  });
});

describe('upsertNode', () => {
  it('目标目录已存在时合并子节点', () => {
    const tree = makeTree();
    const subTree: FileNode = {
      name: 'docs',
      path: 'docs',
      type: 'directory',
      children: [
        { name: 'a.md', path: 'docs/a.md', type: 'file' },
        { name: 'new.md', path: 'docs/new.md', type: 'file' },
      ],
    };

    const result = upsertNode(tree, 'docs', subTree);

    const docs = result.children!.find((c) => c.path === 'docs')!;
    expect(docs.children!.map((c) => c.name)).toEqual(['a.md', 'new.md']);
  });

  it('合并时保留已加载的子节点内容', () => {
    const tree = makeTree();
    // 浅层数据：子目录只有占位，没有内容
    const shallow: FileNode = {
      name: 'docs',
      path: 'docs',
      type: 'directory',
      children: [{ name: 'sub', path: 'docs/sub', type: 'directory', children: [] }],
    };

    const result = upsertNode(tree, 'docs', shallow);

    const docs = result.children!.find((c) => c.path === 'docs')!;
    // 已加载的文件不丢失，新数据中的占位目录被补进来
    expect(docs.children!.map((c) => c.path)).toEqual(['docs/a.md', 'docs/sub']);
  });

  it('浅层数据不会覆盖已加载的深层子目录内容', () => {
    const deep: FileNode = {
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
              name: 'sub',
              path: 'docs/sub',
              type: 'directory',
              children: [{ name: 'x.md', path: 'docs/sub/x.md', type: 'file' }],
            },
          ],
        },
      ],
    };
    const shallow: FileNode = {
      name: 'docs',
      path: 'docs',
      type: 'directory',
      children: [{ name: 'sub', path: 'docs/sub', type: 'directory', children: [] }],
    };

    const result = upsertNode(deep, 'docs', shallow);

    expect(findNodeByPath(result, 'docs/sub/x.md')).not.toBeNull();
  });

  it('路径缺失时创建占位目录链', () => {
    const tree = makeTree();
    const node: FileNode = { name: 'b.md', path: 'a/b/c.md', type: 'file' };

    const result = upsertNode(tree, 'a/b/c.md', node);

    expect(findNodeByPath(result, 'a/b/c.md')).not.toBeNull();
    const a = result.children!.find((c) => c.path === 'a')!;
    const b = a.children!.find((c) => c.path === 'a/b')!;
    expect(b.children!.map((c) => c.path)).toEqual(['a/b/c.md']);
  });

  it('不修改原树（不可变）', () => {
    const tree = makeTree();
    upsertNode(tree, 'a/b/c.md', { name: 'c.md', path: 'a/b/c.md', type: 'file' });
    expect(tree.children!.map((c) => c.path)).toEqual(['docs', 'b.md']);
  });
});
