import { useState } from 'react';
import Editor from '@monaco-editor/react';
import * as monaco from 'monaco-editor';
import { useVariableHighlighter } from './VariableHighlighter';

/**
 * 脚本编辑器组件
 * 基于 Monaco Editor 封装，支持 {{variable}} 变量语法高亮和自动补全
 */
interface ScriptEditorProps {
  /** 编辑器内容 */
  value: string;
  /** 内容变化回调 */
  onChange: (value: string) => void;
  /** 编辑语言类型 */
  language?: 'javascript' | 'json' | 'plaintext';
  /** 环境变量列表，用于高亮和补全 */
  variables?: Record<string, string>;
  /** 编辑器高度 */
  height?: string;
  /** 是否只读 */
  readOnly?: boolean;
  /** 占位提示文本 */
  placeholder?: string;
}

export default function ScriptEditor({
  value,
  onChange,
  language = 'plaintext',
  variables = {},
  height = '200px',
  readOnly = false,
  placeholder,
}: ScriptEditorProps) {
  // 使用 state 持有编辑器实例，确保设置后触发重新渲染
  const [editor, setEditor] = useState<monaco.editor.IStandaloneCodeEditor | null>(null);

  // 使用变量高亮 Hook
  useVariableHighlighter(editor, variables);

  // 编辑器挂载完成回调
  const handleEditorDidMount = (editorInstance: monaco.editor.IStandaloneCodeEditor) => {
    setEditor(editorInstance);
  };

  return (
    <div className="relative border border-border rounded-lg overflow-hidden">
      <Editor
        height={height}
        language={language}
        value={value}
        onChange={(val) => onChange(val || '')}
        onMount={handleEditorDidMount}
        theme="vs-dark"
        options={{
          // 禁用小地图，节省空间
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: 'on',
          // 不显示最后一行之外的空白
          scrollBeyondLastLine: false,
          // 自动调整布局
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
          // 只读模式
          readOnly,
          // 启用自动补全
          quickSuggestions: true,
          suggestOnTriggerCharacters: true,
          // 滚动条样式
          scrollbar: {
            verticalScrollbarSize: 8,
            horizontalScrollbarSize: 8,
          },
          // 内边距
          padding: { top: 8, bottom: 8 },
        }}
      />
      {placeholder && !value && (
        <div className="absolute top-2 left-14 text-ink-faint text-sm pointer-events-none">
          {placeholder}
        </div>
      )}
    </div>
  );
}
