/**
 * useAutoSave Hook - Handles automatic saving with debounce
 * Performance optimizations:
 * - Content hash comparison to avoid unnecessary saves
 * - Debounced save with configurable interval
 * - Prevents save during ongoing save operation
 */
import { useEffect, useRef, useCallback, useState } from 'react';

interface UseAutoSaveOptions {
  content: string;
  isDirty: boolean;
  interval: number; // in seconds
  onSave: () => Promise<void>;
  enabled?: boolean;
}

// Simple hash function for content comparison
function simpleHash(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return hash;
}

export function useAutoSave({
  content,
  isDirty,
  interval,
  onSave,
  enabled = true
}: UseAutoSaveOptions) {
  const timerRef = useRef<number | null>(null);
  const lastSavedHashRef = useRef<number>(0);
  const isSavingRef = useRef(false);
  const [lastSaveTime, setLastSaveTime] = useState<Date | null>(null);

  // Clear timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  // Perform save operation
  const performSave = useCallback(async () => {
    // Prevent concurrent saves
    if (isSavingRef.current) {
      return false;
    }

    const currentHash = simpleHash(content);
    
    // Skip if content hasn't changed since last save
    if (currentHash === lastSavedHashRef.current) {
      return false;
    }

    isSavingRef.current = true;
    try {
      await onSave();
      lastSavedHashRef.current = currentHash;
      setLastSaveTime(new Date());
      return true;
    } catch (e) {
      console.error('Auto-save failed:', e);
      return false;
    } finally {
      isSavingRef.current = false;
    }
  }, [content, onSave]);

  // Handle auto-save with debounce
  useEffect(() => {
    // Clear existing timer
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    // Don't auto-save if disabled, not dirty, or interval is 0
    if (!enabled || !isDirty || interval <= 0) {
      return;
    }

    // Set new timer with debounce
    timerRef.current = setTimeout(() => {
      performSave();
    }, interval * 1000);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [content, isDirty, interval, enabled, performSave]);

  // Force save function - bypasses debounce
  const forceSave = useCallback(async () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    
    if (isDirty && !isSavingRef.current) {
      return performSave();
    }
    return false;
  }, [isDirty, performSave]);

  // Cancel pending auto-save
  const cancelAutoSave = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  return { 
    forceSave, 
    cancelAutoSave,
    lastSaveTime,
    isSaving: isSavingRef.current
  };
}

export default useAutoSave;
