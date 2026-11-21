// 「同步到本机」面板：渲染、单条同步、批量队列、失败原因
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { LocalSyncPanel } from './LocalSyncPanel';
import type { QuotaAccountDto } from '../../../api/subscriptionQuotaApi';

const getExportLinks = vi.fn();
const addToast = vi.fn();
const openUrl = vi.fn();

vi.mock('../../../api/subscriptionQuotaApi', () => ({
  getExportLinks: (...args: unknown[]) => getExportLinks(...args),
}));

vi.mock('../../../hooks/useToast', () => ({
  useToast: () => ({ addToast }),
}));

function account(overrides: Partial<QuotaAccountDto> = {}): QuotaAccountDto {
  return {
    id: 'acc-1',
    providerId: 'kimi',
    label: 'Kimi For Coding',
    maskedKey: 'sk-k********XBud',
    hasKey: true,
    extra: {},
    enabled: true,
    sortOrder: 0,
    createdAt: null,
    updatedAt: null,
    category: 'official',
    app: '',
    notes: '',
    websiteUrl: '',
    manualTotal: 0,
    manualUsed: 0,
    quotaUnit: 'credits',
    windowType: 'none',
    windowResetAt: '',
    isManual: false,
    lastGood: null,
    baseUrl: 'https://api.kimi.com/coding/v1',
    ...overrides,
  };
}

function linkItem(overrides: Record<string, unknown> = {}) {
  return {
    accountId: 'acc-1',
    providerId: 'kimi',
    label: 'Kimi For Coding',
    maskedKey: 'sk-k********XBud',
    target: 'magpie',
    url: 'magpie://import?preset=kimi-code&key=sk-test',
    app: 'kimi-code',
    warnings: [],
    ...overrides,
  };
}

beforeEach(() => {
  getExportLinks.mockReset();
  addToast.mockReset();
  openUrl.mockReset();
});

afterEach(() => {
  cleanup();
});

describe('LocalSyncPanel', () => {
  it('渲染账号与两个渠道按钮，并给出本地桥命令', () => {
    render(<LocalSyncPanel accounts={[account()]} onRefresh={() => {}} openUrl={openUrl} />);
    expect(screen.getByText('Kimi For Coding')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'CC Switch' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Magpie' })).toBeTruthy();
    expect(screen.getByText(/subscription_bridge push/)).toBeTruthy();
    expect(screen.getByText(/subscription_bridge pull/)).toBeTruthy();
  });

  it('单条同步：点 Magpie 只取该账号的 magpie 链接', async () => {
    getExportLinks.mockResolvedValue({ target: 'magpie', items: [linkItem()], count: 1 });

    render(<LocalSyncPanel accounts={[account()]} onRefresh={() => {}} openUrl={openUrl} />);
    fireEvent.click(screen.getByRole('button', { name: 'Magpie' }));

    await waitFor(() => expect(getExportLinks).toHaveBeenCalledWith('magpie', ['acc-1']));
    await waitFor(() =>
      expect(addToast).toHaveBeenCalledWith(expect.stringContaining('Magpie'), 'success')
    );
    expect(openUrl).toHaveBeenCalledWith('magpie://import?preset=kimi-code&key=sk-test');
  });

  it('批量同步：生成队列后逐条打开，并显示剩余条数', async () => {
    getExportLinks.mockResolvedValue({
      target: 'ccswitch',
      items: [
        linkItem({
          target: 'ccswitch',
          url: 'ccswitch://v1/import?resource=provider&app=opencode',
          app: 'opencode',
        }),
        linkItem({
          accountId: 'acc-2',
          providerId: 'zhipu',
          label: 'GLM',
          target: 'ccswitch',
          url: null,
          app: '',
          warnings: ['缺少 endpoint'],
        }),
      ],
      count: 2,
    });

    render(
      <LocalSyncPanel
        accounts={[account(), account({ id: 'acc-2', providerId: 'zhipu', label: 'GLM' })]}
        onRefresh={() => {}}
        openUrl={openUrl}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /全选/ }));
    fireEvent.click(screen.getByRole('button', { name: /同步选中到 CC Switch/ }));

    await waitFor(() =>
      expect(getExportLinks).toHaveBeenCalledWith('ccswitch', ['acc-1', 'acc-2'])
    );
    expect(await screen.findByText(/待打开 1 条/)).toBeTruthy();
    expect(screen.getByText(/缺少 endpoint/)).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: /打开下一条/ }));
    await waitFor(() => expect(screen.getByText(/待打开 0 条/)).toBeTruthy());
    expect(openUrl).toHaveBeenCalledTimes(1);
  });

  it('没有 Key 的账号不可勾选', () => {
    render(
      <LocalSyncPanel
        accounts={[account({ hasKey: false, maskedKey: null })]}
        onRefresh={() => {}}
        openUrl={openUrl}
      />
    );
    const checkbox = screen.getByLabelText(/选择 Kimi For Coding/) as HTMLInputElement;
    expect(checkbox.disabled).toBe(true);
  });
});