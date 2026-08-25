/**
 * K8s 底部多标签页面板
 *
 * 替代原有的右侧 PodDetail 抽屉
 * 支持同时打开多个资源的详情，每个标签页独立
 *
 * 将 activeTabId 作为 tabId 传给 PodDetail，
 * PodDetail 从 store 的 openedTabs 中读取对应资源信息
 *
 * 支持通过拖动顶部分隔条调整面板高度（300px ~ 70vh）
 */
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useK8sStore } from '../../../../stores/k8sStore';
import { TabBar } from './TabBar';
import { PodDetail } from '../ResourceDetail/PodDetail';

/** 默认面板高度 */
const DEFAULT_HEIGHT = '50vh';
/** 最小面板高度（像素） */
const MIN_HEIGHT = 300;
/** 最大面板高度占视口百分比 */
const MAX_HEIGHT_PERCENT = 70;

export const BottomPanel: React.FC = () => {
  const { openedTabs, activeTabId } = useK8sStore();
  const [panelHeight, setPanelHeight] = useState(DEFAULT_HEIGHT);
  const [isDragging, setIsDragging] = useState(false);

  /** 拖动开始时鼠标的 Y 坐标 */
  const dragStartYRef = useRef(0);
  /** 拖动开始时的面板高度（像素） */
  const dragStartHeightRef = useRef(0);

  /** 解析面板高度为像素值 */
  const parseHeightToPx = useCallback((height: string): number => {
    if (height.endsWith('vh')) {
      return (parseFloat(height) / 100) * window.innerHeight;
    }
    return parseFloat(height);
  }, []);

  /** 开始拖动：记录初始位置与高度 */
  const handleDragStart = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    dragStartYRef.current = e.clientY;
    dragStartHeightRef.current = parseHeightToPx(panelHeight);
    e.preventDefault();
  }, [panelHeight, parseHeightToPx]);

  /**
   * 拖动过程中监听 document 级别的 mousemove / mouseup
   *
   * 重要：useEffect 必须在条件返回之前声明，
   * 否则当 openedTabs 为空时组件提前返回，effect 不会注册
   */
  useEffect(() => {
    if (!isDragging) return;

    // 拖动期间禁止文本选中
    const prevUserSelect = document.body.style.userSelect;
    document.body.style.userSelect = 'none';

    const handleMouseMove = (e: MouseEvent) => {
      // 向上拖动（clientY 减小）→ 增加高度
      const deltaY = dragStartYRef.current - e.clientY;
      const maxPx = (MAX_HEIGHT_PERCENT / 100) * window.innerHeight;
      const newHeight = Math.max(
        MIN_HEIGHT,
        Math.min(maxPx, dragStartHeightRef.current + deltaY),
      );
      setPanelHeight(`${newHeight}px`);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.body.style.userSelect = prevUserSelect;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  // 如果没有打开的标签，不渲染（放在所有 hooks 之后，遵守 React 规则）
  if (openedTabs.length === 0) return null;

  return (
    <div
      className="absolute bottom-0 left-0 right-0 bg-canvas border-t border-border z-40 shadow-lg animate-slide-in-bottom flex flex-col"
      style={{ height: panelHeight }}
    >
      {/* 标签栏 */}
      <TabBar />

      {/* 可拖动分隔条 */}
      <div
        onMouseDown={handleDragStart}
        className={`h-1 transition-colors ${
          isDragging
            ? 'bg-accent cursor-grabbing'
            : 'bg-surface-2 hover:bg-accent-hover cursor-grab'
        }`}
        title="拖动调整面板高度"
      />

      {/* 内容区域 */}
      <div className="flex-1 overflow-hidden">
        {activeTabId && <PodDetail tabId={activeTabId} />}
      </div>
    </div>
  );
};
