/**
 * 内容类型检测工具
 * 自动识别 JSON、代码、Markdown、普通文本
 */

export type ContentType = 'json' | 'code' | 'markdown' | 'text';

/**
 * 检测内容类型
 * @param content - 要检测的内容
 * @returns 内容类型
 */
export function detectContentType(content: string): ContentType {
  if (!content || content.trim() === '') {
    return 'text';
  }

  const trimmedContent = content.trim();

  // 1. 检测 JSON (优先级 1)
  if (/^\s*[\[{]/.test(trimmedContent)) {
    try {
      JSON.parse(trimmedContent);
      return 'json';
    } catch {
      // 不是有效 JSON，继续检测其他类型
    }
  }

  // 2. 检测代码块 (优先级 2)
  if (/^```[\w]*\n/.test(trimmedContent)) {
    return 'code';
  }

  // 3. 检测 Markdown (优先级 3)
  // 检查是否包含 Markdown 语法特征
  const markdownPatterns = [
    /^#{1,6}\s/,           // 标题
    /^\*\*.*\*\*/,         // 粗体
    /^\*.*\*/,             // 斜体
    /^-+\s/,               // 无序列表
    /^\d+\.\s/,            // 有序列表
    /^>\s/,                // 引用
    /^`{3,}/,              // 代码块
    /\[.*\]\(.*\)/,        // 链接
    /^!?\[.*\]\(.*\)/,     // 图片
  ];

  if (markdownPatterns.some(pattern => pattern.test(trimmedContent))) {
    return 'markdown';
  }

  // 4. 默认为普通文本
  return 'text';
}

/**
 * 计算内容行数
 * @param content - 要计算的内容
 * @returns 行数
 */
export function countLines(content: string): number {
  if (!content) return 0;
  return content.split('\n').length;
}

/**
 * 从代码块中提取语言标识
 * @param content - 代码块内容
 * @returns 语言标识（如 javascript, python 等）
 */
export function extractCodeLanguage(content: string): string {
  const match = content.match(/^```(\w+)?/);
  return match?.[1] || 'javascript';
}

/**
 * 从代码块中提取纯代码内容（移除 ``` 标记）
 * @param content - 代码块内容
 * @returns 纯代码内容
 */
export function extractCodeContent(content: string): string {
  // 移除开头的 ```language 和结尾的 ```
  const cleaned = content.replace(/^```\w*\n/, '').replace(/\n```$/, '');
  return cleaned;
}

/**
 * 检测是否是 URL 链接
 * @param content - 要检测的内容
 * @returns 是否是 URL
 */
export function isUrl(content: string): boolean {
  if (!content || content.trim() === '') {
    return false;
  }

  const trimmedContent = content.trim();

  // 检查是否是完整的 URL（包含协议）
  const urlPattern = /^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(\/.*)?$/;
  const urlWithProtocolPattern = /^https?:\/\/([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(\/.*)?$/;

  // 检查是否是常见的 URL 格式
  if (urlWithProtocolPattern.test(trimmedContent)) {
    return true;
  }

  // 检查是否是 www 开头的 URL
  if (/^www\./.test(trimmedContent)) {
    return true;
  }

  return false;
}
