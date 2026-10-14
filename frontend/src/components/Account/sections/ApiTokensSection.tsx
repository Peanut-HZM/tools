/**
 * 个人中心 - API Token 管理
 * 创建（明文仅一次展示+复制）、列表（前缀/时间/状态）、撤销（二次确认）
 * 供 MCP endpoint（/mcp/k8s）认证使用
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import SettingCard from '../SettingCard';
import { KeyRound, Copy, Trash2, RefreshCw } from 'lucide-react';
import { userTokenApi, UserToken } from '../../../api/userTokenApi';

function formatTime(value?: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleString('zh-CN');
}

export default function ApiTokensSection() {
  const [tokens, setTokens] = useState<UserToken[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [expiresDays, setExpiresDays] = useState('');
  const [error, setError] = useState('');
  const [createdToken, setCreatedToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setTokens(await userTokenApi.list());
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleCreate = async () => {
    if (!name.trim()) {
      setError('请填写令牌名称');
      return;
    }
    try {
      const days = expiresDays ? parseInt(expiresDays, 10) : undefined;
      const created = await userTokenApi.create({ name: name.trim(), expiresDays: days });
      setCreatedToken(created.token);   // 明文仅此一次展示
      setCopied(false);
      setName('');
      setExpiresDays('');
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : '创建失败');
    }
  };

  const handleRevoke = async (id: string) => {
    if (!window.confirm('确认撤销该 Token？已配置它的 Agent 将立即失去访问权限。')) return;
    try {
      await userTokenApi.revoke(id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : '撤销失败');
    }
  };

  const handleCopy = async () => {
    if (!createdToken) return;
    try {
      await navigator.clipboard.writeText(createdToken);
      setCopied(true);
    } catch {
      setError('复制失败，请手动选中复制');
    }
  };

  return (
    <SettingCard title="API Token" icon={<KeyRound className="w-5 h-5 text-accent" />}>
      <div className="space-y-6" data-testid="api-tokens-section">
        {/* 创建 */}
        <Card className="p-4 bg-canvas/50">
          <div className="font-medium text-sm mb-1">创建新 Token</div>
          <p className="text-xs text-muted mb-3">
            用于本地 Agent（Claude Code / Cursor 等）通过 MCP 访问 K8s 排障接口。
            明文仅在创建时展示一次，请立即保存。
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              placeholder="令牌名称，如 claude-code-local"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="max-w-xs"
            />
            <Input
              placeholder="有效天数（留空=永不过期）"
              type="number"
              min={1}
              value={expiresDays}
              onChange={(e) => setExpiresDays(e.target.value)}
              className="max-w-[220px]"
            />
            <Button onClick={handleCreate}>创建</Button>
            <Button variant="ghost" onClick={() => void refresh()} aria-label="刷新列表">
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
          {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
        </Card>

        {/* 明文一次性展示 */}
        {createdToken && (
          <Card className="p-4 border-amber-500/40 bg-amber-500/5">
            <div className="font-medium text-sm mb-1">Token 已创建 — 仅此一次展示，请立即保存</div>
            <div className="flex items-center gap-2 mt-2">
              <code className="flex-1 px-3 py-2 rounded bg-canvas/60 text-sm break-all select-all">
                {createdToken}
              </code>
              <Button variant="outline" onClick={handleCopy} aria-label="复制 Token">
                <Copy className="w-4 h-4 mr-1" />
                {copied ? '已复制' : '复制'}
              </Button>
              <Button onClick={() => setCreatedToken(null)}>我已保存</Button>
            </div>
            <p className="text-xs text-muted mt-2">
              关闭后将无法再次查看；如遗失请在下方撤销并重新创建。
            </p>
          </Card>
        )}

        {/* 列表 */}
        <Card className="p-4 bg-canvas/50">
          <div className="font-medium text-sm mb-3">已有 Token</div>
          {loading ? (
            <p className="text-xs text-muted">加载中…</p>
          ) : tokens.length === 0 ? (
            <p className="text-xs text-muted">还没有 Token，请在上方创建。</p>
          ) : (
            <div className="space-y-2">
              {tokens.map((t) => (
                <div
                  key={t.id}
                  className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded border border-border/60"
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">{t.name}</div>
                    <div className="text-xs text-muted">
                      <code>{t.token_prefix}…</code> · 创建于 {formatTime(t.created_at)} ·
                      最后使用 {formatTime(t.last_used_at)}
                      {t.expires_at ? ` · 过期于 ${formatTime(t.expires_at)}` : ' · 永不过期'}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {t.revoked ? (
                      <span className="text-xs px-2 py-0.5 rounded bg-red-500/10 text-red-500">
                        已撤销
                      </span>
                    ) : (
                      <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-500">
                        有效
                      </span>
                    )}
                    {!t.revoked && (
                      <Button
                        variant="ghost"
                        onClick={() => handleRevoke(t.id)}
                        aria-label={`撤销 ${t.name}`}
                      >
                        <Trash2 className="w-4 h-4 mr-1" />
                        撤销
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </SettingCard>
  );
}
