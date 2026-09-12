/**
 * 后端工具 iconColor（'bg-blue-500' 式 Tailwind 类名）→ 小程序 tint 类名 + 图标色值。
 *
 * 与 Web 端 utils/iconTint.ts 同构（同样的 'bg-{color}-{n}' 正则解析与 violet 兜底），
 * tint 色板定义在 styles/_glass.scss，色值照抄 Web 端 styles/glass.css 的 tint 段。
 *
 * 为什么除类名外还要返回色值：小程序 Image 组件不继承 CSS color，
 * SVG 图标渲染成 Image 后无法通过 tint 类的 color 生效，
 * 必须把颜色作为 Icon 组件的 color prop 直接烘进 SVG 字符串
 * （详见 components/Icon/index.tsx 的 data-URI 方案说明）。
 */

/** 单个 tint 的呈现信息：容器类名 + 同源图标色值（与 _glass.scss tint 段一致） */
interface TintInfo {
  className: string;
  color: string;
}

/** 8 色 tint 映射：色名 → { 类名, 图标色值 }（色值照抄 Web glass.css tint 段） */
const TINT_MAP: Record<string, TintInfo> = {
  blue: { className: 'tint tint-blue', color: '#60A5FA' },
  violet: { className: 'tint tint-violet', color: '#8B9BFF' },
  emerald: { className: 'tint tint-emerald', color: '#34D399' },
  indigo: { className: 'tint tint-indigo', color: '#818CF8' },
  orange: { className: 'tint tint-orange', color: '#FB923C' },
  red: { className: 'tint tint-red', color: '#F87171' },
  purple: { className: 'tint tint-purple', color: '#C084FC' },
  cyan: { className: 'tint tint-cyan', color: '#22D3EE' },
};

/** 未识别/缺省时的兜底 tint（与 Web iconTint.ts 一致，回退 violet） */
const TINT_FALLBACK: TintInfo = TINT_MAP.violet;

/**
 * 由后端 iconColor 解析 tint 容器类名与同源图标色值。
 * 参数：iconColor - 形如 'bg-blue-500' 的 Tailwind 类名（可空）
 * 返回：{ className, color }；无法识别时回退 tint-violet
 */
export function tintColorOf(iconColor?: string): TintInfo {
  // iconColor 形如 'bg-blue-500'，取中间色名段
  const match = iconColor?.match(/^bg-([a-z]+)-\d+$/);
  const name = match?.[1];
  if (name && TINT_MAP[name]) {
    return TINT_MAP[name];
  }
  return TINT_FALLBACK;
}
