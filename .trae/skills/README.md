# Trae Skills 使用说明

## 📋 概述

本目录包含所有适用于 Trae 的技能，已从 `.cursor/skills` 转换而来，共 **31 个技能**。

## 📁 目录结构

```
.trae/skills/
├── core/                    # 核心规则
│   └── SKILL.md
├── chinese-documentation/   # 中文文档编写规范
│   └── SKILL.md
├── code-style/              # 编码产出规范
├── architecture/            # 分层与架构规范
├── api-design/              # 接口设计规范
├── database/                # 数据库规范
├── security/                # 安全规范
├── performance/             # 性能规范
├── logging/                 # 日志与可观测性
├── config/                  # 环境与配置
│
├── react-best-practices/    # React 性能优化
├── web-design-guidelines/   # Web 设计最佳实践
├── ui-ux-pro-max/           # UI/UX 设计智能（含 scripts/data）
│
├── brainstorming/           # 头脑风暴
├── writing-plans/           # 编写计划
├── executing-plans/         # 执行计划
├── subagent-driven-development/  # 子代理开发
├── dispatching-parallel-agents/  # 并行代理调度
│
├── test-driven-development/ # 测试驱动开发
├── webapp-testing/          # Web 应用测试（含 scripts）
├── requesting-code-review/  # 代码审查请求
├── receiving-code-review/   # 接收代码审查
├── verification-before-completion/  # 完成前验证
│
├── systematic-debugging/    # 系统性调试
│
├── using-git-worktrees/     # Git Worktrees 使用
├── finishing-a-development-branch/  # 完成开发分支
│
├── vercel-deploy-claimable/ # Vercel 部署（含 scripts）
│
├── skill-creator/           # 技能创建工具（含 scripts/references）
├── mcp-builder/             # MCP 服务器构建（含 scripts）
├── writing-skills/          # 技能编写指南
├── using-superpowers/       # Superpowers 使用指南
│
├── README.md                # 本文件
└── CONVERSION_NOTES.md      # 转换说明
```

## 🎯 技能分类

### 核心技能（自动加载）
- **core/** - 核心开发规则
- **chinese-documentation/** - 中文文档编写规范

### 项目开发规范
- **code-style/** - 编码产出规范
- **architecture/** - 分层与架构规范
- **api-design/** - 接口设计规范
- **database/** - 数据库规范
- **security/** - 安全规范
- **performance/** - 性能规范
- **logging/** - 日志与可观测性
- **config/** - 环境与配置

### 性能优化
- **react-best-practices/** - React 和 Next.js 性能优化指南
- **web-design-guidelines/** - Web 设计最佳实践审查

### 工作流技能
- **brainstorming/** - 苏格拉底式设计细化流程
- **writing-plans/** - 详细实施计划编写
- **executing-plans/** - 计划执行（批量执行）
- **subagent-driven-development/** - 子代理驱动开发
- **dispatching-parallel-agents/** - 并行代理调度

### 测试与质量
- **test-driven-development/** - 测试驱动开发（TDD）
- **webapp-testing/** - Web 应用测试技能
- **requesting-code-review/** - 代码审查请求
- **receiving-code-review/** - 接收代码审查
- **verification-before-completion/** - 完成前验证

### 调试
- **systematic-debugging/** - 系统性调试（4阶段流程）

### Git 工作流
- **using-git-worktrees/** - Git Worktrees 使用
- **finishing-a-development-branch/** - 完成开发分支

### 设计技能
- **ui-ux-pro-max/** - UI/UX 设计智能技能（100+ 推理规则，57 种样式）

### 部署技能
- **vercel-deploy-claimable/** - Vercel 一键部署技能

### 技能开发
- **skill-creator/** - 技能创建工具
- **mcp-builder/** - MCP 服务器构建工具
- **writing-skills/** - 技能编写指南
- **using-superpowers/** - Superpowers 使用指南

## 🚀 使用方法

### Trae 中的使用

Trae 会自动识别 `.trae/skills/` 目录下的技能。技能会根据任务类型自动加载。

**示例**：
- 编写 React 代码 → 自动加载 `react-best-practices`
- 设计 UI → 自动加载 `ui-ux-pro-max`
- 编写测试 → 自动加载 `test-driven-development`
- 调试问题 → 自动加载 `systematic-debugging`

### 手动指定技能

也可以在对话中明确指定：
- "使用 react-best-practices 优化这个组件"
- "按照 brainstorming 流程设计这个功能"

## 📊 统计信息

- **总技能数**：31 个
- **有资源文件的技能**：5 个
  - mcp-builder（scripts）
  - skill-creator（scripts, references）
  - ui-ux-pro-max（scripts, data）
  - vercel-deploy-claimable（scripts）
  - webapp-testing（scripts）

## 🔧 格式说明

### 技能文件格式

Trae 使用 `SKILL.md` 格式，与 Claude Code 类似：

```markdown
---
name: skill-name
description: 技能描述（说明何时使用此技能）
type: always_apply  # 可选，如果需要自动加载
---

# 技能标题

技能内容...
```

### 路径引用

- 脚本路径使用相对路径：`scripts/deploy.sh`
- 技能目录路径：`~/.trae/skills`
- 数据文件路径：`data/styles.csv`

## ⚠️ 注意事项

1. **路径引用**：所有路径引用已调整为 Trae 格式（`~/.trae/skills`）
2. **资源文件**：某些技能包含 scripts、data、references 目录，请确保这些文件存在
3. **脚本执行**：脚本路径使用相对路径，确保在技能目录中执行
4. **格式兼容**：Trae 技能格式与 Claude Code 类似，但使用 `SKILL.md` 而不是 `.mdc`

## 🔄 更新和维护

### 从 Cursor Skills 同步

如果需要从 `.cursor/skills` 同步更新：

1. 运行转换脚本（参考 `CONVERSION_NOTES.md`）
2. 修复路径引用
3. 测试技能功能

### 添加新技能

1. 在 `.trae/skills/` 下创建新目录
2. 创建 `SKILL.md` 文件
3. 添加 YAML frontmatter
4. 编写技能内容
5. 如需资源文件，添加 scripts/data/references 目录

## 📚 相关文档

- [CONVERSION_NOTES.md](./CONVERSION_NOTES.md) - 转换详细说明
- [Cursor Skills README](../.cursor/skills/README.md) - Cursor 技能说明
- [unified-skills/README.md](../../unified-skills/README.md) - 统一技能集合说明

---

**最后更新**：2025年1月19日  
**技能总数**：31 个  
**来源**：从 `.cursor/skills` 转换而来  
**状态**：✅ 已完成转换和适配
