import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { DatabaseConfig, ExecutionHistory } from '../types/databaseTool';
import * as api from '../api/databaseToolApi';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../stores/authStore';

interface DatabaseToolContextType {
  configs: DatabaseConfig[];
  currentConfig: DatabaseConfig | null;
  currentDatabase: string | null;
  history: ExecutionHistory[];
  isLoading: boolean;
  refreshConfigs: () => Promise<void>;
  refreshHistory: () => Promise<void>;
  setCurrentConfig: (config: DatabaseConfig | null) => void;
  setCurrentDatabase: (database: string | null) => void;
  selectConfigById: (id: string) => void;
}

const DatabaseToolContext = createContext<DatabaseToolContextType | undefined>(undefined);

export const DatabaseToolProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [configs, setConfigs] = useState<DatabaseConfig[]>([]);
  const [currentConfig, setCurrentConfig] = useState<DatabaseConfig | null>(null);
  const [currentDatabase, setCurrentDatabase] = useState<string | null>(null);
  const [history, setHistory] = useState<ExecutionHistory[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();
  const { isAuthenticated, user, authVersion } = useAuth();

  const refreshConfigs = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const data = await api.getDatabases(user?.role === 'admin');
      setConfigs(data);
      
      // If current config is in the list, update it (to get latest status)
      if (currentConfig) {
        const found = data.find(c => c.id === currentConfig.id);
        if (found) {
          setCurrentConfig(found);
        } else {
          // If current config was deleted
          setCurrentConfig(null);
        }
      }
    } catch (error) {
      console.error('Failed to fetch database configs:', error);
      toast.error('Failed to fetch database configurations');
    } finally {
      setIsLoading(false);
    }
  }, [currentConfig, toast, isAuthenticated, user?.role]);

  const refreshHistory = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const data = await api.getHistory();
      setHistory(data);
    } catch (error) {
      console.error('Failed to fetch history:', error);
    }
  }, [isAuthenticated]);

  const selectConfigById = useCallback((id: string) => {
    const config = configs.find(c => c.id === id);
    if (config) {
      setCurrentConfig(config);
      // Reset current database or set to default if configured
      setCurrentDatabase(config.database_name || null);
    }
  }, [configs]);

  useEffect(() => {
    if (isAuthenticated) {
      // 并行请求：连接列表和历史记录同时发起，不再串行等待
      Promise.all([refreshConfigs(), refreshHistory()]).catch(console.error);
    } else {
      setConfigs([]);
      setHistory([]);
      setCurrentConfig(null);
      setCurrentDatabase(null);
    }
    // authVersion：登录成功/401 失效后自动重载
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, authVersion]);

  return (
    <DatabaseToolContext.Provider
      value={{
        configs,
        currentConfig,
        currentDatabase,
        history,
        isLoading,
        refreshConfigs,
        refreshHistory,
        setCurrentConfig,
        setCurrentDatabase,
        selectConfigById
      }}
    >
      {children}
    </DatabaseToolContext.Provider>
  );
};

export const useDatabaseTool = () => {
  const context = useContext(DatabaseToolContext);
  if (context === undefined) {
    throw new Error('useDatabaseTool must be used within a DatabaseToolProvider');
  }
  return context;
};
