import { describe, it, expect, vi } from 'vitest';
import { parseSSE, EventStreamClient } from '../eventStreamClient';

describe('parseSSE', () => {
  it('解析单个完整事件', () => {
    const input = 'event: text_delta\ndata: {"type":"text_delta","delta":"hello","timestamp":123}\n\n';
    const { events, remaining } = parseSSE(input);
    expect(events).toHaveLength(1);
    expect(events[0].event).toBe('text_delta');
    expect(events[0].data).toBe('{"type":"text_delta","delta":"hello","timestamp":123}');
    expect(remaining).toBe('');
  });

  it('解析多个事件（粘包）', () => {
    const input = [
      'event: text_delta',
      'data: {"type":"text_delta","delta":"a","timestamp":1}',
      '',
      'event: text_delta',
      'data: {"type":"text_delta","delta":"b","timestamp":2}',
      '',
      '',
    ].join('\n');
    const { events, remaining } = parseSSE(input);
    expect(events).toHaveLength(2);
    expect(events[0].data).toContain('"delta":"a"');
    expect(events[1].data).toContain('"delta":"b"');
    expect(remaining).toBe('');
  });

  it('处理半包：保留未完整事件在 remaining 中', () => {
    const input = 'event: text_delta\ndata: {"delta":"he';
    const { events, remaining } = parseSSE(input);
    expect(events).toHaveLength(0);
    expect(remaining).toContain('delta');
  });

  it('处理带 id 字段的事件', () => {
    const input = 'id: evt-1\nevent: turn_start\ndata: {"type":"turn_start","turn_id":"t1","timestamp":1}\n\n';
    const { events, remaining } = parseSSE(input);
    expect(events).toHaveLength(1);
    expect(events[0].id).toBe('evt-1');
    expect(events[0].event).toBe('turn_start');
    expect(remaining).toBe('');
  });

  it('忽略注释行', () => {
    const input = ': this is a comment\nevent: done\ndata: {"type":"done","timestamp":1}\n\n';
    const { events } = parseSSE(input);
    expect(events).toHaveLength(1);
    expect(events[0].event).toBe('done');
  });

  it('处理跨 chunk 的事件拼接', () => {
    // 第一个 chunk 包含一个完整事件和半个事件
    const chunk1 = 'event: text_delta\ndata: {"delta":"a","timestamp":1}\n\nevent: text_delta\ndata: {"delta":"b",';
    const { events: evts1, remaining: rem1 } = parseSSE(chunk1);
    expect(evts1).toHaveLength(1);
    expect(evts1[0].data).toContain('"delta":"a"');
    expect(rem1).toContain('"delta":"b"');

    // 第二个 chunk 完成半个事件
    const chunk2 = '"timestamp":2}\n\n';
    const { events: evts2, remaining: rem2 } = parseSSE(rem1 + chunk2);
    expect(evts2).toHaveLength(1);
    expect(evts2[0].data).toContain('"delta":"b"');
    expect(rem2).toBe('');
  });

  it('处理多行 data', () => {
    const input = 'data: line1\ndata: line2\n\n';
    const { events } = parseSSE(input);
    expect(events).toHaveLength(1);
    expect(events[0].data).toBe('line1\nline2');
  });
});

describe('EventStreamClient - done 事件', () => {
  it('收到 done 事件后触发 onDone 回调', async () => {
    const onEvent = vi.fn();
    const onDone = vi.fn();
    const client = new EventStreamClient({ onEvent, onDone });

    // 模拟 fetch 返回 SSE 流
    const sseData = [
      'event: text_delta',
      'data: {"type":"text_delta","delta":"hi","timestamp":1}',
      '',
      'event: done',
      'data: {"type":"done","timestamp":2}',
      '',
      '',
    ].join('\n');
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(sseData));
        controller.close();
      },
    });

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      body: stream,
    }));

    await client.connect('/api/test', { agent_id: 'a1' });
    expect(onEvent).toHaveBeenCalledTimes(2);
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(client.getState()).toBe('done');

    vi.unstubAllGlobals();
  });

  it('cancel 中止连接', async () => {
    const onEvent = vi.fn();
    const onError = vi.fn();
    const client = new EventStreamClient({ onEvent, onError });

    // 模拟一个可中断的流 — 当 AbortSignal 触发时 reader.read 抛错
    let readerReject: ((err: Error) => void) | null = null;
    const stream = new ReadableStream({
      start() {
        // reader 永远不主动 resolve，等 abort 触发 reject
      },
    });

    // 覆盖 stream 的 getReader，使其在 abort 时抛错
    const originalGetReader = stream.getReader.bind(stream);
    vi.spyOn(stream, 'getReader').mockImplementation(() => {
      const reader = originalGetReader();
      const originalRead = reader.read.bind(reader);
      let aborted = false;
      return {
        ...reader,
        read: () => {
          if (aborted) return Promise.reject(new DOMException('Aborted', 'AbortError'));
          return new Promise((resolve, reject) => {
            readerReject = reject;
            // 永不 resolve，模拟挂起的流
          });
        },
        cancel: () => Promise.resolve(),
        releaseLock: () => {},
        closed: Promise.resolve(),
      } as any;
    });

    vi.stubGlobal('fetch', vi.fn().mockImplementation((_url: string, init: any) => {
      // 监听 abort
      init?.signal?.addEventListener('abort', () => {
        readerReject?.(new DOMException('Aborted', 'AbortError'));
      });
      return Promise.resolve({
        ok: true,
        body: stream,
      });
    }));

    const connectPromise = client.connect('/api/test', {});

    // 等待 fetch 被调用（流开始读取）
    await new Promise((r) => setTimeout(r, 50));

    client.cancel();
    expect(client.getState()).toBe('cancelled');

    await connectPromise;
    expect(onError).not.toHaveBeenCalled();

    vi.unstubAllGlobals();
  });
});

describe('EventStreamClient - 重连 bug 修复', () => {
  it('test_reconnect_resets_sseBuffer: 重连时清空 sseBuffer，避免半包拼接', async () => {
    const onEvent = vi.fn();
    const onError = vi.fn();
    const client = new EventStreamClient({ onEvent, onError, maxRetries: 1, retryInterval: 30 });

    const encoder = new TextEncoder();
    let fetchCount = 0;

    vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => {
      fetchCount++;
      if (fetchCount === 1) {
        // 第一次 fetch 失败；在抛错前污染 sseBuffer，模拟前次连接残留的半包
        (client as any).sseBuffer = 'event: text_delta\ndata: {"delta":"stale';
        throw new Error('network error');
      }
      // 第二次连接（重连）：发送一个完整事件
      const fullEvent = 'event: text_delta\ndata: {"type":"text_delta","delta":"fresh","timestamp":99}\n\n';
      const stream = new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(fullEvent));
          controller.close();
        },
      });
      return { ok: true, body: stream };
    }));

    await client.connect('/api/test', { agent_id: 'a1' });

    // 等待重连定时器触发并完成第二次连接
    await new Promise((r) => setTimeout(r, 150));

    // fetch 应被调用两次（第一次失败，第二次成功）
    expect(fetchCount).toBe(2);
    // 应该只收到一个事件（来自重连后的完整事件）
    // 如果 sseBuffer 没被清空，残留的半包 'stale' 会与新数据拼接，导致 JSON 解析失败，事件类型变为 custom
    expect(onEvent).toHaveBeenCalledTimes(1);
    const receivedEvent = onEvent.mock.calls[0][0];
    expect(receivedEvent.type).toBe('text_delta');
    expect(receivedEvent.delta).toBe('fresh');

    vi.unstubAllGlobals();
  });

  it('test_cancel_clears_reconnect_timer: cancel 清除待执行的 reconnect timer', async () => {
    const onEvent = vi.fn();
    const onError = vi.fn();
    const client = new EventStreamClient({ onEvent, onError, maxRetries: 3, retryInterval: 500 });

    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')));

    // 发起连接，会立即进入 catch 并设置 reconnect timer（500ms 后重试）
    const connectPromise = client.connect('/api/test', {});
    await connectPromise;

    // 此时 state 应该仍是 connecting（因为 fetch reject 后进入 catch 设置了 timer）
    // 在 timer 触发前调用 cancel
    expect(client.getState()).not.toBe('done');
    client.cancel();
    expect(client.getState()).toBe('cancelled');

    // 等待超过 retryInterval，确认 cancel 后不会触发重连（fetch 不会再被调用）
    const fetchCallCountAfterCancel = (vi.mocked(fetch).mock.calls.length);
    await new Promise((r) => setTimeout(r, 700));
    expect(vi.mocked(fetch).mock.calls.length).toBe(fetchCallCountAfterCancel);

    // onError 也不应被调用（因为 cancel 阻断了重连链）
    expect(onError).not.toHaveBeenCalled();

    vi.unstubAllGlobals();
  });
});
