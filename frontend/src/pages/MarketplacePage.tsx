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
import { iconTintClass } from '../utils/iconTint';
import { Button } from '@/components/ui/Button';

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
        {/* 标题区：移动端纵向堆叠，sm 起横向排布；刷新按钮不收缩防折行 */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-ink flex items-center gap-2">
              <Bot className="w-6 h-6" />
              {/* gradient-text 会置 color: transparent，故只包文字词组，避免图标（currentColor）被透明化 */}
              <span className="gradient-text">Agent 市场</span>
            </h1>
            <p className="text-sm text-ink-muted mt-1">
              浏览公开 Agent，fork 一份私有副本到自己的工作区
            </p>
          </div>
          {/* 刷新按钮走设计系统 outline 变体；保留 flex 布局类（shrink-0 防折行、self-* 控制移动端对齐） */}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={load}
            disabled={loading}
            className="gap-1 shrink-0 self-start sm:self-auto"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </Button>
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
                className="glass-card hover-lift rounded-xl p-4 cursor-pointer flex flex-col gap-2"
              >
                <div className="flex items-center gap-2">
                  {/* icon_color 改经 tint 色板映射（饱和色块已废弃），图标颜色由 tint 类提供 */}
                  <span
                    className={`w-8 h-8 rounded ${iconTintClass(a.icon_color)}`}
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
                  {/* Fork 主按钮走设计系统 default 变体（.btn-primary 品牌渐变） */}
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => handleFork(a)}
                    disabled={forkingId === a.id}
                    className="gap-1"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    {forkingId === a.id ? 'fork 中...' : 'Fork'}
                  </Button>
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
