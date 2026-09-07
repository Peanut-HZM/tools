/**
 * 文件类型判断工具
 *
 * 用于根据文件名判断其所属类别（代码 / PDF / Excel / Word / 图片 / 文本 / 未知）
 * 以及对应的编程语言，便于 FileViewer 路由到不同的查看器。
 */

/** 文件分类 */
export type FileCategory = 'code' | 'pdf' | 'excel' | 'word' | 'image' | 'text' | 'unknown';

/**
 * 各分类对应的扩展名映射
 *
 * 注意：`md` 同时出现在 code 与 text 两个分类时，优先命中 code；
 * 这里将 `md` / `markdown` 仅归入 text，符合文档浏览场景的直觉。
 */
const FILE_EXTENSIONS: Record<Exclude<FileCategory, 'unknown'>, string[]> = {
  code: [
    'js', 'ts', 'jsx', 'tsx', 'py', 'java', 'go', 'rs', 'css',
    'html', 'htm', 'json', 'xml', 'yaml', 'yml', 'toml', 'ini',
    'conf', 'cfg', 'sh', 'bash', 'sql', 'c', 'cpp', 'h', 'hpp',
    'rb', 'php', 'swift', 'kt', 'scala', 'r', 'm', 'mm',
    'vue', 'svelte', 'astro', 'mdx',
  ],
  pdf: ['pdf'],
  excel: ['xlsx', 'xls', 'csv', 'tsv'],
  word: ['doc', 'docx', 'odt', 'rtf'],
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
  xml: 'xml',
  yaml: 'yaml',
  yml: 'yaml',
  toml: 'toml',
  ini: 'ini',
  conf: 'ini',
  cfg: 'ini',
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
