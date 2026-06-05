import React, { useEffect, useRef } from 'react';
import Editor, { useMonaco } from '@monaco-editor/react';
import { TableItem } from '../../../../types/databaseTool';
import { useI18n } from '../../../../i18n';

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
    <div className="flex flex-col h-full border border-slate-700 rounded-md overflow-hidden bg-slate-800 shadow-sm">
      <div className="bg-slate-900 px-4 py-2 border-b border-slate-700 flex justify-between items-center">
        <span className="text-sm font-medium text-slate-300">{t.database.executor.title}</span>
        <div className="space-x-2 flex items-center">
          <button
            className="text-xs text-slate-400 hover:text-blue-400 transition-colors"
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
              className="text-slate-400 hover:text-blue-400 transition-colors"
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
            <div className="flex items-center justify-center h-full text-slate-500">
               <i className="fas fa-spinner fa-spin mr-2"></i> Loading Editor...
            </div>
          }
        />
      </div>
      <div className="bg-slate-900 px-4 py-2 border-t border-slate-700 flex justify-end">
        <button
          onClick={onExecute}
          disabled={loading || !value.trim()}
          className={`px-4 py-1.5 rounded-md text-sm font-medium text-white transition-colors flex items-center gap-2
            ${loading || !value.trim() 
              ? 'bg-blue-500/50 cursor-not-allowed' 
              : 'bg-blue-600 hover:bg-blue-500 shadow-sm'
            }`}
        >
          {loading && <i className="fas fa-spinner fa-spin"></i>}
          {loading ? t.database.executor.executing : t.database.executor.run}
        </button>
      </div>
    </div>
  );
};

export default SQLEditor;
