// Schema 概览面板：Label 卡片网格 + 关系类型表格
// 点击 Label 卡片回调 onSelectLabel（Task 7 探索 Tab 预选）
import React from 'react';
import { Tag, GitFork, Database } from 'lucide-react';
import { Neo4jSchema } from '../../../api/neo4jToolApi';

interface Props {
  schema: Neo4jSchema | null;
  loading: boolean;
  /** 点击 Label 卡片回调（Task 7 接探索 Tab） */
  onSelectLabel?: (label: string) => void;
}

/** 数字千分位格式化 */
function formatCount(n: number): string {
  return n.toLocaleString('zh-CN');
}

export const SchemaOverview: React.FC<Props> = ({ schema, loading, onSelectLabel }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-ink-faint text-sm">
        正在加载 Schema 概览...
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="flex items-center justify-center py-16 text-ink-faint text-sm">
        暂无数据，请选择连接
      </div>
    );
  }

  const isEmpty =
    schema.labels.length === 0 &&
    schema.relationshipTypes.length === 0 &&
    schema.propertyKeys.length === 0;

  // 空库空态
  if (isEmpty) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-ink-faint">
        <Database className="w-12 h-12 mb-3 opacity-30" />
        <p className="text-sm">数据库为空，暂无节点与关系</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 overflow-y-auto h-full">
      {/* ---------- Label 卡片网格 ---------- */}
      <section>
        <h3 className="text-sm font-semibold text-ink-muted mb-3 flex items-center gap-1.5">
          <Tag className="w-4 h-4" />
          节点标签（{schema.labels.length}）
        </h3>
        {schema.labels.length === 0 ? (
          <p className="text-xs text-ink-faint">暂无节点标签</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {schema.labels.map((label) => (
              <button
                key={label.name}
                type="button"
                onClick={() => onSelectLabel?.(label.name)}
                className="text-left rounded-lg border border-border bg-surface-1 p-3 hover:border-accent hover:bg-surface-2 transition-colors"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-ink text-sm truncate">{label.name}</span>
                  <span className="text-xs text-ink-muted shrink-0">
                    {label.estimated ? '约 ' : ''}
                    {formatCount(label.count)} 节点
                  </span>
                </div>
                {label.sampleProperties.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {label.sampleProperties.map((prop) => (
                      <span
                        key={prop}
                        className="inline-flex items-center rounded bg-surface-2 px-1.5 py-0.5 text-[10px] text-ink-faint border border-border"
                      >
                        {prop}
                      </span>
                    ))}
                  </div>
                )}
              </button>
            ))}
          </div>
        )}
      </section>

      {/* ---------- 关系类型表格 ---------- */}
      <section>
        <h3 className="text-sm font-semibold text-ink-muted mb-3 flex items-center gap-1.5">
          <GitFork className="w-4 h-4" />
          关系类型（{schema.relationshipTypes.length}）
        </h3>
        {schema.relationshipTypes.length === 0 ? (
          <p className="text-xs text-ink-faint">暂无关系类型</p>
        ) : (
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-surface-2">
                <tr>
                  <th className="text-left px-3 py-2 font-medium text-ink-muted">名称</th>
                  <th className="text-right px-3 py-2 font-medium text-ink-muted">数量</th>
                </tr>
              </thead>
              <tbody>
                {schema.relationshipTypes.map((rel) => (
                  <tr key={rel.name} className="border-t border-border">
                    <td className="px-3 py-2 text-ink font-mono text-xs">{rel.name}</td>
                    <td className="px-3 py-2 text-right text-ink-muted">
                      {formatCount(rel.count)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ---------- 属性键摘要 ---------- */}
      {schema.propertyKeys.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-ink-muted mb-3">属性键（{schema.propertyKeys.length}）</h3>
          <div className="flex flex-wrap gap-1.5">
            {schema.propertyKeys.map((key) => (
              <span
                key={key}
                className="inline-flex items-center rounded bg-surface-2 px-2 py-0.5 text-xs text-ink-muted border border-border"
              >
                {key}
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};
