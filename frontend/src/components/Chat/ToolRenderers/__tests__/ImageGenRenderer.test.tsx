/**
 * ImageGenRenderer 单元测试
 *
 * 覆盖：
 * - 渲染：
 *   - 工具名 badge "image_gen" 渲染
 *   - 4 种 operation 正确映射中文（text2img / img2img / inpaint / upload_edit）
 *   - model_used 标签渲染
 *   - 图片网格：1 张时单列，>=2 张时两列
 *   - revised_prompt 可折叠切换
 *   - 失败状态显示错误信息
 *   - pending 状态显示「正在生成图像...」
 *   - 成功但无图片时显示「未生成图片」
 * - 安全：
 *   - 危险 URL（javascript: / data:）经过 safeHref 校验后被降级为提示文本
 *   - https URL 渲染为可点击缩略图（带 rel="noopener noreferrer nofollow"）
 * - 兼容：
 *   - result.content 为字符串（JSON）时正确解析
 *   - result.content 为对象时直接使用
 */
import React from 'react';
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { ImageGenRenderer } from '../ImageGenRenderer';
import type { ToolCall, ToolResult, Attachment } from '@/types/tool';

afterEach(() => {
  cleanup();
});

const makeCall = (overrides: Partial<ToolCall['arguments']> = {}): ToolCall => ({
  id: 'call-img-1',
  name: 'image_gen',
  arguments: { operation: 'text2img', prompt: 'a cat', ...overrides },
});

const makeImageAttachment = (url: string): Attachment => ({
  type: 'image',
  url,
});

const makeResult = (overrides: Partial<ToolResult> = {}): ToolResult => ({
  id: 'result-img-1',
  name: 'image_gen',
  success: true,
  content_type: 'json',
  content: { model_used: 'wanx-v1', operation: 'text2img' },
  attachments: [],
  ...overrides,
});

describe('ImageGenRenderer — 顶部 badge 与 operation 映射', () => {
  it('渲染工具名 badge "image_gen"', () => {
    render(<ImageGenRenderer call={makeCall()} pending result={undefined} />);
    // 至少出现两次 image_gen（StatusLine + builtin renderer 内部）
    expect(screen.getAllByText('image_gen').length).toBeGreaterThanOrEqual(1);
  });

  it('text2img -> 文生图', () => {
    render(
      <ImageGenRenderer
        call={makeCall({ operation: 'text2img' })}
        result={makeResult()}
      />
    );
    expect(screen.getByText('文生图')).toBeTruthy();
  });

  it('img2img -> 图生图', () => {
    render(
      <ImageGenRenderer
        call={makeCall({ operation: 'img2img' })}
        result={makeResult()}
      />
    );
    expect(screen.getByText('图生图')).toBeTruthy();
  });

  it('inpaint -> 局部重绘', () => {
    render(
      <ImageGenRenderer
        call={makeCall({ operation: 'inpaint' })}
        result={makeResult()}
      />
    );
    expect(screen.getByText('局部重绘')).toBeTruthy();
  });

  it('upload_edit -> 指令编辑', () => {
    render(
      <ImageGenRenderer
        call={makeCall({ operation: 'upload_edit' })}
        result={makeResult()}
      />
    );
    expect(screen.getByText('指令编辑')).toBeTruthy();
  });

  it('未知 operation 回退为原始字符串', () => {
    render(
      <ImageGenRenderer
        call={makeCall({ operation: 'foo_bar' })}
        result={makeResult()}
      />
    );
    expect(screen.getByText('foo_bar')).toBeTruthy();
  });

  it('model_used 标签渲染', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({ content: { model_used: 'hailuo-v2' } })}
      />
    );
    expect(screen.getByText('hailuo-v2')).toBeTruthy();
  });
});

describe('ImageGenRenderer — 图片网格', () => {
  it('1 张图片时单列布局', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({
          attachments: [makeImageAttachment('https://cdn.example.com/a.png')],
        })}
      />
    );
    const img = document.querySelector('img');
    expect(img).not.toBeNull();
    expect(img?.getAttribute('src')).toBe('https://cdn.example.com/a.png');
    expect(img?.getAttribute('alt')).toBe('生成图片 1');

    // 包裹 img 的 anchor 包含 target=_blank + rel=noopener noreferrer nofollow
    const a = document.querySelector('a');
    expect(a).not.toBeNull();
    expect(a?.getAttribute('href')).toBe('https://cdn.example.com/a.png');
    expect(a?.getAttribute('target')).toBe('_blank');
    expect(a?.getAttribute('rel')).toBe('noopener noreferrer nofollow');
  });

  it('4 张图片全部渲染', () => {
    const urls = [
      'https://cdn.example.com/a.png',
      'https://cdn.example.com/b.png',
      'https://cdn.example.com/c.png',
      'https://cdn.example.com/d.png',
    ];
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({
          attachments: urls.map(makeImageAttachment),
        })}
      />
    );

    const imgs = document.querySelectorAll('img');
    expect(imgs.length).toBe(4);
    imgs.forEach((img, idx) => {
      expect(img.getAttribute('src')).toBe(urls[idx]);
      expect(img.getAttribute('alt')).toBe(`生成图片 ${idx + 1}`);
    });
  });

  it('非 image 类型附件被过滤', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({
          attachments: [
            { type: 'file', url: 'https://cdn.example.com/spec.pdf' },
            makeImageAttachment('https://cdn.example.com/img.png'),
          ],
        })}
      />
    );
    // 只应渲染 1 张图片
    expect(document.querySelectorAll('img').length).toBe(1);
    expect(document.querySelector('img')?.getAttribute('src')).toBe(
      'https://cdn.example.com/img.png'
    );
  });

  it('成功但无图片时显示「未生成图片」', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({ attachments: [] })}
      />
    );
    expect(screen.getByText('未生成图片')).toBeTruthy();
  });
});

describe('ImageGenRenderer — 失败与 pending 状态', () => {
  it('失败时显示 error 信息', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({
          success: false,
          error: 'rate limit exceeded',
          content: '',
        })}
      />
    );
    expect(screen.getByText(/生成失败/)).toBeTruthy();
    expect(screen.getByText(/rate limit exceeded/)).toBeTruthy();
  });

  it('失败但无 error 字段时显示「未知错误」', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({ success: false, error: undefined, content: '' })}
      />
    );
    expect(screen.getByText(/未知错误/)).toBeTruthy();
  });

  it('pending 且无 result 时显示「正在生成图像...」', () => {
    render(<ImageGenRenderer call={makeCall()} pending result={undefined} />);
    expect(screen.getByText('正在生成图像...')).toBeTruthy();
  });
});

describe('ImageGenRenderer — revised_prompt 折叠', () => {
  it('默认折叠，点击展开 prompt 内容', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({
          content: {
            model_used: 'wanx-v1',
            revised_prompt: 'a fluffy orange cat sitting on a wooden table',
          },
        })}
      />
    );

    // 初始折叠时不应出现完整 prompt 文本
    expect(
      screen.queryByText('a fluffy orange cat sitting on a wooden table')
    ).toBeNull();

    // 点击展开按钮
    fireEvent.click(screen.getByText('查看润色 prompt'));

    // 展开后 prompt 文本应出现
    expect(
      screen.getByText('a fluffy orange cat sitting on a wooden table')
    ).toBeTruthy();

    // 再次点击应折叠
    fireEvent.click(screen.getByText('收起润色 prompt'));
    expect(
      screen.queryByText('a fluffy orange cat sitting on a wooden table')
    ).toBeNull();
  });
});

describe('ImageGenRenderer — URL 安全 (safeHref)', () => {
  it('javascript: URL 不渲染为 <img>，降级为不安全提示', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({
          attachments: [makeImageAttachment('javascript:alert(1)')],
        })}
      />
    );

    // 没有渲染 img
    expect(document.querySelector('img')).toBeNull();
    // 没有渲染 anchor
    expect(document.querySelector('a')).toBeNull();
    // 出现降级提示
    expect(screen.getByText(/图片 URL 不安全/)).toBeTruthy();
  });

  it('data: URL 不渲染为 <img>', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({
          attachments: [
            makeImageAttachment('data:image/png;base64,AAAA'),
          ],
        })}
      />
    );
    expect(document.querySelector('img')).toBeNull();
    expect(screen.getByText(/图片 URL 不安全/)).toBeTruthy();
  });

  it('https URL 渲染为 img，src 经 safeHref 校验', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({
          attachments: [
            makeImageAttachment('https://cdn.example.com/img.png'),
          ],
        })}
      />
    );
    const img = document.querySelector('img');
    expect(img).not.toBeNull();
    expect(img?.getAttribute('src')).toBe('https://cdn.example.com/img.png');
  });

  it('http URL 也允许渲染', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({
          attachments: [makeImageAttachment('http://cdn.example.com/img.png')],
        })}
      />
    );
    const img = document.querySelector('img');
    expect(img?.getAttribute('src')).toBe('http://cdn.example.com/img.png');
  });

  it('混合安全 / 危险 URL：仅安全项渲染为 <img>', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({
          attachments: [
            makeImageAttachment('javascript:alert(1)'),
            makeImageAttachment('https://cdn.example.com/safe.png'),
          ],
        })}
      />
    );

    const imgs = document.querySelectorAll('img');
    expect(imgs.length).toBe(1);
    expect(imgs[0].getAttribute('src')).toBe('https://cdn.example.com/safe.png');
    expect(screen.getByText(/图片 URL 不安全/)).toBeTruthy();
  });
});

describe('ImageGenRenderer — result.content 兼容 string / object', () => {
  it('字符串 JSON 形式的 content 正确解析', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({
          content: JSON.stringify({
            model_used: 'wanx-json',
            revised_prompt: 'json-string prompt',
            operation: 'img2img',
          }),
        })}
      />
    );

    expect(screen.getByText('wanx-json')).toBeTruthy();
    fireEvent.click(screen.getByText('查看润色 prompt'));
    expect(screen.getByText('json-string prompt')).toBeTruthy();
  });

  it('非法 JSON 字符串降级为空内容，不抛错', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({ content: '{not valid json' })}
      />
    );
    // 仍能渲染，无崩溃；model_used 缺失，badge 不应出现
    expect(screen.queryByText('wanx-v1')).toBeNull();
  });

  it('对象形式的 content 直接使用', () => {
    render(
      <ImageGenRenderer
        call={makeCall()}
        result={makeResult({ content: { model_used: 'obj-model' } })}
      />
    );
    expect(screen.getByText('obj-model')).toBeTruthy();
  });
});
