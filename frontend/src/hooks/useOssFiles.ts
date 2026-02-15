import { useState, useEffect, useCallback } from 'react';
import { listOssFiles } from '../api/markdownEditorApi';
import type { OssFileInfo } from '../types/offlineCache';

interface UseOssFilesReturn {
  ossFiles: OssFileInfo[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useOssFiles(): UseOssFilesReturn {
  const [ossFiles, setOssFiles] = useState<OssFileInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const files = await listOssFiles();
      setOssFiles(files);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load OSS files');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return {
    ossFiles,
    isLoading,
    error,
    refresh,
  };
}

export default useOssFiles;
