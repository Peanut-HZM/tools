// 工具相关类型定义
// 供 Task 19 及后续 harness 前端模块使用

export interface Tool {
  id: string;
  name: string;
  display_name: string;
  description: string;
  type: 'builtin' | 'http' | 'mcp' | 'plugin';
  config: Record<string, any>;
  parameters_schema: Record<string, any>;
  returns_schema?: Record<string, any>;
  is_available_condition: Record<string, any>;
  rate_limit_per_minute?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ToolBinding {
  binding_id: string;
  tool_id: string;
  tool_name: string;
  tool_display_name: string;
  tool_type: 'builtin' | 'http' | 'mcp' | 'plugin';
  parameter_overrides: Record<string, any>;
  priority: number;
  is_enabled: boolean;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface ToolResult {
  id: string;
  name: string;
  success: boolean;
  content_type: 'text' | 'image' | 'file' | 'json' | 'error';
  content: any;
  attachments: Attachment[];
  error?: string;
}

export interface Attachment {
  type: 'image' | 'file';
  url: string;
  mime_type?: string;
  name?: string;
  size?: number;
}
