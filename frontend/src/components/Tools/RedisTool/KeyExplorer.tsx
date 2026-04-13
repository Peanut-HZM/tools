import React, { useState, useEffect } from 'react';
import { RedisKeyInfo, getRedisKeys, deleteRedisKeys } from '../../../api/redisToolApi';
import { KeyDetail } from './KeyDetail';
import { AddKeyModal } from './AddKeyModal';
import { useToast } from '../../../hooks/useToast';
import { useI18n, interpolate } from '../../../i18n';

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

  const loadKeys = async (searchPattern?: string) => {
    // If it's an auto-refresh (no loading spinner for better UX)
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
      // Only show toast on manual load to avoid spamming
      if (!isAutoRefresh) addToast(t.common.error, 'error');
      // Don't clear keys on auto-refresh error to keep UI stable
      if (!isAutoRefresh) setKeys([]);
    } finally {
      if (!isAutoRefresh) setLoading(false);
    }
  };

  const handleRefresh = () => {
    // Force reset pattern to current input value or '*' if empty? 
    // Actually handleRefresh should probably use the current pattern in the input
    // But we need to make sure pattern state is up to date.
    loadKeys();
    // Trigger KeyDetail refresh if a key is selected
    if (selectedKey) {
      setRefreshTrigger(prev => prev + 1);
    }
  };

  useEffect(() => {
    setPattern('*');
    setSelectedKey(null);
    loadKeys('*');
  }, [configId]);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    const intervalId = setInterval(() => {
      loadKeys(); // Use current pattern
      
      // If a key is selected, we should also trigger its refresh.
      // We do this by incrementing refreshTrigger which is part of KeyDetail's key.
      if (selectedKey) {
        setRefreshTrigger(prev => prev + 1);
      }
    }, 5000);

    return () => clearInterval(intervalId);
  }, [configId, selectedKey, pattern]); // Dependencies for auto-refresh interval


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
      case 'string': return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      case 'list': return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
      case 'set': return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400';
      case 'zset': return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400';
      case 'hash': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400';
    }
  };

  return (
    <div className="flex h-full bg-slate-900">
      {/* Key List Sidebar */}
      <div className="w-1/3 border-r border-slate-700 flex flex-col bg-slate-900">
        <div className="p-4 border-b border-slate-700 space-y-2">
          <div className="flex space-x-2">
            <div className="relative flex-1">
                <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-500"></i>
                <input
                type="text"
                value={pattern}
                onChange={(e) => setPattern(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-md pl-9 pr-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-blue-500"
                placeholder={t.redis.searchKeys}
                onKeyDown={(e) => e.key === 'Enter' && loadKeys()}
                />
            </div>
            <button
              onClick={handleRefresh}
              className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
              title={t.redis.refresh}
            >
              <i className="fas fa-sync-alt"></i>
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-3 py-2 bg-blue-600 border border-transparent rounded-md text-white hover:bg-blue-700 transition-colors"
              title={t.redis.addKey}
            >
              <i className="fas fa-plus"></i>
            </button>
          </div>
          <div className="text-xs text-slate-500">
            {keys.length} {t.redis.keys}
            {keys.length === 0 && !loading && (
               <span className="ml-2 text-xs opacity-50 hidden group-hover:inline">
                 (Pattern: {pattern})
               </span>
            )}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {loading ? (
            <div className="flex justify-center items-center h-32 text-slate-500">
                <i className="fas fa-spinner fa-spin mr-2"></i> {t.common.loading}
            </div>
          ) : (
            <div className="space-y-1">
              {keys.map((k) => (
                <div
                  key={k.key}
                  className={`p-2 rounded cursor-pointer flex justify-between items-center group ${
                    selectedKey === k.key 
                        ? 'bg-blue-600 text-white' 
                        : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                  onClick={() => setSelectedKey(k.key)}
                >
                  <div className="truncate flex-1 mr-2">
                    <div className="font-medium text-sm truncate" title={k.key}>
                      {k.key}
                    </div>
                    <div className="text-xs mt-0.5 flex items-center space-x-2 opacity-80">
                      <span className={`px-1.5 rounded text-[10px] uppercase font-bold ${
                          selectedKey === k.key ? 'bg-white/20 text-white' : getKeyTypeColor(k.type)
                      }`}>
                          {k.type}
                      </span>
                      {k.ttl > 0 && <span>TTL: {k.ttl}s</span>}
                    </div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDeleteKey(k.key); }}
                    className={`p-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity ${
                        selectedKey === k.key ? 'hover:bg-blue-500 text-blue-100' : 'hover:bg-slate-700 text-slate-400 hover:text-red-400'
                    }`}
                    title={t.redis.deleteKey}
                  >
                    <i className="fas fa-trash text-xs"></i>
                  </button>
                </div>
              ))}
              {keys.length === 0 && (
                <div className="p-8 text-center text-sm text-slate-500">
                    {t.redis.noKeysFound}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Key Detail View */}
      <div className="flex-1 bg-slate-900 overflow-hidden flex flex-col">
        {selectedKey ? (
          <KeyDetail
            key={`${configId}-${selectedKey}-${refreshTrigger}`}
            configId={configId}
            keyName={selectedKey}
            onKeyUpdated={loadKeys}
          />
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-500">
            <i className="fas fa-hand-pointer text-4xl mb-4 opacity-30"></i>
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
