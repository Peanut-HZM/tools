import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, Plug, RefreshCw, Server, Shield, Waypoints } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import * as gatewayApi from '../../../api/gatewayApi';
import type { GatewayConfigResponse, GatewayModelDto, PluginDto } from '../../../api/gatewayApi';

/** 网关面板：本地网关 / 掩码 / 意图路由 / 路由组 / 插件 / 预热 */
export function GatewayPanel() {
  const [data, setData] = useState<GatewayConfigResponse | null>(null);
  const [models, setModels] = useState<GatewayModelDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [configData, modelData] = await Promise.all([
        gatewayApi.getGatewayConfig(),
        gatewayApi.getGatewayModels(),
      ]);
      setData(configData);
      setModels(modelData.data ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : '读取网关设置失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const patch = useCallback(
    async (updates: Parameters<typeof gatewayApi.updateGatewayConfig>[0]) => {
      setSaving(true);
      setError(null);
      setNotice(null);
      try {
        const result = await gatewayApi.updateGatewayConfig(updates);
        setData((prev) => (prev ? { ...prev, config: result.config } : prev));
        setNotice('设置已保存');
      } catch (err) {
        setError(err instanceof Error ? err.message : '保存失败');
      } finally {
        setSaving(false);
      }
    },
    []
  );

  if (loading && !data) {
    return (
      <div className="rounded-xl border border-border bg-surface-1 p-4 text-sm text-ink-muted">
        正在读取网关设置…
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-xl border border-border bg-surface-1 p-4 text-sm text-accent-danger">
        {error ?? '网关设置不可用'}
      </div>
    );
  }

  const cfg = data.config;
  const baseUrl = `http://${cfg.host}:{port}/api/gateway`.replace('{port}', String(cfg.port));

  return (
    <div className="rounded-xl border border-border bg-surface-1 p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-ink">
            <Server className="h-4 w-4" aria-hidden />
            本地网关
          </h3>
          <p className="mt-0.5 text-xs text-ink-faint">
            一个端点同时兼容 OpenAI 与 Anthropic 协议；支持多账号失败切换、隐私掩码、意图路由。
            <br />
            <span className="text-accent-warning">本工具不会自动改写任何 CLI 配置</span>，
            需要你自行把 agent 的 base_url 指过来。
          </p>
        </div>
        <div className="flex items-center gap-2">
          {cfg.enabled ? (
            <Badge variant="tint-success" className="gap-1">
              <CheckCircle2 className="h-3 w-3" aria-hidden />
              已启用
            </Badge>
          ) : (
            <Badge variant="outline">未启用</Badge>
          )}
          <button
            type="button"
            onClick={() => void patch({ enabled: !cfg.enabled })}
            disabled={saving}
            className="rounded-lg border border-border px-3 py-1.5 text-sm text-ink hover:bg-surface-2 disabled:opacity-50"
          >
            {cfg.enabled ? '停用' : '启用'}
          </button>
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            aria-label="刷新网关设置"
            className="rounded-md p-1.5 text-ink-muted hover:bg-surface-2 hover:text-ink disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden />
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-2 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-accent-danger">
          {error}
        </div>
      )}
      {notice && (
        <div className="mb-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-xs text-accent-success">
          {notice}
        </div>
      )}

      <div className="mb-3 rounded-lg bg-surface-2 px-3 py-2 font-mono text-xs text-ink-muted">
        <div>OpenAI 兼容：{baseUrl}/v1/chat/completions</div>
        <div>Anthropic 兼容：{baseUrl}/v1/messages</div>
        <div>模型目录：{baseUrl}/v1/models（{models.length} 项）</div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {/* 隐私掩码 */}
        <Section
          icon={<Shield className="h-3.5 w-3.5" aria-hidden />}
          title="隐私掩码"
          description="请求离开本机前把 API Key / 私钥 / JWT / 邮箱换成占位符，回复回来前还原。映射只在内存中。"
        >
          <Toggle
            label="启用掩码"
            checked={cfg.masking.enabled}
            disabled={saving}
            onChange={(value) => void patch({ masking: { ...cfg.masking, enabled: value } })}
          />
          <Toggle
            label="掩码银行卡号（Luhn 校验）"
            checked={cfg.masking.maskCards}
            disabled={saving || !cfg.masking.enabled}
            onChange={(value) => void patch({ masking: { ...cfg.masking, maskCards: value } })}
          />
          <Toggle
            label="掩码身份证号"
            checked={cfg.masking.maskIds}
            disabled={saving || !cfg.masking.enabled}
            onChange={(value) => void patch({ masking: { ...cfg.masking, maskIds: value } })}
          />
        </Section>

        {/* 意图路由 */}
        <Section
          icon={<Waypoints className="h-3.5 w-3.5" aria-hidden />}
          title="意图路由"
          description="按这一轮的问题内容自动选路由组（测试/代码 → coding，闲聊 → fast），不需要额外模型调用。"
        >
          <Toggle
            label="启用意图路由"
            checked={cfg.intentRouting}
            disabled={saving}
            onChange={(value) => void patch({ intentRouting: value })}
          />
          <div className="mt-1 text-xs text-ink-faint">
            规则：测试/代码 → group/coding；长上下文 → group/long-context；闲聊/翻译 → group/fast
          </div>
        </Section>

        {/* 失败切换 */}
        <Section
          icon={<RefreshCw className="h-3.5 w-3.5" aria-hidden />}
          title="失败切换"
          description="同一供应商配了多个账号时，遇到 429/5xx 自动换下一个账号；4xx 参数错误不重试。"
        >
          <Toggle
            label="启用失败切换"
            checked={cfg.failover.enabled !== false}
            disabled={saving}
            onChange={(value) =>
              void patch({ failover: { ...cfg.failover, enabled: value } })
            }
          />
          <div className="mt-1 text-xs text-ink-faint">
            最多重试 {cfg.failover.maxRetries ?? 2} 次
          </div>
        </Section>

        {/* 插件 */}
        <Section
          icon={<Plug className="h-3.5 w-3.5" aria-hidden />}
          title="中间件插件"
          description="受控 Python 中间件，可改写请求体。单个插件出错或超时则请求保持原样。"
        >
          <PluginList plugins={data.plugins} />
        </Section>
      </div>

      {/* 路由组 */}
      <div className="mt-3">
        <div className="mb-1 text-xs text-ink-muted">路由组（成员写 provider/model）</div>
        <div className="flex flex-col gap-1">
          {Object.entries(cfg.groups).map(([name, members]) => (
            <div key={name} className="flex items-center gap-2 text-xs">
              <span className="w-[92px] shrink-0 font-mono text-ink-muted">group/{name}</span>
              <span className="min-w-0 flex-1 truncate text-ink-faint">
                {members.length > 0 ? members.join('、') : '（空，未配置成员）'}
              </span>
              {members.length === 0 && (
                <span className="shrink-0 text-[10px] text-ink-faint">
                  目标会回落到直接路由
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Section({
  icon,
  title,
  description,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border p-3">
      <div className="flex items-center gap-1.5 text-xs font-medium text-ink">
        {icon}
        {title}
      </div>
      <p className="mt-0.5 mb-2 text-[11px] leading-relaxed text-ink-faint">{description}</p>
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
}

function Toggle({
  label,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-xs text-ink">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="h-3.5 w-3.5 rounded border-border accent-accent disabled:opacity-50"
      />
      {label}
    </label>
  );
}

function PluginList({ plugins }: { plugins: PluginDto[] }) {
  if (plugins.length === 0) {
    return <p className="text-xs text-ink-faint">插件目录为空</p>;
  }
  return (
    <div className="flex flex-col gap-1">
      {plugins.map((plugin) => (
        <div key={plugin.name} className="flex items-center gap-2 text-xs">
          {plugin.error ? (
            <AlertCircle className="h-3 w-3 shrink-0 text-accent-warning" aria-hidden />
          ) : (
            <CheckCircle2 className="h-3 w-3 shrink-0 text-accent-success" aria-hidden />
          )}
          <span className="font-mono text-ink">{plugin.name}</span>
          {plugin.error && (
            <span className="min-w-0 truncate text-ink-faint">{plugin.error}</span>
          )}
        </div>
      ))}
    </div>
  );
}
