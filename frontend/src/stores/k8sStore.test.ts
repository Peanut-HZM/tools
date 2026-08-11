/**
 * k8sStore 多标签页状态管理单元测试
 *
 * 覆盖 openResourceTab / closeResourceTab / setActiveTab / clearAllTabs 四个 action
 *
 * 注意：Zustand 的 getState() 返回状态快照，
 * 每次 action 调用后必须重新 getState() 获取最新状态再做断言。
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useK8sStore } from './k8sStore';

/** 构造一个 ResourceTab 测试数据 */
const makeTab = (id: string) => ({
  id,
  type: 'pod',
  namespace: 'default',
  name: id,
});

/** 便捷读取当前 store 状态 */
const state = () => useK8sStore.getState();

describe('k8sStore 多标签页状态管理', () => {
  beforeEach(() => {
    // 每个用例前重置标签页状态，保证用例隔离
    useK8sStore.getState().clearAllTabs();
  });

  // ---------- openResourceTab ----------

  describe('openResourceTab', () => {
    it('打开新标签页时，追加到 openedTabs 并将 activeTabId 设置为新标签 id', () => {
      const tab = makeTab('pod-default-nginx');
      useK8sStore.getState().openResourceTab(tab);

      expect(state().openedTabs).toHaveLength(1);
      expect(state().openedTabs[0]).toEqual(tab);
      expect(state().activeTabId).toBe('pod-default-nginx');
    });

    it('连续打开多个新标签页，依次追加并激活最后一个', () => {
      useK8sStore.getState().openResourceTab(makeTab('tab-1'));
      useK8sStore.getState().openResourceTab(makeTab('tab-2'));

      expect(state().openedTabs).toHaveLength(2);
      expect(state().openedTabs.map((t) => t.id)).toEqual(['tab-1', 'tab-2']);
      expect(state().activeTabId).toBe('tab-2');
    });

    it('打开已存在的标签页时，不重复追加，仅切换 activeTabId', () => {
      useK8sStore.getState().openResourceTab(makeTab('tab-1'));
      useK8sStore.getState().openResourceTab(makeTab('tab-2'));
      // 重新打开 tab-1（已存在）
      useK8sStore.getState().openResourceTab(makeTab('tab-1'));

      // 标签页数量不变
      expect(state().openedTabs).toHaveLength(2);
      expect(state().openedTabs.map((t) => t.id)).toEqual(['tab-1', 'tab-2']);
      // activeTabId 切换到已存在的 tab-1
      expect(state().activeTabId).toBe('tab-1');
    });
  });

  // ---------- closeResourceTab ----------

  describe('closeResourceTab', () => {
    it('关闭当前激活标签页（存在多个标签页时），激活最后一个剩余标签页', () => {
      useK8sStore.getState().openResourceTab(makeTab('tab-1'));
      useK8sStore.getState().openResourceTab(makeTab('tab-2'));
      useK8sStore.getState().openResourceTab(makeTab('tab-3'));
      // 此时 activeTabId = 'tab-3'
      expect(state().activeTabId).toBe('tab-3');

      // 关闭激活的 tab-3
      useK8sStore.getState().closeResourceTab('tab-3');

      expect(state().openedTabs).toHaveLength(2);
      expect(state().openedTabs.map((t) => t.id)).toEqual(['tab-1', 'tab-2']);
      // 切换到最后一个剩余标签页
      expect(state().activeTabId).toBe('tab-2');
    });

    it('关闭最后一个标签页时，activeTabId 置 null，openedTabs 置空', () => {
      useK8sStore.getState().openResourceTab(makeTab('only-tab'));
      expect(state().openedTabs).toHaveLength(1);

      useK8sStore.getState().closeResourceTab('only-tab');

      expect(state().openedTabs).toEqual([]);
      expect(state().activeTabId).toBeNull();
    });

    it('关闭非激活标签页时，activeTabId 保持不变', () => {
      useK8sStore.getState().openResourceTab(makeTab('tab-1'));
      useK8sStore.getState().openResourceTab(makeTab('tab-2'));
      useK8sStore.getState().openResourceTab(makeTab('tab-3'));
      // activeTabId = 'tab-3'
      expect(state().activeTabId).toBe('tab-3');

      // 关闭非激活的 tab-1
      useK8sStore.getState().closeResourceTab('tab-1');

      expect(state().openedTabs).toHaveLength(2);
      expect(state().openedTabs.map((t) => t.id)).toEqual(['tab-2', 'tab-3']);
      // activeTabId 不受影响
      expect(state().activeTabId).toBe('tab-3');
    });

    it('关闭不存在的标签页时，状态不变', () => {
      useK8sStore.getState().openResourceTab(makeTab('tab-1'));

      useK8sStore.getState().closeResourceTab('non-existent-id');

      expect(state().openedTabs).toHaveLength(1);
      expect(state().activeTabId).toBe('tab-1');
    });
  });

  // ---------- setActiveTab ----------

  describe('setActiveTab', () => {
    it('将 activeTabId 设置为指定的 id', () => {
      useK8sStore.getState().openResourceTab(makeTab('tab-1'));
      useK8sStore.getState().openResourceTab(makeTab('tab-2'));
      // 默认激活最后打开的 tab-2
      expect(state().activeTabId).toBe('tab-2');

      useK8sStore.getState().setActiveTab('tab-1');

      expect(state().activeTabId).toBe('tab-1');
      // openedTabs 内容不变
      expect(state().openedTabs).toHaveLength(2);
    });
  });

  // ---------- clearAllTabs ----------

  describe('clearAllTabs', () => {
    it('重置 openedTabs 为空数组，activeTabId 为 null', () => {
      useK8sStore.getState().openResourceTab(makeTab('tab-1'));
      useK8sStore.getState().openResourceTab(makeTab('tab-2'));
      useK8sStore.getState().openResourceTab(makeTab('tab-3'));

      // 验证前置状态
      expect(state().openedTabs).toHaveLength(3);
      expect(state().activeTabId).toBe('tab-3');

      useK8sStore.getState().clearAllTabs();

      expect(state().openedTabs).toEqual([]);
      expect(state().activeTabId).toBeNull();
    });

    it('空状态下调用 clearAllTabs 不会报错，状态仍为空', () => {
      useK8sStore.getState().clearAllTabs();

      expect(state().openedTabs).toEqual([]);
      expect(state().activeTabId).toBeNull();
    });
  });
});
