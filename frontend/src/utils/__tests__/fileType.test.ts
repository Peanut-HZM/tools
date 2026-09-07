import { describe, it, expect } from 'vitest';
import { getFileCategory, getFileLanguage, isTextFile } from '../fileType';

describe('getFileCategory', () => {
  it('识别代码文件', () => {
    expect(getFileCategory('app.py')).toBe('code');
    expect(getFileCategory('index.js')).toBe('code');
    expect(getFileCategory('styles.css')).toBe('code');
  });

  it('识别 PDF 文件', () => {
    expect(getFileCategory('document.pdf')).toBe('pdf');
  });

  it('识别 Excel 文件', () => {
    expect(getFileCategory('data.xlsx')).toBe('excel');
    expect(getFileCategory('data.csv')).toBe('excel');
  });

  it('识别 Word 文件', () => {
    expect(getFileCategory('report.docx')).toBe('word');
  });

  it('识别图片文件', () => {
    expect(getFileCategory('photo.jpg')).toBe('image');
    expect(getFileCategory('icon.png')).toBe('image');
  });

  it('识别文本文件', () => {
    expect(getFileCategory('README.md')).toBe('text');
    expect(getFileCategory('notes.txt')).toBe('text');
  });

  it('未知类型返回 unknown', () => {
    expect(getFileCategory('file.xyz')).toBe('unknown');
    expect(getFileCategory('noextension')).toBe('unknown');
  });
});

describe('getFileLanguage', () => {
  it('返回正确的编程语言', () => {
    expect(getFileLanguage('app.py')).toBe('python');
    expect(getFileLanguage('index.ts')).toBe('typescript');
    expect(getFileLanguage('styles.css')).toBe('css');
  });

  it('未知扩展名返回 plaintext', () => {
    expect(getFileLanguage('file.xyz')).toBe('plaintext');
  });
});

describe('isTextFile', () => {
  it('代码文件返回 true', () => {
    expect(isTextFile('app.py')).toBe(true);
    expect(isTextFile('index.ts')).toBe(true);
  });

  it('文本文件返回 true', () => {
    expect(isTextFile('README.md')).toBe(true);
    expect(isTextFile('notes.txt')).toBe(true);
  });

  it('非文本文件返回 false', () => {
    expect(isTextFile('document.pdf')).toBe(false);
    expect(isTextFile('photo.jpg')).toBe(false);
    expect(isTextFile('data.xlsx')).toBe(false);
  });
});
