# 阶段⑥–⑦ 延后项与裁决记录（阶段⑧⑨ 及后续继承清单）

> 来源：阶段⑥–⑦ 执行（10 任务 + 终审 + 修复波次，13 提交 `38411226..32ed17b6`）。终审结论：可合并，2 项标准化漏网已修复并复验（`32ed17b6`）。工作区已清理。

## 合并前已修复（commit 32ed17b6）

- AdminLayout 启动 spinner → Admin 域标准类串
- QuotaManagementTab 空态 → glass-card + Inbox 图标（对齐标准空态模式）

## 建议独立跟踪的功能/产品项（与样式无关，勿混入样式分支）

1. **后端**：课程详情 `view_count` UPDATE 缺事务提交 → 行锁阻塞事件循环（phase4-5 已记录，仍未修）
2. **前端**：GUI 注册提交不生效（AuthModal 双面板既有问题）；TechContent 点赞/收藏无 onClick（存量，补 handler 属业务变更需立项）
3. **后端 API**：市场 / OpenSpecCourse 404、LLM 流式 500
4. **存量 bug**：TechContentDetailPage `reading_time` → `readingTime`（1 行）
5. **测试账号清理**：t15smoke / t9walktest / probe-noop / t14smoke2 / t67walktest（本地 dev 库）
6. **移动端访客点"我的"**：未登录进入 /account-settings 会弹错误 toast（存量行为，需产品决策登录引导）
7. **CI 留证**：合并后干净环境跑 `npm ci && npm run build`（42ad1721 的 lockfile 重生成含 @svta peer 移除与 dev 翻转，留证排除风险）

## 后续小专项（重构/增强，非缺陷）

- AdminLayout 抽屉 JSX 与桌面侧栏重复约 40 行 → 抽 `renderAdminMenu()`，顺带补 `role="dialog"`/`aria-modal`/focus trap
- MobileTabBar TABS 收敛进 `lib/navigation.ts`（profile key 同步迁移；需同步 Footer 语义，单独小 PR）
- 按钮语义变体专项：用户管理"添加用户"（bg-accent 纯色）vs MCP"添加 Server"（btn-primary）等风格统一；Dashboard 数字渐变统一（from-accent-secondary to-accent vs --gradient-brand）
- CategoryTabs 触控高度 40px vs 规格 44px：触控专项对齐或在 design.md §7 记录豁免
- Toast 主题联动范式统一：未来可切 `useTheme().resolved`（与 MetricsPanel MutationObserver 等价，二选一统一）
- theme.tsx 非法存储值白名单（透传为既有边缘缺陷）

## 关键技术备忘（追加，继承 phase3/4-5 全部备忘）

- 玻璃 chip 激活标准串（全站 4 处同构）：`text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)] border-transparent hover:border-transparent`（Button variant 上需补 border 占位 + hover:border-transparent 压 outline 残留）
- Admin 域标准 spinner：`h-8 w-8 rounded-full border-2 border-accent border-t-transparent animate-spin`；标准空态：glass-card 容器 + lucide Inbox
- tailwind accent 组无 `primary` 子键 → `text-accent-primary` 不生成 CSS，必须写 `text-accent`（Hero 漏网教训，grep 全 src 已零残留）
- Admin 移动抽屉模式：桌面侧栏 `hidden lg:flex` + sticky 管理条（lg:hidden glass-panel）+ fixed 玻璃抽屉（z-50 > Header z-40）+ 遮罩
- 底部 Tab 栏挂 Layout 层（isImmersion false 才渲染），/admin 与 /login 天然排除；Footer pb-24 md:pb-10 防遮挡
- 清零 grep 白名单（当前全 src）：markdownEditor 63 / TimeTravel 28 / DevComponents 8 / useMarkdownPreview 5 / iconTint.test 4 / mermaidRenderer 2 / iconTint 2 / Toast 1（styles/、glass.css、tint、Badge/JsonFormatter 语义 rgba 不在校验范围）
