/**
 * JsonTree - 可折叠 JSON 树
 *
 * 特性：
 * - 节点点击复制 JSONPath（$.data.items[0].name）
 * - 折叠/展开、数组/对象子节点计数
 * - 类型着色（字符串/数字/布尔/null）
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight, Copy } from 'lucide-react';

interface JsonTreeProps {
  data: any;
  /** 根路径表达式（默认 $） */
  rootPath?: string;
  defaultCollapsedDepth?: number;
}

export default function JsonTree({ data, rootPath = '$', defaultCollapsedDepth = 2 }: JsonTreeProps) {
  return <JsonNode value={data} path={rootPath} depth={0} defaultCollapsedDepth={defaultCollapsedDepth} />;
}

function JsonNode({ value, path, depth, defaultCollapsedDepth }: {
  value: any;
  path: string;
  depth: number;
  defaultCollapsedDepth: number;
}) {
  const isObject = value !== null && typeof value === 'object';
  const [collapsed, setCollapsed] = useState(depth >= defaultCollapsedDepth);
  const [copied, setCopied] = useState(false);

  const copyPath = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(path).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    });
  };

  if (!isObject) {
    return (
      <div className="flex items-center gap-1.5 py-0.5 group" style={{ paddingLeft: depth * 14 }}>
        <span
          onClick={copyPath}
          className="font-mono text-xs text-accent-secondary cursor-pointer hover:underline"
          title="点击复制 JSONPath"
        >
          {path.includes('.') || path.includes('[') ? path : ''}
        </span>
        {path !== '$' && <span className="text-ink-faint text-xs">:</span>}
        {renderScalar(value)}
        {copied && <span className="text-[10px] text-success ml-1">已复制路径</span>}
      </div>
    );
  }

  const entries = Array.isArray(value)
    ? value.map((v, i) => [String(i), v] as [string, any])
    : Object.entries(value);
  const bracketOpen = Array.isArray(value) ? '[' : '{';
  const bracketClose = Array.isArray(value) ? ']' : '}';
  const itemCount = entries.length;

  const nextPath = (key: string, isArr: boolean) =>
    isArr ? `${path}[${key}]` : /^[A-Za-z_][A-Za-z0-9_]*$/.test(key) ? `${path}.${key}` : `${path}["${key}"]`;

  return (
    <div className="font-mono text-xs" style={{ paddingLeft: depth > 0 ? 14 : 0 }}>
      <div className="flex items-center gap-1.5 py-0.5 group">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-ink-faint hover:text-ink flex-shrink-0"
        >
          {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
        <span
          onClick={copyPath}
          className="text-accent-secondary cursor-pointer hover:underline"
          title="点击复制 JSONPath"
        >
          {path}
        </span>
        <span className="text-ink-faint">:</span>
        <span className="text-ink-faint">{bracketOpen}</span>
        {collapsed ? (
          <>
            <span className="text-ink-faint">{itemCount} 项</span>
            <span className="text-ink-faint">{bracketClose}</span>
          </>
        ) : (
          <span className="text-ink-faint text-[10px] opacity-0 group-hover:opacity-100">
            {itemCount} 项
          </span>
        )}
        {copied && <span className="text-[10px] text-success">已复制路径</span>}
      </div>
      {!collapsed && (
        <>
          {entries.map(([key, child]) => (
            <JsonNode
              key={key}
              value={child}
              path={nextPath(key, Array.isArray(value))}
              depth={depth + 1}
              defaultCollapsedDepth={defaultCollapsedDepth}
            />
          ))}
          <div style={{ paddingLeft: 14 }} className="text-ink-faint py-0.5">{bracketClose}</div>
        </>
      )}
    </div>
  );
}

function renderScalar(value: any) {
  if (value === null) return <span className="text-accent-warning">null</span>;
  if (typeof value === 'boolean') return <span className="text-accent-info">{String(value)}</span>;
  if (typeof value === 'number') return <span className="text-accent">{value}</span>;
  // 链接高亮
  if (typeof value === 'string' && /^https?:\/\//.test(value)) {
    return (
      <a href={value} target="_blank" rel="noreferrer" className="text-accent-secondary underline break-all">
        "{value}"
      </a>
    );
  }
  return <span className="text-success">"{value}"</span>;
}
