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
}

export default function ResizablePanel({
  children,
  defaultWidth = 280,
  minWidth = 200,
  maxWidth = 500,
  storageKey,
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
    <div className="flex h-full">
      <div style={{ width, flexShrink: 0 }} className="h-full">
        {children}
      </div>
      <div
        onMouseDown={startResize}
        className="w-1 hover:bg-blue-500 cursor-col-resize transition-colors flex items-center justify-center group"
      >
        <div className="h-full w-0.5 bg-gray-700 group-hover:bg-blue-500 transition-colors" />
      </div>
    </div>
  );
}
