import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QuotaCard } from './index';
import type { QuotaResultDto } from '../../../api/subscriptionQuotaApi';

const baseQuota: QuotaResultDto = {
  tool: 'kimi',
  providerId: 'kimi',
  label: 'Kimi 工作号',
  kind: 'window',
  credentialStatus: 'valid',
  credentialMessage: null,
  success: true,
  tiers: [
    { name: 'five_hour', utilization: 26, resetsAt: new Date(Date.now() + 3600_000).toISOString() },
    { name: 'weekly_limit', utilization: 47, resetsAt: new Date(Date.now() + 3 * 86400_000).toISOString() },
  ],
  planName: 'Allegretto',
  error: null,
  queriedAt: Date.now() - 60_000,
  accountId: 'acc-1',
  maskedKey: 'sk-a********klmn',
};

describe('QuotaCard', () => {
  afterEach(cleanup);

  it('渲染自定义标签、套餐名、掩码 Key 与每档剩余百分比', () => {
    render(<QuotaCard quota={baseQuota} now={Date.now()} refreshing={false} onRefresh={() => {}} />);

    expect(screen.getByText('Kimi 工作号')).toBeTruthy();
    expect(screen.getByText('Allegretto')).toBeTruthy();
    expect(screen.getByText('sk-a********klmn')).toBeTruthy();
    expect(screen.getByText('5 小时')).toBeTruthy();
    expect(screen.getByText('74%')).toBeTruthy();
    expect(screen.getByText('每周')).toBeTruthy();
    expect(screen.getByText('53%')).toBeTruthy();
  });

  it('额度条带 meter 无障碍语义', () => {
    render(<QuotaCard quota={baseQuota} now={Date.now()} refreshing={false} onRefresh={() => {}} />);
    const meters = screen.getAllByRole('meter');
    expect(meters).toHaveLength(2);
    expect(meters[0].getAttribute('aria-valuenow')).toBe('74');
    expect(meters[1].getAttribute('aria-valuenow')).toBe('53');
  });

  it('余额型渲染金额而不是百分比', () => {
    const balanceQuota: QuotaResultDto = {
      ...baseQuota,
      providerId: 'deepseek',
      label: 'DeepSeek',
      kind: 'balance',
      planName: null,
      maskedKey: null,
      tiers: [
        {
          name: 'balance_CNY',
          utilization: 0,
          resetsAt: null,
          balanceAmount: 12.34,
          balanceUnit: 'CNY',
        },
      ],
    };
    render(
      <QuotaCard quota={balanceQuota} now={Date.now()} refreshing={false} onRefresh={() => {}} />
    );
    expect(screen.getByText('余额 CNY')).toBeTruthy();
    expect(screen.getByText('12.34 CNY')).toBeTruthy();
    expect(screen.queryByRole('meter')).toBeNull();
  });

  it('余额为 0 显示红色语义', () => {
    const zeroBalance: QuotaResultDto = {
      ...baseQuota,
      kind: 'balance',
      tiers: [
        { name: 'balance_USD', utilization: 0, resetsAt: null, balanceAmount: 0, balanceUnit: 'USD' },
      ],
    };
    render(
      <QuotaCard quota={zeroBalance} now={Date.now()} refreshing={false} onRefresh={() => {}} />
    );
    const node = screen.getByText('0.00 USD');
    expect(node.className).toContain('danger');
  });

  it('未登录显示提示而不是伪造额度', () => {
    const notFound: QuotaResultDto = {
      ...baseQuota,
      providerId: 'claude',
      label: 'Claude Code',
      kind: 'subscription',
      credentialStatus: 'not_found',
      success: false,
      tiers: [],
      planName: null,
      accountId: null,
      maskedKey: null,
    };
    render(<QuotaCard quota={notFound} now={Date.now()} refreshing={false} onRefresh={() => {}} />);
    expect(screen.getByText('Claude Code')).toBeTruthy();
    expect(screen.getByText('未检测到登录')).toBeTruthy();
    expect(screen.getByText('未检测到可用凭据')).toBeTruthy();
    expect(screen.queryByText(/%$/)).toBeNull();
  });

  it('查询失败显示后端原文', () => {
    const failed: QuotaResultDto = {
      ...baseQuota,
      providerId: 'zhipu',
      label: '智谱 GLM',
      success: false,
      tiers: [],
      planName: null,
      error: '认证失败（HTTP 401），请检查 API Key 是否有效',
      credentialMessage: '认证失败（HTTP 401），请检查 API Key 是否有效',
    };
    render(<QuotaCard quota={failed} now={Date.now()} refreshing={false} onRefresh={() => {}} />);
    expect(screen.getByText('额度查询失败')).toBeTruthy();
    expect(screen.getByText('认证失败（HTTP 401），请检查 API Key 是否有效')).toBeTruthy();
  });

  it('刷新按钮触发回调，刷新中禁用', () => {
    const onRefresh = vi.fn();
    const { rerender } = render(
      <QuotaCard quota={baseQuota} now={Date.now()} refreshing={false} onRefresh={onRefresh} />
    );
    screen.getByRole('button', { name: /刷新 Kimi 工作号 额度/ }).click();
    expect(onRefresh).toHaveBeenCalledTimes(1);

    rerender(
      <QuotaCard quota={baseQuota} now={Date.now()} refreshing onRefresh={onRefresh} />
    );
    const button = screen.getByRole('button', { name: /刷新 Kimi 工作号 额度/ }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it('有 accountId 时才显示删除按钮', () => {
    const onRemove = vi.fn();
    const { rerender } = render(
      <QuotaCard
        quota={baseQuota}
        now={Date.now()}
        refreshing={false}
        onRefresh={() => {}}
        onRemove={onRemove}
      />
    );
    const removeBtn = screen.getByRole('button', { name: /删除 Kimi 工作号/ });
    removeBtn.click();
    expect(onRemove).toHaveBeenCalledTimes(1);

    rerender(
      <QuotaCard
        quota={{ ...baseQuota, accountId: null }}
        now={Date.now()}
        refreshing={false}
        onRefresh={() => {}}
        onRemove={onRemove}
      />
    );
    expect(screen.queryByRole('button', { name: /删除/ })).toBeNull();
  });
});
