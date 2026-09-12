# 玻璃光晕改版 · 阶段⑧–⑨ 实施计划（小程序：token 管道重写 + 基础换肤 + 27 页全量）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 小程序（`mini-program/`，Taro + React + Sass，微信 weapp）接入统一设计系统：token 管道修复重写、品牌紫蓝换肤、玻璃降级体系、去 emoji 图标体系、tabBar 换肤 + 图标重绘、主包 14 页 + 分包 13 页全量换肤。

**Architecture:** 单一来源仍是 `frontend/src/styles/tokens/*.css`。token 管道重写为 **WXSS CSS 自定义属性方案**：解析 `_primitives.css` + `colors.css` 暗色块，把 `var()` 引用解析为字面量，输出 `page { --token: value }` 到 `mini-program/src/styles/_tokens.scss`（小程序为暗色单主题，不做运行时切主题——与 design.md §8.2 一致）。旧 `app.scss` 变量名保留为别名层（值改指新 token），27 页零改动即获得品牌色。玻璃用 `_glass.scss` 渐进增强（`@supports (backdrop-filter: blur(1px))`，降级 `--glass-bg-fallback` 实色）。图标用 **内联 SVG data-URI 的 Icon 组件**替代 emoji（裁决：仓库内无法生成 iconfont 字体文件，data-URI Image 在 Taro 可用——openclaw 已有先例，效果等同且免字体加载）。

**Tech Stack:** Taro 3 + React + TypeScript + Sass；node 脚本（仅标准库 fs/zlib）重绘 tabBar 图标。**不新增 npm 依赖。**

## Global Constraints

- 不新增 npm 依赖；不改业务逻辑/API/store/路由配置（页面增删）；中文注释；提交信息 conventional commits + 中文。
- 小程序为**暗色单主题**（design.md §8.2：tabBar 原生换肤、深色底）；亮色主题仅 Web 承载，管道只输出暗色块。
- 工具页只换"壳"：页面容器/标题/按钮/卡片/输入/空态加载态；业务逻辑与接口调用不动。
- `pxtransform`（designWidth 750）会把 scss 中 px 1:1 转 rpx：**token 仅输出颜色/渐变/阴影值，不输出长度 token**（radius/spacing 留在 app.scss 原体系，避免换算口径混乱）。
- 验证：`cd mini-program && npm run build:weapp` 构建通过（首次如需 `npm install` 属环境准备，不算新增依赖）；`npx tsc --noEmit`（如项目配置支持）；视觉走查由用户在微信开发者工具按自检清单验收（本环境无法截图小程序模拟器）。
- 每任务独立提交；杂项不入库。

---

### Task 1: token 管道重写 + `_tokens.scss` 生成 + app.scss 品牌对齐

**Files:**
- Rewrite: `frontend/scripts/generate-miniapp-tokens.js`
- Create: `mini-program/src/styles/_tokens.scss`（脚本产物，提交入库）
- Modify: `mini-program/src/app.scss`（import _tokens + 别名层 + 品牌色 + 页面背景）
- Modify: `mini-program/src/app.config.ts`（window/tabBar 色值）

**Interfaces:**
- Produces: `_tokens.scss` 输出格式 = `page { --p-navy-900: rgb(10, 18, 37); --bg-canvas: rgb(10, 18, 37); --glass-bg: rgba(255,255,255,0.045); --glass-bg-fallback: #131C33; --gradient-brand: linear-gradient(135deg,#5B6BF5,#A155F7); ... }`（全部字面量，无 var() 链——最大 WXSS 兼容）
- app.scss 别名层：`--bg-primary: var(--bg-canvas); --bg-secondary: var(--bg-surface-1); --bg-tertiary: var(--bg-surface-2); --text-primary: rgb(var(--ink-default)) ...`（旧名保值，27 页零改动获品牌色）；`--color-primary: #5B6BF5`、`--color-primary-dark: #4A5AE5`、`--color-primary-light: #8B9BFF`
- app.config：`navigationBarBackgroundColor #0A1225`、`backgroundColor #0A1225`、tabBar `color #5C6784` / `selectedColor #8B9BFF` / `backgroundColor #0A1225`

- [ ] **Step 1: 重写 generate-miniapp-tokens.js**

新逻辑（保留 CLI 入口与中文注释风格）：
1. 输入改为 `_primitives.css` + `colors.css`（解析其中 `:root { }` 暗色块；忽略 `:root[data-theme="light"]`）；输出路径 `OUTPUT_FILE` 修正为 `../../mini-program/src/styles/_tokens.scss`。
2. 解析 `--name: value;` 后做 var() 解析：反复迭代把 `var(--p-*)` / `var(--gradient-*)` / `var(--shadow-*)` / `var(--chart-*)` / `var(--accent-*)` / `var(--ink-*)` 等内部引用替换为已解析值（最多 5 轮，未解析的 var() 报错列出）。
3. 三元组包装：`rgb(var(--p-blue-400))` 迭代后成为 `rgb(96 165 250)` → 归一化为逗号语法 `rgb(96, 165, 250)`（正则把 `rgb\((\d+)\s+(\d+)\s+(\d+)\)` 转 `rgb($1, $2, $3)`）；`rgba(R G B / a)` 同理。
4. 输出头注释"由 generate-miniapp-tokens.js 自动生成，勿手改" + 生成时间 + 来源文件清单。
5. 过滤规则：跳过 `--font-*`（字体栈 Web 专用）、跳过长度类 token（radius/spacing/blur——由调用方过滤 `: \d` 开头的 px 值？改为**仅输出 colors.css 中的颜色/渐变/阴影声明**：值含 `rgb`/`rgba`/`#`/`linear-gradient`/`radial-gradient` 才输出）。

- [ ] **Step 2: 生成并核对 `_tokens.scss`**

Run: `node frontend/scripts/generate-miniapp-tokens.js`
核对：无 `var(` 残留（grep 验证）；含 `--bg-canvas`/`--glass-bg`/`--glass-bg-fallback`/`--gradient-brand`/`--gradient-text`/`--shadow-glass`/`--shadow-glow-accent`/`--accent-primary`/`--ink-*`/`--p-*`（用到的）。

- [ ] **Step 3: app.scss 对齐**

- 顶部 `@import './styles/_tokens.scss';`（Sass 对纯 CSS 文件用 `@import` 即可；若 Sass 版本要求用 `@use` 则按编译器报错调整）
- 别名层（`page` 选择器内，注释说明"旧变量名 → 新 token 的兼容映射，27 页零改动"）：`--bg-primary: var(--bg-canvas); --bg-secondary: var(--bg-surface-1); --bg-tertiary: var(--bg-surface-2); --text-primary/secondary/tertiary → var(--ink-default/muted/faint)` 的 **rgb() 包装形式**（`--text-primary: rgb(var(--ink-default))`——注意 WXSS 支持 var() 链；若求稳可直接写字面量 `rgb(245,247,250)`，两种均可，报告注明选择）；`--color-primary/-dark/-light` → `#5B6BF5/#4A5AE5/#8B9BFF`；`--border-color: var(--glass-border)`；`--shadow-*` 对齐 glass token
- page 背景渐变（:70）`#0F172A→#1E293B` → `#0A1225 → #0F1930`（品牌暗色系）
- 工具类 `.card/.btn/.input-field` 的主色引用随变量自动更新，无需单独改

- [ ] **Step 4: app.config.ts 色值**

按 Interfaces 修改 window 与 tabBar 色值（tabBar 图标 png 在 Task 2 重绘，本任务只改色值）。

- [ ] **Step 5: 验证与提交**

Run: `cd mini-program && npm run build:weapp`
Expected: 构建通过（产物 app.wxss 含新 token）。

```bash
git add frontend/scripts/generate-miniapp-tokens.js mini-program/src/styles/_tokens.scss mini-program/src/app.scss mini-program/src/app.config.ts
git commit -m "feat(mini): token 管道重写（WXSS CSS 自定义属性）+ 品牌紫蓝对齐"
```

---

### Task 2: tabBar 图标重绘（node 脚本程序化生成 8 张 PNG）

**Files:**
- Create: `mini-program/scripts/gen-tabbar-icons.js`
- Overwrite: `mini-program/src/assets/icons/{tool,message,file,profile}[-active].png`（8 张）

**Interfaces:**
- Produces: 8 张 81×81 PNG（微信 tabBar 图标建议 81px）；普通态 `#5C6784`、激活态 `#8B9BFF`；几何线性风格（描边 2px 等效），与 tint/线性图标语言一致

- [ ] **Step 1: 实现生成脚本**

用 node 标准库（`zlib.deflateSync` 手写 PNG：IHDR/IDAT/IEND + CRC32）绘制简单几何图标（81×81 RGBA，透明底，图形居中 48×48 区域）：
- tool：2×2 圆角方块网格
- message：对话气泡（圆角矩形 + 左下小三角）
- file：文档（矩形 + 折角 + 两横线）
- profile：人形（头圆 + 肩弧）
每个图标函数输出 `setPixel(x,y,r,g,b,a)` 级别的绘制逻辑（可用简易描边算法：距离场判定），颜色由参数注入，一次生成 normal/active 两份。中文注释说明手写 PNG 的原因（零依赖、可复现、可改色重生成）。

- [ ] **Step 2: 生成并验证**

Run: `node mini-program/scripts/gen-tabbar-icons.js`
验证：8 张 png 尺寸 81×81（可用 node 读 IHDR 宽高断言）、非空、颜色正确（脚本内自检打印）；`npm run build:weapp` 通过。

- [ ] **Step 3: 提交**

```bash
git add mini-program/scripts/gen-tabbar-icons.js mini-program/src/assets/icons/
git commit -m "feat(mini): tabBar 品牌色图标重绘（零依赖程序化生成 8 张 PNG）"
```

---

### Task 3: `_glass.scss` 玻璃工具类 + Icon 组件 + ToolCard 去 emoji

**Files:**
- Create: `mini-program/src/styles/_glass.scss`
- Modify: `mini-program/src/app.scss`（import）
- Create: `mini-program/src/components/Icon/index.tsx`（+ index.scss 如需）
- Modify: `mini-program/src/components/ToolCard/index.tsx` + `ToolCard.scss`

**Interfaces:**
- Produces:
  - `_glass.scss`：`.glass-card`（`background: var(--glass-bg); border: 1px solid var(--glass-border); @supports (backdrop-filter: blur(14px)) or (-webkit-backdrop-filter: blur(14px)) { backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); }` + 非 supports 分支 `background: var(--glass-bg-fallback)`；含 inset 顶部高光 box-shadow）、`.glass-panel`、`.gradient-text`（`background-image: var(--gradient-text); -webkit-background-clip: text; color: transparent`）、`.btn-primary`（`background-image: var(--gradient-brand); color:#fff; border-radius; box-shadow: 0 4px 18px rgba(120,90,250,0.35)` + hover 态小程序无 hover 可省或用 `hover-class`）、tint 8 类（`.tint` + `.tint-blue|violet|emerald|indigo|orange|red|purple|cyan`，色值照抄 Web glass.css）
  - `<Icon name='json' size={24} color='#8B9BFF' />`：内联 SVG path 表（24×24 viewBox 线性风格）→ `encodeURIComponent` 拼 `data:image/svg+xml` → Taro `<Image mode='aspectFit' style={{width/height}}>`；图标集 ≥24 个：json/code、image、mic、calendar、key、robot、terminal、database、edit、lock、shield、globe、download、upload、search、file、share、video、music、plug、tools、lightbulb、close、chevron-right、user、settings、mail、warning（FA 名映射表 `FA_TO_ICON` 覆盖 ToolCard 原 23 项 fa-* + 兜底 'tools'）

- [ ] **Step 1: `_glass.scss` + app.scss import**（按 Interfaces，注释说明与 Web glass.css 的对应关系及降级策略）
- [ ] **Step 2: Icon 组件**（SVG path 用简单几何线段/圆弧手绘，1.8 stroke-width、round cap；`FA_TO_ICON` 映射 + 未知名兜底 'tools'；中文注释）
- [ ] **Step 3: ToolCard 去 emoji**

- 删除 `FA_TO_EMOJI` 与 `getToolEmoji`；`resolveIconName(icon)` = FA_TO_ICON 查表
- 图标渲染：`custom_icon_url` 有值仍走 Image；否则 `<Icon name={...} size={22} />` 置于 tint chip（`iconTintClass(iconColor)` 等价逻辑内联或建 `utils/tint.ts`：映射 'bg-blue-500' → 'tint-blue'，回退 tint-violet——与 Web iconTint.ts 同构）
- ToolCard.scss：卡片改 `.glass-card`（或类内复刻）、图标底 tint、登录角标硬编码橙（:86-93）→ `--accent-warning` 系、:76 `.auth-badge` → 语义 token

- [ ] **Step 4: 验证与提交**

Run: `cd mini-program && npm run build:weapp`
Expected: 构建通过；ToolCard 逻辑（onClick/custom_icon_url/require_login）不变。

```bash
git add mini-program/src/styles/ mini-program/src/components/Icon/ mini-program/src/components/ToolCard/
git commit -m "feat(mini): 玻璃工具类 + SVG Icon 组件 + ToolCard 去 emoji 走 tint"
```

---

### Task 4: 首页与我的页 custom 导航 + 品牌化

**Files:**
- Modify: `mini-program/src/app.config.ts`（index 与 profile 页加 `"navigationStyle": "custom"`——Taro 页面配置可在 app.config pages 数组旁用页面 config 文件或 `pages/index/index.config.ts`；按 Taro 惯例创建 `pages/index/index.config.ts` 与 `pages/profile/profile.config.ts`（实际路径 profile 页为 `pages/profile/index`，配置文件名跟随））
- Create: `mini-program/src/components/StatusBarSpacer/index.tsx`（`Taro.getSystemInfoSync().statusBarHeight` + `Taro.getMenuButtonBoundingClientRect()` 计算导航高度，输出占位 View；中文注释）
- Modify: `mini-program/src/pages/index/index.tsx` + `index.scss`
- Modify: `mini-program/src/pages/profile/index.tsx` + `index.scss`

- [ ] **Step 1: 状态栏组件 + 页面配置**（两页 `navigationStyle: custom` + 顶部 `<StatusBarSpacer />` + 页内标题栏：渐变 Logo 文字 `gradient-text` + 右侧小图标）
- [ ] **Step 2: 首页品牌化**

- 顶部 hero：`开发者工具箱` 大标题（gradient-text 主词）+ 副标题（`20+ 精选工具 · 即开即用`），下方接现有 SearchBar
- 工具卡网格保持 2 列（ToolCard 已玻璃化自动生效）
- 页面 `🔍` emoji（:91）→ `<Icon name='search' />`；EmptyState 默认 `📭` 在 Task 7 组件化时处理（若本页用到则一并）

- [ ] **Step 3: 我的页品牌化**

- 头部背景 `--bg-secondary→--bg-primary` 渐变 → 品牌系（canvas→surface-1）+ hero 区渐变文字标题
- role-badge 硬编码（index.scss:46）→ `--accent-primary` 系
- 菜单分组卡片 → `.glass-card`

- [ ] **Step 4: 验证与提交**

Run: `cd mini-program && npm run build:weapp`
Expected: 通过（custom 导航需真机/开发者工具核验状态栏高度，列入自检清单）。

```bash
git add mini-program/src/app.config.ts mini-program/src/components/StatusBarSpacer/ mini-program/src/pages/index/ mini-program/src/pages/profile/
git commit -m "feat(mini): 首页/我的 custom 导航品牌化 + hero 渐变标题"
```

---

### Task 5: 登录页玻璃光晕（硬编码最重页面）

**Files:**
- Modify: `mini-program/src/pages/login/index.tsx` + `index.scss`

- [ ] **Step 1: 样式 token 化**

- 页面背景渐变（:5）→ `var(--bg-canvas) → var(--bg-surface-1)` 品牌暗色系
- 装饰光斑 `#3B82F6`/`#10B981`（:30/:38）→ `var(--accent-primary)`/`var(--accent-success)`（保留 blur(80rpx)）
- logo/标题/表单卡/输入框/按钮的 24 处 hex + 13 处 rgba 全部 → token（`--ink-*`、`--glass-*`、`--gradient-brand` 按钮 `.btn-primary`）
- 表单卡 backdrop-filter（:98-99）→ `.glass-card` 渐进增强写法（@supports + fallback）
- tsx 内 emoji 图标（⚙👤🔒✉⚠ :9-29）→ `<Icon name='settings|user|lock|mail|warning' />`

- [ ] **Step 2: 验证与提交**

Run: `cd mini-program && npm run build:weapp`
grep 核对：login/index.scss 无裸 hex（白名单：无）。

```bash
git add mini-program/src/pages/login/
git commit -m "feat(mini): 登录页玻璃光晕（硬编码清零 + 渐进增强）"
```

---

### Task 6: 主包工具页换肤批一（6 页）

**Files:**
- Modify: `mini-program/src/pages/json-formatter/`、`calendar/`、`key-generator/`、`ocr/`、`http-client/`、`asr/`（各自 index.tsx/index.scss）

- [ ] **Step 1: 逐页换肤**

统一规则：卡片/面板 → `.glass-card`；主按钮 → `.btn-primary`；次按钮 → 玻璃描边；输入/textarea → token 边框底色；硬编码 hex/rgba → token（calendar 31 处 hex 12 处 rgba 的多色 legend → 语义 token：粉/青/紫 → accent-secondary/accent-cyan/accent-info 等按语义对号，报告列映射表）；页面内 emoji/Unicode 图标 → `<Icon />`（⌕✕›⚙ 等）；`'Courier New', monospace` 字体保留（代码域惯例）。

- [ ] **Step 2: 验证与提交**

Run: `cd mini-program && npm run build:weapp`；grep 六页无裸 hex（白名单除外）。

```bash
git add mini-program/src/pages/json-formatter/ mini-program/src/pages/calendar/ mini-program/src/pages/key-generator/ mini-program/src/pages/ocr/ mini-program/src/pages/http-client/ mini-program/src/pages/asr/
git commit -m "feat(mini): 主包工具页换肤批一（6 页 token 化 + Icon 化）"
```

---

### Task 7: 主包换肤批二（5 页 + 4 共享组件）

**Files:**
- Modify: `mini-program/src/pages/openclaw/`、`cross-share/message/`、`cross-share/file/`、`change-password/`、`help/`
- Modify: `mini-program/src/components/SearchBar/`、`EmptyState/`、`Loading/`、`Markdown/`

- [ ] **Step 1: 页面换肤**（同 Task 6 规则；openclaw 渐变 `var(--color-primary,#3b82f6)→#8b5cf6` → `var(--gradient-brand)`、:277 `#dc2626` → `var(--accent-danger)`；cross-share 两页 emoji/Unicode → Icon）
- [ ] **Step 2: 组件换肤**

- SearchBar：`⌕`/`✕` → `<Icon name='search'/'close' />`
- EmptyState：默认 `📭` → `<Icon name='file' size={48} />`（保留自定义 icon prop 能力）
- Loading：CSS spinner 色对齐 Admin/Web 标准（border-accent + border-t-transparent）
- Markdown/index.scss：pre 底 rgba(0,0,0,0.3)、code #e2e8f0、行内 code/th 的 blue rgba → `--glass-*`/`--ink-*`/`--accent-primary` 系（代码块底保留深色域惯例可入白名单，报告判定）

- [ ] **Step 3: 验证与提交**

Run: `cd mini-program && npm run build:weapp`

```bash
git add mini-program/src/pages/openclaw/ mini-program/src/pages/cross-share/ mini-program/src/pages/change-password/ mini-program/src/pages/help/ mini-program/src/components/
git commit -m "feat(mini): 主包换肤批二 + 共享组件 token 化"
```

---

### Task 8: 分包换肤（9 页）

**Files:**
- Modify: `mini-program/src/package-media/image-downloader/`、`video-downloader/`、`package-docs/markitdown-converter/`、`markdown-editor/`、`package-learning/course-platform/`(+`detail/`)、`tech-contents/`(+`detail/`)、`package-stats/token-usage/`

- [ ] **Step 1: 逐页换肤**（同 Task 6 规则；video-downloader 9 处 hex、markitdown emoji、学习分包课程卡对齐 Web CourseCard 的 glass + 渐变进度条模式）
- [ ] **Step 2: 验证与提交**

Run: `cd mini-program && npm run build:weapp`；分包体积核对（微信主包 2M 限制不受影响——分包各自独立）。

```bash
git add mini-program/src/package-media/ mini-program/src/package-docs/ mini-program/src/package-learning/ mini-program/src/package-stats/
git commit -m "feat(mini): 分包 9 页换肤（媒体/文档/学习/统计）"
```

---

### Task 9: 阶段⑧⑨收尾——清零校验 + 自检清单交付

**Files:**
- Create: `mini-program/docs/glass-glow-acceptance.md`（逐页自检清单）
- Modify: 无预设代码改动

- [ ] **Step 1: 清零校验**

```bash
cd mini-program && grep -rEn "#[0-9a-fA-F]{3,6}\b" src --include="*.scss" | grep -v "_tokens.scss" | grep -v "_glass.scss"
cd mini-program && grep -rEo "🔧|🖼|🔍|📭|⚙|👤|🔒|✉|⚠|⌕|✕|›" src --include="*.tsx"
```
Expected: hex 残留仅白名单（如有：逐条理由——深色代码块域/图片占位等）；emoji 残留 0（或白名单：文本内容中的非图标 emoji）。
全量：`npm run build:weapp` + `npx tsc --noEmit`（如可用）。

- [ ] **Step 2: 自检清单**

`glass-glow-acceptance.md`：27 页 × 检查点（品牌色/玻璃卡/图标/空态/加载态/custom 导航状态栏高度/tabBar 图标/玻璃降级——开发者工具切"不兼容 backdrop-filter"验证基线）+ 已知限制（暗色单主题、iconfont→SVG 方案裁决、真机项）。

- [ ] **Step 3: 提交**

```bash
git add mini-program/docs/glass-glow-acceptance.md
git commit -m "docs(mini): 玻璃光晕改版逐页自检清单 + 清零校验记录"
```

---

## 交付后事项

- 视觉验收：用户在**微信开发者工具**按 `glass-glow-acceptance.md` 逐页走查（构建产物已入 `dist/`）；真机项（安全区/custom 导航状态栏/backdrop-filter 降级）需真机预览。
- `phase3-deferred.md` 的"小程序阶段注意"全部适用于本计划；完成后把 phase3/4-5/6-7 三份 defer 文档的遗留功能项（view_count 行锁、AuthModal 注册、reading_time 等）汇总开 issue。
