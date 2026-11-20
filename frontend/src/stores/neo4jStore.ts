/**
 * Neo4j 探索画布状态（Zustand）
 *
 * 用 Map 按 elementId（节点/关系 id）去重维护画布数据：
 * - mergeGraph：增量合并（采样 / 展开 / 搜索定位共用），重复 id 后写覆盖，空返回不清空
 * - clearGraph：切换连接或重新采样前清空画布
 * - overLimit：画布节点数超软上限时置 true，UI 提示用户收窄筛选
 *
 * 注意：本 store 为纯内存会话状态，不做 persist（画布数据量可能很大）。
 */
import { create } from 'zustand';
import type { GraphData, GraphNode, GraphRel } from '../api/neo4jToolApi';

/** 画布节点软上限：超过后提示"图过大，建议收窄筛选"（渲染性能保护） */
export const CANVAS_NODE_LIMIT = 2000;

interface Neo4jGraphStore {
  /** 画布节点（已按 id 去重） */
  nodes: GraphNode[];
  /** 画布关系（已按 id 去重） */
  relationships: GraphRel[];
  /** 画布节点数超过软上限 */
  overLimit: boolean;
  /** 最近一次合并的图数据被后端截断（建议收窄筛选或降低上限） */
  truncated: boolean;
  /** 当前选中节点 id（画布点击 / 搜索定位） */
  selectedNodeId: string | null;

  /** 增量合并图数据：重复 id 后写覆盖；空返回不清空已有数据 */
  mergeGraph: (g: GraphData) => void;
  /** 清空画布（切换连接 / 重新采样） */
  clearGraph: () => void;
  setSelectedNode: (id: string | null) => void;
}

export const useNeo4jGraphStore = create<Neo4jGraphStore>((set, get) => ({
  nodes: [],
  relationships: [],
  overLimit: false,
  truncated: false,
  selectedNodeId: null,

  mergeGraph: (g) => {
    const nodeMap = new Map<string, GraphNode>();
    for (const n of get().nodes) nodeMap.set(n.id, n);
    // 同 id 后写覆盖：expand 带回的节点可能带更完整属性
    for (const n of g.nodes) nodeMap.set(n.id, n);

    const relMap = new Map<string, GraphRel>();
    for (const r of get().relationships) relMap.set(r.id, r);
    for (const r of g.relationships) relMap.set(r.id, r);

    set({
      nodes: Array.from(nodeMap.values()),
      relationships: Array.from(relMap.values()),
      overLimit: nodeMap.size > CANVAS_NODE_LIMIT,
      truncated: g.truncated,
    });
  },

  clearGraph: () =>
    set({ nodes: [], relationships: [], overLimit: false, truncated: false, selectedNodeId: null }),

  setSelectedNode: (id) => set({ selectedNodeId: id }),
}));
