// 节点详情侧栏：labels + 全部属性表 + 出/入邻居展开
import React from 'react';
import { X, ArrowUpRight, ArrowDownLeft } from 'lucide-react';
import type { GraphNode } from '../../../api/neo4jToolApi';
import { nodeDisplayName, colorForLabel } from './GraphCanvas';
import { Button } from '@/components/ui/Button';

/** 展开状态：后端返回 total 为 null 表示总数未知 */
export interface ExpandInfo {
  /** 正在加载中 */
  loading: boolean;
  /** 已加载邻居数 */
  loaded: number;
  /** 后端返回的邻居总数；null 表示未知 */
  total: number | null;
}

interface Props {
  node: GraphNode;
  /** 出方向（该节点的出邻居）展开状态 */
  outExpand: ExpandInfo;
  /** 入方向（该节点的入邻居）展开状态 */
  inExpand: ExpandInfo;
  /** 展开回调：direction = 'out' | 'in'（继续加载下一页） */
  onExpand: (nodeId: string, direction: 'out' | 'in') => void;
  onClose: () => void;
}

/** 属性值格式化：字符串原样，其他 JSON 序列化 */
function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

/** 展开按钮文案：total 已知显示剩余数，未知显示继续加载 */
function expandButtonText(info: ExpandInfo): string {
  if (info.loading) return '加载中...';
  if (info.loaded === 0) return '展开';
  if (info.total === null) return '继续加载';
  const remaining = info.total - info.loaded;
  return remaining > 0 ? `加载更多（剩余 ${remaining}）` : '已全部加载';
}

const NodeDetail: React.FC<Props> = ({ node, outExpand, inExpand, onExpand, onClose }) => {
  const entries = Object.entries(node.properties);

  return (
    <div className="flex flex-col h-full min-h-0 border-l border-border bg-surface-1">
      {/* ---------- 头部：名称 + 关闭 ---------- */}
      <div className="flex items-start justify-between gap-2 px-3 py-2.5 border-b border-border shrink-0">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-ink truncate" title={nodeDisplayName(node)}>
            {nodeDisplayName(node)}
          </h3>
          <p className="text-xs text-ink-faint font-mono truncate mt-0.5" title={node.id}>
            {node.id}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="shrink-0 rounded-md p-1 text-ink-muted hover:bg-surface-2 hover:text-ink"
          aria-label="关闭详情"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        {/* ---------- Labels ---------- */}
        <section className="px-3 py-2.5 border-b border-border">
          <h4 className="text-xs font-medium text-ink-muted mb-1.5">标签</h4>
          {node.labels.length === 0 ? (
            <p className="text-xs text-ink-faint">无</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {node.labels.map((label) => (
                <span
                  key={label}
                  className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-xs text-ink"
                >
                  <span
                    className="inline-block w-2 h-2 rounded-full"
                    style={{ backgroundColor: colorForLabel(label) }}
                  />
                  {label}
                </span>
              ))}
            </div>
          )}
        </section>

        {/* ---------- 属性表 ---------- */}
        <section className="px-3 py-2.5 border-b border-border">
          <h4 className="text-xs font-medium text-ink-muted mb-1.5">
            属性（{entries.length}）
          </h4>
          {entries.length === 0 ? (
            <p className="text-xs text-ink-faint">无属性</p>
          ) : (
            <table className="w-full text-xs">
              <tbody>
                {entries.map(([key, value]) => (
                  <tr key={key} className="border-b border-border/50 last:border-0 align-top">
                    <td className="py-1.5 pr-2 text-ink-muted whitespace-nowrap">{key}</td>
                    <td className="py-1.5 text-ink break-all">
                      {formatValue(value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        {/* ---------- 邻居展开 ---------- */}
        <section className="px-3 py-2.5 space-y-2">
          <Button
            variant="secondary"
            size="sm"
            className="w-full justify-start"
            aria-label="展开出邻居"
            disabled={outExpand.loading || (outExpand.total !== null && outExpand.loaded >= outExpand.total)}
            onClick={() => onExpand(node.id, 'out')}
          >
            <ArrowUpRight className="w-3.5 h-3.5 mr-1.5" />
            {expandButtonText(outExpand)}
            {outExpand.loaded > 0 && (
              <span className="ml-auto text-ink-faint">已加载 {outExpand.loaded} 条关系</span>
            )}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="w-full justify-start"
            aria-label="展开入邻居"
            disabled={inExpand.loading || (inExpand.total !== null && inExpand.loaded >= inExpand.total)}
            onClick={() => onExpand(node.id, 'in')}
          >
            <ArrowDownLeft className="w-3.5 h-3.5 mr-1.5" />
            {expandButtonText(inExpand)}
            {inExpand.loaded > 0 && (
              <span className="ml-auto text-ink-faint">已加载 {inExpand.loaded} 条关系</span>
            )}
          </Button>
        </section>
      </div>
    </div>
  );
};

export default NodeDetail;
