import { useTheme } from '@/lib/theme';

const radiusClasses = { sm: 'rounded-sm', md: 'rounded-md', lg: 'rounded-lg', xl: 'rounded-xl', '2xl': 'rounded-2xl', pill: 'rounded-pill' } as const;
const shadowClasses = { sm: 'shadow-sm', md: 'shadow-md', lg: 'shadow-lg', xl: 'shadow-xl', glow: 'shadow-glow', focus: 'shadow-focus' } as const;

/**
 * /dev/components —— 设计系统 token 验证页
 * 仅用于开发期视觉校验，不进入生产 bundle。
 */
export default function DevComponentsPage() {
  const { theme, resolved, setTheme } = useTheme();

  return (
    <div className="p-8 space-y-12">
      <h1 className="text-display-md font-semibold">Design System Token 验证</h1>

      {/* 主题切换器 */}
      <section className="space-y-4">
        <h2 className="text-heading-lg font-medium">主题</h2>
        <div className="flex gap-2">
          {(['dark', 'light', 'system'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className={`px-4 py-2 rounded-md transition-all ${
                theme === t
                  ? 'bg-accent text-ink-inverse shadow-glow'
                  : 'bg-surface-2 text-ink hover:bg-surface-3'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <p className="text-body-md text-ink-muted">当前 resolved: {resolved}</p>
      </section>

      {/* 颜色 */}
      <section className="space-y-4">
        <h2 className="text-heading-lg font-medium">颜色 Token</h2>
        <div className="grid grid-cols-6 gap-4">
          {[
            { name: 'canvas',    cls: 'bg-canvas' },
            { name: 'surface-1', cls: 'bg-surface-1' },
            { name: 'surface-2', cls: 'bg-surface-2' },
            { name: 'surface-3', cls: 'bg-surface-3' },
            { name: 'accent',    cls: 'bg-accent' },
            { name: 'accent-sec',cls: 'bg-accent-secondary' },
            { name: 'accent-warm', cls: 'bg-accent-warm' },
            { name: 'success',   cls: 'bg-accent-success' },
            { name: 'warning',   cls: 'bg-accent-warning' },
            { name: 'danger',    cls: 'bg-accent-danger' },
            { name: 'info',      cls: 'bg-accent-info' },
            { name: 'border',    cls: 'bg-border' },
          ].map((c) => (
            <div key={c.name} className="space-y-2">
              <div className={`${c.cls} h-16 rounded-lg border border-border`} />
              <p className="text-body-sm text-ink-muted">{c.name}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 字体 */}
      <section className="space-y-4">
        <h2 className="text-heading-lg font-medium">字体栈</h2>
        <div className="space-y-3">
          <p className="font-sans text-body-lg">Sans: The quick brown fox jumps over the lazy dog. 敏捷的棕色狐狸跳过了懒狗。</p>
          <p className="font-mono text-body-lg">Mono: const x = 1234; // 等宽字体示例</p>
          <p className="font-serif text-body-lg">Serif: The quick brown fox jumps over the lazy dog. 敏捷的棕色狐狸跳过了懒狗。</p>
          <p className="font-tabular text-body-lg">Tabular-nums: 1234 5678 9012 3456 (对齐测试)</p>
        </div>
      </section>

      {/* 字号 */}
      <section className="space-y-4">
        <h2 className="text-heading-lg font-medium">字号层级</h2>
        <div className="space-y-2">
          <p className="text-display-2xl">Display 2XL</p>
          <p className="text-display-xl">Display XL</p>
          <p className="text-display-lg">Display LG</p>
          <p className="text-display-md">Display MD</p>
          <p className="text-display-sm">Display SM</p>
          <p className="text-heading-lg">Heading LG</p>
          <p className="text-heading-md">Heading MD</p>
          <p className="text-heading-sm">Heading SM</p>
          <p className="text-body-lg">Body LG</p>
          <p className="text-body-md">Body MD</p>
          <p className="text-body-sm">Body SM</p>
          <p className="text-caption">Caption</p>
        </div>
      </section>

      {/* 圆角 */}
      <section className="space-y-4">
        <h2 className="text-heading-lg font-medium">圆角</h2>
        <div className="flex gap-4">
          {(['sm', 'md', 'lg', 'xl', '2xl', 'pill'] as const).map((r) => (
            <div key={r} className={`bg-accent w-20 h-20 ${radiusClasses[r]} flex items-center justify-center text-ink-inverse text-body-sm`}>
              {r}
            </div>
          ))}
        </div>
      </section>

      {/* 阴影 */}
      <section className="space-y-4">
        <h2 className="text-heading-lg font-medium">阴影</h2>
        <div className="flex gap-6">
          {(['sm', 'md', 'lg', 'xl', 'glow', 'focus'] as const).map((s) => (
            <div key={s} className={`bg-surface-2 ${shadowClasses[s]} w-24 h-24 rounded-lg flex items-center justify-center text-ink-muted text-body-sm`}>
              {s}
            </div>
          ))}
        </div>
      </section>

      {/* Logo 渐变 */}
      <section className="space-y-4">
        <h2 className="text-heading-lg font-medium">Logo 渐变</h2>
        <p className="text-display-md font-['Pacifico'] bg-gradient-to-br from-accent to-accent-secondary bg-clip-text text-transparent">
          工具箱
        </p>
      </section>
    </div>
  );
}
