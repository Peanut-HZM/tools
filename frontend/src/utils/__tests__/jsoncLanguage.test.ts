/**
 * jsoncLanguage 工具函数测试
 *
 * 验证：
 * - isJsoncFile 对 .jsonc / 大小写 / 非 jsonc 文件的判断
 * - enableJsoncDiagnostics 把 JSON 诊断切到宽松模式
 * - restoreStrictJsonDiagnostics 恢复严格模式且幂等
 * - Monaco 未暴露 jsonDefaults 时不抛错
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  enableJsoncDiagnostics,
  restoreStrictJsonDiagnostics,
  isJsoncFile,
} from '../jsoncLanguage';

/** 构造带 setDiagnosticsOptions 记录的 mock monaco */
function makeMonaco() {
  const calls: Array<Record<string, unknown>> = [];
  return {
    monaco: {
      languages: {
        json: {
          jsonDefaults: {
            setDiagnosticsOptions: (options: Record<string, unknown>) => {
              calls.push(options);
            },
          },
        },
      },
    },
    calls,
  };
}

describe('isJsoncFile', () => {
  it('识别 .jsonc 文件', () => {
    expect(isJsoncFile('opencode.jsonc')).toBe(true);
    expect(isJsoncFile('C:/config/opencode.jsonc')).toBe(true);
  });

  it('大小写不敏感', () => {
    expect(isJsoncFile('CONFIG.JSONC')).toBe(true);
  });

  it('非 jsonc 文件返回 false', () => {
    expect(isJsoncFile('config.json')).toBe(false);
    expect(isJsoncFile('notes.md')).toBe(false);
    expect(isJsoncFile('')).toBe(false);
  });
});

describe('enableJsoncDiagnostics', () => {
  beforeEach(() => {
    // 每个用例前先恢复到严格模式基线
    const { monaco } = makeMonaco();
    enableJsoncDiagnostics(monaco);
    restoreStrictJsonDiagnostics(monaco);
  });

  it('把注释与尾逗号诊断降级为 ignore', () => {
    const { monaco, calls } = makeMonaco();
    enableJsoncDiagnostics(monaco);
    expect(calls).toEqual([
      { comments: 'ignore', trailingCommas: 'ignore' },
    ]);
  });

  it('重复调用幂等', () => {
    const { monaco, calls } = makeMonaco();
    enableJsoncDiagnostics(monaco);
    enableJsoncDiagnostics(monaco);
    // 两次调用都安全执行，不抛错
    expect(calls.length).toBe(2);
    calls.forEach((c) => {
      expect(c).toEqual({ comments: 'ignore', trailingCommas: 'ignore' });
    });
  });

  it('Monaco 未暴露 jsonDefaults 时不抛错', () => {
    expect(() => enableJsoncDiagnostics({})).not.toThrow();
    expect(() => enableJsoncDiagnostics(null)).not.toThrow();
  });

  it('Monaco 未实现 setDiagnosticsOptions 时不抛错', () => {
    expect(() =>
      enableJsoncDiagnostics({ languages: { json: { jsonDefaults: {} } } })
    ).not.toThrow();
  });
});

describe('restoreStrictJsonDiagnostics', () => {
  it('仅在 jsonc 模式激活过时恢复严格配置', () => {
    const { monaco, calls } = makeMonaco();
    // 未激活过 jsonc 模式时不做任何调用
    restoreStrictJsonDiagnostics(monaco);
    expect(calls.length).toBe(0);

    enableJsoncDiagnostics(monaco);
    restoreStrictJsonDiagnostics(monaco);
    expect(calls).toEqual([
      { comments: 'ignore', trailingCommas: 'ignore' },
      { comments: 'error', trailingCommas: 'error' },
    ]);
  });

  it('恢复后再次调用幂等（不重复下发严格配置）', () => {
    const { monaco, calls } = makeMonaco();
    enableJsoncDiagnostics(monaco);
    restoreStrictJsonDiagnostics(monaco);
    restoreStrictJsonDiagnostics(monaco);
    expect(calls.length).toBe(2);
  });

  it('Monaco 未暴露 jsonDefaults 时不抛错', () => {
    expect(() => restoreStrictJsonDiagnostics({})).not.toThrow();
  });
});
