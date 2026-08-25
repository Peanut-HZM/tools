import React, { useState } from 'react';
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface Props {
  selectedCount: number;
  configId: string;
  selectedKeys: string[];
  onBatchDelete: (keys: string[]) => void;
  onBatchTTL: (keys: string[], ttl: number) => void;
  onBatchRename: (keys: string[], pattern: string, replacement: string) => void;
  onClear: () => void;
}

export const BatchToolbar: React.FC<Props> = ({
  selectedCount,
  selectedKeys,
  onBatchDelete,
  onBatchTTL,
  onBatchRename,
  onClear,
}) => {
  const [showTTLModal, setShowTTLModal] = useState(false);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [ttl, setTtl] = useState(3600);
  const [pattern, setPattern] = useState('*');
  const [replacement, setReplacement] = useState('');

  const handleDelete = () => {
    if (!confirm(`确定删除选中的 ${selectedCount} 个 key？`)) return;
    onBatchDelete(selectedKeys);
  };

  const handleTTL = () => {
    onBatchTTL(selectedKeys, ttl);
    setShowTTLModal(false);
  };

  const handleRename = () => {
    onBatchRename(selectedKeys, pattern, replacement);
    setShowRenameModal(false);
  };

  if (selectedCount === 0) {
    return (
      <div className="p-2 text-xs text-ink-faint flex justify-between items-center">
        <span>批量模式：点击选择 key</span>
        <button onClick={onClear} className="text-ink-muted hover:text-ink-inverse">取消</button>
      </div>
    );
  }

  return (
    <div className="p-2 bg-surface-1/80 border-b border-border space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-ink-muted">已选择 {selectedCount} 个 key</span>
        <div className="flex space-x-1">
          <Button size="sm" onClick={() => setShowTTLModal(true)}>修改 TTL</Button>
          <Button size="sm" onClick={() => setShowRenameModal(true)}>重命名</Button>
          <Button size="sm" variant="destructive" onClick={handleDelete}>删除</Button>
          <Button size="sm" variant="secondary" onClick={onClear}>清空</Button>
        </div>
      </div>

      {showTTLModal && (
        <div className="flex items-center space-x-2">
          <Input
            type="number"
            value={ttl}
            onChange={(e) => setTtl(parseInt(e.target.value))}
            className="w-24"
            placeholder="TTL (秒)"
          />
          <Button size="sm" onClick={handleTTL}>确认</Button>
          <Button size="sm" variant="secondary" onClick={() => setShowTTLModal(false)}>取消</Button>
        </div>
      )}

      {showRenameModal && (
        <div className="flex items-center space-x-2">
          <Input
            type="text"
            value={pattern}
            onChange={(e) => setPattern(e.target.value)}
            className="w-32"
            placeholder="匹配模式"
          />
          <span className="text-ink-muted">→</span>
          <Input
            type="text"
            value={replacement}
            onChange={(e) => setReplacement(e.target.value)}
            className="w-32"
            placeholder="替换为"
          />
          <Button size="sm" onClick={handleRename}>确认</Button>
          <Button size="sm" variant="secondary" onClick={() => setShowRenameModal(false)}>取消</Button>
        </div>
      )}
    </div>
  );
};
