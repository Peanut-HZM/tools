/**
 * fileType 工具测试 —— 重点覆盖「无扩展名文件」的 MIME 兜底逻辑
 *
 * 背景：`xa-higress-config` 这类**没有扩展名**的文件，
 * 靠文件名判断类型会落到 'unknown' → FileViewer 渲染
 * 「不支持的文件类型」占位页，无法正常打开。
 * 后端 read-raw 已做内容嗅探并返回 `content_type`，
 * 前端需要用它兜底路由。
 */
import { describe, it, expect } from 'vitest';
import {
  getFileCategory,
  getFileCategoryWithContentType,
  getFileLanguage,
  isTextContentType,
  isTextFile,
} from './fileType';

describe('getFileCategory（仅按文件名）', () => {
  it('按扩展名识别已有类型', () => {
    expect(getFileCategory('AGENTS.md')).toBe('text');
    expect(getFileCategory('install.sh')).toBe('code');
    expect(getFileCategory('report.pdf')).toBe('pdf');
    expect(getFileCategory('data.xlsx')).toBe('excel');
    expect(getFileCategory('pic.png')).toBe('image');
    expect(getFileCategory('dgpub-dev-ns-admin.kubeconfig')).toBe('code');
  });

  it('无扩展名文件返回 unknown（这正是需要 MIME 兜底的原因）', () => {
    expect(getFileCategory('xa-higress-config')).toBe('unknown');
    expect(getFileCategory('xa-higress-config-pd(1)')).toBe('unknown');
  });
});

describe('isTextContentType', () => {
  it('识别文本类 MIME', () => {
    expect(isTextContentType('text/plain')).toBe(true);
    expect(isTextContentType('text/markdown')).toBe(true);
    expect(isTextContentType('text/html')).toBe(true);
    expect(isTextContentType('application/json')).toBe(true);
    expect(isTextContentType('application/xml')).toBe(true);
    expect(isTextContentType('application/javascript')).toBe(true);
  });

  it('拒绝二进制类 MIME', () => {
    expect(isTextContentType('application/octet-stream')).toBe(false);
    expect(isTextContentType('image/png')).toBe(false);
    expect(isTextContentType('audio/mpeg')).toBe(false);
    expect(isTextContentType('video/mp4')).toBe(false);
    expect(isTextContentType('application/pdf')).toBe(false);
    expect(isTextContentType('application/zip')).toBe(false);
  });

  it('空值返回 false', () => {
    expect(isTextContentType(undefined)).toBe(false);
    expect(isTextContentType(null)).toBe(false);
    expect(isTextContentType('')).toBe(false);
  });

  it('大小写与空白不敏感', () => {
    expect(isTextContentType('  TEXT/PLAIN  ')).toBe(true);
  });
});

describe('getFileCategoryWithContentType', () => {
  it('有扩展名时优先用文件名判断（不受 MIME 影响）', () => {
    // .md 是 markdown → text 类；即使 MIME 说别的也以扩展名为准
    expect(getFileCategoryWithContentType('AGENTS.md', 'text/plain')).toBe('text');
    expect(getFileCategoryWithContentType('install.sh', 'text/plain')).toBe('code');
    expect(getFileCategoryWithContentType('pic.png', 'image/png')).toBe('image');
  });

  it('无扩展名 + 文本 MIME → text（核心修复场景）', () => {
    expect(getFileCategoryWithContentType('xa-higress-config', 'text/plain')).toBe('text');
    expect(getFileCategoryWithContentType('xa-higress-config-pd(1)', 'text/plain')).toBe('text');
  });

  it('无扩展名 + 图片 MIME → image', () => {
    expect(getFileCategoryWithContentType('screenshot', 'image/png')).toBe('image');
    expect(getFileCategoryWithContentType('screenshot', 'image/jpeg')).toBe('image');
  });

  it('无扩展名 + 二进制 MIME → unknown', () => {
    expect(getFileCategoryWithContentType('blob', 'application/octet-stream')).toBe('unknown');
  });

  it('无扩展名 + 无 MIME → unknown', () => {
    expect(getFileCategoryWithContentType('xa-higress-config')).toBe('unknown');
    expect(getFileCategoryWithContentType('xa-higress-config', '')).toBe('unknown');
    expect(getFileCategoryWithContentType('xa-higress-config', null)).toBe('unknown');
  });
});

describe('getFileLanguage / isTextFile（回归）', () => {
  it('语言识别保持不变', () => {
    expect(getFileLanguage('install.sh')).toBe('bash');
    expect(getFileLanguage('AGENTS.md')).toBe('plaintext');
    expect(getFileLanguage('xa-higress-config')).toBe('plaintext');
  });

  it('isTextFile 只看文件名时无扩展名文件为 false', () => {
    expect(isTextFile('install.sh')).toBe(true);
    expect(isTextFile('xa-higress-config')).toBe(false);
  });
});
