// ResultView 单元测试：混合标量 + Node + Path 行、类型徽标、图形去重、截断提示、空态
// mock GraphCanvas（jsdom 无 canvas），聚焦表格/图切换与值渲染逻辑
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, within } from '@testing-library/react';

// GraphCanvas 依赖 Cytoscape 真实画布，替换为轻量占位并捕获 props 供断言
const graphCanvasProps: Array<{ nodes: unknown[]; relationships: unknown[] }> = [];
vi.mock('../GraphCanvas', () => ({
  __esModule: true,
  default: (props: { nodes: unknown[]; relationships: unknown[] }) => {
    graphCanvasProps.push(props);
    return <div data-testid="graph-canvas-mock" />;
  },
}));

import ResultView from '../ResultView';

// ---------------------------------------------------------------------------
// 测试数据构造（对齐后端 §6.5 序列化契约）
// ---------------------------------------------------------------------------

/** 序列化后的 Node 值 */
const makeNodeValue = (elementId: string, labels: string[], properties: Record<string, unknown> = {}) => ({
  __type: 'node',
  elementId,
  labels,
  properties,
});

/** 序列化后的 Relationship 值 */
const makeRelValue = (
  elementId: string,
  type: string,
  startElementId: string,
  endElementId: string,
) => ({
  __type: 'relationship',
  elementId,
  type,
  startElementId,
  endElementId,
  properties: {},
});

/** 序列化后的 Path 值 */
const makePathValue = (nodes: unknown[], relationships: unknown[]) => ({
  __type: 'path',
  nodes,
  relationships,
});

/** 后端返回的查询结果（rows 为 {列名: 值} 记录对象） */
const makeResult = (overrides: Partial<Parameters<typeof buildDefault>[0]> = {}) => buildDefault(overrides);

function buildDefault({
  columns = ['p', 'name', 'path'],
  rows = [
    {
      p: makeNodeValue('e1', ['Person'], { name: 'Tom' }),
      name: 'Tom',
      path: makePathValue(
        [makeNodeValue('e1', ['Person'], { name: 'Tom' }), makeNodeValue('e2', ['Movie'], { title: 'M1' })],
        [makeRelValue('r1', 'ACTED_IN', 'e1', 'e2')],
      ),
    },
    {
      p: makeNodeValue('e2', ['Movie'], { title: 'M1' }),
      name: null,
      path: null,
    },
  ],
  graph = {
    nodes: [
      makeNodeValue('e1', ['Person'], { name: 'Tom' }),
      makeNodeValue('e2', ['Movie'], { title: 'M1' }),
    ],
    relationships: [makeRelValue('r1', 'ACTED_IN', 'e1', 'e2')],
    truncated: false,
  },
  truncated = false,
  elapsedMs = 12,
}: {
  columns?: string[];
  rows?: Record<string, unknown>[];
  graph?: { nodes: unknown[]; relationships: unknown[]; truncated: boolean };
  truncated?: boolean;
  elapsedMs?: number;
}) {
  return { columns, rows, graph, truncated, elapsedMs };
}

// ---------------------------------------------------------------------------
// 测试用例
// ---------------------------------------------------------------------------

describe('ResultView', () => {
  beforeEach(() => {
    graphCanvasProps.length = 0;
  });
  afterEach(() => {
    cleanup();
  });

  it('表格视图：混合标量 + Node + Path 行渲染类型徽标', () => {
    render(<ResultView result={makeResult()} />);

    // 默认展示表格视图
    const table = screen.getByRole('table');
    expect(table).toBeTruthy();

    // 表头包含全部列名
    expect(screen.getByText('p')).toBeTruthy();
    expect(screen.getByText('name')).toBeTruthy();
    expect(screen.getByText('path')).toBeTruthy();

    // Node 列渲染 [Node:Person] + 首属性值（徽标与摘要为嵌套元素，按单元格整体匹配）
    const cells = screen.getAllByRole('cell');
    const cellTexts = cells.map((c) => c.textContent);
    expect(cellTexts.some((t) => t?.includes('Node:Person') && t?.includes('Tom'))).toBe(true);
    expect(cellTexts.some((t) => t?.includes('Node:Movie') && t?.includes('M1'))).toBe(true);

    // 标量列原样渲染（出现多次：标量列 + Node 摘要）
    expect(screen.getAllByText('Tom').length).toBeGreaterThan(0);

    // Path 列渲染路径徽标（节点数 + 关系数）
    const pathCell = cells.find((c) => c.textContent?.includes('Path'));
    expect(pathCell?.textContent).toContain('2 节点');
    expect(pathCell?.textContent).toContain('1 关系');

    // null 渲染为空占位
    expect(screen.getAllByText('（空）').length).toBeGreaterThan(0);
  });

  it('表格视图：Relationship 值渲染类型徽标', () => {
    const result = makeResult({
      columns: ['r'],
      rows: [{ r: makeRelValue('r1', 'ACTED_IN', 'e1', 'e2') }],
      graph: { nodes: [], relationships: [makeRelValue('r1', 'ACTED_IN', 'e1', 'e2')], truncated: false },
    });
    render(<ResultView result={result} />);
    const cellTexts = screen.getAllByRole('cell').map((c) => c.textContent);
    expect(cellTexts.some((t) => t?.includes('Relationship:ACTED_IN') && t?.includes('r1'))).toBe(true);
  });

  it('表格视图：truncated=true 显示截断提示', () => {
    render(<ResultView result={makeResult({ truncated: true })} />);
    expect(screen.getByText(/结果已按 LIMIT 截断/)).toBeTruthy();
  });

  it('表格视图：空结果显示空态（0 行时不渲染表格）', () => {
    render(
      <ResultView
        result={makeResult({ columns: [], rows: [], graph: { nodes: [], relationships: [], truncated: false } })}
      />,
    );
    expect(screen.getByText(/未查询到结果/)).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('图形视图：复用 GraphCanvas，节点/关系按 elementId 去重', () => {
    // graph 中包含重复 elementId 的节点（Path 与 Node 列聚合导致）
    const dupNode = makeNodeValue('e1', ['Person'], { name: 'Tom' });
    const result = makeResult({
      graph: {
        nodes: [dupNode, dupNode, makeNodeValue('e2', ['Movie'], { title: 'M1' })],
        relationships: [
          makeRelValue('r1', 'ACTED_IN', 'e1', 'e2'),
          makeRelValue('r1', 'ACTED_IN', 'e1', 'e2'),
        ],
        truncated: false,
      },
    });
    render(<ResultView result={result} />);

    fireEvent.click(screen.getByRole('button', { name: /图/ }));

    expect(graphCanvasProps.length).toBe(1);
    const props = graphCanvasProps[0];
    // 去重：e1 只出现一次
    expect(props.nodes.length).toBe(2);
    expect(props.relationships.length).toBe(1);
    // 映射为 GraphNode/GraphRel 结构（id 字段 = elementId）
    expect(props.nodes[0]).toMatchObject({ id: 'e1', labels: ['Person'] });
    expect(props.relationships[0]).toMatchObject({ id: 'r1', type: 'ACTED_IN', source: 'e1', target: 'e2' });
  });

  it('图形视图：空结果显示空态，不挂载画布', () => {
    render(
      <ResultView
        result={makeResult({ columns: ['n'], rows: [{ n: 1 }], graph: { nodes: [], relationships: [], truncated: false } })}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /图/ }));
    expect(screen.getByText(/结果中不包含节点/)).toBeTruthy();
    expect(graphCanvasProps.length).toBe(0);
  });

  it('表格/图切换：truncated 提示在两个视图都展示', () => {
    render(<ResultView result={makeResult({ truncated: true })} />);
    fireEvent.click(screen.getByRole('button', { name: /图/ }));
    expect(screen.getByText(/结果已按 LIMIT 截断/)).toBeTruthy();
  });
});
