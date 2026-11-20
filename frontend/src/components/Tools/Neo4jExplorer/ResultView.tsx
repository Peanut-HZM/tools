// Neo4j 查询结果视图 —— 表格 / 图形双视图切换
// 表格视图：按 §6.5 序列化约定渲染类型徽标（[Node:Label] / [Relationship:Type] / [Path]）
// 图形视图：复用 GraphCanvas（只读，不展开），节点/关系按 elementId 去重
import React, { useMemo, useState } from 'react';
import { Table2, Share2, AlertTriangle, Inbox } from 'lucide-react';
import GraphCanvas from './GraphCanvas';
import type { GraphData, GraphNode, GraphRel } from '../../../api/neo4jToolApi';

// ---------------------------------------------------------------------------
// 查询结果类型（与 neo4jToolApi.runQuery 返回一致）
// ---------------------------------------------------------------------------

export interface QueryResult {
  columns: string[];
  /** 每行为 {列名: 序列化值}（后端契约）；兼容数组行 */
  rows: Array<Record<string, unknown>> | unknown[][];
  graph: {
    nodes: unknown[];
    relationships: unknown[];
    truncated?: boolean;
  };
  truncated: boolean;
  elapsedMs: number;
}

// ---------------------------------------------------------------------------
// §6.5 序列化值的类型守卫
// ---------------------------------------------------------------------------

interface SerializedNode {
  __type: 'node';
  elementId: string;
  labels: string[];
  properties: Record<string, unknown>;
}

interface SerializedRelationship {
  __type: 'relationship';
  elementId: string;
  type: string;
  startElementId: string;
  endElementId: string;
  properties: Record<string, unknown>;
}

interface SerializedPath {
  __type: 'path';
  nodes: SerializedNode[];
  relationships: SerializedRelationship[];
}

const isNodeValue = (v: unknown): v is SerializedNode =>
  typeof v === 'object' && v !== null && (v as { __type?: string }).__type === 'node';

const isRelationshipValue = (v: unknown): v is SerializedRelationship =>
  typeof v === 'object' && v !== null && (v as { __type?: string }).__type === 'relationship';

const isPathValue = (v: unknown): v is SerializedPath =>
  typeof v === 'object' && v !== null && (v as { __type?: string }).__type === 'path';

// ---------------------------------------------------------------------------
// 值摘要渲染：类型徽标 + 摘要文本
// ---------------------------------------------------------------------------

/** 取节点/关系的展示摘要：优先 name/title/label 属性，兜底 elementId 截断 */
function summarizeProperties(properties: Record<string, unknown>, fallbackId: string): string {
  for (const key of ['name', 'title', 'label']) {
    const v = properties[key];
    if (typeof v === 'string' && v) return v;
  }
  // 兜底：取第一个非空标量属性值
  for (const v of Object.values(properties)) {
    if (typeof v === 'string' && v) return v;
    if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  }
  return fallbackId.length > 12 ? `${fallbackId.slice(0, 12)}…` : fallbackId;
}

/** 把单元格值渲染为「徽标 + 摘要」结构（React 节点） */
function renderCellValue(value: unknown): React.ReactNode {
  if (value === null || value === undefined) {
    return <span className="text-ink-faint">（空）</span>;
  }
  if (isNodeValue(value)) {
    const firstLabel = value.labels[0] ?? '';
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="inline-block rounded bg-accent/15 px-1.5 py-0.5 text-[10px] font-medium text-accent">
          Node{firstLabel ? `:${firstLabel}` : ''}
        </span>
        <span>{summarizeProperties(value.properties, value.elementId)}</span>
      </span>
    );
  }
  if (isRelationshipValue(value)) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="inline-block rounded bg-orange-500/15 px-1.5 py-0.5 text-[10px] font-medium text-orange-400">
          Relationship:{value.type}
        </span>
        <span>{summarizeProperties(value.properties, value.elementId)}</span>
      </span>
    );
  }
  if (isPathValue(value)) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="inline-block rounded bg-purple-500/15 px-1.5 py-0.5 text-[10px] font-medium text-purple-400">
          Path
        </span>
        <span>{value.nodes.length} 节点 / {value.relationships.length} 关系</span>
      </span>
    );
  }
  if (Array.isArray(value)) {
    return <span className="text-ink-muted">[数组，共 {value.length} 项]</span>;
  }
  if (typeof value === 'object') {
    return <span className="text-ink-muted">{JSON.stringify(value)}</span>;
  }
  return <span>{String(value)}</span>;
}

// ---------------------------------------------------------------------------
// 图形数据转换：序列化值 → GraphNode/GraphRel（按 elementId 去重）
// ---------------------------------------------------------------------------

function toGraphData(graph: QueryResult['graph']): GraphData {
  const nodeMap = new Map<string, GraphNode>();
  const relMap = new Map<string, GraphRel>();

  for (const raw of graph.nodes) {
    if (!isNodeValue(raw)) continue;
    if (nodeMap.has(raw.elementId)) continue;
    nodeMap.set(raw.elementId, {
      id: raw.elementId,
      labels: raw.labels,
      properties: raw.properties,
    });
  }
  for (const raw of graph.relationships) {
    if (!isRelationshipValue(raw)) continue;
    if (relMap.has(raw.elementId)) continue;
    relMap.set(raw.elementId, {
      id: raw.elementId,
      type: raw.type,
      source: raw.startElementId,
      target: raw.endElementId,
      properties: raw.properties,
    });
  }
  // 关系两端节点缺失时跳过（GraphCanvas 也会过滤，这里兜底保证数据一致性）
  const nodes = Array.from(nodeMap.values());
  const nodeIds = new Set(nodes.map((n) => n.id));
  const relationships = Array.from(relMap.values()).filter(
    (r) => nodeIds.has(r.source) && nodeIds.has(r.target),
  );

  return { nodes, relationships, truncated: graph.truncated ?? false };
}

/** 兼容两种行格式：Record（后端契约）或数组（防御） */
function getRowValue(row: unknown, column: string, index: number): unknown {
  if (Array.isArray(row)) return row[index];
  if (typeof row === 'object' && row !== null) return (row as Record<string, unknown>)[column];
  return undefined;
}

// ---------------------------------------------------------------------------
// 组件
// ---------------------------------------------------------------------------

type ViewMode = 'table' | 'graph';

interface Props {
  result: QueryResult;
}

const ResultView: React.FC<Props> = ({ result }) => {
  const [view, setView] = useState<ViewMode>('table');

  /** 图形视图数据（去重 + 结构映射），随 result 变化重新计算 */
  const graphData = useMemo(() => toGraphData(result.graph), [result.graph]);

  const isEmptyRows = result.rows.length === 0;
  const isEmptyGraph = graphData.nodes.length === 0;

  return (
    <div className="flex flex-col flex-1 min-h-0 w-full">
      {/* 工具栏：视图切换 + 行数 + 耗时 + 截断提示 */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border bg-surface-1 shrink-0 flex-wrap">
        <div className="flex rounded-lg border border-border overflow-hidden">
          <button
            type="button"
            onClick={() => setView('table')}
            className={`flex items-center gap-1 px-2.5 py-1 text-xs ${
              view === 'table' ? 'bg-accent/20 text-accent' : 'text-ink-muted hover:text-ink'
            }`}
            aria-pressed={view === 'table'}
          >
            <Table2 className="w-3.5 h-3.5" />
            表格
          </button>
          <button
            type="button"
            onClick={() => setView('graph')}
            className={`flex items-center gap-1 px-2.5 py-1 text-xs ${
              view === 'graph' ? 'bg-accent/20 text-accent' : 'text-ink-muted hover:text-ink'
            }`}
            aria-pressed={view === 'graph'}
          >
            <Share2 className="w-3.5 h-3.5" />
            图
          </button>
        </div>
        <span className="text-xs text-ink-muted">
          {result.rows.length} 行 · {result.elapsedMs} ms
        </span>
        {result.truncated && (
          <span className="inline-flex items-center gap-1 rounded bg-yellow-500/15 px-2 py-0.5 text-xs text-yellow-500">
            <AlertTriangle className="w-3.5 h-3.5" />
            结果已按 LIMIT 截断，请缩小范围
          </span>
        )}
      </div>

      {/* 内容区 */}
      <div className="flex-1 min-h-0 overflow-auto">
        {view === 'table' ? (
          isEmptyRows ? (
            <div className="flex flex-col items-center justify-center h-full text-ink-faint">
              <Inbox className="w-10 h-10 mb-2 opacity-30" />
              <p className="text-sm">未查询到结果</p>
            </div>
          ) : (
            <table className="w-full text-xs border-collapse">
              <thead className="sticky top-0 bg-surface-1">
                <tr>
                  {result.columns.map((col) => (
                    <th
                      key={col}
                      className="text-left font-medium text-ink-muted px-3 py-2 border-b border-border whitespace-nowrap"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, rowIdx) => (
                  <tr key={rowIdx} className="hover:bg-surface-2/50">
                    {result.columns.map((col, colIdx) => (
                      <td
                        key={col}
                        className="px-3 py-1.5 border-b border-border/50 text-ink align-top"
                      >
                        {renderCellValue(getRowValue(row, col, colIdx))}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )
        ) : isEmptyGraph ? (
          <div className="flex flex-col items-center justify-center h-full text-ink-faint">
            <Inbox className="w-10 h-10 mb-2 opacity-30" />
            <p className="text-sm">结果中不包含节点，无法渲染图形</p>
          </div>
        ) : (
          <div className="flex flex-col h-full">
            <GraphCanvas
              nodes={graphData.nodes}
              relationships={graphData.relationships}
              selectedNodeId={null}
              onSelect={() => {
                /* 查询场景只读查看，不展示节点详情 */
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default ResultView;
