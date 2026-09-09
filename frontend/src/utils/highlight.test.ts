/**
 * 高亮工具函数测试
 *
 * 验证：
 * - escapeRegex 正确转义正则特殊字符
 * - highlightText 正确高亮匹配的文本
 * - 边界情况处理（空查询、空文本、无匹配、大小写等）
 */
import { describe, it, expect } from 'vitest';
import { escapeRegex, highlightText } from './highlight';
import { isValidElement } from 'react';

describe('escapeRegex', () => {
  it('转义点号', () => {
    expect(escapeRegex('foo.bar')).toBe('foo\\.bar');
  });

  it('转义多个特殊字符', () => {
    expect(escapeRegex('a.*+?^${}()|[]\\b')).toBe(
      'a\\.\\*\\+\\?\\^\\$\\{\\}\\(\\)\\|\\[\\]\\\\b'
    );
  });

  it('无特殊字符时保持不变', () => {
    expect(escapeRegex('hello world')).toBe('hello world');
  });

  it('空字符串返回空', () => {
    expect(escapeRegex('')).toBe('');
  });
});

describe('highlightText', () => {
  it('空查询返回原文本', () => {
    expect(highlightText('hello world', '')).toBe('hello world');
  });

  it('无匹配时返回原文本', () => {
    expect(highlightText('hello world', 'xyz')).toBe('hello world');
  });

  it('单个匹配时返回数组，包含 <mark> 包裹的匹配', () => {
    const result = highlightText('hello world', 'world') as Array<string | React.ReactElement>;
    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBe(3); // ['hello ', <mark>world</mark>, '']
    expect(result[0]).toBe('hello ');
    expect(isValidElement(result[1])).toBe(true);
    const markEl = result[1] as React.ReactElement;
    expect(markEl.type).toBe('mark');
    expect(markEl.props.children).toBe('world');
    expect(markEl.props.className).toBe('search-highlight');
  });

  it('多个匹配时所有匹配都被高亮', () => {
    const result = highlightText('foo bar foo', 'foo') as Array<string | React.ReactElement>;
    expect(Array.isArray(result)).toBe(true);

    // split 带捕获组返回 ['', 'foo', ' bar ', 'foo', '']
    // 匹配项在索引 1, 3（奇数）
    const marks = result.filter(
      (el) => isValidElement(el) && (el as React.ReactElement).type === 'mark'
    );
    expect(marks.length).toBe(2); // 2 个 'foo' 都被高亮
  });

  it('大小写不敏感匹配', () => {
    const result = highlightText('Hello HELLO hello', 'hello') as Array<string | React.ReactElement>;
    const marks = result.filter(
      (el) => isValidElement(el) && (el as React.ReactElement).type === 'mark'
    );
    expect(marks.length).toBe(3);
  });

  it('特殊字符不报错且能匹配', () => {
    expect(() => highlightText('foo.bar baz', 'foo.bar')).not.toThrow();
    const result = highlightText('foo.bar baz', 'foo.bar') as Array<string | React.ReactElement>;
    const marks = result.filter(
      (el) => isValidElement(el) && (el as React.ReactElement).type === 'mark'
    );
    expect(marks.length).toBe(1);
    expect((marks[0] as React.ReactElement).props.children).toBe('foo.bar');
  });

  it('空文本返回原文本', () => {
    expect(highlightText('', 'hello')).toBe('');
  });

  it('content 匹配中正确高亮', () => {
    const line = "SELECT * FROM users WHERE name = 'alice'";
    const result = highlightText(line, 'users') as Array<string | React.ReactElement>;
    const marks = result.filter(
      (el) => isValidElement(el) && (el as React.ReactElement).type === 'mark'
    );
    expect(marks.length).toBe(1);
    expect((marks[0] as React.ReactElement).props.children).toBe('users');
  });

  it('文件名匹配中正确高亮', () => {
    const result = highlightText('README.md', 'readme') as Array<string | React.ReactElement>;
    const marks = result.filter(
      (el) => isValidElement(el) && (el as React.ReactElement).type === 'mark'
    );
    expect(marks.length).toBe(1);
    expect((marks[0] as React.ReactElement).props.children).toBe('README');
  });
});
