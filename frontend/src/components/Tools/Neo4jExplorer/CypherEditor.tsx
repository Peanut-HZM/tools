// Cypher 查询编辑器 —— textarea + 常驻只读徽标 + Cmd/Ctrl+Enter 执行 + 耗时展示
// 错误 toast 透出后端 detail 文案（只读被拒 400 / 语法错误 400 / 超时 408）
import React, { useCallback, useRef, useState } from 'react';
import { Play, ShieldCheck, Loader2 } from 'lucide-react';
import { runQuery } from '../../../api/neo4jToolApi';
import { useToast } from '../../../hooks/useToast';
import { Button } from '@/components/ui/Button';
import ResultView, { QueryResult } from './ResultView';

/** 对齐 neo4jToolApi.Neo4jQueryResult（本地副本避免循环依赖） */
type RunQueryResult = QueryResult;

// ---------------------------------------------------------------------------
// 常量
// ---------------------------------------------------------------------------

/** 默认查询返回行数上限（与后端 enforce_limit 默认值对齐） */
const DEFAULT_LIMIT = 100;
/** 默认查询超时（毫秒） */
const DEFAULT_TIMEOUT_MS = 10000;
/** 历史记录本地存储键 */
const HISTORY_KEY = 'neo4j-cypher-history';

/** 读取本地历史（最多保留 20 条） */
function loadHistory(): string[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? (JSON.parse(raw) as string[]).slice(0, 20) : [];
  } catch {
    return [];
  }
}

/** 保存历史（去重 + 置顶最新 + 上限 20 条） */
function saveHistory(cypher: string) {
  try {
    const prev = loadHistory().filter((c) => c !== cypher);
    localStorage.setItem(HISTORY_KEY, JSON.stringify([cypher, ...prev].slice(0, 20)));
  } catch {
    /* localStorage 不可用时静默忽略 */
  }
}

// ---------------------------------------------------------------------------
// 组件
// ---------------------------------------------------------------------------

interface Props {
  /** 当前选中的连接 ID（上层保证非空才渲染本组件） */
  connectionId: string;
}

const CypherEditor: React.FC<Props> = ({ connectionId }) => {
  const { addToast } = useToast();
  const [cypher, setCypher] = useState('');
  /** 查询结果（null = 尚未执行） */
  const [result, setResult] = useState<RunQueryResult | null>(null);
  /** 是否正在执行 */
  const [executing, setExecuting] = useState(false);
  /** 最近一条执行的 Cypher（展示在结果区上方） */
  const [lastCypher, setLastCypher] = useState<string | null>(null);
  /** 历史下拉是否展开 */
  const [historyOpen, setHistoryOpen] = useState(false);
  /** 历史记录（初始化时读取一次） */
  const [history, setHistory] = useState<string[]>(() => loadHistory());
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // -------------------------------------------------------------------------
  // 执行查询
  // -------------------------------------------------------------------------

  const execute = useCallback(async () => {
    const trimmed = cypher.trim();
    if (!trimmed || executing) return;

    setExecuting(true);
    setHistoryOpen(false);
    try {
      const data = await runQuery(connectionId, {
        cypher: trimmed,
        limit: DEFAULT_LIMIT,
        timeoutMs: DEFAULT_TIMEOUT_MS,
      });
      setResult(data);
      setLastCypher(trimmed);
      saveHistory(trimmed);
      setHistory(loadHistory());
    } catch (error) {
      // 错误 toast 透出后端 detail 中文文案（request 封装已抛出 Error(detail)）
      addToast(error instanceof Error ? error.message : '查询失败，请稍后重试', 'error');
    } finally {
      setExecuting(false);
    }
  }, [cypher, executing, connectionId, addToast]);

  /** Cmd/Ctrl + Enter 触发执行 */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        void execute();
      }
    },
    [execute],
  );

  // -------------------------------------------------------------------------
  // 渲染
  // -------------------------------------------------------------------------

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* ---------- 编辑器区 ---------- */}
      <div className="shrink-0 border-b border-border bg-surface-1 px-3 py-2">
        <div className="flex items-start gap-2">
          <div className="flex-1 min-w-0 relative">
            <textarea
              ref={textareaRef}
              value={cypher}
              onChange={(e) => setCypher(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入只读 Cypher 查询，如 MATCH (n:Person) RETURN n LIMIT 10&#10;Cmd/Ctrl + Enter 执行"
              rows={4}
              spellCheck={false}
              className="w-full resize-y rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm font-mono text-ink placeholder:text-ink-faint focus-visible:border-accent focus-visible:outline-none"
              aria-label="Cypher 查询输入框"
            />
            {/* 历史记录下拉 */}
            {historyOpen && history.length > 0 && (
              <div className="absolute left-0 right-0 top-full mt-1 z-10 max-h-48 overflow-auto rounded-lg border border-border bg-surface-1 shadow-lg">
                {history.map((h, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="block w-full text-left px-3 py-1.5 text-xs font-mono text-ink-muted hover:bg-surface-2 hover:text-ink truncate"
                    onClick={() => {
                      setCypher(h);
                      setHistoryOpen(false);
                      textareaRef.current?.focus();
                    }}
                  >
                    {h.length > 80 ? `${h.slice(0, 80)}…` : h}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 执行按钮 */}
          <Button
            variant="default"
            size="sm"
            onClick={() => void execute()}
            disabled={!cypher.trim() || executing}
            className="shrink-0"
            aria-label="执行查询"
          >
            {executing ? (
              <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 mr-1" />
            )}
            执行
          </Button>
        </div>

        {/* 底部工具行：只读徽标（常驻）+ 历史 + 快捷键提示 */}
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          <span className="inline-flex items-center gap-1 rounded bg-green-500/15 px-2 py-0.5 text-xs text-green-500">
            <ShieldCheck className="w-3.5 h-3.5" />
            只读模式：仅允许 MATCH / RETURN 等查询语句
          </span>
          {history.length > 0 && (
            <button
              type="button"
              onClick={() => setHistoryOpen((v) => !v)}
              className="text-xs text-ink-muted hover:text-ink"
            >
              历史（{history.length}）
            </button>
          )}
          <span className="ml-auto text-xs text-ink-faint">Cmd/Ctrl + Enter 执行</span>
        </div>
      </div>

      {/* ---------- 结果区 ---------- */}
      <div className="flex-1 min-h-0 flex flex-col">
        {result === null ? (
          <div className="flex flex-col items-center justify-center h-full text-ink-faint">
            <Play className="w-10 h-10 mb-2 opacity-20" />
            <p className="text-sm">执行查询后在此查看结果</p>
            {lastCypher === null && (
              <p className="text-xs mt-1 text-ink-faint/70">支持表格 / 图形双视图切换</p>
            )}
          </div>
        ) : (
          <>
            {/* 最近执行的语句摘要 */}
            <div className="shrink-0 px-3 py-1 border-b border-border/50 bg-surface-1/50">
              <p className="text-xs font-mono text-ink-muted truncate" title={lastCypher ?? ''}>
                {lastCypher}
              </p>
            </div>
            <ResultView result={result} />
          </>
        )}
      </div>
    </div>
  );
};

export default CypherEditor;
