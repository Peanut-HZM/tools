import React, { useEffect, useRef } from 'react';
import Editor, { useMonaco } from '@monaco-editor/react';
import { TableItem } from '../../../../types/databaseTool';
import { useI18n } from '../../../../i18n';
import { Button } from '@/components/ui/Button';

interface SQLEditorProps {
  value: string;
  onChange: (value: string) => void;
  onExecute: () => void;
  loading?: boolean;
  tables?: TableItem[];
  pageSize?: number;
  onPageSizeChange?: (size: number) => void;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
}

const SQLEditor: React.FC<SQLEditorProps> = ({
  value, onChange, onExecute, loading, tables = [],
  pageSize, onPageSizeChange,
  isFullscreen = false,
  onToggleFullscreen
}) => {
  const { t } = useI18n();
  const monaco = useMonaco();
  const editorRef = useRef<any>(null);

  useEffect(() => {
    if (monaco && tables.length > 0) {
      // Clean up previous completion providers if needed
      // Note: This is a global registration, so it might affect other editors if multiple exist.
      // A better way is to register once or use a specific model.
      
      const disposable = monaco.languages.registerCompletionItemProvider('sql', {
        provideCompletionItems: (model, position) => {
          const word = model.getWordUntilPosition(position);
          const range = {
            startLineNumber: position.lineNumber,
            endLineNumber: position.lineNumber,
            startColumn: word.startColumn,
            endColumn: word.endColumn,
          };

          const suggestions = tables.map(table => ({
            label: table.name,
            kind: monaco.languages.CompletionItemKind.Class,
            insertText: table.name,
            range: range,
            detail: table.comment || 'Table'
          }));

          return { suggestions };
        }
      });

      return () => {
        disposable.dispose();
      };
    }
  }, [monaco, tables]);

  const handleEditorDidMount = (editor: any, monacoInstance: any) => {
    editorRef.current = editor;
    
    // Add Command+Enter / Ctrl+Enter to execute
    editor.addCommand(monacoInstance.KeyMod.CtrlCmd | monacoInstance.KeyCode.Enter, () => {
      onExecute();
    });

    // Add Shift+Enter to execute
    editor.addCommand(monacoInstance.KeyMod.Shift | monacoInstance.KeyCode.Enter, () => {
      onExecute();
    });
  };

  return (
    <div className="flex flex-col h-full border border-border rounded-md overflow-hidden bg-surface-1 shadow-sm">
      <div className="bg-canvas px-4 py-2 border-b border-border flex justify-between items-center">
        <span className="text-sm font-medium text-ink-muted">{t.database.executor.title}</span>
        <div className="space-x-2 flex items-center">
          <button
            className="text-xs text-ink-muted hover:text-accent-info transition-colors"
            onClick={() => onChange('')}
          >
            {t.database.executor.clear}
          </button>
          {onToggleFullscreen && (
            <button
              data-testid="fullscreen-toggle"
              onClick={onToggleFullscreen}
              title={isFullscreen
                ? t.database.executor.exitFullscreen
                : t.database.executor.enterFullscreen}
              aria-label={isFullscreen
                ? t.database.executor.exitFullscreen
                : t.database.executor.enterFullscreen}
              className="text-ink-muted hover:text-accent-info transition-colors"
            >
              <i className={isFullscreen
                ? 'fas fa-compress text-sm'
                : 'fas fa-expand text-sm'} />
            </button>
          )}
        </div>
      </div>
      <div className="flex-1 relative">
        <Editor
          height="100%"
          defaultLanguage="sql"
          theme="vs-dark"
          value={value}
          onChange={(val) => onChange(val || '')}
          onMount={handleEditorDidMount}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            padding: { top: 10, bottom: 10 },
            automaticLayout: true,
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            lineNumbers: 'on',
            renderLineHighlight: 'all',
            fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
          }}
          loading={
            <div className="flex items-center justify-center h-full text-ink-faint">
               <i className="fas fa-spinner fa-spin mr-2"></i> Loading Editor...
            </div>
          }
        />
      </div>
      <div className="bg-canvas px-4 py-2 border-t border-border flex justify-end">
        <Button
          onClick={onExecute}
          disabled={loading || !value.trim()}
          className="flex items-center gap-2"
        >
          {loading && <i className="fas fa-spinner fa-spin"></i>}
          {loading ? t.database.executor.executing : t.database.executor.run}
        </Button>
      </div>
    </div>
  );
};

export default SQLEditor;
