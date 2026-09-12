# 阶段①–③ 延后项与裁决记录（阶段④ 继承清单）

> 来源：阶段①–③ 执行过程（15 任务 + 终审）中记录的延后 Minor 与裁决。执行工作区已清理，本文件为持久化记录。终审（commit 2ebe5318..d52c7a99，22 提交）结论：可合并，合并前两项已修复（d52c7a99）。

## 已修复（终审合并前项，commit d52c7a99）

- 品牌发光阴影三处硬编码 → 统一 `var(--shadow-glow-accent)`（亮色降档生效）；组件处需 `shadow-[shadow:var(...)]` 类型提示（Tailwind 3.4.19 行为，`shadow-[var(...)]` 会被误判为阴影颜色）
- Footer 栏3 硬编码中文 → i18n 化（`footer.copyright` 更新为 © 2026、新增 `footer.tagline`，zh/en 同步）

## 延后到阶段④（建议第一批处理）

1. **FOUC 内联引导脚本**（优先级最高）：`index.html` 加 pre-paint 内联脚本按 localStorage 写 `data-theme`，消除亮色用户刷新闪暗（主题持久化修复后该现象变为可见）
2. **路由单一来源**：抽 `lib/navigation.ts`，吃掉 Header NAV_ITEMS / Footer NAV_ITEMS / commandPalette PAGE_ITEMS 三处重复 + `open-command-palette` 事件名常量三处重复
3. **ToastContext 死代码清理**：`typeColors.bg` 失去消费者、`sonner-toast-dark` 死类名（5 分钟）
4. **模糊强度统一**：glass-card 14 / glass-panel 18.2 / Tooltip 与 sonner 12px → 统一到 `--glass-blur` 体系（先定夺 panel 1.3 倍是否有意）
5. **Admin 密集页玻璃卡对比度实测**：OssManagement / LLMConfigs / SystemMonitor 系列是 ui/Card 最大消费方，作为阶段④显式验收条目；对比度不足处启用已备好的 Card `variant="solid"`

## 阶段④+ 顺手项

- CoursesPage 搜索框内层 input 固定 `w-80`（<352px 溢出）→ 改 `w-full sm:w-80`
- Badge default 与 secondary 渲染相同（可给 default 加微弱 accent 描边）；Badge 语义色 rgba 与 tint 色板同值不同源（统一到 token）
- Hero CTA 原生 button 补 focus-visible 环（CategoryTabs 已补）
- Tabs 非激活 hover 反馈弱 → `hover:bg-glass-bg-strong`
- en-US `heroTitle: 'One-stop '` 尾随空格 hack → 改 markup 拼接
- 阶段⑤ 硬编码清理范围：存量 `bg-blue-500` 等静态类（Admin/McpServers 等页面自用，非 tint 消费点）

## 无需处理（裁决记录）

- MarketplacePage 回退色 blue→violet：tint 体系回退色即 violet，测试固化，设计如此
- --border-default/--border-strong 未 primitive 化、typography.css 保留 HarmonyOS/Noto Serif 字体族名：输出等价/本地 fallback 无网络开销
- index.html 末尾换行符、报告计数笔误：cosmetic
- t15smoke 测试账号：仅本地开发库，登记到测试账号清理清单即可
- 主题持久化修复（6bb82de8）与 Badge 语义色恢复（be403f8f）：终审复核保留，均为正确纠偏

## 关键技术备忘（后续阶段直接引用）

- Tailwind 3.4.19 任意值引用 CSS 变量阴影必须带类型提示：`shadow-[shadow:var(--x)]`
- gradient-border 类的内容层必须 `rgb(var(--bg-surface-1))` 包裹（RGB 三元组 token 不能裸进 linear-gradient）
- `glass.css` / `index.css` 导入顺序在 `@tailwind utilities` 之前 → 组件显式 `bg-*` 工具类可覆盖玻璃底（cascade 依据）
- i18n 类型机制：`Translations = typeof zhCN` + `Record<Language, Translations>`，en 缺 key 编译报错
- 基线：tsc 71 存量错（Admin 业务代码）、vitest 4 存量失败文件（monaco/K8s mock）——只要求不劣化
- 小程序阶段注意：`generate-miniapp-tokens.js` 输出路径需修正为 `mini-program/src/styles/`；玻璃降级写法参照 `glass.css` 的 `@supports` 思路；勿从 Task 4 旧简报复制 gradient-border 代码（用修复后的现行 glass.css）
