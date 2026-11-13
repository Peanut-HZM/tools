/**
 * 连接名称宽度自适应钩子
 *
 * 背景：K8s 控制台左侧连接列表宽度是**固定**的（默认 256px，可拖到
 * 200~500px），而每行的固定装饰（拖动把手、健康状态点、来源图标、存储位置
 * 徽章、3 个操作按钮）会占掉大半宽度，导致连接名称被截断成
 * "ai-wor..." / "ai-spa..."。
 *
 * 用户诉求：**连接名称必须在同一行完整展示**，左侧列表宽度应当自适应。
 *
 * 方案
 * ----
 * 直接量出每一行的**固定装饰宽度**，再加上最长名称的完整宽度，反推所需
 * 侧栏宽度：
 *
 *   1. 行外装饰 = 行宽 - 名称按钮宽
 *      名称按钮是 ``flex-1``，会吸收行内所有富余空间，所以这个差值就是
 *      拖动把手 + 操作按钮 + 间距的**精确**宽度。
 *   2. 按钮内装饰 = 名称行内除名称外所有兄弟元素的宽度之和（含 margin）
 *      ——直接量元素，不用"按钮宽 - 名称宽"反推（名称不撑满时那个差值
 *      会把富余空间也算进去，导致宽度被放大到上限）。
 *   3. 名称完整宽度 = ``scrollWidth``（即使被截断，scrollWidth 仍是完整
 *      文本的宽度）。
 *   4. 所需侧栏宽度 = 列表内边距 + 行外装饰 + 按钮内装饰 + 最长名称宽度
 *
 * 关键：这个结果**与当前侧栏宽度无关**，因此不会震荡（名称已完整显示时
 * 不会误判成"不需要调整"）。
 */
import { useCallback, useEffect, useRef, useState } from 'react';

/** 侧栏最小 / 最大宽度（与 K8sTool 拖动分隔条的限制一致）。 */
export const MIN_SIDEBAR_WIDTH = 200;
export const MAX_SIDEBAR_WIDTH = 500;

/** 名称完整显示后额外留的呼吸空间（px）。 */
const NAME_GAP = 4;

interface UseNameFitWidthResult {
  /** 挂到每个名称元素上的 ref 回调（按 index 注册） */
  registerName: (index: number) => (el: HTMLElement | null) => void;
  /** 让所有名称完整显示所需的侧栏宽度（px） */
  requiredWidth: number;
}

/** 量出某个元素及其左右 margin 占用的横向空间。 */
function measureOuterWidth(el: Element): number {
  const rect = el.getBoundingClientRect();
  const styles = window.getComputedStyle(el);
  const marginLeft = parseFloat(styles.marginLeft) || 0;
  const marginRight = parseFloat(styles.marginRight) || 0;
  return rect.width + marginLeft + marginRight;
}

/**
 * 观察名称元素，实时算出"让所有名称完整显示所需的侧栏宽度"。
 *
 * @param sidebarRef 侧栏根元素（用于读取列表内边距）
 */
export function useNameFitWidth(
  sidebarRef: React.RefObject<HTMLElement | null>,
): UseNameFitWidthResult {
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
    const sidebar = sidebarRef.current;
    if (!sidebar) return;

    let longestNameWidth = 0;
    let outsideChrome = 0;
    let insideChrome = 0;

    for (const el of nameElements.current.values()) {
      // 3) 名称完整宽度（截断时 scrollWidth 依然是完整文本宽度）
      longestNameWidth = Math.max(longestNameWidth, el.scrollWidth);

      const button = el.closest('button') as HTMLElement | null;
      const row = el.closest('div.group') as HTMLElement | null;

      // 1) 行外装饰：名称按钮是 flex-1，吸收了行内富余空间，
      //    所以「行宽 - 按钮宽」就是拖动把手 + 操作按钮的精确宽度
      if (button && row) {
        outsideChrome = Math.max(
          outsideChrome,
          row.getBoundingClientRect().width - button.getBoundingClientRect().width,
        );
      }

      // 2) 按钮内装饰：名称所在 flex 行里，除名称外的兄弟元素宽度之和
      const nameRow = el.parentElement;
      if (nameRow) {
        let chrome = 0;
        for (const child of Array.from(nameRow.children)) {
          if (child === el) continue;
          chrome += measureOuterWidth(child);
        }
        insideChrome = Math.max(insideChrome, chrome);
      }
    }

    if (longestNameWidth === 0) {
      setRequiredWidth(0);
      return;
    }

    // 列表容器的左右内边距（p-2）
    const list = sidebar.querySelector('.space-y-1') as HTMLElement | null;
    const listStyles = list ? window.getComputedStyle(list) : null;
    const paddingLeft = listStyles ? parseFloat(listStyles.paddingLeft) || 0 : 0;
    const paddingRight = listStyles ? parseFloat(listStyles.paddingRight) || 0 : 0;

    const needed =
      paddingLeft +
      paddingRight +
      outsideChrome +
      insideChrome +
      longestNameWidth +
      NAME_GAP;

    setRequiredWidth(
      Math.min(MAX_SIDEBAR_WIDTH, Math.max(MIN_SIDEBAR_WIDTH, Math.ceil(needed))),
    );
  }, [sidebarRef]);

  useEffect(() => {
    const sidebar = sidebarRef.current;
    if (!sidebar) return;

    if (typeof ResizeObserver === 'undefined') {
      // 环境不支持时退化为一次性测量
      recompute();
      return;
    }

    const observer = new ResizeObserver(() => recompute());
    observer.observe(sidebar);

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
  }, [sidebarRef, recompute]);

  return { registerName, requiredWidth };
}
