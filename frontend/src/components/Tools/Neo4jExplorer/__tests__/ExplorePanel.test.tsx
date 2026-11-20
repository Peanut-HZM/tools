// ExplorePanel 单元测试：采样 / 展开 / 搜索定位 / 概览预选 Label
// mock neo4jToolApi（不触真实后端），toast hook 捕获提示
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, cleanup } from '@testing-library/react';

vi.mock('../../../../api/neo4jToolApi', () => ({
  sampleGraph: vi.fn(),
  expandGraph: vi.fn(),
  searchNodes: vi.fn(),
}));

const addToastMock = vi.fn();
vi.mock('../../../../hooks/useToast', () => ({
  useToast: () => ({ addToast: addToastMock }),
}));

// GraphCanvas 依赖 Cytoscape 真实画布渲染，jsdom 无 canvas 实现。
// 本测试聚焦面板交互逻辑（采样/展开/搜索），画布组件替换为轻量占位。
vi.mock('../GraphCanvas', () => ({
  __esModule: true,
  default: ({ nodes }: { nodes: GraphNode[] }) =>
    nodes.length === 0 ? <div>画布为空：请在左侧选择筛选条件后点击「采样」</div> : null,
  nodeDisplayName: (node: GraphNode) => String(node.properties?.name ?? node.id),
  colorForLabel: (label: string) => '#000',
}));

import * as api from '../../../../api/neo4jToolApi';
import { sampleGraph, expandGraph, searchNodes } from '../../../../api/neo4jToolApi';
import { useNeo4jGraphStore } from '../../../../stores/neo4jStore';
import ExplorePanel from '../ExplorePanel';
import type { GraphData, Neo4jSchema, GraphNode } from '../../../../api/neo4jToolApi';

const mockedSample = sampleGraph as unknown as ReturnType<typeof vi.fn>;
const mockedExpand = expandGraph as unknown as ReturnType<typeof vi.fn>;
const mockedSearch = searchNodes as unknown as ReturnType<typeof vi.fn>;

const CONN_ID = 'conn-1';

const makeNode = (id: string, labels: string[] = ['Person']): GraphNode => ({
  id,
  labels,
  properties: { name: id },
});

/** 构造测试关系 */
const makeRel = (id: string, source: string, target: string): GraphData['relationships'][number] => ({
  id,
  type: 'ACTED_IN',
  source,
  target,
  properties: {},
});

const makeGraph = (nodes: GraphNode[], rels: GraphData['relationships'] = []): GraphData => ({
  nodes,
  relationships: rels,
  truncated: false,
});

const schema: Neo4jSchema = {
  labels: [
    { name: 'Person', count: 100, estimated: false, sampleProperties: ['name'] },
    { name: 'Movie', count: 50, estimated: false, sampleProperties: ['title'] },
  ],
  relationshipTypes: [{ name: 'ACTED_IN', count: 200 }],
  propertyKeys: ['name', 'title'],
};

const state = () => useNeo4jGraphStore.getState();

beforeEach(() => {
  vi.clearAllMocks();
  state().clearGraph();
});

afterEach(() => {
  cleanup();
});

describe('ExplorePanel 探索面板', () => {
  it('点击「采样」调用 sampleGraph 并合并进画布（清空后替换语义）', async () => {
    // 画布已有旧数据（上一连接残留）
    state().mergeGraph(makeGraph([makeNode('old')]));

    mockedSample.mockResolvedValue(makeGraph([makeNode('a'), makeNode('b')]));

    render(<ExplorePanel connectionId={CONN_ID} schema={schema} />);
    fireEvent.click(screen.getByRole('button', { name: '采样' }));

    await waitFor(() => expect(mockedSample).toHaveBeenCalledTimes(1));
    expect(mockedSample).toHaveBeenCalledWith(CONN_ID, {
      labels: undefined,
      relTypes: undefined,
      nodeLimitPerLabel: 200,
    });

    await waitFor(() => expect(state().nodes.map((n) => n.id).sort()).toEqual(['a', 'b']));
    // 重新采样为替换语义：旧数据被清空
    expect(state().nodes.find((n) => n.id === 'old')).toBeUndefined();
  });

  it('勾选 Label 筛选后采样携带 labels 参数', async () => {
    mockedSample.mockResolvedValue(makeGraph([makeNode('a', ['Person'])]));

    render(<ExplorePanel connectionId={CONN_ID} schema={schema} />);
    fireEvent.click(screen.getByLabelText('Person'));
    fireEvent.click(screen.getByRole('button', { name: '采样' }));

    await waitFor(() => expect(mockedSample).toHaveBeenCalledTimes(1));
    expect(mockedSample.mock.calls[0][1].labels).toEqual(['Person']);
  });

  it('采样失败 toast 报错且保留画布数据（失败不炸页）', async () => {
    mockedSample.mockRejectedValue(new Error('网络错误'));

    render(<ExplorePanel connectionId={CONN_ID} schema={schema} />);
    // 渲染后再写入画布数据（组件挂载时会按连接切换语义清空画布）
    state().mergeGraph(makeGraph([makeNode('keep')]));
    fireEvent.click(screen.getByRole('button', { name: '采样' }));

    await waitFor(() => expect(addToastMock).toHaveBeenCalledWith('采样失败：网络错误', 'error'));
    // 画布数据未被清空
    expect(state().nodes.map((n) => n.id)).toEqual(['keep']);
  });

  it('搜索回车调用 searchNodes，结果合并进画布，点击定位选中节点', async () => {
    mockedSearch.mockResolvedValue(makeGraph([makeNode('target', ['Movie'])]));

    render(<ExplorePanel connectionId={CONN_ID} schema={schema} />);
    const input = screen.getByLabelText('搜索节点');
    fireEvent.change(input, { target: { value: 'matrix' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => expect(mockedSearch).toHaveBeenCalledWith(CONN_ID, 'matrix', 20));
    // 结果已合并进画布
    await waitFor(() => expect(state().nodes.find((n) => n.id === 'target')).toBeTruthy());

    // 点击下拉项定位
    fireEvent.click(await screen.findByText('target'));
    expect(state().selectedNodeId).toBe('target');
  });

  it('画布点击节点后详情侧栏展示属性，total=null 展开显示「继续加载」', async () => {
    // total=null（总数未知）：响应含 1 条边，按边计数后 loaded=1
    mockedExpand.mockResolvedValue({
      graph: makeGraph([makeNode('a'), makeNode('b')], [makeRel('r1', 'a', 'b')]),
      total: null,
    });

    render(<ExplorePanel connectionId={CONN_ID} schema={schema} />);
    // 渲染后写入画布并选中节点（画布点击在单测环境下由 cytoscape 事件触发，这里走 store 等价路径）
    state().mergeGraph(makeGraph([makeNode('a')]));
    state().setSelectedNode('a');
    const expandBtn = await screen.findByRole('button', { name: /展开出邻居/ });
    fireEvent.click(expandBtn);

    await waitFor(() => expect(mockedExpand).toHaveBeenCalledWith(CONN_ID, {
      nodeId: 'a',
      direction: 'out',
      limit: 25,
      offset: 0,
    }));
    // total=null：增量合并后按钮文案变为「继续加载」
    await screen.findByText('继续加载');
    expect(state().nodes.find((n) => n.id === 'b')).toBeTruthy();
    expect(state().nodes.find((n) => n.id === 'a')).toBeTruthy();
  });

  it('total 已知时按边计数显示剩余数「加载更多（剩余 N）」', async () => {
    // 后端按边分页：total=5 条边，本轮返回 2 条边（即使全是画布已有节点也计数）
    mockedExpand.mockResolvedValue({
      graph: makeGraph([makeNode('a'), makeNode('b')], [makeRel('r1', 'a', 'b'), makeRel('r2', 'b', 'a')]),
      total: 5,
    });

    render(<ExplorePanel connectionId={CONN_ID} schema={schema} />);
    state().mergeGraph(makeGraph([makeNode('a')]));
    state().setSelectedNode('a');
    fireEvent.click(await screen.findByRole('button', { name: /展开出邻居/ }));

    await screen.findByText('加载更多（剩余 3）');
  });

  it('loaded >= total 时按钮变为「已全部加载」且不再发起请求', async () => {
    // total=2 条边，一轮 expand 返回 2 条边 → 应立即判定加载完成
    mockedExpand.mockResolvedValue({
      graph: makeGraph([makeNode('a'), makeNode('b')], [makeRel('r1', 'a', 'b'), makeRel('r2', 'b', 'a')]),
      total: 2,
    });

    render(<ExplorePanel connectionId={CONN_ID} schema={schema} />);
    state().mergeGraph(makeGraph([makeNode('a')]));
    state().setSelectedNode('a');
    fireEvent.click(await screen.findByRole('button', { name: /展开出邻居/ }));

    await screen.findByText('已全部加载');
    expect(mockedExpand).toHaveBeenCalledTimes(1);

    // 再点按钮（disabled 但 fireEvent 仍触发 onClick 守卫）：不新增请求
    fireEvent.click(await screen.findByRole('button', { name: /展开出邻居/ }));
    expect(mockedExpand).toHaveBeenCalledTimes(1);
  });

  it('total 已知且节点已部分在画布上：按边计数不误判剩余数', async () => {
    // 画布已有 b、c（与 a 之间已有 1 条边），total=3 条边。
    // 本轮 expand 返回 2 条边（连接的全是画布已有节点），若按节点计数会漏算导致剩余数错误。
    mockedExpand.mockResolvedValue({
      graph: makeGraph(
        [makeNode('a'), makeNode('b'), makeNode('c')],
        [makeRel('r2', 'a', 'b'), makeRel('r3', 'a', 'c')],
      ),
      total: 3,
    });

    render(<ExplorePanel connectionId={CONN_ID} schema={schema} />);
    state().mergeGraph(makeGraph([makeNode('a'), makeNode('b'), makeNode('c')], [makeRel('r1', 'b', 'c')]));
    state().setSelectedNode('a');
    fireEvent.click(await screen.findByRole('button', { name: /展开出邻居/ }));

    // 按边计数：loaded=2，剩余 3-2=1
    await screen.findByText('加载更多（剩余 1）');
  });

  it('概览 Tab 预选 Label 自动勾选并消费', async () => {
    mockedSample.mockResolvedValue(makeGraph([makeNode('a', ['Movie'])]));

    const onConsume = vi.fn();
    render(
      <ExplorePanel
        connectionId={CONN_ID}
        schema={schema}
        preSelectedLabels={['Movie']}
        onConsumePreSelectedLabel={onConsume}
      />,
    );

    // 预选 Label 已勾选（Movie 复选框 checked）
    await waitFor(() => expect(onConsume).toHaveBeenCalledWith('Movie'));

    // 采样携带预选 Label
    fireEvent.click(screen.getByRole('button', { name: '采样' }));
    await waitFor(() => expect(mockedSample).toHaveBeenCalledTimes(1));
    expect(mockedSample.mock.calls[0][1].labels).toEqual(['Movie']);
  });

  it('画布为空时展示空态提示', () => {
    render(<ExplorePanel connectionId={CONN_ID} schema={schema} />);
    expect(screen.getByText(/画布为空/)).toBeTruthy();
  });
});
