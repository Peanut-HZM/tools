/**
 * wordDocument 工具单元测试
 *
 * 覆盖真实世界里的 .doc 变体：
 * - docx（OOXML zip）
 * - 旧版二进制 doc（OLE2）
 * - Confluence / Outlook 导出的 MHTML doc
 * - 直接是 HTML 的 doc
 * - odt（zip，但 mammoth 不支持）
 * - 无法识别的内容
 */
import { describe, it, expect } from 'vitest';
import {
  decodeBase64ToBytes,
  detectWordDocumentKind,
  decodeQuotedPrintable,
  extractMhtmlHtml,
  decodeWordDocument,
} from '../wordDocument';

function bytesToBase64(bytes: number[]): string {
  return btoa(String.fromCharCode(...bytes));
}

function textToBase64(text: string): string {
  return btoa(text);
}

const OLE2_BYTES = [0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1, 0x00, 0x00];
const ZIP_BYTES = [0x50, 0x4b, 0x03, 0x04, 0x14, 0x00, 0x00, 0x00];

const MHTML_SAMPLE = [
  'MIME-Version: 1.0',
  'Content-Type: multipart/related; boundary="BOUND"',
  '',
  '--BOUND',
  'Content-Type: text/html; charset=UTF-8',
  'Content-Transfer-Encoding: quoted-printable',
  'Content-Location: file:///C:/exported.html',
  '',
  '<html><body><h1>=E6=A0=87=E9=A2=98</h1><img src=3D"file:///C:/img1"></body></html>',
  '--BOUND',
  'Content-Type: application/octet-stream',
  'Content-Transfer-Encoding: base64',
  'Content-Location: file:///C:/img1',
  '',
  'iVBORw0KGgo=',
  '--BOUND--',
  '',
].join('\r\n');

describe('wordDocument', () => {
  describe('detectWordDocumentKind', () => {
    it('识别 OOXML docx（zip 文件头）', () => {
      expect(detectWordDocumentKind(new Uint8Array(ZIP_BYTES))).toBe('docx');
    });

    it('识别 ODT（zip + mimetype 条目）', () => {
      const odt = new Uint8Array([
        ...ZIP_BYTES,
        ...Array.from('mimetypeapplication/vnd.oasis.opendocument.text').map(c => c.charCodeAt(0)),
      ]);
      expect(detectWordDocumentKind(odt)).toBe('odt');
    });

    it('识别旧版二进制 doc（OLE2 文件头）', () => {
      expect(detectWordDocumentKind(new Uint8Array(OLE2_BYTES))).toBe('legacy-doc');
    });

    it('识别 MHTML（multipart/related + boundary）', () => {
      const bytes = decodeBase64ToBytes(textToBase64(MHTML_SAMPLE));
      expect(detectWordDocumentKind(bytes)).toBe('mhtml');
    });

    it('识别直接是 HTML 的 doc', () => {
      const bytes = decodeBase64ToBytes(textToBase64('<html><body>hi</body></html>'));
      expect(detectWordDocumentKind(bytes)).toBe('html');
    });

    it('识别 RTF', () => {
      const bytes = decodeBase64ToBytes(textToBase64('{\\rtf1\\ansi hello}'));
      expect(detectWordDocumentKind(bytes)).toBe('rtf');
    });

    it('无法识别的内容返回 unknown', () => {
      const bytes = decodeBase64ToBytes(textToBase64('plain text without any marker'));
      expect(detectWordDocumentKind(bytes)).toBe('unknown');
    });
  });

  describe('decodeQuotedPrintable', () => {
    it('解码 =XX 十六进制与软换行', () => {
      const decoded = decodeQuotedPrintable('a=3Db=\r\nc=E4=B8=AD');
      expect(Array.from(decoded)).toEqual([
        0x61, 0x3d, 0x62, 0x63, 0xe4, 0xb8, 0xad,
      ]);
    });

    it('非法转义按字面量保留', () => {
      const decoded = decodeQuotedPrintable('100=ZZ%');
      expect(new TextDecoder().decode(decoded)).toBe('100=ZZ%');
    });
  });

  describe('extractMhtmlHtml', () => {
    it('提取 HTML 分块并解码中文', () => {
      const html = extractMhtmlHtml(MHTML_SAMPLE);
      expect(html).toContain('<h1>标题</h1>');
    });

    it('把内嵌图片替换为 data URI', () => {
      const html = extractMhtmlHtml(MHTML_SAMPLE);
      expect(html).toContain('src="data:image/png;base64,iVBORw0KGgo="');
    });

    it('非 MHTML 内容返回 null', () => {
      expect(extractMhtmlHtml('<html>plain</html>')).toBeNull();
    });
  });

  describe('decodeWordDocument', () => {
    it('docx 返回 arrayBuffer', () => {
      const result = decodeWordDocument(bytesToBase64(ZIP_BYTES));
      expect(result.kind).toBe('docx');
      expect(result.arrayBuffer).toBeInstanceOf(ArrayBuffer);
    });

    it('MHTML doc 返回提取后的 HTML', () => {
      const result = decodeWordDocument(textToBase64(MHTML_SAMPLE));
      expect(result.kind).toBe('mhtml');
      expect(result.html).toContain('<h1>标题</h1>');
    });

    it('旧版二进制 doc 不返回 html', () => {
      const result = decodeWordDocument(bytesToBase64(OLE2_BYTES));
      expect(result.kind).toBe('legacy-doc');
      expect(result.html).toBeUndefined();
    });
  });
});
