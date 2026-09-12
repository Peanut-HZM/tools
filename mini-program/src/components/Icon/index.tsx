/**
 * 小程序 SVG 线性图标组件（玻璃光晕改版 Task 3）。
 *
 * 方案说明（为什么走 data-URI + Image）：
 * - 小程序不支持内联 <svg> 标签，也不支持图标字体按色渲染（Image 组件不继承
 *   CSS color），因此无法像 Web 端那样用 currentColor 跟随文字色。
 * - 采用：把 SVG 字符串（颜色已烘入 stroke 属性）经 encodeURIComponent 拼
 *   data:image/svg+xml data-URI，交给 Taro <Image> 渲染。
 * - 代价是颜色必须作为 prop 显式传入：tint 场景由调用方经
 *   utils/tint.ts 的 tintColorOf() 取同源色值传入（色板见 styles/_glass.scss）。
 *
 * 图标风格：24×24 viewBox 线性风格，stroke-width 1.8、round cap/join，
 * 全部为简单几何线段/圆弧手绘（部分参照 lucide 官方 path）。
 */
import { useMemo } from 'react';
import { Image } from '@tarojs/components';

/** 图标 path 表：图标名 → 若干条 <path d> 子路径（fill 全局 none，仅描边） */
const ICON_PATHS: Record<string, string[]> = {
  // JSON 花括号 + 中轴三点
  json: [
    'M8 3H7a2 2 0 0 0-2 2v4a2 2 0 0 1-2 2 2 2 0 0 1 2 2v4a2 2 0 0 0 2 2h1',
    'M16 3h1a2 2 0 0 1 2 2v4a2 2 0 0 0 2 2 2 2 0 0 0-2 2v4a2 2 0 0 1-2 2h-1',
    'M12 8v.01',
    'M12 12v.01',
    'M12 16v.01',
  ],
  // 代码尖括号
  code: ['M9 6L3.5 12L9 18', 'M15 6L20.5 12L15 18'],
  // 图片：圆角框 + 太阳 + 山形
  image: [
    'M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z',
    'M9 7a2 2 0 1 0 0 4a2 2 0 1 0 0-4',
    'M21 15l-3.09-3.09a2 2 0 0 0-2.82 0L6 21',
  ],
  // 麦克风：胶囊 + 拾音弧 + 支杆
  mic: ['M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z', 'M19 10v2a7 7 0 0 1-14 0v-2', 'M12 19v3'],
  // 日历
  calendar: ['M8 2v4', 'M16 2v4', 'M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z', 'M3 10h18'],
  // 钥匙：圆环 + 斜柄 + 双齿
  key: [
    'M7.8 11.9a4.3 4.3 0 1 0 0 8.6a4.3 4.3 0 1 0 0-8.6',
    'M10.9 13.1L20 4',
    'M15.6 8.4l2.9 2.9',
    'M13 11l2.5 2.5',
  ],
  // 机器人：天线 + 圆角机身 + 双耳 + 双眼
  robot: [
    'M12 8V4H8',
    'M6 8h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z',
    'M2 14h2',
    'M20 14h2',
    'M15 13v2',
    'M9 13v2',
  ],
  // 终端：提示符 + 命令行
  terminal: ['M4 17l6-6-6-6', 'M12 19h8'],
  // 数据库：三层圆柱
  database: ['M3 5a9 3 0 1 0 18 0a9 3 0 1 0-18 0', 'M3 5v14a9 3 0 0 0 18 0V5', 'M3 12a9 3 0 0 0 18 0'],
  // 编辑（铅笔）
  edit: ['M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5L2 22l1.5-5.5L17 3z', 'M14.5 5.5l4 4'],
  // 锁：锁体 + 锁梁
  lock: ['M5 11h14a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2z', 'M7 11V7a5 5 0 0 1 10 0v4'],
  // 盾牌
  shield: ['M12 2l8 3.5V12c0 4.8-3.2 8-8 9.5-4.8-1.5-8-4.7-8-9.5V5.5L12 2z'],
  // 地球：外圆 + 经线 + 赤道
  globe: ['M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20', 'M12 2a14.5 14.5 0 0 0 0 20a14.5 14.5 0 0 0 0-20', 'M2 12h20'],
  // 下载：托盘 + 下箭头
  download: ['M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4', 'M7 10l5 5 5-5', 'M12 15V3'],
  // 上传：托盘 + 上箭头
  upload: ['M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4', 'M7 8l5-5 5 5', 'M12 3v12'],
  // 搜索：放大镜
  search: ['M11 3a8 8 0 1 0 0 16a8 8 0 1 0 0-16', 'M21 21l-4.35-4.35'],
  // 文件：折角纸页
  file: ['M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z', 'M14 2v4a2 2 0 0 0 2 2h4'],
  // 分享：三节点两连线
  share: [
    'M18 2a3 3 0 1 0 0 6a3 3 0 1 0 0-6',
    'M6 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6',
    'M18 16a3 3 0 1 0 0 6a3 3 0 1 0 0-6',
    'M8.6 13.5l6.8 4',
    'M15.4 6.5l-6.8 4',
  ],
  // 视频：屏幕 + 摄像头三角
  video: ['M4 6h10a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z', 'M16 10.5L21 7v10l-5-3.5'],
  // 音乐：双音符
  music: ['M9 18V5l12-2v13', 'M6 15a3 3 0 1 0 0 6a3 3 0 1 0 0-6', 'M18 13a3 3 0 1 0 0 6a3 3 0 1 0 0-6'],
  // 插头（API/连接）
  plug: ['M12 22v-5', 'M9 8V2', 'M15 8V2', 'M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8z'],
  // 扳手（工具箱兜底图标）
  tools: [
    'M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z',
  ],
  // 灯泡（学习/创意）
  lightbulb: [
    'M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5',
    'M9 18h6',
    'M10 22h4',
  ],
  // 关闭
  close: ['M18 6L6 18', 'M6 6l12 12'],
  // 右箭头
  'chevron-right': ['M9 18l6-6-6-6'],
  // 用户
  user: ['M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2', 'M12 3a4 4 0 1 0 0 8a4 4 0 1 0 0-8'],
  // 设置：双圆齿轮 + 八向齿
  settings: [
    'M12 5.5a6.5 6.5 0 1 0 0 13a6.5 6.5 0 1 0 0-13',
    'M12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6',
    'M18.5 12H21',
    'M12 18.5V21',
    'M5.5 12H3',
    'M12 5.5V3',
    'M18.4 5.6L16.6 7.4',
    'M18.4 18.4L16.6 16.6',
    'M5.6 18.4L7.4 16.6',
    'M5.6 5.6L7.4 7.4',
  ],
  // 邮件：信封
  mail: ['M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z', 'M22 7l-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7'],
  // 警告三角
  warning: ['m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3', 'M12 9v4', 'M12 17h.01'],
};

/** 兜底图标名：未知图标一律回退到扳手（工具箱语义） */
const FALLBACK_ICON = 'tools';

/**
 * 后端 tool.icon 存的是 Font Awesome class 字符串（如 'fa-key'、'fas fa-code'），
 * 映射到本组件的图标名；覆盖 ToolCard 原 23 项 fa-* 及 Web 端 iconResolver 常用项。
 */
const FA_TO_ICON: Record<string, string> = {
  'fa-file-image': 'image',
  'fa-microphone': 'mic',
  'fa-share-alt': 'share',
  'fa-share': 'share',
  'fa-calendar-alt': 'calendar',
  'fa-calendar': 'calendar',
  'fa-plug': 'plug',
  'fa-code': 'code',
  'fa-file-code': 'code',
  'fa-key': 'key',
  'fa-robot': 'robot',
  'fa-image': 'image',
  'fa-music': 'music',
  'fa-video': 'video',
  'fa-database': 'database',
  'fa-server': 'database',
  'fa-terminal': 'terminal',
  'fa-edit': 'edit',
  'fa-pen': 'edit',
  'fa-pen-to-square': 'edit',
  'fa-lock': 'lock',
  'fa-shield': 'shield',
  'fa-shield-alt': 'shield',
  'fa-shield-halved': 'shield',
  'fa-globe': 'globe',
  'fa-download': 'download',
  'fa-upload': 'upload',
  'fa-search': 'search',
  'fa-file': 'file',
  'fa-file-alt': 'file',
  'fa-file-lines': 'file',
  'fa-user': 'user',
  'fa-cog': 'settings',
  'fa-gear': 'settings',
  'fa-gears': 'settings',
  'fa-cogs': 'settings',
  'fa-tools': 'tools',
  'fa-wrench': 'tools',
  'fa-lightbulb': 'lightbulb',
};

/** FA class 中可能出现的样式前缀（fas/fa-solid 等），解析时跳过 */
const FA_STYLE_PREFIXES = ['fas', 'far', 'fab', 'fal', 'fat', 'fa-solid', 'fa-regular', 'fa-brands'];

/**
 * 把 tool.icon 字段解析为本组件图标名（与 Web 端 iconResolver 的
 * resolveFaIconName 同思路：兼容 'fas fa-key' 前缀，未知名兜底 'tools'）。
 * 参数：icon - 后端返回的 FA class 字符串或已是内部图标名（可空）
 * 返回：ICON_PATHS 中存在的图标名
 */
export function resolveIconName(icon?: string): string {
  if (!icon) return FALLBACK_ICON;
  const tokens = icon.trim().split(/\s+/);
  // 跳过样式前缀，取第一个真实图标 token
  let name = tokens[tokens.length - 1] || '';
  for (const t of tokens) {
    if (!FA_STYLE_PREFIXES.includes(t)) {
      name = t;
      break;
    }
  }
  if (!name) return FALLBACK_ICON;
  // 已是本组件内部图标名（未来后端迁移后直接可用的路径）
  if (ICON_PATHS[name]) return name;
  // FA class 查表
  if (name.startsWith('fa-')) {
    const mapped = FA_TO_ICON[name];
    return mapped && ICON_PATHS[mapped] ? mapped : FALLBACK_ICON;
  }
  return FALLBACK_ICON;
}

/** Icon 组件属性 */
interface IconProps {
  /** 图标名（ICON_PATHS 的键），未知名自动回退 'tools' */
  name: string;
  /** 渲染尺寸（px，宽高一致），默认 24 */
  size?: number;
  /** 图标颜色（烘入 SVG stroke），默认品牌浅紫 #8B9BFF；tint 场景传 tintColorOf().color */
  color?: string;
  /** 透传给 Image 的类名（可选） */
  className?: string;
}

/**
 * 由 path 表构建已烘色的 SVG data-URI。
 * 参数：paths - path 子路径数组；color - 烘入 stroke 的色值
 * 返回：data:image/svg+xml data-URI 字符串
 */
function buildDataUri(paths: string[], color: string): string {
  // 单引号经 encodeURIComponent 编码，此处属性统一用双引号避免拼接冲突
  const body = paths.map((d) => `<path d="${d}"/>`).join('');
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" ` +
    `stroke="${color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">` +
    `${body}</svg>`;
  // 颜色已直接写入 stroke 属性（currentColor 在 Image 中无法继承）
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

/**
 * SVG 线性图标：内部把 path 表渲染为 data-URI 交给 Image 显示。
 * 用法：<Icon name='json' size={22} color='#8B9BFF' />
 */
export default function Icon({ name, size = 24, color = '#8B9BFF', className }: IconProps) {
  const paths = ICON_PATHS[name] || ICON_PATHS[FALLBACK_ICON];
  // 同名同色的 data-URI 只需计算一次
  const dataUri = useMemo(() => buildDataUri(paths, color), [paths, color]);

  return (
    <Image
      src={dataUri}
      mode='aspectFit'
      className={className}
      style={{ width: `${size}px`, height: `${size}px` }}
    />
  );
}
