import React, { useEffect, useState } from 'react';
import { CreateSSHRequest, SSHConfig, UpdateSSHRequest, testSSHConnection } from '../../../api/sshToolApi';
import { useI18n } from '../../../i18n';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import StorageLocationSelector from '../../Common/StorageLocationSelector';
import { getStorageStatus } from '../../../api/storageApi';
import type { StorageLocation } from '../../../types/storage';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: CreateSSHRequest | UpdateSSHRequest) => Promise<void>;
  initialData?: SSHConfig;
}

export const ConnectionModal: React.FC<Props> = ({ isOpen, onClose, onSave, initialData }) => {
  const { t } = useI18n();
  const [formData, setFormData] = useState<CreateSSHRequest>({
    alias: '',
    host: 'localhost',
    port: 22,
    username: '',
    password: '',
    private_key: '',
    passphrase: '',
    group_name: ''
  });
  const [isTesting, setIsTesting] = useState(false);
  const [testMessage, setTestMessage] = useState('');
  const [testStatus, setTestStatus] = useState<'idle' | 'success' | 'error'>('idle');
  // 存储位置：新建默认本机；编辑时回填原位置
  const [storageLocation, setStorageLocation] = useState<StorageLocation>('local');
  const [originalLocation, setOriginalLocation] = useState<StorageLocation | null>(null);
  // 远程服务器是否可用（探测失败时按不可用处理，不提供上传选项）
  const [serverAvailable, setServerAvailable] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    // 探测远程服务器是否可用：决定是否展示「上传到服务器」选项
    let cancelled = false;
    getStorageStatus()
      .then((status) => {
        if (!cancelled) setServerAvailable(status.server_available);
      })
      .catch(() => {
        if (!cancelled) setServerAvailable(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  useEffect(() => {
    if (initialData) {
      setFormData({
        alias: initialData.alias,
        host: initialData.host,
        port: initialData.port,
        username: initialData.username,
        password: '',
        private_key: '',
        passphrase: '',
        group_name: initialData.group_name || ''
      });
      // 回填原存储位置（旧数据缺省按本机处理）；未改动时提交不带该字段，避免静默迁移
      const loc = (initialData.storage_location ?? 'local') as StorageLocation;
      setStorageLocation(loc);
      setOriginalLocation(loc);
    } else {
      setFormData({
        alias: '',
        host: 'localhost',
        port: 22,
        username: '',
        password: '',
        private_key: '',
        passphrase: '',
        group_name: ''
      });
      // 新建：默认本机
      setStorageLocation('local');
      setOriginalLocation(null);
    }
    setIsTesting(false);
    setTestMessage('');
    setTestStatus('idle');
  }, [initialData, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (initialData) {
      const payload: UpdateSSHRequest = {
        id: initialData.id,
        alias: formData.alias,
        host: formData.host,
        port: formData.port,
        username: formData.username,
        group_name: formData.group_name
      };
      if (formData.password) payload.password = formData.password;
      if (formData.private_key) payload.private_key = formData.private_key;
      if (formData.passphrase) payload.passphrase = formData.passphrase;
      // 编辑保存：仅当用户显式改动了存储位置才传该字段，绝不静默改变存储位置
      if (originalLocation !== null && storageLocation !== originalLocation) {
        payload.storage_location = storageLocation;
      }
      await onSave(payload);
    } else {
      await onSave({
        alias: formData.alias,
        host: formData.host,
        port: formData.port,
        username: formData.username,
        password: formData.password || undefined,
        private_key: formData.private_key || undefined,
        passphrase: formData.passphrase || undefined,
        group_name: formData.group_name || undefined,
        storage_location: storageLocation
      });
    }
    onClose();
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestMessage('');
    setTestStatus('idle');
    try {
      const response = await testSSHConnection({
        host: formData.host,
        port: formData.port,
        username: formData.username,
        password: formData.password || undefined,
        private_key: formData.private_key || undefined,
        passphrase: formData.passphrase || undefined
      });
      setTestStatus('success');
      setTestMessage(response.message || t.ssh.testSuccess);
    } catch (e) {
      setTestStatus('error');
      setTestMessage(e instanceof Error ? e.message : t.ssh.testFailed);
    } finally {
      setIsTesting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <Card className="w-full max-w-lg shadow-md">
        <CardHeader>
          <CardTitle className="text-xl">
            {initialData ? t.ssh.editConnection : t.ssh.addConnection}
          </CardTitle>
        </CardHeader>
        <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.alias}</label>
            <Input
              required
              value={formData.alias}
              onChange={e => setFormData({ ...formData, alias: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.host}</label>
              <Input
                required
                value={formData.host}
                onChange={e => setFormData({ ...formData, host: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.port}</label>
              <Input
                type="number"
                required
                min="1"
                max="65535"
                value={formData.port}
                onChange={e => setFormData({ ...formData, port: parseInt(e.target.value, 10) || 22 })}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.username}</label>
              <Input
                required
                value={formData.username}
                onChange={e => setFormData({ ...formData, username: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.password}</label>
              <Input
                type="password"
                value={formData.password}
                onChange={e => setFormData({ ...formData, password: e.target.value })}
                placeholder={initialData ? t.common.leaveBlankToKeep : ''}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.privateKey}</label>
            <textarea
              rows={4}
              className="w-full bg-canvas border border-border rounded-md px-3 py-2 text-sm text-ink focus:outline-none focus:border-accent-info"
              value={formData.private_key}
              onChange={e => setFormData({ ...formData, private_key: e.target.value })}
              placeholder={initialData ? t.common.leaveBlankToKeep : ''}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.passphrase}</label>
              <Input
                type="password"
                value={formData.passphrase}
                onChange={e => setFormData({ ...formData, passphrase: e.target.value })}
                placeholder={initialData ? t.common.leaveBlankToKeep : ''}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.group}</label>
              <Input
                value={formData.group_name}
                onChange={e => setFormData({ ...formData, group_name: e.target.value })}
              />
            </div>
          </div>
          <StorageLocationSelector
            value={storageLocation}
            onChange={setStorageLocation}
            serverAvailable={serverAvailable}
          />
          <div className="flex items-center justify-between pt-4">
            <div className="text-sm">
              {testMessage && (
                <Badge variant={testStatus === 'success' ? 'success' : 'destructive'}>
                  {testMessage}
                </Badge>
              )}
            </div>
            <div className="flex items-center space-x-3">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
            >
              {t.common.cancel}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={handleTestConnection}
              disabled={isTesting}
            >
              {isTesting ? t.ssh.testing : t.ssh.testConnection}
            </Button>
            <Button
              type="submit"
              variant="default"
            >
              {t.common.save}
            </Button>
            </div>
          </div>
        </form>
        </CardContent>
      </Card>
    </div>
  );
};
