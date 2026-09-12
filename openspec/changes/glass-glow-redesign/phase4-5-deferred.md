# 阶段④–⑤ 延后项与裁决记录（阶段⑥⑦ 继承清单）

> 来源：阶段④–⑤ 执行过程（14 任务 + 终审 + 修复波次，15 提交 `1f5056f1..92c6880e`）。终审结论：可合并，4 项合并前修复已落地（`92c6880e`）并复验。执行工作区已清理。

## ⚠️ 走查意外捕获的真实功能缺陷（与改版无关，必须单独跟踪修复）

1. **后端**：课程详情 `view_count` UPDATE 存在不提交事务路径 → 持有 `course_statistics` 行锁 → 后续请求永久等锁并阻塞事件循环（后端整体冻结；定位在 `backend` 课程详情接口，需补事务提交/连接池释放）
2. **前端**：GUI 注册提交不生效（AuthModal 双面板既有问题，Task 9/14 两次走查均复现）
3. **后端 API 缺失**：`/api/marketplace/agents` 404（市场页无数据）、OpenSpecCourse 后端 API 404、产品经理 Agent LLM 流式 500
4. **存量运行时 bug**：`TechContentDetailPage.tsx:170` `content.reading_time` 应为 `readingTime`（1 行修复，阅读时长显示异常）
5. **测试账号清理**：本地库留有 t15smoke / t9walktest / probe-noop / t14smoke2，列入清理清单

## 合并前已修复（commit 92c6880e）

- TraceViewer StepRow 判分底色 2 处 rgba → `bg-danger/10` / `bg-warning/10`
- MessagePanel 2 处 `placeholder-slate-500` → `placeholder-ink-faint`（白名单声明遗漏的漏网）
- FilePanel `divide-slate-700` → `divide-border`；DeviceManagerModal `accent-blue-600` → `accent-primary`

## 延后到阶段⑥（Admin 域）

- Admin 域 palette 残留约 23 行清零（QuotaManagementTab `accent-cyan-500` 等）
- ImportExportDialog `bg-success text-ink` 亮字亮底对比度（改版前既有，随按钮语义变体处理）
- JsonFormatter `:140`、Badge 语义 rgba 等 3 处既有 rgba 任意值（重审留档，属设计规格内）

## 延后到阶段⑦（H5 响应式）

- 学习页移动端横向溢出（`w-64` 进度块 + `w-80` 侧栏，改版前既有布局缺陷）
- CategoryTabs 非激活态补 `hover:bg-glass-bg`（与 chip 家族统一）

## 延后小项（任意阶段顺手）

- RichTextEditor blockquote `bg-info/10`→`rgb(var(--accent-cyan))`（#06b6d4 原是 cyan-500，现 info 是 blue，色相漂移；`:598` 注释"同源色"说法错误需一并改）
- MarkdownEditor 固定深底域 token 混用（待"代码域底 token"立项统一，勿单点改）
- MetricsPanel `readChartColors` 可加字面量兜底（token 读取失败时 `stroke=""` 折线不可见，概率极低）
- SpecEditor prose 串补 `prose-a:text-accent`、模式 chip 补 focus-visible 环；prose 容器 `text-ink/80` 双写不统一（建议统一为带）
- QuizView 判分态注释与实现出入；theme.tsx 非法存储值白名单；JSDoc 硬编码事件名 2 处
- **清零校验 grep 前缀扩展**：`bg|text|border|from|via|to|ring|divide|placeholder|accent|decoration|fill|stroke`（防 divide-/placeholder-/accent- 盲区复发），沉淀为脚本纳入阶段⑥ DoD

## 无需处理（裁决记录）

- 侧栏 glass-panel 全高导航轨模式（阶段④确立，全分支 9 消费点已统一）；CTA 阴影常驻（设计系统统一行为）
- TimeTravel 未挂路由、ui/Toast 无引用、DevComponentsPage iconTint 测试输入、xterm/recharts/代码固定深底（HtmlPreview/FileTree/MarkItDown/SystemMonitor/cursorThemes）= 白名单
- FOUC 内联脚本对非法值回退 dark 与 theme.tsx 透传不一致（应用不可达路径，视觉一致）

## 关键技术备忘（阶段⑥⑦⑧⑨ 直接引用）

- 继承 phase3-deferred.md 全部备忘（shadow 类型提示 / gradient-border rgb() 包装 / glass.css 导入顺序 / i18n 类型机制 / 基线数值）
- btn-primary 的 background-image 无法被 tailwind-merge 覆盖，需改渐变底时用 `variant="secondary"` 打底（Task 11 确立）
- 全高导航轨 = `glass-panel rounded-none border-y-0 border-l-0`；玻璃 chip 激活 = `text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)]`（+`hover:border-transparent` 压 outline 变体）
- prose 双主题标准串：`prose dark:prose-invert prose-headings:text-ink prose-p:text-ink-muted prose-a:text-accent`
- recharts 颜色必须 getComputedStyle 直读（图例/悬停点走 SVG attribute 通道），主题联动用 MutationObserver 监听 `data-theme`；`--chart-*` 终端 token 必须完整色值（rgb(var(--p-*)) 包装）
- 走查环境注意：后端 view_count 行锁可能复发（访问课程详情前留意），市场页无数据
