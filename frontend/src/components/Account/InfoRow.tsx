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
    <div className="flex items-center justify-between py-3 border-b border-slate-700/50 last:border-0">
      <span className="text-slate-400 text-sm">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-white font-medium text-sm">{value}</span>
        {copyable && (
          <button
            onClick={onCopy}
            className="text-slate-500 hover:text-cyan-400 transition-colors"
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
