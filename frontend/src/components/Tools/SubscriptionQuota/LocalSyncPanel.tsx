// 「同步到本机」面板：把云端订阅推送到本机 CC Switch / Magpie
// 设计：specs/agent-subscription-bridge-design.md §6.4
//
// 浏览器一次用户手势只能打开一个自定义协议，所以批量采用「队列模式」：
// 点批量后进入队列，逐条点「打开下一条」，每条仍是一次真实手势。
import { useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, ClipboardCopy, ExternalLink, ListChecks, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import * as quotaApi from '../../../api/subscriptionQuotaApi';
import type { ExportLinkItemDto, LinkTargetDto, QuotaAccountDto } from '../../../api/subscriptionQuotaApi';
import { useToast } from '../../../hooks/useToast';

interface LocalSyncPanelProps {
  accounts: QuotaAccountDto[];
  onRefresh: () => void | Promise<void>;
  /** 注入点：默认用系统协议跳转，测试时可替换（避免 jsdom 的 navigation 限制） */
  openUrl?: (url: string) => void;
}

interface QueueEntry {
  accountId: string;
  label: string;
  url: string;
  target: LinkTargetDto;
  opened: boolean;
}

/** 用隐藏 <a> 触发系统协议（比 window.location 更容易被浏览器放行） */
function openProtocolUrl(url: string): void {
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.rel = 'noopener';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

const TARGET_LABEL: Record<LinkTargetDto, string> = {
  ccswitch: 'CC Switch',
  magpie: 'Magpie',
};

export function LocalSyncPanel({ accounts, onRefresh, openUrl }: LocalSyncPanelProps) {
  const { addToast } = useToast();
  const open = openUrl ?? openProtocolUrl;
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [queue, setQueue] = useState<QueueEntry[]>([]);

  const selectable = useMemo(() => accounts.filter((a) => a.hasKey), [accounts]);
  const allSelected = selectable.length > 0 && selected.size === selectable.length;
  const serverOrigin = typeof window !== 'undefined' ? window.location.origin : 'https://tools.peanuthzm.com.cn';

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    setSelected(allSelected ? new Set() : new Set(selectable.map((a) => a.id)));
  };

  const collectWarnings = (items: ExportLinkItemDto[]) => {
    const list: string[] = [];
    for (const item of items) {
      if (!item.url) {
        list.push(`${item.label || item.providerId}：${item.warnings.join('；') || '无法生成链接'}`);
      }
    }
    setWarnings(list);
    return list;
  };

  /** 单条：取链接后立刻打开（一次手势一条） */
  const syncOne = async (account: QuotaAccountDto, target: LinkTargetDto) => {
    setBusy(`${account.id}:${target}`);
    setWarnings([]);
    try {
      const result = await quotaApi.getExportLinks(target, [account.id]);
      const item = result.items[0];
      if (!item?.url) {
        collectWarnings(result.items);
        addToast(`${TARGET_LABEL[target]}：无法生成链接`, 'error');
        return;
      }
      open(item.url);
      addToast(`已唤起 ${TARGET_LABEL[target]}，请在弹窗里确认`, 'success');
    } catch (error) {
      addToast(error instanceof Error ? error.message : '同步失败', 'error');
    } finally {
      setBusy(null);
    }
  };

  /** 批量：取链接后进入队列（避免被浏览器拦截成「只打开第一条」） */
  const syncBatch = async (target: LinkTargetDto) => {
    const ids = Array.from(selected);
    if (ids.length === 0) {
      addToast('请先勾选要同步的订阅', 'error');
      return;
    }
    setBusy(`batch:${target}`);
    setWarnings([]);
    try {
      const result = await quotaApi.getExportLinks(target, ids);
      const usable = result.items.filter((item) => item.url);
      collectWarnings(result.items);
      if (usable.length === 0) {
        addToast('没有可同步的条目（见下方提示）', 'error');
        return;
      }
      setQueue(
        usable.map((item) => ({
          accountId: item.accountId,
          label: item.label || item.providerId,
          url: item.url as string,
          target,
          opened: false,
        }))
      );
      addToast(`已生成 ${usable.length} 条，请逐条点「打开下一条」`, 'success');
    } catch (error) {
      addToast(error instanceof Error ? error.message : '批量生成失败', 'error');
    } finally {
      setBusy(null);
    }
  };

  const openNext = () => {
    setQueue((prev) => {
      const index = prev.findIndex((entry) => !entry.opened);
      if (index < 0) return prev;
      open(prev[index].url);
      const next = [...prev];
      next[index] = { ...next[index], opened: true };
      return next;
    });
  };

  const copyCommand = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      addToast('命令已复制', 'success');
    } catch {
      addToast('复制失败，请手动选择文本复制', 'error');
    }
  };

  const pushCommand = `python -m scripts.subscription_bridge push --server ${serverOrigin} --token $env:TOOLS_DEVICE_TOKEN`;
  const pullCommand = `python -m scripts.subscription_bridge pull --server ${serverOrigin} --token $env:TOOLS_DEVICE_TOKEN`;
  const pendingCount = queue.filter((entry) => !entry.opened).length;
  const doneCount = queue.length - pendingCount;

  return (
    <div className="flex flex-col gap-3">
      {/* 命令块：推荐路径（静默 / 可去重） */}
      <div className="rounded-lg border border-border bg-surface-2/50 p-3">
        <div className="mb-2 flex items-center gap-2 text-sm font-medium text-ink">
          <ListChecks className="h-4 w-4" />
          本机一键同步（推荐，可真正做到按 URL+Key 去重）
        </div>
        <p className="mb-2 text-xs text-ink-muted">
          网页按钮依赖浏览器协议链接，浏览器无法读取本机已配置的订阅，因此只能做「推送」且无法去重。
          需要双向同步与去重时，请在本机执行下面的命令（需先在本页之外创建带
          <code className="mx-1 rounded bg-canvas px-1">subscription:read,subscription:export</code>
          作用域的设备 Token）。
        </p>
        {[
          { label: '云端 → 本机', command: pushCommand },
          { label: '本机 → 云端', command: pullCommand },
        ].map((entry) => (
          <div key={entry.label} className="mb-2">
            <div className="mb-1 text-xs text-ink-muted">{entry.label}</div>
            <div className="flex items-start gap-2">
              <code className="min-w-0 flex-1 overflow-x-auto rounded bg-canvas px-2 py-1.5 text-xs text-ink">
                {entry.command}
              </code>
              <Button variant="ghost" size="sm" onClick={() => copyCommand(entry.command)}>
                <ClipboardCopy className="h-3.5 w-3.5" />
                复制
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* 工具栏 */}
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={toggleAll}>
          {allSelected ? '取消全选' : `全选（${selectable.length}）`}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void syncBatch('ccswitch')}
          disabled={busy !== null || selected.size === 0}
        >
          同步选中到 CC Switch（{selected.size}）
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void syncBatch('magpie')}
          disabled={busy !== null || selected.size === 0}
        >
          同步选中到 Magpie（{selected.size}）
        </Button>
        <Button variant="ghost" size="sm" onClick={() => void onRefresh()} disabled={busy !== null}>
          <RefreshCw className="h-3.5 w-3.5" />
          刷新
        </Button>
      </div>

      {/* 队列（批量时出现） */}
      {queue.length > 0 && (
        <div className="rounded-lg border border-accent/30 bg-accent/5 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-sm text-ink">
              {TARGET_LABEL[queue[0].target]} 队列：待打开 {pendingCount} 条，已完成 {doneCount} 条
            </div>
            <Button size="sm" onClick={openNext} disabled={pendingCount === 0}>
              <ExternalLink className="h-3.5 w-3.5" />
              打开下一条
            </Button>
          </div>
          <ul className="mt-2 flex flex-col gap-1 text-xs text-ink-muted">
            {queue.map((entry) => (
              <li key={`${entry.accountId}-${entry.target}`} className="flex items-center gap-2">
                {entry.opened ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-accent-success" />
                ) : (
                  <span className="h-3.5 w-3.5 rounded-full border border-border" />
                )}
                <span className="truncate">{entry.label}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 生成失败原因 */}
      {warnings.length > 0 && (
        <div className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-xs text-ink">
          <div className="mb-1 flex items-center gap-1.5 font-medium">
            <AlertTriangle className="h-3.5 w-3.5" />
            以下条目无法生成链接
          </div>
          <ul className="list-disc pl-4">
            {warnings.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 列表 */}
      {accounts.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-ink-muted">
          还没有可同步的订阅。先在「供应商」页添加，或从 cc-switch / magpie 导入。
        </div>
      ) : (
        <ul className="flex flex-col gap-2">
          {accounts.map((account) => {
            const checked = selected.has(account.id);
            const disabled = !account.hasKey;
            return (
              <li
                key={account.id}
                className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-canvas px-3 py-2"
              >
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={disabled}
                  onChange={() => toggle(account.id)}
                  aria-label={`选择 ${account.label || account.providerId}`}
                  className="h-4 w-4 rounded border-border"
                />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm text-ink">{account.label || account.providerId}</div>
                  <div className="truncate text-xs text-ink-muted">
                    {account.providerId}
                    {account.baseUrl ? ` · ${account.baseUrl}` : ' · 官方直连'}
                    {account.maskedKey ? ` · ${account.maskedKey}` : ''}
                  </div>
                </div>
                <div className="flex shrink-0 gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={disabled || busy !== null}
                    onClick={() => void syncOne(account, 'ccswitch')}
                  >
                    CC Switch
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={disabled || busy !== null}
                    onClick={() => void syncOne(account, 'magpie')}
                  >
                    Magpie
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <p className="text-xs text-ink-faint">
        提示：深链会把 Key 放进浏览器历史，公共机器上建议改用上面的本地桥命令；CC Switch 每次导入都会弹确认框（官方唯一写入方式）。
      </p>
    </div>
  );
}