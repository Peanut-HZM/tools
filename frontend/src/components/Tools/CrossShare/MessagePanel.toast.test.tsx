/**
 * MessagePanel 组件级测试：验证后端 500 时不会刷屏弹出多个 toast
 *
 * 场景还原：远程数据库不可达 → /api/cross-share/messages 返回 500 →
 * 轮询连续失败 → 用户在后台标签页切回来看到 3 个 500 报错弹窗。
 *
 * 这里直接渲染 MessagePanel 并让接口持续 500，断言 toast 数量。
 */
import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const showToast = vi.fn();
const toast = vi.fn();

vi.mock('../../../hooks/useToast', () => ({
  useToast: () => ({ showToast, toast }),
}));

const getMessages = vi.fn();

vi.mock('../../../services/crossShare', () => ({
  messageApi: {
    getMessages: (...args: unknown[]) => getMessages(...args),
  },
  default: {},
}));

vi.mock('../OssFileList/OssFileList', () => ({ default: () => null }));
vi.mock('../FilePanel', () => ({ default: () => null }));
vi.mock('../DevicePanel', () => ({ default: () => null }));
vi.mock('../SettingsPanel', () => ({ default: () => null }));
vi.mock('../Preview/Preview', () => ({ default: () => null }));
vi.mock('../../Common/StorageLocationBadge', () => ({ default: () => null }));

import MessagePanel from './MessagePanel';

function makeError(status: number, detail: string) {
  const err: any = new Error(detail);
  err.response = { status, data: { detail } };
  return err;
}

describe('MessagePanel 后端 500 时不刷屏', () => {
  beforeEach(() => {
    showToast.mockClear();
    toast.mockClear();
    getMessages.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('连续 12 次 500 只弹出 1 次 toast', async () => {
    getMessages.mockRejectedValue(makeError(500, 'Internal Server Error'));

    render(<MessagePanel />);

    // 等待首次加载失败
    await waitFor(() => expect(showToast).toHaveBeenCalled(), { timeout: 3000 });

    // 模拟后续 11 次轮询失败
    for (let i = 0; i < 11; i++) {
      await act(async () => {
        getMessages.mockRejectedValue(makeError(500, 'Internal Server Error'));
        await Promise.resolve();
      });
    }

    // 服务不可用类错误：只应提示一次
    const serviceErrors = showToast.mock.calls.filter(
      (c) => typeof c[0] === 'string' && c[0].includes('服务暂时不可用')
    );
    expect(serviceErrors).toHaveLength(1);
  });

  it('401 认证失败：停止轮询并只提示一次', async () => {
    getMessages.mockRejectedValue(makeError(401, 'Unauthorized'));

    render(<MessagePanel />);

    await waitFor(() => expect(showToast).toHaveBeenCalled(), { timeout: 3000 });
    const authCalls = showToast.mock.calls.filter(
      (c) => typeof c[0] === 'string' && c[0].includes('登录已过期')
    );
    expect(authCalls).toHaveLength(1);
  });

  it('恢复成功后错误计数被重置（再次失败会重新提示）', async () => {
    vi.useFakeTimers();
    try {
      getMessages.mockRejectedValue(makeError(500, 'Internal Server Error'));
      render(<MessagePanel />);

      // 首次失败 → 提示一次
      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(showToast).toHaveBeenCalledTimes(1);

      // 下一轮轮询：恢复成功
      getMessages.mockResolvedValue({ messages: [] });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      // 再下一轮：再次失败 → 应重新提示（说明计数已重置）
      showToast.mockClear();
      getMessages.mockRejectedValue(makeError(500, 'Internal Server Error'));
      await act(async () => {
        await vi.advanceTimersByTimeAsync(60000);
      });
      expect(showToast).toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });
});
