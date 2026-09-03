/**
 * K8s 控制台 - 右侧抽屉组件
 *
 * 从右侧滑入的详情面板，宽度 50vw
 * 点击遮罩层或关闭按钮可关闭
 * 动画时长 300ms
 */
import React from 'react';
import { X } from 'lucide-react';
import { useK8sStore } from '../../../../stores/k8sStore';
import { PodDetail } from '../ResourceDetail/PodDetail';

export const RightDrawer: React.FC = () => {
  const { rightDrawerOpen, rightDrawerResource, closeRightDrawer } = useK8sStore();

  if (!rightDrawerOpen || !rightDrawerResource) {
    return null;
  }

  return (
    <>
      {/* 遮罩层 */}
      <div
        className="fixed inset-0 bg-black/50 z-40 transition-opacity duration-300"
        onClick={closeRightDrawer}
      />

      {/* 抽屉 */}
      <div
        className={`
          fixed top-0 right-0 h-full w-[50vw] bg-surface-1 shadow-2xl z-50
          transform transition-transform duration-300 ease-in-out
          ${rightDrawerOpen ? 'translate-x-0' : 'translate-x-full'}
        `}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-1 sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-ink truncate max-w-[calc(50vw-120px)]">
              {rightDrawerResource.name}
            </h2>
            <span className="text-xs text-ink-faint bg-surface-2 px-2 py-0.5 rounded">
              {rightDrawerResource.namespace}
            </span>
          </div>
          <button
            onClick={closeRightDrawer}
            className="p-1.5 hover:bg-surface-2 rounded transition-colors text-ink-muted hover:text-ink"
            title="关闭"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 内容区域 */}
        <div className="h-[calc(100%-52px)] overflow-auto">
          <PodDetail resource={rightDrawerResource} />
        </div>
      </div>
    </>
  );
};
