# Phase 1: Token + 基建 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立设计系统的地基 —— 6 份 token CSS 文件（颜色/字体/间距/圆角/阴影/动效）+ Tailwind 集成 + Geist 字体加载 + 主题切换 Hook + .bg-mesh 大气背景层 + Logo 渐变填充 + 首页可见呼吸效果。Phase 1 完成后，业务组件**仍然使用旧样式**，但新 token 已就位、可被新原语消费。

**Architecture:** CSS 变量是单一真相源（`:root` 暗色默认 + `:root[data-theme="light"]` 亮色），Tailwind `theme.extend.colors` 把所有语义色映射到 `var(--*)`，让业务组件可以同时使用 `bg-canvas`（Tailwind 类）和 `background: var(--bg-canvas)`（CSS）。主题切换通过 React Context + `data-theme` 属性 + `localStorage` 持久化。.bg-mesh 大气背景通过 fixed 定位 + 多层 radial-gradient + SVG noise overlay 实现。

**Tech Stack:** React 18 + TypeScript + Vite 5 + TailwindCSS 3.3 + clsx + tailwind-merge + tailwindcss-animate + Google Fonts (Geist + HarmonyOS Sans SC + Noto Serif SC)。

## Global Constraints

- 所有色值/字号/间距必须通过 `var(--*)` 引用，**禁止在组件内写死 hex / px**
- `data-theme="dark|light"` 是主题切换唯一入口
- 字体栈必须使用 spec 定义的完整回退链
- `tailwind.config.js` 必须把语义色映射到 `var(--*)`，**禁止扩展具体 hex**
- 渐变签名永远是 `position: fixed; z-index: -1` 最底层，不抢交互焦点
- 所有新增 CSS 必须兼容 `@media (prefers-reduced-motion: reduce)` 兜底
- 本 Phase 不动业务组件（Phase 2+ 才迁移），只建基建
- 本 Phase 不动 `MarkdownEditor/MarkdownEditor.css` 的独立霓虹主题（Phase 4 整合）
- 本 Phase 不动 `themes/cursorThemes.ts`（Phase 4 简化）
- 字体加载用 Google Fonts CDN + `font-display: swap`，**本 Phase 不做 woff2 子集化**（留待 Phase 4 性能优化）
- 构建必须通过 `npm run build`，无 TypeScript 错误、无 Tailwind 编译错误

---

## File Structure

| 路径 | 类型 | 职责 |
|---|---|---|
| `frontend/src/styles/tokens/colors.css` | 新建 | 全部颜色 token（暗色默认 + 亮色覆写 + 渐变签名） |
| `frontend/src/styles/tokens/typography.css` | 新建 | 字体栈 + 13 级字号 + tabular-nums 工具类 |
| `frontend/src/styles/tokens/spacing.css` | 新建 | 4px base 的 12 级间距 |
| `frontend/src/styles/tokens/radius.css` | 新建 | 6 级圆角 |
| `frontend/src/styles/tokens/shadows.css` | 新建 | 5 级阴影 + glow + focus ring（双模式） |
| `frontend/src/styles/tokens/motion.css` | 新建 | 4 条缓动曲线 + 4 档时长 + reduced-motion 兜底 |
| `frontend/src/styles/tokens/index.css` | 新建 | 聚合 6 个 token 文件的入口 |
| `frontend/src/styles/backgrounds.css` | 新建 | `.bg-mesh` + 强度分层 + SVG noise + 呼吸动画 |
| `frontend/src/styles/reset.css` | 新建 | 极简 reset（移除硬编码背景，接入 token） |
| `frontend/src/lib/cn.ts` | 新建 | `clsx` + `tailwind-merge` 封装 |
| `frontend/src/lib/theme.ts` | 新建 | `Theme` 类型 + `ThemeProvider` React Context + `useTheme()` hook + `applyTheme()` 工具函数 |
| `frontend/tailwind.config.js` | 修改 | 接入 token 变量，扩展语义色、字体、阴影、缓动映射 |
| `frontend/index.html` | 修改 | 移除 Font Awesome CDN（Phase 3 才完全迁移，但本 Phase 提前移除），加 Google Fonts 链接 |
| `frontend/src/index.css` | 修改 | 删除硬编码 `#0f172a` / `#e2e8f0`，改为引用 token 变量；保留业务类 `.tool-card` / `.search-input` / `.category-tab` / 自定义滚动条；保留 Monaco 变量高亮类 |
| `frontend/src/main.tsx` | 修改 | 包裹 `ThemeProvider`；引入 `styles/tokens/index.css` + `styles/backgrounds.css` + `styles/reset.css` |
| `frontend/src/components/Layout/Layout.tsx` | 修改 | 在根 div 前插入 `<div class="bg-mesh bg-mesh--subtle">` 占位背景（Phase 3 才按页面细化强度） |
| `frontend/src/components/Header/Header.tsx` | 修改 | Logo 文字加渐变填充 `bg-clip-text` + `bg-gradient-to-br from-accent to-accent-secondary` |

---

## Task 1: 安装新依赖

**Files:**
- Modify: `frontend/package.json`（通过 `npm install` 自动更新）

**Interfaces:**
- Consumes: 无（本任务是最早的基建）
- Produces: `node_modules/` 新增 `clsx`, `tailwind-merge`, `tailwindcss-animate`

- [ ] **Step 1: 安装依赖**

```bash
cd D:/CodeProjects/tools/frontend
npm install clsx tailwind-merge
npm install -D tailwindcss-animate
```

- [ ] **Step 2: 验证安装**

```bash
cd D:/CodeProjects/tools/frontend
node -e "require('clsx'); require('tailwind-merge'); console.log('OK')"
```

Expected: 输出 `OK`，无错误。

- [ ] **Step 3: 提交**

```bash
cd D:/CodeProjects/tools
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(deps): add clsx, tailwind-merge, tailwindcss-animate for design system infrastructure"
```

---

## Task 2: 创建 6 份 token CSS 文件 + index 聚合

**Files:**
- Create: `frontend/src/styles/tokens/colors.css`
- Create: `frontend/src/styles/tokens/typography.css`
- Create: `frontend/src/styles/tokens/spacing.css`
- Create: `frontend/src/styles/tokens/radius.css`
- Create: `frontend/src/styles/tokens/shadows.css`
- Create: `frontend/src/styles/tokens/motion.css`
- Create: `frontend/src/styles/tokens/index.css`

**Interfaces:**
- Consumes: 无（纯 CSS 变量定义）
- Produces: 全局 CSS 变量（`--bg-canvas`, `--accent-primary`, `--font-sans`, `--space-4`, `--radius-md`, `--shadow-lg`, `--ease-stripe`, `--duration-fast` 等 60+ 个变量）

- [ ] **Step 1: 创建目录**

```bash
mkdir -p D:/CodeProjects/tools/frontend/src/styles/tokens
```

- [ ] **Step 2: 创建 `colors.css`**

写入 `frontend/src/styles/tokens/colors.css`：

```css
:root {
  /* === 暗色 (默认) === */
  --bg-canvas:        #0A1A2F;
  --bg-surface-1:     #112D52;
  --bg-surface-2:     #1A3A6B;
  --bg-surface-3:     #2A4A7F;
  --bg-overlay:       rgba(10, 26, 47, 0.72);

  --ink-default:      #F5F7FA;
  --ink-muted:        #B8C2D1;
  --ink-faint:        #6E7A8F;
  --ink-inverse:      #0A1A2F;

  --accent-primary:   #5B6BF5;
  --accent-hover:     #6E7EFF;
  --accent-press:     #4A5AE5;
  --accent-secondary: #A155F7;
  --accent-warm:      #FF8A4C;
  --accent-success:   #34D399;
  --accent-warning:   #FBBF24;
  --accent-danger:    #F87171;
  --accent-info:      #60A5FA;

  --hairline:         rgba(255, 255, 255, 0.08);
  --border-default:   #1F3A65;
  --border-strong:    #2D4F8A;
  --border-accent:    rgba(91, 107, 245, 0.4);

  /* 渐变签名 */
  --gradient-mesh-1:  radial-gradient(ellipse 80% 60% at 20% 0%,
                       rgba(91, 107, 245, 0.18) 0%, transparent 50%);
  --gradient-mesh-2:  radial-gradient(ellipse 70% 50% at 80% 100%,
                       rgba(161, 85, 247, 0.15) 0%, transparent 50%);
  --gradient-mesh-3:  radial-gradient(ellipse 60% 40% at 50% 50%,
                       rgba(91, 107, 245, 0.08) 0%, transparent 60%);
  --gradient-accent:  linear-gradient(135deg, #5B6BF5 0%, #A155F7 100%);
  --gradient-accent-hover: linear-gradient(135deg, #6E7EFF 0%, #B266FF 100%);
}

:root[data-theme="light"] {
  --bg-canvas:        #F5E9D4;
  --bg-surface-1:     #FFFFFF;
  --bg-surface-2:     #FDF7EC;
  --bg-surface-3:     #F5EDDC;
  --bg-overlay:       rgba(245, 233, 212, 0.72);

  --ink-default:      #0D253D;
  --ink-muted:        #4A5568;
  --ink-faint:        #8B95A3;
  --ink-inverse:      #F5F7FA;

  --accent-primary:   #5B6BF5;
  --accent-hover:     #4A5AE5;
  --accent-press:     #3B4BD5;
  --accent-secondary: #A155F7;
  --accent-warm:      #E86B1A;
  --accent-success:   #10B981;
  --accent-warning:   #D97706;
  --accent-danger:    #EF4444;
  --accent-info:      #3B82F6;

  --hairline:         rgba(13, 37, 61, 0.08);
  --border-default:   #E8DFCC;
  --border-strong:    #D4C8A8;
  --border-accent:    rgba(91, 107, 245, 0.3);

  /* 亮色下渐变更微妙 */
  --gradient-mesh-1:  radial-gradient(ellipse 80% 60% at 20% 0%,
                       rgba(91, 107, 245, 0.10) 0%, transparent 50%);
  --gradient-mesh-2:  radial-gradient(ellipse 70% 50% at 80% 100%,
                       rgba(161, 85, 247, 0.08) 0%, transparent 50%);
  --gradient-mesh-3:  radial-gradient(ellipse 60% 40% at 50% 50%,
                       rgba(91, 107, 245, 0.04) 0%, transparent 60%);
}
```

- [ ] **Step 3: 创建 `typography.css`**

写入 `frontend/src/styles/tokens/typography.css`：

```css
:root {
  --font-sans:  'Geist', 'Geist Fallback', 'HarmonyOS Sans SC',
                'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  --font-mono:  'Geist Mono', 'JetBrains Mono', 'HarmonyOS Sans Mono',
                'SF Mono', Menlo, monospace;
  --font-serif: 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', serif;

  --text-display-2xl: 4.5rem;
  --text-display-xl:  3.75rem;
  --text-display-lg:  3rem;
  --text-display-md:  2.25rem;
  --text-display-sm:  1.875rem;
  --text-heading-lg:  1.5rem;
  --text-heading-md:  1.25rem;
  --text-heading-sm:  1.125rem;
  --text-body-lg:     1rem;
  --text-body-md:     0.875rem;
  --text-body-sm:     0.8125rem;
  --text-caption:     0.75rem;

  --weight-regular:  400;
  --weight-medium:   500;
  --weight-semibold: 600;
  --weight-bold:     700;

  --leading-tight:   1.2;
  --leading-snug:    1.4;
  --leading-normal:  1.6;
  --leading-relaxed: 1.8;

  --tracking-tight:  -0.02em;
  --tracking-normal: 0;
  --tracking-wide:   0.04em;
  --tracking-num:    -0.01em;

  --feature-num: 'tnum' 1, 'lnum' 1;
}

.font-tabular {
  font-feature-settings: var(--feature-num);
}
```

- [ ] **Step 4: 创建 `spacing.css`**

写入 `frontend/src/styles/tokens/spacing.css`：

```css
:root {
  --space-1:  4px;
  --space-2:  8px;
  --space-3:  12px;
  --space-4:  16px;
  --space-5:  20px;
  --space-6:  24px;
  --space-8:  32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
  --space-20: 80px;
  --space-24: 96px;
}
```

- [ ] **Step 5: 创建 `radius.css`**

写入 `frontend/src/styles/tokens/radius.css`：

```css
:root {
  --radius-sm:   6px;
  --radius-md:   8px;
  --radius-lg:   12px;
  --radius-xl:   16px;
  --radius-2xl:  20px;
  --radius-pill: 9999px;
}
```

- [ ] **Step 6: 创建 `shadows.css`**

写入 `frontend/src/styles/tokens/shadows.css`：

```css
:root {
  --shadow-sm:    0 1px 2px rgba(10, 26, 47, 0.5);
  --shadow-md:    0 4px 12px rgba(10, 26, 47, 0.4);
  --shadow-lg:    0 12px 32px rgba(10, 26, 47, 0.35);
  --shadow-xl:    0 24px 48px rgba(10, 26, 47, 0.4);
  --shadow-glow:  0 0 32px rgba(91, 107, 245, 0.25);
  --shadow-focus: 0 0 0 3px rgba(91, 107, 245, 0.4);
}

:root[data-theme="light"] {
  --shadow-sm:    0 1px 2px rgba(13, 37, 61, 0.08);
  --shadow-md:    0 4px 12px rgba(13, 37, 61, 0.10);
  --shadow-lg:    0 12px 32px rgba(13, 37, 61, 0.12);
  --shadow-xl:    0 24px 48px rgba(13, 37, 61, 0.16);
  --shadow-glow:  0 0 32px rgba(91, 107, 245, 0.20);
}
```

- [ ] **Step 7: 创建 `motion.css`**

写入 `frontend/src/styles/tokens/motion.css`：

```css
:root {
  --ease-stripe:  cubic-bezier(0.16, 1, 0.3, 1);
  --ease-bounce:  cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-in-out:  cubic-bezier(0.4, 0, 0.2, 1);
  --ease-out:     cubic-bezier(0, 0, 0.2, 1);

  --duration-fast:   150ms;
  --duration-normal: 240ms;
  --duration-slow:   420ms;
  --duration-slower: 720ms;
}

@media (prefers-reduced-motion: reduce) {
  :root {
    --duration-fast: 0ms;
    --duration-normal: 0ms;
    --duration-slow: 0ms;
    --duration-slower: 0ms;
  }
}
```

- [ ] **Step 8: 创建 `index.css` 聚合**

写入 `frontend/src/styles/tokens/index.css`：

```css
@import './colors.css';
@import './typography.css';
@import './spacing.css';
@import './radius.css';
@import './shadows.css';
@import './motion.css';
```

- [ ] **Step 9: 提交**

```bash
cd D:/CodeProjects/tools
git add frontend/src/styles/tokens/
git commit -m "feat(tokens): add 6 token CSS files (colors/typography/spacing/radius/shadows/motion) with dark + light dual mode

- colors.css: 40+ color variables including bg-canvas, ink, accent, border, gradient signatures
- typography.css: 3 font stacks (sans/mono/serif) + 13 text sizes + tabular-nums utility
- spacing.css: 4px-base 12-step scale
- radius.css: 6 radius levels
- shadows.css: 5 shadow levels + glow + focus ring (dual mode)
- motion.css: 4 easing curves + 4 durations + prefers-reduced-motion fallback

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: 集成 token 到 tailwind.config.js

**Files:**
- Modify: `frontend/tailwind.config.js`

**Interfaces:**
- Consumes: Task 2 产生的 CSS 变量（`--bg-canvas` 等）
- Produces: Tailwind 语义工具类（`bg-canvas`, `text-ink`, `bg-accent`, `rounded-lg`, `shadow-lg`, `ease-stripe` 等）

- [ ] **Step 1: 替换 `frontend/tailwind.config.js` 内容**

替换整个文件为：

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        canvas: 'var(--bg-canvas)',
        surface: {
          1: 'var(--bg-surface-1)',
          2: 'var(--bg-surface-2)',
          3: 'var(--bg-surface-3)',
          overlay: 'var(--bg-overlay)',
        },
        ink: {
          DEFAULT: 'var(--ink-default)',
          muted: 'var(--ink-muted)',
          faint: 'var(--ink-faint)',
          inverse: 'var(--ink-inverse)',
        },
        accent: {
          DEFAULT: 'var(--accent-primary)',
          hover: 'var(--accent-hover)',
          press: 'var(--accent-press)',
          secondary: 'var(--accent-secondary)',
          warm: 'var(--accent-warm)',
          success: 'var(--accent-success)',
          warning: 'var(--accent-warning)',
          danger: 'var(--accent-danger)',
          info: 'var(--accent-info)',
        },
        border: {
          DEFAULT: 'var(--border-default)',
          strong: 'var(--border-strong)',
          accent: 'var(--border-accent)',
          hairline: 'var(--hairline)',
        },
        // 兼容旧色名（避免业务组件全部报错，Phase 3 再清理）
        primary: 'var(--accent-primary)',
        secondary: 'var(--accent-success)',
      },
      fontFamily: {
        sans:  ['var(--font-sans)'],
        mono:  ['var(--font-mono)'],
        serif: ['var(--font-serif)'],
      },
      fontSize: {
        'display-2xl': ['var(--text-display-2xl)', { lineHeight: 'var(--leading-tight)' }],
        'display-xl':  ['var(--text-display-xl)',  { lineHeight: 'var(--leading-tight)' }],
        'display-lg':  ['var(--text-display-lg)',  { lineHeight: 'var(--leading-tight)' }],
        'display-md':  ['var(--text-display-md)',  { lineHeight: 'var(--leading-snug)' }],
        'display-sm':  ['var(--text-display-sm)',  { lineHeight: 'var(--leading-snug)' }],
        'heading-lg':  ['var(--text-heading-lg)',  { lineHeight: 'var(--leading-snug)' }],
        'heading-md':  ['var(--text-heading-md)',  { lineHeight: 'var(--leading-snug)' }],
        'heading-sm':  ['var(--text-heading-sm)',  { lineHeight: 'var(--leading-normal)' }],
        'body-lg':     ['var(--text-body-lg)',     { lineHeight: 'var(--leading-normal)' }],
        'body-md':     ['var(--text-body-md)',     { lineHeight: 'var(--leading-normal)' }],
        'body-sm':     ['var(--text-body-sm)',     { lineHeight: 'var(--leading-normal)' }],
        'caption':     ['var(--text-caption)',     { lineHeight: 'var(--leading-normal)' }],
      },
      borderRadius: {
        sm:   'var(--radius-sm)',
        md:   'var(--radius-md)',
        lg:   'var(--radius-lg)',
        xl:   'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
        pill: 'var(--radius-pill)',
      },
      boxShadow: {
        sm:    'var(--shadow-sm)',
        md:    'var(--shadow-md)',
        lg:    'var(--shadow-lg)',
        xl:    'var(--shadow-xl)',
        glow:  'var(--shadow-glow)',
        focus: 'var(--shadow-focus)',
      },
      transitionTimingFunction: {
        stripe: 'var(--ease-stripe)',
        bounce: 'var(--ease-bounce)',
        'in-out': 'var(--ease-in-out)',
        out: 'var(--ease-out)',
      },
      transitionDuration: {
        fast:   'var(--duration-fast)',
        normal: 'var(--duration-normal)',
        slow:   'var(--duration-slow)',
        slower: 'var(--duration-slower)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('tailwindcss-animate'),
  ],
};
```

- [ ] **Step 2: 验证构建**

```bash
cd D:/CodeProjects/tools/frontend
npm run build 2>&1 | tail -20
```

Expected: 构建成功，无 Tailwind 配置错误。

- [ ] **Step 3: 提交**

```bash
cd D:/CodeProjects/tools
git add frontend/tailwind.config.js
git commit -m "feat(tailwind): integrate design tokens into Tailwind config

- Map all semantic colors (canvas/surface/ink/accent/border) to CSS variables
- Add font family utilities (sans/mono/serif) via CSS variables
- Add 12 font-size utilities (display-*/heading-*/body-*/caption) with line-height
- Add 6 radius levels, 6 shadow levels, 4 easing curves, 4 durations
- Keep primary/secondary aliases for backward compatibility (Phase 3 cleanup)
- Set darkMode selector to [data-theme='dark']

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: 设置 Geist 字体加载

**Files:**
- Modify: `frontend/index.html`（移除 Font Awesome CDN；加 Google Fonts 链接）

**Interfaces:**
- Consumes: Task 2 中 `--font-sans` / `--font-mono` / `--font-serif` 定义的字体栈
- Produces: Geist Sans + Geist Mono + HarmonyOS Sans SC + Noto Serif SC 在首屏前加载（`font-display: swap`）

- [ ] **Step 1: 修改 `frontend/index.html`**

替换整个文件为：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>工具箱 - 聚合类工具网站</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">

    <!-- Geist Sans + Geist Mono (Vercel, 通过 Google Fonts) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

    <!-- HarmonyOS Sans SC (华为, 中文) -->
    <link href="https://fonts.googleapis.com/css2?family=HarmonyOS+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">

    <!-- Noto Serif SC (思源宋体, 课程区衬线) -->
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&display=swap" rel="stylesheet">

    <!-- Pacifico (Logo 手写, 保留) -->
    <link href="https://fonts.googleapis.com/css2?family=Pacifico&display=swap" rel="stylesheet">
</head>
<body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

- [ ] **Step 2: 验证 HTML 语法**

```bash
cd D:/CodeProjects/tools
node -e "const fs=require('fs'); const html=fs.readFileSync('frontend/index.html','utf8'); if (html.includes('fontawesome') || html.includes('fa-')) { console.error('FAIL: Font Awesome CDN still present'); process.exit(1); } console.log('OK: Font Awesome removed, 4 Google Fonts links added');"
```

Expected: 输出 `OK: Font Awesome removed, 4 Google Fonts links added`。

- [ ] **Step 3: 提交**

```bash
cd D:/CodeProjects/tools
git add frontend/index.html
git commit -m "feat(fonts): load Geist, HarmonyOS Sans SC, Noto Serif SC, Pacifico via Google Fonts; remove Font Awesome CDN

- Geist + Geist Mono: primary Latin fonts (Vercel, SF Pro alternative)
- HarmonyOS Sans SC: CJK primary font (Huawei)
- Noto Serif SC: serif accents for course/learning pages
- Pacifico: retained for logo signature script
- Font Awesome 6 CDN removed (Phase 3 icon migration will replace usages with lucide-react)
- All fonts use font-display: swap (no FOIT)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: 创建 `lib/cn.ts` 和 `lib/theme.ts`

**Files:**
- Create: `frontend/src/lib/cn.ts`
- Create: `frontend/src/lib/theme.ts`
- Create: `frontend/src/lib/index.ts`（barrel export）

**Interfaces:**
- Consumes: Task 1 安装的 `clsx` + `tailwind-merge`
- Produces: `cn()` 工具函数（供 Phase 2+ 原语使用）+ `Theme` 类型 + `ThemeProvider` React Context + `useTheme()` hook

- [ ] **Step 1: 创建 `frontend/src/lib/cn.ts`**

```ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * 合并 Tailwind 类名工具。
 * 支持 clsx 的条件类 + tailwind-merge 去重。
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: 创建 `frontend/src/lib/theme.ts`**

```ts
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

export type Theme = 'dark' | 'light' | 'system';

interface ThemeContextValue {
  theme: Theme;
  resolved: 'dark' | 'light';
  setTheme: (t: Theme) => void;
}

const STORAGE_KEY = 'tk-theme';
const DEFAULT_THEME: Theme = 'dark';

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function resolveTheme(theme: Theme): 'dark' | 'light' {
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: light)').matches
      ? 'light'
      : 'dark';
  }
  return theme;
}

function applyTheme(theme: Theme): void {
  const resolved = resolveTheme(theme);
  document.documentElement.setAttribute('data-theme', resolved);
  localStorage.setItem(STORAGE_KEY, theme);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window === 'undefined') return DEFAULT_THEME;
    return (localStorage.getItem(STORAGE_KEY) as Theme) || DEFAULT_THEME;
  });

  const [resolved, setResolved] = useState<'dark' | 'light'>(() =>
    resolveTheme(theme)
  );

  const setTheme = (t: Theme) => {
    setThemeState(t);
    applyTheme(t);
  };

  // 初次挂载：应用 localStorage 中的主题
  useEffect(() => {
    applyTheme(theme);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 监听系统主题变化（仅 theme='system' 时响应）
  useEffect(() => {
    if (theme !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: light)');
    const onChange = () => {
      const r = resolveTheme('system');
      setResolved(r);
      document.documentElement.setAttribute('data-theme', r);
    };
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [theme]);

  // 同步 resolved 状态
  useEffect(() => {
    setResolved(resolveTheme(theme));
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, resolved, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used within <ThemeProvider>');
  }
  return ctx;
}
```

- [ ] **Step 3: 创建 `frontend/src/lib/index.ts`**

```ts
export { cn } from './cn';
export { ThemeProvider, useTheme, type Theme } from './theme';
```

- [ ] **Step 4: 验证 TypeScript 编译**

```bash
cd D:/CodeProjects/tools/frontend
npx tsc --noEmit 2>&1 | grep -E "(error|src/lib)" | head -10
```

Expected: 无 error 输出。

- [ ] **Step 5: 提交**

```bash
cd D:/CodeProjects/tools
git add frontend/src/lib/
git commit -m "feat(lib): add cn() utility + ThemeProvider/useTheme React context

- cn(): clsx + tailwind-merge wrapper for consistent class name composition
- ThemeProvider: React Context managing dark/light/system theme state
- useTheme(): hook returning { theme, resolved, setTheme }
- Persists user preference to localStorage key 'tk-theme'
- Listens to system prefers-color-scheme when theme='system'
- Sets <html data-theme='dark|light'> as single source of truth

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: 创建 `.bg-mesh` 大气背景层

**Files:**
- Create: `frontend/src/styles/backgrounds.css`

**Interfaces:**
- Consumes: Task 2 中 `--gradient-mesh-1/2/3` + `--bg-canvas` 变量
- Produces: `.bg-mesh` + `.bg-mesh--full` / `.bg-mesh--content` / `.bg-mesh--subtle` 强度分层类

- [ ] **Step 1: 创建 `frontend/src/styles/backgrounds.css`**

```css
/* ============================================================
 * 大气渐变背景层 —— Stripe 签名体验
 * 用法: <div class="bg-mesh bg-mesh--subtle" />
 * ============================================================ */

.bg-mesh {
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background:
    var(--gradient-mesh-1),
    var(--gradient-mesh-2),
    var(--gradient-mesh-3),
    var(--bg-canvas);
}

/* 强度分层 */
.bg-mesh--full    { opacity: 1.0; }
.bg-mesh--content { opacity: 0.7; }
.bg-mesh--subtle  { opacity: 0.3; }

/* SVG noise overlay 消除渐变 banding */
.bg-mesh::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  opacity: 0.4;
  mix-blend-mode: overlay;
  pointer-events: none;
}

/* 渐变呼吸动画 (30s 循环) */
@keyframes mesh-breathe {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(2%, -1%) scale(1.02); }
}

.bg-mesh--breathing {
  animation: mesh-breathe 30s ease-in-out infinite;
  will-change: transform;
}

/* 无障碍：用户偏好减少动效时禁用呼吸 */
@media (prefers-reduced-motion: reduce) {
  .bg-mesh--breathing {
    animation: none;
  }
}
```

- [ ] **Step 2: 提交**

```bash
cd D:/CodeProjects/tools
git add frontend/src/styles/backgrounds.css
git commit -m "feat(styles): add .bg-mesh atmospheric gradient background with intensity layers

- .bg-mesh: fixed-position full-viewport background consuming --gradient-mesh-1/2/3 + --bg-canvas
- Intensity variants: --full (1.0), --content (0.7), --subtle (0.3)
- SVG noise overlay via data URI to eliminate gradient banding
- Breathing animation (30s cycle) via transform (GPU-accelerated)
- prefers-reduced-motion fallback disables animation

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: 更新 `index.css` 接入 token 系统

**Files:**
- Modify: `frontend/src/index.css`（删除硬编码颜色，保留业务类）

**Interfaces:**
- Consumes: Task 2 的颜色 token
- Produces: 全局背景/文字色通过 token 表达；业务类 `.tool-card` / `.search-input` / `.category-tab` / 滚动条 / Monaco 高亮保留（Phase 3 再清理）

- [ ] **Step 1: 替换 `frontend/src/index.css` 内容**

```css
@import './styles/tokens/index.css';
@import './styles/backgrounds.css';

@tailwind base;
@tailwind components;
@tailwind utilities;

/* ============================================================
 * 全局 reset & 基础样式 —— 通过 token 变量表达
 * ============================================================ */

html, body {
  height: 100%;
}

body {
  background-color: var(--bg-canvas);
  color: var(--ink-default);
  font-family: var(--font-sans);
  font-feature-settings: 'tnum' 1, 'lnum' 1;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ============================================================
 * 业务类 (Phase 3 清理前保留, 改用 token 表达)
 * ============================================================ */

.tool-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.search-input:focus {
  outline: none;
  box-shadow: var(--shadow-focus);
}

.category-tab.active {
  background-color: var(--accent-primary);
  color: var(--ink-inverse);
}

.category-tab {
  transition: all var(--duration-fast) var(--ease-stripe);
}

/* Pacifico 字体 fallback (当 Google Fonts 不可用时) */
.font-\[Pacifico\] {
  font-family: 'Pacifico', 'Microsoft YaHei', 'PingFang SC', sans-serif;
}

/* ============================================================
 * 弹框 / 进入动画
 * ============================================================ */

@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

@keyframes slide-in-bottom {
  from { transform: translateY(100%); }
  to   { transform: translateY(0); }
}

.animate-fadeIn          { animation: fadeIn var(--duration-fast) var(--ease-out); }
.animate-scaleIn         { animation: scaleIn var(--duration-normal) var(--ease-stripe); }
.animate-slide-in-bottom { animation: slide-in-bottom var(--duration-normal) var(--ease-stripe); }

/* ============================================================
 * 自定义滚动条 —— 通过 token 表达
 * ============================================================ */

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
  border-radius: var(--radius-md);
}

::-webkit-scrollbar-thumb {
  background: var(--hairline);
  border-radius: var(--radius-md);
  transition: background var(--duration-fast) var(--ease-stripe);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--border-default);
}

* {
  scrollbar-width: thin;
  scrollbar-color: var(--hairline) transparent;
}

/* ============================================================
 * Monaco Editor 变量高亮 (保留, 改用 token)
 * ============================================================ */

.variable-defined {
  background-color: rgba(161, 85, 247, 0.2);
  border-bottom: 2px solid var(--accent-secondary);
  border-radius: var(--radius-sm);
}

.variable-undefined {
  background-color: rgba(248, 113, 113, 0.2);
  border-bottom: 2px solid var(--accent-danger);
  text-decoration: underline wavy var(--accent-danger);
  border-radius: var(--radius-sm);
}
```

- [ ] **Step 2: 验证构建**

```bash
cd D:/CodeProjects/tools/frontend
npm run build 2>&1 | tail -10
```

Expected: 构建成功。页面视觉效果与重构前基本一致（仅背景色从 `#0f172a` 变为 `#0A1A2F`，文字从 `#e2e8f0` 变为 `#F5F7FA` —— 极轻微的颜色差异）。

- [ ] **Step 3: 提交**

```bash
cd D:/CodeProjects/tools
git add frontend/src/index.css
git commit -m "feat(styles): migrate index.css to token system

- Replace hardcoded #0f172a / #e2e8f0 with var(--bg-canvas) / var(--ink-default)
- Add font-family: var(--font-sans) globally
- Enable tabular-nums globally (Stripe-style number rendering)
- Import tokens/index.css and styles/backgrounds.css
- Preserve business classes (.tool-card / .search-input / .category-tab) with token expressions
- Preserve animations (.animate-fadeIn / .animate-scaleIn / .animate-slide-in-bottom) with token durations
- Preserve custom scrollbar with token-based colors
- Preserve Monaco variable-highlight classes with token colors

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Logo 渐变填充 + .bg-mesh 接入 Layout

**Files:**
- Modify: `frontend/src/components/Header/Header.tsx`（Logo 渐变）
- Modify: `frontend/src/components/Layout/Layout.tsx`（接入 .bg-mesh）

**Interfaces:**
- Consumes: Task 3 中的 `accent` / `accent-secondary` Tailwind 工具类
- Produces: Logo 显示为渐变填充文字；Layout 根渲染 `.bg-mesh.bg-mesh--subtle` 背景

- [ ] **Step 1: 读取 `frontend/src/components/Layout/Layout.tsx` 当前内容**

```bash
cd D:/CodeProjects/tools
cat frontend/src/components/Layout/Layout.tsx
```

记录完整内容以便精准修改。

- [ ] **Step 2: 在 `Layout.tsx` 根 div 开头插入 `.bg-mesh`**

定位到根 `<div>` 标签，在其**第一个子元素**前插入：

```tsx
<div className={`bg-canvas text-ink ${isImmersion ? 'h-screen overflow-hidden' : 'min-h-screen'} flex flex-col relative`}>
  {/* 新增: 大气背景层 (subtle 强度, Phase 3 按页面细化) */}
  <div className="bg-mesh bg-mesh--subtle" aria-hidden="true" />
  {/* ... 原有内容 ... */}
</div>
```

注意：根 div 已有 `bg-slate-900 text-slate-100` 等类，**需要同时替换为 `bg-canvas text-ink`**，并加上 `relative` 使 `.bg-mesh` 的固定定位正常工作。

- [ ] **Step 3: 修改 `Header.tsx` Logo 为渐变填充**

定位到：

```tsx
<Link to="/" className="text-2xl font-['Pacifico'] text-primary" key={language}>
  {t.common.logo}
</Link>
```

替换为：

```tsx
<Link
  to="/"
  className="text-2xl font-['Pacifico'] bg-gradient-to-br from-accent to-accent-secondary bg-clip-text text-transparent"
  key={language}
>
  {t.common.logo}
</Link>
```

- [ ] **Step 4: 同步替换 Header 背景色**

Header.tsx 中有两处 `bg-slate-800 border-slate-700`（折叠态 + 展开态），分别替换为：

- `bg-slate-800` → `bg-surface-1`
- `border-slate-700` → `border-border`
- `text-slate-400` → `text-ink-faint`
- `hover:text-slate-200` → `hover:text-ink`

- [ ] **Step 5: 验证构建 + 视觉检查**

```bash
cd D:/CodeProjects/tools/frontend
npm run build 2>&1 | tail -10
```

Expected: 构建成功。

然后启动开发服务器：

```bash
cd D:/CodeProjects/tools
python dev-services.py restart frontend
```

手动在浏览器打开 http://localhost:5178，验证：

- ✅ Logo 文字显示为紫罗兰蓝→紫罗兰渐变（不再是纯蓝色）
- ✅ 页面背景有微妙的径向渐变呼吸感（比原来稍深稍紫）
- ✅ Header 背景与新 token 系统一致
- ✅ 字体显示为 Geist（对比旧字体应更几何更现代）

- [ ] **Step 6: 提交**

```bash
cd D:/CodeProjects/tools
git add frontend/src/components/Header/Header.tsx frontend/src/components/Layout/Layout.tsx
git commit -m "feat(layout): apply gradient logo + .bg-mesh atmospheric background

- Header logo: Pacifico script with bg-gradient-to-br from-accent to-accent-secondary
- Header surfaces: replace hardcoded slate-800/700/400 with surface-1/border-border/ink-faint
- Layout root: inject <div class='bg-mesh bg-mesh--subtle' aria-hidden='true' /> before content
- Layout root: replace bg-slate-900 text-slate-100 with bg-canvas text-ink

Visual verification checklist:
- Logo shows indigo→violet gradient text
- Page background has subtle radial gradient breathing
- Header matches new token system
- Geist font is now active globally

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: 接入 ThemeProvider 到 App 根

**Files:**
- Modify: `frontend/src/main.tsx`（包裹 ThemeProvider）

**Interfaces:**
- Consumes: Task 5 的 `ThemeProvider`
- Produces: 整个 React 树可调用 `useTheme()`；主题切换持久化

- [ ] **Step 1: 修改 `frontend/src/main.tsx`**

替换整个文件为：

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ThemeProvider } from './lib/theme';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
```

- [ ] **Step 2: 验证 TypeScript**

```bash
cd D:/CodeProjects/tools/frontend
npx tsc --noEmit 2>&1 | tail -5
```

Expected: 无 error。

- [ ] **Step 3: 提交**

```bash
cd D:/CodeProjects/tools
git add frontend/src/main.tsx
git commit -m "feat(app): wrap App with ThemeProvider for dark/light/system theme

- ThemeProvider at React root enables useTheme() across all pages
- Persists preference to localStorage ('tk-theme')
- Default: 'dark' (matches previous hardcoded slate theme)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: 创建 /dev/components 演示页（验证 token 系统）

**Files:**
- Create: `frontend/src/pages/DevComponentsPage.tsx`
- Modify: `frontend/src/App.tsx`（加 `/dev/components` 路由）

**Interfaces:**
- Consumes: Task 2-6 的全部 token 变量和 `.bg-mesh`
- Produces: 一个可在浏览器访问的视觉验证页面（仅开发用，不打包到生产）

- [ ] **Step 1: 创建 `frontend/src/pages/DevComponentsPage.tsx`**

```tsx
import { useTheme } from '@/lib/theme';

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
          {['sm', 'md', 'lg', 'xl', '2xl', 'pill'].map((r) => (
            <div key={r} className={`bg-accent w-20 h-20 rounded-${r} flex items-center justify-center text-ink-inverse text-body-sm`}>
              {r}
            </div>
          ))}
        </div>
      </section>

      {/* 阴影 */}
      <section className="space-y-4">
        <h2 className="text-heading-lg font-medium">阴影</h2>
        <div className="flex gap-6">
          {['sm', 'md', 'lg', 'xl', 'glow', 'focus'].map((s) => (
            <div key={s} className={`bg-surface-2 shadow-${s} w-24 h-24 rounded-lg flex items-center justify-center text-ink-muted text-body-sm`}>
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
```

- [ ] **Step 2: 在 `App.tsx` 添加路由**

读取 `frontend/src/App.tsx`，找到其他路由定义的位置（例如 `<Route path="/courses" ...>` 附近），在其前面添加：

```tsx
// 仅开发环境：设计系统 token 验证页
import DevComponentsPage from './pages/DevComponentsPage';
```

然后在 `<Routes>` 内添加：

```tsx
{import.meta.env.DEV && (
  <Route path="/dev/components" element={<DevComponentsPage />} />
)}
```

注意：`DevComponentsPage` 必须在文件顶部 import，`import.meta.env.DEV` 仅控制路由注册。如果项目 `vite.config.ts` 未开启 `define: { 'import.meta.env.DEV': ... }`，改用常量判断 `const isDev = import.meta.env.MODE === 'development'`。

- [ ] **Step 3: 验证构建 + 视觉检查**

```bash
cd D:/CodeProjects/tools/frontend
npm run build 2>&1 | tail -10
```

Expected: 构建成功。

启动开发服务器：

```bash
cd D:/CodeProjects/tools
python dev-services.py restart frontend
```

浏览器打开 http://localhost:5178/dev/components，逐项验证：

- ✅ 主题切换：点击 dark / light / system 三个按钮，页面立即切换
- ✅ 颜色：12 个色块显示正确（暗色下 canvas 深海军蓝；亮色下 canvas 暖奶油）
- ✅ 字体：Sans 显示 Geist、Mono 显示 Geist Mono、Serif 显示 Noto Serif SC
- ✅ 字号：13 级字号从巨大到微小依次显示
- ✅ 圆角：6 级圆角依次显示
- ✅ 阴影：6 级阴影依次显示（glow 是紫罗兰色光晕，focus 是 3px 边框光）
- ✅ Logo 渐变：Pacifico 字体显示紫罗兰→紫罗兰渐变文字
- ✅ Tabular-nums：数字列等宽对齐

- [ ] **Step 4: 提交**

```bash
cd D:/CodeProjects/tools
git add frontend/src/pages/DevComponentsPage.tsx frontend/src/App.tsx
git commit -m "feat(dev): add /dev/components token verification page (dev-only route)

- Theme switcher with dark/light/system buttons showing resolved theme
- 12-color swatch grid (canvas/surface/accent/border/semantic colors)
- 4 font stacks (sans/mono/serif + tabular-nums demonstration)
- 13-level font-size scale
- 6-radius and 6-shadow visual grids
- Logo gradient demonstration

Route guarded by import.meta.env.DEV to exclude from production build.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: 端到端构建验证 + 视觉对比

**Files:**
- 无文件修改（仅验证）

**Interfaces:**
- Consumes: Task 1-10 全部产物
- Produces: Phase 1 完成确认

- [ ] **Step 1: 完整构建验证**

```bash
cd D:/CodeProjects/tools/frontend
npm run build
```

Expected: `vite build` 成功，无 TS 错误、无 Tailwind 编译错误。

- [ ] **Step 2: TypeScript 类型检查**

```bash
cd D:/CodeProjects/tools/frontend
npx tsc --noEmit
```

Expected: 无错误输出。

- [ ] **Step 3: 重启开发服务器并视觉验证**

```bash
cd D:/CodeProjects/tools
python dev-services.py restart frontend
```

打开 http://localhost:5178（首页）和 http://localhost:5178/dev/components，逐项核对：

| 检查项 | 期望 |
|---|---|
| 首页背景 | 深海军蓝 `#0A1A2F` 上有微妙 indigo→violet 渐变呼吸 |
| Header Logo | Pacifico 字体 + 紫罗兰→紫罗兰渐变文字 |
| Header 背景 | `bg-surface-1`（新 token），不再是 slate-800 |
| 工具卡片 | hover 上浮 + 新阴影 `var(--shadow-lg)` |
| 字体 | Geist 几何 sans，比旧版更锐利 |
| 数字渲染 | tabular-nums 启用（数字对齐） |
| 主题切换器（/dev/components） | 点击 light 后页面变为暖奶油画布 |
| 持久化 | 刷新页面后主题选择保留 |
| 浏览器 DevTools Network | Geist / HarmonyOS Sans / Noto Serif / Pacifico 字体加载（font-display: swap） |
| `/dev/components` 全 6 节 | 颜色 / 字体 / 字号 / 圆角 / 阴影 / Logo 渐变全部正常显示 |

- [ ] **Step 4: 检查未提交的改动**

```bash
cd D:/CodeProjects/tools
git status
```

Expected: 工作区干净（所有 Phase 1 改动已提交）。如果有未提交改动，按实际情况决定是否需要追加提交。

- [ ] **Step 5: 报告完成**

完成下列清单：

- ✅ `frontend/src/styles/tokens/*.css`：6 份 token 文件 + index 聚合
- ✅ `frontend/src/styles/backgrounds.css`：`.bg-mesh` + 强度分层 + 呼吸动画
- ✅ `frontend/tailwind.config.js`：所有 token 接入为 Tailwind utility
- ✅ `frontend/index.html`：移除 Font Awesome；加载 Geist / HarmonyOS / Noto Serif / Pacifico
- ✅ `frontend/src/lib/cn.ts` + `theme.ts`：`cn()` + `ThemeProvider` + `useTheme()`
- ✅ `frontend/src/index.css`：全局 `body` 接入 token（移除硬编码 slate）
- ✅ `frontend/src/components/Header/Header.tsx`：Logo 渐变填充
- ✅ `frontend/src/components/Layout/Layout.tsx`：`.bg-mesh.bg-mesh--subtle` 背景
- ✅ `frontend/src/main.tsx`：包裹 `ThemeProvider`
- ✅ `frontend/src/pages/DevComponentsPage.tsx`：token 验证页（dev-only）
- ✅ `npm run build` 通过
- ✅ `npx tsc --noEmit` 无错误
- ✅ 双模式切换正确（dark / light / system）
- ✅ localStorage 持久化工作

---

## 完成标准（Definition of Done for Phase 1）

Phase 1 完成后，项目处于以下状态：

1. **新 token 已就位**：60+ 个 CSS 变量覆盖颜色/字体/间距/圆角/阴影/动效，双模式（dark/light）
2. **Tailwind 完全接入**：语义工具类（`bg-canvas` / `text-ink` / `bg-accent` / `rounded-lg` / `shadow-glow`）通过 `var(--*)` 间接引用 token
3. **字体已加载**：Geist / Geist Mono / HarmonyOS Sans SC / Noto Serif SC / Pacifico 通过 Google Fonts CDN + `font-display: swap`
4. **主题切换可用**：`useTheme()` hook 可读写主题；`<ThemeProvider>` 已包裹 App 根；`localStorage('tk-theme')` 持久化
5. **大气背景可见**：`.bg-mesh.bg-mesh--subtle` 已在 Layout 根挂载，全站有呼吸感
6. **Logo 渐变可见**：Pacifico 字体 + `bg-gradient-to-br from-accent to-accent-secondary bg-clip-text text-transparent`
7. **业务组件未破坏**：现有 23 工具页 + Workspace + Admin 仍可正常访问（仅颜色从 slate 系微调为 token 系）
8. **验证页可用**：`/dev/components`（dev-only）展示所有 token，便于后续 Phase 2 接入新原语时对照
9. **构建通过**：`npm run build` + `npx tsc --noEmit` 无错误

**Phase 2 衔接点**：下一 Phase 将建立 `components/ui/` 原语目录（Button / Card / Input / Modal / ... 18 个），基于这些 token 实现，并通过 `/dev/components` 验证视觉一致性。