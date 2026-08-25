import React, { useMemo, useState } from 'react';
import { X, Monitor, Merge, Undo2, Edit3, AlertCircle } from 'lucide-react';
import type { DeviceInfo } from '../../../api/tokenUsageApi';
import { Button } from '@/components/ui/Button';

interface Props {
  devices: DeviceInfo[];
  open: boolean;
  onClose: () => void;
  onRename: (deviceId: string, name: string) => Promise<void>;
  onMerge: (sourceIds: string[], targetId: string) => Promise<void>;
  onUnmerge: (aliasDeviceId: string) => Promise<void>;
}

export default function DeviceManagerModal({
  devices,
  open,
  onClose,
  onRename,
  onMerge,
  onUnmerge,
}: Props) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [mergeTarget, setMergeTarget] = useState<string>('');
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleSelection = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  const handleRename = async (device: DeviceInfo) => {
    const nextName = window.prompt('请输入设备名称。留空会恢复默认名称。', device.name);
    if (nextName === null) return;
    setProcessing(true);
    setError(null);
    try {
      await onRename(device.id, nextName);
    } catch (e: any) {
      setError(e.message || '重命名失败');
    } finally {
      setProcessing(false);
    }
  };

  const handleMerge = async () => {
    if (selectedIds.size < 2 || !mergeTarget) return;
    const sourceIds = Array.from(selectedIds).filter(id => id !== mergeTarget);
    if (sourceIds.length === 0) {
      setError('源设备不能仅包含目标设备');
      return;
    }
    setProcessing(true);
    setError(null);
    try {
      await onMerge(sourceIds, mergeTarget);
      setSelectedIds(new Set());
      setMergeTarget('');
    } catch (e: any) {
      setError(e.message || '合并失败');
    } finally {
      setProcessing(false);
    }
  };

  const handleMergeSameName = async () => {
    const nameGroups: Record<string, DeviceInfo[]> = {};
    for (const d of devices) {
      const key = d.name || d.id;
      nameGroups[key] = nameGroups[key] || [];
      nameGroups[key].push(d);
    }
    const duplicates = Object.entries(nameGroups).filter(([, items]) => items.length > 1);
    if (duplicates.length === 0) {
      setError('没有同名设备可合并');
      return;
    }

    // 合并每组同名设备，以第一个为目标
    setProcessing(true);
    setError(null);
    try {
      for (const [, items] of duplicates) {
        const target = items[0];
        const sources = items.slice(1).map(d => d.id);
        if (sources.length > 0) {
          await onMerge(sources, target.id);
        }
      }
      setSelectedIds(new Set());
      setMergeTarget('');
    } catch (e: any) {
      setError(e.message || '合并同名设备失败');
    } finally {
      setProcessing(false);
    }
  };

  const mergedDevices = useMemo(() => devices.filter(d => d.canonical_id), [devices]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="flex max-h-[80vh] w-full max-w-2xl flex-col rounded-lg border border-border bg-canvas shadow-md">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <h3 className="text-base font-medium text-ink-inverse">设备管理</h3>
            <p className="text-xs text-ink-muted">{devices.length} 个设备 · {mergedDevices.length} 个已合并</p>
          </div>
          <button onClick={onClose} className="text-ink-muted hover:text-ink-inverse">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4">
          {error && (
            <div className="mb-3 rounded-md border border-red-500/30 bg-danger/10 px-3 py-2 text-sm text-red-200">
              <AlertCircle className="mr-1 inline h-4 w-4" />
              {error}
            </div>
          )}

          <div className="mb-3 flex gap-2">
            <button
              onClick={handleMergeSameName}
              disabled={processing}
              className="rounded-md border border-border bg-surface-1 px-3 py-1.5 text-xs text-ink hover:bg-surface-2 disabled:opacity-50"
            >
              <Merge className="mr-1 inline h-3.5 w-3.5" />
              一键合并同名设备
            </button>
            {selectedIds.size >= 2 && (
              <>
                <select
                  value={mergeTarget}
                  onChange={e => setMergeTarget(e.target.value)}
                  className="rounded-md border border-border bg-surface-1 px-2 py-1.5 text-xs text-ink"
                >
                  <option value="">选择合并目标...</option>
                  {Array.from(selectedIds).map(id => {
                    const d = devices.find(dev => dev.id === id);
                    return (
                      <option key={id} value={id}>
                        {d?.name || id}
                      </option>
                    );
                  })}
                </select>
                <Button
                  onClick={handleMerge}
                  disabled={!mergeTarget || processing}
                  size="sm"
                  className="text-xs"
                >
                  合并
                </Button>
              </>
            )}
          </div>

          <div className="space-y-2">
            {devices.map(device => (
              <div
                key={device.id}
                className={`flex items-center gap-3 rounded-md border px-3 py-2.5 text-sm ${
                  selectedIds.has(device.id)
                    ? 'border-blue-500/50 bg-accent-info/10'
                    : 'border-border bg-canvas'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedIds.has(device.id)}
                  onChange={() => toggleSelection(device.id)}
                  className="h-4 w-4 accent-blue-600"
                />
                <Monitor className="h-4 w-4 text-ink-muted" />
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium text-ink">{device.name}</div>
                  <div className="text-xs text-ink-faint">
                    {device.id_type === 'hardware' ? '硬件指纹' : 'UUID'} · {device.id.slice(0, 8)}...
                    {device.canonical_id && (
                      <span className="ml-1 text-accent-info">→ {devices.find(d => d.id === device.canonical_id)?.name || device.canonical_id.slice(0, 8)}</span>
                    )}
                  </div>
                </div>
                {device.canonical_id ? (
                  <button
                    onClick={() => onUnmerge(device.id)}
                    disabled={processing}
                    title="撤销合并"
                    className="rounded-md border border-border p-1.5 text-ink-muted hover:bg-surface-1 hover:text-ink-inverse disabled:opacity-50"
                  >
                    <Undo2 className="h-3.5 w-3.5" />
                  </button>
                ) : (
                  <button
                    onClick={() => handleRename(device)}
                    disabled={processing}
                    title="重命名"
                    className="rounded-md border border-border p-1.5 text-ink-muted hover:bg-surface-1 hover:text-ink-inverse disabled:opacity-50"
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
