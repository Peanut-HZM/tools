/**
 * 文件类型判断工具
 *
 * 用于根据文件名判断其所属类别（代码 / PDF / Excel / Word / 图片 / 文本 / 未知）
 * 以及对应的编程语言，便于 FileViewer 路由到不同的查看器。
 */

/** 文件分类 */
export type FileCategory = 'code' | 'pdf' | 'excel' | 'word' | 'ppt' | 'image' | 'text' | 'unknown';

/**
 * 各分类对应的扩展名映射
 *
 * 注意：`md` 同时出现在 code 与 text 两个分类时，优先命中 code；
 * 这里将 `md` / `markdown` 仅归入 text，符合文档浏览场景的直觉。
 */
const FILE_EXTENSIONS: Record<Exclude<FileCategory, 'unknown'>, string[]> = {
  code: [
    'js', 'ts', 'jsx', 'tsx', 'py', 'java', 'go', 'rs', 'css',
    'html', 'htm', 'json', 'jsonc', 'xml', 'yaml', 'yml', 'toml', 'ini',
    'conf', 'cfg', 'properties', 'sh', 'bash', 'sql', 'c', 'cpp', 'h', 'hpp',
    'rb', 'php', 'swift', 'kt', 'scala', 'r', 'm', 'mm',
    'vue', 'svelte', 'astro', 'mdx', 'kubeconfig',
  ],
  pdf: ['pdf'],
  excel: ['xlsx', 'xls', 'csv', 'tsv'],
  word: ['doc', 'docx', 'odt', 'rtf'],
  ppt: ['pptx', 'ppt'],
  image: ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'bmp', 'ico', 'avif'],
  text: ['md', 'markdown', 'txt', 'log', 'rst', 'adoc'],
};

/** 扩展名 → 编程语言（用于代码高亮） */
const LANGUAGE_MAP: Record<string, string> = {
  js: 'javascript',
  jsx: 'javascript',
  ts: 'typescript',
  tsx: 'typescript',
  py: 'python',
  java: 'java',
  go: 'go',
  rs: 'rust',
  css: 'css',
  html: 'html',
  htm: 'html',
  json: 'json',
  jsonc: 'json',
  xml: 'xml',
  yaml: 'yaml',
  yml: 'yaml',
  kubeconfig: 'yaml',
  toml: 'toml',  ini: 'ini',
  conf: 'ini',
  cfg: 'ini',
  properties: 'ini',
  sh: 'bash',
  bash: 'bash',
  sql: 'sql',
  c: 'c',
  cpp: 'cpp',
  h: 'c',
  hpp: 'cpp',
  rb: 'ruby',
  php: 'php',
  swift: 'swift',
  kt: 'kotlin',
  scala: 'scala',
  r: 'r',
  m: 'objective-c',
  mm: 'objective-c',
  vue: 'vue',
  svelte: 'svelte',
  astro: 'astro',
  mdx: 'mdx',
};

/**
 * 从文件名中提取扩展名（小写）
 * 无扩展名时返回空字符串
 */
function getExtension(filename: string): string {
  // 兼容隐藏文件（如 `.gitignore`）与无扩展名文件
  const lastDot = filename.lastIndexOf('.');
  if (lastDot <= 0 || lastDot === filename.length - 1) {
    return '';
  }
  return filename.slice(lastDot + 1).toLowerCase();
}

/**
 * 根据文件名获取文件分类
 *
 * @param filename - 文件名（含或不含路径均可，仅按扩展名判断）
 * @returns 文件所属类别，未知类型返回 'unknown'
 */
export function getFileCategory(filename: string): FileCategory {
  const ext = getExtension(filename);
  if (!ext) {
    return 'unknown';
  }

  for (const [category, extensions] of Object.entries(FILE_EXTENSIONS)) {
    if (extensions.includes(ext)) {
      return category as FileCategory;
    }
  }
  return 'unknown';
}

/**
 * 根据文件名获取对应的编程语言标识（用于代码高亮）
 *
 * @param filename - 文件名
 * @returns 语言标识（如 'python' / 'typescript'），未知扩展名返回 'plaintext'
 */
export function getFileLanguage(filename: string): string {
  const ext = getExtension(filename);
  if (!ext) {
    return 'plaintext';
  }
  return LANGUAGE_MAP[ext] || 'plaintext';
}

/**
 * 判断文件是否为文本类文件（可直接以文本展示）
 *
 * 代码与纯文本均视为文本文件。
 */
export function isTextFile(filename: string): boolean {
  const category = getFileCategory(filename);
  return category === 'text' || category === 'code';
}

/**
 * 根据后端返回的 MIME 类型判断是否属于文本内容
 *
 * 用于**没有扩展名**的文件（如 `xa-higress-config`）：这类文件无法靠
 * 文件名判断类型，但后端在读取时已经做了内容嗅探（`_sniff_is_text`），
 * 会返回 `text/plain`（或 `text/*`）。
 *
 * @param contentType - 后端 `read-raw` 返回的 content_type
 * @returns 是否为文本内容
 */
export function isTextContentType(contentType: string | undefined | null): boolean {
  if (!contentType) return false;
  const normalized = contentType.trim().toLowerCase();
  if (!normalized) return false;
  // 明确的二进制类型
  if (normalized === 'application/octet-stream') return false;
  if (normalized.startsWith('image/')) return false;
  if (normalized.startsWith('audio/') || normalized.startsWith('video/')) return false;
  if (
    normalized === 'application/pdf' ||
    normalized === 'application/zip' ||
    normalized === 'application/x-zip-compressed' ||
    normalized === 'application/gzip' ||
    normalized === 'application/msword' ||
    normalized === 'application/vnd.openxmlformats-officedocument' ||
    normalized === 'application/vnd.ms-excel' ||
    normalized === 'application/vnd.ms-powerpoint'
  ) {
    return false;
  }
  // text/* 以及常见的文本类 JSON / XML / JS MIME
  return (
    normalized.startsWith('text/') ||
    normalized === 'application/json' ||
    normalized === 'application/xml' ||
    normalized === 'application/javascript' ||
    normalized === 'application/x-sh' ||
    normalized === 'application/yaml' ||
    normalized === 'application/x-yaml'
  );
}

/**
 * 综合文件路径与 MIME 类型判断文件分类
 *
 * 优先级：
 * 1. 文件名能识别出扩展名 → 用扩展名判断（最准确）
 * 2. 没有扩展名（`getFileCategory` 返回 'unknown'）→ 用 MIME 类型兜底：
 *    - 文本类 MIME → 'text'（用编辑器打开）
 *    - 图片类 MIME → 'image'
 *    - 其余 → 'unknown'
 *
 * 这样 `xa-higress-config`（无扩展名、实际是文本）就能正常打开，
 * 而不是落到「不支持的文件类型」占位页。
 *
 * @param filename - 文件名（含或不含路径均可）
 * @param contentType - 后端返回的 MIME 类型，可选
 * @returns 文件所属类别
 */
export function getFileCategoryWithContentType(
  filename: string,
  contentType?: string | undefined | null,
): FileCategory {
  const byName = getFileCategory(filename);
  if (byName !== 'unknown') return byName;

  const normalized = (contentType || '').trim().toLowerCase();
  if (!normalized) return 'unknown';

  if (normalized.startsWith('image/')) return 'image';
  if (isTextContentType(normalized)) return 'text';
  return 'unknown';
}
