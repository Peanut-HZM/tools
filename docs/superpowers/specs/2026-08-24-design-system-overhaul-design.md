# 设计系统全量重构设计文档

> **状态：** 设计稿，待用户审阅
> **日期：** 2026-08-24
> **目标读者：** 本项目开发者、维护者、设计审阅者
> **参考：** `awesome-design-md/design-md/stripe/DESIGN.md`（品牌参考锚点），`awesome-design-md/design-md/linear.app/DESIGN.md`、`vercel/DESIGN.md`（次级参考）

## 1. 背景与目标

### 1.1 背景

工具箱项目（`D:\CodeProjects\tools`）是一个面向中文开发者与产品经理的多工具 SaaS 聚合平台，包含：

- **PC Web 前端**：**24 个工具组件（25 个路由，ProductManagerAgent 占 2 路由）**（ImageDownloader、VideoDownloader、JSON 格式化、Calendar、AIAssistant、KeyGenerator、Markdown 编辑器、MarkItDownConverter、OCR、ASR、数据库、Redis、SSH、PM Agent、跨设备分享、OpenSpecCourse、LearningSharePlatform、CursorHistory、HttpApiClient、SystemMonitor、TokenUsage、OpenClawChat、K8sTool、ImageGeneration），独立的 `/workspace` 标签页工作区，13 个 admin 后台页面，课程/学习模块，含 `/account-settings` 与 `/tech-contents` 内容页（**实际 47 条路由**）
- **微信小程序**：Taro 4 + React + 纯 SCSS，"深空蓝"暗色主题，已通过相同调色板与 PC 端视觉对齐
- **后端**：FastAPI + Python，端口 19092

当前视觉现状：

1. **PC 端**：暗色 `slate-900/800/700` 三层 + 霓虹蓝/青/紫点缀 + Pacifico 手写 Logo + Font Awesome 图标。视觉连贯但**无抽象层**：每个组件各自拼 Tailwind 工具类，`primary`/`secondary` Tailwind 别名定义了却几乎没人用，全站零设计 token、零共享组件原语
2. **小程序**：`mini-program/src/app.scss` 已有完整 CSS 自定义属性 token（`--bg-primary`、`--color-primary`、`--radius-*`、`--shadow-*`），但 Token 命名与 PC 端不同步，与 awesome-design-md 中的世界级设计语言有差距
3. **三套并存的主题系统**：`index.css` 的全局暗色、`MarkdownEditor/MarkdownEditor.css` 的赛博朋克霓虹（完全独立的 CSS 变量层）、`themes/cursorThemes.ts` 的 CursorHistory 主题切换器（三者互不消费对方的变量）
4. **图标系统分裂**：Font Awesome 6 CDN + lucide-react 双系统并存，无迁移路径

用户明确表达的需求："**重构整个项目的样式风格，包括小程序的样式，一定要显得很有技术水平，一定要很好看**"。

### 1.2 目标

构建一个 Stripe 级别（`#5B6BF5` 紫罗兰蓝 + 大气渐变网格 + 暖奶油亮色）的完整设计系统，覆盖 PC 端 + 微信小程序：

1. **统一 token 源**：所有颜色 / 字体 / 间距 / 圆角 / 阴影 / 动效用 CSS 自定义属性表达，PC 和小程序共享同一份 token 源（自动 codegen 到 SCSS）
2. **组件原语库**：在 `components/ ui/` 下建立 shadcn/ui 风格 + Radix 原语底座的 18 个核心原语（Button、Card、Input、Modal、Dropdown、Tabs、Toast、Tooltip、Select、Switch、Checkbox、Badge、Avatar、Separator、Skeleton、Dialog、Popover、Slider）
3. **签名渐变全站存在**：indigo→violet 大气网格背景作为每个页面的"底色"，强度按 marketing/workspace/admin 三档分层（100% / 25% / 25%）
4. **暗 + 亮双模式**：`data-theme` 切换，亮色保留 Stripe 招牌 `#F5E9D4` 暖奶油画布
5. **课程区衬线点缀**：唯一允许 Noto Serif SC 进入标题区域的页面（Stripe 自己的 Press/Docs 也用 serif 处理内容型页面）
6. **图标系统统一（分阶段）**：
   - **Phase 1**：保留 Font Awesome CDN（代码库有 1,011 处引用 / 121 文件，强行移除会破坏全站）；新增 `<Icon name="..." />` 抽象组件（支持同时渲染 FA 与 lucide，按 name 前缀分发）
   - **Phase 3**：逐工具迁移 Font Awesome → lucide-react（含 20+ 文件的动态图标模式）
   - **Phase 3 末尾**：移除 Font Awesome CDN + `@fortawesome/fontawesome-free`（如已列入 npm 依赖）
   - **新增后端迁移**：数据库 `tools.icon` / `agents.icon` / `courses.icon` 字段从 `fa-xxx` 值迁移为 lucide 名称
7. **主题切换器**：设置页可手动切换"暗 / 亮 / 跟随系统"，记住用户偏好；接入休眠的 `PreferencesSection.tsx` 与已有的 `CursorHistory` 多色主题（后者收敛为 ThemeProvider 的消费者）
8. **小程序同步升级**：核心页面（首页 / 工具列表 / 工具详情）同步 token，平台原生模式（底部 Tab + 抽屉 + 底部 sheet）替代 PC 组件
9. **品牌色策略（cyan + violet-blue 双轨）**：
   - `cyan` 保留为"辅助强调色"（代码库事实标准，403 处使用）—— 用于焦点环、链接、选中态、代码高亮
   - `violet-blue`（`#5B6BF5`）作为"主 CTA 品牌色"（按钮、Logo 渐变、主品牌标识）
   - 两者不互相替换，共存于 token 层：`--accent-primary: #5B6BF5` + `--accent-cyan: #06B6D4`
   - Phase 3 迁移时，cyan 使用保留原位置，violet-blue 仅替换原 primary/secondary 别名（29 处）

### 1.3 非目标（v1 不做）

- 不重写业务逻辑（仅视觉/样式层）
- 不替换 Markdown 编辑器的 Monaco / CodeMirror 编辑器内核（只重做 CSS 主题包装）
- 不做用户头像 / 团队头像 / 品牌空间 / 自定义主题编辑器
- 不做无障碍深度审计（仅保证 WCAG AA 级文本对比度；不全键盘穿越、不做 ARIA 全套）
- 不重做图标系统的所有图标（仅迁移 PC 端实际使用的 ~120 个 Font Awesome 图标到 lucide-react 对应物）
- 不动 Admin 后端的业务表单逻辑（仅做样式层）
- 不重做 CursorHistory 主题切换的运行时切换（保留 `themes/cursorThemes.ts` 但只接受 `dark` / `light` 两态，不支持 `deep-space` / `ocean-blue` / `forest-green` 等多色主题）
- 不做主题切换的动画过渡（仅在初次加载和点击切换器时有过渡）
- 不为每个工具页做定制视觉（统一外壳 + 工具内自定）

---

## 2. 设计语言决策（已与用户对齐）

### 2.1 美学方向

**"Stripe × 暖中文"**：参考 `awesome-design-md/design-md/stripe/DESIGN.md`，但做两处有意识本地化：

1. 主色偏暖化：Stripe 原 `#533AFD`（电光靛蓝）→ **`#5B6BF5`**（紫罗兰蓝，配合中文审美更温润）
2. 课程区引入 Noto Serif SC 衬线作为标题点缀，体现"阅读/学习"调性

### 2.2 重构幅度

**全量重构 + 新设计系统**（用户已确认）：
- 抽出完整 token 层（CSS variables）
- 引入 shadcn/ui + Radix UI 原语
- lucide-react 统一图标
- 重构所有页面（公共首页 / workspace / admin / **24 个工具组件（25 路由）** + Recommendations / AccountSettings / TechContents / 课程页）
- 小程序同步升级
- 工期 3-4 周

### 2.3 主题策略

**暗 + 亮双模式**（用户已确认）：
- 暗色：深海军蓝墨底 `#0A1A2F` + 紫罗兰蓝 `#5B6BF5`
- 亮色：Stripe 招牌暖奶油 `#F5E9D4` + 同款紫罗兰蓝

### 2.4 字体系统

**Geist + HarmonyOS Sans SC**（用户已确认）：
- 拉丁主字：`Geist`（Vercel 出品，SF Pro 开源替代，几何现代）
- 拉丁代码：`Geist Mono`（与主字同设计师）
- 中文：`HarmonyOS Sans SC`（华为开源，几何感与 Geist 气质匹配）
- 数字：`Geist Mono` + `font-feature-settings: 'tnum'` 启用 tabular-nums（Stripe 同款体验）
- 课程区衬线点缀：`Noto Serif SC`（思源宋体，仅用于课程详情/学习页面标题）

字体栈优先级：
```
sans:  'Geist', 'Geist Fallback', 'HarmonyOS Sans SC',
       'PingFang SC', 'Microsoft YaHei', sans-serif
mono:  'Geist Mono', 'JetBrains Mono', 'HarmonyOS Sans Mono', monospace
serif: 'Noto Serif SC', 'Source Han Serif SC', serif
```

### 2.5 签名渐变定位

**全站大气背景（Stripe 原生体验）**（用户已确认）：
- 首页 hero / 课程页 / 营销页：渐变 100%
- 工具页 / 工作区 / admin：渐变 25%（微妙的呼吸感，避免视觉疲劳）
- 渐变通过 radial-gradient 多层叠加 + SVG noise overlay 实现，opacity 分层控制

### 2.6 Logo 处理

**保留 Pacifico + 渐变填充**（用户已确认）：
- 当前 `Header.tsx` 的 `font-['Pacifico']` 保留（独特品牌特征）
- 增加 `bg-clip-text` + `linear-gradient(135deg, #5B6BF5, #A155F7)` 渐变填充
- Pacifico 字体继续从 Google Fonts 加载
- 不引入新的 wordmark（与"工程工具"气质冲突）

---

## 3. 架构概览

### 3.1 分层结构

```
前端项目根
├── frontend/
│   ├── src/
│   │   ├── styles/
│   │   │   ├── tokens/
│   │   │   │   ├── colors.css         # 所有色 token（双模式）
│   │   │   │   ├── typography.css     # 字体层级 + tabular-nums
│   │   │   │   ├── spacing.css        # 4px-base 间距
│   │   │   │   ├── radius.css         # 圆角
│   │   │   │   ├── shadows.css        # 阴影 + 发光
│   │   │   │   ├── motion.css         # 缓动曲线 + 时长
│   │   │   │   └── index.css          # 聚合入口
│   │   │   ├── backgrounds.css        # .bg-mesh 全站背景层
│   │   │   └── reset.css              # 极简 reset + prefers-reduced-motion
│   │   ├── components/ui/             # shadcn/ui 风格原语
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── modal.tsx              # 基于 Radix Dialog
│   │   │   ├── dropdown.tsx           # 基于 Radix Dropdown
│   │   │   ├── tabs.tsx               # 基于 Radix Tabs
│   │   │   ├── toast.tsx              # 基于 Radix Toast
│   │   │   ├── tooltip.tsx            # 基于 Radix Tooltip
│   │   │   ├── select.tsx             # 基于 Radix Select
│   │   │   ├── switch.tsx             # 基于 Radix Switch
│   │   │   ├── checkbox.tsx           # 基于 Radix Checkbox
│   │   │   ├── badge.tsx
│   │   │   ├── avatar.tsx
│   │   │   ├── separator.tsx
│   │   │   ├── skeleton.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── popover.tsx            # 基于 Radix Popover
│   │   │   ├── slider.tsx             # 基于 Radix Slider
│   │   │   └── theme-switcher.tsx     # 暗/亮/跟随系统 三态切换
│   │   ├── lib/
│   │   │   ├── cn.ts                  # clsx + tailwind-merge
│   │   │   ├── motion.ts              # Framer Motion 预设
│   │   │   └── theme.ts               # 主题应用工具
│   │   └── (现有业务组件目录, 渐次替换)
│   └── tailwind.config.js             # 扩展接入 token 变量
└── mini-program/
    └── src/styles/
        ├── tokens.scss                # 由前端 colors.css 自动生成
        └── (现有 SCSS, 渐次替换)
```

### 3.2 关键不变量

1. **CSS 变量是单一真相源**：所有色值、字号、间距都通过 `var(--*)` 引用，组件不写死 hex / px
2. **Tailwind utility 与 CSS 变量共存**：`tailwind.config.js` 把 colors 全部映射到 `var(--*)` 上，开发者可以同时使用 `bg-canvas`（Tailwind 类）和 `background: var(--bg-canvas)`（CSS）
3. **主题切换通过 `data-theme`**：`<html data-theme="dark|light">` 是唯一入口，CSS 变量在 `:root` 与 `:root[data-theme="light"]` 下分别定义
4. **小程序与 PC 共享同一份 token 源**：`frontend/src/styles/tokens/colors.css` 是源，codegen 脚本生成 `mini-program/src/styles/tokens.scss`
5. **组件库引入前先停**：原语目录先建好（Button / Card / Input），业务组件再迁移。禁止一边迁业务一边发明新原语
6. **签名渐变是低优先级背景**：永远是 `position: fixed; z-index: -1` 的最底层，不抢任何交互焦点

### 3.3 依赖矩阵

新增 npm 依赖：

| 包 | 用途 | 版本 |
|---|---|---|
| `@radix-ui/react-*` | 13 个原语底层 | 最新稳定版 |
| `class-variance-authority` (CVA) | 组件变体管理 | 最新 |
| `clsx` | 类名拼接 | 最新 |
| `tailwind-merge` | Tailwind 类去重 | 最新 |
| `framer-motion` | 弹窗/抽屉/页面切换动效 | 最新 |
| `lucide-react` | 图标（替换 Font Awesome） | 最新 |
| `tailwindcss-animate` | Tailwind 动画预设 | 最新 |

移除依赖：
- `@fortawesome/fontawesome-free`（如果已显式列出；CDN 引用从 `index.html` 移除）

---

## 4. Token 系统（CSS 变量）

### 4.1 颜色 token（`colors.css`）

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
  --accent-warm:      #FF8A4C;   /* 数字/价格强调 */
  --accent-cyan:      #06B6D4;   /* 辅助强调色：焦点环/链接/选中态/代码高亮（保留代码库事实标准） */
  --accent-cyan-hover:#22D3EE;
  --accent-cyan-press:#0891B2;
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
  --bg-canvas:        #F5E9D4;     /* Stripe 招牌暖奶油 */
  --bg-surface-1:     #FFFFFF;
  --bg-surface-2:     #FDF7EC;
  --bg-surface-3:     #F5EDDC;
  --bg-overlay:       rgba(245, 233, 212, 0.72);

  --ink-default:      #0D253D;     /* Stripe 同款深海军墨 */
  --ink-muted:        #4A5568;
  --ink-faint:        #8B95A3;
  --ink-inverse:      #F5F7FA;

  --accent-primary:   #5B6BF5;
  --accent-hover:     #4A5AE5;
  --accent-press:     #3B4BD5;
  --accent-secondary: #A155F7;
  --accent-warm:      #E86B1A;     /* 亮色下橙色调更沉 */
  --accent-cyan:      #0891B2;     /* 亮色下 cyan 调深以保持对比度 */
  --accent-cyan-hover:#0E7490;
  --accent-cyan-press:#155E75;
  --accent-success:   #10B981;
  --accent-warning:   #D97706;
  --accent-danger:    #EF4444;
  --accent-info:      #3B82F6;

  --hairline:         rgba(13, 37, 61, 0.08);
  --border-default:   #E8DFCC;
  --border-strong:    #D4C8A8;
  --border-accent:    rgba(91, 107, 245, 0.3);

  /* 亮色下渐变更微妙（白底叠加更轻） */
  --gradient-mesh-1:  radial-gradient(ellipse 80% 60% at 20% 0%,
                       rgba(91, 107, 245, 0.10) 0%, transparent 50%);
  --gradient-mesh-2:  radial-gradient(ellipse 70% 50% at 80% 100%,
                       rgba(161, 85, 247, 0.08) 0%, transparent 50%);
  --gradient-mesh-3:  radial-gradient(ellipse 60% 40% at 50% 50%,
                       rgba(91, 107, 245, 0.04) 0%, transparent 60%);
}
```

### 4.2 字体 token（`typography.css`）

```css
:root {
  --font-sans:  'Geist', 'Geist Fallback', 'HarmonyOS Sans SC',
                'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  --font-mono:  'Geist Mono', 'JetBrains Mono', 'HarmonyOS Sans Mono',
                'SF Mono', Menlo, monospace;
  --font-serif: 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', serif;

  /* 字号 (8 级) */
  --text-display-2xl: 4.5rem;     /* 72px - hero 标题 */
  --text-display-xl:  3.75rem;    /* 60px */
  --text-display-lg:  3rem;       /* 48px */
  --text-display-md:  2.25rem;    /* 36px */
  --text-display-sm:  1.875rem;   /* 30px */
  --text-heading-lg:  1.5rem;     /* 24px */
  --text-heading-md:  1.25rem;    /* 20px */
  --text-heading-sm:  1.125rem;   /* 18px */
  --text-body-lg:     1rem;       /* 16px */
  --text-body-md:     0.875rem;   /* 14px */
  --text-body-sm:     0.8125rem;  /* 13px */
  --text-caption:     0.75rem;    /* 12px */

  /* 字重 */
  --weight-regular:  400;
  --weight-medium:   500;
  --weight-semibold: 600;
  --weight-bold:     700;

  /* 行高 */
  --leading-tight:   1.2;
  --leading-snug:    1.4;
  --leading-normal:  1.6;
  --leading-relaxed: 1.8;

  /* 字距 */
  --tracking-tight:  -0.02em;
  --tracking-normal: 0;
  --tracking-wide:   0.04em;
  --tracking-num:    -0.01em;     /* 数字专用 */
}

/* 全局启用 tabular-nums 用于 <data>, <time>, 数字段落 */
:root {
  --feature-num: 'tnum' 1, 'lnum' 1;
}
.font-tabular {
  font-feature-settings: var(--feature-num);
}
```

### 4.3 间距 / 圆角 / 阴影 / 动效 token

```css
:root {
  /* === 间距 (4px base) === */
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

  /* === 圆角 === */
  --radius-sm:   6px;     /* 按钮 */
  --radius-md:   8px;     /* 输入框 */
  --radius-lg:   12px;    /* 卡片 */
  --radius-xl:   16px;    /* 弹窗 */
  --radius-2xl:  20px;    /* 大卡片 */
  --radius-pill: 9999px;

  /* === 阴影 === */
  --shadow-sm:    0 1px 2px rgba(10, 26, 47, 0.5);
  --shadow-md:    0 4px 12px rgba(10, 26, 47, 0.4);
  --shadow-lg:    0 12px 32px rgba(10, 26, 47, 0.35);
  --shadow-xl:    0 24px 48px rgba(10, 26, 47, 0.4);
  --shadow-glow:  0 0 32px rgba(91, 107, 245, 0.25);
  --shadow-focus: 0 0 0 3px rgba(91, 107, 245, 0.4);

  /* 亮色下阴影更深 */
}
:root[data-theme="light"] {
  --shadow-sm:    0 1px 2px rgba(13, 37, 61, 0.08);
  --shadow-md:    0 4px 12px rgba(13, 37, 61, 0.10);
  --shadow-lg:    0 12px 32px rgba(13, 37, 61, 0.12);
  --shadow-xl:    0 24px 48px rgba(13, 37, 61, 0.16);
  --shadow-glow:  0 0 32px rgba(91, 107, 245, 0.20);
}

:root {
  /* === 缓动曲线 === */
  --ease-stripe:  cubic-bezier(0.16, 1, 0.3, 1);
  --ease-bounce:  cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-in-out:  cubic-bezier(0.4, 0, 0.2, 1);
  --ease-out:     cubic-bezier(0, 0, 0.2, 1);

  /* === 时长 === */
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
  }
}
```

### 4.4 Tailwind 集成（`tailwind.config.js`）

```js
import { tokens } from './src/styles/tokens';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas:    'var(--bg-canvas)',
        surface: {
          1: 'var(--bg-surface-1)',
          2: 'var(--bg-surface-2)',
          3: 'var(--bg-surface-3)',
        },
        ink: {
          DEFAULT: 'var(--ink-default)',
          muted:   'var(--ink-muted)',
          faint:   'var(--ink-faint)',
          inverse: 'var(--ink-inverse)',
        },
        accent: {
          DEFAULT:  'var(--accent-primary)',
          hover:    'var(--accent-hover)',
          press:    'var(--accent-press)',
          secondary:'var(--accent-secondary)',
          warm:     'var(--accent-warm)',
        },
        border: {
          DEFAULT: 'var(--border-default)',
          strong:  'var(--border-strong)',
          accent:  'var(--border-accent)',
        },
        success: 'var(--accent-success)',
        warning: 'var(--accent-warning)',
        danger:  'var(--accent-danger)',
        info:    'var(--accent-info)',
      },
      fontFamily: {
        sans:  ['var(--font-sans)'],
        mono:  ['var(--font-mono)'],
        serif: ['var(--font-serif)'],
      },
      borderRadius: {
        sm:   'var(--radius-sm)',
        md:   'var(--radius-md)',
        lg:   'var(--radius-lg)',
        xl:   'var(--radius-xl)',
        '2xl':'var(--radius-2xl)',
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
      },
      transitionDuration: {
        fast:   'var(--duration-fast)',
        normal: 'var(--duration-normal)',
        slow:   'var(--duration-slow)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('tailwindcss-animate'),
  ],
};
```

---

## 5. 签名渐变背景（`backgrounds.css`）

### 5.1 实现

```css
.bg-mesh {
  position: fixed;
  inset: 0;
  z-index: -1;
  background:
    var(--gradient-mesh-1),
    var(--gradient-mesh-2),
    var(--gradient-mesh-3),
    var(--bg-canvas);
  pointer-events: none;
}

/* 强度分层 */
.bg-mesh--full    { opacity: 1.0; }   /* marketing / 首页 hero */
.bg-mesh--content { opacity: 0.7; }   /* 课程 / 学习 */
.bg-mesh--subtle  { opacity: 0.3; }   /* workspace / admin / 工具页 */

/* SVG noise overlay 消除 banding */
.bg-noise::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9'/></filter><rect width='100%' height='100%' filter='url(%23n)' opacity='0.03'/></svg>");
  opacity: 0.4;
  mix-blend-mode: overlay;
  pointer-events: none;
}

/* 渐变呼吸动画（30s 循环） */
@keyframes mesh-breathe {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(2%, -1%) scale(1.02); }
}
.bg-mesh--breathing { animation: mesh-breathe 30s ease-in-out infinite; }

/* 性能回退 */
@media (prefers-reduced-motion: reduce) {
  .bg-mesh--breathing { animation: none; }
}
```

### 5.2 应用规则

| 区域 | 类名 | 强度 | 备注 |
|---|---|---|---|
| 首页 hero | `.bg-mesh.bg-mesh--full.bg-mesh--breathing` | 100% + 呼吸 | 视觉爆点 |
| 首页工具网格 / 课程页 | `.bg-mesh.bg-mesh--content` | 70% | 强但不刺眼 |
| Workspace / Admin / 工具页 | `.bg-mesh.bg-mesh--subtle` | 30% | 微弱呼吸 |
| 弹窗内 | 不应用 | — | 弹窗自带遮罩 |
| Login / 404 / 空状态 | `.bg-mesh.bg-mesh--full` | 100% | 品牌时刻 |

---

## 6. 组件库（`components/ui/`）

### 6.1 原语清单（18 个）

| 原语 | 基于 Radix | 主要变体 |
|---|---|---|
| Button | — | primary, secondary, ghost, outline, destructive, link；size: sm, md, lg；loading 状态 |
| Card | — | default, bordered, elevated, glass（毛玻璃） |
| Input | — | default, error, success, with-icon, with-prefix, with-suffix |
| Modal (Dialog) | Dialog | sm, md, lg, fullscreen；confirm 变体 |
| Dropdown Menu | DropdownMenu | 菜单项、分割线、checkbox、radio |
| Tabs | Tabs | underline, pill, card |
| Toast | Toast | info, success, warning, danger；含渐变背景变体 |
| Tooltip | Tooltip | top, right, bottom, left |
| Select | Select | default, searchable, multi |
| Switch | Switch | sm, md；loading |
| Checkbox | Checkbox | default, indeterminate；label 联动 |
| Badge | — | solid, soft, outline, dot；color: 7 种语义色 |
| Avatar | — | image, initials, fallback；size: xs/sm/md/lg/xl |
| Separator | Separator | horizontal, vertical |
| Skeleton | — | text, circle, rect；含渐变动画 |
| Popover | Popover | default, with-arrow |
| Slider | Slider | single, range；step marks |
| Theme Switcher | — | 三态：暗 / 亮 / 跟随系统 |

### 6.2 Button 原语范本

```tsx
// components/ui/button.tsx
import { cva, type VariantProps } from 'class-variance-authority';
import { Slot } from '@radix-ui/react-slot';
import { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/cn';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-md font-medium ' +
  'transition-all duration-fast ease-stripe ' +
  'focus-visible:outline-none focus-visible:shadow-focus ' +
  'disabled:opacity-50 disabled:pointer-events-none',
  {
    variants: {
      variant: {
        primary:
          'bg-accent text-white hover:bg-accent-hover active:bg-accent-press ' +
          'shadow-glow hover:shadow-lg',
        secondary:
          'bg-surface-2 text-ink hover:bg-surface-3 border border-border',
        ghost:
          'text-ink hover:bg-surface-2',
        outline:
          'border border-border-accent text-accent hover:bg-accent/10',
        destructive:
          'bg-danger text-white hover:bg-danger/90',
        link:
          'text-accent underline-offset-4 hover:underline',
      },
      size: {
        sm: 'h-8 px-3 text-body-sm',
        md: 'h-10 px-4 text-body-md',
        lg: 'h-12 px-6 text-body-lg',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild, loading, children, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        disabled={loading || props.disabled}
        {...props}
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        {children}
      </Comp>
    );
  }
);
```

### 6.3 原语约束

1. **零业务知识**：原语不知道 Tool、User、Course 等业务概念，只接收 props
2. **样式仅来自 token**：原语不写死任何 hex / px / rem，所有值都通过 `var(--*)` 或 Tailwind utility 间接引用
3. **完整的 TypeScript 类型**：每个原语导出 props 接口，使用方 IDE 自动补全
4. **a11y 基础**：使用 Radix 原语时它已处理 keyboard / ARIA，自建原语需手动处理 focus-visible / role / aria-label
5. **可单独替换**：业务组件用 `import { Button } from '@/components/ui/button'` 即可使用，未来换底层不破坏业务

---

## 7. 页面处理策略

### 7.1 公共首页（`HomePage.tsx`）

- **背景**：`.bg-mesh.bg-mesh--full.bg-mesh--breathing`（全强度呼吸）
- **Hero**：Geist display-xl 字"工具箱 / ToolKit" + 副标"为开发者与产品经理打造的多工具聚合平台" + 双 CTA（"开始使用" → 登录弹框、"了解更多" → 滚动到工具网格）
- **Logo**：Pacifico + 渐变填充居中
- **工具网格**：每张卡片 `.card-glass`（毛玻璃 + backdrop-blur + 渐变描边 hover）+ lucide 图标
- **统计区**：数据卡片（用户数 / 工具数 / 调用次数），数字用 tabular-nums + accent-warm

### 7.2 Workspace（`WorkspacePage.tsx` + `WorkspaceSidebar.tsx`）

- **背景**：`.bg-mesh.bg-mesh--subtle`
- **侧边栏**：w-56 改左，bg-surface-1 + border-r + 滚动定制
- **标签栏**：顶部 tab 切换已开工具，使用 Radix Tabs
- **主面板**：保持当前 IDE 密度（顶部条 + split-pane + 状态栏结构），仅换皮肤
- **关闭/重排**：用 Radix Dropdown 菜单替代自定义

### 7.3 Admin 后台（`AdminLayout.tsx`）

- **背景**：`.bg-mesh.bg-mesh--subtle`
- **侧边栏**：w-64，bg-surface-1 + border-r，导航项 hover 时左侧出现 2px 渐变条（用 `--gradient-accent`）
- **active 项**：bg-surface-2 + border-accent + text-accent
- **顶部 Header**：包含 logo + 当前页面包屑 + 主题切换器 + 用户菜单
- **内容区**：保持现有表单/表格结构，仅换皮肤

### 7.4 课程/学习页（`CoursesPage.tsx` / `CourseLearnPage.tsx`）

- **背景**：`.bg-mesh.bg-mesh--content`
- **标题**：用 `font-serif`（Noto Serif SC），更文学化
- **卡片**：课程卡片用 `.card-elevated` + 课程封面渐变覆盖
- **学习页主体**：宽留白（max-w-3xl），行高 leading-relaxed，章节标题用 serif，正文用 sans
- **进度条**：渐变填充 + 微发光

### 7.5 工具页（**24 个组件 / 25 个路由**，逐一替换）

**统一外壳**：

```tsx
<div className="flex-1 text-ink flex flex-col overflow-hidden bg-canvas">
  <header className="bg-surface-1 border-b border-border px-4 py-2 flex items-center">
    <ToolIcon /> <h1 className="font-medium">{toolName}</h1>
    <div className="ml-auto flex gap-2">{/* 工具专属 actions */}</div>
  </header>

  {error && (
    <div className="bg-danger/10 border-b border-danger/30 px-4 py-2 text-danger text-body-sm">
      {error}
    </div>
  )}

  <main className="flex-1 flex overflow-hidden">
    {/* 工具专属 split-pane 内容 */}
  </main>

  <footer className="bg-surface-1 border-t border-border px-4 py-1 text-caption text-ink-faint">
    {/* 状态信息 */}
  </footer>
</div>
```

**优先级替换顺序**（按使用频率）：

1. **第一梯队**（高频工具，先做）：JSON 格式化、HTTP 客户端、Markdown 编辑器、密钥生成、跨设备分享（CrossShare）
2. **第二梯队**（中等频率）：SSH、Redis、数据库、K8s、PM Agent、OpenClaw、TokenUsage
3. **第三梯队**（低频或工具聚合类）：OCR、ASR、ImageGen、ImageDownloader、VideoDownloader、Calendar、SystemMonitor、CursorHistory、MarkItDownConverter、OpenSpecCourse、LearningSharePlatform、AI Assistant

每个工具页只动样式，业务逻辑零修改。组件替换策略：
- 旧的 `bg-slate-800 rounded-xl border border-slate-700` → `bg-surface-2 rounded-lg border border-border`
- 旧的 `<i className="fas fa-...">` → **Phase 3 引入 `<Icon name="..." />` 抽象组件后**替换（Phase 1 / Phase 2 保留 FA 不变）
- 旧的 `<button className="bg-blue-600 ...">` → `<Button variant="primary">...</Button>`
- **CrossShareMain 改造项**：从 eager 改 lazy 加载（仅 24 工具中唯一非 lazy，影响首屏 bundle）

### 7.6 登录弹框（`LoginModal.tsx`）

- **背景**：弹窗本体用 `bg-surface-1` + `shadow-xl` + 圆角 `radius-xl`
- **居中卡片**：max-w-md，包含 logo + 渐变 + 表单
- **强调色**：warm orange `#FF8A4C` 用于"主要操作"按钮（与登录转化目标匹配）
- **入场动画**：Framer Motion + ease-stripe，240ms，scale 0.95→1 + opacity 0→1

### 7.7 Markdown 编辑器（`MarkdownEditor.tsx` + `MarkdownEditor.css`）

- **背景**：`.bg-mesh.bg-mesh--subtle`
- **删除原 `MarkdownEditor.css` 的独立赛博朋克主题**：所有变量改为引用 `tokens/colors.css`
- **保留"专业编辑器"调性**：双栏（编辑 / 预览），等宽字体用于代码块
- **预览区 H1 渐变**：保留原 `linear-gradient(45deg, #00f5ff, #ff00ff)` 但改为 `linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))`
- **新增 dark/light 同步**：编辑器和预览区都跟随 `data-theme`

### 7.8 个人中心（`AccountSettings.tsx`）

- **背景**：`.bg-mesh.bg-mesh--subtle`
- **表单**：输入框改用新 Input 原语
- **数据卡片**：用户统计、订阅、配额用 tabular-nums + accent-warm 强调
- **主题切换器**：集成到设置页

### 7.9 TechContents 内容页（`TechContentsPage.tsx` + `TechContentDetailPage.tsx`）

- **背景**：`.bg-mesh.bg-mesh--content`（介于 marketing 与 workspace 之间）
- **路由**：`/tech-contents`（列表） + `/tech-contents/:slug`（详情）
- **列表页**：网格布局，每张技术内容卡片用 `.card-elevated` + 渐变边框 hover
- **详情页**：宽留白（max-w-3xl），正文 sans（Geist），章节标题用 serif（Noto Serif SC，呼应课程区点缀）
- **代码块**：保留 ` monospace` 字体（Geist Mono）+ `--neon-cyan` 高亮配色（与 Markdown 编辑器风格一致）
- **小程序对应**：`package-learning/pages/tech-contents/*`（Phase 5 同步）

### 7.10 首页 Recommendations 组件（`RecommendationCard.tsx`）

- **背景**：嵌入首页 hero 下方或工具网格之后
- **卡片**：`.card-glass`（毛玻璃 + backdrop-blur）+ 渐变描边
- **图标**：复用 `<Icon name="..." />`（Phase 3 引入后）；Phase 1-2 保留 `fas ${icon}` 渲染
- **数据来源**：与 ToolCard 类似的 API，icon 从 props 传入

---

## 8. 主题切换器

### 8.1 状态机

```ts
type Theme = 'dark' | 'light' | 'system';
```

存储：localStorage `tk-theme`，默认 `'system'`。

### 8.2 应用逻辑

```ts
// lib/theme.ts
export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  const resolved =
    theme === 'system'
      ? window.matchMedia('(prefers-color-scheme: light)').matches
        ? 'light' : 'dark'
      : theme;

  root.setAttribute('data-theme', resolved);
  localStorage.setItem('tk-theme', theme);
}

// 监听系统主题变化
window.matchMedia('(prefers-color-scheme: light)')
  .addEventListener('change', () => {
    if (localStorage.getItem('tk-theme') === 'system') {
      applyTheme('system');
    }
  });
```

### 8.3 Theme Switcher 原语

```tsx
// components/ui/theme-switcher.tsx
import { Moon, Sun, Monitor } from 'lucide-react';
import { useTheme } from '@/lib/theme';

export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="flex bg-surface-2 rounded-pill p-1">
      {(['light', 'dark', 'system'] as const).map((t) => (
        <button
          key={t}
          onClick={() => setTheme(t)}
          className={cn(
            'h-7 px-3 rounded-pill text-body-sm transition-all duration-fast ease-stripe',
            theme === t
              ? 'bg-accent text-white shadow-glow'
              : 'text-ink-muted hover:text-ink'
          )}
        >
          {t === 'light' && <Sun className="h-3.5 w-3.5" />}
          {t === 'dark' && <Moon className="h-3.5 w-3.5" />}
          {t === 'system' && <Monitor className="h-3.5 w-3.5" />}
        </button>
      ))}
    </div>
  );
}
```

---

## 9. Logo 与品牌

### 9.1 Logo 处理（`Header.tsx`）

```tsx
<h1 className="font-['Pacifico',_cursive] text-3xl
               bg-gradient-to-br from-accent to-accent-secondary
               bg-clip-text text-transparent select-none">
  工具箱
</h1>
```

### 9.2 品牌色应用规则

| 元素 | 颜色 |
|---|---|
| Logo 文字 | `from-accent to-accent-secondary` 渐变填充 |
| 主要 CTA 按钮 | `bg-accent` |
| 链接 / hover | `text-accent-hover` |
| 选中状态 | `bg-accent/10 border border-accent` |
| 数字 / 价格 | `text-accent-warm` + tabular-nums |
| 加载 / 进度 | `bg-gradient-to-r from-accent to-accent-secondary` |

---

## 10. 动效语言

### 10.1 全局缓动

- **hover / tap**：`var(--ease-stripe)` 150ms（小快）
- **弹窗 / 抽屉**：`var(--ease-stripe)` 240ms（招牌 ease-out）
- **页面切换**：`var(--ease-stripe)` 420ms
- **数字滚动**：`var(--ease-out)` 720ms

### 10.2 关键动效

**按钮 hover**：
```css
.btn {
  transition: transform var(--duration-fast) var(--ease-stripe),
              box-shadow var(--duration-fast) var(--ease-stripe),
              background-color var(--duration-fast) var(--ease-stripe);
}
.btn:hover { transform: translateY(-1px) scale(1.01); }
.btn:active { transform: translateY(0) scale(0.99); }
```

**弹窗入场**（Framer Motion）：
```tsx
<motion.div
  initial={{ opacity: 0, scale: 0.95, y: 8 }}
  animate={{ opacity: 1, scale: 1, y: 0 }}
  exit={{ opacity: 0, scale: 0.95, y: 8 }}
  transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
/>
```

**签名渐变呼吸**：30s 循环，缓慢到不察觉

**表单提交**：按钮内部渐变从左到右流动 800ms 然后归位（仅 primary variant）

### 10.3 无障碍

`@media (prefers-reduced-motion: reduce)` 全局禁用时长（设为 0ms），渐变呼吸停止。

---

## 11. 小程序同步

### 11.0 页面分类（PC ↔ MP 对应关系）

**PC 端独有的页面**（7 页，无 MP 对应））：

- `/`（HomePage）
- `/admin/*`（13 个 admin 路由，MP 不开放后台）
- `/account-settings`（MP 用 `pages/profile` 等价）
- `/tech-contents/:slug`（MP 有 `package-learning/pages/tech-contents/detail`，但内容可能不同步）

**MP 端独有的页面**（8 页，无 PC 对应）：

- `pages/index`（MP 工具导航页）
- `pages/profile`（个人中心，PC 用 `/account-settings`）
- `pages/login`（PC 用全局 LoginModal）
- `pages/change-password`（PC 在 `/account-settings` 内）
- `pages/help`（PC 在 `/courses/:slug/help` 或独立页）
- `package-learning/pages/tech-contents/index`（内容列表，PC 用 `/tech-contents`）
- `package-learning/pages/tech-contents/detail`（内容详情，PC 用 `/tech-contents/:slug`）

**同步目标（15 页有 PC 对应）**：

- 工具页（10 页）：JSON / Calendar / KeyGenerator / OCR / ASR / HTTP Client / ImageDownloader / VideoDownloader / MarkItDownConverter / MarkdownEditor
- 跨设备（2 页）：CrossShare / messages + CrossShare / files
- OpenClaw（1 页）
- 学习平台（2 页）：CoursePlatform / list + CoursePlatform / detail（对应 PC 的 LearningSharePlatform + OpenSpecCourse）

**Token 同步清单**：同步 token 覆盖全部 PC 页面（含 Admin）；MP 端 23 页全部应用 token，但 PC 独有页面不强制 MP 端对应。

### 11.1 Token 同步机制

**Codegen 脚本**（`scripts/sync-miniprogram-tokens.ts`）：

```ts
// 读 frontend/src/styles/tokens/colors.css
// 转 SCSS 变量：
//   $bg-canvas: #0A1A2F;
//   $bg-canvas-light: #F5E9D4;
// 用 rpx 单位（设计稿 750px → 1px = 2rpx）

// 写 mini-program/src/styles/tokens.scss
// 写 mini-program/src/styles/dark.scss
// 写 mini-program/src/styles/light.scss
```

执行时机：每次 `frontend/src/styles/tokens/*.css` 修改后，自动触发（pre-commit hook 或手动 `npm run sync:tokens`）。

### 11.2 小程序组件策略

PC 端组件**结构**差异映射：

| PC 组件 | 小程序等价 | 实现方式 |
|---|---|---|
| Sidebar（侧边栏） | 底部 Tab Bar | `<TabBar>` 原生组件 |
| Modal | 底部 Action Sheet | `<PageContainer>` + 自定动画 |
| Dropdown | ActionSheet | `<ActionSheet>` API |
| Toast | wx.showToast 风格 | 自建，token 化 |
| Tooltip | — | 小程序无 Tooltip 概念，省略 |
| Tabs（垂直/水平） | 顶部 Tab + 侧栏 | `<Tabs>` 自建 |
| DatePicker | wx picker | 系统原生 |

PC 原语**样式 token 直接复用**：颜色 / 字号 / 间距 / 圆角 / 阴影全部走同一份。

### 11.3 平台适配

- **rpx**：所有长度转 rpx（设计稿 750，1px = 2rpx）；token 文件用 px 表达，codegen 时转换
- **字体栈**：小程序去掉 Geist（体积），保留 `'HarmonyOS Sans SC', 'PingFang SC', sans-serif`，等宽用 `'Geist Mono', monospace`（如果体积允许）
- **渐变背景**：PC 100% 的页面，小程序降到 70%（性能 + 微信原生审美）
- **暗 / 亮模式**：通过 `wx.setStorageSync('tk-theme')` + `page.setData({ theme })` 切换，所有 SCSS 变量按 `[data-theme="light"]` 选择器切换

---

## 12. 迁移路径（5 阶段，3-4 周）

### Phase 1：Token + 基建（5-7 天）

**完成标志**：

- [ ] `frontend/src/styles/tokens/*.css` 全部建立
- [ ] `frontend/src/styles/backgrounds.css` 大气背景就位
- [ ] `frontend/tailwind.config.js` 接入 token
- [ ] 字体加载（Geist + Geist Mono woff2 子集化 + HarmonyOS Sans SC 系统回退）
- [ ] Logo 渐变填充
- [ ] 主题切换器可用（暗 / 亮 / 跟随系统）
- [ ] `<div className="bg-mesh ...">` 已挂在 Layout 根

**验证**：

- 首页可见大气背景呼吸效果
- 主题切换可工作（亮色下奶油色正确，文字对比度 ≥ AA）
- `npm run build` 通过，CSS 变量无未定义引用

### Phase 2：组件原语 + 公共页（5-7 天）

**完成标志**：

- [ ] 18 个原语全部建立（Button、Card、Input、Modal、Dropdown、Tabs、Toast、Tooltip、Select、Switch、Checkbox、Badge、Avatar、Separator、Skeleton、Dialog、Popover、Slider）
- [ ] Storybook（或独立 Demo 页 `/dev/components`）展示所有原语
- [ ] Layout / Header / Footer 重构完成
- [ ] HomePage 重构（hero + 工具网格）
- [ ] Workspace（侧边栏 + tab）重构
- [ ] LoginModal / Toast / Modal 原语化

**验证**：

- 18 个原语在 `/dev/components` 展示完整
- 首页 hero、工具网格视觉达到 Stripe 级
- Workspace 切换工具流畅

### Phase 3：Admin + 工具页（10-14 天）

**前置条件**：Phase 2 完成 `<Icon name="..." />` 抽象组件（同时支持 FA 与 lucide，按 name 前缀分发：`name="fa-home"` 走 FA，`name="home"` 走 lucide）。

**完成标志**：

- [ ] AdminLayout 重构（侧边栏细化 + `<RequireAuth role="admin">` 显式守卫）
- [ ] 通用工具页外壳 `<ToolShell>` 抽出（含 ErrorBoundary）
- [ ] CrossShareMain 改 lazy 加载
- [ ] 第一梯队 6 个工具页替换（JSON / HTTP / Markdown / 密钥 / 跨设备 / TokenUsage）
- [ ] 第二梯队 6 个工具页替换（SSH / Redis / DB / K8s / PM Agent / OpenClaw）
- [ ] 第三梯队 12 个工具页替换（OCR / ASR / ImageGen / ImageDownloader / VideoDownloader / Calendar / SystemMonitor / CursorHistory / MarkItDownConverter / OpenSpecCourse / LearningSharePlatform / AIAssistant）
- [ ] **icon 字段后端迁移脚本**（`scripts/migrate-tool-icons.ts`：数据库 `tools.icon` / `agents.icon` / `courses.icon` 从 `fa-xxx` 转 lucide 名）
- [ ] **Font Awesome 静态引用迁移**：硬编码 `fas fa-xxx` 改为 `<Icon name="xxx" />`（按 priority 顺序）
- [ ] **Font Awesome 动态引用迁移**：变量/props 模板字符串改为 `<Icon name={...} />`
- [ ] **后端数据迁移完成**：admin 通过 API 重新写入 icon 字段
- [ ] **移除 Font Awesome CDN**（仅在 1,011 处全部迁移 + 后端 icon 字段迁移完成后）+ `index.html` 删除 FA link

**验证**：

- 所有 **24 个工具组件（25 路由）**视觉一致（统一外壳）
- 图标系统：FA 用量 1,011 → 0
- 后端数据库 icon 字段全部为 lucide 名（无 fa- 前缀）
- 工具内数据流不破坏（单元测试通过）

### Phase 4：课程 + Markdown 编辑器 + 主题系统整合（5-7 天）

**完成标志**：

- [ ] 课程列表 / 详情 / 学习页重构（serif 字体点缀）
- [ ] **TechContents 列表 / 详情**页重构（与课程页同风格 + serif 章节标题）
- [ ] Recommendations 组件重构（首页内嵌）
- [ ] Markdown 编辑器整合进 token 系统（原赛博朋克主题通过 `data-theme` 自动切换）
  - `MarkdownEditor.css` 的 `--neon-*` / `--bg-*` 变量从 `:root` 移到 `.markdown-editor-container` 作用域
- [ ] 个人中心 + 设置页（含主题切换器）
- [ ] **CursorHistory 接入 ThemeProvider**（`cursorThemes.ts` 改造为读 `useTheme()`；`--theme-*` 变量从 `:root` 移到 `.cursor-history-container` 作用域）
- [ ] **MarkdownEditor 的 `.dark-theme` class 改造**：改为读 `data-theme` 属性
- [ ] **PreferencesSection 接入 ThemeProvider**：替换休眠的本地 useState

**验证**：

- 课程 / TechContents 详情页标题用 Noto Serif SC
- Markdown 编辑器在 dark/light 双模式下渲染一致
- 设置页可保存主题偏好（与全局 ThemeProvider 同步）
- CursorHistory 颜色随主题切换（不再"卡"在原 `--theme-*`）
- MarkdownEditor 颜色随主题切换

### Phase 5：小程序同步（3-5 天）

**完成标志**：

- [ ] Codegen 脚本 `scripts/sync-miniprogram-tokens.ts` 就绪
- [ ] `mini-program/src/styles/tokens.scss` 等 SCSS 文件由 codegen 生成
- [ ] 小程序首页 / 工具列表 / 工具详情 / 个人中心 重构
- [ ] 小程序主题切换器（设置页）
- [ ] 微信开发者工具双模式预览通过

**验证**：

- PC 和小程序 token 一致（用脚本对比无差异）
- 小程序在真机暗 / 亮模式下渲染正确
- 渐变背景在小程序性能可接受（不卡顿）

---

## 13. 测试策略

### 13.1 视觉回归

- 用 Playwright + 截图对比（before/after）记录首页、Workspace、Admin、工具页的关键状态
- 验证 WCAG AA 对比度（亮色画布上的 `--ink-default`，暗色画布上的 `--ink-default` 都 ≥ 4.5:1）

### 13.2 组件测试（Vitest + React Testing Library）

- 18 个原语各 1 个测试：渲染、variant、disabled、loading、focus
- 主题切换器：localStorage 读写、`data-theme` 属性设置
- cn.ts 工具：类名去重、undefined 安全

### 13.3 集成测试

- 登录弹框 → 登录成功 → Workspace 数据刷新（沿用 `useAuthPageData` hook 已存在测试）
- 主题切换 → localStorage 持久化 → 刷新页面后保留

### 13.4 性能验证

- 首页 LCP（最大内容绘制）≤ 2.5s（暗色 + 大气背景）
- Workspace FCP（首次内容绘制）≤ 1.5s
- 字体加载总大小 ≤ 300KB（Geist woff2 子集 + Geist Mono woff2 子集）
- 主题切换不闪烁（CSS 变量切换瞬时）

### 13.5 手动验证清单（用户验收）

- [ ] 首页：暗色下大气背景呼吸效果明显，工具卡片 hover 微发光
- [ ] 首页：亮色下奶油画布温暖，紫罗兰蓝主色统一
- [ ] Workspace：开启 JSON 工具 + Markdown 工具 + 切换 tab 流畅
- [ ] Admin：13 个后台页切换无样式异常
- [ ] 课程：详情页用 serif 标题，正文清晰
- [ ] Markdown 编辑器：双栏布局，编辑/预览区字体一致，H1 渐变保留
- [ ] 主题切换器：点击立即切换，刷新保留
- [ ] 字体加载：无 FOIT（不可见文字闪烁），FOUT（可见文字闪烁）≤ 100ms
- [ ] 响应式：移动端（375px）布局不破
- [ ] 小程序：真机暗 / 亮模式预览通过

---

## 14. 风险与权衡

| 风险 | 缓解策略 |
|---|---|
| Geist + Geist Mono 字体体积大 | woff2 子集化（仅拉丁 + 数字 + 常用符号），`font-display: swap`；HarmonyOS Sans SC + Noto Serif SC 留系统回退避免双倍字体下载 |
| 大气背景低端设备性能 | SVG noise overlay 用 data URI（无 HTTP 请求），渐变用 GPU 加速的 `transform` 而非 `background-position` |
| 双模式 token 维护成本 | CSS 变量是单一真相源，`data-theme` 切换瞬时无重排 |
| shadcn/ui 默认观感风险 | 大量 token 覆盖 + 渐变签名贯穿，禁止"shadcn 默认出场" |
| 小程序 Taro + SCSS 同步漂移 | Codegen 脚本 + pre-commit hook 强制同步 |
| Markdown 编辑器原有用户期待赛博朋克 | 保留 H1 渐变 + 双栏布局，仅去掉独立霓虹变量层；`MarkdownEditor.css` 的霓虹变量从 `:root` 移到 `.markdown-editor-container` 作用域避免与新 token 冲突 |
| **🔴 Font Awesome 大规模迁移风险**（1,011 处引用 / 121 文件 / 含 20+ 文件动态图标 / 后端数据库 icon 字段） | **分阶段策略**：Phase 1 保留 FA CDN + 新增 `<Icon name="..." />` 抽象组件（同时支持 FA 与 lucide，按 name 前缀分发）；Phase 3 逐工具迁移 → 测试 → 在所有图标迁移完成后才移除 CDN；后端数据库 `icon` 字段提供 SQL 迁移脚本（`fa-xxx` → lucide 名）|
| **🟠 3 个现有主题系统共存风险**（CursorHistory / MarkdownEditor / MarkdownEditor.css） | Phase 1 不触碰这 3 个系统；Phase 4 把它们接入新 ThemeProvider（CursorHistory 的 `--theme-*` 收敛到 `.cursor-history-container` 作用域；MarkdownEditor 的 `.dark-theme` class 改造为读 `data-theme`）|
| **🟠 cyan 品牌色保留风险**（403 处使用，violet-blue 仅 29 处） | 不强迁 cyan；引入 `--accent-cyan` token；Phase 3 时 cyan 保留原使用位置，violet-blue 仅替换原 primary/secondary 别名（29 处）|
| **🟠 Admin 路由无显式鉴权守卫** | Phase 2 重构 AdminLayout 时增加 `<RequireAuth role="admin">` 包裹（设计系统迁移无关但是顺带改进）|
| **🟡 CrossShareMain eager 加载风险**（24 工具唯一非 lazy） | Phase 3 改 lazy（bundle 优化，与设计系统无关但是顺带改进）|
| **🟡 重复路由 bug**（`/courses/:slug/learn` 声明两次） | Phase 2 重构 App.tsx 时清理 |
| 主题切换闪烁（FOUC） | 在 `<head>` 内联一段 critical CSS（包含 `--bg-canvas`、`color` 等最基本变量） |
| 渐变背景在长 workspace 会话引起视觉疲劳 | 25% 强度 + 30s 呼吸 + 不在编辑器/数据表格区增加额外色彩 |

---

## 15. 不做的事（范围外）

- 不做暗/亮之外的"自定义主题"（用户不能调色板编辑器）
- 不做无障碍深度审计（仅保证 WCAG AA 文本对比度，不做完整键盘穿越 / ARIA 全套）
- 不做动画性能优化（GPU 加速等），仅保证 `prefers-reduced-motion` 兜底
- 不做国际化（i18n）系统重构（沿用现有 i18n）
- 不重做 Header 的搜索功能 / Footer 的链接
- 不做"页面 A/B 测试"基础设施
- 不做设计令牌 JSON 导出（仅 CSS + SCSS 两份，给后续 Figma sync 留口）
- 不做组件版本号管理（仅 git history）
- 不迁移现有主题切换器（`themes/cursorThemes.ts` 内的多色方案），仅保留 dark/light 两态

---

## 16. 验收标准（Definition of Done）

设计系统全量重构完成的标志：

1. ✅ PC 端 **24 个工具组件（25 路由）** + 公共首页 + Workspace + Admin + 课程页 + AccountSettings + TechContents + Recommendations **全部**视觉达到 Stripe 级（背景渐变、token 一致、原语化）
2. ✅ 暗 / 亮双模式可平滑切换，主题持久化到 localStorage
3. ✅ 18 个原语在 `/dev/components` 展示完整，所有业务组件基于原语构建
4. ✅ 图标系统统一为 lucide-react，无 Font Awesome 残留
5. ✅ Logo 渐变填充 + 课程区衬线点缀
6. ✅ 微信小程序核心页面（首页 / 工具列表 / 工具详情 / 个人中心）同步 token
7. ✅ `npm run type-check && npm run lint && npm run build` 全通过
8. ✅ WCAG AA 对比度审计通过（所有文本 / 背景组合）
9. ✅ 字体加载 ≤ 300KB 总大小，无 FOIT 闪烁
10. ✅ 性能：首页 LCP ≤ 2.5s，Workspace FCP ≤ 1.5s

---

## 17. 相关文档

- `awesome-design-md/design-md/stripe/DESIGN.md`（品牌参考）
- `awesome-design-md/design-md/linear.app/DESIGN.md`（次级参考）
- `awesome-design-md/design-md/vercel/DESIGN.md`（字体参考：Geist 来源）
- `CLAUDE.md`（项目总体规则）
- `docs/superpowers/specs/`（其他 spec，借鉴结构）