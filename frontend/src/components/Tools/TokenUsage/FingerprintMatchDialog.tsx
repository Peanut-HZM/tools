import React from 'react';
import { Monitor, X } from 'lucide-react';
import type { FingerprintMatch } from '../../../api/tokenUsageApi';

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
      <div className="w-full max-w-md rounded-lg border border-slate-700 bg-slate-900 p-5 shadow-xl">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-500/10">
            <Monitor className="h-5 w-5 text-amber-400" />
          </div>
          <div>
            <h3 className="text-base font-medium text-white">检测到已存在的设备</h3>
            <p className="text-xs text-slate-400">系统发现当前设备与已有记录匹配</p>
          </div>
          <button onClick={onClose} className="ml-auto text-slate-400 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mb-4 space-y-2 rounded-md bg-slate-950 p-3 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">当前设备：</span>
            <span className="text-slate-200">{currentDeviceName}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">匹配到已有设备：</span>
            <span className="text-slate-200">{match.matched_device_name}</span>
          </div>
        </div>

        <p className="mb-4 text-sm text-slate-300">
          这可能是同一台物理设备。请选择如何处理：
        </p>

        <div className="flex gap-2">
          <button
            onClick={onReuse}
            className="flex-1 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-500"
          >
            复用已有设备
          </button>
          <button
            onClick={onCreateNew}
            className="flex-1 rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700"
          >
            创建为新设备
          </button>
        </div>
      </div>
    </div>
  );
}
