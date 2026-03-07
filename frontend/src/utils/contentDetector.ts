/**
 * 内容类型检测工具
 */

export type ContentType = 'json' | 'code' | 'markdown' | 'text';

export interface ContentDetectionResult {
  type: ContentType;
  language?: string; // 代码语言
  lines: number; // 行数
}

/**
 * 检测内容类型
 * 优先级：JSON > Code > Markdown > Text
 */
export function detectContentType(content: string): ContentDetectionResult {
  const trimmed = content.trim();
  const lines = countLines(trimmed);

  // 1. 检测 JSON (优先级最高)
  if (/^\s*[\[{]/.test(trimmed)) {
    try {
      JSON.parse(trimmed);
      return { type: 'json', lines };
    } catch {
      // 不是有效 JSON，继续检测其他类型
    }
  }

  // 2. 检测代码块
  const codeBlockMatch = trimmed.match(/^```(\w*)\n/);
  if (codeBlockMatch) {
    const language = codeBlockMatch[1] || 'plaintext';
    return { type: 'code', language, lines };
  }

  // 3. 检测内联代码或常见 Markdown 语法
  if (isMarkdown(trimmed)) {
    return { type: 'markdown', lines };
  }

  // 4. 默认为普通文本
  return { type: 'text', lines };
}

/**
 * 检测是否为 Markdown 内容
 */
function isMarkdown(content: string): boolean {
  const markdownPatterns = [
    /^#{1,6}\s+/m, // 标题
    /^\s*[-*+]\s+/m, // 无序列表
    /^\s*\d+\.\s+/m, // 有序列表
    /^\s*>/m, // 引用
    /`[^`]+`/, // 内联代码
    /\*\*[^*]+\*\*/, // 粗体
    /\*[^*]+\*/, // 斜体
    /\[([^\]]+)\]\(([^)]+)\)/, // 链接
    /^---+$/m, // 分割线
    /^\|.*\|.*\|/m, // 表格
  ];

  return markdownPatterns.some(pattern => pattern.test(content));
}

/**
 * 计算内容行数
 */
export function countLines(content: string): number {
  if (!content) return 0;
  return content.split('\n').length;
}

/**
 * 提取代码块的语言和内容
 */
export function parseCodeBlock(content: string): { language: string; code: string } {
  const match = content.match(/^```(\w*)\n([\s\S]*?)```$/);
  if (match) {
    return {
      language: match[1] || 'plaintext',
      code: match[2].trim(),
    };
  }
  return { language: 'plaintext', code: content };
}

/**
 * 尝试格式化 JSON
 */
export function formatJson(content: string): { success: boolean; result: string } {
  try {
    const parsed = JSON.parse(content);
    return {
      success: true,
      result: JSON.stringify(parsed, null, 2),
    };
  } catch {
    return { success: false, result: content };
  }
}
