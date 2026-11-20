// Cytoscape 画布封装：fcose 布局 / 按首个 Label 哈希取色 / hover 高亮一跳邻居 / 点击选中 / 图例
import React, { useEffect, useMemo, useRef } from 'react';
import cytoscape from 'cytoscape';
import fcose from 'cytoscape-fcose';
import type { GraphNode, GraphRel } from '../../../api/neo4jToolApi';

// fcose 扩展只注册一次（模块级守卫，避免 HMR 重复注册报错）
let fcoseRegistered = false;
if (!fcoseRegistered) {
  cytoscape.use(fcose);
  fcoseRegistered = true;
}

// ---------------------------------------------------------------------------
// 配色与工具函数
// ---------------------------------------------------------------------------

/** 节点调色板：按首个 Label 哈希取色，保证同 Label 同色 */
const PALETTE = [
  '#539bf5', '#57ab5a', '#e0823d', '#b083f0', '#39c5cf',
  '#e5534b', '#d4a72c', '#f778ba', '#76b900', '#6e7681',
  '#a371f7', '#2f81f7',
];

/** Label -> 颜色（稳定哈希） */
export function colorForLabel(label: string): string {
  let hash = 0;
  for (let i = 0; i < label.length; i++) {
    hash = (hash * 31 + label.charCodeAt(i)) | 0;
  }
  return PALETTE[Math.abs(hash) % PALETTE.length];
}

/** 节点展示名：优先 name / title / 首个属性值，兜底 id */
export function nodeDisplayName(node: GraphNode): string {
  const p = node.properties as Record<string, unknown>;
  for (const key of ['name', 'title', 'label']) {
    const v = p[key];
    if (typeof v === 'string' && v) return v;
  }
  return node.id;
}

interface Props {
  nodes: GraphNode[];
  relationships: GraphRel[];
  /** 当前选中节点 id（搜索定位 / 画布点击同步高亮） */
  selectedNodeId: string | null;
  /** 点击节点回调；点击空白处回调 null */
  onSelect: (node: GraphNode | null) => void;
}

const GraphCanvas: React.FC<Props> = ({ nodes, relationships, selectedNodeId, onSelect }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  /** 画布是否处于"全新一屏"状态：true 时下次布局随机初始化，false 增量保持位置 */
  const freshLayoutRef = useRef(true);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  // 初始化 Cytoscape 实例（仅一次）
  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      // 交互配置：禁止框选、禁止节点拖拽改变位置（探索场景以查看为主）
      boxSelectionEnabled: false,
      autoungrabify: true,
      wheelSensitivity: 0.2,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            label: 'data(label)',
            width: 20,
            height: 20,
            'font-size': 9,
            color: '#8b949e',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            'min-zoomed-font-size': 5,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1,
            'line-color': '#3d444d',
            'target-arrow-color': '#3d444d',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.8,
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': 7,
            color: '#6e7681',
            'text-rotation': 'autorotate',
            'min-zoomed-font-size': 5,
          },
        },
        // hover 高亮：一跳邻居保持，其余淡化
        {
          selector: '.dimmed',
          style: { opacity: 0.12 },
        },
        {
          selector: 'node.highlight',
          style: {
            'border-width': 3,
            'border-color': '#f0883e',
          },
        },
        // 选中态（搜索定位 / 画布点击）
        {
          selector: 'node.selected',
          style: {
            'border-width': 3,
            'border-color': '#539bf5',
          },
        },
      ],
    });
    cyRef.current = cy;

    // hover：高亮一跳邻居，其余淡化
    cy.on('mouseover', 'node', (event) => {
      const target = event.target as cytoscape.NodeSingular;
      const neighborhood = target.closedNeighborhood();
      cy.elements().not(neighborhood).addClass('dimmed');
      target.addClass('highlight');
    });
    cy.on('mouseout', 'node', () => {
      cy.elements().removeClass('dimmed');
      cy.elements().removeClass('highlight');
    });

    // 点击节点回调（通过 id 反查完整 GraphNode）
    cy.on('tap', 'node', (event) => {
      const id = (event.target as cytoscape.NodeSingular).id();
      const found = cy.scratch('_nodes') as GraphNode[] | undefined;
      onSelectRef.current(found?.find((n) => n.id === id) ?? null);
    });
    // 点击空白处取消选中
    cy.on('tap', (event) => {
      if (event.target === cy) {
        onSelectRef.current(null);
      }
    });

    // 容器尺寸变化时刷新画布
    const observer = new ResizeObserver(() => {
      cy.resize();
      cy.fit(undefined, 20);
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
  }, []);

  // 数据同步：增量增删元素，保持已有节点位置
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    // 保存完整节点引用，供 tap 回调反查
    cy.scratch('_nodes', nodes);

    const nodeIds = new Set(nodes.map((n) => n.id));
    const relIds = new Set(relationships.map((r) => r.id));

    // 待新增元素
    const added: cytoscape.ElementDefinition[] = [];
    const existingIds = new Set(cy.elements().map((e) => e.id()));

    for (const n of nodes) {
      if (!existingIds.has(n.id)) {
        added.push({
          group: 'nodes',
          data: {
            id: n.id,
            label: nodeDisplayName(n),
            color: colorForLabel(n.labels[0] ?? ''),
          },
        });
      }
    }
    for (const r of relationships) {
      // 两端节点不在画布上的关系直接跳过（避免悬空边报错）
      if (nodeIds.has(r.source) && nodeIds.has(r.target) && !existingIds.has(r.id)) {
        added.push({
          group: 'edges',
          data: { id: r.id, source: r.source, target: r.target, label: r.type },
        });
      }
    }
    // 待移除元素（重新采样后旧数据可能被整体替换）
    const removed = cy
      .elements()
      .filter(
        (e) =>
          (e.isNode() && !nodeIds.has(e.id())) ||
          (e.isEdge() && !relIds.has(e.id())),
      );

    if (added.length === 0 && removed.length === 0) return;

    cy.batch(() => {
      removed.remove();
      if (added.length > 0) cy.add(added);
    });

    // 布局：全新一屏时随机初始化；增量合并时保持已有位置（fcose randomize:false）
    const layout = cy.layout({
      name: 'fcose',
      randomize: freshLayoutRef.current,
      animate: false,
      padding: 30,
      nodeRepulsion: 8000,
      idealEdgeLength: 80,
      fit: freshLayoutRef.current,
    } as cytoscape.LayoutOptions);
    layout.run();
    freshLayoutRef.current = false;
  }, [nodes, relationships]);

  // 选中高亮同步
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass('selected');
    if (selectedNodeId && cy.getElementById(selectedNodeId).nonempty()) {
      cy.getElementById(selectedNodeId).addClass('selected');
    }
  }, [selectedNodeId, nodes]);

  // 图例：当前画布内出现的 Label（按数量排序，取前若干）
  const legend = useMemo(() => {
    const counts = new Map<string, number>();
    for (const n of nodes) {
      const label = n.labels[0] ?? '';
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8);
  }, [nodes]);

  return (
    <div className="relative flex-1 min-h-0 w-full">
      <div ref={containerRef} className="absolute inset-0" data-testid="neo4j-graph-canvas" />

      {/* 空态提示 */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-ink-faint pointer-events-none">
          <p className="text-sm">画布为空：请在左侧选择筛选条件后点击「采样」</p>
        </div>
      )}

      {/* 图例 */}
      {legend.length > 1 && (
        <div className="absolute left-3 bottom-3 rounded-lg border border-border bg-surface-1/90 px-3 py-2 text-xs text-ink-muted max-w-[200px]">
          {legend.map(([label, count]) => (
            <div key={label} className="flex items-center gap-1.5 py-0.5">
              <span
                className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: colorForLabel(label === '（无标签）' ? '' : label) }}
              />
              <span className="truncate" title={label}>
                {label || '（无标签）'}
              </span>
              <span className="text-ink-faint shrink-0">{count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default GraphCanvas;
