// 探索 Tab：左侧 Label/关系类型筛选 + 采样，中央 Cytoscape 画布，右侧节点详情
// 顶部搜索框调 searchNodes 定位高亮
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Search, Loader2, Eraser, ChevronDown, ChevronRight } from 'lucide-react';
import type { Neo4jSchema, GraphNode } from '../../../api/neo4jToolApi';
import { sampleGraph, expandGraph, searchNodes } from '../../../api/neo4jToolApi';
import { useNeo4jGraphStore, CANVAS_NODE_LIMIT } from '../../../stores/neo4jStore';
import { useToast } from '../../../hooks/useToast';
import { Checkbox } from '@/components/ui/Checkbox';
import { Button } from '@/components/ui/Button';
import GraphCanvas, { nodeDisplayName } from './GraphCanvas';
import NodeDetail, { type ExpandInfo } from './NodeDetail';

/** 单次展开的邻居条数 */
const EXPAND_PAGE_SIZE = 25;
/** 搜索结果下拉最多条数 */
const SEARCH_RESULT_LIMIT = 20;

/** 展开状态初始值 */
const initialExpandInfo = (): ExpandInfo => ({ loading: false, loaded: 0, total: null });

interface Props {
  connectionId: string;
  schema: Neo4jSchema | null;
  /** 概览 Tab 点 Label 卡片预选的标签：本组件挂载时自动勾选并从列表消费掉 */
  preSelectedLabels?: string[];
  /** 消费一个预选标签的回调（从父组件预选列表移除） */
  onConsumePreSelectedLabel?: (label: string) => void;
}

/** 页面级刷新信号：连接切换时由父组件重置（重新采样 + 清空画布） */
const ExplorePanel: React.FC<Props> = ({ connectionId, schema, preSelectedLabels, onConsumePreSelectedLabel }) => {
  const { addToast } = useToast();
  const {
    nodes,
    relationships,
    overLimit,
    truncated,
    selectedNodeId,
    mergeGraph,
    clearGraph,
    setSelectedNode,
  } = useNeo4jGraphStore();

  // ---------- 采样筛选状态 ----------
  const [selectedLabels, setSelectedLabels] = useState<string[]>([]);
  const [selectedRelTypes, setSelectedRelTypes] = useState<string[]>([]);
  const [limitPerLabel, setLimitPerLabel] = useState('200');
  const [sampling, setSampling] = useState(false);
  const [filterOpen, setFilterOpen] = useState(true);

  // ---------- 搜索状态 ----------
  const [searchText, setSearchText] = useState('');
  const [searchResults, setSearchResults] = useState<GraphNode[] | null>(null);
  const [searching, setSearching] = useState(false);

  // ---------- 展开状态（key: `${nodeId}:${direction}`） ----------
  const [expandMap, setExpandMap] = useState<Record<string, ExpandInfo>>({});

  // 连接切换：清空画布与本地状态
  useEffect(() => {
    clearGraph();
    setSearchText('');
    setSearchResults(null);
    setExpandMap({});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connectionId]);

  // 消费概览 Tab 预选的 Label：勾选后从父组件预选列表移除（仅挂载时处理一次）
  useEffect(() => {
    if (!preSelectedLabels || preSelectedLabels.length === 0) return;
    setSelectedLabels((prev) => {
      const next = [...prev];
      for (const label of preSelectedLabels) {
        if (!next.includes(label)) next.push(label);
      }
      return next;
    });
    preSelectedLabels.forEach((label) => onConsumePreSelectedLabel?.(label));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preSelectedLabels]);

  // ---------- 采样 ----------
  const handleSample = useCallback(async () => {
    setSampling(true);
    try {
      const parsed = parseInt(limitPerLabel, 10);
      const data = await sampleGraph(connectionId, {
        labels: selectedLabels.length > 0 ? selectedLabels : undefined,
        relTypes: selectedRelTypes.length > 0 ? selectedRelTypes : undefined,
        nodeLimitPerLabel: Number.isFinite(parsed) && parsed > 0 ? parsed : undefined,
      });
      // 采样成功后才清空画布再合并（失败时保留旧画布数据，不炸页）
      clearGraph();
      mergeGraph(data);
      if (data.truncated) {
        addToast('结果已按上限截断，建议提高采样上限或收窄筛选', 'warning');
      }
      if (data.nodes.length === 0) {
        addToast('未采样到任何数据，请检查筛选条件', 'info');
      }
    } catch (error) {
      // 失败不炸页：保留已有画布数据
      addToast(`采样失败：${error instanceof Error ? error.message : '未知错误'}`, 'error');
    } finally {
      setSampling(false);
    }
  }, [connectionId, selectedLabels, selectedRelTypes, limitPerLabel, clearGraph, mergeGraph, addToast]);

  // 画布超上限提示（merge 后异步生效，用 effect 监听）
  const lastOverLimitRef = React.useRef(false);
  useEffect(() => {
    if (overLimit && !lastOverLimitRef.current) {
      addToast(`图过大（超过 ${CANVAS_NODE_LIMIT} 节点），建议收窄筛选`, 'warning');
    }
    lastOverLimitRef.current = overLimit;
  }, [overLimit, addToast]);

  // ---------- 节点展开 ----------
  const handleExpand = useCallback(
    async (nodeId: string, direction: 'out' | 'in') => {
      const key = `${nodeId}:${direction}`;
      const info = expandMap[key] ?? initialExpandInfo();

      // total 已知且已加载完：不再请求
      if (info.total !== null && info.loaded >= info.total) return;

      setExpandMap((prev) => ({ ...prev, [key]: { ...info, loading: true } }));
      try {
        const { graph, total } = await expandGraph(connectionId, {
          nodeId,
          direction,
          limit: EXPAND_PAGE_SIZE,
          offset: info.loaded,
        });
        // 增量合并不清空画布
        mergeGraph(graph);
        // 后端按边分页、total 为该节点唯一邻居边数：loaded 必须与 total 同口径按边计数。
        // 若按新增节点计数，画布已有节点会导致剩余数低估、提前「已全部加载」漏加载。
        const loaded = info.loaded + graph.relationships.length;
        setExpandMap((prev) => ({ ...prev, [key]: { loading: false, loaded, total } }));
      } catch (error) {
        setExpandMap((prev) => ({ ...prev, [key]: { ...info, loading: false } }));
        addToast(`展开失败：${error instanceof Error ? error.message : '未知错误'}`, 'error');
      }
    },
    [connectionId, expandMap, mergeGraph, addToast],
  );

  // ---------- 搜索定位 ----------
  const handleSearch = useCallback(async () => {
    const q = searchText.trim();
    if (!q) return;
    setSearching(true);
    try {
      const data = await searchNodes(connectionId, q, SEARCH_RESULT_LIMIT);
      // 搜索结果合并进画布（去重），便于直接展开
      mergeGraph(data);
      setSearchResults(data.nodes);
      if (data.nodes.length === 0) {
        addToast('未找到匹配节点', 'info');
      }
    } catch (error) {
      addToast(`搜索失败：${error instanceof Error ? error.message : '未知错误'}`, 'error');
    } finally {
      setSearching(false);
    }
  }, [connectionId, searchText, mergeGraph, addToast]);

  /** 点击搜索结果：定位高亮（选中即高亮，画布自动居中） */
  const handleLocate = useCallback(
    (node: GraphNode) => {
      setSelectedNode(node.id);
      setSearchResults(null);
      setSearchText(nodeDisplayName(node));
    },
    [setSelectedNode],
  );

  // ---------- 选中节点（画布点击 / 搜索定位共用） ----------
  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId) ?? null,
    [nodes, selectedNodeId],
  );

  // ---------- 筛选勾选 ----------
  const toggleLabel = useCallback((label: string) => {
    setSelectedLabels((prev) =>
      prev.includes(label) ? prev.filter((l) => l !== label) : [...prev, label],
    );
  }, []);

  const toggleRelType = useCallback((relType: string) => {
    setSelectedRelTypes((prev) =>
      prev.includes(relType) ? prev.filter((r) => r !== relType) : [...prev, relType],
    );
  }, []);

  return (
    <div className="flex h-full min-h-0">
      {/* ---------- 左侧：筛选栏 ---------- */}
      <div className="w-56 shrink-0 border-r border-border bg-surface-1 overflow-y-auto flex flex-col">
        <div className="p-3 space-y-3 flex-1">
          {/* 采样上限 */}
          <div>
            <label className="text-xs font-medium text-ink-muted block mb-1">
              每标签采样上限
            </label>
            <input
              type="number"
              min={1}
              value={limitPerLabel}
              onChange={(e) => setLimitPerLabel(e.target.value)}
              className="w-full h-8 rounded-md border border-border bg-surface-1 px-2 text-sm text-ink focus-visible:border-accent focus-visible:outline-none"
              aria-label="每标签采样上限"
            />
          </div>

          {/* Label 多选 */}
          <div>
            <button
              type="button"
              onClick={() => setFilterOpen((v) => !v)}
              className="flex items-center gap-1 text-xs font-medium text-ink-muted mb-1.5 hover:text-ink"
            >
              {filterOpen ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5" />
              )}
              节点标签（{selectedLabels.length} 已选）
            </button>
            {filterOpen && (
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {schema?.labels.length ? (
                  schema.labels.map((label) => (
                    <div key={label.name} className="flex items-center gap-2">
                      <Checkbox
                        id={`label-${label.name}`}
                        checked={selectedLabels.includes(label.name)}
                        onCheckedChange={() => toggleLabel(label.name)}
                      />
                      <label
                        htmlFor={`label-${label.name}`}
                        className="text-xs text-ink cursor-pointer truncate"
                        title={label.name}
                      >
                        {label.name}
                      </label>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-ink-faint">暂无标签</p>
                )}
              </div>
            )}
          </div>

          {/* 关系类型多选 */}
          <div>
            <div className="text-xs font-medium text-ink-muted mb-1.5">关系类型（可选）</div>
            <div className="space-y-1.5 max-h-32 overflow-y-auto">
              {schema?.relationshipTypes.length ? (
                schema.relationshipTypes.map((rel) => (
                  <div key={rel.name} className="flex items-center gap-2">
                    <Checkbox
                      id={`rel-${rel.name}`}
                      checked={selectedRelTypes.includes(rel.name)}
                      onCheckedChange={() => toggleRelType(rel.name)}
                    />
                    <label
                      htmlFor={`rel-${rel.name}`}
                      className="text-xs text-ink cursor-pointer truncate"
                      title={rel.name}
                    >
                      {rel.name}
                    </label>
                  </div>
                ))
              ) : (
                <p className="text-xs text-ink-faint">暂无关系类型</p>
              )}
            </div>
          </div>
        </div>

        {/* 底部操作区 */}
        <div className="p-3 border-t border-border space-y-2 shrink-0">
          <Button
            size="sm"
            className="w-full"
            disabled={sampling}
            onClick={handleSample}
          >
            {sampling ? (
              <>
                <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                采样中...
              </>
            ) : (
              '采样'
            )}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="w-full"
            disabled={nodes.length === 0 && relationships.length === 0}
            onClick={() => {
              clearGraph();
              setExpandMap({});
              setSearchResults(null);
              setSearchText('');
            }}
          >
            <Eraser className="w-3.5 h-3.5 mr-1.5" />
            清空画布
          </Button>
        </div>
      </div>

      {/* ---------- 中央：搜索框 + 画布 ---------- */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部搜索 */}
        <div className="relative flex items-center gap-2 px-3 py-2 border-b border-border shrink-0">
          <Search className="w-4 h-4 text-ink-muted shrink-0" />
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="搜索节点属性，回车定位..."
            className="flex-1 h-8 rounded-md border border-border bg-surface-1 px-2 text-sm text-ink placeholder:text-ink-faint focus-visible:border-accent focus-visible:outline-none"
            aria-label="搜索节点"
          />
          <Button
            variant="secondary"
            size="sm"
            disabled={searching || !searchText.trim()}
            onClick={handleSearch}
          >
            {searching ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              '定位'
            )}
          </Button>

          {/* 搜索结果下拉 */}
          {searchResults !== null && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setSearchResults(null)}
              />
              <div className="absolute left-3 right-3 top-full mt-1 z-20 rounded-lg border border-border bg-surface-1 shadow-lg max-h-64 overflow-y-auto">
                {searchResults.length === 0 ? (
                  <p className="px-3 py-2 text-xs text-ink-faint">无匹配结果</p>
                ) : (
                  searchResults.map((node) => (
                    <button
                      key={node.id}
                      type="button"
                      onClick={() => handleLocate(node)}
                      className="w-full text-left px-3 py-2 hover:bg-surface-2 text-sm text-ink flex items-center gap-2"
                    >
                      <span className="truncate">{nodeDisplayName(node)}</span>
                      <span className="text-xs text-ink-faint shrink-0">
                        {node.labels[0] ?? ''}
                      </span>
                    </button>
                  ))
                )}
              </div>
            </>
          )}
        </div>

        {/* 画布 */}
        <div className="flex-1 flex min-h-0">
          <GraphCanvas
            nodes={nodes}
            relationships={relationships}
            selectedNodeId={selectedNodeId}
            onSelect={(node) => setSelectedNode(node?.id ?? null)}
          />

          {/* 右侧详情侧栏 */}
          {selectedNode && (
            <div className="w-72 shrink-0">
              <NodeDetail
                node={selectedNode}
                outExpand={expandMap[`${selectedNode.id}:out`] ?? initialExpandInfo()}
                inExpand={expandMap[`${selectedNode.id}:in`] ?? initialExpandInfo()}
                onExpand={handleExpand}
                onClose={() => setSelectedNode(null)}
              />
            </div>
          )}
        </div>

        {/* 底部状态栏 */}
        <div className="flex items-center gap-3 px-3 py-1.5 border-t border-border text-xs text-ink-muted shrink-0 flex-wrap">
          <span>节点 {nodes.length.toLocaleString()}</span>
          <span>关系 {relationships.length.toLocaleString()}</span>
          {truncated && (
            <span className="text-accent-warning">结果已截断，建议提高上限</span>
          )}
          {overLimit && (
            <span className="text-accent-danger">图过大（超 {CANVAS_NODE_LIMIT} 节点），建议收窄筛选</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default ExplorePanel;
