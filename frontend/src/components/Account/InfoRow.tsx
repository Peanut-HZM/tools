import React from 'react';
import { Copy } from 'lucide-react';

interface InfoRowProps {
  label: string;
  value: string | React.ReactNode;
  copyable?: boolean;
  onCopy?: () => void;
}

export default function InfoRow({ label, value, copyable = false, onCopy }: InfoRowProps) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-border/50 last:border-0">
      <span className="text-ink-muted text-sm">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-ink-inverse font-medium text-sm">{value}</span>
        {copyable && (
          <button
            onClick={onCopy}
            className="text-ink-faint hover:text-accent transition-colors"
            title="复制"
            type="button"
          >
            <Copy className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
