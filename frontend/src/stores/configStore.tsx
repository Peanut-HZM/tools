/**
 * Config Store - Manages user settings using React Context
 */
import { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react';
import * as markdownEditorApi from '../api/markdownEditorApi';
import type { EditorConfig } from '../types/markdownEditor';

const defaultConfig: EditorConfig = {
  theme: 'dark',
  fontSize: 14,
  autoSaveInterval: 30,
  previewTheme: 'github',
  showLineNumbers: true,
  tabSize: 2,
  useSpaces: true,
  wordWrap: true,
  showMinimap: false,
  language: (localStorage.getItem('markdown-editor-language') as 'zh-CN' | 'en-US') || 'zh-CN'
};

export interface ConfigState {
  config: EditorConfig;
  isLoading: boolean;
  error: string | null;
}

export interface ConfigActions {
  loadConfig: () => Promise<void>;
  saveConfig: () => Promise<void>;
  updateConfig: (updates: Partial<EditorConfig>) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  setLanguage: (lang: 'zh-CN' | 'en-US') => void;
  setFontSize: (size: number) => void;
  setAutoSaveInterval: (interval: number) => void;
  resetToDefaults: () => void;
  clearError: () => void;
}

export type ConfigContextType = ConfigState & ConfigActions;

const ConfigContext = createContext<ConfigContextType | null>(null);

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<EditorConfig>({ ...defaultConfig });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Watch for language changes and persist to localStorage
  useEffect(() => {
    localStorage.setItem('markdown-editor-language', config.language);
  }, [config.language]);

  const loadConfig = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const loadedConfig = await markdownEditorApi.getConfig();
      setConfig({ ...defaultConfig, ...loadedConfig });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load config');
      // Use default config on error
      setConfig({ ...defaultConfig });
    } finally {
      setIsLoading(false);
    }
  }, []);

  const saveConfig = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      await markdownEditorApi.saveConfig(config);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save config');
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, [config]);

  const updateConfig = useCallback((updates: Partial<EditorConfig>) => {
    setConfig(prev => ({ ...prev, ...updates }));
  }, []);

  const setTheme = useCallback((theme: 'light' | 'dark') => {
    setConfig(prev => ({ ...prev, theme }));
  }, []);

  const setLanguage = useCallback((lang: 'zh-CN' | 'en-US') => {
    setConfig(prev => ({ ...prev, language: lang }));
  }, []);

  const setFontSize = useCallback((size: number) => {
    const clampedSize = Math.max(8, Math.min(32, size));
    setConfig(prev => ({ ...prev, fontSize: clampedSize }));
  }, []);

  const setAutoSaveInterval = useCallback((interval: number) => {
    const clampedInterval = Math.max(5, Math.min(300, interval));
    setConfig(prev => ({ ...prev, autoSaveInterval: clampedInterval }));
  }, []);

  const resetToDefaults = useCallback(() => {
    setConfig({ ...defaultConfig });
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value: ConfigContextType = {
    config,
    isLoading,
    error,
    loadConfig,
    saveConfig,
    updateConfig,
    setTheme,
    setLanguage,
    setFontSize,
    setAutoSaveInterval,
    resetToDefaults,
    clearError
  };

  return (
    <ConfigContext.Provider value={value}>
      {children}
    </ConfigContext.Provider>
  );
}

export function useConfigStore(): ConfigContextType {
  const context = useContext(ConfigContext);
  if (!context) {
    throw new Error('useConfigStore must be used within a ConfigProvider');
  }
  return context;
}

export { ConfigContext };
