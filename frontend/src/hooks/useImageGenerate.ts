/**
 * useImageGenerate — 封装 store 的 generate + abort
 */
import { useCallback } from 'react';
import { useImageGenStore } from '../stores/imageGenerationStore';

export function useImageGenerate() {
  const generate = useImageGenStore((s) => s.generate);
  const abort = useImageGenStore((s) => s.abort);
  const loading = useImageGenStore((s) => s.loading);
  const error = useImageGenStore((s) => s.error);
  const currentResult = useImageGenStore((s) => s.currentResult);
  const setError = useImageGenStore((s) => s.setError);

  const handleGenerate = useCallback(() => {
    generate();
  }, [generate]);

  const handleAbort = useCallback(() => {
    abort();
  }, [abort]);

  return {
    generate: handleGenerate,
    abort: handleAbort,
    loading,
    error,
    currentResult,
    setError,
  };
}
