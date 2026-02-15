# SpecFlow Lab - 前端设计文档

> **文档版本**: v1.0  
> **最后更新**: 2024-02-13  
> **状态**: ✅ 设计规范已定义  
> **文档类型**: Frontend Design System  
> **技术栈**: React + TypeScript + Tailwind CSS + Framer Motion

---

## 文档目录

1. [设计系统概述](#一设计系统概述)
2. [设计原则](#二设计原则)
3. [色彩系统](#三色彩系统)
4. [字体与排版](#四字体与排版)
5. [间距与布局](#五间距与布局)
6. [组件库规范](#六组件库规范)
7. [页面设计规范](#七页面设计规范)
8. [动画与交互](#八动画与交互)
9. [响应式设计](#九响应式设计)
10. [可访问性规范](#十可访问性规范)
11. [技术实现指南](#十一技术实现指南)
12. [设计Token](#十二设计token)

---

# 一、设计系统概述

## 1.1 设计系统名称

**SpecFlow Lab Design System (SLDS)**

## 1.2 设计系统目标

为SpecFlow Lab演示平台提供一套完整、一致、可扩展的视觉设计规范，确保：

- ✅ **一致性**: 跨页面、跨组件保持统一的视觉语言
- ✅ **专业性**: 体现技术分享平台的专业感和现代感
- ✅ **沉浸感**: 深色主题设计，减少视觉疲劳，突出演示内容
- ✅ **可扩展性**: 支持未来功能扩展和新组件添加
- ✅ **开发效率**: 提供可直接使用的Tailwind配置和组件代码

## 1.3 设计理念

### 核心设计关键词

| 关键词 | 描述 | 应用 |
|--------|------|------|
| **科技感** | 深色主题、发光效果、代码高亮 | 整体视觉风格 |
| **专业性** | 简洁布局、清晰层级、精确间距 | 界面结构 |
| **流畅性** | 平滑动画、60fps性能、即时反馈 | 交互体验 |
| **沉浸感** | 全屏模式、深色背景、内容聚焦 | 演示模式 |
| **现代感** | 圆角设计、微妙阴影、渐变效果 | 视觉细节 |

### 设计哲学

```
内容优先 > 视觉效果 > 装饰元素

演示者体验 = 观众体验 = 开发者体验
```

## 1.4 设计系统架构

```
SpecFlow Lab Design System
├── Foundation (基础)
│   ├── Colors (色彩)
│   ├── Typography (字体)
│   ├── Spacing (间距)
│   ├── Shadows (阴影)
│   └── Animation (动画)
├── Components (组件)
│   ├── Buttons (按钮)
│   ├── Cards (卡片)
│   ├── Forms (表单)
│   ├── Navigation (导航)
│   ├── Modals (模态框)
│   └── Animation Components (动画组件)
├── Patterns (模式)
│   ├── Page Layouts (页面布局)
│   ├── Content Structures (内容结构)
│   └── Interaction Patterns (交互模式)
└── Guidelines (指南)
    ├── Accessibility (可访问性)
    ├── Responsive Design (响应式)
    └── Best Practices (最佳实践)
```

---

# 二、设计原则

## 2.1 核心设计原则

### 原则1：内容为王 (Content First)

**描述**: 所有设计决策都应服务于内容展示，而非装饰。

**实践**:
- 演示区域占据最大视觉空间
- 控制元素精简且不干扰内容
- 深色背景突出前景内容
- 字体选择优先保证代码可读性

### 原则2：渐进式披露 (Progressive Disclosure)

**描述**: 根据用户当前任务和上下文，逐步展示信息和功能。

**实践**:
- 默认隐藏高级功能
- 编辑模式下才显示完整工具栏
- 步骤列表可折叠
- 设置面板分层级组织

### 原则3：即时反馈 (Immediate Feedback)

**描述**: 用户的每个操作都应得到即时、明确的反馈。

**实践**:
- 按钮悬停状态 (150ms过渡)
- 操作成功/失败的Toast提示
- 加载状态显示Skeleton或Spinner
- 实时预览编辑效果

### 原则4：一致性 (Consistency)

**描述**: 相同的功能使用相同的视觉语言和交互模式。

**实践**:
- 统一的颜色语义
- 一致的间距系统
- 标准化的组件尺寸
- 统一的动画时长和缓动

### 原则5：无障碍优先 (Accessibility First)

**描述**: 设计必须考虑所有用户，包括使用辅助技术的用户。

**实践**:
- 颜色对比度 ≥ 4.5:1
- 键盘可完全操作
- 屏幕阅读器友好
- 支持 prefers-reduced-motion

---

# 三、色彩系统

## 3.1 色彩系统概述

采用**深色主题 (Dark Theme)** 作为主要配色方案，原因：
- 技术分享长时间观看，深色减少视觉疲劳
- 突出代码和内容，符合开发者习惯
- 营造专业、沉浸的演示氛围
- 支持发光效果和渐变效果

## 3.2 主色调

### Primary (主色)

| Token | Hex | RGB | 用途 |
|-------|-----|-----|------|
| `--color-primary-50` | `#EFF6FF` | rgb(239, 246, 255) | 最浅背景 |
| `--color-primary-100` | `#DBEAFE` | rgb(219, 234, 254) | 浅色背景 |
| `--color-primary-200` | `#BFDBFE` | rgb(191, 219, 254) | 禁用状态 |
| `--color-primary-300` | `#93C5FD` | rgb(147, 197, 253) | 高亮 |
| `--color-primary-400` | `#60A5FA` | rgb(96, 165, 250) | 悬停状态 |
| `--color-primary-500` | `#3B82F6` | rgb(59, 130, 246) | 主按钮 |
| `--color-primary-600` | `#2563EB` | rgb(37, 99, 235) | 默认主色 |
| `--color-primary-700` | `#1D4ED8` | rgb(29, 78, 216) | 按下状态 |
| `--color-primary-800` | `#1E40AF` | rgb(30, 64, 175) | 深色强调 |
| `--color-primary-900` | `#1E3A8A` | rgb(30, 58, 138) | 最深 |

**主色使用规则**:
- 主按钮: `--color-primary-600`
- 按钮悬停: `--color-primary-700`
- 链接文字: `--color-primary-400`
- 光晕效果: `--color-primary-500` 20%透明度

### Secondary (次要色)

| Token | Hex | 用途 |
|-------|-----|------|
| `--color-secondary-400` | `#34D399` | 成功提示 |
| `--color-secondary-500` | `#10B981` | 成功状态 |
| `--color-secondary-600` | `#059669` | 成功深色 |

### Accent (强调色)

| Token | Hex | 用途 |
|-------|-----|------|
| `--color-accent-purple` | `#8B5CF6` | 紫色调强调 |
| `--color-accent-cyan` | `#06B6D4` | 信息提示 |
| `--color-accent-orange` | `#F97316` | 警告/CTA |
| `--color-accent-pink` | `#EC4899` | 特殊强调 |

## 3.3 背景色

| Token | Hex | 用途 |
|-------|-----|------|
| `--color-bg-base` | `#0F172A` | 最深背景 (页面背景) |
| `--color-bg-surface` | `#1E293B` | 卡片背景 |
| `--color-bg-elevated` | `#334155` | 悬浮层、边框 |
| `--color-bg-overlay` | `rgba(15, 23, 42, 0.8)` | 模态框遮罩 |
| `--color-bg-input` | `#0F172A` | 输入框背景 |

## 3.4 文字色

| Token | Hex | 用途 | 对比度 |
|-------|-----|------|--------|
| `--color-text-primary` | `#F8FAFC` | 主要文字 | 15.8:1 ✅ |
| `--color-text-secondary` | `#94A3B8` | 次要文字 | 8.2:1 ✅ |
| `--color-text-muted` | `#64748B` | 禁用/提示 | 4.6:1 ✅ |
| `--color-text-placeholder` | `#475569` | 占位符 | 3.2:1 ⚠️ |

**对比度说明**: 所有主要文字对比度均符合WCAG AA标准 (≥4.5:1)

## 3.5 功能色 (Semantic Colors)

| Token | Hex | 用途 |
|-------|-----|------|
| `--color-success` | `#10B981` | 成功、完成、正常 |
| `--color-warning` | `#F59E0B` | 警告、注意 |
| `--color-error` | `#EF4444` | 错误、失败 |
| `--color-info` | `#06B6D4` | 信息、提示 |

### 功能色透明度变体

```css
--color-success-bg: rgba(16, 185, 129, 0.1);
--color-warning-bg: rgba(245, 158, 11, 0.1);
--color-error-bg: rgba(239, 68, 68, 0.1);
--color-info-bg: rgba(6, 182, 212, 0.1);
```

## 3.6 渐变方案

### Hero渐变

```css
background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%);
```

**用途**: 
- 着陆页Hero区域
- 品牌标识背景
- 主要CTA按钮

### 背景渐变

```css
background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%);
```

**用途**:
- 页面背景
- 卡片微妙渐变

### 卡片光晕

```css
box-shadow: 0 0 20px rgba(37, 99, 235, 0.3);
```

**用途**:
- 激活状态卡片
- 当前播放步骤高亮
- 重要元素强调

### 边框渐变

```css
border-image: linear-gradient(135deg, #3B82F6, #8B5CF6) 1;
```

**用途**:
- 特殊卡片边框
- 选中状态指示

## 3.7 色彩使用模式

### 模式1：层级结构

```
页面背景: --color-bg-base (#0F172A)
    ↓
卡片背景: --color-bg-surface (#1E293B)
    ↓
输入框背景: --color-bg-input (#0F172A)
    ↓
文字: --color-text-primary (#F8FAFC)
```

### 模式2：交互状态

```
默认: --color-primary-600 (#2563EB)
悬停: --color-primary-700 (#1D4ED8) + translateY(-2px)
按下: --color-primary-800 (#1E40AF)
禁用: --color-bg-elevated (#334155) + opacity 0.5
```

### 模式3：代码展示

```
代码背景: --color-bg-base (#0F172A)
代码边框: --color-bg-elevated (#334155)
代码文字: --color-text-primary (#F8FAFC)
语法高亮: 根据语言使用不同语义色
```

---

# 四、字体与排版

## 4.1 字体系统概述

采用**双字体系统**:
- **界面字体**: Inter - 现代、清晰、适合UI
- **代码字体**: JetBrains Mono - 等宽、易读、适合代码展示

## 4.2 字体族

### 界面字体 (UI Font)

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
```

**特点**:
- 优秀的屏幕可读性
- 丰富的字重选择 (100-900)
- 优秀的数字显示
- 支持中文回退

### 代码字体 (Code Font)

```css
font-family: 'JetBrains Mono', 'Fira Code', 'Source Code Pro', 'Consolas', monospace;
```

**特点**:
- 等宽设计，代码对齐
- 连字支持 (ligatures)
- 区分相似字符 (0/O, 1/l/I)
- 适合长时间代码阅读

### 加载方式

```html
<!-- Google Fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

## 4.3 字体规格

### 显示文字 (Display)

| 样式 | 桌面端 | 移动端 | 行高 | 字重 | 用途 |
|------|--------|--------|------|------|------|
| Display Large | 48px | 32px | 1.2 | 700 | 着陆页Hero标题 |
| Display Medium | 36px | 28px | 1.2 | 700 | 页面大标题 |
| Display Small | 32px | 24px | 1.3 | 600 | 场景标题 |

### 标题文字 (Headings)

| 级别 | 桌面端 | 移动端 | 行高 | 字重 | 用途 |
|------|--------|--------|------|------|------|
| H1 | 30px | 24px | 1.3 | 600 | 页面标题 |
| H2 | 24px | 20px | 1.4 | 600 | 区块标题 |
| H3 | 20px | 18px | 1.4 | 500 | 小节标题 |
| H4 | 18px | 16px | 1.4 | 500 | 卡片标题 |
| H5 | 16px | 14px | 1.5 | 500 | 列表标题 |
| H6 | 14px | 13px | 1.5 | 500 | 小标题 |

### 正文文字 (Body)

| 样式 | 桌面端 | 移动端 | 行高 | 字重 | 用途 |
|------|--------|--------|------|------|------|
| Body Large | 18px | 16px | 1.7 | 400 | 重要正文 |
| Body | 16px | 14px | 1.6 | 400 | 默认正文 |
| Body Small | 14px | 13px | 1.5 | 400 | 次要文字 |
| Caption | 12px | 11px | 1.4 | 400 | 标签、提示 |

### 代码文字 (Code)

| 样式 | 字号 | 行高 | 字重 | 用途 |
|------|------|------|------|------|
| Code Block | 14px | 1.8 | 400 | 代码块 |
| Code Inline | 0.9em | inherit | 400 | 行内代码 |
| Code Comment | 12px | 1.6 | 400 | 代码注释 |

## 4.4 排版规范

### 行长度 (Line Length)

- **正文**: 每行45-75个字符 (最佳: 66字符)
- **代码**: 最大80-100字符 (符合编码规范)
- **标题**: 无限制，但建议不超过2行

### 段落间距

```css
/* 段落之间 */
p + p {
  margin-top: 1em;
}

/* 标题与内容之间 */
h2 + p, h3 + p {
  margin-top: 0.5em;
}

/* 区块之间 */
section + section {
  margin-top: 3rem;
}
```

### 代码展示排版

```css
/* 代码块 */
code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  line-height: 1.8;
  tab-size: 2;
}

/* 行内代码 */
code.inline {
  padding: 0.2em 0.4em;
  background: var(--color-bg-surface);
  border-radius: 4px;
  font-size: 0.9em;
}
```

## 4.5 语义化排版

### 用途映射

| 内容类型 | 字体 | 字号 | 颜色 |
|----------|------|------|------|
| 页面标题 | Inter | 30px | --color-text-primary |
| 步骤标题 | Inter | 24px | --color-text-primary |
| 讲解词 | Inter | 18px | --color-text-secondary |
| 正文 | Inter | 16px | --color-text-primary |
| 代码展示 | JetBrains Mono | 14px | --color-text-primary |
| 代码注释 | JetBrains Mono | 12px | --color-text-muted |
| 标签 | Inter | 12px | --color-text-muted |

---

# 五、间距与布局

## 5.1 间距系统

基于**4px网格系统**，所有间距都是4的倍数。

### 间距Token

| Token | 值 | Tailwind | 用途 |
|-------|------|----------|------|
| `space-0` | 0px | `p-0`, `m-0` | 无间距 |
| `space-1` | 4px | `p-1`, `m-1` | 图标间距 |
| `space-2` | 8px | `p-2`, `m-2` | 紧凑间距 |
| `space-3` | 12px | `p-3`, `m-3` | 小间距 |
| `space-4` | 16px | `p-4`, `m-4` | 默认间距 |
| `space-5` | 20px | `p-5`, `m-5` | 中等间距 |
| `space-6` | 24px | `p-6`, `m-6` | 组件间距 |
| `space-8` | 32px | `p-8`, `m-8` | 区块间距 |
| `space-10` | 40px | `p-10`, `m-10` | 大间距 |
| `space-12` | 48px | `p-12`, `m-12` | 大区块间距 |
| `space-16` | 64px | `p-16`, `m-16` | 页面间距 |
| `space-20` | 80px | `p-20`, `m-20` | 超大间距 |

### 间距使用模式

```
组件内部: space-3 ~ space-4 (12-16px)
组件之间: space-4 ~ space-6 (16-24px)
区块之间: space-8 ~ space-12 (32-48px)
页面边距: space-6 ~ space-16 (24-64px)
```

## 5.2 布局系统

### 断点系统

| 断点 | 宽度 | 描述 |
|------|------|------|
| `sm` | 640px | 大手机 |
| `md` | 768px | 平板 |
| `lg` | 1024px | 小型笔记本 |
| `xl` | 1280px | 桌面 |
| `2xl` | 1536px | 大屏幕 |

### 容器系统

| 容器 | 最大宽度 | 内边距 |
|------|----------|--------|
| `container-sm` | 640px | px-4 |
| `container-md` | 768px | px-6 |
| `container-lg` | 1024px | px-8 |
| `container-xl` | 1280px | px-12 |
| `container-full` | 100% | px-4 sm:px-6 lg:px-8 |

### 页面布局结构

#### Demo Player 页面布局

```
┌─────────────────────────────────────────────────────────┐
│                      Header (56px)                       │
├──────────┬──────────────────────────────┬───────────────┤
│          │                              │               │
│  Steps   │                              │   Notes       │
│  Panel   │      Animation Stage         │   Panel       │
│ (280px)  │         (flex: 1)            │   (320px)     │
│          │                              │               │
│          │                              │               │
├──────────┴──────────────────────────────┴───────────────┤
│                   Controls Bar (64px)                    │
└─────────────────────────────────────────────────────────┘
```

**布局规则**:
- 步骤面板: 固定宽度 280px
- 讲解面板: 固定宽度 320px
- 动画区域: 自适应剩余空间
- 最小高度: 60vh

#### CMS 编辑器页面布局

```
┌─────────────────────────────────────────────────────────┐
│                      Header (56px)                       │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│ Sidebar  │              Editor Area                     │
│ (240px)  │                                              │
│          │    ┌────────────────┬─────────────────┐     │
│          │    │   Form/Edit    │    Preview      │     │
│          │    │                │                 │     │
│          │    └────────────────┴─────────────────┘     │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

**布局规则**:
- 侧边栏: 固定宽度 240px
- 编辑器: 分屏或全屏模式
- 预览区: 最小宽度 400px

## 5.3 网格系统

### 12列网格

```css
.grid-12 {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 24px;
}

/* 响应式 */
@media (max-width: 768px) {
  .grid-12 {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}
```

### 常用网格模式

| 模式 | 桌面端 | 平板 | 手机 |
|------|--------|------|------|
| 2列 | `grid-cols-2` | `md:grid-cols-2` | `grid-cols-1` |
| 3列 | `grid-cols-3` | `md:grid-cols-2` | `grid-cols-1` |
| 4列 | `grid-cols-4` | `md:grid-cols-2` | `grid-cols-1` |
| 侧边栏+内容 | `grid-cols-[240px_1fr]` | `grid-cols-1` | `grid-cols-1` |

## 5.4 响应式布局策略

### 移动优先设计

```css
/* 基础样式 (移动端) */
.component {
  padding: 16px;
  font-size: 14px;
}

/* 平板 */
@media (min-width: 768px) {
  .component {
    padding: 24px;
    font-size: 16px;
  }
}

/* 桌面 */
@media (min-width: 1024px) {
  .component {
    padding: 32px;
  }
}
```

### 布局变化规则

| 元素 | 移动端 | 平板 | 桌面 |
|------|--------|------|------|
| **导航** | 汉堡菜单 | 侧边栏 | 顶部导航 |
| **Player布局** | 单栏堆叠 | 三栏 | 三栏 |
| **步骤面板** | 可折叠 | 固定 | 固定 |
| **字体大小** | 14px | 16px | 16px |
| **间距** | 16px | 24px | 32px |

---

# 六、组件库规范

## 6.1 组件库概述

**组件库名称**: SpecFlow UI  
**组件总数**: 40+ 组件  
**分类**: 基础组件、表单组件、展示组件、动画组件、布局组件

## 6.2 基础组件

### Button (按钮)

#### 按钮类型

| 类型 | 用途 | 视觉特征 |
|------|------|----------|
| **Primary** | 主要操作 | 蓝色背景、白色文字 |
| **Secondary** | 次要操作 | 透明背景、边框 |
| **Ghost** | 低强调操作 | 透明背景、无边框 |
| **Danger** | 危险操作 | 红色背景 |
| **Icon** | 图标按钮 | 仅图标、方形 |

#### 按钮尺寸

| 尺寸 | 高度 | 内边距 | 用途 |
|------|------|--------|------|
| **Small** | 32px | px-3 | 紧凑空间 |
| **Medium** | 40px | px-4 | 默认 |
| **Large** | 48px | px-6 | 强调 |

#### 按钮状态

```css
/* 默认状态 */
.btn-primary {
  background: var(--color-primary-600);
  color: white;
  border-radius: 8px;
  transition: all 150ms ease;
}

/* 悬停状态 */
.btn-primary:hover {
  background: var(--color-primary-700);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

/* 按下状态 */
.btn-primary:active {
  background: var(--color-primary-800);
  transform: translateY(0);
}

/* 禁用状态 */
.btn-primary:disabled {
  background: var(--color-bg-elevated);
  opacity: 0.5;
  cursor: not-allowed;
}

/* 加载状态 */
.btn-primary.loading {
  position: relative;
  color: transparent;
}

.btn-primary.loading::after {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
```

#### 按钮组

```css
.btn-group {
  display: inline-flex;
  border-radius: 8px;
  overflow: hidden;
}

.btn-group .btn {
  border-radius: 0;
}

.btn-group .btn:not(:first-child) {
  border-left: 1px solid rgba(255, 255, 255, 0.1);
}
```

### Card (卡片)

#### 卡片类型

| 类型 | 用途 | 特征 |
|------|------|------|
| **Default** | 通用内容容器 | 标准圆角、阴影 |
| **Hoverable** | 可点击卡片 | 悬停效果 |
| **Active** | 选中状态 | 边框高亮 |
| **Flat** | 简洁卡片 | 无边框、无阴影 |

#### 卡片结构

```jsx
<Card>
  <Card.Header>
    <Card.Title>标题</Card.Title>
    <Card.Description>描述</Card.Description>
  </Card.Header>
  <Card.Content>
    {/* 内容 */}
  </Card.Content>
  <Card.Footer>
    {/* 底部操作 */}
  </Card.Footer>
</Card>
```

#### 卡片样式

```css
.card {
  background: var(--color-bg-surface);
  border-radius: 12px;
  border: 1px solid transparent;
  overflow: hidden;
}

.card-hoverable:hover {
  border-color: var(--color-primary-600);
  box-shadow: 0 0 20px rgba(37, 99, 235, 0.2);
  transform: translateY(-4px);
  transition: all 200ms ease;
}

.card-active {
  border-color: var(--color-primary-600);
  box-shadow: 0 0 20px rgba(37, 99, 235, 0.3);
}
```

## 6.3 表单组件

### Input (输入框)

#### 输入框类型

| 类型 | 用途 |
|------|------|
| **Text** | 单行文本 |
| **Textarea** | 多行文本 |
| **Password** | 密码输入 |
| **Number** | 数字输入 |
| **Search** | 搜索输入 |
| **Select** | 下拉选择 |

#### 输入框状态

```css
.input {
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-elevated);
  border-radius: 8px;
  padding: 12px 16px;
  color: var(--color-text-primary);
  transition: all 150ms ease;
}

.input:focus {
  border-color: var(--color-primary-600);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  outline: none;
}

.input::placeholder {
  color: var(--color-text-placeholder);
}

.input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input.error {
  border-color: var(--color-error);
}

.input.error:focus {
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}
```

### Select (选择器)

```jsx
<Select>
  <Select.Trigger>
    <Select.Value placeholder="请选择..." />
  </Select.Trigger>
  <Select.Content>
    <Select.Item value="1">选项1</Select.Item>
    <Select.Item value="2">选项2</Select.Item>
  </Select.Content>
</Select>
```

### Checkbox & Radio

```css
.checkbox {
  width: 18px;
  height: 18px;
  border: 2px solid var(--color-bg-elevated);
  border-radius: 4px;
  background: var(--color-bg-input);
  transition: all 150ms ease;
}

.checkbox:checked {
  background: var(--color-primary-600);
  border-color: var(--color-primary-600);
}

.checkbox:focus {
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
}
```

## 6.4 导航组件

### Navigation (导航栏)

```jsx
<Navbar>
  <Navbar.Logo />
  <Navbar.Links>
    <Navbar.Link href="/">首页</Navbar.Link>
    <Navbar.Link href="/scenarios">场景</Navbar.Link>
    <Navbar.Link href="/templates">模板</Navbar.Link>
  </Navbar.Links>
  <Navbar.Actions>
    <Button>创建场景</Button>
    <UserMenu />
  </Navbar.Actions>
</Navbar>
```

#### 导航栏样式

```css
.navbar {
  height: 56px;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-bg-elevated);
  position: sticky;
  top: 0;
  z-index: 50;
}
```

### Sidebar (侧边栏)

```css
.sidebar {
  width: 240px;
  height: calc(100vh - 56px);
  background: var(--color-bg-surface);
  border-right: 1px solid var(--color-bg-elevated);
  overflow-y: auto;
}

.sidebar-item {
  padding: 12px 16px;
  border-radius: 8px;
  margin: 4px 8px;
  transition: all 150ms ease;
}

.sidebar-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.sidebar-item.active {
  background: rgba(37, 99, 235, 0.1);
  color: var(--color-primary-400);
}
```

### Breadcrumb (面包屑)

```jsx
<Breadcrumb>
  <Breadcrumb.Item href="/">首页</Breadcrumb.Item>
  <Breadcrumb.Separator />
  <Breadcrumb.Item href="/scenarios">场景</Breadcrumb.Item>
  <Breadcrumb.Separator />
  <Breadcrumb.Item active>我的场景</Breadcrumb.Item>
</Breadcrumb>
```

## 6.5 展示组件

### Avatar (头像)

| 尺寸 | 用途 |
|------|------|
| 24px | 列表项 |
| 32px | 卡片 |
| 40px | 导航栏 |
| 64px | 个人资料 |

```css
.avatar {
  border-radius: 50%;
  object-fit: cover;
  background: var(--color-bg-elevated);
}

.avatar-group {
  display: flex;
}

.avatar-group .avatar {
  border: 2px solid var(--color-bg-base);
  margin-left: -8px;
}

.avatar-group .avatar:first-child {
  margin-left: 0;
}
```

### Badge (徽章)

```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
}

.badge-primary {
  background: rgba(37, 99, 235, 0.1);
  color: var(--color-primary-400);
}

.badge-success {
  background: rgba(16, 185, 129, 0.1);
  color: var(--color-success);
}

.badge-warning {
  background: rgba(245, 158, 11, 0.1);
  color: var(--color-warning);
}

.badge-error {
  background: rgba(239, 68, 68, 0.1);
  color: var(--color-error);
}
```

### Tooltip (提示框)

```css
.tooltip {
  position: absolute;
  padding: 8px 12px;
  background: var(--color-bg-elevated);
  border-radius: 6px;
  font-size: 12px;
  white-space: nowrap;
  z-index: 100;
}

.tooltip::before {
  content: '';
  position: absolute;
  width: 8px;
  height: 8px;
  background: var(--color-bg-elevated);
  transform: rotate(45deg);
}
```

### Progress (进度条)

```css
.progress {
  height: 8px;
  background: var(--color-bg-elevated);
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--color-primary-600);
  border-radius: 4px;
  transition: width 300ms ease;
}
```

## 6.6 动画组件

### FadeIn (淡入动画)

```jsx
<FadeIn duration={300} delay={0}>
  <Content />
</FadeIn>
```

```css
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.fade-in {
  animation: fadeIn 300ms ease forwards;
}
```

### SlideUp (上滑动画)

```jsx
<SlideUp duration={400} delay={100}>
  <Content />
</SlideUp>
```

```css
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.slide-up {
  animation: slideUp 400ms cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
}
```

### Scale (缩放动画)

```jsx
<Scale duration={300}>
  <Content />
</Scale>
```

### StaggerChildren (交错动画)

```jsx
<StaggerChildren staggerDelay={100}>
  {items.map(item => (
    <StaggerItem key={item.id}>
      <Card>{item.content}</Card>
    </StaggerItem>
  ))}
</StaggerChildren>
```

## 6.7 反馈组件

### Toast (轻提示)

```jsx
toast.success('操作成功！');
toast.error('操作失败，请重试');
toast.warning('请注意检查');
toast.info('新消息');
```

#### Toast样式

```css
.toast {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--color-bg-surface);
  border-radius: 8px;
  border: 1px solid var(--color-bg-elevated);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
}

.toast-success {
  border-left: 4px solid var(--color-success);
}

.toast-error {
  border-left: 4px solid var(--color-error);
}
```

### Modal (模态框)

```jsx
<Modal open={isOpen} onClose={handleClose}>
  <Modal.Header>
    <Modal.Title>确认删除</Modal.Title>
  </Modal.Header>
  <Modal.Content>
    <p>确定要删除这个场景吗？此操作无法撤销。</p>
  </Modal.Content>
  <Modal.Footer>
    <Button variant="ghost" onClick={handleClose}>取消</Button>
    <Button variant="danger" onClick={handleConfirm}>删除</Button>
  </Modal.Footer>
</Modal>
```

#### Modal样式

```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--color-bg-surface);
  border-radius: 12px;
  border: 1px solid var(--color-bg-elevated);
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  padding: 24px 24px 0;
}

.modal-content {
  padding: 24px;
}

.modal-footer {
  padding: 0 24px 24px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
```

### Skeleton (骨架屏)

```jsx
<Skeleton className="h-4 w-3/4" />
<Skeleton className="h-4 w-1/2" />
<Skeleton className="h-32 w-full" />
```

```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--color-bg-elevated) 0%,
    rgba(255, 255, 255, 0.05) 50%,
    var(--color-bg-elevated) 100%
  );
  background-size: 200% 100%;
  border-radius: 4px;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}
```

---

# 七、页面设计规范

## 7.1 页面类型

### 页面分类

| 页面类型 | 描述 | 示例 |
|----------|------|------|
| **Landing** | 营销页面 | 首页 |
| **Dashboard** | 数据仪表板 | 场景列表 |
| **Editor** | 编辑器 | 场景编辑 |
| **Player** | 演示播放器 | Demo播放 |
| **Settings** | 设置页面 | 用户设置 |
| **Auth** | 认证页面 | 登录/注册 |

## 7.2 Demo Player 页面

### 页面结构

```
Player Layout
├── Header (56px)
│   ├── Logo
│   ├── Scenario Title
│   └── Actions (Share, Fullscreen)
├── Main Content
│   ├── Steps Panel (280px, collapsible)
│   ├── Animation Stage (flex: 1)
│   │   ├── Step Content
│   │   └── Animation Canvas
│   └── Notes Panel (320px, collapsible)
└── Controls Bar (64px)
    ├── Playback Controls
    ├── Progress Bar
    └── Settings
```

### 步骤面板 (Steps Panel)

```jsx
<StepsPanel>
  <StepsPanel.Header>
    <h3>步骤</h3>
    <span>{currentStep} / {totalSteps}</span>
  </StepsPanel.Header>
  <StepsPanel.List>
    {steps.map((step, index) => (
      <StepItem
        key={step.id}
        step={step}
        index={index}
        isActive={currentStep === index}
        isCompleted={index < currentStep}
        onClick={() => goToStep(index)}
      />
    ))}
  </StepsPanel.List>
</StepsPanel>
```

#### 步骤项样式

```css
.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 150ms ease;
}

.step-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.step-item.active {
  background: rgba(37, 99, 235, 0.1);
  border: 1px solid var(--color-primary-600);
}

.step-item.completed {
  opacity: 0.6;
}

.step-number {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-bg-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 500;
}

.step-item.active .step-number {
  background: var(--color-primary-600);
  color: white;
}

.step-item.completed .step-number {
  background: var(--color-success);
  color: white;
}
```

### 动画舞台 (Animation Stage)

#### 舞台区域

```css
.animation-stage {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: var(--color-bg-base);
  position: relative;
  overflow: hidden;
}

.animation-stage::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 600px;
  height: 600px;
  background: radial-gradient(
    circle,
    rgba(37, 99, 235, 0.1) 0%,
    transparent 70%
  );
  transform: translate(-50%, -50%);
  pointer-events: none;
}
```

### 控制栏 (Controls Bar)

```jsx
<ControlsBar>
  <ControlsBar.Left>
    <Button variant="ghost" size="icon" onClick={prevStep}>
      <ChevronLeft />
    </Button>
    <Button variant="primary" size="icon" onClick={togglePlay}>
      {isPlaying ? <Pause /> : <Play />}
    </Button>
    <Button variant="ghost" size="icon" onClick={nextStep}>
      <ChevronRight />
    </Button>
  </ControlsBar.Left>
  
  <ControlsBar.Center>
    <ProgressBar value={progress} max={100} />
  </ControlsBar.Center>
  
  <ControlsBar.Right>
    <SpeedControl value={speed} onChange={setSpeed} />
    <Button variant="ghost" size="icon" onClick={toggleFullscreen}>
      <Fullscreen />
    </Button>
  </ControlsBar.Right>
</ControlsBar>
```

## 7.3 CMS 编辑器页面

### 页面结构

```
Editor Layout
├── Header (56px)
├── Sidebar (240px)
│   ├── Scenario Info
│   ├── Steps List
│   └── Settings
└── Editor Area
    ├── Toolbar
    ├── Split View
    │   ├── Editor Panel
    │   └── Preview Panel
    └── Status Bar
```

### 编辑器面板

```jsx
<EditorPanel>
  <EditorToolbar>
    <Toolbar.Group>
      <Toolbar.Button active={view === 'edit'}>编辑</Toolbar.Button>
      <Toolbar.Button active={view === 'preview'}>预览</Toolbar.Button>
      <Toolbar.Button active={view === 'split'}>分屏</Toolbar.Button>
    </Toolbar.Group>
    <Toolbar.Group>
      <Toolbar.Button onClick={save}>保存</Toolbar.Button>
      <Toolbar.Button onClick={publish}>发布</Toolbar.Button>
    </Toolbar.Group>
  </EditorToolbar>
  
  <SplitView direction="horizontal">
    <EditorContent>
      <StepEditor step={currentStep} />
    </EditorContent>
    <PreviewPanel>
      <StepPreview step={currentStep} />
    </PreviewPanel>
  </SplitView>
</EditorPanel>
```

## 7.4 场景列表页面

### 页面结构

```
Scenarios Layout
├── Header
├── Filters Bar
│   ├── Search Input
│   ├── Category Filter
│   └── Sort Dropdown
├── Content
│   ├── Grid View / List View Toggle
│   └── Scenarios Grid
│       ├── Scenario Card x N
└── Pagination
```

### 场景卡片

```jsx
<ScenarioCard>
  <ScenarioCard.Cover>
    <img src={scenario.coverImage} alt={scenario.title} />
    <ScenarioCard.Badge>{scenario.category}</ScenarioCard.Badge>
  </ScenarioCard.Cover>
  <ScenarioCard.Content>
    <ScenarioCard.Title>{scenario.title}</ScenarioCard.Title>
    <ScenarioCard.Description>{scenario.description}</ScenarioCard.Description>
    <ScenarioCard.Meta>
      <span>{scenario.author.name}</span>
      <span>{scenario.metadata.viewCount} 次播放</span>
    </ScenarioCard.Meta>
  </ScenarioCard.Content>
  <ScenarioCard.Footer>
    <Button size="sm">播放</Button>
    <Button variant="ghost" size="sm">编辑</Button>
  </ScenarioCard.Footer>
</ScenarioCard>
```

---

# 八、动画与交互

## 8.1 动画设计原则

### 动画目的

1. **引导注意力**: 引导用户关注重要内容
2. **提供反馈**: 确认用户操作已生效
3. **保持连续性**: 平滑过渡，减少认知负荷
4. **增加愉悦感**: 提升产品质感

### 动画性能

- 使用 `transform` 和 `opacity` 属性
- 避免动画 `width`, `height`, `top`, `left`
- 使用 `will-change` 提示浏览器优化
- 尊重 `prefers-reduced-motion` 设置

## 8.2 缓动函数

```css
:root {
  /* 标准缓动 */
  --ease-default: cubic-bezier(0.4, 0, 0.2, 1);
  
  /* 进入缓动 */
  --ease-enter: cubic-bezier(0, 0, 0.2, 1);
  
  /* 退出缓动 */
  --ease-exit: cubic-bezier(0.4, 0, 1, 1);
  
  /* 弹性缓动 */
  --ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
  
  /* 弹簧缓动 */
  --ease-spring: cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
```

## 8.3 时长规范

| 类型 | 时长 | 用途 |
|------|------|------|
| **Micro** | 100-150ms | 按钮悬停、颜色变化 |
| **Fast** | 150-200ms | 开关、小元素显示 |
| **Normal** | 200-300ms | 模态框、下拉菜单 |
| **Slow** | 300-500ms | 页面过渡、大元素 |
| **Demo** | 800-1500ms | 演示动画 |

## 8.4 常见动画

### 页面过渡

```css
.page-enter {
  opacity: 0;
  transform: translateY(20px);
}

.page-enter-active {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 300ms ease, transform 300ms ease;
}

.page-exit {
  opacity: 1;
  transform: translateY(0);
}

.page-exit-active {
  opacity: 0;
  transform: translateY(-20px);
  transition: opacity 200ms ease, transform 200ms ease;
}
```

### 列表动画

```css
.list-item-enter {
  opacity: 0;
  transform: translateX(-20px);
}

.list-item-enter-active {
  opacity: 1;
  transform: translateX(0);
  transition: all 300ms ease;
}

.list-item-exit {
  opacity: 1;
  transform: translateX(0);
}

.list-item-exit-active {
  opacity: 0;
  transform: translateX(20px);
  transition: all 200ms ease;
}
```

### 模态框动画

```css
.modal-overlay-enter {
  opacity: 0;
}

.modal-overlay-enter-active {
  opacity: 1;
  transition: opacity 200ms ease;
}

.modal-content-enter {
  opacity: 0;
  transform: scale(0.95) translateY(-10px);
}

.modal-content-enter-active {
  opacity: 1;
  transform: scale(1) translateY(0);
  transition: opacity 200ms ease, transform 200ms ease;
}
```

## 8.5 演示动画

### 需求卡片动画

```jsx
<RequirementCard
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: [0, -10, 0] }}
  transition={{
    opacity: { duration: 0.5 },
    y: {
      duration: 2,
      repeat: Infinity,
      ease: "easeInOut"
    }
  }}
>
  {content}
</RequirementCard>
```

### 打字机效果

```jsx
<TypewriterText text={markdownContent} speed={50} />
```

```jsx
function TypewriterText({ text, speed = 50 }) {
  const [displayText, setDisplayText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  
  useEffect(() => {
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setDisplayText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, speed);
      return () => clearTimeout(timeout);
    }
  }, [currentIndex, text, speed]);
  
  return <span>{displayText}</span>;
}
```

### 节点连线动画

```jsx
<NodeGraph nodes={nodes} connections={connections}>
  {nodes.map((node, index) => (
    <Node
      key={node.id}
      initial={{ opacity: 0, scale: 0 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.2 }}
    />
  ))}
  {connections.map((conn, index) => (
    <Connection
      key={conn.id}
      initial={{ pathLength: 0 }}
      animate={{ pathLength: 1 }}
      transition={{ delay: nodes.length * 0.2 + index * 0.3 }}
    />
  ))}
</NodeGraph>
```

## 8.6 交互反馈

### 按钮悬停

```css
.btn {
  transition: all 150ms var(--ease-default);
}

.btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.btn:active {
  transform: translateY(0);
  transition-duration: 50ms;
}
```

### 卡片悬停

```css
.card {
  transition: all 200ms var(--ease-default);
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
}
```

### 输入框聚焦

```css
.input {
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.input:focus {
  border-color: var(--color-primary-600);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}
```

---

# 九、响应式设计

## 9.1 断点定义

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    screens: {
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
      '2xl': '1536px',
    },
  },
}
```

## 9.2 响应式策略

### 移动优先

```css
/* 基础样式 (移动端) */
.component {
  padding: 16px;
}

/* 平板 */
@media (min-width: 768px) {
  .component {
    padding: 24px;
  }
}

/* 桌面 */
@media (min-width: 1024px) {
  .component {
    padding: 32px;
  }
}
```

## 9.3 页面响应式变化

### Player 页面

| 元素 | 移动端 | 平板 | 桌面 |
|------|--------|------|------|
| **布局** | 单栏堆叠 | 三栏 | 三栏 |
| **步骤面板** | 底部抽屉 | 左侧固定 | 左侧固定 |
| **讲解面板** | 隐藏 | 右侧固定 | 右侧固定 |
| **控制栏** | 底部固定 | 底部固定 | 底部固定 |

### CMS 编辑器

| 元素 | 移动端 | 平板 | 桌面 |
|------|--------|------|------|
| **布局** | 单栏 | 侧边栏+内容 | 侧边栏+内容 |
| **侧边栏** | 抽屉 | 固定 | 固定 |
| **编辑器** | 全屏 | 分屏 | 分屏 |
| **预览** | 模态框 | 右侧 | 右侧 |

## 9.4 字体响应式

```css
/* 标题 */
.heading-1 {
  font-size: 24px;
}

@media (min-width: 768px) {
  .heading-1 {
    font-size: 30px;
  }
}

/* 正文 */
.body-text {
  font-size: 14px;
}

@media (min-width: 768px) {
  .body-text {
    font-size: 16px;
  }
}
```

## 9.5 间距响应式

```css
.container {
  padding: 16px;
}

@media (min-width: 640px) {
  .container {
    padding: 24px;
  }
}

@media (min-width: 1024px) {
  .container {
    padding: 32px;
  }
}

@media (min-width: 1280px) {
  .container {
    padding: 48px;
  }
}
```

---

# 十、可访问性规范

## 10.1 可访问性目标

遵循 **WCAG 2.1 Level AA** 标准

## 10.2 颜色对比度

### 文字对比度

| 文字大小 | 正常文字 | 大号文字 | 粗体文字 |
|----------|----------|----------|----------|
| 对比度 | ≥ 4.5:1 | ≥ 3:1 | ≥ 3:1 |

### 对比度检查

```javascript
// 使用工具检查
- WebAIM Contrast Checker
- Stark (Figma Plugin)
- A11y - Color Contrast Checker
```

## 10.3 键盘导航

### 焦点管理

```css
/* 可见的焦点指示器 */
:focus-visible {
  outline: 2px solid var(--color-primary-600);
  outline-offset: 2px;
}

/* 焦点样式 */
.focus-ring {
  @apply focus:outline-none focus-visible:ring-2 
         focus-visible:ring-primary-600 
         focus-visible:ring-offset-2 
         focus-visible:ring-offset-surface;
}
```

### Tab 顺序

```html
<!-- 正确的Tab顺序 -->
<form>
  <input type="text" tabindex="0" />
  <input type="email" tabindex="0" />
  <button type="submit" tabindex="0">提交</button>
</form>
```

### 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Tab` | 导航到下一个焦点元素 |
| `Shift + Tab` | 导航到上一个焦点元素 |
| `Enter` | 激活按钮或链接 |
| `Space` | 切换开关或播放/暂停 |
| `Escape` | 关闭模态框或菜单 |
| `Arrow Keys` | 导航列表或控制播放 |
| `F` | 全屏切换 |

## 10.4 屏幕阅读器

### ARIA 标签

```jsx
// 图标按钮
<button aria-label="播放演示">
  <PlayIcon />
</button>

// 当前步骤
<div aria-current="step" aria-label="步骤 3 of 10">
  {stepContent}
</div>

// 进度条
<div 
  role="progressbar"
  aria-valuenow={currentStep}
  aria-valuemin={0}
  aria-valuemax={totalSteps}
  aria-label={`演示进度: ${currentStep} of ${totalSteps}`}
/>
```

### 语义化HTML

```html
<!-- 正确 -->
<nav aria-label="主导航">
  <ul>
    <li><a href="/">首页</a></li>
  </ul>
</nav>

<main>
  <article>
    <h1>标题</h1>
    <section aria-labelledby="section1">
      <h2 id="section1">小节标题</h2>
    </section>
  </article>
</main>
```

## 10.5 动画可访问性

### 减少动画

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 动画开关

```jsx
function AnimationWrapper({ children, animation }) {
  const prefersReducedMotion = usePrefersReducedMotion();
  
  if (prefersReducedMotion) {
    return children;
  }
  
  return (
    <motion.div {...animation}>
      {children}
    </motion.div>
  );
}
```

## 10.6 表单可访问性

### 标签关联

```jsx
// 正确
<label htmlFor="email">邮箱地址</label>
<input id="email" type="email" />

// 或使用 aria-label
<input 
  type="email" 
  aria-label="邮箱地址"
  placeholder="your@email.com"
/>
```

### 错误提示

```jsx
<div>
  <label htmlFor="username">用户名</label>
  <input
    id="username"
    type="text"
    aria-invalid={hasError}
    aria-describedby={hasError ? "username-error" : undefined}
  />
  {hasError && (
    <span id="username-error" role="alert">
      用户名不能为空
    </span>
  )}
</div>
```

---

# 十一、技术实现指南

## 11.1 技术栈

### 核心框架

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18.x | UI框架 |
| **TypeScript** | 5.x | 类型安全 |
| **Next.js** | 14.x | 全栈框架 |
| **Tailwind CSS** | 3.x | 样式系统 |

### 动画库

| 库 | 用途 |
|----|------|
| **Framer Motion** | React动画 |
| **GSAP** | 复杂时间线动画 |

### UI组件

| 库 | 用途 |
|----|------|
| **shadcn/ui** | 基础组件 |
| **Radix UI** | 无头组件 |
| **Lucide React** | 图标 |

## 11.2 项目结构

```
app/
├── components/
│   ├── ui/              # 基础UI组件
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   └── input.tsx
│   ├── animation/       # 动画组件
│   │   ├── fade-in.tsx
│   │   └── slide-up.tsx
│   └── player/          # Player相关组件
│       ├── steps-panel.tsx
│       └── controls-bar.tsx
├── hooks/               # 自定义Hooks
├── lib/
│   ├── utils.ts
│   └── animations.ts    # 动画配置
├── styles/
│   └── globals.css
├── page.tsx
└── layout.tsx
```

## 11.3 Tailwind 配置

```javascript
// tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      animation: {
        "fade-in": "fadeIn 300ms ease forwards",
        "slide-up": "slideUp 400ms cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
```

## 11.4 CSS 变量

```css
/* globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 222 47% 11%;
    --foreground: 210 40% 98%;
    --card: 217 33% 17%;
    --card-foreground: 210 40% 98%;
    --popover: 217 33% 17%;
    --popover-foreground: 210 40% 98%;
    --primary: 217 91% 60%;
    --primary-foreground: 210 40% 98%;
    --secondary: 217 33% 17%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217 33% 17%;
    --muted-foreground: 215 20% 65%;
    --accent: 217 33% 17%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 84% 60%;
    --destructive-foreground: 210 40% 98%;
    --border: 217 33% 25%;
    --input: 217 33% 25%;
    --ring: 217 91% 60%;
    --radius: 0.5rem;
  }
}
```

## 11.5 组件开发规范

### 组件模板

```tsx
// components/ui/button.tsx
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "underline-offset-4 hover:underline text-primary",
      },
      size: {
        default: "h-10 py-2 px-4",
        sm: "h-9 px-3 rounded-md",
        lg: "h-11 px-8 rounded-md",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
```

---

# 十二、设计Token

## 12.1 Token 结构

```json
{
  "color": {
    "base": {
      "bg": "#0F172A",
      "surface": "#1E293B",
      "elevated": "#334155"
    },
    "text": {
      "primary": "#F8FAFC",
      "secondary": "#94A3B8",
      "muted": "#64748B"
    },
    "primary": {
      "50": "#EFF6FF",
      "100": "#DBEAFE",
      "500": "#3B82F6",
      "600": "#2563EB",
      "700": "#1D4ED8"
    },
    "semantic": {
      "success": "#10B981",
      "warning": "#F59E0B",
      "error": "#EF4444",
      "info": "#06B6D4"
    }
  },
  "spacing": {
    "1": "4px",
    "2": "8px",
    "4": "16px",
    "6": "24px",
    "8": "32px",
    "12": "48px",
    "16": "64px"
  },
  "radius": {
    "sm": "4px",
    "md": "8px",
    "lg": "12px",
    "xl": "16px",
    "full": "9999px"
  },
  "shadow": {
    "card": "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
    "hover": "0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.3)",
    "modal": "0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3)",
    "glow": "0 0 20px rgba(37, 99, 235, 0.3)"
  },
  "animation": {
    "duration": {
      "fast": "150ms",
      "normal": "300ms",
      "slow": "500ms"
    },
    "easing": {
      "default": "cubic-bezier(0.4, 0, 0.2, 1)",
      "enter": "cubic-bezier(0, 0, 0.2, 1)",
      "exit": "cubic-bezier(0.4, 0, 1, 1)",
      "bounce": "cubic-bezier(0.68, -0.55, 0.265, 1.55)"
    }
  },
  "typography": {
    "family": {
      "sans": "'Inter', system-ui, sans-serif",
      "mono": "'JetBrains Mono', monospace"
    },
    "size": {
      "xs": "12px",
      "sm": "14px",
      "base": "16px",
      "lg": "18px",
      "xl": "20px",
      "2xl": "24px",
      "3xl": "30px",
      "4xl": "36px"
    },
    "lineHeight": {
      "tight": "1.25",
      "normal": "1.5",
      "relaxed": "1.625"
    }
  }
}
```

## 12.2 Token 使用示例

### CSS 自定义属性

```css
:root {
  /* Colors */
  --color-bg-base: #0F172A;
  --color-bg-surface: #1E293B;
  --color-primary-600: #2563EB;
  --color-text-primary: #F8FAFC;
  
  /* Spacing */
  --space-4: 16px;
  --space-6: 24px;
  
  /* Radius */
  --radius-md: 8px;
  --radius-lg: 12px;
  
  /* Shadows */
  --shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
  --shadow-glow: 0 0 20px rgba(37, 99, 235, 0.3);
  
  /* Animation */
  --duration-normal: 300ms;
  --ease-default: cubic-bezier(0.4, 0, 0.2, 1);
}
```

### JavaScript/TypeScript

```typescript
// tokens.ts
export const tokens = {
  color: {
    bg: {
      base: '#0F172A',
      surface: '#1E293B',
      elevated: '#334155',
    },
    text: {
      primary: '#F8FAFC',
      secondary: '#94A3B8',
      muted: '#64748B',
    },
    primary: {
      600: '#2563EB',
      700: '#1D4ED8',
    },
  },
  spacing: {
    4: '16px',
    6: '24px',
    8: '32px',
  },
  radius: {
    md: '8px',
    lg: '12px',
  },
} as const;
```

---

# 文档结束

## 附录

### A. 参考资源

- [Tailwind CSS 文档](https://tailwindcss.com/docs)
- [Framer Motion 文档](https://www.framer.com/motion/)
- [shadcn/ui 组件](https://ui.shadcn.com/)
- [Radix UI](https://www.radix-ui.com/)
- [WCAG 2.1 指南](https://www.w3.org/WAI/WCAG21/quickref/)

### B. 工具推荐

- **设计**: Figma
- **颜色**: Coolors, ColorHunt
- **字体**: Google Fonts, Font Pair
- **图标**: Lucide, Heroicons
- **动画**: Framer Motion Playground

### C. 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2024-02-13 | 初始版本，完整设计系统 | AI Agent |

---

**文档使用说明**

1. 设计师应参考此文档进行UI设计
2. 开发者应按照规范实现组件
3. 产品经理应了解设计约束
4. 测试人员应验证设计实现

**反馈渠道**

如有疑问或建议，请在GitHub Issues中创建设计改进建议。

