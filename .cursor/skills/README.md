# Agent Skills 使用说明

## 目录结构

```
.cursor/skills/
├── core/                    # 核心规则（每次对话必用）
│   └── core.mdc
├── chinese-documentation/   # 中文文档编写规范（每次对话必用）
│   └── chinese-documentation.mdc
│
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
└── SKILLS_MIGRATION.md      # 技能迁移说明
```

> 📊 **统计**：共 31 个技能目录，5 个技能包含资源文件（scripts/data/references）

## 架构设计

本项目采用**分层 Skills 架构**：

### 核心层（自动加载）

- **core/** - 核心开发规则，每次对话自动应用
- **chinese-documentation/** - 中文文档编写规范，每次对话自动应用

### 项目开发规范层（按需加载）

- **code-style, architecture, api-design, database** - 代码和架构规范
- **security, performance, logging, config** - 安全、性能、日志、配置规范

### 功能增强层（按需加载）

- **性能优化**：react-best-practices, web-design-guidelines
- **工作流**：brainstorming, writing-plans, executing-plans 等
- **测试与质量**：test-driven-development, code-review 相关
- **调试**：systematic-debugging
- **设计**：ui-ux-pro-max
- **部署**：vercel-deploy-claimable
- **技能开发**：skill-creator, mcp-builder, writing-skills

### 组织原则

- **独立文件夹**：每个 Skill 放在独立文件夹中，便于扩展和维护
- **资源文件**：scripts、data、references 等资源文件与技能文件一起存放
- **自动识别**：根据任务类型自动加载相关技能

## Skills 列表

### 核心 Skills（每次必用）

#### 1. core/（核心规则）

- **类型**：`always_apply`
- **文件**：`core/core.mdc`
- **内容**：基础约束、自检清单、违例处理
- **自动加载**：每次对话都会自动应用

#### 2. chinese-documentation/（中文文档编写规范）

- **类型**：`always_apply`
- **文件**：`chinese-documentation/chinese-documentation.mdc`
- **适用场景**：创建新的 Markdown 文档、编写项目文档
- **内容**：文档命名规范、内容编写规范、中文优先原则
- **自动加载**：每次对话都会自动应用

### 项目开发规范 Skills

#### 3. code-style/（编码产出规范）

- **文件**：`code-style/code-style.mdc`
- **适用场景**：编写新代码、修改现有代码
- **内容**：注释规范、导包规范、DTO规范、ID生成规范

#### 4. architecture/（分层与架构规范）

- **文件**：`architecture/architecture.mdc`
- **适用场景**：设计Controller、Service层、异常处理
- **内容**：Controller规范、异常处理、网关规范

#### 5. api-design/（接口设计规范）

- **文件**：`api-design/api-design.mdc`
- **适用场景**：设计RESTful接口、定义路由
- **内容**：路由规范、参数规范、命名规范、对象流转

#### 6. database/（数据库规范）

- **文件**：`database/database.mdc`
- **适用场景**：设计表结构、编写SQL、数据库操作
- **内容**：表结构规范、查询规范、批量操作规范

#### 7. security/（安全规范）

- **文件**：`security/security.mdc`
- **适用场景**：处理用户输入、记录日志
- **内容**：入参校验、日志脱敏

#### 8. performance/（性能规范）

- **文件**：`performance/performance.mdc`
- **适用场景**：优化查询、处理大数据、引入缓存
- **内容**：N+1问题、分页、缓存一致性

#### 9. logging/（日志与可观测性）

- **文件**：`logging/logging.mdc`
- **适用场景**：记录操作日志、异常处理
- **内容**：操作日志、异常上下文、日志级别

#### 10. config/（环境与配置）

- **文件**：`config/config.mdc`
- **适用场景**：配置多环境、端口设置
- **内容**：多环境配置、端口约束

### 新增 Skills（来自 unified-skills）

#### 性能优化

- **react-best-practices/** - React 和 Next.js 性能优化指南（40+ 条规则）
- **web-design-guidelines/** - Web 设计最佳实践审查（100+ 条规则）

#### 工作流 Skills

- **brainstorming/** - 苏格拉底式设计细化流程
- **writing-plans/** - 详细实施计划编写
- **executing-plans/** - 计划执行（批量执行）
- **subagent-driven-development/** - 子代理驱动开发
- **dispatching-parallel-agents/** - 并行代理调度

#### 测试与质量

- **test-driven-development/** - 测试驱动开发（TDD）
- **webapp-testing/** - Web 应用测试技能
- **requesting-code-review/** - 代码审查请求
- **receiving-code-review/** - 接收代码审查
- **verification-before-completion/** - 完成前验证

#### 调试

- **systematic-debugging/** - 系统性调试（4阶段流程）

#### Git 工作流

- **using-git-worktrees/** - Git Worktrees 使用
- **finishing-a-development-branch/** - 完成开发分支

#### 设计技能

- **ui-ux-pro-max/** - UI/UX 设计智能技能（100+ 推理规则，57 种样式）

#### 部署技能

- **vercel-deploy-claimable/** - Vercel 一键部署技能

#### 技能开发

- **skill-creator/** - 技能创建工具
- **mcp-builder/** - MCP 服务器构建工具
- **writing-skills/** - 技能编写指南
- **using-superpowers/** - Superpowers 使用指南

> 📝 **完整列表**：共 31 个技能（原有 10 个 + 新增 21 个）
>
> 详细迁移说明请查看 [SKILLS_MIGRATION.md](./SKILLS_MIGRATION.md)

## 使用方式

### 自动加载（推荐）

以下 skills 会自动加载，无需手动操作：

- `core/core.mdc` - 核心开发规则
- `chinese-documentation/chinese-documentation.mdc` - 中文文档编写规范

### 按需加载

根据任务类型，Agent 会自动识别并加载相关 skills：

### 项目开发

- 编写代码 → 自动加载 `code-style`
- 设计接口 → 自动加载 `api-design`、`architecture`
- 数据库操作 → 自动加载 `database`、`performance`
- 安全相关 → 自动加载 `security`、`logging`
- 配置相关 → 自动加载 `config`

### 新增技能自动加载

- React/Next.js 开发 → 自动加载 `react-best-practices`
- UI/UX 设计 → 自动加载 `ui-ux-pro-max`、`web-design-guidelines`
- 功能设计 → 自动加载 `brainstorming`
- 编写测试 → 自动加载 `test-driven-development`
- 调试问题 → 自动加载 `systematic-debugging`
- 代码审查 → 自动加载 `requesting-code-review`
- 部署应用 → 自动加载 `vercel-deploy-claimable`

### 手动指定（高级用法）

如果需要强制加载特定 skills，可以在对话中明确提及：

- "请按照 code-style 和 architecture 规范来..."
- "遵循 database 和 performance 规范..."
- "使用 react-best-practices 优化这个组件"
- "按照 brainstorming 流程设计这个功能"
- "使用 test-driven-development 实现这个功能"

### 技能组合使用

多个技能可以组合使用，例如：

- **新功能开发**：`brainstorming` → `writing-plans` → `test-driven-development` → `executing-plans`
- **性能优化**：`react-best-practices` + `performance` + `web-design-guidelines`
- **代码审查**：`requesting-code-review` → `receiving-code-review`
- **问题排查**：`systematic-debugging` + `verification-before-completion`

## 添加新 Skill

当需要添加新的 Skill 时：

1. **创建文件夹**：在 `.cursor/skills/` 下创建新的文件夹，例如 `new-skill/`
2. **创建 Skill 文件**：在文件夹中创建 `.mdc` 文件，例如 `new-skill/new-skill.mdc`
3. **定义元数据**：在文件头部添加 YAML front matter：

   ```yaml
   ---
   name: new-skill-rules
   description: 新技能的描述
   ---
   ```

4. **更新文档**：在 `core/core.mdc` 的"按需加载其他 Skills"部分添加新 skill 的说明
5. **可选**：在 skill 文件夹中添加 `README.md` 提供详细说明

## 规则优先级

**本规则 > 仓库既有约定/代码风格 > 一般最佳实践**

如果出现冲突，Agent 会：

1. 先说明原因
2. 给出替代方案
3. 等待用户确认后才继续

## 🔍 快速查找技能

### 按使用场景查找

| 场景 | 推荐技能 |
|------|---------|
| **开始新功能** | `brainstorming` → `writing-plans` → `executing-plans` |
| **React/Next.js 开发** | `react-best-practices` + `code-style` |
| **UI/UX 设计** | `ui-ux-pro-max` + `web-design-guidelines` |
| **编写测试** | `test-driven-development` + `webapp-testing` |
| **调试问题** | `systematic-debugging` + `verification-before-completion` |
| **代码审查** | `requesting-code-review` + `receiving-code-review` |
| **性能优化** | `react-best-practices` + `performance` |
| **部署应用** | `vercel-deploy-claimable` |
| **Git 工作流** | `using-git-worktrees` + `finishing-a-development-branch` |
| **创建技能** | `skill-creator` + `writing-skills` + `mcp-builder` |

### 按技能类型查找

- **性能优化**：`react-best-practices`, `web-design-guidelines`, `performance`
- **工作流**：`brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development`
- **测试质量**：`test-driven-development`, `webapp-testing`, `requesting-code-review`
- **调试**：`systematic-debugging`, `verification-before-completion`
- **Git**：`using-git-worktrees`, `finishing-a-development-branch`
- **设计**：`ui-ux-pro-max`, `web-design-guidelines`
- **部署**：`vercel-deploy-claimable`
- **技能开发**：`skill-creator`, `mcp-builder`, `writing-skills`, `using-superpowers`

## 📚 相关文档

- [SKILLS_MIGRATION.md](./SKILLS_MIGRATION.md) - 技能迁移详细说明
- [unified-skills/README.md](../unified-skills/README.md) - 统一技能集合说明
- [unified-skills/SKILLS_INDEX.md](../unified-skills/SKILLS_INDEX.md) - 技能索引

## ⚠️ 注意事项

- **所有 skills 都遵循"最小修改原则"**：只修改与需求直接相关的代码
- **编译自检**：每次代码修改后必须执行编译自检
- **规则冲突**：无法满足规则时必须先说明原因并等待确认
- **独立文件夹**：每个 skill 放在独立文件夹中，便于扩展和维护
- **资源文件**：某些技能包含 scripts、data、references 目录，请确保这些文件存在
- **路径引用**：脚本路径使用相对路径（如 `scripts/deploy.sh`），确保在技能目录中执行

## 🔄 更新和维护

### 更新技能

1. 修改技能文件（`.mdc`）
2. 如需更新资源文件，同步更新 scripts/data/references 目录
3. 测试技能功能是否正常

### 添加新技能

1. **创建文件夹**：在 `.cursor/skills/` 下创建新的文件夹，例如 `new-skill/`
2. **创建 Skill 文件**：在文件夹中创建 `.mdc` 文件，例如 `new-skill/new-skill.mdc`
3. **定义元数据**：在文件头部添加 YAML front matter：

   ```yaml
   ---
   name: new-skill-rules
   description: 新技能的描述（说明何时使用此技能）
   type: always_apply  # 可选，如果需要自动加载
   ---
   ```

4. **更新文档**：在本 README.md 中添加新技能的说明
5. **可选**：在 skill 文件夹中添加 `README.md` 提供详细说明

### 从 unified-skills 同步

如果需要从 `unified-skills/.claude/skills` 同步新技能：

1. 运行转换脚本（参考 `SKILLS_MIGRATION.md`）
2. 检查路径引用是否正确
3. 测试技能功能
4. 更新本 README.md

---

**最后更新**：2025年1月19日  
**技能总数**：31 个  
**维护状态**：✅ 活跃维护中
