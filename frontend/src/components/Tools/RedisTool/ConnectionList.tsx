import React from 'react';
import { Plus, Server, Pencil, Trash2, HardDriveDownload, HardDriveUpload } from 'lucide-react';
import { RedisConfig } from '../../../api/redisToolApi';
import { useI18n, interpolate } from '../../../i18n';
import { Button } from "@/components/ui/Button";
import { useToast } from '../../../hooks/useToast';
import StorageLocationBadge from '../../Common/StorageLocationBadge';
import { migrateConfig } from '../../../api/storageApi';
import type { StorageLocation } from '../../../types/storage';

interface Props {
  configs: RedisConfig[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAdd: () => void;
  onEdit: (config: RedisConfig) => void;
  onDelete: (id: string) => void;
  /** 迁移成功后刷新列表 */
  onMigrated?: () => void;
}

export const ConnectionList: React.FC<Props> = ({ configs, selectedId, onSelect, onAdd, onEdit, onDelete, onMigrated }) => {
  const { t } = useI18n();
  const { addToast } = useToast();

  /** 存储位置迁移：本机 ↔ 服务器（迁移时后端会用目标端密钥重新加密凭据） */
  const handleMigrate = async (e: React.MouseEvent, config: RedisConfig) => {
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
      const result = await migrateConfig('redis', config.id, target);
      addToast(result.message || '迁移成功', result.success ? 'success' : 'error');
      onMigrated?.();
    } catch (err) {
      addToast(err instanceof Error ? err.message : '迁移失败', 'error');
    }
  };

  return (
    // 桌面端高度由内容决定（md:h-auto），连接少时不再撑满整列留白；
    // 内容超出视口高度时自身滚动（md:max-h-[calc(100vh-140px)] 留出顶部空间）。
    // 移动端:侧栏占满整行并限制高度(自身滚动),避免挤压右侧主面板;md 以上恢复固定 256px 侧栏
    <div className="flex flex-col h-full bg-surface-1 border-b border-border md:h-auto md:max-h-[calc(100vh-140px)] md:border-b-0 md:border-r w-full md:w-64 max-h-[40vh] overflow-y-auto">
      <div className="p-4 border-b border-border flex flex-col gap-2 bg-surface-1">
        <div className="flex justify-between items-center">
          <h2 className="font-semibold text-ink">{t.redis.connections}</h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={onAdd}
            title={t.redis.addConnection}
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1 md:min-h-0 md:max-h-[calc(100vh-160px)]">
        {configs.map(config => (
          <div
            key={config.id}
            className={`p-2 rounded cursor-pointer group flex justify-between items-center ${
              selectedId === config.id
                ? 'bg-accent text-white'
                : 'text-ink-muted hover:bg-surface-2 hover:text-ink'
            }`}
            onClick={() => onSelect(config.id)}
          >
            <div className="truncate flex-1">
              <div className="font-medium flex items-center min-w-0">
                <Server className="w-3 h-3 mr-2 opacity-70 shrink-0" />
                <span className="truncate min-w-0">{config.alias}</span>
                <span className="ml-1.5 flex-shrink-0">
                  <StorageLocationBadge
                    location={(config.storage_location ?? 'local') as StorageLocation}
                    compact
                  />
                </span>
              </div>
              <div className={`text-xs truncate ${selectedId === config.id ? 'text-ink' : 'text-ink-faint group-hover:text-ink-muted'}`}>
                {config.host}:{config.port} (DB {config.db})
              </div>
            </div>
            <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
               <Button
                variant="ghost"
                size="icon"
                onClick={(e) => handleMigrate(e, config)}
                className={`h-8 w-8 p-1 ${selectedId === config.id ? 'hover:bg-accent-hover text-ink-inverse' : 'hover:bg-surface-3 text-ink-muted hover:text-ink'}`}
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
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => { e.stopPropagation(); onEdit(config); }}
                className={`h-8 w-8 p-1 ${selectedId === config.id ? 'hover:bg-accent-hover text-ink-inverse' : 'hover:bg-surface-3 text-ink-muted hover:text-ink'}`}
                title={t.redis.editConnection}
              >
                <Pencil className="w-3 h-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  if(confirm(interpolate(t.redis.confirmDeleteConnection, { alias: config.alias }))) {
                    onDelete(config.id);
                  }
                }}
                className={`h-8 w-8 p-1 ${selectedId === config.id ? 'hover:bg-accent-hover text-ink-inverse' : 'hover:bg-surface-3 text-ink-muted hover:text-danger'}`}
                title={t.common.delete}
              >
                 <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          </div>
        ))}
        {configs.length === 0 && (
            <div className="p-4 text-center text-sm text-ink-faint">
                {t.redis.noKeysFound}
            </div>
        )}
      </div>
    </div>
  );
};
