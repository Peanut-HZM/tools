import React from 'react';
import { Plus, Server, Pencil, Trash2 } from 'lucide-react';
import { RedisConfig } from '../../../api/redisToolApi';
import { useI18n, interpolate } from '../../../i18n';
import { Button } from "@/components/ui/Button";

interface Props {
  configs: RedisConfig[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAdd: () => void;
  onEdit: (config: RedisConfig) => void;
  onDelete: (id: string) => void;
}

export const ConnectionList: React.FC<Props> = ({ configs, selectedId, onSelect, onAdd, onEdit, onDelete }) => {
  const { t } = useI18n();

  return (
    <div className="flex flex-col h-full bg-surface-1 border-r border-border w-64">
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
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
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
              <div className="font-medium flex items-center">
                <Server className="w-3 h-3 mr-2 opacity-70" />
                {config.alias}
              </div>
              <div className={`text-xs truncate ${selectedId === config.id ? 'text-ink' : 'text-ink-faint group-hover:text-ink-muted'}`}>
                {config.host}:{config.port} (DB {config.db})
              </div>
            </div>
            <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
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
