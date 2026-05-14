import React, { useState } from 'react';

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
      <div className="p-2 text-xs text-slate-500 flex justify-between items-center">
        <span>批量模式：点击选择 key</span>
        <button onClick={onClear} className="text-slate-400 hover:text-white">取消</button>
      </div>
    );
  }

  return (
    <div className="p-2 bg-slate-800/80 border-b border-slate-700 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-300">已选择 {selectedCount} 个 key</span>
        <div className="flex space-x-1">
          <button onClick={() => setShowTTLModal(true)} className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700">修改 TTL</button>
          <button onClick={() => setShowRenameModal(true)} className="px-2 py-1 text-xs bg-purple-600 text-white rounded hover:bg-purple-700">重命名</button>
          <button onClick={handleDelete} className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700">删除</button>
          <button onClick={onClear} className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded hover:bg-slate-600">清空</button>
        </div>
      </div>

      {showTTLModal && (
        <div className="flex items-center space-x-2">
          <input
            type="number"
            value={ttl}
            onChange={(e) => setTtl(parseInt(e.target.value))}
            className="w-24 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
            placeholder="TTL (秒)"
          />
          <button onClick={handleTTL} className="px-2 py-1 text-xs bg-green-600 text-white rounded">确认</button>
          <button onClick={() => setShowTTLModal(false)} className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded">取消</button>
        </div>
      )}

      {showRenameModal && (
        <div className="flex items-center space-x-2">
          <input
            type="text"
            value={pattern}
            onChange={(e) => setPattern(e.target.value)}
            className="w-32 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
            placeholder="匹配模式"
          />
          <span className="text-slate-400">→</span>
          <input
            type="text"
            value={replacement}
            onChange={(e) => setReplacement(e.target.value)}
            className="w-32 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
            placeholder="替换为"
          />
          <button onClick={handleRename} className="px-2 py-1 text-xs bg-green-600 text-white rounded">确认</button>
          <button onClick={() => setShowRenameModal(false)} className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded">取消</button>
        </div>
      )}
    </div>
  );
};
