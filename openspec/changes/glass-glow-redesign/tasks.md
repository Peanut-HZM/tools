# 玻璃光晕全站改版 · 实施计划（阶段①–③：设计系统基建 + Web 核心页面）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地「玻璃光晕」设计系统的 token 基建（primitive/semantic/玻璃工具类/字体修复）并完成 Web 核心页面改版（基础组件、Header+⌘K、Footer、首页 Hero/ToolGrid/ToolCard），产出可被后续阶段（④–⑨）直接复用的完整设计系统。

**Architecture:** Token 单一来源在 `frontend/src/styles/tokens/*.css`（primitive 原始色板 → semantic 语义层），Web 经 Tailwind 映射与 CSS 变量消费，小程序经 `generate-miniapp-tokens.js` 生成 SCSS（后续阶段）。视觉语言统一为玻璃拟态 + 紫蓝渐变，所有组件只引用 semantic token。

**Tech Stack:** React 18 + TypeScript + Tailwind + CSS 自定义属性；Radix UI（Dialog/Popover 等）；cva；lucide-react；Vitest。**不新增任何 npm 依赖。**

## Global Constraints（每个任务隐含遵守）

- 不新增 npm 依赖；不改业务逻辑、API、路由结构、后端。
- 所有代码注释使用中文；遵循 AGENTS.md 热重载规范（改组件/CSS 不重启服务）。
- 暗色为默认主题；`data-theme`（dark/light/system）机制不变（`lib/theme.tsx` 不动）。
- 语义 token 值必须是 `R G B` 三元组或简单 rgba/渐变声明（保证可被 `generate-miniapp-tokens.js` 解析），semantic 引用 primitive 用 `var(--p-*)`。
- 工作目录均在 `frontend/` 下执行命令。构建验证：`npm run build`；类型检查：`npx tsc --noEmit`（package.json 无 type-check 脚本）；单测：`npx vitest run`。
- 提交信息用 conventional commits + 中文描述（如 `feat(design-system): 新增 primitive 调色板`）。
- 设计稿基准（已确认）：暗色玻璃 + `#5B6BF5→#A155F7` 渐变主色，见 `design.md` §3、§5。

---

## 阶段① Token 基建

### Task 1: primitive 调色板

**Files:**
- Create: `frontend/src/styles/tokens/_primitives.css`
- Modify: `frontend/src/styles/tokens/index.css`（加一行 @import）

**Interfaces:**
- Produces: `--p-*` 原始色阶变量（后续所有 semantic 引用它；命名前缀 `--p-` 为团队约定）

- [ ] **Step 1: 创建 `_primitives.css`**

```css
/* ============================================================
 * Primitive 原始调色板 —— 唯一色值来源（不要在业务代码引用 --p-*）
 * 命名：--p-<色名>-<阶>，值为 "R G B" 三元组
 * ============================================================ */
:root {
  /* 品牌紫蓝 */
  --p-violet-300: 165 180 252;
  --p-violet-400: 139 155 255;
  --p-violet-500: 91 107 245;
  --p-violet-600: 74 90 229;
  --p-violet-700: 59 75 213;
  --p-purple-400: 192 132 252;
  --p-purple-500: 161 85 247;
  --p-purple-600: 146 66 240;
  --p-blue-300:  147 197 253;
  --p-blue-400:  96 165 250;
  --p-blue-500:  59 130 246;
  --p-blue-600:  37 99 235;
  --p-cyan-300:  103 232 249;
  --p-cyan-400:  34 211 238;
  --p-cyan-500:  6 182 212;
  --p-cyan-600:  8 145 178;

  /* 中性底色（暗色系） */
  --p-navy-950: 6 10 22;
  --p-navy-900: 10 18 37;
  --p-navy-800: 15 25 48;
  --p-navy-700: 21 33 64;
  --p-navy-600: 27 42 80;

  /* 中性底色（亮色系） */
  --p-gray-50:  246 247 251;
  --p-gray-100: 241 243 249;
  --p-gray-200: 231 234 243;
  --p-gray-300: 226 230 240;
  --p-gray-400: 203 210 227;

  /* 文字（暗色系用） */
  --p-ink-light-1: 245 247 250;
  --p-ink-light-2: 184 194 209;
  --p-ink-light-3: 110 122 143;
  /* 文字（亮色系用） */
  --p-ink-dark-1: 13 37 61;
  --p-ink-dark-2: 74 85 104;
  --p-ink-dark-3: 139 149 163;

  /* 状态色 */
  --p-green-400: 110 231 183;
  --p-green-500: 52 211 153;
  --p-green-600: 16 185 129;
  --p-amber-400: 251 191 36;
  --p-amber-600: 217 119 6;
  --p-red-400:  248 113 113;
  --p-red-500:  239 68 68;
}
```

- [ ] **Step 2: 注册到 `tokens/index.css`**

在 `@import './colors.css';` 之前加入一行：

```css
@import './_primitives.css';
```

- [ ] **Step 3: 验证构建**

Run: `cd frontend && npm run build`
Expected: 构建成功（CSS 变量未消费不报错）

- [ ] **Step 4: Commit**

```bash
git add frontend/src/styles/tokens/_primitives.css frontend/src/styles/tokens/index.css
git commit -m "feat(design-system): 新增 primitive 原始调色板"
```

---

### Task 2: semantic token 升级（亮色冷调 + 玻璃组 + 渐变组）+ Tailwind 映射

**Files:**
- Modify: `frontend/src/styles/tokens/colors.css`（暗色块微调、亮色块整块替换、两块各追加玻璃/渐变组）
- Modify: `frontend/src/styles/tokens/shadows.css`（追加 glass/glow 阴影 + light 覆盖）
- Modify: `frontend/tailwind.config.js`（colors 增加 glass 组、shadows 增加 glass/glow 映射）

**Interfaces:**
- Consumes: Task 1 的 `--p-*`
- Produces（后续所有任务依赖）: semantic token `--bg-canvas/--bg-surface-1..3/--border-default/--border-strong/--ink-*/--accent-*/--hairline`（语义名不变，只换值）；新增 `--glass-bg/--glass-bg-strong/--glass-bg-fallback/--glass-border/--glass-highlight/--glass-blur`、`--gradient-brand/--gradient-brand-hover/--gradient-text/--shadow-glass/--shadow-glow-accent`。Tailwind 类：`bg-glass-bg`、`border-glass-border`、`shadow-glass`、`shadow-glow-accent`。

- [ ] **Step 1: 修改 `colors.css` 暗色块（`:root`）**

画布向设计稿 `#0A1225` 靠拢，semantic 全部改为引用 primitive（保持语义名不变，下游零感知）。替换暗色块顶部基础变量部分为：

```css
:root {
  /* === 暗色 (默认) === */
  --bg-canvas:        var(--p-navy-900);
  --bg-surface-1:     var(--p-navy-800);
  --bg-surface-2:     var(--p-navy-700);
  --bg-surface-3:     var(--p-navy-600);
  --bg-overlay:       rgba(10, 18, 37, 0.72);

  --ink-default:      var(--p-ink-light-1);
  --ink-muted:        var(--p-ink-light-2);
  --ink-faint:        var(--p-ink-light-3);
  --ink-inverse:      var(--p-navy-900);

  --accent-primary:   var(--p-violet-500);
  --accent-hover:     var(--p-violet-400);
  --accent-press:     var(--p-violet-600);
  --accent-secondary: var(--p-purple-500);
  --accent-warm:      255 138 76;
  --accent-cyan:      var(--p-cyan-500);
  --accent-cyan-hover:var(--p-cyan-400);
  --accent-cyan-press:var(--p-cyan-600);
  --accent-success:   var(--p-green-500);
  --accent-warning:   var(--p-amber-400);
  --accent-danger:    var(--p-red-400);
  --accent-info:      var(--p-blue-400);

  --hairline:         rgba(255, 255, 255, 0.08);
  --border-default:   31 58 101;
  --border-strong:    45 79 138;
  --border-accent:    rgba(91, 107, 245, 0.4);

  /* === 玻璃表面组（新增） === */
  --glass-bg:          rgba(255, 255, 255, 0.045);
  --glass-bg-strong:   rgba(255, 255, 255, 0.07);
  --glass-bg-fallback: #131C33;
  --glass-border:      rgba(255, 255, 255, 0.09);
  --glass-highlight:   rgba(255, 255, 255, 0.07);
  --glass-blur:        14px;

  /* === 品牌渐变组（扩展现有签名渐变） === */
  --gradient-brand:       linear-gradient(135deg, #5B6BF5 0%, #A155F7 100%);
  --gradient-brand-hover: linear-gradient(135deg, #6E7EFF 0%, #B266FF 100%);
  --gradient-text:        linear-gradient(120deg, #7C8CFF 10%, #B36BFF 60%, #67E8F9 105%);
  --shadow-glow-accent:   0 6px 24px rgba(120, 90, 250, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.25);
  --shadow-glass:         0 12px 32px rgba(3, 7, 20, 0.50);

  /* 渐变签名（mesh 保留现有定义不动） */
  --gradient-mesh-1:  radial-gradient(ellipse 80% 60% at 20% 0%,
                       rgba(91, 107, 245, 0.18) 0%, transparent 50%);
  --gradient-mesh-2:  radial-gradient(ellipse 70% 50% at 80% 100%,
                       rgba(161, 85, 247, 0.15) 0%, transparent 50%);
  --gradient-mesh-3:  radial-gradient(ellipse 60% 40% at 50% 50%,
                       rgba(91, 107, 245, 0.08) 0%, transparent 60%);
  --gradient-accent:  var(--gradient-brand);
  --gradient-accent-hover: var(--gradient-brand-hover);
}
```

注意：原暗色块的 `--gradient-accent: linear-gradient(...)` 两行删除，由上面 `var(--gradient-brand)` 引用替代，避免双份定义。

- [ ] **Step 2: 整块替换亮色块（`:root[data-theme="light"]`）为冷调灰白 + 玻璃亮色值**

```css
:root[data-theme="light"] {
  /* === 亮色：冷调灰白（玻璃质感配套，原米黄纸感废弃） === */
  --bg-canvas:        var(--p-gray-50);
  --bg-surface-1:     255 255 255;
  --bg-surface-2:     var(--p-gray-100);
  --bg-surface-3:     var(--p-gray-200);
  --bg-overlay:       rgba(246, 247, 251, 0.72);

  --ink-default:      var(--p-ink-dark-1);
  --ink-muted:        var(--p-ink-dark-2);
  --ink-faint:        var(--p-ink-dark-3);
  --ink-inverse:      var(--p-ink-light-1);

  --accent-primary:   var(--p-violet-500);
  --accent-hover:     var(--p-violet-600);
  --accent-press:     var(--p-violet-700);
  --accent-secondary: var(--p-purple-500);
  --accent-warm:      232 107 26;
  --accent-cyan:      var(--p-cyan-600);
  --accent-cyan-hover:14 116 144;
  --accent-cyan-press:21 94 117;
  --accent-success:   var(--p-green-600);
  --accent-warning:   var(--p-amber-600);
  --accent-danger:    var(--p-red-500);
  --accent-info:      var(--p-blue-600);

  --hairline:         rgba(13, 37, 61, 0.08);
  --border-default:   var(--p-gray-300);
  --border-strong:    var(--p-gray-400);
  --border-accent:    rgba(91, 107, 245, 0.3);

  /* === 玻璃表面组（亮色：白半透明 + 细灰描边） === */
  --glass-bg:          rgba(255, 255, 255, 0.65);
  --glass-bg-strong:   rgba(255, 255, 255, 0.85);
  --glass-bg-fallback: #FFFFFF;
  --glass-border:      rgba(13, 37, 61, 0.08);
  --glass-highlight:   rgba(255, 255, 255, 0.90);
  --glass-blur:        14px;

  /* === 品牌渐变组（亮色降档不透明度） === */
  --gradient-brand:       linear-gradient(135deg, #5B6BF5 0%, #A155F7 100%);
  --gradient-brand-hover: linear-gradient(135deg, #5158E8 0%, #9440E8 100%);
  --gradient-text:        linear-gradient(120deg, #4F5BE8 10%, #8B3EE8 60%, #0891B2 105%);
  --shadow-glow-accent:   0 6px 20px rgba(91, 107, 245, 0.28);
  --shadow-glass:         0 12px 32px rgba(13, 37, 61, 0.10);

  /* mesh 亮色降档（保留现有定义） */
  --gradient-mesh-1:  radial-gradient(ellipse 80% 60% at 20% 0%,
                       rgba(91, 107, 245, 0.10) 0%, transparent 50%);
  --gradient-mesh-2:  radial-gradient(ellipse 70% 50% at 80% 100%,
                       rgba(161, 85, 247, 0.08) 0%, transparent 50%);
  --gradient-mesh-3:  radial-gradient(ellipse 60% 40% at 50% 50%,
                       rgba(91, 107, 245, 0.04) 0%, transparent 60%);
  --gradient-accent:  var(--gradient-brand);
  --gradient-accent-hover: var(--gradient-brand-hover);
}
```

- [ ] **Step 3: `shadows.css` 追加（若 Step 1/2 已含 --shadow-glass/--shadow-glow-accent 则此处跳过，仅在 shadows.css 追加 light 覆盖注释引用）**

本任务阴影统一放在 colors.css 渐变组旁（与设计文档 §5.1 一致），shadows.css 无需改动。**本步骤为空操作，仅确认不重复定义。**

- [ ] **Step 4: `tailwind.config.js` 映射**

在 `theme.extend.colors` 中追加（与现有 `canvas/surface/ink` 平级）：

```js
        glass: {
          bg: 'var(--glass-bg)',
          'bg-strong': 'var(--glass-bg-strong)',
          border: 'var(--glass-border)',
        },
```

在 `theme.extend.boxShadow` 中追加：

```js
        glass: 'var(--shadow-glass)',
        'glow-accent': 'var(--shadow-glow-accent)',
```

- [ ] **Step 5: 验证：构建 + 亮暗切换**

Run: `cd frontend && npm run build`
Expected: 成功。
Run: `python dev-services.py status`（服务应已运行；未运行则 `python dev-services.py start`），浏览器打开 `/dev/components`，切换亮/暗主题：
Expected: 暗色画布变为 `#0A1225` 深空蓝；亮色从米黄变为冷灰白；全站无大面积样式错乱（semantic 语义名未变）。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/styles/tokens/colors.css frontend/tailwind.config.js
git commit -m "feat(design-system): 语义 token 升级——亮色冷调/玻璃组/品牌渐变组 + Tailwind 映射"
```

---

### Task 3: 字体修复（index.html 清理 + Logo 渐变字）

**Files:**
- Modify: `frontend/index.html:10-22`（Google Fonts 外链区）
- Modify: `frontend/src/index.css`（删除 Pacifico fallback 块）

- [ ] **Step 1: 清理 `index.html` 字体外链**

- 删除 HarmonyOS Sans SC 的 `<link>`（该字体不在 Google Fonts，实际 404）；
- 删除 Noto Serif SC 的 `<link>`（先全局搜索 `font-serif` 确认无业务使用；`--font-serif` token 定义保留）；
- 删除 Pacifico 的 `<link>`；
- 保留 Geist + Geist Mono 的 `<link>`；
- 对每个保留/删除的 link，确认对应 `preconnect` 行仍成对合理。

- [ ] **Step 2: 删除 `src/index.css` 中的 Pacifico fallback 块**

删除以下块（约 44-49 行）：

```css
/* Pacifico 字体 fallback (当 Google Fonts 不可用时) */
.font-\[Pacifico\] {
  font-family: 'Pacifico', 'Microsoft YaHei', 'PingFang SC', sans-serif;
```

（连同闭合大括号整体删除）

- [ ] **Step 3: 全局搜索残留引用**

Run: `cd frontend && grep -rn "Pacifico\|HarmonyOS\|Noto Serif" src/ index.html`
Expected: `src/` 中无 Pacifico 类使用；`index.html` 无三个失效外链。若 `src/` 中仍有 `font-['Pacifico']` 使用（Header.tsx:31 将在 Task 13 改造，其余位置此时先替换为 `font-extrabold`），逐处替换。

- [ ] **Step 4: 验证构建**

Run: `cd frontend && npm run build`
Expected: 成功。

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html frontend/src/index.css
git commit -m "fix(design-system): 清理失效字体外链（HarmonyOS 404/Pacifico/Noto Serif），Logo 改用系统字体栈"
```

---

### Task 4: 玻璃工具类 `styles/glass.css`

**Files:**
- Create: `frontend/src/styles/glass.css`
- Modify: `frontend/src/index.css:1`（追加 @import）

**Interfaces:**
- Consumes: Task 2 的玻璃组/渐变组 token、`--duration-fast`/`--ease-stripe`（motion token，已存在）
- Produces（后续所有页面/组件任务依赖）: 类 `.glass-card`、`.glass-panel`、`.gradient-text`、`.gradient-border`、`.hover-lift`、`.btn-primary`；tint 类在 Task 10 提供。

- [ ] **Step 1: 创建 `glass.css`**

```css
/* ============================================================
 * 玻璃光晕 · 工具类词汇表
 * 设计规范见 openspec/changes/glass-glow-redesign/design.md §5.4
 * 只引用 semantic token，禁止写死色值
 * ============================================================ */

/* 玻璃卡片：半透明底 + 细描边 + 模糊 + 悬浮阴影 + 顶部内高光 */
.glass-card {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  box-shadow: var(--shadow-glass), inset 0 1px 0 var(--glass-highlight);
}
/* 不支持 backdrop-filter 时的实色降级（web 端兜底，小程序端同思路） */
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .glass-card { background: var(--glass-bg-fallback); }
}

/* 玻璃面板：比卡片更强的底色（导航/抽屉/弹层用） */
.glass-panel {
  background: var(--glass-bg-strong);
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(calc(var(--glass-blur) * 1.3));
  -webkit-backdrop-filter: blur(calc(var(--glass-blur) * 1.3));
  box-shadow: var(--shadow-glass), inset 0 1px 0 var(--glass-highlight);
}
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .glass-panel { background: var(--glass-bg-fallback); }
}

/* 品牌渐变文字 */
.gradient-text {
  background-image: var(--gradient-text);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

/* 品牌渐变主按钮底（供 Button default variant 使用） */
.btn-primary {
  background-image: var(--gradient-brand);
  color: #fff;
  box-shadow: 0 4px 18px rgba(120, 90, 250, 0.35);
}
.btn-primary:hover {
  background-image: var(--gradient-brand-hover);
}

/* 渐变描边（双背景法：内容底 + 渐变边）。用法：元素本身 border transparent */
.gradient-border {
  border: 1px solid transparent;
  background:
    linear-gradient(var(--bg-surface-1), var(--bg-surface-1)) padding-box,
    var(--gradient-brand) border-box;
}

/* 悬浮抬升：hover 上移 4px + 渐变描边 + 发光阴影 */
.hover-lift {
  transition: transform var(--duration-fast, 150ms) var(--ease-stripe, ease-out),
              box-shadow var(--duration-fast, 150ms) var(--ease-stripe, ease-out),
              border-color var(--duration-fast, 150ms) var(--ease-stripe, ease-out);
}
.hover-lift:hover {
  transform: translateY(-4px);
  border-color: var(--border-accent);
  box-shadow: var(--shadow-glow-accent), inset 0 1px 0 var(--glass-highlight);
}
@media (prefers-reduced-motion: reduce) {
  .hover-lift:hover { transform: none; }
}
```

- [ ] **Step 2: 在 `src/index.css` 顶部注册**

在 `@import './styles/backgrounds.css';` 之后加一行：

```css
@import './styles/glass.css';
```

- [ ] **Step 3: 验证**

Run: `cd frontend && npm run build`
Expected: 成功。浏览器 `/dev/components` 临时给任一元素加 `glass-card` 类目视确认（Task 5 会正式加演示区）。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/styles/glass.css frontend/src/index.css
git commit -m "feat(design-system): 新增玻璃工具类词汇表 glass.css"
```

---

### Task 5: `/dev/components` 验收页更新

**Files:**
- Modify: `frontend/src/pages/DevComponentsPage.tsx`

- [ ] **Step 1: 追加「玻璃系统」演示区**

在现有色卡区之后新增一个 section：8 个 `glass-card` 小卡（其中 2 个改 `glass-panel`）、一个 `.gradient-text` 大标题示例、一个 `.gradient-border` 胶囊、一个 `.hover-lift + glass-card` 卡片（演示悬浮抬升）。参照文件内现有 section 的 JSX 风格编写（保持 token 色卡写法，用 `var(--glass-*)` 展示）。

- [ ] **Step 2: 浏览器走查**

Run: `python dev-services.py status`，访问 `http://localhost:<前端端口>/dev/components`
Expected: 亮/暗两种主题下玻璃卡、渐变文字、悬浮抬升均正常；不支持模糊的场景已由 fallback 兜底。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/DevComponentsPage.tsx
git commit -m "feat(design-system): /dev/components 增加玻璃系统验收区"
```

---

## 阶段② 基础组件升级

### Task 6: Button 组件（渐变主按钮 / 玻璃次按钮 / 幽灵）

**Files:**
- Modify: `frontend/src/components/ui/Button.tsx:6-30`（buttonVariants 的 cva 定义）

**Interfaces:**
- Consumes: Task 4 的 `.btn-primary`、`.glass-panel`
- Produces: Button variant 语义不变（default/destructive/outline/secondary/ghost/link），全站调用方零改动

- [ ] **Step 1: 替换 variants 类串**

```ts
const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "btn-primary hover:text-white",
        destructive: "bg-accent-danger text-white hover:bg-accent-danger/90",
        outline:
          "border border-glass-border bg-glass-bg hover:bg-glass-bg-strong hover:border-accent text-ink",
        secondary: "bg-glass-bg text-ink hover:bg-glass-bg-strong border border-glass-border",
        ghost: "hover:bg-glass-bg hover:text-ink",
        link: "text-accent underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-lg px-3",
        lg: "h-11 rounded-lg px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)
```

- [ ] **Step 2: 验证**

Run: `cd frontend && npm run build && npx tsc --noEmit`
Expected: 均通过。浏览器走查 `/dev/components` 与首页按钮：主按钮呈紫蓝渐变、次按钮玻璃半透明、暗/亮主题均正常。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/Button.tsx
git commit -m "feat(ui): Button 升级玻璃光晕视觉（渐变主按钮/玻璃次按钮）"
```

---

### Task 7: Card 组件玻璃化

**Files:**
- Modify: `frontend/src/components/ui/Card.tsx:4-13`

**Interfaces:**
- Produces: Card 基类默认玻璃化；新增 `variant?: "glass" | "solid"` prop（默认 glass）。全站使用处无需改动即获得新视觉；个别需要实底的调用方可传 `variant="solid"`。

- [ ] **Step 1: 改造 Card**

```tsx
import * as React from "react"
import { cn } from "@/lib/cn"

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** glass=玻璃拟态（默认），solid=实色表面（兼容个别需要实底的场景） */
  variant?: "glass" | "solid"
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = "glass", ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-xl text-ink",
        variant === "glass" ? "glass-card" : "border border-border bg-surface-1 shadow-sm",
        className
      )}
      {...props}
    />
  )
)
Card.displayName = "Card"
```

（CardHeader/CardTitle/CardDescription/CardContent/CardFooter 不动。）

- [ ] **Step 2: 验证**

Run: `cd frontend && npm run build && npx tsc --noEmit`
Expected: 通过。走查首页/市场/课程页卡片：玻璃化生效、文字对比度正常；Admin 页面如有个别卡片观感异常属预期（阶段⑥统一处理），不阻塞。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/Card.tsx
git commit -m "feat(ui): Card 玻璃化并新增 solid 变体"
```

---

### Task 8: Input / Textarea / Select 玻璃化

**Files:**
- Modify: `frontend/src/components/ui/Input.tsx`
- Modify: `frontend/src/components/ui/Select.tsx`（触发器与内容层类串）

- [ ] **Step 1: Input 基类替换**

将 Input 基类中的表面类统一为（保持原有 focus ring 类不变）：

```
"bg-glass-bg border border-glass-border placeholder:text-ink-faint"
```

（即替换原来的 `bg-surface-*`/`border-border` 相应片段；focus 态统一为 `focus-visible:ring-2 focus-visible:ring-accent` 或文件既有的 focus 约定。）

- [ ] **Step 2: Select 触发器同样替换为玻璃类串**

SelectContent 弹层类串替换为 `"glass-panel rounded-lg"`（保留原有定位/popover 类）。

- [ ] **Step 3: 验证**

Run: `cd frontend && npm run build`
Expected: 通过。走查登录表单、搜索框、Admin 任一表单：输入框玻璃化、亮/暗正常。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui/Input.tsx frontend/src/components/ui/Select.tsx
git commit -m "feat(ui): Input/Select 玻璃化"
```

---

### Task 9: 弹层组件统一（Dialog/ConfirmDialog/DropdownMenu/Popover/Tooltip/Toast）

**Files:**
- Modify: `frontend/src/components/ui/Dialog.tsx`（Overlay + Content 类串）
- Modify: `frontend/src/components/ui/ConfirmDialog.tsx`（若复用 Dialog 则无需改）
- Modify: `frontend/src/components/ui/DropdownMenu.tsx`（Content 类串）
- Modify: `frontend/src/components/ui/Popover.tsx`（Content 类串）
- Modify: `frontend/src/components/ui/Tooltip.tsx`（Content 类串）
- Modify: `frontend/src/components/ui/Toast.tsx`（viewport/条目类串）

- [ ] **Step 1: 统一替换规则（逐文件应用）**

| 位置 | 原类串片段 | 替换为 |
|---|---|---|
| DialogOverlay | `bg-black/80` 类片段 | `bg-canvas/60 backdrop-blur-sm` |
| DialogContent | `bg-surface-1 border border-border shadow-...` | `glass-panel rounded-2xl` |
| DropdownMenu/Popover Content | `bg-surface-1 border border-border ...` | `glass-panel rounded-xl` |
| Tooltip Content | `bg-surface-2 ...` | `bg-glass-bg-strong border border-glass-border backdrop-blur-md rounded-lg` |
| Toast 条目 | `bg-surface-1 border ...` | `glass-panel rounded-xl` |

（各文件保留原有动画/定位类，仅替换表面与边框片段。）

- [ ] **Step 2: 验证**

Run: `cd frontend && npm run build`
Expected: 通过。手动触发验证：登录弹框（LoginModal）、联系我们（ContactModal）、工具卡右键/下拉、Toast 通知均为玻璃面板且遮罩模糊。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/Dialog.tsx frontend/src/components/ui/DropdownMenu.tsx frontend/src/components/ui/Popover.tsx frontend/src/components/ui/Tooltip.tsx frontend/src/components/ui/Toast.tsx
git commit -m "feat(ui): 弹层组件统一玻璃面板视觉"
```

---

### Task 10: 反馈/杂项组件 + tint 图标体系

**Files:**
- Modify: `frontend/src/components/ui/Badge.tsx`、`Skeleton.tsx`、`Tabs.tsx`、`Switch.tsx`、`Checkbox.tsx`、`Separator.tsx`、`Avatar.tsx`、`Slider.tsx`（类串微调）
- Modify: `frontend/src/styles/glass.css`（追加 tint 类）
- Create: `frontend/src/utils/iconTint.ts` + `frontend/src/utils/iconTint.test.ts`
- Modify: `frontend/src/components/ToolCard/ToolCard.tsx:33-38`（图标块）
- Modify: `frontend/tailwind.config.js:7-13`（safelist 替换）
- Modify: `frontend/src/pages/DevComponentsPage.tsx`（tint 演示）

**Interfaces:**
- Produces: `iconTintClass(iconColor?: string): string`（输入后端 `bg-blue-500` 式类名，输出 `tint tint-blue`；未知值回退 `tint tint-violet`）；类 `.tint .tint-{blue|violet|emerald|indigo|orange|red|purple|cyan}`

- [ ] **Step 1: 写失败测试 `frontend/src/utils/iconTint.test.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { iconTintClass } from './iconTint';

describe('iconTintClass', () => {
  it('把后端 bg-<name>-<shade> 类名映射为 tint 类', () => {
    expect(iconTintClass('bg-blue-500')).toBe('tint tint-blue');
    expect(iconTintClass('bg-violet-500')).toBe('tint tint-violet');
    expect(iconTintClass('bg-emerald-500')).toBe('tint tint-emerald');
    expect(iconTintClass('bg-red-600')).toBe('tint tint-red');
  });
  it('未知颜色回退 violet', () => {
    expect(iconTintClass('bg-chartreuse-900')).toBe('tint tint-violet');
  });
  it('空值回退 violet', () => {
    expect(iconTintClass()).toBe('tint tint-violet');
    expect(iconTintClass('')).toBe('tint tint-violet');
  });
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd frontend && npx vitest run src/utils/iconTint.test.ts`
Expected: FAIL（`iconTint` 模块不存在）

- [ ] **Step 3: 实现 `iconTint.ts`**

```ts
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
```

- [ ] **Step 4: 运行确认通过**

Run: `cd frontend && npx vitest run src/utils/iconTint.test.ts`
Expected: PASS（5 例全绿）

- [ ] **Step 5: `glass.css` 追加 tint 类**

```css
/* ============================================================
 * Tint 图标色板：低饱和色底 + 同色描边 + 同色图标（替换饱和色块）
 * ============================================================ */
.tint {
  display: flex;
  align-items: center;
  justify-content: center;
}
.tint-blue    { color: #60A5FA; background: rgba(59, 130, 246, 0.14);  border: 1px solid rgba(59, 130, 246, 0.28); }
.tint-violet  { color: #8B9BFF; background: rgba(101, 116, 255, 0.14); border: 1px solid rgba(101, 116, 255, 0.28); }
.tint-emerald { color: #34D399; background: rgba(52, 211, 153, 0.12);  border: 1px solid rgba(52, 211, 153, 0.28); }
.tint-indigo  { color: #818CF8; background: rgba(99, 102, 241, 0.14);  border: 1px solid rgba(99, 102, 241, 0.28); }
.tint-orange  { color: #FB923C; background: rgba(251, 146, 60, 0.13);  border: 1px solid rgba(251, 146, 60, 0.28); }
.tint-red     { color: #F87171; background: rgba(248, 113, 113, 0.12); border: 1px solid rgba(248, 113, 113, 0.28); }
.tint-purple  { color: #C084FC; background: rgba(192, 132, 252, 0.13); border: 1px solid rgba(192, 132, 252, 0.28); }
.tint-cyan    { color: #22D3EE; background: rgba(34, 211, 238, 0.12);  border: 1px solid rgba(34, 211, 238, 0.28); }
```

- [ ] **Step 6: ToolCard 图标块改造**

`ToolCard.tsx` 顶部加 `import { iconTintClass } from '../../utils/iconTint';`，图标容器（33-38 行）替换为：

```tsx
      <div className={`w-12 h-12 rounded-xl mb-4 ${iconTintClass(iconColor)}`}>
        {custom_icon_url ? (
          <img src={custom_icon_url} alt={title} className="w-6 h-6 object-contain" />
        ) : (
          <Icon className="w-6 h-6" />
        )}
      </div>
```

同时外层 Card 类串（25 行）替换为：

```tsx
      className="p-6 hover-lift cursor-pointer relative"
```

（`hover:border-accent transition-all` 由 `.hover-lift` 承担；Card 本身已在 Task 7 玻璃化。）

- [ ] **Step 7: tailwind safelist 替换**

`tailwind.config.js` safelist 数组替换为（保留注释说明来源）：

```js
  safelist: [
    // tint 图标色板类（styles/glass.css 定义）；iconColor 由后端 tools_data.py 下发，
    // 经 utils/iconTint.ts 映射，这里 safelist 供 JIT 保留
    // 注意：tint-* 为普通 CSS 类（非 Tailwind 工具类），无需 safelist；
    // 此处保留空数组占位说明。若后续新增 Tailwind 动态类再加。
  ],
```

（说明：`tint-*` 是自定义 CSS 类不受 JIT 控制，原 safelist 的 `bg-blue-500` 等 8 个类随之作废，必须清空，否则 CSS 里残留废弃饱和色块类。）

- [ ] **Step 8: 全局排查其他 `iconColor` 消费点**

Run: `cd frontend && grep -rn "iconColor" src/ --include="*.tsx" | grep -v ToolCard`
Expected: 若有其他组件直接把 `iconColor` 当 Tailwind 类拼接（如列表页小卡），同样改用 `iconTintClass()`；无则跳过。

- [ ] **Step 9: Badge/Skeleton/Tabs/Switch 类串微调**

- Badge：底色改 `bg-glass-bg` + `border border-glass-border`（各 variant 的文字色保留）；
- Skeleton：底色 `bg-glass-bg`（保留 animate-pulse）；
- Tabs：激活触发器 `text-white bg-[image:var(--gradient-brand)] shadow-[0_4px_14px_rgba(120,90,250,0.35)]`，非激活 `text-ink-muted hover:text-ink hover:bg-glass-bg`，整体加 `rounded-full p-1 bg-glass-bg border border-glass-border`（玻璃胶囊组）；
- Switch：轨道选中态 `bg-[image:var(--gradient-brand)]`（Tailwind 任意值 `bg-[image:...]` 对 gradient 变量适用）；
- Checkbox：选中态 `bg-[image:var(--gradient-brand)] border-transparent`；
- Separator：`bg-glass-border`；
- Avatar：fallback 底 `bg-glass-bg-strong border border-glass-border`；
- Slider：range 选中轨道与滑块用 `bg-accent`（保持现有 token 引用，宽度/圆角不动）。

- [ ] **Step 10: 验证**

Run: `cd frontend && npx vitest run && npm run build`
Expected: 单测全绿、构建成功。浏览器走查 `/dev/components`（tint 演示已加）与首页工具卡：饱和色块消失、tint 图标 + hover 抬升生效。

- [ ] **Step 11: Commit**

```bash
git add frontend/src/utils/iconTint.ts frontend/src/utils/iconTint.test.ts frontend/src/styles/glass.css frontend/src/components/ToolCard/ToolCard.tsx frontend/tailwind.config.js frontend/src/components/ui/ frontend/src/pages/DevComponentsPage.tsx
git commit -m "feat(ui): tint 图标体系替换饱和色块 + 反馈组件玻璃化（含单测）"
```

---

## 阶段③ Web 核心页面

### Task 11: Header 玻璃化 + 渐变 Logo + 导航链接 + 移动端收纳

**Files:**
- Modify: `frontend/src/components/Header/Header.tsx`（整体重构）
- Modify: `frontend/src/components/Header/SearchBar.tsx`（玻璃胶囊 + 宽度响应式）
- Delete: `frontend/src/components/Header/Navigation.tsx`（死代码，重写内联进 Header）

**Interfaces:**
- Consumes: Task 6 Button、Task 4 工具类、Task 2 token
- Produces: 新增导航链接组（首页/工具市场/课程/技术内容），active 判定用 `useLocation().pathname` 前缀匹配；Header 导出签名不变（Layout 调用方零改动）

- [ ] **Step 1: 重写 Header 结构**

要点（保持现有 props/依赖不变）：

1. `<header>` 类串改为：`sticky top-0 z-40 glass-panel border-x-0 border-t-0 rounded-none`（玻璃悬浮条，去掉 `bg-surface-1 border-b`）；
2. Logo：删除 `font-['Pacifico']`，改为 `<Link to="/" className="text-2xl font-extrabold tracking-tight gradient-text">{t.common.logo}</Link>`；
3. 新增桌面导航（`hidden md:flex`，放在 Logo 右侧 `space-x-1`）：

```tsx
const NAV_ITEMS = [
  { to: '/', label: t.nav.home, match: (p: string) => p === '/' },
  { to: '/marketplace', label: t.nav.marketplace, match: (p: string) => p.startsWith('/marketplace') },
  { to: '/courses', label: t.nav.courses, match: (p: string) => p.startsWith('/courses') },
  { to: '/tech-contents', label: t.nav.techContents, match: (p: string) => p.startsWith('/tech-contents') },
];
```

每个 item 渲染为 `<Link>`：非激活 `text-ink-muted hover:text-ink px-3 py-2 rounded-lg hover:bg-glass-bg`；激活 `text-ink px-3 py-2 rounded-lg bg-glass-bg` 且下方加 2px 渐变下划线（`<span className="block h-0.5 rounded-full bg-[image:var(--gradient-brand)]" />`）。`t.nav.*` 缺失的 key 在 i18n 资源补齐（见 Step 4）。
4. 右侧按钮组：Admin/联系我们/语言/主题改用 `variant="ghost"` + 图标化（语言与主题已是图标按钮，改为 ghost 玻璃）；`LoginButton` 不动；
5. 移动端收纳（`md:hidden`）：显示 Logo + 搜索图标按钮（点击派发 `window.dispatchEvent(new CustomEvent('open-command-palette'))`，打开 Task 12 面板）+ 头像/LoginButton；完整移动端导航（底部 Tab 栏等）属阶段⑦，本任务只保证 375px 视口 Header 不溢出；
6. `useLocation` 来自 `react-router-dom`。

- [ ] **Step 2: SearchBar 玻璃胶囊**

类串改为 `w-full md:w-64` 外层 + 内层 `bg-glass-bg border border-glass-border rounded-full focus-within:border-accent`；原有 onChange/onSearch 逻辑不动。

- [ ] **Step 3: 删除死代码 `Navigation.tsx`**

```bash
git rm frontend/src/components/Header/Navigation.tsx
```

先 `grep -rn "Header/Navigation" frontend/src` 确认无引用（调研确认是死代码）。

- [ ] **Step 4: i18n key 补齐**

在 i18n 资源（`frontend/src/i18n/` 下 zh/en 两个资源文件，结构与 `t.nav.*` 现有用法一致）追加：
- `nav.home`：zh `首页` / en `Home`
- `nav.courses`：zh `课程` / en `Courses`
- `nav.techContents`：zh `技术内容` / en `Tech Content`

- [ ] **Step 5: 验证**

Run: `cd frontend && npm run build && npx tsc --noEmit`
Expected: 通过。走查：玻璃 Header、渐变 Logo、当前页渐变下划线、375px 视口下 Header 不溢出（仅 Logo+搜索图标+头像）。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Header/Header.tsx frontend/src/components/Header/SearchBar.tsx frontend/src/i18n/
git rm frontend/src/components/Header/Navigation.tsx
git commit -m "feat(header): 玻璃悬浮 Header + 渐变 Logo + 导航链接 + 移动端收纳"
```

---

### Task 12: ⌘K 命令面板（TDD）

**Files:**
- Create: `frontend/src/lib/commandPalette.ts` + `frontend/src/lib/commandPalette.test.ts`
- Create: `frontend/src/components/Common/CommandPalette.tsx`
- Modify: `frontend/src/components/Layout/Layout.tsx`（挂载面板 + 全局快捷键）
- Modify: `frontend/src/components/Header/Header.tsx`（桌面搜索框与移动搜索图标改为打开面板的入口之一）

**Interfaces:**
- Produces:
  - `lib/commandPalette.ts`：`interface CommandItem { id: string; label: string; hint?: string; group: '工具' | '页面'; route: string; toolId?: string }`（`toolId` 仅工具条目有）；`buildCommandItems(tools: Tool[]): CommandItem[]`；`filterCommands(items: CommandItem[], query: string): CommandItem[]`（大小写不敏感、label/hint/route 包含匹配、空 query 返回全部）
  - 工具跳转约定与 `App.tsx` 的 `handleToolClick`（App.tsx:236-246）一致：`navigate('/workspace', { state: { openToolId: toolId } })`
  - `CommandPalette` 组件：无 props（自管理 open 态），暴露全局事件 `window.dispatchEvent(new CustomEvent('open-command-palette'))` 作为外部打开约定（Header 移动端按钮、Hero 搜索胶囊共用）
  - 全局快捷键：`Cmd/Ctrl + K`

- [ ] **Step 1: 写失败测试 `commandPalette.test.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { buildCommandItems, filterCommands, type CommandItem } from './commandPalette';

const tools = [
  { id: 'json-formatter', name: 'JSON 格式化', description: '校验、压缩', route: '/tools/json-formatter' },
  { id: 'ocr', name: 'OCR 文字识别', description: '图片转文字', route: '/tools/ocr' },
] as any[];

const PAGES: CommandItem[] = [
  { id: 'page-marketplace', label: '工具市场', group: '页面', route: '/marketplace' },
  { id: 'page-courses', label: '课程', group: '页面', route: '/courses' },
];

describe('buildCommandItems', () => {
  it('工具与静态页面合并，工具在前', () => {
    const items = [...buildCommandItems(tools), ...PAGES];
    expect(items[0].label).toBe('JSON 格式化');
    expect(items.at(-1)!.group).toBe('页面');
  });
});

describe('filterCommands', () => {
  const items = [...buildCommandItems(tools), ...PAGES];
  it('空 query 返回全部', () => {
    expect(filterCommands(items, '')).toHaveLength(items.length);
  });
  it('大小写不敏感匹配 label 与 route', () => {
    expect(filterCommands(items, 'json')).toHaveLength(1);
    expect(filterCommands(items, 'OCR')).toHaveLength(1);
  });
  it('无匹配返回空数组', () => {
    expect(filterCommands(items, '不存在的工具xyz')).toHaveLength(0);
  });
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd frontend && npx vitest run src/lib/commandPalette.test.ts`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现 `commandPalette.ts`**

```ts
import type { Tool } from '../types';

/** 命令面板条目：工具 + 静态页面 */
export interface CommandItem {
  id: string;
  label: string;
  hint?: string;
  group: '工具' | '页面';
  route: string;
}

/** 面板固定收录的静态页面入口 */
export const PAGE_ITEMS: CommandItem[] = [
  { id: 'page-home', label: '首页', group: '页面', route: '/' },
  { id: 'page-marketplace', label: '工具市场', group: '页面', route: '/marketplace' },
  { id: 'page-courses', label: '课程', group: '页面', route: '/courses' },
  { id: 'page-tech-contents', label: '技术内容', group: '页面', route: '/tech-contents' },
  { id: 'page-account', label: '账户设置', group: '页面', route: '/account-settings' },
];

/** 后端工具列表 → 面板条目（description 作为 hint；toolId 供工作区 state 跳转） */
export function buildCommandItems(tools: Tool[]): CommandItem[] {
  return tools.map((tool) => ({
    id: `tool-${tool.id}`,
    label: tool.name,
    hint: tool.description,
    group: '工具' as const,
    route: '/workspace',
    toolId: tool.id,
  }));
}

/** 过滤：大小写不敏感，匹配 label/hint/route；空串返回全部 */
export function filterCommands(items: CommandItem[], query: string): CommandItem[] {
  const q = query.trim().toLowerCase();
  if (!q) return items;
  return items.filter(
    (item) =>
      item.label.toLowerCase().includes(q) ||
      (item.hint ?? '').toLowerCase().includes(q) ||
      item.route.toLowerCase().includes(q)
  );
}
```

- [ ] **Step 4: 运行确认通过**

Run: `cd frontend && npx vitest run src/lib/commandPalette.test.ts`
Expected: PASS

- [ ] **Step 5: 实现 `CommandPalette.tsx`**

基于现有 Radix Dialog（`components/ui/Dialog.tsx` 的 Dialog/DialogContent）封装，核心逻辑：

```tsx
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { Dialog, DialogContent } from '../ui/Dialog';
import { fetchTools } from '../../services/api';
import { buildCommandItems, filterCommands, PAGE_ITEMS, type CommandItem } from '../../lib/commandPalette';

/**
 * 全局 ⌘K 命令面板：搜索工具与页面并跳转。
 * 打开方式：Cmd/Ctrl+K 或 window 事件 'open-command-palette'。
 */
export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [tools, setTools] = useState<CommandItem[]>([]);
  const navigate = useNavigate();

  // 工具列表懒加载：首次打开面板时拉取一次
  useEffect(() => {
    if (!open || tools.length > 0) return;
    fetchTools('pc').then((data) => setTools(buildCommandItems(data))).catch(() => {/* 拉取失败时仅显示页面入口 */});
  }, [open, tools.length]);

  // 全局快捷键与外部打开事件
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    const onOpen = () => setOpen(true);
    window.addEventListener('keydown', onKey);
    window.addEventListener('open-command-palette', onOpen);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('open-command-palette', onOpen);
    };
  }, []);

  const results = useMemo(
    () => filterCommands([...tools, ...PAGE_ITEMS], query),
    [tools, query]
  );

  const go = (item: CommandItem) => {
    setOpen(false);
    setQuery('');
    // 工具走工作区 state 跳转（与 App.tsx handleToolClick 约定一致），页面走路由
    if (item.toolId) {
      navigate('/workspace', { state: { openToolId: item.toolId } });
    } else {
      navigate(item.route);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="glass-panel rounded-2xl max-w-lg p-0 top-[20%] translate-y-0">
        <div className="flex items-center gap-3 border-b border-glass-border px-4 py-3">
          <Search className="w-4 h-4 text-ink-faint" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索工具、页面…"
            className="w-full bg-transparent text-sm outline-none placeholder:text-ink-faint"
          />
          <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-glass-bg border border-glass-border text-ink-faint">Esc</kbd>
        </div>
        <ul className="max-h-80 overflow-y-auto p-2">
          {results.length === 0 && (
            <li className="px-3 py-6 text-center text-sm text-ink-faint">无匹配结果</li>
          )}
          {results.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => go(item)}
                className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-glass-bg-strong transition-colors"
              >
                <span className="text-xs text-ink-faint mr-2">{item.group}</span>
                <span className="text-sm text-ink">{item.label}</span>
                {item.hint && <span className="block text-xs text-ink-faint truncate">{item.hint}</span>}
              </button>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  );
}
```

注意：`fetchTools` 以 `services/api.ts` 实际导出签名为准；Dialog 若为 `open/onOpenChange` 标准封装则直接使用（见 `components/ui/Dialog.tsx` 实际 API）。

- [ ] **Step 6: 挂载到 Layout**

`Layout.tsx` 在 `<LoginModal />` 同级渲染 `<CommandPalette />`（或紧邻 `<Outlet/>` 的容器内），import 路径 `../Common/CommandPalette`。

- [ ] **Step 7: 验证**

Run: `cd frontend && npx vitest run src/lib/commandPalette.test.ts && npm run build`
Expected: 单测通过、构建成功。浏览器：`Cmd/Ctrl+K` 唤起面板、搜索 "json" 出现工具并回车跳转、Esc 关闭。

- [ ] **Step 8: Commit**

```bash
git add frontend/src/lib/commandPalette.ts frontend/src/lib/commandPalette.test.ts frontend/src/components/Common/CommandPalette.tsx frontend/src/components/Layout/Layout.tsx frontend/src/components/Header/Header.tsx
git commit -m "feat(common): 新增 ⌘K 全局命令面板（搜索工具/页面并跳转，含单测）"
```

---

### Task 13: Footer 三栏改版

**Files:**
- Modify: `frontend/src/components/Footer/Footer.tsx`

- [ ] **Step 1: 重写为三栏结构**

保持组件签名不变，结构改为：

```
<footer> （border-t border-glass-border bg-surface-1/50 backdrop-blur-md）
  container mx-auto px-6 py-10
  ├─ 栏1（品牌）：渐变 Logo（gradient-text font-extrabold text-xl）+ 一句话简介（text-ink-muted text-sm）
  ├─ 栏2（页面导航）：首页 / 工具市场 / 课程 / 技术内容（复用 Task 11 的 NAV_ITEMS 结构，Link + text-ink-muted hover:text-ink）
  └─ 栏3（说明）：版权 © 2026 Toolbox + "20+ 开发者工具 · 数据云端同步"
  移动端：三栏改 grid-cols-1 md:grid-cols-3，间距 space-y-6 md:space-y-0
```

- [ ] **Step 2: 验证**

Run: `cd frontend && npm run build`
Expected: 通过。走查亮/暗 × 桌面/移动视口 Footer 排版。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Footer/Footer.tsx
git commit -m "feat(footer): 三栏化改版（品牌/导航/说明）"
```

---

### Task 14: 首页 Hero 大标题区 + CategoryTabs 玻璃胶囊 + ToolGrid

**Files:**
- Modify: `frontend/src/components/Hero/Hero.tsx`（新增大标题区）
- Modify: `frontend/src/components/Hero/CategoryTabs.tsx`（玻璃胶囊）
- Modify: `frontend/src/components/Hero/ToolGrid.tsx`（断点与间距）
- Modify: `frontend/src/i18n/`（新增 home.* key）

**Interfaces:**
- Consumes: `.gradient-text`、`open-command-palette` 全局事件（Task 12）
- Produces: i18n key `home.heroBadge / home.heroTitle / home.heroTitleAccent / home.heroSubtitle / home.heroCta`

- [ ] **Step 1: Hero 增加大标题区（CategoryTabs 之前）**

```tsx
export default function Hero({ activeCategory, onCategoryChange, tools, onToolClick, categories }: HeroProps) {
  const { t } = useI18n();

  return (
    <section className="mb-16">
      {/* 大标题主视觉 */}
      <div className="text-center pt-10 pb-10">
        <span className="inline-block text-xs px-3 py-1 rounded-full mb-5 text-accent-primary bg-glass-bg border border-glass-border">
          {t.home.heroBadge}
        </span>
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-ink mb-4">
          {t.home.heroTitle}
          <span className="gradient-text">{t.home.heroTitleAccent}</span>
        </h1>
        <p className="text-ink-muted text-base mb-8">{t.home.heroSubtitle}</p>
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={() => window.dispatchEvent(new CustomEvent('open-command-palette'))}
            className="btn-primary rounded-full px-6 h-11 text-sm font-medium inline-flex items-center gap-2"
          >
            {t.home.heroCta}
          </button>
        </div>
      </div>

      <div className="flex items-center justify-center mb-8">
        <CategoryTabs ... />  {/* 原有 props 不变 */}
        <DeployTimeIndicator />
      </div>

      <ToolGrid tools={tools} onToolClick={onToolClick} />
    </section>
  );
}
```

i18n 追加（zh / en）：
- `home.heroBadge`：`✦ 全新升级` / `✦ Newly Upgraded`
- `home.heroTitle`：`一站式` / `One-stop `
- `home.heroTitleAccent`：`开发者工具箱` / `Developer Toolbox`
- `home.heroSubtitle`：`20+ 精选工具 · 即开即用 · 数据云端同步` / `20+ curated tools · ready to use · cloud synced`
- `home.heroCta`：`开始探索` / `Start Exploring`

- [ ] **Step 2: CategoryTabs 玻璃胶囊**

整体容器加 `glass-card rounded-full p-1 inline-flex`；单个 Tab：非激活 `text-ink-muted hover:text-ink rounded-full px-4 py-1.5 text-sm`；激活 `rounded-full px-4 py-1.5 text-sm text-white bg-[image:var(--gradient-brand)] shadow-[0_4px_14px_rgba(120,90,250,0.35)]`（替换 `index.css:39-41` 的 `.category-tab.active` 纯色规则——该业务类如仍被引用则同步改为透明规则或删除）。

- [ ] **Step 3: ToolGrid 断点**

网格类串改为 `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5`。

- [ ] **Step 4: 验证**

Run: `cd frontend && npm run build && npx tsc --noEmit`
Expected: 通过。走查 1280/768/375px 三档视口：大标题渐变、胶囊 Tab 溢出可换行或横向滚动（`overflow-x-auto flex-nowrap`）、网格列数正确。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Hero/ frontend/src/i18n/
git commit -m "feat(hero): 首页大标题主视觉 + 分类玻璃胶囊 + 网格断点优化"
```

---

### Task 15: 阶段③收尾——四组合走查 + 回归

**Files:** 无新改动（纯验证任务；发现问题时当场小修并并入本任务提交）

- [ ] **Step 1: 全量验证**

```bash
cd frontend && npx vitest run && npm run build && npx tsc --noEmit
```
Expected: 全部通过。

- [ ] **Step 2: 四组合视觉走查**

用浏览器 DevTools 设备模拟逐页检查：首页、登录页、市场、课程、技术内容、账户设置、工作区、Admin 仪表盘。
组合：亮色桌面(1280+) / 亮色移动(390) / 暗色桌面 / 暗色移动。
关注点：文字对比度、玻璃卡在亮色下的可读性、Header/按钮/卡片一致性、无横向滚动条。
发现问题当场修复（小样式问题直接改对应文件），重跑 Step 1。

- [ ] **Step 3: 冒烟回归**

登录 → 首页点击工具进工作区 → 打开 ⌘K 搜索跳转 → Admin 仪表盘。
Expected: 功能零影响（本阶段只动样式与新增组件）。

- [ ] **Step 4: Commit（如有走查小修）**

```bash
git add -A frontend/src
git commit -m "fix(design-system): 阶段③四组合走查小修"
```

---

## 后续阶段计划（占位说明）

本文件当前为**阶段①–③**的可执行计划。阶段④–⑨（其余页面、工作区/工具页外壳与硬编码清理、Admin、H5 底部 Tab、小程序基础、小程序页面）将在阶段①–③落地后，基于实际产出的 token 值与组件形态**续写为本目录下的独立计划文件**（`openspec/changes/glass-glow-redesign/plans/phase4-*.md` 等），每份独立可执行、独立验收——避免在未定稿的 token 值上写死后续细节。
