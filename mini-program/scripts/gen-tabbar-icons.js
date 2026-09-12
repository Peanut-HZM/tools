#!/usr/bin/env node
/**
 * tabBar 图标程序化生成脚本（零依赖，仅 node 标准库 fs/zlib/path）
 *
 * 用途：一键生成 4 个 tabBar 图标（tool / message / file / profile）的
 *       普通态与激活态共 8 张 81×81 PNG，输出到 src/assets/icons/。
 *
 * 为什么手写 PNG 而不用图像库 / 设计稿导出：
 * 1. 零依赖：不引入任何 npm 包，脚本随仓库分发即可运行，CI 与本地行为一致；
 * 2. 可复现：同版本脚本生成的 PNG 字节级一致，图标进入版本管理后可追溯、可回滚；
 * 3. 可改色重生成：品牌色调整时只需修改下方 COLORS 常量，一键重出全部 8 张，
 *    避免"设计稿改色 → 手动逐张导出 → 容易漏改/尺寸不一"的流程。
 *
 * 绘制方案说明（自选：带符号距离场 SDF 判定，而非逐点 setPixel 硬描）：
 * - 每个像素按其到图形边界的符号距离计算覆盖度（边界半覆盖、向两侧 1px 线性渐变），
 *   在 81px 小画布上圆角 / 圆弧依然平滑无锯齿；
 * - 距离场描边天然形成"圆头线帽 + 圆角连接"，与 Web 端线性图标
 *   （24 网格 / 2px 描边 / stroke-linecap: round）的视觉语言一致；
 *   换算到本画布：图形区域 48×48（= 24 网格 ×2），等效线宽 4px（= 2px ×2）。
 */
'use strict';

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

/* ============================================================
 * 一、PNG 手写编码（IHDR / IDAT / IEND + CRC32）
 * ============================================================ */

// CRC32 查表法（标准多项式 0xEDB88320，反射形式）
const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c >>> 0;
  }
  return table;
})();

// 计算一段数据的 CRC32（用于 PNG chunk 完整性校验字段）
function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) {
    c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

// 组装单个 PNG chunk：长度(4B 大端) + 类型(4B ASCII) + 数据 + CRC32(类型+数据)
function makeChunk(type, data) {
  const typeBuf = Buffer.from(type, 'ascii');
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length, 0);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])), 0);
  return Buffer.concat([len, typeBuf, data, crc]);
}

/**
 * 将 RGBA 像素缓冲编码为 PNG 文件内容
 * 规格：bit depth 8、color type 6（RGBA，直通 alpha 非预乘）
 * 注意坑点：IDAT 的原始像素流每行前置 1 字节滤波类型，此处固定写 0（None）
 */
function encodePng(width, height, rgba) {
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  // IHDR 数据块（固定 13 字节）：宽、高、位深、颜色类型、压缩/滤波/隔行方式
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; // bit depth: 8
  ihdr[9] = 6; // color type: 6 = RGBA
  ihdr[10] = 0; // compression: deflate
  ihdr[11] = 0; // filter method: 0（规范固定值）
  ihdr[12] = 0; // interlace: 不隔行

  // 原始像素流：每行 = 1 字节滤波类型(0) + 宽×4 字节 RGBA
  const stride = width * 4;
  const raw = Buffer.alloc(height * (1 + stride));
  for (let y = 0; y < height; y++) {
    const rowStart = y * (1 + stride);
    raw[rowStart] = 0; // 每行行首滤波字节：0 = None
    rgba.copy(raw, rowStart + 1, y * stride, (y + 1) * stride);
  }

  // IDAT 使用 zlib 格式 deflate（zlib.deflateSync 输出即带 zlib 头）
  const idat = zlib.deflateSync(raw, { level: 9 });

  return Buffer.concat([
    signature,
    makeChunk('IHDR', ihdr),
    makeChunk('IDAT', idat),
    makeChunk('IEND', Buffer.alloc(0)),
  ]);
}

/* ============================================================
 * 二、几何 / 距离场工具
 * ============================================================ */

const clamp01 = (v) => Math.min(1, Math.max(0, v));

// 由符号距离计算覆盖度：d <= -0.5 全覆盖，d >= 0.5 全透明，中间 1px 线性抗锯齿
const coverage = (d) => clamp01(0.5 - d);

// 描边覆盖度：|d| - halfW <= 0 为带内，等效线宽 = halfW * 2
const stroke = (d, halfW) => coverage(Math.abs(d) - halfW);

// 填充覆盖度：d <= 0 为内部
const fill = (d) => coverage(d);

// 到圆的符号距离（内部为负）
function sdCircle(px, py, cx, cy, r) {
  return Math.hypot(px - cx, py - cy) - r;
}

// 到圆角矩形的符号距离（cx/cy 中心，hw/hh 半宽半高，r 圆角半径，描边路径在中心线上）
function sdRoundRect(px, py, cx, cy, hw, hh, r) {
  const qx = Math.abs(px - cx) - (hw - r);
  const qy = Math.abs(py - cy) - (hh - r);
  const outside = Math.hypot(Math.max(qx, 0), Math.max(qy, 0));
  const inside = Math.min(Math.max(qx, qy), 0);
  return outside + inside - r;
}

// 到线段 ab 的距离（非符号；用于描边时端点自然形成圆头线帽）
function sdSegment(px, py, ax, ay, bx, by) {
  const abx = bx - ax;
  const aby = by - ay;
  const apx = px - ax;
  const apy = py - ay;
  const t = Math.min(1, Math.max(0, (apx * abx + apy * aby) / (abx * abx + aby * aby)));
  return Math.hypot(apx - abx * t, apy - aby * t);
}

/**
 * 构造凸多边形的符号距离函数（内部为负，精确）
 * 实现思路：
 * - 预计算每条边的外法线；法线方向用"背离多边形重心"判定，
 *   从而对顶点排列顺序 / 屏幕坐标系（y 向下）不敏感；
 * - 求值时：内部（所有半平面距离 <= 0）取各边距离最大值；
 *   外部取到各边线段距离最小值（凸多边形下即到边界的精确距离）。
 */
function makeConvexPolygon(verts) {
  const cx = verts.reduce((s, v) => s + v[0], 0) / verts.length;
  const cy = verts.reduce((s, v) => s + v[1], 0) / verts.length;
  const edges = [];
  for (let i = 0; i < verts.length; i++) {
    const a = verts[i];
    const b = verts[(i + 1) % verts.length];
    const ex = b[0] - a[0];
    const ey = b[1] - a[1];
    const len = Math.hypot(ex, ey);
    // 法线两个候选方向，选与"重心指向"点积为负的一侧（即朝外）
    let nx = ey / len;
    let ny = -ex / len;
    if (nx * (cx - a[0]) + ny * (cy - a[1]) > 0) {
      nx = -nx;
      ny = -ny;
    }
    edges.push({ ax: a[0], ay: a[1], bx: b[0], by: b[1], nx, ny, off: nx * a[0] + ny * a[1] });
  }
  return function (px, py) {
    let maxHalfPlane = -Infinity;
    let minSegDist = Infinity;
    let inside = true;
    for (const e of edges) {
      const h = e.nx * px + e.ny * py - e.off;
      if (h > 0) inside = false;
      if (h > maxHalfPlane) maxHalfPlane = h;
      const d = sdSegment(px, py, e.ax, e.ay, e.bx, e.by);
      if (d < minSegDist) minSegDist = d;
    }
    return inside ? maxHalfPlane : minSegDist;
  };
}

// 多个形状求并集：同色图标取最大覆盖度即可，避免交叠处出现半透明接缝
function unionCoverage(shapes, px, py) {
  let a = 0;
  for (let i = 0; i < shapes.length; i++) {
    const c = shapes[i](px, py);
    if (c > a) a = c;
    if (a >= 1) return 1;
  }
  return a;
}

/* ============================================================
 * 三、图标几何定义（坐标系：像素中心坐标，画布中心 C = 40.5）
 * ============================================================ */

const SIZE = 81; // 微信 tabBar 图标建议尺寸 81×81
const C = SIZE / 2; // 画布中心（像素中心坐标下即 40.5）
const HALF_W = 2; // 描边半宽 → 等效线宽 4px（= Web 端 24 网格上的 2px）
const CONTENT_HALF = 24; // 图形区域半径 → 约 48×48 居中

// tool：2×2 圆角方块网格（线性描边风格，对应 Web 端 layout-grid 类图标）
// 几何：每个方块中心线 18×18、圆角 5，中心相对画布中心偏移 ±13；
//       外缘 13+9+2 = 24 恰好贴合 48×48 内容区，方块间视觉留白 4px
function drawTool() {
  const shapes = [];
  const off = 13;
  const half = 9;
  const radius = 5;
  for (const dx of [-off, off]) {
    for (const dy of [-off, off]) {
      shapes.push((x, y) => stroke(sdRoundRect(x, y, C + dx, C + dy, half, half, radius), HALF_W));
    }
  }
  return shapes;
}

// message：对话气泡（圆角矩形描边 + 左下实心小三角尾巴）
// 几何：气泡中心线上移 4.5 给尾巴让位，外缘 y 20..52；
//       三角尾巴从气泡下边探出至 y≈61，指向左下
function drawMessage() {
  const shapes = [];
  shapes.push((x, y) => stroke(sdRoundRect(x, y, C, C - 4.5, 19, 14, 10), HALF_W));
  // 左下小三角尾巴（实心；与描边同色，交叠处走并集，无接缝）
  const tail = makeConvexPolygon([
    [C - 7.5, C + 8.5],
    [C + 2.5, C + 8.5],
    [C - 12.5, C + 20.5],
  ]);
  shapes.push((x, y) => fill(tail(x, y)));
  return shapes;
}

// file：文档（切角矩形描边 + 两横线，切角即"折角"）
// 几何：轮廓为凸五边形，顶点内收 3px 后整体外扩（膨胀）3px，
//       在精确多边形距离场上自然获得半径 3 的圆角；
//       外缘 x ±19、y ±24，垂直方向恰好撑满 48 内容区
function drawFile() {
  const shapes = [];
  const poly = makeConvexPolygon([
    [-14, -19], // 左上
    [3, -19], // 上边（折角起点）
    [14, -8], // 右上斜切（折角斜边）
    [14, 19], // 右下
    [-14, 19], // 左下
  ]);
  const INFLATE = 3; // 外扩量 = 圆角半径（距离场减常数 = 整体膨胀并圆化凸角）
  shapes.push((x, y) => stroke(poly(x - C, y - C) - INFLATE, HALF_W));
  // 文档内两横线（圆头线帽）
  shapes.push((x, y) => stroke(sdSegment(x, y, C - 9, C - 5, C + 9, C - 5), HALF_W));
  shapes.push((x, y) => stroke(sdSegment(x, y, C - 9, C + 7, C + 9, C + 7), HALF_W));
  return shapes;
}

// profile：人形（头圆描边 + 肩部半圆弧 + 两侧短竖线）
// 几何：头圆中心 (C, 28) 半径 8.5；肩弧为半径 14.5 圆的上半段（圆环描边被
//       "y <= 圆心" 半平面裁剪），两端由短竖线向下延伸并以圆头收尾
function drawProfile() {
  const shapes = [];
  shapes.push((x, y) => stroke(sdCircle(x, y, C, 28, 8.5), HALF_W));
  const shCy = 60; // 肩弧圆心 y
  const shR = 14.5; // 肩弧半径（中心线）
  shapes.push((x, y) => {
    const ring = Math.abs(sdCircle(x, y, C, shCy, shR)) - HALF_W;
    const cut = y - shCy; // 半平面约束：仅保留上半（y <= shCy）
    // 两个区域的交集用距离取 max 模拟（边界处仍有 1px 抗锯齿）
    return coverage(Math.max(ring, cut));
  });
  // 两侧短竖线：衔接肩弧端点并向下延伸，端点圆头收底
  shapes.push((x, y) => stroke(sdSegment(x, y, C - shR, shCy - 2, C - shR, shCy + 2.5), HALF_W));
  shapes.push((x, y) => stroke(sdSegment(x, y, C + shR, shCy - 2, C + shR, shCy + 2.5), HALF_W));
  return shapes;
}

/* ============================================================
 * 四、颜色与渲染输出
 * ============================================================ */

// 与 src/app.config.ts 中 tabBar.color / tabBar.selectedColor 严格一致
const COLORS = {
  normal: [0x5c, 0x67, 0x84], // #5C6784 普通态
  active: [0x8b, 0x9b, 0xff], // #8B9BFF 激活态
};

const ICONS = [
  { name: 'tool', draw: drawTool },
  { name: 'message', draw: drawMessage },
  { name: 'file', draw: drawFile },
  { name: 'profile', draw: drawProfile },
];

const OUT_DIR = path.join(__dirname, '..', 'src', 'assets', 'icons');

// 将一组形状（距离场覆盖度函数）渲染为 RGBA 缓冲：颜色由参数注入，一次出任意态
function renderIcon(shapes, color) {
  const rgba = Buffer.alloc(SIZE * SIZE * 4, 0); // 默认全透明底
  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      // 采样像素中心点；直通 alpha：RGB 恒为注入色，A 携带覆盖度
      const a = unionCoverage(shapes, x + 0.5, y + 0.5);
      if (a <= 0) continue;
      const i = (y * SIZE + x) * 4;
      rgba[i] = color[0];
      rgba[i + 1] = color[1];
      rgba[i + 2] = color[2];
      rgba[i + 3] = Math.round(a * 255);
    }
  }
  return rgba;
}

/* ============================================================
 * 五、自检（读回文件逐项断言）
 * ============================================================ */

function fail(msg) {
  console.error('自检失败: ' + msg);
  process.exit(1);
}

function assert(cond, msg) {
  if (!cond) fail(msg);
}

// 解析 PNG：校验签名与每个 chunk 的 CRC，返回 IHDR 元数据与解压后的原始像素流
function parsePng(buf) {
  const SIG = [137, 80, 78, 71, 13, 10, 26, 10];
  for (let i = 0; i < 8; i++) {
    assert(buf[i] === SIG[i], 'PNG 签名不正确');
  }
  let off = 8;
  const chunks = {};
  const idatParts = [];
  while (off < buf.length) {
    const len = buf.readUInt32BE(off);
    const type = buf.toString('ascii', off + 4, off + 8);
    const data = buf.subarray(off + 8, off + 8 + len);
    // CRC 覆盖"类型 + 数据"，读回校验确保文件未被破坏
    const expect = buf.readUInt32BE(off + 8 + len);
    const actual = crc32(buf.subarray(off + 4, off + 8 + len));
    assert(expect === actual, type + ' chunk CRC 校验失败');
    if (type === 'IDAT') idatParts.push(data);
    else chunks[type] = data;
    off += 12 + len;
  }
  const ihdr = chunks.IHDR;
  assert(ihdr && ihdr.length === 13, 'IHDR 缺失或长度错误');
  assert(chunks.IEND && chunks.IEND.length === 0, 'IEND 缺失');
  return {
    width: ihdr.readUInt32BE(0),
    height: ihdr.readUInt32BE(4),
    bitDepth: ihdr[8],
    colorType: ihdr[9],
    raw: zlib.inflateSync(Buffer.concat(idatParts)),
  };
}

const MIN_NON_EMPTY = 350; // 描边类图标面积下限（估算每枚 >= 430，留裕量）
const BBOX_LO = 14; // 内容区 16.5..64.5，抗锯齿最多外溢约 1px，取宽松边界
const BBOX_HI = 67;

// 读取生成的 PNG 并逐项断言；返回统计信息供清单打印
function selfCheck(file, color) {
  const buf = fs.readFileSync(file);
  const meta = parsePng(buf);

  // 1) IHDR 断言：尺寸 81×81、8bit、RGBA
  assert(meta.width === SIZE && meta.height === SIZE, file + ': 尺寸应为 81×81，实际 ' + meta.width + '×' + meta.height);
  assert(meta.bitDepth === 8, file + ': 位深应为 8');
  assert(meta.colorType === 6, file + ': 颜色类型应为 6（RGBA）');

  // 2) 原始像素流断言：长度、行首滤波字节
  const stride = SIZE * 4;
  assert(meta.raw.length === SIZE * (1 + stride), file + ': 像素流长度不符');
  for (let y = 0; y < SIZE; y++) {
    assert(meta.raw[y * (1 + stride)] === 0, file + ': 第 ' + y + ' 行滤波类型非 0');
  }

  // 3) 像素断言：非空像素数、颜色恒等于注入色、内容包围盒、四角透明
  let nonEmpty = 0;
  let opaque = 0;
  let colorMismatch = 0;
  let minX = SIZE;
  let minY = SIZE;
  let maxX = -1;
  let maxY = -1;
  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      const i = y * (1 + stride) + 1 + x * 4;
      const a = meta.raw[i + 3];
      if (a === 0) continue;
      nonEmpty++;
      if (meta.raw[i] !== color[0] || meta.raw[i + 1] !== color[1] || meta.raw[i + 2] !== color[2]) {
        colorMismatch++;
      }
      if (a === 255) {
        opaque++;
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      }
    }
  }
  assert(nonEmpty >= MIN_NON_EMPTY, file + ': 非空像素 ' + nonEmpty + ' 低于下限 ' + MIN_NON_EMPTY);
  assert(colorMismatch === 0, file + ': 有 ' + colorMismatch + ' 个像素 RGB 与注入色不符');
  assert(opaque > 0, file + ': 无完全不透明像素');
  assert(minX >= BBOX_LO && minY >= BBOX_LO && maxX <= BBOX_HI && maxY <= BBOX_HI, file + ': 图形越出预期内容区');
  assert(maxX - minX >= 30 && maxY - minY >= 30, file + ': 图形过小，绘制疑似异常');
  for (const [cx, cy] of [[0, 0], [SIZE - 1, 0], [0, SIZE - 1], [SIZE - 1, SIZE - 1]]) {
    assert(meta.raw[cy * (1 + stride) + 1 + cx * 4 + 3] === 0, file + ': 画布四角应为透明底');
  }

  return { bytes: buf.length, nonEmpty, opaque, bbox: [minX, minY, maxX, maxY] };
}

/* ============================================================
 * 六、主流程
 * ============================================================ */

function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const outputs = [];
  for (const { name, draw } of ICONS) {
    const shapes = draw(); // 几何与颜色解耦：同一组形状注入不同颜色即出两态
    for (const [state, color] of Object.entries(COLORS)) {
      const suffix = state === 'active' ? '-active' : '';
      const file = path.join(OUT_DIR, name + suffix + '.png');
      fs.writeFileSync(file, encodePng(SIZE, SIZE, renderIcon(shapes, color)));
      const stat = selfCheck(file, color);
      outputs.push({ name: path.basename(file), state, ...stat });
    }
  }

  // 打印 8 张输出清单
  console.log('tabBar 图标生成完成（81×81 RGBA 透明底，等效线宽 4px，图形居中约 48×48）:');
  for (const o of outputs) {
    console.log(
      '  ' +
        o.name.padEnd(20) +
        String(o.bytes).padStart(6) +
        ' B   非空像素 ' +
        String(o.nonEmpty).padStart(4) +
        '   不透明 ' +
        String(o.opaque).padStart(4) +
        '   包围盒 [' +
        o.bbox.join(', ') +
        ']   [OK]'
    );
  }
  console.log(
    '自检 8/8 通过: PNG 签名 / chunk CRC / IHDR(81×81, 8bit, RGBA) / 行滤波字节 / ' +
      '非空像素数 / 颜色一致性 / 包围盒 / 四角透明'
  );
}

main();
