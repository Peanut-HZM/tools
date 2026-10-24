import { beforeEach, describe, expect, it, vi } from 'vitest';
import { conversationApi } from './conversationApi';
import { authedFetch } from '../api/http';

vi.mock('../api/http', () => ({
  authedFetch: vi.fn((_input: RequestInfo | URL, init?: RequestInit) => (
    new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => {
        reject(new DOMException('请求已取消', 'AbortError'));
      });
    })
  )),
}));

vi.mock('../api/authApi', () => ({
  getAuthToken: vi.fn(() => null),
}));

describe('conversationApi.sendMessageStream', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('取消当前流式请求且不触发任何消息回调', async () => {
    const callbacks = {
      onChunk: vi.fn(),
      onDone: vi.fn(),
      onError: vi.fn(),
    };
    const cancel = conversationApi.sendMessageStream(
      'conversation-id',
      { content: '测试消息' },
      callbacks,
    );

    const requestOptions = vi.mocked(authedFetch).mock.calls[0][1];
    expect(requestOptions?.signal?.aborted).toBe(false);

    cancel();

    expect(requestOptions?.signal?.aborted).toBe(true);
    await new Promise<void>((resolve) => queueMicrotask(resolve));
    expect(callbacks.onChunk).not.toHaveBeenCalled();
    expect(callbacks.onDone).not.toHaveBeenCalled();
    expect(callbacks.onError).not.toHaveBeenCalled();
  });
});
