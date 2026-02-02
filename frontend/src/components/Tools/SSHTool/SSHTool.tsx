import React, { useEffect, useMemo, useState } from 'react';
import { ConnectionList } from './ConnectionList';
import { ConnectionModal } from './ConnectionModal';
import { TerminalPanel } from './TerminalPanel';
import { CreateSSHRequest, SSHConfig, UpdateSSHRequest, createSSHConfig, deleteSSHConfig, getSSHConfigs, updateSSHConfig } from '../../../api/sshToolApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n } from '../../../i18n';

const SSHTool: React.FC = () => {
  const { addToast } = useToast();
  const { t } = useI18n();
  const [configs, setConfigs] = useState<SSHConfig[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<string | null>(null);
  const [showConnectionModal, setShowConnectionModal] = useState(false);
  const [editingConfig, setEditingConfig] = useState<SSHConfig | undefined>(undefined);

  const selectedConfig = useMemo(() => configs.find(config => config.id === selectedConfigId) || null, [configs, selectedConfigId]);

  const loadConfigs = async () => {
    try {
      const data = await getSSHConfigs();
      setConfigs(data);
      if (selectedConfigId && !data.find(config => config.id === selectedConfigId)) {
        setSelectedConfigId(null);
      }
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

  const handleEditConfig = (config: SSHConfig) => {
    setEditingConfig(config);
    setShowConnectionModal(true);
  };

  const handleSaveConfig = async (data: CreateSSHRequest | UpdateSSHRequest) => {
    try {
      if ('id' in data) {
        await updateSSHConfig(data);
        addToast(t.ssh.saveSuccess, 'success');
      } else {
        await createSSHConfig(data);
        addToast(t.ssh.saveSuccess, 'success');
      }
      loadConfigs();
    } catch (error) {
      addToast(t.common.error, 'error');
    }
  };

  const handleDeleteConfig = async (id: string) => {
    try {
      await deleteSSHConfig(id);
      addToast(t.ssh.deleteSuccess, 'success');
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
        <TerminalPanel config={selectedConfig} />
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

export default SSHTool;
