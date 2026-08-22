import { useEffect, useRef } from 'react';
import * as monaco from 'monaco-editor';

/**
 * 变量高亮 Hook
 * 在 Monaco Editor 中高亮 {{variable}} 语法，支持：
 * 1. 已定义变量：紫色高亮 + 悬停显示值
 * 2. 未定义变量：红色波浪线 + 悬停提示未定义
 * 3. 自动补全：输入 {{ 时提示可用变量
 */
export function useVariableHighlighter(
  editor: monaco.editor.IStandaloneCodeEditor | null,
  variables: Record<string, string>
) {
  // 使用 ref 存储装饰器 ID，便于清理
  const decorationIdsRef = useRef<string[]>([]);

  useEffect(() => {
    if (!editor) return;

    // 注册变量自动补全提供器
    const completionDisposable = monaco.languages.registerCompletionItemProvider('plaintext', {
      triggerCharacters: ['{', ''],
      provideCompletionItems: (model, position) => {
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        };

        // 生成变量补全建议
        const suggestions = Object.keys(variables).map(key => ({
          label: `{{${key}}}`,
          kind: monaco.languages.CompletionItemKind.Variable,
          insertText: `{{${key}}}`,
          range,
          detail: variables[key] || '未赋值',
          documentation: `环境变量: ${key}`,
        }));

        return { suggestions };
      },
    });

    // 注册 JSON 语言的补全提供器
    const jsonCompletionDisposable = monaco.languages.registerCompletionItemProvider('json', {
      triggerCharacters: ['{', ''],
      provideCompletionItems: (model, position) => {
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        };

        const suggestions = Object.keys(variables).map(key => ({
          label: `{{${key}}}`,
          kind: monaco.languages.CompletionItemKind.Variable,
          insertText: `{{${key}}}`,
          range,
          detail: variables[key] || '未赋值',
        }));

        return { suggestions };
      },
    });

    // 应用变量高亮装饰器
    const applyDecorations = () => {
      const model = editor.getModel();
      if (!model) return;

      const text = model.getValue();
      // 匹配 {{变量名}} 格式
      const variableRegex = /\{\{(\w+)\}\}/g;
      const decorations: monaco.editor.IModelDeltaDecoration[] = [];
      let match;

      while ((match = variableRegex.exec(text)) !== null) {
        const varName = match[1];
        const isDefined = varName in variables;
        const startPos = model.getPositionAt(match.index);
        const endPos = model.getPositionAt(match.index + match[0].length);

        decorations.push({
          range: new monaco.Range(
            startPos.lineNumber,
            startPos.column,
            endPos.lineNumber,
            endPos.column
          ),
          options: {
            inlineClassName: isDefined ? 'variable-defined' : 'variable-undefined',
            hoverMessage: {
              value: isDefined
                ? `**${varName}** = \`${variables[varName]}\``
                : `⚠️ 未定义变量: **${varName}**`,
            },
          },
        });
      }

      // 更新装饰器（deltaDecorations 返回当前装饰器 ID 数组）
      decorationIdsRef.current = editor.deltaDecorations(
        decorationIdsRef.current,
        decorations
      );
    };

    // 初始应用高亮
    applyDecorations();

    // 监听内容变化，动态更新高亮
    const changeDisposable = editor.onDidChangeModelContent(() => {
      applyDecorations();
    });

    return () => {
      completionDisposable.dispose();
      jsonCompletionDisposable.dispose();
      changeDisposable.dispose();
      // 清理装饰器
      if (editor.getModel()) {
        editor.deltaDecorations(decorationIdsRef.current, []);
      }
      decorationIdsRef.current = [];
    };
  }, [editor, variables]);
}
