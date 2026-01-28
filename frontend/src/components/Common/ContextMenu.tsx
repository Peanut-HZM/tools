import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

export interface MenuItem {
  label: string;
  icon?: string;
  action: () => void;
  disabled?: boolean;
  danger?: boolean;
  separator?: boolean;
}

interface ContextMenuProps {
  x: number;
  y: number;
  items: MenuItem[];
  onClose: () => void;
}

export const ContextMenu: React.FC<ContextMenuProps> = ({ x, y, items, onClose }) => {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [onClose]);

  // Adjust position if menu goes off screen
  const style: React.CSSProperties = {
    top: y,
    left: x,
  };

  return createPortal(
    <div
      ref={menuRef}
      className="fixed z-50 bg-slate-800 border border-slate-700 rounded shadow-lg py-1 min-w-[160px] select-none"
      style={style}
      onContextMenu={(e) => e.preventDefault()} // Prevent native context menu on the menu itself
    >
      {items.map((item, index) => {
        if (item.separator) {
          return <div key={index} className="h-px bg-slate-700 my-1" />;
        }

        return (
          <div
            key={index}
            className={`
              px-4 py-2 text-sm flex items-center gap-2 cursor-pointer transition-colors
              ${item.disabled 
                ? 'text-slate-500 cursor-not-allowed' 
                : item.danger 
                  ? 'text-red-400 hover:bg-red-900/20' 
                  : 'text-slate-300 hover:bg-slate-700 hover:text-white'
              }
            `}
            onClick={() => {
              if (!item.disabled) {
                item.action();
                onClose();
              }
            }}
          >
            {item.icon && <i className={`fas ${item.icon} w-4 text-center ${item.danger ? '' : 'text-slate-400'}`}></i>}
            <span>{item.label}</span>
          </div>
        );
      })}
    </div>,
    document.body
  );
};
