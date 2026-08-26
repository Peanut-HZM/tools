import React, { useState, useEffect } from 'react';
import { ConnectionList } from './ConnectionList';
import { KeyExplorer } from './KeyExplorer';
import { MonitorPanel } from './MonitorPanel';
import { OperationsPanel } from './OperationsPanel';
import { ConnectionModal } from './ConnectionModal';
import { RedisConfig, getRedisConfigs, createRedisConfig, updateRedisConfig, deleteRedisConfig, CreateRedisRequest } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n, interpolate } from '../../../i18n';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';

const RedisTool: React.FC = () => {
  const { addToast } = useToast();
  const { t } = useI18n();
  const [configs, setConfigs] = useState<RedisConfig[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<string | null>(null);
  const [showConnectionModal, setShowConnectionModal] = useState(false);
  const [editingConfig, setEditingConfig] = useState<RedisConfig | undefined>(undefined);
  const [activeTab, setActiveTab] = useState<'keys' | 'monitor' | 'ops'>('keys');

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
    <div className="flex h-[calc(100vh-64px)] bg-canvas overflow-hidden">
      <ConnectionList
        configs={configs}
        selectedId={selectedConfigId}
        onSelect={setSelectedConfigId}
        onAdd={handleAddConfig}
        onEdit={handleEditConfig}
        onDelete={handleDeleteConfig}
      />
      <div className="flex-1 overflow-hidden bg-canvas flex flex-col">
        {selectedConfigId ? (
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'keys' | 'monitor' | 'ops')} className="flex-1 flex flex-col overflow-hidden">
            <TabsList className="mx-2 mt-2 bg-surface-2 shrink-0">
              <TabsTrigger value="keys"><i className="fas fa-key mr-1"></i> 键值浏览</TabsTrigger>
              <TabsTrigger value="monitor"><i className="fas fa-chart-line mr-1"></i> 监控</TabsTrigger>
              <TabsTrigger value="ops"><i className="fas fa-tools mr-1"></i> 运维</TabsTrigger>
            </TabsList>
            <TabsContent value="keys" className="flex-1 overflow-hidden">
              <KeyExplorer configId={selectedConfigId} />
            </TabsContent>
            <TabsContent value="monitor" className="flex-1 overflow-hidden">
              <MonitorPanel configId={selectedConfigId} />
            </TabsContent>
            <TabsContent value="ops" className="flex-1 overflow-hidden">
              <OperationsPanel configId={selectedConfigId} />
            </TabsContent>
          </Tabs>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-ink-faint">
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
