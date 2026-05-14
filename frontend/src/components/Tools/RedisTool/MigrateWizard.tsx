import React, { useState } from 'react';
import { migrateData } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';

interface Props {
  configId: string;
  onClose: () => void;
}

export const MigrateWizard: React.FC<Props> = ({ configId, onClose }) => {
  const { addToast } = useToast();
  const [step, setStep] = useState(1);
  const [targetConfigId, setTargetConfigId] = useState('');
  const [pattern, setPattern] = useState('*');
  const [replace, setReplace] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [migrating, setMigrating] = useState(false);

  const handleMigrate = async () => {
    if (!targetConfigId) {
      addToast('请选择目标连接', 'error');
      return;
    }
    setMigrating(true);
    try {
      const res = await migrateData(configId, {
        source_config_id: configId,
        target_config_id: targetConfigId,
        pattern,
        replace
      });
      setResult(res);
      setStep(4);
      addToast(`迁移完成：成功 ${res.migrated_count} 个，失败 ${res.failed_count} 个`, 'success');
    } catch (e) {
      addToast('迁移失败', 'error');
    } finally {
      setMigrating(false);
    }
  };

  return (
    <div className="mt-3 space-y-3">
      {step === 1 && (
        <div className="space-y-2">
          <div className="text-xs text-slate-400">目标连接 ID</div>
          <input
            value={targetConfigId}
            onChange={e => setTargetConfigId(e.target.value)}
            placeholder="输入目标 Redis 配置 ID"
            className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
          />
          <button onClick={() => setStep(2)} className="px-3 py-1 bg-blue-600 text-white text-xs rounded">下一步</button>
        </div>
      )}
      {step === 2 && (
        <div className="space-y-2">
          <div className="text-xs text-slate-400">Key 匹配模式</div>
          <input value={pattern} onChange={e => setPattern(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200" />
          <div className="flex items-center space-x-2">
            <input type="checkbox" checked={replace} onChange={e => setReplace(e.target.checked)} className="w-4 h-4" />
            <span className="text-xs text-slate-400">覆盖已存在的 key</span>
          </div>
          <div className="flex space-x-2">
            <button onClick={() => setStep(1)} className="px-3 py-1 bg-slate-700 text-slate-300 text-xs rounded">上一步</button>
            <button onClick={() => setStep(3)} className="px-3 py-1 bg-blue-600 text-white text-xs rounded">下一步</button>
          </div>
        </div>
      )}
      {step === 3 && (
        <div className="space-y-2">
          <div className="text-sm text-slate-300">确认迁移配置：</div>
          <div className="text-xs text-slate-400">源连接: {configId}</div>
          <div className="text-xs text-slate-400">目标连接: {targetConfigId}</div>
          <div className="text-xs text-slate-400">Pattern: {pattern}</div>
          <div className="text-xs text-slate-400">Replace: {replace ? 'Yes' : 'No'}</div>
          <div className="flex space-x-2">
            <button onClick={() => setStep(2)} className="px-3 py-1 bg-slate-700 text-slate-300 text-xs rounded">上一步</button>
            <button onClick={handleMigrate} disabled={migrating} className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50">
              {migrating ? '迁移中...' : '执行迁移'}
            </button>
          </div>
        </div>
      )}
      {step === 4 && result && (
        <div className="space-y-2">
          <div className="text-sm text-green-400">迁移完成</div>
          <div className="text-xs text-slate-400">成功: {result.migrated_count}</div>
          <div className="text-xs text-slate-400">失败: {result.failed_count}</div>
          {result.errors?.length > 0 && (
            <div className="text-xs text-red-400">错误: {result.errors.slice(0, 5).join(', ')}</div>
          )}
          <button onClick={onClose} className="px-3 py-1 bg-slate-700 text-slate-300 text-xs rounded">关闭</button>
        </div>
      )}
    </div>
  );
};
