/**
 * Editor Store - Manages editor state and dirty flag using React Context
 */
import { createContext, useContext, useState, useCallback, useMemo, ReactNode } from 'react';
import type { SaveStatus } from '../types/markdownEditor';

export interface EditorState {
  content: string;
  originalContent: string;
  cursorLine: number;
  cursorColumn: number;
  isSaving: boolean;
  lastSaveTime: Date | null;
  saveError: string | null;
}

export interface EditorActions {
  setContent: (content: string, isOriginal?: boolean) => void;
  updateContent: (content: string) => void;
  setCursorPosition: (line: number, column: number) => void;
  markAsSaved: () => void;
  setSaving: (saving: boolean) => void;
  setSaveError: (error: string | null) => void;
  reset: () => void;
}

export interface EditorGetters {
  isDirty: boolean;
  saveStatus: SaveStatus;
}

export type EditorContextType = EditorState & EditorActions & EditorGetters;

const EditorContext = createContext<EditorContextType | null>(null);

export function EditorProvider({ children }: { children: ReactNode }) {
  const [content, setContentState] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [cursorLine, setCursorLine] = useState(1);
  const [cursorColumn, setCursorColumn] = useState(1);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaveTime, setLastSaveTime] = useState<Date | null>(null);
  const [saveError, setSaveErrorState] = useState<string | null>(null);

  // Computed values
  const isDirty = useMemo(() => content !== originalContent, [content, originalContent]);
  
  const saveStatus = useMemo((): SaveStatus => {
    if (isSaving) return 'saving';
    if (saveError) return 'error';
    if (isDirty) return 'unsaved';
    return 'saved';
  }, [isSaving, saveError, isDirty]);

  // Actions
  const setContent = useCallback((newContent: string, isOriginal: boolean = false) => {
    setContentState(newContent);
    if (isOriginal) {
      setOriginalContent(newContent);
    }
  }, []);

  const updateContent = useCallback((newContent: string) => {
    setContentState(newContent);
  }, []);

  const setCursorPosition = useCallback((line: number, column: number) => {
    setCursorLine(line);
    setCursorColumn(column);
  }, []);

  const markAsSaved = useCallback(() => {
    setOriginalContent(content);
    setLastSaveTime(new Date());
    setSaveErrorState(null);
  }, [content]);

  const setSaving = useCallback((saving: boolean) => {
    setIsSaving(saving);
  }, []);

  const setSaveError = useCallback((error: string | null) => {
    setSaveErrorState(error);
  }, []);

  const reset = useCallback(() => {
    setContentState('');
    setOriginalContent('');
    setCursorLine(1);
    setCursorColumn(1);
    setIsSaving(false);
    setLastSaveTime(null);
    setSaveErrorState(null);
  }, []);

  const value: EditorContextType = {
    // State
    content,
    originalContent,
    cursorLine,
    cursorColumn,
    isSaving,
    lastSaveTime,
    saveError,
    // Getters
    isDirty,
    saveStatus,
    // Actions
    setContent,
    updateContent,
    setCursorPosition,
    markAsSaved,
    setSaving,
    setSaveError,
    reset
  };

  return (
    <EditorContext.Provider value={value}>
      {children}
    </EditorContext.Provider>
  );
}

export function useEditorStore(): EditorContextType {
  const context = useContext(EditorContext);
  if (!context) {
    throw new Error('useEditorStore must be used within an EditorProvider');
  }
  return context;
}

export { EditorContext };
