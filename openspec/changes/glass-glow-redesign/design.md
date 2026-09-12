# 工具箱全站改版设计：玻璃光晕（Glass Glow）

- **日期**：2026-09-12
- **状态**：待用户审阅
- **范围**：Web 桌面端、H5（移动端响应式）、微信小程序（`mini-program/`）全量视觉改版 + 统一设计系统建设
- **性质**：纯视觉/样式改版，不改动任何业务逻辑、API 与后端

---

## 1. 背景与问题

用户反馈全站"太丑、不高端、缺乏设计感"。调研发现根因不在缺少设计系统骨架，而在落地覆盖率低与三端不一致：

- **Web 端**：已有 token 体系（`frontend/src/styles/tokens/`：colors/typography/spacing/radius/shadows/motion）与双主题机制（`data-theme`，暗色默认），但全站约 213 处硬编码 Tailwind palette 类、约 63 处 tsx 内联 hex；首页无主视觉区；Header 无任何移动端适配；`OpenSpecCourse` 等页面整页脱离 token（大紫渐变）。
- **小程序端**（`mini-program/`，Taro + React + TS + Sass）：自带一套与 Web 不一致的变量（信任蓝 `#3B82F6` vs Web 紫蓝）；工具图标全靠 **emoji 映射**（低级感最大来源）；token 生成脚本 `frontend/scripts/generate-miniapp-tokens.js` 输出路径指向不存在的 `miniapp/` 目录，**管道已断**。
- **字体**：`index.html` 引入的 HarmonyOS Sans SC 在 Google Fonts 上不存在（404），中文实际回退系统字体；Pacifico、Noto Serif SC 等外链存在无效加载。

## 2. 目标与非目标

### 目标

1. 建立**一套完整、单一来源的样式设计系统**，Web / H5 / 小程序三端复用。
2. 设计系统**可扩展**：可持续新增样式（工具类/组件）与新增主题（如未来加"高对比度"或换品牌色），无需改动业务代码。
3. 全站（Web + 小程序）视觉统一为「玻璃光晕」语言：暗色为默认基调，亮色主题同步适配，主色为电光紫蓝渐变。
4. 移动端体验达到"产品级"：底部玻璃 Tab 栏、触控目标规范、网格与排版适配。
5. 小程序去 emoji 化，图标与 Web 同构。

### 非目标（明确不做）

- 不引入新 UI 框架/组件库，**不新增任何 npm 依赖**（⌘K 命令面板基于现有 Radix Dialog 自研）。
- 不改业务逻辑、API、后端、路由结构。
- 不做独立 App / 不基于 Taro 重写 Web（Web 继续走 Vite+React 响应式，即 H5）。
- 不做自定义小程序 tabBar（用原生 tabBar 换肤，见 §8）。
- 不做国际化样式分叉、不做 SSR。

## 3. 已确认的关键决策

| 决策点 | 结论 | 备注 |
|---|---|---|
| 视觉风格 | 双主题（亮/暗可切换），暗色默认 | 沿用现有 `data-theme` 三态机制（dark/light/system） |
| 视觉语言 | **A · 玻璃光晕**：毛玻璃卡片 + 多层光晕背景 + 渐变标题 | 三候选中最接近 Linear/Arc 质感（设计稿已确认） |
| 主色 | 电光紫蓝渐变（`#5B6BF5 → #A155F7`，文字渐变延伸到 `#67E8F9`） | 品牌签名 |
| 移动端导航 | **M1 · 底部玻璃 Tab 栏**（md 以下显示） | 首页/市场/课程/我的 四入口（设计稿已确认） |
| Admin / 工作区 | 玻璃侧栏分组导航 / 玻璃标签 chip（设计稿已确认） | 去 glow+渐变堆叠 |
| 小程序 | 纳入本次改版，全页面覆盖 | 主包 14 页 + 4 分包 |
| 架构 | 单一 token 来源 → Web(SCSS/CSS 变量) 与 小程序(SCSS) 双输出 | 见 §4 |

## 4. 统一设计系统架构（核心）

### 4.1 单一来源与三层 token

Token 唯一来源为 `frontend/src/styles/tokens/*.css`（CSS 自定义属性）。分两层：

```
primitive（原始调色板，新增 _primitives.css）
  --p-violet-500、--p-blue-600、--p-cyan-400、--p-gray-…（含暗/亮通用色阶）
        │  语义映射
        ▼
semantic（语义 token，现有 colors/typography/spacing/radius/shadows/motion + 新增玻璃组）
  --bg-canvas、--accent-primary、--glass-bg、--shadow-glow-accent …
        │  消费
        ▼
组件/工具类直接引用 semantic（不建 component 层，避免过度设计）
```

- **主题 = 一组 semantic 覆盖**：`:root[data-theme="dark"]` 与 `:root[data-theme="light"]`。新增主题只需新增一组 semantic 映射（引用 primitive），primitive 永远不动。
- 小程序侧沿用既有占位符机制：`%light-tokens` + `@mixin light-tokens`，未来新主题生成对应的 `%<theme>-tokens`。

### 4.2 多端输出管道

| 端 | 消费方式 |
|---|---|
| Web 桌面 / H5（同一代码库，Vite + React + Tailwind） | `tokens/*.css` 经 `:root` 变量全局生效；`tailwind.config.js` 将 fontFamily/fontSize/radius/shadow/color 映射到 CSS 变量（已有机制，扩展映射） |
| 小程序（Taro + React + Sass） | `node frontend/scripts/generate-miniapp-tokens.js` 将 tokens CSS 解析为 `mini-program/src/styles/_tokens.scss`（**修正输出路径**：脚本现指向不存在的 `miniapp/`）；另生成/维护 `_glass.scss`（玻璃工具类 + 降级 mixin，见 §8.3），该文件手工维护、但引用 `_tokens.scss` 变量 |
| 未来端（如 Taro H5/RN） | token 均为无单位数值 + 颜色字符串，可再写一个生成器对接，架构预留 |

**管道纪律**：tokens CSS 变更后必须重跑生成脚本（写入实施计划的检查清单）；`_tokens.scss` 顶部保留"自动生成，勿手改"声明。

### 4.3 主题/样式扩展流程（可扩展性的落地定义）

**新增一个主题**（示例"高对比度暗色"）：
1. Web：在 `tokens/colors.css` 新增 `:root[data-theme="hc-dark"]` 语义映射（只引用 primitive）。
2. 运行生成脚本 → 小程序自动获得对应占位符与 mixin。
3. `lib/theme.tsx` 的 Theme 联合类型与切换器加一项；小程序如有同样入口则在设置页加配置。
4. 业务代码零改动（全部组件引用 semantic token）。

**新增一个样式**（如新的卡片变体）：Web 侧在 `styles/glass.css` 加工具类或组件变体；小程序侧在对应 SCSS 模块用同名 class + `_tokens.scss` 变量实现，两端共用设计规范但不共享代码（各端实现层解耦，token 层强一致）。

## 5. 设计规范详情

### 5.1 色彩

**暗色（默认）**：保留深海军蓝基底（`--bg-canvas: 10 26 47` 向 mockup 的 `#0A1225` 微调靠拢），语义 token 结构不变。新增：

```
/* 玻璃表面组 */
--glass-bg:         rgba(255,255,255,0.045);
--glass-bg-strong:  rgba(255,255,255,0.07);
--glass-bg-fallback: #131C33;              /* 不支持 backdrop-filter 时的实色降级底 */
--glass-border:     rgba(255,255,255,0.09);
--glass-highlight:  rgba(255,255,255,0.07);   /* inset 顶部高光 */
--glass-blur:       14px;

/* 品牌渐变组（扩展现有 --gradient-accent） */
--gradient-brand:        linear-gradient(135deg,#5B6BF5 0%,#A155F7 100%);
--gradient-brand-hover:  linear-gradient(135deg,#6E7EFF 0%,#B266FF 100%);
--gradient-text:         linear-gradient(120deg,#7C8CFF 10%,#B36BFF 60%,#67E8F9 105%);
--shadow-glow-accent:    0 6px 24px rgba(120,90,250,0.45), inset 0 1px 0 rgba(255,255,255,0.25);
--shadow-glass:          0 12px 32px rgba(3,7,20,0.50);
```

**亮色**：从米黄纸感（`245 233 212`）**改为冷调灰白**（canvas 约 `#F6F7FB` 系），玻璃表现为白色半透明面 + 细灰描边 + 柔和扩散投影；渐变降低不透明度（复用现有 mesh 亮色降档思路）。

**图标 tint 色板**（替换 8 个饱和色块）：8 组「低饱和色底 + 同色描边 + 同色图标」，如 `bg rgba(101,116,255,0.14) / border rgba(101,116,255,0.25) / icon #8B9BFF`；以 primitive 色阶派生，暗亮两套自动适配。

### 5.2 字体

- 拉丁/数字：**Geist / Geist Mono**（已加载，保留）。
- 中文：系统栈 `PingFang SC → HarmonyOS Sans SC(本地) → Microsoft YaHei`；**删除 404 的 Google Fonts HarmonyOS 链接**。
- Logo：从 Pacifico 手写体改为**渐变无衬线粗体**（Geist 800 + `--gradient-text`），移除 Pacifico 外链；Noto Serif SC 外链确认无引用后一并移除（保留 `--font-serif` token 定义）。
- 字号层级沿用现有 12 级 token；首页 Hero 大标题用 `display-xl`（60px 级）。

### 5.3 圆角 / 阴影 / 动效

- 卡片 12–16px、玻璃面板 16px、胶囊 999px、图标 chip 9–10px。
- 交互统一模式：**hover 抬升 4px + 描边转 accent + glow/glass 阴影**，150–200ms，复用现有 `--ease-stripe` 缓动；保留 `prefers-reduced-motion` 降级（Web 与小程序 CSS 动画均适用）。

### 5.4 工具类（两端复用的"样式词汇表"）

| 工具类 | Web 实现（新增 `styles/glass.css`） | 小程序对应（`styles/_glass.scss`） |
|---|---|---|
| `.glass-card` | 半透明底+描边+blur+glass 阴影+inset 高光 | 同名 class，`@supports` 渐进增强 |
| `.glass-panel` | 更强底色的面板（导航/抽屉） | 同上 |
| `.gradient-text` | 渐变裁切文字 | 同上（background-clip 兼容写法） |
| `.gradient-border` | 渐变描边（border-image/双背景法） | 同上 |
| `.hover-lift` | 抬升+发光 hover 态 | 小程序无 hover，转为 `hover-class` 用法 |
| `.tint-icon` | tint 色板图标 chip | 同上 |

### 5.5 图标体系

- Web：继续 lucide-react（线性图标），工具卡图标 = tint chip + lucide。
- 小程序：引入 **iconfont 字体**（Taro 支持字体文件），图标名对齐 lucide 语义（如 `icon-json`、`icon-image`）；ToolCard 删除 `FA_TO_EMOJI` 映射表；tabBar 图标重绘为品牌风格 PNG（4 组 × 2 态）。

## 6. Web 端改造清单

| 优先 | 位置 | 改造内容 |
|---|---|---|
| 1 | `styles/tokens/*` + `styles/glass.css` + 字体修复 | §5 全部 token/工具类落地；`index.html` 字体外链清理 |
| 1 | `components/ui/*`（18 个组件） | Button（主=渐变、次=玻璃、幽灵）、Card、Input、Dialog、Tabs、Toast、Tooltip、Skeleton 等统一玻璃语言；`/dev/components` 验收页同步更新 |
| 1 | `Header` + 新增 ⌘K 命令面板 | 玻璃悬浮条、渐变 Logo、当前页渐变下划线、⌘K 面板（搜索工具/页面/操作，Radix Dialog 自研）；清理死代码 `Navigation.tsx` |
| 1 | 首页 `Hero` + `ToolGrid` + `ToolCard` | 新增大标题区（渐变标题+副标题+搜索胶囊+CTA）、分类 Tab 玻璃胶囊化、网格 1/2/3/4 列、卡片玻璃化+hover 抬升发光+tint 图标 |
| 2 | `Footer` | 从单行扩展为三栏（品牌+渐变 Logo / 页面导航 / 说明与版权） |
| 2 | 市场 / 课程 / 技术内容 / 账户设置 / 登录注册 | 套用新视觉；登录注册页加光晕背景与玻璃卡 |
| 3 | 工作区 `WorkspacePage` | 玻璃标签 chip（激活态渐变薄底）、虚线"＋"开新工具、画布保持全屏沉浸 |
| 3 | 工具页外壳统一 | 各工具页的页面级容器/标题/按钮换肤；**工具内部功能区只换颜色引用不动布局逻辑** |
| 4 | 硬编码清理（重点文件） | `OpenSpecCourse.tsx`（整页紫渐变）、`OpenSpecCourseCard`、`CrossShareCard`、`AIAssistant`、`MetricsPanel`（19 处 hex）、`ToastContext`、`TraceViewer`、`ImportExportDialog`；全站 palette 类/hex 逐步 token 化 |
| 5 | `Admin` 全套 | 玻璃侧栏按「概览/内容管理/系统」分组、激活态渐变薄底+细描边（去 glow 堆叠）、统计卡/表格/表单统一、移动端抽屉化 |

## 7. H5 / 移动端适配（Web 响应式）

- 断点统一 Tailwind 标准：sm 640 / md 768 / lg 1024 / xl 1280。
- **md 以下显示 M1 底部玻璃 Tab 栏**（首页/市场/课程/我的，active 渐变点+图标发光），lg 以上隐藏；Header 收纳为 Logo + 搜索图标 + 头像（搜索框点开全屏玻璃层）。
- 触控目标 ≥ 44px；工具网格移动端 1→2 列；卡片信息密度降档（次要元数据收起）。
- 工具类页面（编辑器/终端类）保持全屏沉浸，移动端增加顶部返回栏（标题+关闭/返回）。
- Admin 移动端：侧栏变为玻璃抽屉（汉堡触发）。

## 8. 小程序改造（`mini-program/`）

### 8.1 token 与基础

- 修正 `generate-miniapp-tokens.js` 输出路径为 `mini-program/src/styles/_tokens.scss`，接入 §5 全部新 token（含玻璃组）。
- `app.scss` 现有独立变量整体迁移到 `_tokens.scss`（旧变量保留别名过渡一个版本，避免遗漏引用）。

### 8.2 设计语言对齐

- 背景向 Web 的 `#0A1225` 靠拢；主色换品牌紫蓝；渐变文字/渐变按钮同 Web 规范。
- tabBar：**保留原生 tabBar**（不做自定义——玻璃 tabBar 在小程序内兼容与性能风险高、收益低），配色换新：深色底（与 canvas 一致）、选中色品牌紫、新图标。

### 8.3 玻璃降级策略（关键工程点）

小程序 WebView 对 `backdrop-filter` 支持参差（iOS 较好、安卓部分机型失效）。统一写法：

```scss
.glass-card {
  background: $glass-bg-fallback;     // 实色降级底（token：--glass-bg-fallback）
  border: 1px solid $glass-border;
  @supports (backdrop-filter: blur(14px)) or (-webkit-backdrop-filter: blur(14px)) {
    background: $glass-bg;
    backdrop-filter: blur(14px);
  }
}
```

任何机型下保证"半透明实色 + 细描边"基线观感，支持模糊的机型增强。

### 8.4 页面改造范围（全量）

- **主包 14 页**：首页（工具网格 2 列、渐变大标题 custom 导航）、cross-share 消息/文件、profile（custom 导航）、login（光晕背景）、json-formatter、calendar、key-generator、ocr、http-client、asr、openclaw、help、change-password —— 统一工具页外壳（导航栏、输入框、按钮、卡片、空态/加载态）。
- **4 分包**：package-media（图片/视频下载）、package-docs（MarkItDown/Markdown 编辑器）、package-learning（课程平台列表+详情、技术内容列表+详情）、package-stats（Token 用量）。
- 首页与 profile 使用 `navigationStyle: custom`（品牌化大标题，需处理状态栏高度）；其余页面保留原生导航栏（`navigationBarBackgroundColor` 配品牌暗色、白字）。
- 工具页只换"壳"，不动业务逻辑与接口调用。

## 9. 实施阶段概览

| 阶段 | 内容 | 依赖 |
|---|---|---|
| ① | Web token 升级（primitive+玻璃组+亮色冷调）+ 字体修复 + `glass.css` | 无 |
| ② | Web 基础组件 18 个 + `/dev/components` 更新 | ① |
| ③ | Header/⌘K/Footer/首页/ToolCard | ② |
| ④ | 市场/课程/技术内容/账户/登录注册 | ② |
| ⑤ | 工作区 + 工具页外壳 + 硬编码清理 | ② |
| ⑥ | Admin 全套 | ② |
| ⑦ | H5：底部 Tab 栏 + 全站响应式核查 | ③ |
| ⑧ | 小程序基础：token 管道修复 + tabBar/导航/图标字体/ToolCard | ①（仅需 tokens 定稿） |
| ⑨ | 小程序主包页面 → 分包页面 | ⑧ |

①定稿后 ⑧ 即可并行启动；Web 各阶段与小程序阶段相互独立。

## 10. 验证与验收标准

- **每阶段**：`cd frontend && npm run build` + 类型检查通过；小程序阶段 `cd mini-program && npm run build:weapp` 构建通过（类型检查如可独立运行则一并执行）。
- **视觉回归基准**：`/dev/components` 验收页（token 色卡/字号/组件样例），四组合走查：**亮/暗 × 桌面(1280+)/移动(390px)**。
- **小程序验收**：微信开发者工具逐页走查（按 §8.4 清单），提供自检清单（含降级观感：开发者工具切"不支持 backdrop-filter"验证基线）。
- **冒烟回归**：登录→首页→打开工具→工作区→Admin 关键路径各一遍，确认零功能影响。
- **管道检查**：tokens 变更后生成脚本重跑、`_tokens.scss` 与 CSS 一致（纳入实施计划 DoD）。

## 11. 风险与对策

| 风险 | 对策 |
|---|---|
| 全站 palette 类清理面大（约 213 处） | 按阶段⑤分文件清理，视觉走查护航；非重点文件允许后续迭代 |
| 小程序玻璃兼容性 | §8.3 渐进增强，基线观感保底 |
| 亮色主题改冷调可能影响既有亮色审美 | 亮色由 mockup 确认后再全量铺开（阶段①产出对照截图给用户确认） |
| token 生成脚本解析能力有限（现只解析 `:root`/`[data-theme]`） | 玻璃 rgba 值均为简单声明可解析；复杂渐变在两端各自定义、以规范文档对齐 |
| ⌘K 面板自研复杂度 | 仅做搜索+跳转（工具/页面），不做命令注册中心，控制范围 |

## 12. 设计稿记录

头脑风暴阶段浏览器 mockup（已确认稿）存档于 `.superpowers/brainstorm/33-1789180499/content/`：`visual-language.html`（视觉方向 A）、`mobile-nav.html`（M1）、`admin-workspace.html`（Admin/工作区）。
