/**
 * replaceSubtree / removeSubtree 纯函数单元测试
 */
import { describe, it, expect } from 'vitest';
import { replaceSubtree, removeSubtree } from '../fileStore';
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
