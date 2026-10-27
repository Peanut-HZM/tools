/**
 * 可调节宽度面板组件
 */
import { useState, useCallback, useRef } from 'react';

interface ResizablePanelProps {
  children: React.ReactNode;
  defaultWidth?: number;
  minWidth?: number;
  maxWidth?: number;
  storageKey?: string;
  /** 外层容器类名：用于响应式覆盖容器高度/宽度 */
  className?: string;
  /**
   * 移动端（< md）是否整行铺满。
   * 开启后窄屏下面板占满整行（配合父级 flex-col 纵向堆叠），
   * md 以上仍使用可拖拽的固定宽度；关闭时保持原有的固定宽度行为。
   */
  mobileFullWidth?: boolean;
}

export default function ResizablePanel({
  children,
  defaultWidth = 280,
  minWidth = 200,
  maxWidth = 500,
  storageKey,
  className = 'h-full',
  mobileFullWidth = false,
}: ResizablePanelProps) {
  const [width, setWidth] = useState(() => {
    if (storageKey) {
      const saved = localStorage.getItem(storageKey);
      if (saved) return parseInt(saved, 10);
    }
    return defaultWidth;
  });

  const isResizing = useRef(false);

  const startResize = useCallback((e: React.MouseEvent) => {
    isResizing.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const startX = e.clientX;
    const startWidth = width;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!isResizing.current) return;

      const delta = moveEvent.clientX - startX;
      const newWidth = Math.min(Math.max(startWidth + delta, minWidth), maxWidth);
      setWidth(newWidth);

      if (storageKey) {
        localStorage.setItem(storageKey, newWidth.toString());
      }
    };

    const handleMouseUp = () => {
      isResizing.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [width, minWidth, maxWidth, storageKey]);

  return (
    <div className={`flex ${className}`}>
      {/*
        宽度改由 CSS 变量驱动（拖拽时只更新变量，宽度实时生效）：
        - 移动端整行模式：w-full 铺满，md 以上恢复为可拖拽宽度
        - 固定宽度模式：保持原有行为，宽度始终由变量决定
        max-w-full 保证面板宽度不会超出视口容器宽度
      */}
      <div
        style={{ '--panel-width': `${width}px` } as React.CSSProperties}
        className={`h-full min-w-0 max-w-full shrink-0 ${
          mobileFullWidth ? 'w-full md:w-[var(--panel-width)]' : 'w-[var(--panel-width)]'
        }`}
      >
        {children}
      </div>
      {/* 拖拽手柄：整行堆叠模式下窄屏无法横向拖拽，隐藏处理 */}
      <div
        onMouseDown={startResize}
        className={`${
          mobileFullWidth ? 'hidden md:flex' : 'flex'
        } w-1 hover:bg-accent-cyan cursor-col-resize transition-colors items-center justify-center group`}
      >
        <div className="h-full w-0.5 bg-border-strong group-hover:bg-accent-cyan transition-colors" />
      </div>
    </div>
  );
}
