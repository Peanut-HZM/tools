/**
 * imageGenerationApi.chatGenerate backend 参数 测试
 *
 * 验证 chatGenerate 在调用时会自动从 BackendSwitch.getBackend() 读取后端选择
 * 并追加到 FormData 中：
 *   - 默认（localStorage 无值）→ backend='selfdev'
 *   - 切换到 dify → backend='dify'
 */

import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest';
import { chatGenerate } from '../imageGenerationApi';
import { setBackend } from '../../components/Tools/ImageGeneration/BackendSwitch';

describe('chatGenerate backend param', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    localStorage.clear();

    // mock fetch，捕获实际发送到后端的 FormData 以便断言
    fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => {
      return new Response(
        JSON.stringify({
          conversation_id: 'conv-1',
          answer: 'ok',
          image_urls: [],
          status: 'asking',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('默认带 backend=selfdev', async () => {
    await chatGenerate('text2img', 'a cat', null);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const body = fetchMock.mock.calls[0][1]?.body as FormData;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get('backend')).toBe('selfdev');
    expect(body.get('operation')).toBe('text2img');
    expect(body.get('prompt')).toBe('a cat');
  });

  it('切换到 dify 后带 backend=dify', async () => {
    setBackend('dify');

    await chatGenerate('text2img', 'a dog', null);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const body = fetchMock.mock.calls[0][1]?.body as FormData;
    expect(body.get('backend')).toBe('dify');
  });

  it('切回 selfdev 后带 backend=selfdev', async () => {
    setBackend('dify');
    setBackend('selfdev');

    await chatGenerate('text2img', 'a bird', null);

    const body = fetchMock.mock.calls[0][1]?.body as FormData;
    expect(body.get('backend')).toBe('selfdev');
  });

  it('切换后端不影响其他 FormData 字段', async () => {
    setBackend('dify');

    await chatGenerate(
      'inpaint',
      '修复',
      'conv-abc',
      { size: '1024x1024', model_preference: 'auto' },
    );

    const body = fetchMock.mock.calls[0][1]?.body as FormData;
    expect(body.get('backend')).toBe('dify');
    expect(body.get('operation')).toBe('inpaint');
    expect(body.get('prompt')).toBe('修复');
    expect(body.get('conversation_id')).toBe('conv-abc');
    expect(body.get('size')).toBe('1024x1024');
    expect(body.get('model_preference')).toBe('auto');
  });
});
