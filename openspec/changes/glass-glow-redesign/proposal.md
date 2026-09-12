# 变更提案：玻璃光晕（Glass Glow）全站改版

## 为什么改

用户反馈全站（Web/H5/小程序）视觉"不高端、缺乏设计感"。调研确认三端各有一套不一致的样式来源：Web 已有 token 体系但落地覆盖率低（约 213 处硬编码 palette 类）；小程序用信任蓝 + emoji 图标；token 生成管道（Web → 小程序）输出路径已断裂。

## 改什么

1. **统一设计系统**：以 `frontend/src/styles/tokens/` 为单一来源，建立 primitive → semantic 两层 token 与玻璃工具类（`glass.css` / `_glass.scss`），Web 与小程序双端消费，主题可扩展（新增主题 = 一组 semantic 覆盖 + 重跑生成脚本）。
2. **Web 全站改版**：视觉语言定为「玻璃光晕」（毛玻璃卡片 + 光晕背景 + 紫蓝渐变），覆盖 Header/⌘K 命令面板/首页/工具卡/市场/课程/技术内容/账户/登录/工作区/Admin，硬编码颜色 token 化。
3. **H5 适配**：md 以下底部玻璃 Tab 栏（M1 方案）、触控目标 ≥44px、Admin 移动端抽屉化。
4. **小程序改版**：主包 14 页 + 4 分包全量换肤，去 emoji 图标（iconfont），tabBar 原生换肤，玻璃 `@supports` 降级。

## 影响范围

- 纯视觉/样式变更：不改业务逻辑、API、路由、后端。
- 新增依赖：无（⌘K 命令面板基于现有 Radix Dialog 自研）。
- 涉及目录：`frontend/src/styles/`、`frontend/src/components/**`、`frontend/index.html`、`frontend/tailwind.config.js`、`mini-program/src/**`、`frontend/scripts/generate-miniapp-tokens.js`。

## 详细设计

见同目录 [design.md](./design.md)。实施计划见 [tasks.md](./tasks.md)（分阶段：本文件当前版本为阶段①–③详细计划，④–⑨ 于前置阶段落地后续写）。
