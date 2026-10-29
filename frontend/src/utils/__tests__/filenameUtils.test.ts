/**
 * 文件名扩展名处理测试
 *
 * 核心诉求：新建文件时，只有文件名**完全没有扩展名**才默认补 .md，
 * 已经带扩展名（如 example.kubeconfig）必须保持原样。
 */
import { describe, it, expect } from 'vitest';
import {
  ensureFileExtension,
  getFileExtension,
  hasFileExtension,
  resolveRenameName,
} from '../filenameUtils';

describe('hasFileExtension', () => {
  it('普通带扩展名的文件返回 true', () => {
    expect(hasFileExtension('report.md')).toBe(true);
    expect(hasFileExtension('example.kubeconfig')).toBe(true);
    expect(hasFileExtension('a.b.c')).toBe(true);
  });

  it('无扩展名的文件返回 false', () => {
    expect(hasFileExtension('README')).toBe(false);
    expect(hasFileExtension('新建文档')).toBe(false);
  });

  it('隐藏文件与以点结尾的文件视为无扩展名', () => {
    expect(hasFileExtension('.gitignore')).toBe(false);
    expect(hasFileExtension('foo.')).toBe(false);
  });

  it('只按最后一段路径判断扩展名', () => {
    expect(hasFileExtension('dir.v2/README')).toBe(false);
    expect(hasFileExtension('dir.v2/README.txt')).toBe(true);
  });
});

describe('ensureFileExtension', () => {
  it('无扩展名时补上默认扩展名', () => {
    expect(ensureFileExtension('README')).toBe('README.md');
    expect(ensureFileExtension('新建文档')).toBe('新建文档.md');
  });

  it('已有扩展名时保持原样，不追加 .md', () => {
    expect(ensureFileExtension('example.kubeconfig')).toBe('example.kubeconfig');
    expect(ensureFileExtension('report.md')).toBe('report.md');
    expect(ensureFileExtension('notes.txt')).toBe('notes.txt');
    expect(ensureFileExtension('config.yaml')).toBe('config.yaml');
  });

  it('支持指定默认扩展名', () => {
    expect(ensureFileExtension('data', 'json')).toBe('data.json');
    expect(ensureFileExtension('data.json', 'json')).toBe('data.json');
  });

  it('空字符串与纯空白原样返回', () => {
    expect(ensureFileExtension('')).toBe('');
    expect(ensureFileExtension('   ')).toBe('');
  });
});

describe('getFileExtension', () => {
  it('返回不含点号的扩展名', () => {
    expect(getFileExtension('a.md')).toBe('md');
    expect(getFileExtension('a.b.c')).toBe('c');
    expect(getFileExtension('example.kubeconfig')).toBe('kubeconfig');
  });

  it('无扩展名时返回空串', () => {
    expect(getFileExtension('README')).toBe('');
    expect(getFileExtension('.gitignore')).toBe('');
    expect(getFileExtension('foo.')).toBe('');
  });
});

describe('resolveRenameName', () => {
  it('新名字带扩展名时原样使用', () => {
    expect(resolveRenameName('b.txt', 'a.md')).toBe('b.txt');
    expect(resolveRenameName('b.md', 'a.md')).toBe('b.md');
  });

  it('新名字无扩展名时沿用原文件扩展名', () => {
    expect(resolveRenameName('b', 'a.md')).toBe('b.md');
    expect(resolveRenameName('b', 'example.kubeconfig')).toBe('b.kubeconfig');
  });

  it('原文件也没有扩展名时保持原样，不强制补 .md', () => {
    expect(resolveRenameName('b', 'README')).toBe('b');
  });

  it('空字符串原样返回', () => {
    expect(resolveRenameName('', 'a.md')).toBe('');
    expect(resolveRenameName('   ', 'a.md')).toBe('');
  });
});
