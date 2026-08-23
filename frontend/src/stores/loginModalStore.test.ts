/**
 * loginModalStore 单元测试 — 全局登录弹框开关与幂等
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useLoginModalStore } from './loginModalStore';

describe('loginModalStore', () => {
  beforeEach(() => {
    useLoginModalStore.getState().closeLoginModal();
  });

  it('初始状态关闭', () => {
    expect(useLoginModalStore.getState().isOpen).toBe(false);
  });

  it('openLoginModal 打开弹框', () => {
    useLoginModalStore.getState().openLoginModal();
    expect(useLoginModalStore.getState().isOpen).toBe(true);
  });

  it('重复 openLoginModal 幂等', () => {
    useLoginModalStore.getState().openLoginModal();
    useLoginModalStore.getState().openLoginModal();
    expect(useLoginModalStore.getState().isOpen).toBe(true);
  });

  it('closeLoginModal 关闭弹框', () => {
    useLoginModalStore.getState().openLoginModal();
    useLoginModalStore.getState().closeLoginModal();
    expect(useLoginModalStore.getState().isOpen).toBe(false);
  });
});
