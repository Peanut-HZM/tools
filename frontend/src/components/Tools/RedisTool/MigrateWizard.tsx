import React, { useState } from 'react';
import { migrateData } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

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
          <div className="text-xs text-ink-muted">目标连接 ID</div>
          <Input
            value={targetConfigId}
            onChange={e => setTargetConfigId(e.target.value)}
            placeholder="输入目标 Redis 配置 ID"
            className="w-full"
          />
          <Button size="sm" onClick={() => setStep(2)}>下一步</Button>
        </div>
      )}
      {step === 2 && (
        <div className="space-y-2">
          <div className="text-xs text-ink-muted">Key 匹配模式</div>
          <Input value={pattern} onChange={e => setPattern(e.target.value)} className="w-full" />
          <div className="flex items-center space-x-2">
            <input type="checkbox" checked={replace} onChange={e => setReplace(e.target.checked)} className="w-4 h-4" />
            <span className="text-xs text-ink-muted">覆盖已存在的 key</span>
          </div>
          <div className="flex space-x-2">
            <Button size="sm" variant="secondary" onClick={() => setStep(1)}>上一步</Button>
            <Button size="sm" onClick={() => setStep(3)}>下一步</Button>
          </div>
        </div>
      )}
      {step === 3 && (
        <div className="space-y-2">
          <div className="text-sm text-ink-muted">确认迁移配置：</div>
          <div className="text-xs text-ink-muted">源连接: {configId}</div>
          <div className="text-xs text-ink-muted">目标连接: {targetConfigId}</div>
          <div className="text-xs text-ink-muted">Pattern: {pattern}</div>
          <div className="text-xs text-ink-muted">Replace: {replace ? 'Yes' : 'No'}</div>
          <div className="flex space-x-2">
            <Button size="sm" variant="secondary" onClick={() => setStep(2)}>上一步</Button>
            <Button size="sm" onClick={handleMigrate} disabled={migrating}>
              {migrating ? '迁移中...' : '执行迁移'}
            </Button>
          </div>
        </div>
      )}
      {step === 4 && result && (
        <div className="space-y-2">
          <div className="text-sm text-success">迁移完成</div>
          <div className="text-xs text-ink-muted">成功: {result.migrated_count}</div>
          <div className="text-xs text-ink-muted">失败: {result.failed_count}</div>
          {result.errors?.length > 0 && (
            <div className="text-xs text-danger">错误: {result.errors.slice(0, 5).join(', ')}</div>
          )}
          <Button size="sm" variant="secondary" onClick={onClose}>关闭</Button>
        </div>
      )}
    </div>
  );
};
