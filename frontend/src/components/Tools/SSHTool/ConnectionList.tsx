import React from 'react';
import { SSHConfig } from '../../../api/sshToolApi';
import { useI18n, interpolate } from '../../../i18n';

interface Props {
  configs: SSHConfig[];
  /** 仅用于保留 API 兼容;实际不再使用高亮 */
  selectedId: string | null;
  /** 语义:打开新 tab(不再是"选中") */
  onSelect: (id: string) => void;
  onAdd: () => void;
  onEdit: (config: SSHConfig) => void;
  onDelete: (id: string) => void;
}

export const ConnectionList: React.FC<Props> = ({ configs, onSelect, onAdd, onEdit, onDelete }) => {
  const { t } = useI18n();

  return (
    <div className="flex flex-col h-full bg-surface-1 border-r border-border w-64">
      <div className="p-4 border-b border-border flex flex-col gap-2 bg-surface-1">
        <div className="flex justify-between items-center">
          <h2 className="font-semibold text-ink">{t.ssh.connections}</h2>
          <button
            onClick={onAdd}
            className="p-1.5 text-ink-muted hover:text-ink-inverse hover:bg-surface-2 rounded transition-colors"
            title={t.ssh.addConnection}
          >
            <i className="fas fa-plus"></i>
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {configs.map(config => (
          <div
            key={config.id}
            className="p-2 rounded cursor-pointer group flex justify-between items-center text-ink-muted hover:bg-surface-2 hover:text-ink-inverse"
            onClick={() => onSelect(config.id)}
          >
            <div className="truncate flex-1">
              <div className="font-medium flex items-center">
                <i className="fas fa-terminal mr-2 text-xs opacity-70"></i>
                {config.alias}
              </div>
              <div className="text-xs truncate text-ink-faint group-hover:text-ink-muted">
                {config.username}@{config.host}:{config.port}
              </div>
            </div>
            <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={(e) => { e.stopPropagation(); onEdit(config); }}
                className="p-1 rounded hover:bg-surface-3 text-ink-muted hover:text-ink-inverse"
                title={t.ssh.editConnection}
              >
                <i className="fas fa-pen text-xs"></i>
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
                <i className="fas fa-trash text-xs"></i>
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
