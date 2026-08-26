#!/usr/bin/env node
/**
 * generate-miniapp-tokens.js
 * ---------------------------
 * 将前端 CSS 设计令牌（frontend/src/styles/tokens/*.css）转换为小程序 SCSS 变量文件。
 *
 * 输入：frontend/src/styles/tokens/*.css（除 index.css 外的各独立令牌文件）
 * 输出：miniapp/src/styles/_tokens.scss
 *
 * 用法：
 *   node frontend/scripts/generate-miniapp-tokens.js
 *
 * 说明：
 * - 解析 :root { ... } 中的 CSS 自定义属性，转换为 $token-name: value; 形式的 SCSS 变量
 * - :root[data-theme="light"] 中的覆盖值会被收集到 %light-tokens 占位符选择器中，
 *   通过 @mixin light-tokens 提供给小程序按需应用
 * - 输出文件顶部包含自动生成说明，请勿手动编辑
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TOKENS_DIR = path.resolve(__dirname, '../src/styles/tokens');
const OUTPUT_FILE = path.resolve(__dirname, '../../miniapp/src/styles/_tokens.scss');

// 需要处理的令牌文件（按逻辑顺序排列）
const TOKEN_FILES = [
  'colors.css',
  'typography.css',
  'spacing.css',
  'radius.css',
  'shadows.css',
  'motion.css',
];

/**
 * 解析 CSS 文件中的自定义属性
 * 返回 { dark: Map<name, value>, light: Map<name, value> }
 */
function parseTokens(css) {
  const dark = new Map();
  const light = new Map();

  // 匹配 :root[data-theme="light"] { ... }
  const lightRegex = /:root\s*\[\s*data-theme\s*=\s*"light"\s*\]\s*\{([^}]+)\}/g;
  let match;
  while ((match = lightRegex.exec(css)) !== null) {
    const block = match[1];
    parseBlock(block, light);
  }

  // 匹配 :root { ... }（暗色 / 默认值）
  // 注意：要排除 :root[data-theme="light"] 的块
  const rootRegex = /:root\s*\{([^}]+)\}/g;
  while ((match = rootRegex.exec(css)) !== null) {
    // 简单判断：如果 match[0] 前一个字符是 ] 则属于 data-theme，跳过
    const precedingIdx = match.index - 1;
    if (precedingIdx >= 0 && css[precedingIdx] === ']') continue;
    parseBlock(match[1], dark);
  }

  return { dark, light };
}

function parseBlock(block, map) {
  // 匹配 --name: value; （value 可能跨行）
  const propRegex = /(--[\w-]+)\s*:\s*([^;]+);/g;
  let m;
  while ((m = propRegex.exec(block)) !== null) {
    const name = m[1].trim();
    const value = m[2].trim();
    map.set(name, value);
  }
}

/**
 * 将 CSS 属性名转为 SCSS 变量名
 * --bg-canvas → $bg-canvas
 */
function toScssVar(cssVarName) {
  return '$' + cssVarName.replace(/^--/, '');
}

/**
 * 规范化多行值为单行（折叠多余空白）
 */
function collapse(value) {
  return value.replace(/\s+/g, ' ');
}

function main() {
  const allDark = new Map();
  const allLight = new Map();
  const sources = [];

  for (const file of TOKEN_FILES) {
    const filePath = path.join(TOKENS_DIR, file);
    if (!fs.existsSync(filePath)) {
      console.warn(`[warn] 令牌文件不存在，跳过：${filePath}`);
      continue;
    }
    const css = fs.readFileSync(filePath, 'utf-8');
    const { dark, light } = parseTokens(css);
    sources.push(file);
    for (const [k, v] of dark) allDark.set(k, v);
    for (const [k, v] of light) allLight.set(k, v);
  }

  // 计算仅在暗色中存在 / 仅在亮色中存在 / 两者都有的变量
  const darkOnlyKeys = [...allDark.keys()].filter((k) => !allLight.has(k));
  const lightOnlyKeys = [...allLight.keys()].filter((k) => !allDark.has(k));
  const sharedKeys = [...allDark.keys()].filter((k) => allLight.has(k));

  const lines = [];
  const header = [
    '// ==========================================================',
    '// AUTO-GENERATED FILE — DO NOT EDIT',
    '// 由 frontend/scripts/generate-miniapp-tokens.js 自动生成',
    `// 源文件：${sources.join(', ')}`,
    `// 生成时间：${new Date().toISOString()}`,
    '// ==========================================================',
    '',
    '// -----------------------------------------------------------',
    '// 默认令牌（暗色主题）',
    '// 用法：.my-class { color: $ink-default; }',
    '// -----------------------------------------------------------',
  ];
  lines.push(...header);

  // 暗色（默认）
  for (const k of allDark.keys()) {
    lines.push(`${toScssVar(k)}: ${collapse(allDark.get(k))};`);
  }
  lines.push('');

  // 亮色覆盖值：仅列出与暗色不同的变量
  if (sharedKeys.length > 0 || lightOnlyKeys.length > 0) {
    lines.push('// -----------------------------------------------------------');
    lines.push('// 亮色主题覆盖值');
    lines.push('// 在小程序中通过 mixin 应用到根容器：');
    lines.push('//   @include light-tokens;');
    lines.push('// -----------------------------------------------------------');
    lines.push('');
    lines.push('@mixin light-tokens {');
    const keysToEmit = [...sharedKeys, ...lightOnlyKeys].sort();
    for (const k of keysToEmit) {
      const val = allLight.has(k) ? allLight.get(k) : allDark.get(k);
      lines.push(`  ${toScssVar(k)}: ${collapse(val)};`);
    }
    lines.push('}');
    lines.push('');
  }

  // 便捷工具 mixin：在小程序根容器应用暗/亮
  lines.push('// -----------------------------------------------------------');
  lines.push('// 主题应用 mixin');
  lines.push('// 用法：在小程序 page 或根容器选择器中');
  lines.push('//   page { @include apply-theme(dark); }');
  lines.push('// -----------------------------------------------------------');
  lines.push('');
  lines.push('@mixin apply-theme($mode: dark) {');
  lines.push('  @if $mode == light {');
  lines.push('    @include light-tokens;');
  lines.push('  }');
  lines.push('  // dark 模式使用上方默认变量，无需额外覆盖');
  lines.push('}');
  lines.push('');

  const output = lines.join('\n') + '\n';

  // 确保输出目录存在
  const outDir = path.dirname(OUTPUT_FILE);
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  fs.writeFileSync(OUTPUT_FILE, output, 'utf-8');

  console.log(`[ok] 已生成 SCSS 令牌文件：${OUTPUT_FILE}`);
  console.log(`     默认（暗色）变量数：${allDark.size}`);
  console.log(`     亮色覆盖变量数：${sharedKeys.length + lightOnlyKeys.length}`);
}

main();
