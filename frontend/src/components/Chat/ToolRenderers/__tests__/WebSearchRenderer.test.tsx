/**
 * WebSearchRenderer 单元测试
 *
 * 覆盖：
 * - safeHref helper:
 *   - http/https URL 接受
 *   - javascript: / data: / vbscript: / file: 等危险 scheme 拒绝
 *   - 相对 URL 解析为绝对 URL
 *   - URL 中的 username/password 被清除
 *   - 非法字符串返回 null
 * - 渲染:
 *   - 危险 URL 不渲染为 <a>，降级为纯文本
 *   - http/https URL 渲染为 <a>，带 rel="noopener noreferrer nofollow"
 *   - 相对 URL 被解析为绝对 URL 后渲染
 */
import React from 'react';
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { WebSearchRenderer, safeHref } from '../WebSearchRenderer';
import type { ToolCall, ToolResult } from '@/types/tool';

afterEach(() => {
  cleanup();
});

const makeCall = (): ToolCall => ({
  id: 'call-1',
  name: 'web_search',
  arguments: { query: 'claude opus' },
});

const makeResult = (results: unknown[]): ToolResult => ({
  id: 'result-1',
  name: 'web_search',
  success: true,
  content_type: 'json',
  content: { results },
  attachments: [],
});

describe('safeHref helper', () => {
  it('接受 http URL', () => {
    expect(safeHref('http://example.com/page')).toBe('http://example.com/page');
  });

  it('接受 https URL', () => {
    expect(safeHref('https://example.com/article?id=1')).toBe(
      'https://example.com/article?id=1'
    );
  });

  it('拒绝 javascript: scheme', () => {
    expect(safeHref('javascript:alert(1)')).toBeNull();
  });

  it('拒绝带大小写绕过的 javascript: scheme', () => {
    expect(safeHref('JavaScript:alert(1)')).toBeNull();
    expect(safeHref('JAVASCRIPT:alert(1)')).toBeNull();
  });

  it('拒绝 data: scheme', () => {
    expect(safeHref('data:text/html,<script>alert(1)</script>')).toBeNull();
  });

  it('拒绝 vbscript: scheme', () => {
    expect(safeHref('vbscript:msgbox(1)')).toBeNull();
  });

  it('拒绝 file: scheme', () => {
    expect(safeHref('file:///etc/passwd')).toBeNull();
  });

  it('将相对 URL 解析为基于 https://invalid.local 的绝对 URL', () => {
    // URL 解析后 protocol 是 https（因为 base 是 https://invalid.local）
    const r = safeHref('/article/42');
    expect(r).not.toBeNull();
    expect(r).toMatch(/^https:\/\/invalid\.local\/article\/42$/);
  });

  it('清除 URL 中的 username 和 password', () => {
    const r = safeHref('https://user:pass@example.com/path');
    expect(r).not.toBeNull();
    // userinfo 应被剥离
    expect(r).not.toMatch(/user/);
    expect(r).not.toMatch(/pass/);
    expect(r).toMatch(/example\.com/);
  });

  it('非法字符串（无法解析为 URL）返回 null', () => {
    // 包含非法字符的字符串无法被 URL 解析
    expect(safeHref('http://[invalid')).toBeNull();
  });
});

describe('WebSearchRenderer 渲染', () => {
  it('javascript: URL 不渲染为链接，降级为纯文本', () => {
    render(
      <WebSearchRenderer
        call={makeCall()}
        result={makeResult([
          { title: '点我', url: 'javascript:alert(1)', snippet: 'xss' },
        ])}
      />
    );

    // 不应渲染 anchor
    expect(document.querySelector('a')).toBeNull();
    // title 应作为纯文本出现
    expect(screen.getByText('点我')).toBeTruthy();
    expect(screen.getByText('xss')).toBeTruthy();
  });

  it('data: URL 不渲染为链接', () => {
    render(
      <WebSearchRenderer
        call={makeCall()}
        result={makeResult([
          { title: 'A', url: 'data:text/html,<script>alert(1)</script>', snippet: '' },
        ])}
      />
    );
    expect(document.querySelector('a')).toBeNull();
    expect(screen.getByText('A')).toBeTruthy();
  });

  it('https URL 渲染为带 rel="noopener noreferrer nofollow" 的链接', () => {
    render(
      <WebSearchRenderer
        call={makeCall()}
        result={makeResult([
          { title: 'Example', url: 'https://example.com/foo', snippet: 'desc' },
        ])}
      />
    );

    const a = document.querySelector('a');
    expect(a).not.toBeNull();
    expect(a?.getAttribute('href')).toBe('https://example.com/foo');
    expect(a?.getAttribute('target')).toBe('_blank');
    expect(a?.getAttribute('rel')).toBe('noopener noreferrer nofollow');
    expect(a?.textContent).toBe('Example');
  });

  it('http URL 同样被允许', () => {
    render(
      <WebSearchRenderer
        call={makeCall()}
        result={makeResult([
          { title: 'Plain', url: 'http://example.org/' },
        ])}
      />
    );
    const a = document.querySelector('a');
    expect(a?.getAttribute('href')).toBe('http://example.org/');
  });

  it('相对 URL 被解析为绝对 URL 后渲染', () => {
    render(
      <WebSearchRenderer
        call={makeCall()}
        result={makeResult([{ title: 'Rel', url: '/docs/intro' }])}
      />
    );
    const a = document.querySelector('a');
    expect(a).not.toBeNull();
    // 应解析为 https://invalid.local/docs/intro
    expect(a?.getAttribute('href')).toBe('https://invalid.local/docs/intro');
  });

  it('URL 中包含 userinfo 时被剥离', () => {
    render(
      <WebSearchRenderer
        call={makeCall()}
        result={makeResult([
          { title: 'Cred', url: 'https://user:pass@example.com/x' },
        ])}
      />
    );
    const a = document.querySelector('a');
    expect(a).not.toBeNull();
    const href = a?.getAttribute('href') ?? '';
    expect(href).not.toMatch(/user/);
    expect(href).not.toMatch(/pass/);
    expect(href).toMatch(/example\.com/);
  });

  it('仅有 URL 无 title 时，危险 URL 渲染为纯文本 span（无 anchor）', () => {
    render(
      <WebSearchRenderer
        call={makeCall()}
        result={makeResult([
          { url: 'javascript:alert(1)' },
        ])}
      />
    );
    expect(document.querySelector('a')).toBeNull();
    // 危险 URL 应降级为文本
    expect(screen.getByText('javascript:alert(1)')).toBeTruthy();
  });

  it('仅有 URL 无 title 时，安全 URL 渲染为 anchor', () => {
    render(
      <WebSearchRenderer
        call={makeCall()}
        result={makeResult([
          { url: 'https://example.org/' },
        ])}
      />
    );
    const a = document.querySelector('a');
    expect(a?.getAttribute('href')).toBe('https://example.org/');
    expect(a?.getAttribute('rel')).toBe('noopener noreferrer nofollow');
    expect(a?.textContent).toBe('https://example.org/');
  });

  it('多条结果中混合危险与安全 URL，仅安全项渲染为链接', () => {
    render(
      <WebSearchRenderer
        call={makeCall()}
        result={makeResult([
          { title: 'Bad', url: 'javascript:alert(1)' },
          { title: 'Good', url: 'https://example.com/safe' },
        ])}
      />
    );

    const anchors = document.querySelectorAll('a');
    expect(anchors.length).toBe(1);
    expect(anchors[0].getAttribute('href')).toBe('https://example.com/safe');
    expect(anchors[0].textContent).toBe('Good');

    // 'Bad' title 仍作为纯文本展示
    expect(screen.getByText('Bad')).toBeTruthy();
  });
});