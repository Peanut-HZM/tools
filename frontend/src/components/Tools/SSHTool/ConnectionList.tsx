import React from 'react';
import { Plus, Terminal, Pencil, Trash2, HardDriveDownload, HardDriveUpload } from 'lucide-react';
import { SSHConfig } from '../../../api/sshToolApi';
import { useI18n, interpolate } from '../../../i18n';
import { useToast } from '../../../hooks/useToast';
import StorageLocationBadge from '../../Common/StorageLocationBadge';
import { migrateConfig } from '../../../api/storageApi';
import type { StorageLocation } from '../../../types/storage';

interface Props {
  configs: SSHConfig[];
  /** 仅用于保留 API 兼容;实际不再使用高亮 */
  selectedId: string | null;
  /** 语义:打开新 tab(不再是"选中") */
  onSelect: (id: string) => void;
  onAdd: () => void;
  onEdit: (config: SSHConfig) => void;
  onDelete: (id: string) => void;
  /** 迁移成功后刷新列表 */
  onMigrated?: () => void;
}

export const ConnectionList: React.FC<Props> = ({ configs, onSelect, onAdd, onEdit, onDelete, onMigrated }) => {
  const { t } = useI18n();
  const { addToast } = useToast();

  /** 存储位置迁移：本机 ↔ 服务器（迁移时后端会用目标端密钥重新加密凭据） */
  const handleMigrate = async (e: React.MouseEvent, config: SSHConfig) => {
    e.stopPropagation();
    const target: StorageLocation =
      (config.storage_location ?? 'local') === 'local' ? 'server' : 'local';
    const targetLabel = target === 'local' ? '仅保存在本机' : '上传到服务器';
    if (
      !window.confirm(
        `确定要「${targetLabel}」该连接配置吗？\n迁移时会用目标端的密钥重新加密凭据。`,
      )
    ) {
      return;
    }
    try {
      const result = await migrateConfig('ssh', config.id, target);
      addToast(result.message || '迁移成功', result.success ? 'success' : 'error');
      onMigrated?.();
    } catch (err) {
      addToast(err instanceof Error ? err.message : '迁移失败', 'error');
    }
  };

  return (
    // 移动端:侧栏占满整行并限制高度(自身滚动),避免挤压右侧终端区;md 以上恢复固定 256px 侧栏
    <div className="flex flex-col h-full bg-surface-1 border-b border-border md:border-b-0 md:border-r w-full md:w-64 max-h-[40vh] md:max-h-none overflow-y-auto">
      <div className="p-4 border-b border-border flex flex-col gap-2 bg-surface-1">
        <div className="flex justify-between items-center">
          <h2 className="font-semibold text-ink">{t.ssh.connections}</h2>
          <button
            onClick={onAdd}
            className="p-1.5 text-ink-muted hover:text-ink hover:bg-surface-2 rounded transition-colors"
            title={t.ssh.addConnection}
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {configs.map(config => (
          <div
            key={config.id}
            className="p-2 rounded cursor-pointer group flex justify-between items-center text-ink-muted hover:bg-surface-2 hover:text-ink"
            onClick={() => onSelect(config.id)}
          >
            <div className="truncate flex-1">
              <div className="font-medium flex items-center">
                <Terminal className="w-3 h-3 mr-2 opacity-70" />
                {config.alias}
                <span className="ml-1.5 flex-shrink-0">
                  <StorageLocationBadge location={(config.storage_location ?? 'local') as StorageLocation} />
                </span>
              </div>
              <div className="text-xs truncate text-ink-faint group-hover:text-ink-muted">
                {config.username}@{config.host}:{config.port}
              </div>
            </div>
            <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={(e) => handleMigrate(e, config)}
                className="p-1 rounded hover:bg-surface-3 text-ink-muted hover:text-ink"
                title={
                  (config.storage_location ?? 'local') === 'local'
                    ? '迁移到服务器存储'
                    : '迁移到本机存储'
                }
              >
                {(config.storage_location ?? 'local') === 'local' ? (
                  <HardDriveUpload className="w-3 h-3" />
                ) : (
                  <HardDriveDownload className="w-3 h-3" />
                )}
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onEdit(config); }}
                className="p-1 rounded hover:bg-surface-3 text-ink-muted hover:text-ink"
                title={t.ssh.editConnection}
              >
                <Pencil className="w-3 h-3" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm(interpolate(t.ssh.confirmDeleteConnection, { alias: config.alias }))) {
                    onDelete(config.id);
                  }
                }}
                className="p-1 rounded hover:bg-surface-3 text-ink-muted hover:text-danger"
                title={t.common.delete}
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          </div>
        ))}
        {configs.length === 0 && (
          <div className="p-4 text-center text-sm text-ink-faint">
            {t.ssh.emptyConnections}
          </div>
        )}
      </div>
    </div>
  );
};
