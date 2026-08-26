import React, { useState, useEffect } from 'react';
import { Search, CheckSquare, RefreshCw, Plus, Loader2, Trash2, Hand } from 'lucide-react';
import { RedisKeyInfo, getRedisKeys, deleteRedisKeys } from '../../../api/redisToolApi';
import { batchUpdateTTL, batchRename } from '../../../api/redisToolApi';
import { KeyDetail } from './KeyDetail';
import { AddKeyModal } from './AddKeyModal';
import { BatchToolbar } from './BatchToolbar';
import { useToast } from '../../../hooks/useToast';
import { useI18n, interpolate } from '../../../i18n';
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from '@/components/ui/Badge';

interface Props {
  configId: string;
}

export const KeyExplorer: React.FC<Props> = ({ configId }) => {
  const { addToast } = useToast();
  const { t } = useI18n();
  const [keys, setKeys] = useState<RedisKeyInfo[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [pattern, setPattern] = useState('*');
  const [showAddModal, setShowAddModal] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [batchMode, setBatchMode] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  const loadKeys = async (searchPattern?: string) => {
    const isAutoRefresh = !searchPattern && !loading;
    if (!isAutoRefresh) setLoading(true);

    const patternToUse = searchPattern ?? pattern;
    try {
      const data = await getRedisKeys(configId, patternToUse);
      if (!Array.isArray(data)) {
        console.error('[RedisTool] Data is not an array:', data);
        setKeys([]);
      } else {
        setKeys(data);
      }
    } catch (error) {
      console.error('[RedisTool] Failed to load keys:', error);
      if (!isAutoRefresh) addToast(t.common.error, 'error');
      if (!isAutoRefresh) setKeys([]);
    } finally {
      if (!isAutoRefresh) setLoading(false);
    }
  };

  const handleRefresh = () => {
    loadKeys();
    if (selectedKey) {
      setRefreshTrigger(prev => prev + 1);
    }
  };

  useEffect(() => {
    setPattern('*');
    setSelectedKey(null);
    loadKeys('*');
  }, [configId]);

  useEffect(() => {
    const intervalId = setInterval(() => {
      loadKeys();
      if (selectedKey) {
        setRefreshTrigger(prev => prev + 1);
      }
    }, 5000);

    return () => clearInterval(intervalId);
  }, [configId, selectedKey, pattern]);

  const handleDeleteKey = async (key: string) => {
    if (!confirm(interpolate(t.redis.confirmDeleteKey, { key }))) return;
    try {
      await deleteRedisKeys(configId, [key]);
      addToast(t.redis.deleteSuccess, 'success');
      if (selectedKey === key) setSelectedKey(null);
      loadKeys();
    } catch (error) {
      addToast(t.common.error, 'error');
    }
  };

  const getKeyTypeColor = (type: string) => {
    switch (type) {
      case 'string': return 'bg-success/15 text-success';
      case 'list': return 'bg-accent-info/15 text-accent-info';
      case 'set': return 'bg-accent-secondary/15 text-accent-secondary';
      case 'zset': return 'bg-warning/15 text-warning';
      case 'hash': return 'bg-accent-warm/15 text-accent-warm';
      default: return 'bg-surface-2 text-ink-muted';
    }
  };

  return (
    <div className="flex h-full bg-canvas">
      <div className="w-1/3 border-r border-border flex flex-col bg-canvas">
        <div className="p-4 border-b border-border space-y-2">
          <div className="flex space-x-2">
            <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-ink-faint" />
                <Input
                type="text"
                value={pattern}
                onChange={(e) => setPattern(e.target.value)}
                className="w-full pl-9"
                placeholder={t.redis.searchKeys}
                onKeyDown={(e) => e.key === 'Enter' && loadKeys()}
                />
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => {
                setBatchMode(!batchMode);
                setSelectedKeys(new Set());
              }}
              className={batchMode ? 'bg-accent text-ink-inverse border-accent-hover hover:bg-accent-hover hover:text-ink-inverse' : ''}
              title={batchMode ? '退出批量' : '批量模式'}
            >
              <CheckSquare className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleRefresh}
              title={t.redis.refresh}
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
            <Button
              size="icon"
              onClick={() => setShowAddModal(true)}
              title={t.redis.addKey}
            >
              <Plus className="w-4 h-4" />
            </Button>
          </div>
          <div className="text-xs text-ink-faint">
            {keys.length} {t.redis.keys}
            {keys.length === 0 && !loading && (
               <span className="ml-2 text-xs opacity-50 hidden group-hover:inline">
                 (Pattern: {pattern})
               </span>
            )}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {batchMode && (
            <BatchToolbar
              selectedCount={selectedKeys.size}
              configId={configId}
              selectedKeys={Array.from(selectedKeys)}
              onBatchDelete={async (keys) => {
                await deleteRedisKeys(configId, keys);
                addToast(t.redis.deleteSuccess, 'success');
                setSelectedKeys(new Set());
                loadKeys();
              }}
              onBatchTTL={async (keys, ttl) => {
                await batchUpdateTTL(configId, keys, ttl);
                addToast('TTL updated', 'success');
                setSelectedKeys(new Set());
                loadKeys();
              }}
              onBatchRename={async (keys, pattern, replacement) => {
                await batchRename(configId, keys, pattern, replacement);
                addToast('Keys renamed', 'success');
                setSelectedKeys(new Set());
                loadKeys();
              }}
              onClear={() => setSelectedKeys(new Set())}
            />
          )}
          {loading ? (
            <div className="flex justify-center items-center h-32 text-ink-faint">
                <Loader2 className="w-4 h-4 mr-2 animate-spin" /> {t.common.loading}
            </div>
          ) : (
            <div className="space-y-1">
              {keys.map((k) => (
                <div
                  key={k.key}
                  className={`p-2 rounded cursor-pointer flex items-center group ${
                    selectedKey === k.key && !batchMode
                        ? 'bg-accent text-white'
                        : selectedKeys.has(k.key) && batchMode
                        ? 'bg-accent-info/40 text-ink-inverse'
                        : 'text-ink-muted hover:bg-surface-1 hover:text-ink'
                  }`}
                  onClick={() => {
                    if (batchMode) {
                      const newSet = new Set(selectedKeys);
                      if (newSet.has(k.key)) newSet.delete(k.key);
                      else newSet.add(k.key);
                      setSelectedKeys(newSet);
                    } else {
                      setSelectedKey(k.key);
                    }
                  }}
                >
                  {batchMode && (
                    <input
                      type="checkbox"
                      checked={selectedKeys.has(k.key)}
                      onChange={(e) => {
                        e.stopPropagation();
                        const newSet = new Set(selectedKeys);
                        if (e.target.checked) newSet.add(k.key);
                        else newSet.delete(k.key);
                        setSelectedKeys(newSet);
                      }}
                      className="mr-2 w-4 h-4 rounded border-border bg-surface-1 text-accent-info focus:ring-accent-info"
                    />
                  )}
                  <div className="truncate flex-1 mr-2">
                    <div className="font-medium text-sm truncate" title={k.key}>
                      {k.key}
                    </div>
                    <div className="text-xs mt-0.5 flex items-center space-x-2 opacity-80">
                      <Badge variant="secondary" className={`text-[10px] uppercase font-bold px-1.5 py-0 ${
                          selectedKey === k.key ? '' : getKeyTypeColor(k.type)
                      }`}>
                          {k.type}
                      </Badge>
                      {k.ttl > 0 && <span>TTL: {k.ttl}s</span>}
                    </div>
                  </div>
                  {!batchMode && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => { e.stopPropagation(); handleDeleteKey(k.key); }}
                      className={`h-8 w-8 opacity-0 group-hover:opacity-100 ${
                          selectedKey === k.key ? 'hover:bg-accent-hover text-ink-inverse' : 'hover:bg-surface-2 text-ink-muted hover:text-danger'
                      }`}
                      title={t.redis.deleteKey}
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  )}
                </div>
              ))}
              {keys.length === 0 && (
                <div className="p-8 text-center text-sm text-ink-faint">
                    {t.redis.noKeysFound}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 bg-canvas overflow-hidden flex flex-col">
        {selectedKey ? (
          <KeyDetail
            key={`${configId}-${selectedKey}-${refreshTrigger}`}
            configId={configId}
            keyName={selectedKey}
            onKeyUpdated={loadKeys}
          />
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-ink-faint">
            <Hand className="w-10 h-10 mb-4 opacity-30" />
            <p className="text-lg">{t.redis.selectConnection}</p>
          </div>
        )}
      </div>

      <AddKeyModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        configId={configId}
        onSuccess={loadKeys}
      />
    </div>
  );
};