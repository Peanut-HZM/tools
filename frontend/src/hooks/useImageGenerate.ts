/**
 * useImageGenerate — 封装 store 的 generate + chatGenerate
 */
import { useCallback } from 'react';
import { useImageGenStore } from '../stores/imageGenerationStore';
import type { ChatParams } from '../api/imageGenerationApi';

export function useImageGenerate() {
  const generate = useImageGenStore((s) => s.generate);
  const chatGenerate = useImageGenStore((s) => s.chatGenerate);
  const resetConversation = useImageGenStore((s) => s.resetConversation);
  const abort = useImageGenStore((s) => s.abort);
  const loading = useImageGenStore((s) => s.loading);
  const error = useImageGenStore((s) => s.error);
  const currentResult = useImageGenStore((s) => s.currentResult);
  const setError = useImageGenStore((s) => s.setError);
  const operation = useImageGenStore((s) => s.operation);

  const handleGenerate = useCallback(() => {
    generate();
  }, [generate]);

  const handleChat = useCallback(
    (prompt: string, params: ChatParams) => {
      return chatGenerate(operation, prompt, params);
    },
    [chatGenerate, operation],
  );

  const handleAbort = useCallback(() => {
    abort();
  }, [abort]);

  return {
    generate: handleGenerate,
    chat: handleChat,
    abort: handleAbort,
    loading,
    error,
    currentResult,
    setError,
    resetConversation,
  };
}
