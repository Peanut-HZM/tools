/**
 * neo4jStore 画布状态管理单元测试（Task 7）
 *
 * 覆盖 mergeGraph 去重 / 增量合并 / 空返回不清空 / 2000 软上限 / clearGraph
 *
 * 注意：Zustand 的 getState() 返回状态快照，
 * 每次 action 调用后必须重新 getState() 获取最新状态再做断言。
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useNeo4jGraphStore, CANVAS_NODE_LIMIT } from '../neo4jStore';
import type { GraphData, GraphNode, GraphRel } from '../../api/neo4jToolApi';

/** 便捷读取当前 store 状态 */
const state = () => useNeo4jGraphStore.getState();

/** 构造测试节点 */
const makeNode = (id: string, labels: string[] = ['Person']): GraphNode => ({
  id,
  labels,
  properties: { name: id },
});

/** 构造测试关系 */
const makeRel = (id: string, source: string, target: string): GraphRel => ({
  id,
  type: 'KNOWS',
  source,
  target,
  properties: {},
});

/** 构造 n 个互不相同的节点 + 空关系集 */
const makeGraph = (n: number): GraphData => ({
  nodes: Array.from({ length: n }, (_, i) => makeNode(`n-${i}`)),
  relationships: [],
  truncated: false,
});

describe('neo4jStore 画布状态管理', () => {
  beforeEach(() => {
    // 每个用例前清空画布，保证用例隔离
    state().clearGraph();
  });

  // ---------- mergeGraph：节点去重 ----------

  it('mergeGraph 对重复 elementId 的节点去重', () => {
    state().mergeGraph({ nodes: [makeNode('a'), makeNode('b')], relationships: [], truncated: false });
    // 再次合并同 id 节点（属性不同，模拟 expand 带回更新数据）
    state().mergeGraph({ nodes: [makeNode('a', ['Movie'])], relationships: [], truncated: false });

    expect(state().nodes).toHaveLength(2);
    // 同 id 后写覆盖：a 的标签应为最新值
    expect(state().nodes.find((n) => n.id === 'a')?.labels).toEqual(['Movie']);
  });

  // ---------- mergeGraph：关系去重 ----------

  it('mergeGraph 对重复 id 的关系去重', () => {
    const rel = makeRel('r1', 'a', 'b');
    state().mergeGraph({ nodes: [makeNode('a'), makeNode('b')], relationships: [rel], truncated: false });
    state().mergeGraph({ nodes: [], relationships: [rel], truncated: false });

    expect(state().relationships).toHaveLength(1);
  });

  // ---------- mergeGraph：增量合并 ----------

  it('expandNode 增量合并：保留已有节点与关系，仅追加新数据', () => {
    state().mergeGraph({
      nodes: [makeNode('a'), makeNode('b')],
      relationships: [makeRel('r1', 'a', 'b')],
      truncated: false,
    });
    state().mergeGraph({
      nodes: [makeNode('c')],
      relationships: [makeRel('r2', 'b', 'c')],
      truncated: false,
    });

    expect(state().nodes.map((n) => n.id).sort()).toEqual(['a', 'b', 'c']);
    expect(state().relationships.map((r) => r.id).sort()).toEqual(['r1', 'r2']);
  });

  // ---------- mergeGraph：空返回不清空 ----------

  it('mergeGraph 传入空图不清空已有数据（expand 到叶子节点等场景）', () => {
    state().mergeGraph({
      nodes: [makeNode('a'), makeNode('b')],
      relationships: [makeRel('r1', 'a', 'b')],
      truncated: false,
    });
    state().mergeGraph({ nodes: [], relationships: [], truncated: false });

    expect(state().nodes).toHaveLength(2);
    expect(state().relationships).toHaveLength(1);
  });

  // ---------- truncated 标记 ----------

  it('mergeGraph 记录 truncated 标记（后端截断提示）', () => {
    state().mergeGraph({ nodes: [makeNode('a')], relationships: [], truncated: true });
    expect(state().truncated).toBe(true);

    state().mergeGraph({ nodes: [makeNode('b')], relationships: [], truncated: false });
    expect(state().truncated).toBe(false);
  });

  // ---------- 2000 节点软上限 ----------

  it(`画布节点数超 ${CANVAS_NODE_LIMIT} 时 overLimit=true，回到上限内复位`, () => {
    state().mergeGraph(makeGraph(CANVAS_NODE_LIMIT));
    expect(state().nodes).toHaveLength(CANVAS_NODE_LIMIT);
    expect(state().overLimit).toBe(false);

    state().mergeGraph(makeGraph(CANVAS_NODE_LIMIT + 1));
    expect(state().nodes).toHaveLength(CANVAS_NODE_LIMIT + 1);
    expect(state().overLimit).toBe(true);

    // 去重合并回上限内后复位
    state().clearGraph();
    state().mergeGraph(makeGraph(CANVAS_NODE_LIMIT));
    expect(state().overLimit).toBe(false);
  });

  // ---------- clearGraph ----------

  it('clearGraph 清空节点/关系/标记/选中态', () => {
    state().mergeGraph({ nodes: [makeNode('a')], relationships: [], truncated: true });
    state().setSelectedNode('a');
    state().clearGraph();

    expect(state().nodes).toHaveLength(0);
    expect(state().relationships).toHaveLength(0);
    expect(state().overLimit).toBe(false);
    expect(state().truncated).toBe(false);
    expect(state().selectedNodeId).toBeNull();
  });

  // ---------- setSelectedNode ----------

  it('setSelectedNode 更新选中节点，可置空', () => {
    state().setSelectedNode('x');
    expect(state().selectedNodeId).toBe('x');
    state().setSelectedNode(null);
    expect(state().selectedNodeId).toBeNull();
  });
});
