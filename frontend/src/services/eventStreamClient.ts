// SSE 事件流客户端
// 用于接收 harness Agent 的流式事件
// 设计为 UI 无关（不依赖 React），可在 Node / 浏览器环境使用

import type { AgentEvent } from '../types/event';

export interface EventStreamClientOptions {
  /** 收到事件回调 */
  onEvent: (event: AgentEvent) => void;
  /** 流结束回调（收到 done 事件或服务端关闭流） */
  onDone?: () => void;
  /** 错误回调 */
  onError?: (error: Error) => void;
  /** 连接状态变更回调 */
  onStateChange?: (state: EventStreamState) => void;
  /** 重连前的 Last-Event-ID（用于断线续传） */
  lastEventId?: string;
  /** 重连尝试次数，默认 0（不重连） */
  maxRetries?: number;
  /** 重连间隔（ms），默认 1000 */
  retryInterval?: number;
}

export type EventStreamState = 'idle' | 'connecting' | 'streaming' | 'done' | 'error' | 'cancelled';

/**
 * 解析 SSE 文本块为事件数组。
 * 处理粘包/半包：通过维护 buffer 正确处理跨 chunk 的事件。
 * 返回解析出的事件数组和未消费完的剩余 buffer。
 */
export function parseSSE(buffer: string): { events: Array<{ id?: string; event?: string; data: string }>; remaining: string } {
  const events: Array<{ id?: string; event?: string; data: string }> = [];
  // SSE 规范：事件之间用空行分隔（\n\n 或 \r\n\r\n）
  // 统一使用 \n 分割，先按双换行切块
  const normalized = buffer.replace(/\r\n/g, '\n');
  const blocks = normalized.split(/\n\n/);

  // 最后一个块可能不完整（没有以 \n\n 结尾），保留为剩余 buffer
  const remaining = blocks.pop() ?? '';

  for (const block of blocks) {
    if (!block.trim()) continue;
    let eventId: string | undefined;
    let eventType: string | undefined;
    const dataLines: string[] = [];

    for (const line of block.split('\n')) {
      if (!line) continue;
      if (line.startsWith('id:')) {
        eventId = line.slice(3).trim();
      } else if (line.startsWith('event:')) {
        eventType = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart());
      }
      // 忽略以 ':' 开头的注释行
    }

    if (dataLines.length > 0) {
      events.push({
        id: eventId,
        event: eventType,
        data: dataLines.join('\n'),
      });
    }
  }

  return { events, remaining };
}

export class EventStreamClient {
  private abortController: AbortController | null = null;
  private state: EventStreamState = 'idle';
  private retryCount = 0;
  private lastEventId: string | undefined;
  private sseBuffer = '';
  private url: string | null = null;
  private body: any = null;
  private headers: Record<string, string> = {};

  constructor(private readonly options: EventStreamClientOptions) {
    this.lastEventId = options.lastEventId;
  }

  /**
   * 连接到 SSE 流
   * 使用 POST 方法发送 body（与 harness API 对齐）
   */
  async connect(url: string, body: any, headers: Record<string, string> = {}): Promise<void> {
    this.url = url;
    this.body = body;
    this.headers = headers;
    this.retryCount = 0;
    await this.doConnect();
  }

  private async doConnect(): Promise<void> {
    if (!this.url) return;
    this.abortController = new AbortController();
    this.setState('connecting');

    try {
      const requestHeaders: Record<string, string> = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        ...this.headers,
      };
      if (this.lastEventId) {
        requestHeaders['Last-Event-ID'] = this.lastEventId;
      }

      const response = await fetch(this.url, {
        method: 'POST',
        headers: requestHeaders,
        body: JSON.stringify(this.body),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`SSE 连接失败: HTTP ${response.status} ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('SSE 连接失败: 响应体为空');
      }

      this.setState('streaming');
      this.retryCount = 0;
      await this.readStream(response.body);
    } catch (error) {
      if (this.state === 'cancelled') {
        return;
      }
      const err = error instanceof Error ? error : new Error(String(error));
      // 尝试重连
      const maxRetries = this.options.maxRetries ?? 0;
      if (this.retryCount < maxRetries) {
        this.retryCount++;
        const interval = this.options.retryInterval ?? 1000;
        setTimeout(() => {
          if (this.state !== 'cancelled') {
            this.doConnect();
          }
        }, interval);
      } else {
        this.setState('error');
        this.options.onError?.(err);
      }
    }
  }

  private async readStream(body: ReadableStream<Uint8Array>): Promise<void> {
    const reader = body.getReader();
    const decoder = new TextDecoder('utf-8');

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          this.handleStreamEnd();
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        this.sseBuffer += chunk;

        const { events, remaining } = parseSSE(this.sseBuffer);
        this.sseBuffer = remaining;

        for (const evt of events) {
          if (evt.id) {
            this.lastEventId = evt.id;
          }
          this.handleSSEEvent(evt);
        }

        if (this.state === 'done' || this.state === 'cancelled') {
          break;
        }
      }
    } catch (error) {
      if (this.state === 'cancelled') {
        return;
      }
      const err = error instanceof Error ? error : new Error(String(error));
      this.setState('error');
      this.options.onError?.(err);
    }
  }

  private handleSSEEvent(evt: { id?: string; event?: string; data: string }): void {
    let agentEvent: AgentEvent;

    // 如果 event 字段指定了类型，用它；否则从 data 里解析
    const eventType = evt.event;

    try {
      const parsed = JSON.parse(evt.data);
      // 如果 data 已经是完整的 AgentEvent（含 type 字段），直接使用
      if (parsed && typeof parsed === 'object' && 'type' in parsed) {
        agentEvent = parsed as AgentEvent;
      } else {
        // 否则用 event 字段作为 type 构造事件
        agentEvent = {
          type: (eventType ?? 'custom') as AgentEvent['type'],
          ...parsed,
          timestamp: parsed?.timestamp ?? Date.now(),
        } as AgentEvent;
      }
    } catch {
      // data 不是 JSON，按纯文本 custom 事件处理
      agentEvent = {
        type: 'custom',
        name: eventType ?? 'unknown',
        data: evt.data,
        timestamp: Date.now(),
      };
    }

    this.options.onEvent(agentEvent);

    // done 事件自动结束
    if (agentEvent.type === 'done') {
      this.handleStreamEnd();
    }
  }

  private handleStreamEnd(): void {
    if (this.state === 'done' || this.state === 'cancelled') return;
    this.setState('done');
    this.options.onDone?.();
  }

  /** 取消连接 */
  cancel(): void {
    this.setState('cancelled');
    this.abortController?.abort();
    this.abortController = null;
  }

  /** 获取当前状态 */
  getState(): EventStreamState {
    return this.state;
  }

  /** 获取最新的 Last-Event-ID */
  getLastEventId(): string | undefined {
    return this.lastEventId;
  }

  private setState(state: EventStreamState): void {
    this.state = state;
    this.options.onStateChange?.(state);
  }
}
