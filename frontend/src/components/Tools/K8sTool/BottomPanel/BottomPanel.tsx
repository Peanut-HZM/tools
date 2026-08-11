/**
 * K8s 底部多标签页面板
 *
 * 替代原有的右侧 PodDetail 抽屉
 * 支持同时打开多个资源的详情，每个标签页独立
 *
 * 注意：当前 PodDetail 尚未接受 tabId prop（将在 Task 3 中实现）
 * 目前仅根据 activeTabId 决定是否渲染 PodDetail
 */
import React, { useState } from 'react';
import { useK8sStore } from '../../../../stores/k8sStore';
import { TabBar } from './TabBar';
import { PodDetail } from '../ResourceDetail/PodDetail';

/** 默认面板高度 */
const DEFAULT_HEIGHT = '50vh';

export const BottomPanel: React.FC = () => {
  const { openedTabs, activeTabId } = useK8sStore();
  const [panelHeight, setPanelHeight] = useState(DEFAULT_HEIGHT);
  const [isDragging, setIsDragging] = useState(false);

  // 如果没有打开的标签，不渲染
  if (openedTabs.length === 0) return null;

  /** 处理拖动调整面板高度 */
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const windowHeight = window.innerHeight;
    const newHeight = windowHeight - e.clientY;
    // 限制最小高度 300px，最大高度为窗口 70%
    const minHeight = 300;
    const maxHeight = windowHeight * 0.7;
    const clampedHeight = Math.max(minHeight, Math.min(maxHeight, newHeight));
    setPanelHeight(`${clampedHeight}px`);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  return (
    <div
      className="absolute bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-700 z-40 shadow-2xl animate-slide-in-bottom"
      style={{ height: panelHeight }}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* 标签栏 */}
      <TabBar />

      {/* 可拖动分隔条 */}
      <div
        onMouseDown={(e) => {
          setIsDragging(true);
          e.preventDefault();
        }}
        className={`h-1 bg-slate-700 hover:bg-blue-500 cursor-row-resize transition-colors ${
          isDragging ? 'bg-blue-500' : ''
        }`}
      />

      {/* 内容区域 */}
      <div className="flex-1 overflow-hidden">
        {activeTabId && <PodDetail />}
      </div>
    </div>
  );
};
