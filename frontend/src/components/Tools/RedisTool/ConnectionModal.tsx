import React, { useState, useEffect } from 'react';
import { RedisConfig, CreateRedisRequest, testConnection } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n } from '../../../i18n';
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: CreateRedisRequest) => Promise<void>;
  initialData?: RedisConfig;
}

export const ConnectionModal: React.FC<Props> = ({ isOpen, onClose, onSave, initialData }) => {
  const { addToast } = useToast();
  const { t } = useI18n();
  const [formData, setFormData] = useState<CreateRedisRequest>({
    alias: '',
    host: 'localhost',
    port: 6379,
    username: '',
    password: '',
    db: 0,
    group_name: '',
    is_active: true
  });
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    if (initialData) {
      setFormData({
        alias: initialData.alias,
        host: initialData.host,
        port: initialData.port,
        username: initialData.username || '',
        password: '', // Password not returned
        db: initialData.db,
        group_name: initialData.group_name || '',
        is_active: initialData.is_active
      });
    } else {
      setFormData({
        alias: '',
        host: 'localhost',
        port: 6379,
        username: '',
        password: '',
        db: 0,
        group_name: '',
        is_active: true
      });
    }
  }, [initialData, isOpen]);

  const handleTest = async () => {
    setTesting(true);
    try {
      const result = await testConnection(formData);
      if (result.success) {
        addToast(t.redis.connectionSuccess, 'success');
      } else {
        addToast(`${t.redis.connectionFailed}: ${result.message}`, 'error');
      }
    } catch (error) {
      addToast(t.redis.connectionFailed, 'error');
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSave(formData);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-surface-1 rounded-lg shadow-md w-full max-w-md p-6 border border-border">
        <h2 className="text-xl font-bold mb-4 text-ink">
          {initialData ? t.redis.editConnection : t.redis.addConnection}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-ink-muted mb-1">{t.redis.alias}</label>
            <Input
              type="text"
              required
              className="w-full"
              value={formData.alias}
              onChange={e => setFormData({ ...formData, alias: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.redis.host}</label>
              <Input
                type="text"
                required
                className="w-full"
                value={formData.host}
                onChange={e => setFormData({ ...formData, host: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.redis.port}</label>
              <Input
                type="number"
                required
                className="w-full"
                value={formData.port}
                onChange={e => setFormData({ ...formData, port: parseInt(e.target.value) })}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
             <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.redis.username}</label>
              <Input
                type="text"
                className="w-full"
                value={formData.username}
                onChange={e => setFormData({ ...formData, username: e.target.value })}
              />
            </div>
             <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.redis.password}</label>
              <Input
                type="password"
                className="w-full"
                value={formData.password}
                onChange={e => setFormData({ ...formData, password: e.target.value })}
                placeholder={initialData ? t.common.leaveBlankToKeep : ''}
              />
            </div>
          </div>
           <div>
            <label className="block text-sm font-medium text-ink-muted mb-1">{t.redis.db}</label>
            <Input
              type="number"
              min="0"
              className="w-full"
              value={formData.db}
              onChange={e => setFormData({ ...formData, db: parseInt(e.target.value) })}
            />
          </div>
          <div className="flex justify-between items-center pt-4">
             <Button
              type="button"
              variant="secondary"
              onClick={handleTest}
              disabled={testing}
            >
              {testing ? t.redis.testing : t.redis.testConnection}
            </Button>
            <div className="flex space-x-3">
              <Button
                type="button"
                variant="secondary"
                onClick={onClose}
              >
                {t.common.cancel}
              </Button>
              <Button
                type="submit"
              >
                {t.common.save}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
