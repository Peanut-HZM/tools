import React, { useState, useEffect } from 'react';
import { getRedisConfig, updateRedisServerConfig, getReplicationInfo, flushDB, getBigKeys } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';
import { MigrateWizard } from './MigrateWizard';
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

interface Props {
  configId: string;
}

export const OperationsPanel: React.FC<Props> = ({ configId }) => {
  const { addToast } = useToast();
  const [configs, setConfigs] = useState<any[]>([]);
  const [replication, setReplication] = useState<any>(null);
  const [bigKeys, setBigKeys] = useState<any[]>([]);
  const [showMigrate, setShowMigrate] = useState(false);
  const [filter, setFilter] = useState('');

  const load = async () => {
    try {
      const [c, r, b] = await Promise.all([
        getRedisConfig(configId),
        getReplicationInfo(configId),
        getBigKeys(configId, 50)
      ]);
      setConfigs(c);
      setReplication(r);
      setBigKeys(b.keys || []);
    } catch (e) {
      addToast('Failed to load operations data', 'error');
    }
  };

  useEffect(() => { load(); }, [configId]);

  const handleConfigUpdate = async (key: string, value: string) => {
    try {
      await updateRedisServerConfig(configId, key, value);
      addToast('Config updated', 'success');
      load();
    } catch (e) {
      addToast('Failed to update config', 'error');
    }
  };

  const handleFlush = async (mode: string) => {
    const msg = mode === 'all' ? '确定要清空所有数据库吗？此操作不可撤销！' : '确定要清空当前数据库吗？此操作不可撤销！';
    if (!confirm(msg)) return;
    try {
      const result = await flushDB(configId, mode);
      addToast(result.message, 'success');
    } catch (e) {
      addToast('Flush failed', 'error');
    }
  };

  const filteredConfigs = configs.filter(c => c.key.toLowerCase().includes(filter.toLowerCase()));

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      <Card className="bg-danger/20 border-danger p-4">
        <div className="text-sm font-medium text-danger mb-3">危险操作</div>
        <div className="flex space-x-2">
          <Button size="sm" variant="destructive" onClick={() => handleFlush('db')}>FLUSHDB</Button>
          <Button size="sm" variant="destructive" onClick={() => handleFlush('all')}>FLUSHALL</Button>
        </div>
      </Card>

      <Card className="p-4">
        <div className="flex justify-between items-center mb-3">
          <div className="text-sm font-medium text-ink-muted">数据迁移</div>
          <Button size="sm" onClick={() => setShowMigrate(!showMigrate)}>
            {showMigrate ? '关闭' : '开始迁移'}
          </Button>
        </div>
        {showMigrate && <MigrateWizard configId={configId} onClose={() => setShowMigrate(false)} />}
      </Card>

      {replication && (
        <Card className="p-4">
          <div className="text-sm font-medium text-ink-muted mb-3">复制信息</div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="text-ink-muted">Role:</div><div className="text-ink">{replication.role}</div>
            <div className="text-ink-muted">Connected Slaves:</div><div className="text-ink">{replication.connected_slaves}</div>
            {replication.master_replid && <><div className="text-ink-muted">Repl ID:</div><div className="text-ink font-mono text-xs">{replication.master_replid}</div></>}
          </div>
        </Card>
      )}

      <Card className="overflow-hidden">
        <CardHeader className="px-4 py-3 border-b border-border flex flex-row justify-between items-center">
          <CardTitle className="text-sm font-medium text-ink-muted">配置参数</CardTitle>
          <Input
            value={filter}
            onChange={e => setFilter(e.target.value)}
            placeholder="搜索配置项..."
            className="w-48 h-8 text-xs"
          />
        </CardHeader>
        <CardContent className="max-h-96 overflow-y-auto p-0">
          <table className="w-full text-sm">
            <thead className="bg-canvas text-ink-muted sticky top-0">
              <tr><th className="px-4 py-2 text-left">Key</th><th className="px-4 py-2 text-left">Value</th></tr>
            </thead>
            <tbody>
              {filteredConfigs.map((c) => (
                <tr key={c.key} className="border-t border-border hover:bg-surface-1/50">
                  <td className="px-4 py-2 font-mono text-xs text-ink-muted">{c.key}</td>
                  <td className="px-4 py-2">
                    {c.editable ? (
                      <Input
                        defaultValue={c.value}
                        onBlur={e => handleConfigUpdate(c.key, e.target.value)}
                        className="w-full h-8 text-xs"
                      />
                    ) : (
                      <span className="text-ink-muted">{c.value}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader className="px-4 py-3 border-b border-border">
          <CardTitle className="text-sm font-medium text-ink-muted">大 Key Top 50</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="bg-canvas text-ink-muted">
              <tr><th className="px-4 py-2 text-left">Key</th><th className="px-4 py-2 text-left">Type</th><th className="px-4 py-2 text-right">Memory</th></tr>
            </thead>
            <tbody>
              {bigKeys.map((k) => (
                <tr key={k.key} className="border-t border-border hover:bg-surface-1/50">
                  <td className="px-4 py-2 font-mono text-xs text-ink-muted">{k.key}</td>
                  <td className="px-4 py-2"><Badge variant="secondary" className="text-[10px]">{k.type}</Badge></td>
                  <td className="px-4 py-2 text-right text-ink-muted">{(k.memory_usage / 1024).toFixed(2)} KB</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
};