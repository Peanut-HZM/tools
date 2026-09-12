/**
 * 后端工具 iconColor（'bg-blue-500' 式 Tailwind 类名）→ tint 色板类名映射。
 * tint 色板定义在 styles/glass.css，为"低饱和色底 + 同色描边 + 同色图标"。
 */
const TINT_NAMES = ['blue', 'violet', 'emerald', 'indigo', 'orange', 'red', 'purple', 'cyan'] as const;

export function iconTintClass(iconColor?: string): string {
  // iconColor 形如 'bg-blue-500'，取中间色名段
  const match = iconColor?.match(/^bg-([a-z]+)-\d+$/);
  const name = match?.[1];
  if (name && (TINT_NAMES as readonly string[]).includes(name)) {
    return `tint tint-${name}`;
  }
  return 'tint tint-violet';
}
