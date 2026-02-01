import React, { useState, useEffect } from 'react';
import { ConnectionList } from './ConnectionList';
import { KeyExplorer } from './KeyExplorer';
import { ConnectionModal } from './ConnectionModal';
import { RedisConfig, getRedisConfigs, createRedisConfig, updateRedisConfig, deleteRedisConfig, CreateRedisRequest } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n, interpolate } from '../../../i18n';

const RedisTool: React.FC = () => {
  const { addToast } = useToast();
  const { t } = useI18n();
  const [configs, setConfigs] = useState<RedisConfig[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<string | null>(null);
  const [showConnectionModal, setShowConnectionModal] = useState(false);
  const [editingConfig, setEditingConfig] = useState<RedisConfig | undefined>(undefined);

  const loadConfigs = async () => {
    try {
      const data = await getRedisConfigs();
      setConfigs(data);
    } catch (error) {
      addToast(t.common.error, 'error');
    }
  };

  useEffect(() => {
    loadConfigs();
  }, []);

  const handleAddConfig = () => {
    setEditingConfig(undefined);
    setShowConnectionModal(true);
  };

  const handleEditConfig = (config: RedisConfig) => {
    setEditingConfig(config);
    setShowConnectionModal(true);
  };

  const handleSaveConfig = async (data: CreateRedisRequest) => {
    try {
      if (editingConfig) {
        await updateRedisConfig(editingConfig.id, data);
        addToast(t.redis.saveSuccess, 'success');
      } else {
        await createRedisConfig(data);
        addToast(t.redis.saveSuccess, 'success');
      }
      loadConfigs();
    } catch (error) {
      addToast(t.common.error, 'error');
    }
  };

  const handleDeleteConfig = async (id: string) => {
    try {
      await deleteRedisConfig(id);
      addToast(t.redis.deleteSuccess, 'success');
      if (selectedConfigId === id) setSelectedConfigId(null);
      loadConfigs();
    } catch (error) {
      addToast(t.common.error, 'error');
    }
  };

  return (
    <div className="flex h-[calc(100vh-64px)] bg-slate-900 overflow-hidden">
      <ConnectionList
        configs={configs}
        selectedId={selectedConfigId}
        onSelect={setSelectedConfigId}
        onAdd={handleAddConfig}
        onEdit={handleEditConfig}
        onDelete={handleDeleteConfig}
      />
      <div className="flex-1 overflow-hidden bg-slate-900">
        {selectedConfigId ? (
          <KeyExplorer configId={selectedConfigId} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <i className="fas fa-server text-6xl mb-4 opacity-20"></i>
            <p className="text-lg">{t.redis.selectConnection}</p>
          </div>
        )}
      </div>
      <ConnectionModal
        isOpen={showConnectionModal}
        onClose={() => setShowConnectionModal(false)}
        onSave={handleSaveConfig}
        initialData={editingConfig}
      />
    </div>
  );
};

export default RedisTool;
