/**
 * PathInput - 路径输入框组件
 * 支持手动输入路径并按 Enter 或点击按钮跳转
 */
import React from 'react';

interface PathInputProps {
  value: string;
  onChange: (path: string) => void;
  onSubmit: () => void;
  loading?: boolean;
}

export default function PathInput({ value, onChange, onSubmit, loading }: PathInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading) {
      onSubmit();
    }
  };

  return (
    <div className="flex-1 flex items-center gap-2">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="输入路径，按 Enter 跳转..."
        className="flex-1 px-2 py-1.5 text-sm bg-surface-2 border border-border rounded text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-accent-cyan/50"
        disabled={loading}
      />
      <button
        onClick={onSubmit}
        disabled={loading}
        className="px-3 py-1.5 text-sm bg-accent text-ink-inverse rounded cursor-pointer hover:bg-accent-hover transition-colors disabled:opacity-50"
      >
        {loading ? '加载中...' : '跳转'}
      </button>
    </div>
  );
}
