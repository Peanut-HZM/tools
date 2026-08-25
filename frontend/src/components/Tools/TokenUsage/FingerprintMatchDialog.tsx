import React from 'react';
import { Monitor, X } from 'lucide-react';
import type { FingerprintMatch } from '../../../api/tokenUsageApi';
import { Button } from '@/components/ui/Button';

interface Props {
  match: FingerprintMatch;
  currentDeviceName: string;
  onReuse: () => void;
  onCreateNew: () => void;
  onClose: () => void;
}

export default function FingerprintMatchDialog({
  match,
  currentDeviceName,
  onReuse,
  onCreateNew,
  onClose,
}: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-lg border border-border bg-canvas p-5 shadow-md">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-500/10">
            <Monitor className="h-5 w-5 text-amber-400" />
          </div>
          <div>
            <h3 className="text-base font-medium text-ink-inverse">检测到已存在的设备</h3>
            <p className="text-xs text-ink-muted">系统发现当前设备与已有记录匹配</p>
          </div>
          <button onClick={onClose} className="ml-auto text-ink-muted hover:text-ink-inverse">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mb-4 space-y-2 rounded-md bg-canvas p-3 text-sm">
          <div className="flex justify-between">
            <span className="text-ink-muted">当前设备：</span>
            <span className="text-ink">{currentDeviceName}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">匹配到已有设备：</span>
            <span className="text-ink">{match.matched_device_name}</span>
          </div>
        </div>

        <p className="mb-4 text-sm text-ink-muted">
          这可能是同一台物理设备。请选择如何处理：
        </p>

        <div className="flex gap-2">
          <Button
            onClick={onReuse}
            className="flex-1"
          >
            复用已有设备
          </Button>
          <button
            onClick={onCreateNew}
            className="flex-1 rounded-md border border-border bg-surface-1 px-3 py-2 text-sm text-ink hover:bg-surface-2"
          >
            创建为新设备
          </button>
        </div>
      </div>
    </div>
  );
}