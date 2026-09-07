/**
 * CodeEditor 组件测试
 *
 * 验证：
 * - 根据文件扩展名正确传入 language 给 Monaco Editor
 * - content 为 null 时回退为空字符串
 * - content 正常透传
 * - onChange 回调正确触发
 * - readOnly 模式正确传递
 *
 * 由于 Monaco Editor 依赖真实 DOM（canvas / web worker），
 * 在 jsdom 测试环境中统一 mock @monaco-editor/react。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, cleanup } from '@testing-library/react';
import CodeEditor from '../CodeEditor';

/** 记录最近一次传给 MockEditor 的 props，便于断言 */
let lastProps: Record<string, unknown> | null = null;

/**
 * Mock 的 Monaco Editor 组件
 * 仅渲染一个 textarea 以承载 content / onChange，并记录全部 props
 */
function MockEditor(props: Record<string, unknown>) {
  lastProps = props;
  const value = (props.value as string) || '';
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (typeof props.onChange === 'function') {
      (props.onChange as (v: string) => void)(e.target.value);
    }
  };
  return (
    <div data-testid="monaco-mock">
      <textarea data-testid="mock-textarea" value={value} onChange={handleChange} />
      <span data-testid="mock-language">{props.language as string}</span>
    </div>
  );
}

// Mock @monaco-editor/react（必须在 import 之前声明，vi.mock 会自动提升）
vi.mock('@monaco-editor/react', () => ({
  __esModule: true,
  default: MockEditor,
}));

describe('CodeEditor', () => {
  beforeEach(() => {
    lastProps = null;
    cleanup();
  });

  describe('语言识别', () => {
    it('Python 文件识别为 python 语言', () => {
      render(<CodeEditor filePath="app.py" content="print('hi')" />);
      expect(lastProps?.language).toBe('python');
    });

    it('TypeScript 文件识别为 typescript 语言', () => {
      render(<CodeEditor filePath="index.ts" content="const x = 1" />);
      expect(lastProps?.language).toBe('typescript');
    });

    it('JavaScript 文件识别为 javascript 语言', () => {
      render(<CodeEditor filePath="util.js" content="const y = 2" />);
      expect(lastProps?.language).toBe('javascript');
    });

    it('Go 文件识别为 go 语言', () => {
      render(<CodeEditor filePath="main.go" content="package main" />);
      expect(lastProps?.language).toBe('go');
    });

    it('未知扩展名回退为 plaintext', () => {
      render(<CodeEditor filePath="readme.xyz" content="hello" />);
      expect(lastProps?.language).toBe('plaintext');
    });
  });

  describe('内容处理', () => {
    it('content 为 null 时回退为空字符串', () => {
      render(<CodeEditor filePath="app.py" content={null} />);
      expect(lastProps?.value).toBe('');
    });

    it('content 正常透传', () => {
      render(<CodeEditor filePath="app.py" content="hello world" />);
      expect(lastProps?.value).toBe('hello world');
    });
  });

  describe('onChange 回调', () => {
    it('用户输入时触发 onChange', () => {
      const handleChange = vi.fn();
      const { getByTestId } = render(
        <CodeEditor filePath="app.py" content="init" onChange={handleChange} />,
      );
      const textarea = getByTestId('mock-textarea');
      // 使用 fireEvent.change 触发 React 合成事件
      fireEvent.change(textarea, { target: { value: 'updated' } });
      expect(handleChange).toHaveBeenCalledWith('updated');
    });

    it('未提供 onChange 时不抛出错误', () => {
      const { getByTestId } = render(
        <CodeEditor filePath="app.py" content="init" />,
      );
      const textarea = getByTestId('mock-textarea');
      fireEvent.change(textarea, { target: { value: 'updated' } });
      // 不抛错即为通过
      expect(true).toBe(true);
    });
  });

  describe('只读模式', () => {
    it('readOnly 为 true 时透传给 Editor', () => {
      render(<CodeEditor filePath="app.py" content="x" readOnly={true} />);
      expect((lastProps?.options as Record<string, unknown>)?.readOnly).toBe(true);
    });

    it('readOnly 未传时默认为 false', () => {
      render(<CodeEditor filePath="app.py" content="x" />);
      expect((lastProps?.options as Record<string, unknown>)?.readOnly).toBe(false);
    });
  });

  describe('Editor 配置项', () => {
    it('启用行号显示', () => {
      render(<CodeEditor filePath="app.py" content="" />);
      expect((lastProps?.options as Record<string, unknown>)?.lineNumbers).toBe('on');
    });

    it('启用代码折叠', () => {
      render(<CodeEditor filePath="app.py" content="" />);
      expect((lastProps?.options as Record<string, unknown>)?.folding).toBe(true);
    });

    it('启用 automaticLayout 适应容器尺寸', () => {
      render(<CodeEditor filePath="app.py" content="" />);
      expect((lastProps?.options as Record<string, unknown>)?.automaticLayout).toBe(true);
    });

    it('使用 vs-dark 主题', () => {
      render(<CodeEditor filePath="app.py" content="" />);
      expect(lastProps?.theme).toBe('vs-dark');
    });
  });
});
