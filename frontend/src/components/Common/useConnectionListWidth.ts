/**
 * 连接列表侧栏宽度自适应钩子（通用版）
 *
 * 背景
 * ----
 * SSH / Redis / 数据库等工具的左侧连接列表宽度是**固定**的（256~280px），
 * 而每行还有一堆固定装饰（展开箭头、类型图标、环境徽章、存储位置徽章、
 * 若干操作按钮），导致连接名称被截断成
 * "logistics-fina..." / "community-p..." / "smar..." / "gld-j..."，
 * 用户根本无法分辨是哪个连接。
 *
 * 方案
 * ----
 * 反推「让所有名称完整显示所需的侧栏宽度」：
 *
 *   1. 名称的自然宽度 = 临时设 ``width: max-content`` 量到的文本完整宽度
 *      （不依赖当前分配宽度，因此不会震荡）
 *   2. 名称当前实际占用宽度 = 元素渲染宽度
 *   3. **缺口** = 自然宽度 - 实际占用宽度（> 0 说明名称被截断了）
 *   4. 所需侧栏宽度 = 当前侧栏宽度 + 最大缺口
 *
 * 「当前侧栏宽度 + 缺口」这个写法的好处：侧栏里除了名称还有徽章、图标、
 * 操作按钮等固定装饰，它们占多少宽度与侧栏宽度无关；侧栏每加 1px，
 * 全部富余空间都会流向名称（名称所在容器是 flex-1）。所以只需要把
 * 「被截断掉的那部分」补回去即可，无需枚举每一层装饰。
 * 名称完全显示时缺口为 0，此时**不更新**所需宽度（只增不减），
 * 因此用户把侧栏拖宽后再拖窄也不会出现来回震荡。
 */
import { useCallback, useEffect, useRef, useState } from 'react';

/** 侧栏最小 / 最大宽度（px）。 */
export const MIN_SIDEBAR_WIDTH = 200;
export const MAX_SIDEBAR_WIDTH = 560;

/** 名称完整显示后额外留的呼吸空间（px）。 */
const NAME_GAP = 4;

interface UseConnectionListWidthResult {
  /** 挂到每个名称元素上的 ref 回调（按 index 注册） */
  registerName: (index: number) => (el: HTMLElement | null) => void;
  /** 让所有名称完整显示所需的侧栏宽度（px）；0 表示尚未测量 */
  requiredWidth: number;
}

/**
 * 量出名称元素的自然宽度（不换行、不截断的完整文本宽度）。
 *
 * 直接用 scrollWidth 不可靠：名称未被截断时 scrollWidth 会等于当前分配宽度
 * （把 flex 富余空间也算进来）。临时设 ``width: max-content`` + ``flex-shrink: 0``
 * 量一次最准，且结果与当前宽度无关（因此不会震荡）。
 */
function measureNaturalWidth(el: HTMLElement): number {
  const prevWidth = el.style.width;
  const prevMaxWidth = el.style.maxWidth;
  const prevShrink = el.style.flexShrink;
  el.style.width = 'max-content';
  el.style.maxWidth = 'none';
  el.style.flexShrink = '0';
  const natural = el.getBoundingClientRect().width;
  el.style.width = prevWidth;
  el.style.maxWidth = prevMaxWidth;
  el.style.flexShrink = prevShrink;
  return natural;
}

/**
 * 观察名称元素，实时算出"让所有名称完整显示所需的侧栏宽度"。
 *
 * @param listRef 列表容器元素（用于读取列表内边距）
 */
export function useConnectionListWidth(
  listRef: React.RefObject<HTMLElement | null>,
): UseConnectionListWidthResult {
  const nameElements = useRef(new Map<number, HTMLElement>());
  const [requiredWidth, setRequiredWidth] = useState(0);

  const registerName = useCallback((index: number) => {
    return (el: HTMLElement | null) => {
      if (el) {
        nameElements.current.set(index, el);
      } else {
        nameElements.current.delete(index);
      }
    };
  }, []);

  const recompute = useCallback(() => {
    const root = listRef.current;
    if (!root) return;

    let maxDeficit = 0;

    for (const el of nameElements.current.values()) {
      // 缺口 = 自然宽度 - 实际占用宽度
      const natural = measureNaturalWidth(el);
      const actual = el.getBoundingClientRect().width;
      maxDeficit = Math.max(maxDeficit, natural - actual);
    }

    if (maxDeficit <= 0) {
      // 名称已完整显示：保持当前所需宽度不变（只增不减，避免震荡）
      return;
    }

    // 当前侧栏宽度：列表 clientWidth 已含自身内边距，即等于侧栏内容宽度
    const listEl = root.classList.contains('space-y-1')
      ? root
      : ((root.querySelector('.space-y-1') as HTMLElement | null) ?? root);
    const currentSidebarWidth = listEl.clientWidth;

    const needed = currentSidebarWidth + maxDeficit + NAME_GAP;

    const next = Math.min(MAX_SIDEBAR_WIDTH, Math.max(MIN_SIDEBAR_WIDTH, Math.ceil(needed)));
    // 只增不减：名称已完整显示时（缺口为 0）上面的分支会直接 return，
    // 这里再兜一层，确保所需宽度单调不减，避免与用户拖拽互相打架。
    setRequiredWidth((prev) => Math.max(prev, next));
  }, [listRef]);

  useEffect(() => {
    const root = listRef.current;
    if (!root) return;

    if (typeof ResizeObserver === 'undefined') {
      recompute();
      return;
    }

    const observer = new ResizeObserver(() => recompute());
    observer.observe(root);

    // 名称元素在首次渲染后才挂上 ref，需要在下一帧补进观察列表
    const raf = requestAnimationFrame(() => {
      for (const el of nameElements.current.values()) {
        observer.observe(el);
      }
      recompute();
    });

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
    };
  }, [listRef, recompute]);

  return { registerName, requiredWidth };
}
