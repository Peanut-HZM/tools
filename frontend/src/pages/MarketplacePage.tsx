/**
 * MarketplacePage — Agent 市场页
 *
 * P2-④ Agent 市场 / 分享
 * 浏览 public Agent 目录，一键 fork 到自己名下（private 副本，
 * 在后台管理中编辑）。
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Bot, Copy, RefreshCw } from 'lucide-react';
import { marketplaceApi, MarketAgent } from '../api/marketplaceApi';

const MarketplacePage: React.FC = () => {
  const [agents, setAgents] = useState<MarketAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [forkingId, setForkingId] = useState<string | null>(null);
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const result = await marketplaceApi.list();
      setAgents(result.records);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleFork = async (agent: MarketAgent) => {
    setForkingId(agent.id);
    setNotice('');
    try {
      const result = await marketplaceApi.fork(agent.id);
      setNotice(`已创建副本"${result.name}"（私有），可在后台管理中编辑`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'fork 失败');
    } finally {
      setForkingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-canvas">
      <div className="container mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-ink flex items-center gap-2">
              <Bot className="w-6 h-6" />
              Agent 市场
            </h1>
            <p className="text-sm text-ink-muted mt-1">
              浏览公开 Agent，fork 一份私有副本到自己的工作区
            </p>
          </div>
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1 px-4 py-2 bg-surface-2 hover:bg-surface-3 text-ink rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
        </div>

        {notice && (
          <div className="mb-4 px-4 py-3 bg-surface-1 border border-border rounded-lg text-sm text-ink">
            {notice}
          </div>
        )}
        {error && <div className="mb-4 text-danger text-sm">{error}</div>}

        {loading ? (
          <div className="text-ink-muted">加载中...</div>
        ) : agents.length === 0 ? (
          <div className="text-ink-muted">暂无公开 Agent</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((a) => (
              <div
                key={a.id}
                className="p-4 border border-border rounded-lg bg-surface-1 flex flex-col gap-2"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`w-8 h-8 rounded ${a.icon_color || 'bg-blue-500'} flex items-center justify-center text-white`}
                  >
                    <Bot className="w-4 h-4" />
                  </span>
                  <span className="font-medium text-ink">{a.name}</span>
                </div>
                <p className="text-sm text-ink-muted line-clamp-3 min-h-[3.75rem]">
                  {a.description || '（无描述）'}
                </p>
                <div className="flex items-center justify-between mt-auto pt-2">
                  <span className="text-xs text-ink-muted">{a.category}</span>
                  <button
                    type="button"
                    onClick={() => handleFork(a)}
                    disabled={forkingId === a.id}
                    className="flex items-center gap-1 px-3 py-1.5 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg text-sm transition-colors disabled:opacity-50"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    {forkingId === a.id ? 'fork 中...' : 'Fork'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MarketplacePage;
