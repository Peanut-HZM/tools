import React, { useEffect, useState } from 'react';
import { CreateSSHRequest, SSHConfig, UpdateSSHRequest, testSSHConnection } from '../../../api/sshToolApi';
import { useI18n } from '../../../i18n';

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
        group_name: formData.group_name || undefined
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
      <div className="bg-surface-1 rounded-lg shadow-md w-full max-w-lg p-6 border border-border">
        <h2 className="text-xl font-bold mb-4 text-ink-inverse">
          {initialData ? t.ssh.editConnection : t.ssh.addConnection}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.alias}</label>
            <input
              type="text"
              required
              className="w-full bg-canvas border border-border rounded-md px-3 py-2 text-sm text-ink-inverse focus:outline-none focus:border-blue-500"
              value={formData.alias}
              onChange={e => setFormData({ ...formData, alias: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.host}</label>
              <input
                type="text"
                required
                className="w-full bg-canvas border border-border rounded-md px-3 py-2 text-sm text-ink-inverse focus:outline-none focus:border-blue-500"
                value={formData.host}
                onChange={e => setFormData({ ...formData, host: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.port}</label>
              <input
                type="number"
                required
                min="1"
                max="65535"
                className="w-full bg-canvas border border-border rounded-md px-3 py-2 text-sm text-ink-inverse focus:outline-none focus:border-blue-500"
                value={formData.port}
                onChange={e => setFormData({ ...formData, port: parseInt(e.target.value, 10) || 22 })}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.username}</label>
              <input
                type="text"
                required
                className="w-full bg-canvas border border-border rounded-md px-3 py-2 text-sm text-ink-inverse focus:outline-none focus:border-blue-500"
                value={formData.username}
                onChange={e => setFormData({ ...formData, username: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.password}</label>
              <input
                type="password"
                className="w-full bg-canvas border border-border rounded-md px-3 py-2 text-sm text-ink-inverse focus:outline-none focus:border-blue-500"
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
              className="w-full bg-canvas border border-border rounded-md px-3 py-2 text-sm text-ink-inverse focus:outline-none focus:border-blue-500"
              value={formData.private_key}
              onChange={e => setFormData({ ...formData, private_key: e.target.value })}
              placeholder={initialData ? t.common.leaveBlankToKeep : ''}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.passphrase}</label>
              <input
                type="password"
                className="w-full bg-canvas border border-border rounded-md px-3 py-2 text-sm text-ink-inverse focus:outline-none focus:border-blue-500"
                value={formData.passphrase}
                onChange={e => setFormData({ ...formData, passphrase: e.target.value })}
                placeholder={initialData ? t.common.leaveBlankToKeep : ''}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.ssh.group}</label>
              <input
                type="text"
                className="w-full bg-canvas border border-border rounded-md px-3 py-2 text-sm text-ink-inverse focus:outline-none focus:border-blue-500"
                value={formData.group_name}
                onChange={e => setFormData({ ...formData, group_name: e.target.value })}
              />
            </div>
          </div>
          <div className="flex items-center justify-between pt-4">
            <div className="text-sm">
              {testMessage && (
                <span className={testStatus === 'success' ? 'text-green-400' : 'text-danger'}>
                  {testMessage}
                </span>
              )}
            </div>
            <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-surface-2 border border-border rounded-md text-sm font-medium text-ink-muted hover:bg-surface-3 transition-colors"
            >
              {t.common.cancel}
            </button>
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={isTesting}
              className="px-4 py-2 bg-surface-2 border border-border rounded-md text-sm font-medium text-ink hover:bg-surface-3 transition-colors disabled:opacity-60"
            >
              {isTesting ? t.ssh.testing : t.ssh.testConnection}
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-accent border border-transparent rounded-md text-sm font-medium text-white hover:bg-blue-700 transition-colors"
            >
              {t.common.save}
            </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
