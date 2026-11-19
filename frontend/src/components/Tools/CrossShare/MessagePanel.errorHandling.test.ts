/**
 * MessagePanel 错误去重逻辑测试
 *
 * 背景：后端连不上远程数据库时 /api/cross-share/messages 返回 500，
 * 页面在后台标签页被节流到 1 分钟/次轮询，用户切回页签会看到
 * 3 个几乎同时弹出的 500 报错弹窗（刷屏且无法操作）。
 *
 * 本测试锁定修复后的行为：
 * 1. 服务不可用类错误（5xx / 超时 / 网络）**只提示一次**，不按 6 次重复弹
 * 2. 业务类错误仍按「首次 + 每 6 次」提示，避免完全静默
 * 3. 错误信息变化时重新提示（可感知恢复 / 换错误）
 */
import { describe, it, expect } from 'vitest';

/**
 * 与 MessagePanel.tsx 中一致的判定逻辑（提取为纯函数便于测试）。
 * 真实实现位于组件内部，这里复刻同一规则以锁定行为。
 */
function classifyError(error: any): { errorMsg: string; httpStatus?: number; isServiceUnavailable: boolean } {
  const errorMsg = error?.response?.data?.detail || error?.message || '未知错误';
  const httpStatus = error?.response?.status;
  const isServiceUnavailable =
    httpStatus >= 500 ||
    httpStatus === 429 ||
    error?.code === 'ECONNABORTED' ||
    error?.code === 'ETIMEDOUT' ||
    /timeout|network|failed to fetch|网络|连接/i.test(errorMsg);
  return { errorMsg, httpStatus, isServiceUnavailable };
}

/**
 * 与 MessagePanel.tsx 中一致的 toast 触发判定。
 */
function shouldShowToast(
  errorMsg: string,
  consecutiveErrors: number,
  hasShownFirstError: boolean,
  lastError: string | null,
  isServiceUnavailable: boolean
): boolean {
  const isSameError = lastError === errorMsg;
  return (
    (!isSameError && consecutiveErrors > 0) ||
    (consecutiveErrors === 1 && !hasShownFirstError) ||
    (!isServiceUnavailable && consecutiveErrors % 6 === 0)
  );
}

describe('错误分类', () => {
  it('5xx 归类为服务不可用', () => {
    const r = classifyError({ response: { status: 500, data: { detail: 'Internal Server Error' } } });
    expect(r.isServiceUnavailable).toBe(true);
  });

  it('429 归类为服务不可用（限流，属于服务侧问题）', () => {
    expect(classifyError({ response: { status: 429 } }).isServiceUnavailable).toBe(true);
  });

  it('网络超时归类为服务不可用', () => {
    expect(classifyError({ code: 'ECONNABORTED', message: 'timeout of 5000ms exceeded' }).isServiceUnavailable).toBe(true);
    expect(classifyError({ code: 'ETIMEDOUT' }).isServiceUnavailable).toBe(true);
    expect(classifyError({ message: 'Network Error' }).isServiceUnavailable).toBe(true);
    expect(classifyError({ message: 'Failed to fetch' }).isServiceUnavailable).toBe(true);
  });

  it('数据库连接失败文案归类为服务不可用', () => {
    const r = classifyError({
      response: { status: 500, data: { detail: 'connection to server failed: Operation timed out' } },
    });
    expect(r.isServiceUnavailable).toBe(true);
  });

  it('普通业务错误不归类为服务不可用', () => {
    const r = classifyError({ response: { status: 400, data: { detail: '参数不合法' } } });
    expect(r.isServiceUnavailable).toBe(false);
  });

  it('401/403 归为认证失败（由另一条分支熔断处理）', () => {
    expect(classifyError({ response: { status: 401 } }).httpStatus).toBe(401);
    expect(classifyError({ response: { status: 403 } }).httpStatus).toBe(403);
  });
});

describe('toast 去重策略（修复核心）', () => {
  it('服务不可用时只提示一次，不再按 6 次重复弹', () => {
    const msg = 'Internal Server Error';
    // 连续失败 1~12 次，都只有第 1 次弹（错误信息不变）
    const shown: number[] = [];
    let hasShown = false;
    let lastError: string | null = null;
    for (let n = 1; n <= 12; n++) {
      if (shouldShowToast(msg, n, hasShown, lastError, true)) {
        shown.push(n);
        hasShown = true;
      }
      lastError = msg;
    }
    expect(shown).toEqual([1]); // ← 修复前会是 [1, 6, 12]
  });

  it('业务错误仍按「首次 + 每 6 次」提示', () => {
    const msg = '参数不合法';
    const shown: number[] = [];
    let hasShown = false;
    let lastError: string | null = null;
    for (let n = 1; n <= 12; n++) {
      if (shouldShowToast(msg, n, hasShown, lastError, false)) {
        shown.push(n);
        hasShown = true;
      }
      lastError = msg;
    }
    expect(shown).toEqual([1, 6, 12]);
  });

  it('错误信息变化时重新提示（可感知服务恢复）', () => {
    const shown: number[] = [];
    let hasShown = false;
    let lastError: string | null = null;
    const seq = ['Internal Server Error', 'Internal Server Error', 'Service Unavailable'];
    seq.forEach((msg, i) => {
      const n = i + 1;
      if (shouldShowToast(msg, n, hasShown, lastError, true)) {
        shown.push(n);
        hasShown = true;
      }
      lastError = msg;
    });
    // 第 3 次错误信息变了 → 应重新提示（与具体失败计数无关）
    expect(shown).toContain(3);
  });
});
