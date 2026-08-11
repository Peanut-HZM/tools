/**
 * k8sStore 多标签页状态管理单元测试
 *
 * 覆盖 openResourceTab / closeResourceTab / setActiveTab / clearAllTabs 四个 action
 *
 * 注意：Zustand 的 getState() 返回状态快照，
 * 每次 action 调用后必须重新 getState() 获取最新状态再做断言。
 */
import { describe, it, expect, beforeEach, test } from 'vitest';
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

    it('标签数量达到 10 个上限时，阻止新增标签', () => {
      // 打开 10 个标签
      for (let i = 1; i <= 10; i++) {
        useK8sStore.getState().openResourceTab(makeTab(`tab-${i}`));
      }
      expect(state().openedTabs).toHaveLength(10);

      // 尝试打开第 11 个标签
      useK8sStore.getState().openResourceTab(makeTab('tab-11'));

      // 标签数量仍为 10
      expect(state().openedTabs).toHaveLength(10);
      // activeTabId 不应变更（仍为 tab-10）
      expect(state().activeTabId).toBe('tab-10');
    });

    it('标签数量达到上限时，打开已存在的标签仍可切换 activeTabId', () => {
      // 打开 10 个标签
      for (let i = 1; i <= 10; i++) {
        useK8sStore.getState().openResourceTab(makeTab(`tab-${i}`));
      }
      expect(state().activeTabId).toBe('tab-10');

      // 切换到已存在的 tab-1（不应被限制）
      useK8sStore.getState().openResourceTab(makeTab('tab-1'));

      // 标签数量不变
      expect(state().openedTabs).toHaveLength(10);
      // activeTabId 切换到 tab-1
      expect(state().activeTabId).toBe('tab-1');
    });

    it('关闭标签后再新增标签，可以正常打开', () => {
      // 打开 10 个标签
      for (let i = 1; i <= 10; i++) {
        useK8sStore.getState().openResourceTab(makeTab(`tab-${i}`));
      }
      expect(state().openedTabs).toHaveLength(10);

      // 关闭一个标签
      useK8sStore.getState().closeResourceTab('tab-10');
      expect(state().openedTabs).toHaveLength(9);

      // 新增标签应该成功
      useK8sStore.getState().openResourceTab(makeTab('tab-11'));
      expect(state().openedTabs).toHaveLength(10);
      expect(state().activeTabId).toBe('tab-11');
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

  // ---------- setActiveConnection（连接切换） ----------

  describe('setActiveConnection', () => {
    it('切换连接清空已打开的标签页', () => {
      useK8sStore.getState().openResourceTab({ id: 'pod-ns-a', type: 'pod', namespace: 'default', name: 'a' });
      useK8sStore.getState().openResourceTab({ id: 'pod-ns-b', type: 'pod', namespace: 'default', name: 'b' });
      expect(useK8sStore.getState().openedTabs.length).toBe(2);
      useK8sStore.getState().setActiveConnection('connection-2');
      expect(useK8sStore.getState().openedTabs.length).toBe(0);
      expect(useK8sStore.getState().activeTabId).toBeNull();
    });
  });
});

describe('activeSubTabs 子 Tab 持久化', () => {
  beforeEach(() => {
    useK8sStore.getState().clearAllTabs();
  });

  test('setActiveSubTab 存储指定标签的子 Tab', () => {
    const { setActiveSubTab } = useK8sStore.getState();
    setActiveSubTab('tab-1', 'logs');
    expect(useK8sStore.getState().activeSubTabs['tab-1']).toBe('logs');
  });

  test('不同标签的子 Tab 状态独立', () => {
    const { setActiveSubTab } = useK8sStore.getState();
    setActiveSubTab('tab-1', 'logs');
    setActiveSubTab('tab-2', 'terminal');
    expect(useK8sStore.getState().activeSubTabs['tab-1']).toBe('logs');
    expect(useK8sStore.getState().activeSubTabs['tab-2']).toBe('terminal');
  });

  test('closeResourceTab 清理对应的 activeSubTabs 条目', () => {
    const { openResourceTab, setActiveSubTab, closeResourceTab } = useK8sStore.getState();
    openResourceTab({ id: 'tab-1', type: 'pod', namespace: 'default', name: 'a' });
    setActiveSubTab('tab-1', 'logs');
    closeResourceTab('tab-1');
    expect(useK8sStore.getState().activeSubTabs['tab-1']).toBeUndefined();
  });

  test('clearAllTabs 清空所有 activeSubTabs', () => {
    const { setActiveSubTab, clearAllTabs } = useK8sStore.getState();
    setActiveSubTab('tab-1', 'logs');
    setActiveSubTab('tab-2', 'terminal');
    clearAllTabs();
    expect(useK8sStore.getState().activeSubTabs).toEqual({});
  });
});
