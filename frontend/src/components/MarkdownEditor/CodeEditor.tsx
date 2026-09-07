/**
 * CodeEditor - 基于 Monaco Editor 的代码编辑器组件
 *
 * 功能：
 * - 根据文件扩展名自动识别编程语言并应用语法高亮
 * - 支持行号显示、代码折叠、MiniMap
 * - 支持只读模式
 * - 支持内容变更回调
 *
 * 依赖 utils/fileType.ts 的 getFileLanguage 进行语言识别
 */
import React, { useRef, useCallback } from 'react';
import Editor, { type OnMount } from '@monaco-editor/react';
import { getFileLanguage } from '../../utils/fileType';

/** CodeEditor 组件属性 */
interface CodeEditorProps {
  /** 文件路径（用于推断语言类型） */
  filePath: string;
  /** 文件文本内容；null 时回退为空字符串 */
  content: string | null;
  /** 内容变更回调 */
  onChange?: (content: string) => void;
  /** 是否只读 */
  readOnly?: boolean;
}

const CodeEditor: React.FC<CodeEditorProps> = ({ filePath, content, onChange, readOnly }) => {
  /** Monaco Editor 实例引用 */
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);

  /** 根据文件路径获取对应的 Monaco 语言标识 */
  const language = getFileLanguage(filePath);

  /** Editor 挂载完成时保存实例引用 */
  const handleEditorDidMount: OnMount = useCallback((editor) => {
    editorRef.current = editor;
  }, []);

  /** 内容变更时透传给外部回调 */
  const handleChange = useCallback(
    (value: string | undefined) => {
      if (onChange && value !== undefined) {
        onChange(value);
      }
    },
    [onChange],
  );

  return (
    <div className="h-full w-full">
      <Editor
        height="100%"
        language={language}
        value={content || ''}
        onChange={handleChange}
        onMount={handleEditorDidMount}
        options={{
          readOnly: readOnly || false,
          fontSize: 14,
          lineNumbers: 'on',
          minimap: { enabled: true },
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          automaticLayout: true,
          tabSize: 2,
          renderWhitespace: 'selection',
          bracketPairColorization: { enabled: true },
          folding: true,
          showFoldingControls: 'always',
        }}
        theme="vs-dark"
      />
    </div>
  );
};

export default CodeEditor;
