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
    <div className="flex flex-col h-full bg-slate-800 border-r border-slate-700 w-64">
      <div className="p-4 border-b border-slate-700 flex flex-col gap-2 bg-slate-800">
        <div className="flex justify-between items-center">
          <h2 className="font-semibold text-slate-100">{t.ssh.connections}</h2>
          <button
            onClick={onAdd}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
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
            className="p-2 rounded cursor-pointer group flex justify-between items-center text-slate-300 hover:bg-slate-700 hover:text-white"
            onClick={() => onSelect(config.id)}
          >
            <div className="truncate flex-1">
              <div className="font-medium flex items-center">
                <i className="fas fa-terminal mr-2 text-xs opacity-70"></i>
                {config.alias}
              </div>
              <div className="text-xs truncate text-slate-500 group-hover:text-slate-400">
                {config.username}@{config.host}:{config.port}
              </div>
            </div>
            <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={(e) => { e.stopPropagation(); onEdit(config); }}
                className="p-1 rounded hover:bg-slate-600 text-slate-400 hover:text-white"
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
                className="p-1 rounded hover:bg-slate-600 text-slate-400 hover:text-red-400"
                title={t.common.delete}
              >
                <i className="fas fa-trash text-xs"></i>
              </button>
            </div>
          </div>
        ))}
        {configs.length === 0 && (
          <div className="p-4 text-center text-sm text-slate-500">
            {t.ssh.emptyConnections}
          </div>
        )}
      </div>
    </div>
  );
};
