import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';

interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  delay?: number;
}

export const Tooltip: React.FC<TooltipProps> = ({ content, children, delay = 300 }) => {
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState({ left: 0, top: 0 });
  const timerRef = useRef<number>();

  const handleMouseEnter = (e: React.MouseEvent) => {
    if (!content) return;

    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setCoords({
      left: rect.left + rect.width / 2,
      top: rect.top
    });

    timerRef.current = window.setTimeout(() => {
      setIsVisible(true);
    }, delay);
  };

  const handleMouseLeave = () => {
    clearTimeout(timerRef.current);
    setIsVisible(false);
  };

  useEffect(() => {
    return () => clearTimeout(timerRef.current);
  }, []);

  return (
    <>
      {React.cloneElement(children, {
        onMouseEnter: (e: React.MouseEvent) => {
            handleMouseEnter(e);
            children.props.onMouseEnter?.(e);
        },
        onMouseLeave: (e: React.MouseEvent) => {
            handleMouseLeave();
            children.props.onMouseLeave?.(e);
        }
      })}
      {isVisible && content && createPortal(
        <div
            className="fixed z-[9999] px-3 py-2 text-xs font-medium text-ink bg-surface-1 border border-border rounded-md shadow-md pointer-events-none transform -translate-x-1/2 -translate-y-full -mt-2 max-w-sm break-words whitespace-normal"
            style={{ left: coords.left, top: coords.top }}
        >
          {content}
          {/* Arrow */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-full w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-border"></div>
          <div className="absolute bottom-[1px] left-1/2 -translate-x-1/2 translate-y-full w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-surface-1"></div>
        </div>,
        document.body
      )}
    </>
  );
};
