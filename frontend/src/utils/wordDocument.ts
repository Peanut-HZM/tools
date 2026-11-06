/**
 * Word 文档格式识别与解码
 *
 * `.doc` 在实际使用中并不只有一种格式：
 * - `.docx`：OOXML，本质是 zip（mammoth 可解析）
 * - `.odt`：OpenDocument，也是 zip，但 mammoth 不支持
 * - 旧版二进制 `.doc`：OLE2 复合文档（D0 CF 11 E0 ...），浏览器端无纯 JS 解析方案
 * - Confluence / Outlook 导出的 `.doc`：实际是 MHTML（multipart/related 包一个 text/html）
 * - 部分系统导出的 `.doc`：直接就是 HTML 文本
 *
 * 本模块只做「字节嗅探 + MHTML/HTML 提取」，不依赖后端转换，
 * 保证在服务器没有 LibreOffice 时也能预览 MHTML 形式的 .doc。
 */

/** Word 文档实际格式 */
export type WordDocumentKind =
  | 'docx'
  | 'odt'
  | 'mhtml'
  | 'html'
  | 'legacy-doc'
  | 'rtf'
  | 'unknown';

/** 解码结果 */
export interface DecodedWordDocument {
  kind: WordDocumentKind;
  /** docx 的二进制数据（交给 mammoth） */
  arrayBuffer?: ArrayBuffer;
  /** mhtml / html 提取出的完整 HTML 文档 */
  html?: string;
}

/** 各格式不支持时给用户的说明 */
export const UNSUPPORTED_WORD_REASON: Record<string, string> = {
  'legacy-doc':
    '该文件是旧版二进制 Word（.doc，OLE2 格式），浏览器端无法直接解析。请用 Word / WPS 另存为 .docx 后预览，或下载原文件查看。',
  odt: '暂不支持 OpenDocument（.odt）在线预览，请另存为 .docx 或下载原文件查看。',
  rtf: '暂不支持 RTF（.rtf）在线预览，请另存为 .docx 或下载原文件查看。',
  unknown: '无法识别该 Word 文件的格式，请确认文件是否损坏，或另存为 .docx 后重试。',
};

const ZIP_MAGIC = [0x50, 0x4b];
const OLE2_MAGIC = [0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1];

/** base64 → 字节数组 */
export function decodeBase64ToBytes(base64: string): Uint8Array {
  const binaryStr = atob(base64);
  const bytes = new Uint8Array(binaryStr.length);
  for (let i = 0; i < binaryStr.length; i++) {
    bytes[i] = binaryStr.charCodeAt(i);
  }
  return bytes;
}

/** 按 latin1 取前 limit 个字节，用于格式嗅探（保留原始字节值） */
function bytesToLatin1(bytes: Uint8Array, limit = 4096): string {
  const end = Math.min(bytes.length, limit);
  let text = '';
  for (let i = 0; i < end; i++) {
    text += String.fromCharCode(bytes[i]);
  }
  return text;
}

/** 判断是否为 zip（docx / odt 的容器格式） */
function isZip(bytes: Uint8Array): boolean {
  return (
    bytes.length >= 3 &&
    bytes[0] === ZIP_MAGIC[0] &&
    bytes[1] === ZIP_MAGIC[1] &&
    (bytes[2] === 0x03 || bytes[2] === 0x05 || bytes[2] === 0x07)
  );
}

function isOle2(bytes: Uint8Array): boolean {
  if (bytes.length < OLE2_MAGIC.length) return false;
  return OLE2_MAGIC.every((value, index) => bytes[index] === value);
}

/** 根据文件头判断实际格式 */
export function detectWordDocumentKind(bytes: Uint8Array): WordDocumentKind {
  if (isZip(bytes)) {
    // ODT 的 mimetype 是 zip 的第一个未压缩条目，文件头附近就能看到
    const head = bytesToLatin1(bytes, 2048);
    if (head.includes('application/vnd.oasis.opendocument.text')) {
      return 'odt';
    }
    return 'docx';
  }

  if (isOle2(bytes)) {
    return 'legacy-doc';
  }

  const head = bytesToLatin1(bytes, 8192).replace(/^\uFEFF/, '').trimStart();

  if (/^\{\\rtf/i.test(head)) {
    return 'rtf';
  }

  // MHTML：MIME 头 + multipart boundary（Confluence / Outlook 导出的 .doc）
  if (
    /content-type:\s*multipart\/(related|mixed|alternative)/i.test(head) &&
    /boundary\s*=\s*"?[^"\s;]+/i.test(head)
  ) {
    return 'mhtml';
  }

  if (/^mime-version:/i.test(head) && /content-type:\s*text\/html/i.test(head)) {
    return 'mhtml';
  }

  if (/<html[\s>]|<!doctype\s+html|<body[\s>]/i.test(head)) {
    return 'html';
  }

  return 'unknown';
}

/** quoted-printable 解码（返回原始字节，字符集由调用方决定） */
export function decodeQuotedPrintable(input: string): Uint8Array {
  const out: number[] = [];
  const hexPair = /^[0-9a-fA-F]{2}$/;

  for (let i = 0; i < input.length; i++) {
    const ch = input[i];
    if (ch === '=') {
      const next = input[i + 1];
      const next2 = input[i + 2];
      // 软换行：=\r\n 或 =\n
      if (next === '\r' && next2 === '\n') {
        i += 2;
        continue;
      }
      if (next === '\n') {
        i += 1;
        continue;
      }
      // =XX 十六进制字节
      if (next && next2 && hexPair.test(next + next2)) {
        out.push(parseInt(next + next2, 16));
        i += 2;
        continue;
      }
      // 非法转义按字面量保留
    }
    out.push(ch.charCodeAt(0) & 0xff);
  }

  return new Uint8Array(out);
}

function decodeWithCharset(bytes: Uint8Array, charset: string): string {
  try {
    return new TextDecoder(charset || 'utf-8').decode(bytes);
  } catch {
    return new TextDecoder('utf-8').decode(bytes);
  }
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = '';
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

/** 按 magic number 嗅探图片 MIME，用于把 MHTML 内嵌图片转成 data URI */
function sniffImageMime(bytes: Uint8Array): string | null {
  if (bytes.length >= 8 && bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) {
    return 'image/png';
  }
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
    return 'image/jpeg';
  }
  if (bytes.length >= 6 && bytes[0] === 0x47 && bytes[1] === 0x49 && bytes[2] === 0x46) {
    return 'image/gif';
  }
  if (
    bytes.length >= 12 &&
    bytes[0] === 0x52 && bytes[1] === 0x49 && bytes[2] === 0x46 && bytes[3] === 0x46 &&
    bytes[8] === 0x57 && bytes[9] === 0x45 && bytes[10] === 0x42 && bytes[11] === 0x50
  ) {
    return 'image/webp';
  }
  const head = bytesToLatin1(bytes, 512).trimStart().toLowerCase();
  if (head.startsWith('<svg') || (head.startsWith('<?xml') && head.includes('<svg'))) {
    return 'image/svg+xml';
  }
  return null;
}

function parseMimePart(block: string): { headers: Record<string, string>; body: string } {
  const separator = block.includes('\r\n\r\n') ? '\r\n\r\n' : '\n\n';
  const splitIndex = block.indexOf(separator);
  const headerText = splitIndex === -1 ? block : block.slice(0, splitIndex);
  const body = splitIndex === -1 ? '' : block.slice(splitIndex + separator.length);

  const headers: Record<string, string> = {};
  // 展开折行（RFC 5322 续行）
  const unfolded = headerText.replace(/\r?\n[ \t]+/g, ' ');
  for (const line of unfolded.split(/\r?\n/)) {
    const colon = line.indexOf(':');
    if (colon <= 0) continue;
    headers[line.slice(0, colon).trim().toLowerCase()] = line.slice(colon + 1).trim();
  }
  return { headers, body };
}

function decodeMimePartBody(part: { headers: Record<string, string>; body: string }): Uint8Array {
  const encoding = (part.headers['content-transfer-encoding'] || '').toLowerCase();
  if (encoding === 'base64') {
    return decodeBase64ToBytes(part.body.replace(/\s+/g, ''));
  }
  if (encoding === 'quoted-printable') {
    return decodeQuotedPrintable(part.body);
  }
  // 7bit / 8bit / binary：body 本身是 latin1 逐字节解码的字符串
  const bytes = new Uint8Array(part.body.length);
  for (let i = 0; i < part.body.length; i++) {
    bytes[i] = part.body.charCodeAt(i) & 0xff;
  }
  return bytes;
}

function getCharset(contentType: string): string {
  const match = /charset\s*=\s*"?([^";\s]+)"?/i.exec(contentType || '');
  return match ? match[1] : 'utf-8';
}

/**
 * 解析 MHTML，提取主 HTML 文档，并把内嵌资源（图片）替换为 data URI。
 * 解析失败返回 null，由调用方降级处理。
 */
export function extractMhtmlHtml(raw: string): string | null {
  const topEnd = raw.includes('\r\n\r\n') ? raw.indexOf('\r\n\r\n') : raw.indexOf('\n\n');
  if (topEnd === -1) return null;

  const top = parseMimePart(raw);
  const boundaryMatch = /boundary\s*=\s*"?([^";\r\n]+)"?/i.exec(top.headers['content-type'] || '');
  if (!boundaryMatch) return null;

  const boundary = boundaryMatch[1].trim();
  const segments = raw.split(`--${boundary}`);

  let htmlPart: { headers: Record<string, string>; body: string } | null = null;
  const resources = new Map<string, string>();

  for (const segment of segments) {
    // 去掉分段开头/结尾的换行与结束标记
    const cleaned = segment.replace(/^\r?\n/, '').replace(/\r?\n$/, '');
    if (!cleaned || cleaned.startsWith('--')) continue;

    const part = parseMimePart(cleaned);
    if (!part.headers['content-type']) continue;

    const contentType = part.headers['content-type'];
    const lowerType = contentType.toLowerCase();

    if (!htmlPart && lowerType.startsWith('text/html')) {
      htmlPart = part;
      continue;
    }

    const location = part.headers['content-location'];
    if (location) {
      const bytes = decodeMimePartBody(part);
      const mime = sniffImageMime(bytes) || lowerType.split(';')[0].trim() || 'application/octet-stream';
      const dataUri = `data:${mime};base64,${bytesToBase64(bytes)}`;
      resources.set(location, dataUri);
      // 同时用文件名兜底匹配（HTML 里可能只引用文件名）
      const fileName = location.split('/').pop();
      if (fileName && fileName !== location) {
        resources.set(fileName, dataUri);
      }
    }
  }

  if (!htmlPart) return null;

  const htmlBytes = decodeMimePartBody(htmlPart);
  let html = decodeWithCharset(htmlBytes, getCharset(htmlPart.headers['content-type']));

  // 内嵌资源引用替换（如 file:///C:/xxx.png → data:image/png;base64,...）
  for (const [ref, dataUri] of resources) {
    if (!ref) continue;
    html = html.split(ref).join(dataUri);
  }

  return html;
}

/**
 * 把 base64 内容解码为 WordViewer 可渲染的形态。
 * docx 交给 mammoth；MHTML / HTML 直接提取 HTML；其余返回格式类型。
 */
export function decodeWordDocument(base64: string): DecodedWordDocument {
  const bytes = decodeBase64ToBytes(base64);
  const kind = detectWordDocumentKind(bytes);

  if (kind === 'docx') {
    return { kind, arrayBuffer: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer };
  }

  if (kind === 'mhtml') {
    const raw = bytesToLatin1(bytes, bytes.length);
    const html = extractMhtmlHtml(raw);
    if (html) return { kind, html };
    // 头部像 MHTML 但解析失败：退回按 HTML 处理
    return { kind: 'html', html: new TextDecoder('utf-8').decode(bytes) };
  }

  if (kind === 'html') {
    return { kind, html: new TextDecoder('utf-8').decode(bytes) };
  }

  return { kind };
}
