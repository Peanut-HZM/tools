// Agent 事件类型定义
// discriminated union：通过 type 字段区分 14 种事件
// 所有事件都包含 timestamp（毫秒时间戳）

import type { ToolCall, ToolResult } from './tool';

export interface TurnStartEvent {
  type: 'turn_start';
  turn_id: string;
  timestamp: number;
}

export interface TextDeltaEvent {
  type: 'text_delta';
  delta: string;
  timestamp: number;
}

export interface TextCompleteEvent {
  type: 'text_complete';
  full_text: string;
  timestamp: number;
}

export interface ThinkingDeltaEvent {
  type: 'thinking_delta';
  delta: string;
  timestamp: number;
}

export interface ToolCallStartEvent {
  type: 'tool_call_start';
  tool_call: ToolCall;
  timestamp: number;
}

export interface ToolCallProgressEvent {
  type: 'tool_call_progress';
  tool_call_id: string;
  progress: string;
  timestamp: number;
}

export interface ToolResultEvent {
  type: 'tool_result';
  result: ToolResult;
  timestamp: number;
}

export interface ImageGeneratedEvent {
  type: 'image_generated';
  url: string;
  prompt?: string;
  timestamp: number;
}

export interface HandoffEvent {
  type: 'handoff';
  target_agent_id: string;
  target_agent_name: string;
  reason?: string;
  timestamp: number;
}

export interface GuardrailTriggeredEvent {
  type: 'guardrail_triggered';
  direction: 'input' | 'output';
  guardrail_name: string;
  action: 'block' | 'warn' | 'modify';
  message?: string;
  timestamp: number;
}

export interface MemoryRetrievedEvent {
  type: 'memory_retrieved';
  memory_type: 'short_term' | 'long_term';
  items: Array<{ key: string; value: any }>;
  timestamp: number;
}

export interface ErrorEvent {
  type: 'error';
  code: string;
  message: string;
  recoverable: boolean;
  timestamp: number;
}

export interface DoneEvent {
  type: 'done';
  turn_id?: string;
  timestamp: number;
}

export interface CustomEvent {
  type: 'custom';
  name: string;
  data: any;
  timestamp: number;
}

export type AgentEvent =
  | TurnStartEvent
  | TextDeltaEvent
  | TextCompleteEvent
  | ThinkingDeltaEvent
  | ToolCallStartEvent
  | ToolCallProgressEvent
  | ToolResultEvent
  | ImageGeneratedEvent
  | HandoffEvent
  | GuardrailTriggeredEvent
  | MemoryRetrievedEvent
  | ErrorEvent
  | DoneEvent
  | CustomEvent;
