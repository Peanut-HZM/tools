# 玻璃光晕改版 · 阶段④–⑤ 实施计划（FOUC + 页面套用新视觉 + 工作区/工具页外壳 + 硬编码清理）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 Web 端剩余页面（登录注册/市场/课程/技术内容/账户）的玻璃光晕套用、工作区与工具页外壳统一、全站硬编码颜色清零，并修复 FOUC 与收敛路由单一来源——Web 端（阶段①–⑦中的④⑤）全部完成。

**Architecture:** 设计系统已在阶段①–③ 落地（token 双主题、glass.css 工具类、tint 图标、UI 组件玻璃化）。本计划是**应用层**改造：把已 token 化但视觉未升级的页面统一到玻璃语言，并清零残余硬编码。工具页只换壳（页面级容器/标题/按钮/图标），不动功能区布局逻辑。

**Tech Stack:** React 18 + TypeScript + Tailwind（darkMode: `['selector', '[data-theme="dark"]']`）+ CSS 变量 token。**不新增 npm 依赖。**

## Global Constraints

- 不新增 npm 依赖；不改业务逻辑/API/路由结构（路由跳转目标不变）；中文注释；提交信息 conventional commits + 中文。
- 工具页只换"壳"：页面级容器、标题区、图标块、按钮、空态/加载态；工具内部功能区仅替换颜色引用（写死的 surface/palette/hex → token），不改布局与交互逻辑。
- 现状基线（来自 2026-09-12 调研，行号以执行时实际为准，允许 ±5 行漂移）：tsc 71 存量错（Admin 既有）、vitest 4 个存量失败文件（monaco/K8s mock）——验证要求"不劣化"而非清零。
- 遗留带入项见 `openspec/changes/glass-glow-redesign/phase3-deferred.md`：FOUC（Task 1）、路由单一来源（Task 2）、ToastContext 死代码（Task 11）、CoursesPage input `w-80`（Task 5）。
- 关键技术备忘：Tailwind 3.4.19 任意值引用变量阴影须 `shadow-[shadow:var(--x)]`；`glass.css` 在 `@tailwind utilities` 之前导入（组件显式 `bg-*` 可覆盖玻璃底）；`dark:` 变体已绑定 `[data-theme="dark"]`，`prose` + `dark:prose-invert` 即可双主题。
- 工作目录 `frontend/`；验证命令：`npx vitest run`（基线不劣化）、`npm run build`、`npx tsc --noEmit`（71 错不新增）；每任务独立提交。

---

## 阶段④ FOUC 修复 + 页面套用新视觉

### Task 1: FOUC 内联引导脚本

**Files:**
- Modify: `frontend/index.html`（head 内，`</head>` 之前；同时顺手补文件末尾换行符）

**Interfaces:**
- Consumes: `theme.tsx` 的约定——localStorage key `tk-theme`、值 `dark|light|system`、默认 `dark`、system 按 `prefers-color-scheme: light` 解析
- Produces: 刷新时首帧前 `data-theme` 已就位（消除亮色用户闪暗）

- [ ] **Step 1: 插入内联脚本**

在 `index.html` 的 `</head>` 之前（字体 link 之前亦可，位置在 head 内任意样式加载点之前即可）插入：

```html
<script>
  // 首帧前同步主题，消除亮色用户刷新时的暗色闪烁（FOUC）。
  // 语义与 src/lib/theme.tsx 保持一致：key 'tk-theme'，值 dark|light|system，默认 dark。
  (function () {
    try {
      var t = localStorage.getItem('tk-theme');
      if (t !== 'light' && t !== 'dark') {
        t = (t === 'system' || t == null)
          ? (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark')
          : 'dark';
      }
      document.documentElement.setAttribute('data-theme', t);
    } catch (e) {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  })();
</script>
```

注意：`theme.tsx` 挂载 effect 随后会幂等重写同一属性，无冲突（阶段③终审已确认双写无害）。

- [ ] **Step 2: 验证**

Run: `cd frontend && npm run build`
Expected: 成功（index.html 为 Vite 模板原样输出，脚本不被处理）。
浏览器验证（可选）：切亮色 → 刷新，观察首帧无暗色闪烁；DevTools 查看 `<html data-theme="light">` 在 CSS 加载前已存在。

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "fix(design-system): index.html 内联主题引导脚本消除 FOUC"
```

---

### Task 2: 路由单一来源 `lib/navigation.ts`

**Files:**
- Create: `frontend/src/lib/navigation.ts`
- Modify: `frontend/src/components/Header/Header.tsx`、`frontend/src/components/Footer/Footer.tsx`、`frontend/src/components/Common/CommandPalette.tsx`（改用共享定义）
- Modify: `frontend/src/lib/commandPalette.ts`（PAGE_ITEMS 改由 navigation.ts 派生或移除）

**Interfaces:**
- Produces（均在 `lib/navigation.ts`，纯数据、不依赖 React/i18n——i18n 需组件上下文，路由结构属纯数据）:
  - `export const OPEN_COMMAND_PALETTE_EVENT = 'open-command-palette';`
  - `export interface NavRoute { to: string; key: 'home' | 'marketplace' | 'courses' | 'techContents'; match(path: string): boolean }`
  - `export const NAV_ROUTES: NavRoute[]`（首页全等、其余 startsWith，与现 Header NAV_ITEMS 一致；消费端用 `t.nav[item.key]` 取文案）
  - `export const PAGE_ROUTES: { id: string; to: string; key: NavRoute['key'] | 'account' }[]`（commandPalette PAGE_ITEMS 的路由来源：首页/市场/课程/技术内容/账户设置）
  - `lib/commandPalette.ts` 的 `PAGE_ITEMS` 改为从 `PAGE_ROUTES` 派生（key → 静态中文 label 映射留在 commandPalette.ts，re-export 签名不变，测试不受影响）

- [ ] **Step 1: 创建 navigation.ts**（按上述 Interfaces 实现，含中文注释：为什么 lib 层不做 i18n 依赖——i18n 需 React 上下文，路由结构属纯数据）

- [ ] **Step 2: 三个消费点切换**

- Header.tsx：删除局部 NAV_ITEMS，改 `NAV_ROUTES.map(...)` + `t.nav[item.key]`；事件派发改 `new CustomEvent(OPEN_COMMAND_PALETTE_EVENT)`
- Footer.tsx：删除局部 NAV_ITEMS（4 链接），改 `NAV_ROUTES` + `t.nav[item.key]`（match 字段 Footer 不用）
- CommandPalette.tsx：`'open-command-palette'` 字符串改用常量；`PAGE_ITEMS` 内部改为从 `PAGE_ROUTES` 派生（key→静态中文 label 映射留在 commandPalette.ts），对组件与测试的导出签名不变
- Hero.tsx 的 `open-command-palette` 派发改用常量

- [ ] **Step 3: 验证**

Run: `cd frontend && npx vitest run src/lib/commandPalette.test.ts && npm run build && npx tsc --noEmit`
Expected: 单测通过（PAGE_ITEMS re-export 后行为不变）、构建成功、tsc 不新增。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/navigation.ts frontend/src/lib/commandPalette.ts frontend/src/components/Header/Header.tsx frontend/src/components/Footer/Footer.tsx frontend/src/components/Common/CommandPalette.tsx frontend/src/components/Hero/Hero.tsx
git commit -m "refactor(navigation): 路由与事件名单一来源 lib/navigation.ts"
```

---

### Task 3: 登录/注册页玻璃化

**Files:**
- Modify: `frontend/src/App.tsx`（LoginPage 容器，约 :108）
- Modify: `frontend/src/components/Auth/LoginForm.tsx`（约 :57 卡片）
- Modify: `frontend/src/components/Auth/RegisterForm.tsx`（约 :150 卡片）

- [ ] **Step 1: 容器加光晕氛围**

LoginPage 容器类串改为：

```
min-h-screen bg-canvas relative overflow-hidden flex items-center justify-center p-4
```

并在容器内、表单卡之前加装饰层（自闭合，不拦截交互）：

```tsx
      {/* 氛围光晕装饰层（纯视觉，pointer-events-none） */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -top-24 -left-24 w-[28rem] h-[28rem] rounded-full bg-accent/20 blur-3xl" />
        <div className="absolute -bottom-32 -right-20 w-[26rem] h-[26rem] rounded-full bg-accent-secondary/15 blur-3xl" />
      </div>
```

表单卡外层包 `relative`（或卡片自身加 relative）确保在装饰层之上。

- [ ] **Step 2: 两张表单卡玻璃化**

LoginForm :57 与 RegisterForm :150 的卡片类串：`bg-surface-1 rounded-xl p-8 shadow-md` → `glass-card rounded-2xl p-8 relative`。

- [ ] **Step 3: 验证与提交**

Run: `cd frontend && npm run build`
浏览器走查（可选）：亮/暗两主题登录页光晕 + 玻璃卡。

```bash
git add frontend/src/App.tsx frontend/src/components/Auth/
git commit -m "feat(auth): 登录注册页光晕背景 + 玻璃卡片"
```

---

### Task 4: MarketplacePage 玻璃化

**Files:**
- Modify: `frontend/src/pages/MarketplacePage.tsx`

- [ ] **Step 1: 卡片与按钮升级**

- Agent 卡（约 :91）：`p-4 border border-border rounded-lg bg-surface-1` → `glass-card hover-lift rounded-xl p-4 cursor-pointer`（保留原 onClick/内部结构）
- Fork/主操作按钮（约 :111 手写 `bg-accent` 系）→ `<Button size="sm">`（ui/Button default 即 .btn-primary）；刷新按钮（约 :68 手写 bg-surface-2）→ `<Button variant="outline" size="sm">`
- 页面标题区若为普通文本，给 h1 加 `gradient-text`（仅主标题词组）

- [ ] **Step 2: 验证与提交**

Run: `cd frontend && npm run build && npx tsc --noEmit`

```bash
git add frontend/src/pages/MarketplacePage.tsx
git commit -m "feat(marketplace): Agent 卡片玻璃化 + 按钮走设计系统"
```

---

### Task 5: 课程列表页三件套（CoursesPage + CourseCard + FilterSidebar）

**Files:**
- Modify: `frontend/src/pages/CoursesPage.tsx`
- Modify: `frontend/src/components/Courses/CourseCard.tsx`
- Modify: `frontend/src/components/Courses/FilterSidebar.tsx`

- [ ] **Step 1: CoursesPage**

- 头部横幅（约 :63）`bg-surface-1/50 border-b border-border/50` → `glass-panel border-x-0 border-t-0 rounded-none`
- 搜索框（约 :85 手写）→ 换 `ui/Input`（玻璃输入框），同时修复带入项：外层容器 `w-full sm:w-80` 且 **input 自身 `w-full`**（原内层固定 `w-80` 在 <352px 溢出）
- 手写按钮（约 :139/:169/:173/:179）：主操作 → `ui/Button`（default），次操作 → `variant="outline"`/`"ghost"`

- [ ] **Step 2: CourseCard**

- 卡片（约 :59）实心 surface + `hover:-translate-y-1` → `glass-card hover-lift rounded-xl`（删除旧 hover 位移类，由 hover-lift 承担）
- CTA（约 :145）旧式渐变 `bg-gradient-to-r from-accent to-accent-hover ...` → `<Button size="sm" className="w-full">`（default variant）

- [ ] **Step 3: FilterSidebar**

- 面板（约 :49/:63/:104）`bg-surface-1/50` 准玻璃 → `glass-card rounded-xl`
- radio 双背景类冲突（约 :81/:121 `bg-accent bg-surface-2`）→ 选中态 `bg-[image:var(--gradient-brand)] border-transparent text-white`，未选中 `bg-glass-bg border-glass-border`

- [ ] **Step 4: 验证与提交**

Run: `cd frontend && npm run build && npx tsc --noEmit`
浏览器走查（可选）：课程列表亮/暗 × 移动端。

```bash
git add frontend/src/pages/CoursesPage.tsx frontend/src/components/Courses/
git commit -m "feat(courses): 课程列表页玻璃化 + CTA/搜索框走设计系统"
```

---

### Task 6: 课程详情与学习页（CourseDetailPage + CourseLearnPage）

**Files:**
- Modify: `frontend/src/pages/CourseDetailPage.tsx`
- Modify: `frontend/src/pages/CourseLearnPage.tsx`

- [ ] **Step 1: CourseDetailPage**

- `prose prose-invert`（约 :131）→ `prose dark:prose-invert prose-headings:text-ink prose-p:text-ink-muted prose-a:text-accent`（dark: 变体已绑定 data-theme，双主题正确；prose 子元素 token 化防止亮色下继承失败）
- 信息卡（约 :93/:137/:189）`bg-surface-1/50 backdrop-blur-sm` → `glass-card rounded-xl`
- 手写 `bg-accent` 按钮（约 :67/:177/:221）→ `ui/Button`（default/outline 按语义）
- 头像渐变（约 :234）`from-accent to-accent-hover` 保留（token 渐变，符合品牌）

- [ ] **Step 2: CourseLearnPage**

- CTA（约 :316）`bg-gradient-to-r from-accent to-accent-hover hover:from-accent-hover hover:to-accent-hover` → `<Button className="...">`（default）；同款完成按钮（约 :407）`bg-accent-success` 保留语义（改 `ui/Button` 不合适——成功色按钮保留原类，仅把 hover 系列对齐 token）
- 头部（约 :198）与侧栏（约 :237）`bg-surface-1/30` 系 → `glass-panel border-x-0 border-t-0 rounded-none` / `glass-card`（侧栏）
- 内容卡（约 :341/:353）准玻璃 → `glass-card rounded-xl`
- 进度条渐变（约 :224）保留

- [ ] **Step 3: 验证与提交**

Run: `cd frontend && npm run build && npx tsc --noEmit`

```bash
git add frontend/src/pages/CourseDetailPage.tsx frontend/src/pages/CourseLearnPage.tsx
git commit -m "feat(courses): 详情/学习页玻璃化 + prose 双主题修复 + CTA 走设计系统"
```

---

### Task 7: 技术内容两页 + 卡片（TechContentsPage + DetailPage + TechContentCard）

**Files:**
- Modify: `frontend/src/pages/TechContentsPage.tsx`
- Modify: `frontend/src/pages/TechContentDetailPage.tsx`
- Modify: `frontend/src/components/TechContent/TechContentCard.tsx`

- [ ] **Step 1: TechContentsPage**

- hero 横幅（约 :95）`bg-gradient-to-r from-accent-info/50 to-accent-secondary/50` 整宽旧渐变 → 改为结构化 hero：外层 `glass-panel border-x-0 border-t-0 rounded-none`，标题 `gradient-text`，副标题 `text-ink-muted`（删除整宽彩色渐变）
- 筛选 chip（约 :111-115 手写 bg-primary/bg-surface-1）→ 玻璃胶囊（同 CategoryTabs 模式）：激活 `text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)]`，非激活 `text-ink-muted hover:text-ink hover:bg-glass-bg`，容器 `glass-card rounded-full p-1 inline-flex`
- 分页按钮（约 :150/:160）→ `ui/Button variant="outline" size="sm"`

- [ ] **Step 2: TechContentDetailPage**

- `prose prose-invert`（约 :227）→ 同 Task 6 Step 1 的写法
- 手写按钮（约 :105/:235/:239/:243）→ `ui/Button`（点赞/收藏等互动按钮语义色保留 token，但容器用 ghost/outline）
- 头像渐变（约 :165）保留

- [ ] **Step 3: TechContentCard**

- 卡片（约 :75）`bg-surface-1` → `glass-card hover-lift rounded-xl`
- 头像渐变（约 :143）保留；封面渐变（约 :96）token 保留

- [ ] **Step 4: 验证与提交**

Run: `cd frontend && npm run build && npx tsc --noEmit`

```bash
git add frontend/src/pages/TechContentsPage.tsx frontend/src/pages/TechContentDetailPage.tsx frontend/src/components/TechContent/
git commit -m "feat(tech-content): 列表/详情玻璃化 + hero 重构 + prose 双主题修复"
```

---

### Task 8: 账户设置（AccountLayout + AccountSidebar + SettingCard）

**Files:**
- Modify: `frontend/src/components/Account/AccountLayout.tsx`
- Modify: `frontend/src/components/Account/AccountSidebar.tsx`
- Modify: `frontend/src/components/Account/SettingCard.tsx`

- [ ] **Step 1: AccountLayout**

- 页面底（约 :40）`bg-gradient-to-br from-canvas via-surface-1 to-canvas` 旧风格 → `bg-canvas`（氛围交给 mesh/玻璃卡，不再整页斜向渐变）

- [ ] **Step 2: AccountSidebar**

- 桌面 nav 与移动标签页（约 :37-92）激活态 `bg-accent/10 border-accent text-accent hover:bg-accent/20` → 玻璃 chip：激活 `text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)] border-transparent`，非激活 `text-ink-muted hover:text-ink hover:bg-glass-bg border-glass-border`；桌面项 `rounded-lg`、移动项 `rounded-full`（保持现有布局，仅换激活/非激活类串）

- [ ] **Step 3: SettingCard**

- （约 :13）`backdrop-blur-sm bg-surface-1/50 border-border/50` → `glass-card rounded-xl`（保留原 padding 类）

- [ ] **Step 4: 验证与提交**

Run: `cd frontend && npm run build && npx tsc --noEmit`

```bash
git add frontend/src/components/Account/
git commit -m "feat(account): 账户设置玻璃化（侧栏玻璃 chip + 设置卡统一）"
```

---

### Task 9: 阶段④收尾——新改页面四组合走查

**Files:** 无预设改动（发现问题当场小修，同类修法参照前任务规则）

- [ ] **Step 1: 全量验证**

`cd frontend && npx vitest run && npm run build && npx tsc --noEmit`（基线不劣化）

- [ ] **Step 2: 走查**

页面：登录/注册、市场、课程列表/详情/学习、技术内容列表/详情、账户设置。组合：亮/暗 × 桌面(1280)/移动(390)。重点：prose 正文双主题可读性、玻璃卡亮色对比度、光晕装饰层不遮挡交互、移动端表格/侧栏不溢出。截图存 `.superpowers/sdd/phase4-5/shots/`。

- [ ] **Step 3: 冒烟 + 提交**

登录 → 课程列表 → 进详情 → 学习页进度；技术内容列表 → 详情。
有修复则 `git add -A frontend/src && git commit -m "fix(design-system): 阶段④走查小修"`

---

## 阶段⑤ 工作区 + 工具页外壳 + 硬编码清理

### Task 10: 工作区玻璃化（TabBar + WorkspaceSidebar）

**Files:**
- Modify: `frontend/src/components/Workspace/TabBar.tsx`
- Modify: `frontend/src/components/Workspace/WorkspaceSidebar.tsx`

- [ ] **Step 1: TabBar 标签 chip 玻璃化（已确认的 mockup 方案）**

- 栏（约 :12）`bg-surface-1 border-b border-border h-10` → `glass-panel border-x-0 border-t-0 rounded-none h-10`
- tab chip（约 :33-36）：active `bg-canvas text-ink border-t/l/r border-border` → `text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)] rounded-lg`；inactive `bg-surface-1 hover:bg-surface-2` → `text-ink-muted hover:text-ink hover:bg-glass-bg rounded-lg`
- 关闭 ×/溢出滚动等逻辑不动

- [ ] **Step 2: WorkspaceSidebar**

- 侧栏（约 :46）`w-52 bg-surface-1 border-r` → `w-52 glass-panel rounded-none border-y-0 border-l-0`（右描边保留）
- 首页按钮（约 :51 手写 bg-accent）→ `ui/Button` default（.btn-primary）
- 搜索框（约 :67 手写）→ `ui/Input`
- 打开项 active（约 :88）`bg-accent/20 text-accent` 保留（token 正确），非 active hover 对齐 `hover:bg-glass-bg`
- fas 图标（约 :93）：若为 Font Awesome 类名字符串，替换为等价 lucide-react 组件（Home/Search/Wrench 等按语义挑选）；若替换成本高（多处动态映射），仅把图标容器包 tint chip（`iconTintClass` 不适用于 FA 名，直接用 `tint tint-violet` 基样或保留原样），在报告中说明取舍

- [ ] **Step 3: 验证与提交**

Run: `cd frontend && npm run build && npx tsc --noEmit`

```bash
git add frontend/src/components/Workspace/
git commit -m "feat(workspace): 标签栏玻璃 chip + 侧栏走设计系统"
```

---

### Task 11: 工具页外壳统一（抽样三件 + OpenSpecCourse 整页 + AIAssistant）

**Files:**
- Modify: `frontend/src/components/Tools/JsonFormatter.tsx`
- Modify: `frontend/src/components/Tools/ImageDownloader.tsx`
- Modify: `frontend/src/components/Tools/OpenSpecCourse.tsx`
- Modify: `frontend/src/components/Tools/AIAssistant.tsx`

**外壳规则（抽样建立范式，供阶段⑤批量复制）：** 页面级顶栏 `bg-surface-1 border-b` → `glass-panel border-x-0 border-t-0 rounded-none`；标题图标块实心色 → `tint` chip（w-10~12 rounded-xl）；手写按钮 → `ui/Button` 对应 variant；页面标题主词 `gradient-text`。

- [ ] **Step 1: JsonFormatter**

- 顶栏（约 :92）`bg-surface-1 border-b` → glass-panel 模式
- 图标块（约 :103 实心 `bg-success`）→ `tint tint-emerald w-10 h-10 rounded-xl`（图标 text-white → 继承 tint 色）
- 手写覆盖按钮（约 :134 `bg-warning hover:opacity-90`）→ 保留语义黄色但收敛为 `bg-[rgba(251,191,36,0.12)] text-accent-warning border border-[rgba(251,191,36,0.3)]`（Badge 语义色同款规格）或改 ghost+图标提示，按现有交互语义择一并在报告说明

- [ ] **Step 2: ImageDownloader**

- 标题图标（约 :170-171）`w-16 h-16 bg-accent rounded-full` + text-white → `w-12 h-12 tint tint-violet rounded-xl`
- 其余已用 ui/Card（阶段① 已玻璃化）确认即可

- [ ] **Step 3: OpenSpecCourse 整页去紫渐变（全站最突兀页面）**

- 三处整页容器（约 :118/:129/:145）`bg-gradient-to-br from-purple-900 via-indigo-800 to-blue-900` → `bg-canvas`（氛围由 Layout 的 mesh 背景承担）
- header（约 :147）`bg-black/30 backdrop-blur-sm border-white/10` → `glass-panel border-x-0 border-t-0 rounded-none`
- 文字（约 :161-162）`text-white / text-white/60` → `text-ink / text-ink-muted`
- 页内其余 palette/text-white 逐处替换为 ink 系 token（工具内容区逻辑不动）；内部卡片若依赖深底，改 `glass-card`

- [ ] **Step 4: AIAssistant**

- 图标块（约 :26-27）`bg-gradient-to-r from-purple-500 to-pink-500` + text-white → `tint tint-purple w-10 h-10 rounded-xl`

- [ ] **Step 5: 验证与提交**

Run: `cd frontend && npm run build && npx tsc --noEmit`
浏览器走查（可选）：四个工具页亮/暗，确认功能区交互无回归（仅换壳）。

```bash
git add frontend/src/components/Tools/JsonFormatter.tsx frontend/src/components/Tools/ImageDownloader.tsx frontend/src/components/Tools/OpenSpecCourse.tsx frontend/src/components/Tools/AIAssistant.tsx
git commit -m "feat(tools): 工具页外壳统一（顶栏/图标/按钮走设计系统）+ OpenSpecCourse 去整页紫渐变"
```

---

### Task 12: 死代码删除 + 硬编码清理（ToastContext / TraceViewer / ImportExportDialog）

**Files:**
- Delete: `frontend/src/components/Tools/CrossShare/CrossShareCard.tsx`、`frontend/src/components/Tools/OpenSpecCourse/OpenSpecCourseCard.tsx`、`frontend/src/components/Recommendations/RecommendationCard.tsx`（三者经调研均为零引用死代码——**执行前必须重新 grep 验证**，若有引用则改为按外壳规则重写而非删除，并在报告说明）
- Modify: `frontend/contexts/ToastContext.tsx`
- Modify: `frontend/src/components/Harness/TraceViewer.tsx`
- Modify: `frontend/src/components/Admin/CourseManagement/ImportExportDialog.tsx`

- [ ] **Step 1: 死代码验证与删除**

```bash
cd frontend && grep -rn "CrossShareCard\|OpenSpecCourseCard\|RecommendationCard" src/ --include="*.tsx" --include="*.ts" | grep -v "^Binary"
```
Expected: 仅自引用（自身文件）。确认后 `git rm` 三个文件。

- [ ] **Step 2: ToastContext hex → token**

- :38-41 四类型的 hex/rgba 改用 token 值（style 内联需具体值，读 `styles/tokens/colors.css` 对应语义变量的实际 RGB：success `#34D399`(dark)/`#10B981`(light) 等——**取暗色值为准**（Toast 走暗色玻璃，phase③ 已统一 sonner 样式），或改为 `rgb(var(--accent-success))` 形式（style 属性支持 var()，且随主题联动，**优先此方案**）；rgba(…,0.1) 底 → `rgb(var(--accent-success) / 0.1)` 同理
- 顺带删除死代码：`typeColors.bg` 字段（无消费者）与 `sonner-toast-dark` 死类名（:121 附近，全库无 CSS 定义）

- [ ] **Step 3: TraceViewer palette → token（16 处）**

映射表（gray 系 → ink 系，浅底 → 玻璃，语义色 → accent 语义）：
- `text-gray-500/400` → `text-ink-faint`；`text-gray-700` → `text-ink-muted`
- `hover:bg-gray-50` → `hover:bg-glass-bg`；`bg-blue-50` → `bg-glass-bg`
- `bg-red-50`/`bg-amber-50` → `bg-[rgba(248,113,113,0.12)]` / `bg-[rgba(251,191,36,0.12)]`
- `text-red-500/600` → `text-accent-danger`；`text-amber-600` → `text-accent-warning`；`text-blue-500` → `text-accent-info`；`text-green-600` → `text-accent-success`

- [ ] **Step 4: ImportExportDialog**

- 主 CTA（约 :556）`bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white` → `btn-primary` 类串（或 `ui/Button`）；:221 `to-blue-500/20` → `to-accent-info/20`
- 冗余写法顺手收敛（:218/:220/:257/:272/:334/:440/:444/:448/:528 中 `from-success to-success` 之类同色双停渐变 → 单色 `bg-success`，逐一判断，报告列出收敛清单）

- [ ] **Step 5: 验证与提交**

Run: `cd frontend && npx vitest run && npm run build && npx tsc --noEmit`（基线不劣化；Toast 属全局组件，冒烟触发一条 toast 确认样式）

```bash
git rm frontend/src/components/Tools/CrossShare/CrossShareCard.tsx frontend/src/components/Tools/OpenSpecCourse/OpenSpecCourseCard.tsx frontend/src/components/Recommendations/RecommendationCard.tsx
git add frontend/contexts/ToastContext.tsx frontend/src/components/Harness/TraceViewer.tsx frontend/src/components/Admin/CourseManagement/ImportExportDialog.tsx
git commit -m "chore(design-system): 死代码删除 + ToastContext/TraceViewer/ImportExportDialog 硬编码清零"
```

---

### Task 13: MetricsPanel 图表颜色 token 化（19 处 hex）

**Files:**
- Modify: `frontend/src/styles/tokens/colors.css`（新增图表语义组）
- Modify: `frontend/src/components/Tools/K8sTool/ResourceDetail/MetricsPanel.tsx`

**Interfaces:**
- Produces: 图表语义 token（双主题）：`--chart-cpu`、`--chart-memory`、`--chart-grid`、`--chart-axis`、`--chart-surface`、`--chart-label`

- [ ] **Step 1: colors.css 追加图表组**

暗色块（:root）：

```css
  /* === 图表语义组（recharts 内联 style 用，支持 var() 随主题联动） === */
  --chart-cpu:      var(--p-blue-400);
  --chart-memory:   var(--p-green-500);
  --chart-grid:     rgba(148, 163, 204, 0.15);
  --chart-axis:     var(--p-ink-light-2);
  --chart-surface:  #1E293B;
  --chart-label:    var(--p-ink-light-3);
```

亮色块（`:root[data-theme="light"]`）：

```css
  --chart-cpu:      var(--p-blue-600);
  --chart-memory:   var(--p-green-600);
  --chart-grid:     rgba(13, 37, 61, 0.10);
  --chart-axis:     var(--p-ink-dark-2);
  --chart-surface:  #FFFFFF;
  --chart-label:    var(--p-ink-dark-3);
```

- [ ] **Step 2: MetricsPanel 替换（hex 行号清单见调研 :42-256）**

- `#3b82f6` → `var(--chart-cpu)`；`#10b981` → `var(--chart-memory)`
- `#374151`（网格/分隔）→ `var(--chart-grid)`；`#9ca3af`（轴/标签）→ `var(--chart-axis)` 或 `var(--chart-label)`（按语义：刻度文字用 label，轴线用 axis）
- `#4b5563` → `var(--chart-grid)`；`#1e293b`（tooltip/面板底）→ `var(--chart-surface)`
- **注意**：recharts 的 stroke/fill 走 SVG attribute 时 var() 在部分浏览器不解析——这些值必须位于 `style={{...}}` 内联样式或经 `getComputedStyle` 读取；逐处核对当前写法，属性式（stroke="…"/fill="…"）的一律迁移到 style 对象，报告中列出迁移清单

- [ ] **Step 3: 验证与提交**

Run: `cd frontend && npm run build && npx tsc --noEmit`
浏览器走查（可选）：K8s 工具任一资源详情页图表双主题渲染正常。

```bash
git add frontend/src/styles/tokens/colors.css frontend/src/components/Tools/K8sTool/ResourceDetail/MetricsPanel.tsx
git commit -m "feat(design-system): 新增图表语义 token，MetricsPanel 19 处 hex 清零"
```

---

### Task 14: 阶段⑤收尾——硬编码清零校验 + 四组合走查

**Files:** 无预设改动

- [ ] **Step 1: 清零校验**

```bash
cd frontend && grep -rEn "#[0-9a-fA-F]{6}\b" src/ contexts/ --include="*.tsx" --include="*.ts" | grep -v "\.test\." | grep -v "index.css"
cd frontend && grep -rEn "(bg|text|border|from|via|to|ring)-(blue|violet|purple|indigo|emerald|green|orange|amber|red|yellow|pink|gray|slate|zinc|neutral|stone|cyan|teal|sky|rose|fuchsia|lime|mango)-[0-9]{2,3}\b" src/ contexts/ --include="*.tsx"
```
Expected: 结果清单为空或仅剩**白名单项**（逐条判定：tint 色板/glass.css/charts 定义处、recharts 数据点调色板等合理保留项列入报告白名单；其余当场替换）。注意本约束只针对 src/contexts 业务代码，`styles/tokens/`、`styles/glass.css`、`styles/backgrounds.css` 不在校验范围。

- [ ] **Step 2: 全量验证 + 四组合走查**

`npx vitest run && npm run build && npx tsc --noEmit`（基线不劣化）。
走查页面：工作区（开 2-3 个工具标签验证玻璃 chip）、OpenSpecCourse、AIAssistant、K8s 图表页、TraceViewer 所在页、导入导出弹窗、Toast 触发。组合亮/暗 × 桌面/移动。截图存 `.superpowers/sdd/phase4-5/shots/`。

- [ ] **Step 3: 冒烟 + 提交**

登录 → 首页 → 打开 3 个工具 → 工作区切换标签 → K8s 图表 → Toast。
有修复则 `git add -A frontend && git commit -m "fix(design-system): 阶段⑤走查小修与清零校验白名单确认"`

---

## 后续阶段（本计划不含）

- 阶段⑥ Admin 全套、⑦ H5 底部 Tab 栏 + 全站响应式核查、⑧⑨ 小程序——在阶段④–⑤ 落地后续写独立计划（沿用 `plans/` 目录）。
- `phase3-deferred.md` 中剩余未带入项（Badge default/secondary 区分、Tabs 非激活 hover、模糊强度统一、Admin 对比度实测）并入阶段⑥/⑦。
