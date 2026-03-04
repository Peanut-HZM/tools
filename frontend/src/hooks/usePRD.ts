import { useState, useCallback } from 'react';
import { prdApi, PRDVersion, PRDCompareResult } from '../services/prdApi';

interface UsePRDResult {
  versions: PRDVersion[];
  currentVersion: PRDVersion | null;
  loading: boolean;
  error: string | null;
  loadVersions: (conversationId: string) => Promise<void>;
  loadVersion: (conversationId: string, versionNumber: number) => Promise<void>;
  compareVersions: (conversationId: string, fromVersion: number, toVersion: number) => Promise<PRDCompareResult | null>;
  rollbackToVersion: (conversationId: string, targetVersion: number) => Promise<PRDVersion | null>;
  updateSection: (conversationId: string, sectionTitle: string, sectionContent: string) => Promise<PRDVersion | null>;
}

export function usePRD(): UsePRDResult {
  const [versions, setVersions] = useState<PRDVersion[]>([]);
  const [currentVersion, setCurrentVersion] = useState<PRDVersion | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadVersions = useCallback(async (conversationId: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await prdApi.getVersions(conversationId);
      setVersions(data);
      if (data.length > 0) {
        setCurrentVersion(data[0]); // 默认加载最新版本
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载版本列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadVersion = useCallback(async (conversationId: string, versionNumber: number) => {
    try {
      setLoading(true);
      setError(null);
      const data = await prdApi.getVersion(conversationId, versionNumber);
      setCurrentVersion(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载版本失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const compareVersions = useCallback(async (
    conversationId: string,
    fromVersion: number,
    toVersion: number
  ): Promise<PRDCompareResult | null> => {
    try {
      setLoading(true);
      setError(null);
      const result = await prdApi.compareVersions(conversationId, fromVersion, toVersion);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : '对比版本失败');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const rollbackToVersion = useCallback(async (
    conversationId: string,
    targetVersion: number
  ): Promise<PRDVersion | null> => {
    try {
      setLoading(true);
      setError(null);
      const result = await prdApi.rollbackToVersion(conversationId, targetVersion);
      if (result) {
        setVersions(prev => [result, ...prev]);
        setCurrentVersion(result);
      }
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : '回滚版本失败');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateSection = useCallback(async (
    conversationId: string,
    sectionTitle: string,
    sectionContent: string
  ): Promise<PRDVersion | null> => {
    try {
      setLoading(true);
      setError(null);
      const result = await prdApi.updateSection(conversationId, sectionTitle, sectionContent);
      if (result) {
        setVersions(prev => [result, ...prev]);
        setCurrentVersion(result);
      }
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新章节失败');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    versions,
    currentVersion,
    loading,
    error,
    loadVersions,
    loadVersion,
    compareVersions,
    rollbackToVersion,
    updateSection,
  };
}
