#!/usr/bin/env node
/**
 * generate-miniapp-tokens.js
 * ---------------------------
 * 将 Web 设计令牌转换为小程序 WXSS CSS 自定义属性文件（_tokens.scss）。
 *
 * 输入（与 Web 端同源的单一色值来源）：
 *   - frontend/src/styles/tokens/_primitives.css（--p-* 原始调色板，值为 "R G B" 三元组）
 *   - frontend/src/styles/tokens/colors.css（:root 暗色块 = 当前生效主题；
 *     :root[data-theme="light"] 亮色块直接忽略——小程序为暗色单主题）
 *
 * 输出：
 *   - mini-program/src/styles/_tokens.scss
 *     形如 page { --p-navy-900: rgb(10, 18, 37); --bg-canvas: rgb(10, 18, 37); ... }
 *
 * 处理规则：
 *   1. 仅解析上述两个文件中 :root 块的 CSS 自定义属性；
 *   2. var() 解析：反复迭代，把 var(--p-*) / var(--gradient-*) / var(--shadow-*) /
 *      var(--chart-*) / var(--accent-*) / var(--ink-*) 等内部引用替换为已解析的值
 *      （最多 5 轮；仍有未解析引用则报错并列出，避免输出脏数据）；
 *   3. 三元组包装与归一化（WXSS 兼容）：
 *      - rgb(96 165 250)   → rgb(96, 165, 250)（空格语法 → 逗号语法）
 *      - rgba(255 255 255 / 0.08) → rgba(255, 255, 255, 0.08)
 *      - 解析后为裸 "R G B" 三元组的（如 --p-*、--accent-warm）包装为 rgb(R, G, B)
 *   4. 过滤：仅输出颜色/渐变/阴影类声明（值含 rgb/rgba/#/linear-gradient/radial-gradient）；
 *      跳过 --font-*（字体栈 Web 专用）；长度类 token（如 --glass-blur: 14px）不迁移
 *      ——小程序 pxtransform 会把 px 1:1 转 rpx，长度语义与 Web 不一致，由调用方自理；
 *   5. 输出全部为字面量（无任何 var() 链），最大化 WXSS 兼容性；
 *      旧变量名兼容映射（别名层）由 app.scss 负责，不在本脚本职责内。
 *
 * 用法：
 *   node frontend/scripts/generate-miniapp-tokens.js
 *
 * 注意：输出文件为自动生成产物，请勿手动编辑；变更请修改令牌源文件后重新生成。
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 输入：原始调色板 + 语义色板（暗色主题）
const PRIMITIVES_FILE = path.resolve(__dirname, '../src/styles/tokens/_primitives.css');
const COLORS_FILE = path.resolve(__dirname, '../src/styles/tokens/colors.css');

// 输出：小程序全局样式目录下的 token 文件
const OUTPUT_FILE = path.resolve(__dirname, '../../mini-program/src/styles/_tokens.scss');

// var() 解析最大迭代轮数（超过仍未解析干净则报错，防止循环引用静默产出脏数据）
const MAX_RESOLVE_ROUNDS = 5;

// 匹配 var(--name) 或 var(--name, fallback)
const VAR_REF_REGEX = /var\(\s*(--[\w-]+)\s*(?:,\s*([^()]+?)\s*)?\)/g;
// 裸 "R G B" 三元组（解析完成后仍是这种形态的，视为未包装的颜色值）
const TRIPLET_REGEX = /^\d+\s+\d+\s+\d+$/;
// 颜色/渐变/阴影类值的判定：含 rgb/rgba/#/linear-gradient/radial-gradient 才输出
const COLOR_VALUE_REGEX = /rgba?\(|#|linear-gradient|radial-gradient/;

/**
 * 从 CSS 文本中提取 :root 块内的自定义属性声明
 * 忽略 :root[data-theme="light"] 亮色块（小程序为暗色单主题）
 * 参数：css - CSS 文件全文
 * 返回：Map<变量名, 值>（保持源文件声明顺序）
 * 异常：文件中不存在 :root 块时抛错
 */
function parseRootTokens(css, sourceName) {
  // 先移除亮色主题块，避免 :root 正则误匹配
  const withoutLight = css.replace(
    /:root\s*\[\s*data-theme\s*=\s*["']light["']\s*\]\s*\{[^}]*\}/g,
    ''
  );
  const blockMatch = withoutLight.match(/:root\s*\{([^}]*)\}/);
  if (!blockMatch) {
    throw new Error(`[generate-miniapp-tokens] ${sourceName} 中未找到 :root 块`);
  }

  const map = new Map();
  // 匹配 --name: value;（值可能跨行，如多行渐变）
  const propRegex = /(--[\w-]+)\s*:\s*([^;]+);/g;
  let m;
  while ((m = propRegex.exec(blockMatch[1])) !== null) {
    map.set(m[1].trim(), m[2].trim());
  }
  return map;
}

/**
 * 迭代解析所有 token 值中的 var() 内部引用
 * 参数：tokens - Map<变量名, 值>（原地更新为解析后的值）
 * 异常：超过最大轮数仍有 var( 残留时抛错并列出未解析项
 */
function resolveAllVars(tokens) {
  for (let round = 1; round <= MAX_RESOLVE_ROUNDS; round++) {
    let changed = false;
    // 固定本轮快照遍历，轮内替换引用到的值可能是其他 token 的原始值，下一轮继续解析
    for (const name of [...tokens.keys()]) {
      const raw = tokens.get(name);
      if (!raw.includes('var(')) continue;
      const next = raw.replace(VAR_REF_REGEX, (full, ref, fallback) => {
        if (tokens.has(ref)) return tokens.get(ref);
        // 引用不存在但提供了 fallback，则使用 fallback
        if (fallback !== undefined) return fallback.trim();
        // 无法解析，保留原样，最终统一报错
        return full;
      });
      if (next !== raw) {
        tokens.set(name, next);
        changed = true;
      }
    }
    if (!changed) return; // 全部解析完成
  }

  const unresolved = [...tokens.entries()].filter(([, v]) => v.includes('var('));
  if (unresolved.length > 0) {
    const detail = unresolved.map(([k, v]) => `  ${k}: ${v}`).join('\n');
    throw new Error(
      `[generate-miniapp-tokens] 存在无法解析的 var() 引用（可能为循环引用或未定义变量），` +
        `共 ${unresolved.length} 处：\n${detail}`
    );
  }
}

/**
 * 折叠多行值为单行
 */
function collapse(value) {
  return value.replace(/\s+/g, ' ').trim();
}

/**
 * 将 rgb/rgba 的 CSS 空格语法归一化为逗号语法（旧版 WXSS 渲染层兼容）
 * - rgb(96 165 250) → rgb(96, 165, 250)
 * - rgba(255 255 255 / 0.08) → rgba(255, 255, 255, 0.08)
 */
function normalizeColorFunctions(value) {
  return value
    .replace(/(rgba?)\(\s*(\d+)\s+(\d+)\s+(\d+)\s*\/\s*([\d.]+)\s*\)/g, '$1($2, $3, $4, $5)')
    .replace(/(rgba?)\(\s*(\d+)\s+(\d+)\s+(\d+)\s*\)/g, '$1($2, $3, $4)');
}

/**
 * 把 token 值转换为可直接输出的字面量：
 * 解析 var() → 折叠空白 → 归一化颜色函数 → 裸三元组包装为 rgb()
 */
function toLiteral(value) {
  let v = normalizeColorFunctions(collapse(value));
  if (TRIPLET_REGEX.test(v)) {
    v = `rgb(${v.split(/\s+/).join(', ')})`;
  }
  return v;
}

/**
 * 过滤规则：是否输出该 token
 * - --font-* 字体栈 Web 专用，跳过
 * - 仅输出颜色/渐变/阴影类声明（值含 rgb/rgba/#/linear-gradient/radial-gradient）
 *   长度类 token（px/毫秒等）不迁移：pxtransform 会把 px 1:1 转 rpx，语义不一致
 */
function shouldEmit(name, literalValue) {
  if (name.startsWith('--font-')) return false;
  return COLOR_VALUE_REGEX.test(literalValue);
}

function main() {
  // 1. 解析两个来源文件的 :root（暗色）块
  const primitives = parseRootTokens(
    fs.readFileSync(PRIMITIVES_FILE, 'utf-8'),
    path.basename(PRIMITIVES_FILE)
  );
  const semantic = parseRootTokens(
    fs.readFileSync(COLORS_FILE, 'utf-8'),
    path.basename(COLORS_FILE)
  );

  // 2. var() 解析：合并为同一解析池（semantic 大量引用 primitives，必须跨文件解析）
  const pool = new Map([...primitives, ...semantic]);
  resolveAllVars(pool);

  // 3. 逐个转为字面量并按规则过滤；按 --p- 前缀区分输出分区
  const primitivesOut = []; // 原始调色板（--p-*）
  const semanticOut = [];   // 语义色板（colors.css 暗色块）
  const skipped = [];       // 被过滤的 token（记录原因，便于核对）

  for (const [name, value] of pool) {
    const literal = toLiteral(value);
    if (!shouldEmit(name, literal)) {
      skipped.push([name, literal]);
      continue;
    }
    if (name.startsWith('--p-')) primitivesOut.push([name, literal]);
    else semanticOut.push([name, literal]);
  }

  // 4. 组装输出（page 选择器块 + 全字面量，注释用 // 静默注释不进入 WXSS 产物）
  const lines = [
    '// ==========================================================',
    '// AUTO-GENERATED FILE — DO NOT EDIT',
    '// 由 frontend/scripts/generate-miniapp-tokens.js 自动生成，勿手改',
    `// 生成时间：${new Date().toISOString()}`,
    '// 来源文件：',
    `//   - frontend/src/styles/tokens/_primitives.css`,
    `//   - frontend/src/styles/tokens/colors.css（:root 暗色块，亮色主题已忽略）`,
    '// 说明：',
    '//   - 全部为字面量（内部 var 引用已全部解析），最大化 WXSS 兼容',
    '//   - rgb 空格语法已归一化为逗号语法，裸三元组已包装为 rgb()',
    '//   - 仅含颜色/渐变/阴影类 token；--font-* 与长度类 token 不迁移',
    '//   - 用法：app.scss 顶部 @import 本文件，页面以 var 函数引用 --token-name',
    '// ==========================================================',
    '',
    'page {',
  ];

  lines.push('  /* 原始调色板（--p-*，三元组已包装为 rgb()） */');
  for (const [name, literal] of primitivesOut) {
    lines.push(`  ${name}: ${literal};`);
  }
  lines.push('');
  lines.push('  /* 语义色板（colors.css 暗色主题：背景/文字/品牌/玻璃/渐变/阴影/图表） */');
  for (const [name, literal] of semanticOut) {
    lines.push(`  ${name}: ${literal};`);
  }
  lines.push('}');
  lines.push('');

  // 5. 写出（目录不存在则创建）
  const outDir = path.dirname(OUTPUT_FILE);
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }
  fs.writeFileSync(OUTPUT_FILE, lines.join('\n'), 'utf-8');

  // 6. 生成核对信息
  console.log(`[ok] 已生成小程序 token 文件：${OUTPUT_FILE}`);
  console.log(`     原始调色板（--p-*）：${primitivesOut.length} 项`);
  console.log(`     语义色板（colors.css 暗色块）：${semanticOut.length} 项`);
  if (skipped.length > 0) {
    console.log(`     已过滤 ${skipped.length} 项（非颜色/渐变/阴影类）：`);
    for (const [name, literal] of skipped) {
      console.log(`       - ${name}: ${literal}`);
    }
  }
}

main();
