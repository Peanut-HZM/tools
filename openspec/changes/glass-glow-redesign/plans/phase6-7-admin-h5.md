# 玻璃光晕改版 · 阶段⑥–⑦ 实施计划（Admin 全套 + H5 底部 Tab 栏与全站响应式核查）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Admin 后台全套玻璃化（分组玻璃侧栏 + 移动抽屉 + palette 清零）、H5 底部玻璃 Tab 栏（M1 方案）落地、全站响应式与触控目标核查——Web 端（阶段①–⑦）全部完成。

**Architecture:** 设计系统已就绪（token 双主题、glass.css、tint、UI 组件玻璃化）。Admin 建立分组导航 + 抽屉模式；H5 在 Layout 层挂 MobileTabBar（/admin 与沉浸路由天然排除）。延续既定模式：全高导航轨 = `glass-panel rounded-none border-y-0 border-l-0`，玻璃 chip 激活 = `text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)]`。

**Tech Stack:** React 18 + TypeScript + Tailwind（darkMode `[data-theme="dark"]`）+ lucide-react。**不新增 npm 依赖。**

## Global Constraints

- 不新增 npm 依赖；不改业务逻辑/API/路由结构（新增 UI 组件与类串不算改路由）；中文注释；提交信息 conventional commits + 中文。
- Admin 页面只换"壳"（容器/表格/卡片/按钮/空态加载态样式），不动查询/提交/权限逻辑。
- 验证基线不劣化：`npx tsc --noEmit` 71 存量错、`npx vitest run` 4 个存量失败文件（monaco/K8s mock）。
- 关键备忘：glass.css 先于 `@tailwind utilities` 导入（组件显式类可覆盖玻璃底）；`shadow-[shadow:var(--x)]` 需类型提示；prose 标准串 `prose dark:prose-invert prose-headings:text-ink prose-p:text-ink-muted prose-a:text-accent`。
- 工作目录 `frontend/`；每任务独立提交；杂项（package-lock.json、awesome-design-md/）不入库。

---

### Task 1: H5 底部玻璃 Tab 栏（M1 方案）

**Files:**
- Create: `frontend/src/components/Layout/MobileTabBar.tsx`
- Modify: `frontend/src/components/Layout/Layout.tsx`（挂载）
- Modify: `frontend/src/i18n/`（补 `nav.profile`：zh `我的` / en `Me`；类型机制强制 en/zh 同步）

**Interfaces:**
- Consumes: `lib/navigation.ts` 的 `NAV_ROUTES`（复用首页/市场/课程三项的路由与 i18n key）；`glass-panel`；lucide 图标
- Produces: `<MobileTabBar />`——固定底部玻璃 Tab 栏，md 以下显示（`md:hidden`），沉浸路由（`/tools/*`、`/workspace`）不渲染；4 项：首页 `/`(Home)、市场 `/marketplace`(Store)、课程 `/courses`(GraduationCap)、我的 `/account-settings`(User, i18n key `nav.profile`)

- [ ] **Step 1: 实现 MobileTabBar**

结构（参照已确认的 M1 设计稿：glass-panel 浮条 + 激活图标发光 + 渐变底标）：

```tsx
import { NavLink, useLocation } from 'react-router-dom';
import { Home, Store, GraduationCap, User } from 'lucide-react';
import { useI18n } from '../../i18n';

/**
 * 移动端底部玻璃 Tab 栏（M1 方案，design.md §7）。
 * 仅 md 以下显示；沉浸路由（/tools/*、/workspace）由 Layout 控制不渲染。
 */
const TABS = [
  { to: '/', key: 'home', Icon: Home, match: (p: string) => p === '/' },
  { to: '/marketplace', key: 'marketplace', Icon: Store, match: (p: string) => p.startsWith('/marketplace') },
  { to: '/courses', key: 'courses', Icon: GraduationCap, match: (p: string) => p.startsWith('/courses') },
  { to: '/account-settings', key: 'profile', Icon: User, match: (p: string) => p.startsWith('/account-settings') },
] as const;

export default function MobileTabBar() {
  const { t } = useI18n();
  const { pathname } = useLocation();
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 px-3 pb-[max(env(safe-area-inset-bottom),0.75rem)] pt-2 pointer-events-none">
      <div className="glass-panel rounded-2xl flex items-stretch justify-around pointer-events-auto">
        {TABS.map(({ to, key, Icon, match }) => {
          const active = match(pathname);
          return (
            <NavLink
              key={to}
              to={to}
              className={`flex flex-col items-center justify-center gap-0.5 min-h-[56px] min-w-[64px] px-3 rounded-xl transition-colors ${
                active ? 'text-accent-primary' : 'text-ink-faint hover:text-ink-muted'
              }`}
            >
              <Icon className={`w-5 h-5 ${active ? 'drop-shadow-[0_0_8px_rgba(122,108,255,0.8)]' : ''}`} />
              <span className="text-[10px] leading-none">{t.nav[key]}</span>
              {active && <span className="w-6 h-0.5 rounded-full bg-[image:var(--gradient-brand)]" />}
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
```

注意：`t.nav[key]` 的 key 联合类型需覆盖 `profile`（i18n 补 key 后自然成立）；`useNavigate`/跳转由 NavLink 承担。

- [ ] **Step 2: Layout 挂载**

Layout.tsx：`isImmersion` 为 false 时在 `<Footer />` 之后渲染 `<MobileTabBar />`（沉浸时不渲染）；Footer 移动端加 `pb-24 md:pb-10` 类的底部留白（避免被 Tab 栏遮挡最后的内容——用 `pb-24 md:pb-10` 方式加在 Layout 主容器或 Footer 上，按现有结构择一）。

- [ ] **Step 3: 验证**

Run: `cd frontend && npm run build && npx tsc --noEmit`（基线不劣化）。
浏览器走查（可选）：390px 视口四 Tab 切换、激活态发光/底标、沉浸路由与 /admin 无 Tab 栏、安全区填充。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Layout/ frontend/src/i18n/
git commit -m "feat(h5): 移动端底部玻璃 Tab 栏（首页/市场/课程/我的）"
```

---

### Task 2: Header 移动端补齐 + Admin ⌘K 修复

**Files:**
- Modify: `frontend/src/components/Header/Header.tsx`
- Modify: `frontend/src/components/Admin/AdminLayout.tsx`（仅挂 CommandPalette）

- [ ] **Step 1: 主题切换按钮移动端可达**

主题切换按钮（约 :123-126）`hidden md:inline-flex` → 常显（去掉 hidden md:）；语言/联系我们/Admin 入口保持 `hidden md:inline-flex`（语言移动端入口 = 账户设置 preferences 区，已在；联系与 Admin 属低频，移动端由后续需求承载，报告注明）。

- [ ] **Step 2: Admin 域 ⌘K 修复**

AdminLayout.tsx 引入并渲染 `<CommandPalette />`（import `../Common/CommandPalette`）——修复移动端搜索图标在 /admin 下点击无响应（CommandPalette 此前只挂 Layout，/admin 不在其内）。

- [ ] **Step 3: 验证与提交**

Run: `cd frontend && npm run build && npx tsc --noEmit`
浏览器（可选）：390px 移动 Header 出现主题按钮；/admin 下 ⌘K 与搜索图标可唤起面板。

```bash
git add frontend/src/components/Header/Header.tsx frontend/src/components/Admin/AdminLayout.tsx
git commit -m "fix(h5): 移动端主题切换可达 + Admin 域接入命令面板"
```

---

### Task 3: 触控目标 ≥44px 统一

**Files:**
- Modify: `frontend/src/components/ui/Button.tsx`（size icon）
- Modify: `frontend/src/components/Header/LoginButton.tsx`
- Modify: `frontend/src/components/Hero/CategoryTabs.tsx`
- Modify: `frontend/src/pages/CourseLearnPage.tsx`（返回箭头）
- Modify: `frontend/src/pages/TechContentDetailPage.tsx`（点赞/收藏）

- [ ] **Step 1: 逐点调整**

- `ui/Button.tsx` size.icon：`h-10 w-10` → `h-11 w-11`（44px，桌面端视觉影响极小）
- LoginButton：登录按钮（约 :83-88）加 `min-h-[44px]`；已登录下拉触发器（约 :43-48）→ `min-h-[44px]`
- CategoryTabs（约 :24）：Tab 类补 `min-h-[40px]` 并把 `py-1.5` → `py-2.5`（视觉接近 44px 且保持胶囊形态）；**同时补非激活态 `hover:bg-glass-bg`**（L30，带入项）
- CourseLearnPage 返回箭头（约 :201-206）：裸图标按钮 → `h-11 w-11 rounded-lg hover:bg-glass-bg inline-flex items-center justify-center`
- TechContentDetailPage 点赞/收藏（约 :158-170）：`p-2` → `min-h-[44px] min-w-[44px] p-2`（保持 ghost 观感）

- [ ] **Step 2: 验证与提交**

Run: `cd frontend && npm run build && npx tsc --noEmit`

```bash
git add frontend/src/components/ui/Button.tsx frontend/src/components/Header/LoginButton.tsx frontend/src/components/Hero/CategoryTabs.tsx frontend/src/pages/CourseLearnPage.tsx frontend/src/pages/TechContentDetailPage.tsx
git commit -m "fix(h5): 交互触控目标统一 ≥44px + CategoryTabs hover 补齐"
```

---

### Task 4: 学习页移动端溢出修复（带入项）

**Files:**
- Modify: `frontend/src/pages/CourseLearnPage.tsx`

- [ ] **Step 1: 响应式堆叠**

- 外层（约 :234）`flex h-[calc(100vh-80px)]` → `flex flex-col lg:flex-row h-[calc(100vh-80px)] lg:overflow-hidden overflow-y-auto`
- 侧栏 aside（约 :237）`w-80` → `w-full lg:w-80 lg:flex-shrink-0`（移动端章节列表在上方堆叠）
- 页内 header 进度块（约 :216）`w-64` → `w-full sm:w-64`
- 内容区（约 :341 起的卡片区）确认 `min-w-0` 防溢出（如有固定宽度类逐处加 lg 限定）
- 双头堆叠（全站 Header + 页内 header）为既有结构，本次不动（报告注明）

- [ ] **Step 2: 验证与提交**

Run: `cd frontend && npm run build`
浏览器（可选）：390px 学习页无横向溢出（scrollWidth == clientWidth）。

```bash
git add frontend/src/pages/CourseLearnPage.tsx
git commit -m "fix(h5): 学习页移动端响应式堆叠，消除横向溢出"
```

---

### Task 5: AdminLayout 玻璃化 + 菜单分组

**Files:**
- Modify: `frontend/src/Admin/AdminLayout.tsx`（即 `components/Admin/AdminLayout.tsx`）

**Interfaces:**
- Produces: 菜单数据重组为三组（纯前端分组，不改路由）：概览[仪表盘]、内容管理[工具管理/课程管理/Agent 管理/对话管理/留言管理]、系统[用户管理/OSS 存储/大模型配置/OpenClaw 管理/MCP 工具/系统设置]；导出 `ADMIN_MENU_GROUPS`（组内项 = 现 12 项的 to/label/icon 原样搬移）

- [ ] **Step 1: 侧栏玻璃化 + 分组**

- 去渐变堆叠：侧栏容器（约 :72）`bg-gradient-to-br from-surface-1 to-canvas … shadow-xl` → 全高导航轨模式 `glass-panel rounded-none border-y-0 border-l-0`
- 徽标块（约 :74）`from-accent to-accent-info` 渐变底 → `tint tint-violet` chip 或渐变文字（选一，报告注明）
- 菜单按三组渲染（组标题：`text-[10px] uppercase tracking-widest text-ink-faint px-3 pt-4 pb-1`）
- 激活项（约 :86-87）`bg-gradient-to-r from-accent/20 to-accent-info/10 … shadow-lg shadow-accent/10` → 玻璃 chip 标准串（激活）+ `text-ink-muted hover:text-ink hover:bg-glass-bg`（非激活），用 NavLink/useLocation 激活判定（以 `pathname === to` 或 startsWith，/admin 精确匹配仪表盘）
- 主内容区（约 :101）`bg-gradient-to-br … shadow-xl` → `bg-canvas`（去掉容器阴影）

- [ ] **Step 2: 验证与提交**

Run: `cd frontend && npm run build && npx tsc --noEmit`

```bash
git add frontend/src/components/Admin/AdminLayout.tsx
git commit -m "feat(admin): 玻璃分组侧栏替换渐变堆叠（概览/内容管理/系统）"
```

---

### Task 6: Admin 移动端抽屉

**Files:**
- Modify: `frontend/src/components/Admin/AdminLayout.tsx`

- [ ] **Step 1: 抽屉化**

- 侧栏（约 :71）`w-64 flex-shrink-0` → `hidden lg:flex lg:flex-col lg:w-64 lg:flex-shrink-0`（原 overflow-y-auto 保留在 lg 侧栏上）
- 新增移动端管理条：主内容区顶部 `lg:hidden` sticky 条（`glass-panel rounded-none border-x-0 border-t-0`）内含汉堡按钮（Menu 图标，h-11 w-11 触控达标）+ "管理后台"标题
- 点击汉堡开抽屉：固定覆盖层（`bg-canvas/60 backdrop-blur-sm`）+ 左侧滑入玻璃抽屉（`glass-panel` 全高、w-72、含同款分组菜单与激活态）；点遮罩/菜单项关闭（路由跳转后 `useState(false)`）
- 抽屉菜单复用 `ADMIN_MENU_GROUPS` 数据与激活类串（同 Task 5）

- [ ] **Step 2: 验证与提交**

Run: `cd frontend && npm run build && npx tsc --noEmit`
浏览器（可选）：390px /admin 汉堡开抽屉、跳转自动关。

```bash
git add frontend/src/components/Admin/AdminLayout.tsx
git commit -m "feat(admin): 移动端玻璃抽屉导航（lg 以下汉堡触发）"
```

---

### Task 7: Dashboard 玻璃化 + 加载/空态统一

**Files:**
- Modify: `frontend/src/components/Admin/Dashboard.tsx`

- [ ] **Step 1: 统计卡/表格/状态**

- 统计卡（约 :59/:71/:83 手写）→ `glass-card rounded-xl`（保留数值/布局）；:85/:91 `to-purple-500` 渐变清零（改 `--gradient-brand` 引用或语义 token，按原语义：若为装饰渐变 → `bg-[image:var(--gradient-brand)]`；若为状态色 → accent-success/danger）
- 表格容器（约 :98）→ `glass-card rounded-xl overflow-hidden`（行 hover `hover:bg-glass-bg`）
- 加载态（约 :30）统一为标准 spinner：`h-8 w-8 rounded-full border-2 border-accent border-t-transparent animate-spin`（Admin 域标准，后续任务复用）
- 空态（约 :128）保留 Inbox 图标模式但底色换 `glass-card rounded-xl`（Admin 域空态标准）

- [ ] **Step 2: 验证与提交**

Run: `cd frontend && npm run build && npx tsc --noEmit`

```bash
git add frontend/src/components/Admin/Dashboard.tsx
git commit -m "feat(admin): 仪表盘玻璃化 + 加载/空态标准化"
```

---

### Task 8: Admin palette 残留清零（23 行清单）

**Files:**
- Modify: `frontend/src/components/Admin/CourseDetail.tsx`(:182 ×2)、`AgentManagement.tsx`(:573)、`McpServers/index.tsx`(:108/:151/:155/:168/:175/:182/:189/:196)、`McpServers/EvalDialog.tsx`(:103/:144)、`McpServers/CreateDialog.tsx`(:272)、`McpServers/TestResultDialog.tsx`(:50)、`CourseManagement/CourseEditor.tsx`(:268)、`CourseManagement/ChapterList.tsx`(:108)、`LLMConfigs/QuotaManagementTab.tsx`(:555)、`LLMConfigs/ResourceManager.tsx`(:73-78)

**映射规则**（语义对号入座，±5 行漂移以语义定位）：
- `bg-blue-500/20 text-blue-600 border-blue-500/30` 类状态底 → `bg-accent-info/10 text-accent-info border-accent-info/30` 模式
- `text-green-600` → `text-accent-success`；`text-gray-400` → `text-ink-faint`
- `hover:to-pink-500/20`/`to-blue-600/20`/`to-blue-500/20` 装饰渐变端点 → `to-accent-secondary/20` / `to-accent-info/20`
- `bg-blue-500/600` 按钮 → `ui/Button`（default）或 `btn-primary` 类串
- cyan/yellow/red/gray hover 对（McpServers index :168-196）→ `accent-cyan`/`accent-warning`/`accent-danger`/`ink` 对应 hover 档
- `accent-cyan-500` → `accent-cyan`
- ResourceManager 5 组装饰渐变（:73-78 from-blue-500 to-cyan-500 等）→ 统一替换为品牌系：交替使用 `bg-[image:var(--gradient-brand)]` 与 `bg-accent-info`/`bg-accent-success`/`bg-accent-danger`/`bg-ink-muted` 纯色（分类色标语义），报告列映射表
- 顺带统一各页 spinner 为 Task 7 标准类、空态为 glass-card 模式（触到的文件内顺手，不专门扩展文件清单）

- [ ] **Step 1: 逐文件清零**（按映射表，报告列 23 行逐条映射）
- [ ] **Step 2: 清零校验**

```bash
cd frontend && grep -rEn "(bg|text|border|from|via|to|ring|divide|placeholder|accent)-(blue|violet|purple|indigo|emerald|green|orange|amber|red|yellow|pink|gray|slate|zinc|cyan|teal|sky|rose)-[0-9]{2,3}" src/components/Admin src/contexts --include="*.tsx"
```
Expected: 仅剩白名单（逐条列出理由）。

- [ ] **Step 3: 验证与提交**

Run: `cd frontend && npx vitest run && npm run build && npx tsc --noEmit`（基线不劣化）

```bash
git add frontend/src/components/Admin/
git commit -m "chore(admin): palette 残留清零 + 加载/空态标准化"
```

---

### Task 9: Toast 主题联动修复

**Files:**
- Modify: `frontend/contexts/ToastContext.tsx`

- [ ] **Step 1: Toaster theme 联动**

- :134 `theme="dark"` 硬编码 → 读取实际解析主题：先查 `lib/theme.tsx` 是否导出 resolved 主题（读文件确认）；若无，在 ToastContext 内用 `useTheme()` 的 theme + `window.matchMedia('(prefers-color-scheme: light)')` 按 theme.tsx 同语义解析（dark/light/system），或直接读 `document.documentElement.getAttribute('data-theme')`（Task 1 的内联脚本保证其先于首帧就位——**优先此方案**，简单且与 CSS 联动源一致）
- 保持 sonner 其余配置不动

- [ ] **Step 2: 验证与提交**

Run: `cd frontend && npm run build`
浏览器（可选）：亮色主题触发 toast，面板底色为亮色玻璃。

```bash
git add frontend/contexts/ToastContext.tsx
git commit -m "fix(design-system): Toaster 主题跟随 data-theme 联动"
```

---

### Task 10: 阶段⑥⑦收尾——全站响应式核查 + 清零校验 + 冒烟

**Files:** 无预设改动（发现小问题当场修，功能问题记 BLOCKED-NOTE）

- [ ] **Step 1: 全量验证 + 扩展清零校验**

`cd frontend && npx vitest run && npm run build && npx tsc --noEmit`（基线不劣化）。
清零 grep（palette + divide/placeholder/accent 前缀，Task 8 的扩展版）全 src 复核，白名单逐条理由（预期残留：styles/ 定义处、tint/Badge/语义底 rgba、xterm/recharts/代码深底域、DevComponentsPage、TimeTravel、phase4-5-deferred 已裁决项）。

- [ ] **Step 2: 四组合走查**

页面 = Admin 全部 12 页（桌面亮/暗）+ 移动端重点（Tab 栏四页、学习页、Admin 抽屉、Header 主题按钮）。截图存 `D:\CodeProjects\tools\.superpowers\sdd\phase6-7-admin-h5\shots\`（t67-*.png）。
重点：Admin 玻璃侧栏分组/抽屉、Dashboard 卡片、H5 Tab 栏四页切换与安全区、触控目标、学习页无溢出。

- [ ] **Step 3: 冒烟 + 提交**

Admin：仪表盘 → 工具管理列表 → OSS → 系统设置（只读走查，不提交数据）；H5：首页 → 市场 → 课程 → 我的 → 工具打开。
有修复则 `git add -A frontend && git commit -m "fix(design-system): 阶段⑥⑦走查小修"`

---

## 后续阶段（本计划不含）

- 阶段⑧⑨ 小程序（token 管道重写为 WXSS CSS 自定义属性方案、tabBar 换肤+图标重绘、Icon 组件去 emoji、首页/profile custom 导航、27 页换肤）——在阶段⑥⑦ 落地后由独立计划 `plans/phase8-9-mini-program.md` 承载。
- 继承项：`phase4-5-deferred.md`（清零 grep 前缀扩展已纳入 Task 8/10；其余延后项随触碰顺手处理）。
