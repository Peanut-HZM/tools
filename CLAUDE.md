# CLAUDE.md

工具集合平台（tools）项目规则。所有 agent 必须严格遵守。

---

## 事后规则沉淀强制规则（最高优先级）

**解决问题后，如果问题暴露了规则缺失或重复发生的模式，必须沉淀为规则补充到 CLAUDE.md 和 AGENTS.md。**

### 核心原则

- ✅ **问题解决 ≠ 任务结束**：每次问题排查后自问："会再发生吗？是规则缺失还是执行疏漏？"
- ✅ **两份文件同步**：CLAUDE.md 和 AGENTS.md 必须同步沉淀同一条规则
- ✅ **最小改动**：补充新规则，不重写现有规则
- ❌ **禁止"解决完就结束"**：不沉淀会让同样的问题反复出现
- ❌ **禁止 AI 自行写入**：沉淀规则必须先展示草稿，用户明确同意后才能写文件

### 触发条件（至少满足之一）

1. **频率触发**：同一类问题在最近 30 天内被排查 ≥ 2 次
2. **违规触发**：问题根因是违反现有规则，且该规则未被严格遵守
3. **空白触发**：发现了现有规则完全未覆盖的新领域/新场景

### 沉淀流程

1. **评估是否触发**：命中三类触发条件之一？
2. **起草规则草稿**：在对话中展示给用户审阅（包含规则名称、核心原则、禁止行为、事故案例）
3. **用户审阅**：等待用户明确同意
4. **写入两份文件**：CLAUDE.md 和 AGENTS.md 同步写入
5. **提交 commit**：两份文件的改动一起提交

### 违规后果

- 不沉淀高频问题会让同样的坑被反复踩
- AI 自行写入未经审阅的规则会引入不合理规则
- 两份文件不同步会让规则漂移

---

## 禁止批量脚本修改代码规则（最高优先级）

**绝对禁止使用任何脚本批量修改项目代码文件。所有代码修改必须逐个文件手动进行。**

### 核心原则

- ✅ **逐个文件手动修改**：每个文件独立打开、阅读、修改、验证
- ✅ **每次修改前先读文件**：确认当前内容，理解上下文
- ❌ **禁止** 使用 Python/Shell/Node.js 脚本批量修改 `.py`、`.tsx`、`.ts`、`.css` 等源代码
- ❌ **禁止** 使用 `sed`、`awk`、`perl` 等命令行工具批量替换代码
- ❌ **禁止** 使用 `ast-grep` 的 `replace` 模式批量应用修改

### 允许的例外

- ✅ `ast-grep` 的 `search` 模式（仅搜索，不修改）
- ✅ `grep` 搜索（查找代码位置，不修改）
- ✅ 项目已有标准脚本（如 `dev-services.py` 等服务管理工具）

### 违规后果

- 批量修改无法逐行审查，错误难以发现
- 已多次导致命名不一致、遗漏、误改其他代码、不可回滚等问题
- 违反后必须立即回滚，逐个手动重新修改

---

## 临时产物及时清理规则（最高优先级）

**任务完成后必须立即清理所有临时产物，禁止让测试脚本、审计文件、调试截图等临时文件污染工作区。**

### 核心原则

- ✅ **任务完成 ≠ 结束**：完成后必须自查是否产生了临时产物
- ✅ **临时产物零残留**：测试脚本、审计文件、合并备份、调试截图等必须在任务完成后 24 小时内删除
- ✅ **提交前必须检查**：`git status` 显示的未跟踪文件必须是预期的新增文件
- ❌ **禁止** 提交临时产物到 Git
- ❌ **禁止** 让临时产物长期残留

### 临时产物类型

- 测试/验证脚本（`verify_*.py`、`test_*.py`）
- 审计/扫描产物（`.audit-*`、`.scan-*`）
- 合并备份（`*.before-merge-*`、`.original`）
- 调试截图（`*-after-fix.png`）
- 一次性修复脚本（`.fix-*.py`）

### 违规后果

- 临时产物进入版本库会污染历史记录
- 大量临时文件干扰工作区
- 可能误提交敏感信息

---

## 禁止 Mock 与兜底规则（最高优先级）

**项目代码中绝对禁止任何形式的 mock、兜底、默认值掩盖错误。**

### 核心原则

- ✅ **没有就是没有**：数据为空就返回空/Null，禁止用假数据冒充
- ✅ **报错就是报错**：出现异常必须抛出或按规范返回真实错误
- ✅ **接口失败就是失败**：依赖服务调用失败必须如实暴露
- ❌ **禁止** 业务代码中写 mock 数据、mock 接口、mock 返回值
- ❌ **禁止** 为未定义/不存在/为空/异常场景写兜底默认值
- ❌ **禁止** try-catch 吞掉异常后返回默认值/空对象/null 并继续执行业务逻辑
- ❌ **禁止** 为"防止页面报错"而伪造数据

### 允许的例外

- ✅ 单元测试/集成测试代码中的 mock（必须在测试目录内）
- ✅ 前端开发阶段的 Storybook/示例页面（必须明确区分）
- ✅ 经过用户明确确认的业务默认值（必须在代码注释中说明理由）

### 违规后果

- 掩盖真实问题，导致线上故障无法及时定位
- 审查发现后必须立即删除或改为真实错误处理

---

## 问题排查强制规则（最高优先级）

**排查问题必须找到准确的代码级根因，禁止猜测；报告任务完成必须以真实场景验收为前提。**

### 核心原则

- ✅ **根因必须有证据链**：基于数据、日志、代码、问题现象四类证据交叉验证
- ✅ **根因必须能解释全部现象**：解释不了全部现象就是还没找到根因
- ✅ **修复后必须真实验收**：必须在真实场景完整复现原问题场景并确认已修复
- ✅ **如实报告**：验证失败就说失败，没验证就明说没验证
- ❌ **禁止** 猜测错误原因（"可能是"、"应该是"、"大概率是"）
- ❌ **禁止** 凭经验乱猜（不看日志、不查数据、不读代码）
- ❌ **禁止** 改一版就说修好了（未验收前禁止声称"已修复"）
- ❌ **禁止** 虚假验收报告（未部署就声称验证通过）

### 强制排查流程

1. **收集现象**：完整记录问题表现、触发条件、报错信息
2. **获取证据**：浏览器 Console + Network、服务器日志、数据库查询
3. **读代码验证**：沿调用链读代码，找到确切位置
4. **形成根因结论**：必须同时解释所有已观察到的现象
5. **修复后真实场景验收**：部署 → 完整复现 → 确认修复
6. **如实报告**：证据、根因、修复内容、验收结果全部列出

### 违规后果

- 猜测式修复会让同一个 bug 反复出现
- 虚假验收报告误导用户决策，属于最严重的诚信问题

---

## 代码修改后浏览器验收规则（强制）

**所有影响用户界面的代码修改，必须在浏览器中真实验收后才能声称完成。**

### 核心原则

- ✅ **前端修改必须视觉验证**：修改组件/样式后，必须在浏览器中查看实际效果
- ✅ **后端 API 修改必须集成验证**：修改 API 后，必须通过前端页面或 Swagger UI 验证
- ✅ **修复 bug 必须复现原场景**：在浏览器中完整复现用户操作流程
- ✅ **验收证据**：Console 无错误 + 页面行为符合预期
- ❌ **禁止** 只改代码不验收就声称"已修复"
- ❌ **禁止** 只看代码逻辑不实际运行验证

### 验收流程

1. **启动服务**：`python dev-services.py`（如果未启动）
2. **打开浏览器**：访问 http://localhost:5178
3. **验证修改**：
   - 前端：检查页面渲染、交互行为
   - 后端：测试 API 功能、错误处理
4. **检查 Console**：F12 打开开发者工具，确认无错误
5. **如实报告**：验收通过说通过，失败说失败

### 违规后果

- 未验收就声称完成会掩盖真实问题
- 用户看到的效果与预期不符
- 属于虚假完成报告

---

## 客户端代码路径必须 DRY 规则（强制）

**客户端调用服务端端点的路径字符串必须只在一处定义（函数 helper 或模块常量），多调用点统一引用，禁止 inline 重复字符串。**

### 核心原则

- ✅ **一处定义**：URL 路径放在 `api.py` / `ENDPOINTS` 等 helper 或模块常量
- ✅ **多调用点统一引用**：所有调用都通过 helper / 常量访问
- ✅ **路径变更只改一处**：修改路径字符串只动 helper 定义，多调用点自动同步
- ❌ 禁止在两个函数里分别写 `requests.post("/api/v1/tool1", ...)` 路径字符串
- ❌ 禁止"复制粘贴修改"流程：一处改了路径、另一处忘了改
- ❌ 禁止"先 inline 写一遍、改天再抽 helper"的延迟重构——直接 helper 化

### 违规后果

- 同一资源多调用点，路径漂移导致部分功能正常部分失败（最隐蔽）
- 路径修改需要全局搜所有调用点，遗漏一个就出 bug
- 代码 review 难以发现 inline 路径错误（"看上去对就过"）
- 排查耗时翻倍：失败时不知道是哪条路径不对，需要逐调用点核对

---

## Git 工作流完整规范（最高优先级）

**本规范整合了 Git 操作的所有要求：Rebase 工作流、冲突解决、多 agent 并行、历史分叉防护。**

### 第一部分：Rebase 工作流核心原则

**所有 git 操作绝对不允许丢失任何文件变更或提交日志。**

#### 核心原则

- ✅ **提交前必须 rebase**：`git fetch` 然后 `git pull --rebase --autostash`
- ✅ **更新分支必须 rebase**：只能用 `git pull --rebase` 或 `git fetch + git rebase`
- ✅ **合并功能分支必须 rebase**：先 `git rebase master`，保持线性历史
- ✅ **冲突必须妥善解决**：逐个文件、逐个冲突点手动解决，保留双方代码
- ✅ **保护所有人的提交**：绝对不允许丢失任何人的代码和 commit message
- ✅ **变更提交前必须确认范围**：`git status --short` 与 `git diff --cached --name-only` 必须先检查
- ❌ **禁止** `git pull`（不带 `--rebase`）
- ❌ **禁止** `git merge` 用于更新本地分支
- ❌ **禁止** `git push --force` / `git push -f`
- ❌ **禁止** `git reset --hard` 丢弃未提交的工作
- ❌ **禁止** `git checkout --theirs` / `git checkout --ours` 粗暴覆盖整个文件
- ❌ **禁止** `git add .` / `git commit -a` 批量操作

#### 强制前置步骤

```bash
git status --porcelain                    # 1. 检查工作区状态
git fetch --all --prune                   # 2. 获取远程最新状态
git pull --rebase --autostash origin master  # 3. rebase 更新
git status --porcelain                    # 4. 确认 rebase 成功
```

### 第二部分：冲突解决规范

1. **查看冲突文件列表**：`git status`
2. **逐个文件打开**：理解双方代码意图
3. **手动合并**：保留双方代码的正确部分
4. **验证合并结果**：确保逻辑正确
5. **标记解决**：`git add <文件>`，然后 `git rebase --continue`
6. **如果冲突太复杂**：停下来告知用户

### 第三部分：多 agent 并行规则

**多个 agent 同时修改同一仓库时，绝对禁止回滚、覆盖或丢弃另一个 agent 已写入磁盘但未提交的代码修改。**

- ✅ **磁盘上的修改 = 另一个 agent 的工作成果**
- ✅ **只能合并，不能覆盖**
- ✅ **先 diff 再操作**：`git diff` 确认没有别人的修改被丢弃
- ❌ **禁止** `git checkout -- <file>` 丢弃他人未提交的修改
- ❌ **禁止** 在 rebase 后重新写文件覆盖其他 agent 的修改

### 第四部分：防止历史分叉

#### 核心原则

- ✅ **推送前必须检查分叉**：`git log --oneline HEAD...<remote>/<branch>`
- ✅ **发现分叉必须立即处理**：先同步再推送
- ✅ **创建备份分支**：任何 rebase/reset/merge 操作前，先 `git branch backup-<timestamp>`
- ❌ **禁止** `git commit --amend` 修改已推送的提交
- ❌ **禁止** `git rebase -i` 修改已推送的提交

### 第五部分：违规后果

1. **Rebase 违规**：生成大量 merge commit，粗暴覆盖导致协作者代码丢失
2. **历史分叉违规**：提交丢失、功能缺失、合并冲突

---

## 配置文件管理完整规范（最高优先级）

**本规范整合了配置文件的所有要求：存储位置、Git 保护。**

### 第一部分：核心原则

#### 1.1 配置存储位置

- ✅ **本地配置文件是唯一真相源**：所有配置都存放在本地 `backend/app/config/config.py` 和 `frontend/.env`
- ✅ **环境变量管理敏感信息**：API 密钥、数据库密码等通过 `.env` 或环境变量传入

#### 1.2 配置修改流程

1. 修改本地配置文件
2. 提交到 Git 仓库
3. 重启服务（使用 `dev-services.py`）

### 第二部分：Git 操作保护

**`config.py`、`.env` 等配置文件中的关键值属于"受保护配置"，在任何 git 操作中绝对禁止被静默覆盖或回退。**

#### 核心原则

- ✅ **新值优先**：rebase 冲突解决时，必须默认保留较新的配置值
- ✅ **配置冲突必须停下来**：用 `git log -p` 查看双方历史，理解每个配置值的来龙去脉
- ✅ **配置与代码分开提交**：配置变更永远用独立小 commit
- ❌ **禁止** `git checkout --ours/--theirs` 用于配置文件
- ❌ **禁止** 在 rebase 后不检查配置文件

#### 受保护的配置文件

- `backend/app/config/config.py`：后端配置（数据库、OSS、JWT 等）
- `frontend/.env`、`frontend/.env.*`：前端环境变量（API 地址、Vite 配置等）
- `dev-services.py`：服务管理脚本

### 第三部分：违规后果

1. **配置存储违规**：敏感信息硬编码到代码中，无法审计
2. **Git 保护违规**：配置静默回退会导致线上服务完全不可用

---

## 浏览器进程管理规则（强制）

**在使用 Skill 或 MCP 工具操作浏览器时，绝对禁止杀死所有 Chrome 进程。**

### 核心原则

- ❌ **绝对禁止** 执行任何会杀死全部 Chrome 进程的命令（如 `taskkill /F /IM chrome.exe`）
- ✅ **优先操作已打开的浏览器**：使用 DevTools Protocol 连接已存在的浏览器实例
- ✅ **只能重启 AI 操作过的进程**：只终止由当前 AI 会话启动/控制的特定浏览器进程
- ✅ **使用隔离上下文**：新启动浏览器时，应使用独立的数据目录

### 违规后果

- 杀死用户正在使用的浏览器会导致所有标签页丢失
- 属于破坏性操作，违反最小影响原则

---

## ID 字段类型规则（强制）

**所有实体 ID 字段在数据库层和后端代码中必须使用合适的类型，前端 API 传输时必须用 `String` 类型。**

### 后端规则

- **数据库**：ID 列使用 `BIGINT` 或 `UUID`
- **Python 实体**：ID 字段使用 `int` 或 `str` 类型

### 前端规则

- **API 请求/响应**：ID 字段使用 `string` 类型
- **后端接收前端请求时**：接收 `str`，转换为 `int` 或保持原类型
- **后端返回前端响应时**：将 ID 转为 `str`

### 原因

JavaScript 的 `Number` 类型最大安全整数是 `2^53 - 1`（约 9 × 10^15），而数据库 BIGINT 最大值为 `2^63 - 1`（约 9 × 10^18）。雪花算法等生成的 ID 经常超过 JS 安全范围，传输时如不转 String 会丢失精度。

---

## 项目概览

工具集合平台（tools），基于 Python FastAPI + React 18 的单体应用架构。

### 架构层次

```
前端 (React + Vite) → 后端 (FastAPI) → 数据库 (PostgreSQL)
                                          ↓
                                     阿里云 OSS
```

### 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | React 18 + TypeScript + Vite | 单页应用（端口 5178） |
| UI | Tailwind CSS + Zustand | 样式 + 状态管理 |
| 后端 | Python 3.10+ + FastAPI | RESTful API（端口 19092） |
| ORM | SQLAlchemy | 数据库操作 |
| 数据库 | PostgreSQL | 主数据库 |
| 存储 | 阿里云 OSS | 文件存储 |

### 项目结构

```
tools/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── api/routes/          # API 路由 (v1 版本)
│   │   ├── routes/              # 工具路由
│   │   ├── models/              # 数据模型
│   │   ├── schemas/             # Pydantic 模式
│   │   ├── services/            # 业务逻辑层
│   │   ├── config/              # 配置管理
│   │   └── utils/               # 工具函数
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React 组件
│   │   ├── hooks/               # 自定义 Hooks
│   │   ├── services/            # API 服务层
│   │   ├── stores/              # Zustand 状态管理
│   │   ├── types/               # TypeScript 类型
│   │   └── App.tsx
│   └── package.json
├── specs/                       # 需求规格文档
└── docs/                        # 项目文档
```

### 核心模块

#### 后端路由

- `/api/v1` - Product Manager Agent (LLM 配置、对话、PRD 生成)
- `/api` - 工具集合 (OCR、ASR、数据库、Redis、SSH、Markdown 编辑器等)
- `/api/auth` - 用户认证 (JWT)

#### 前端主要组件

- `components/Tools/` - 各工具页面实现
- `components/Admin/` - 管理后台
- `services/` - 后端 API 封装

---

## 常用命令

### 后端（backend/ 目录）

```bash
uvicorn app.main:app --reload --port 19092  # 开发服务器 (热重载)
python -m py_compile app/main.py            # 语法检查
ruff check .                                # 代码规范检查
ruff format .                               # 代码格式化
pytest                                      # 运行测试
```

**强制规则**：
- **必须** 使用 `ruff` 进行代码规范检查
- **必须** 使用 `dev-services.py` 管理服务，不要手动启动 uvicorn

### 前端（frontend/ 目录）

```bash
npm run dev           # 启动开发服务器 (热重载)
npm run build         # 构建生产版本
npm run test          # 运行测试
npm run preview       # 预览生产构建
npm run type-check    # TypeScript 类型检查
npm run lint          # ESLint 检查并修复
npm run format        # Prettier 格式化
```

### 服务管理（项目根目录）

```bash
python dev-services.py              # 启动前后端服务
python dev-services.py status       # 查看服务状态
python dev-services.py restart      # 重启前后端服务
python dev-services.py stop         # 停止前后端服务
python dev-services.py kill all     # 强制终止所有服务
python dev-services.py logs backend # 查看后端实时日志
python dev-services.py logs frontend# 查看前端实时日志
```

---

## 日志管理完整规范（强制）

### 第一部分：核心原则

- ✅ **本地日志用于开发调试**：通过 `logging` 模块输出到控制台
- ✅ **远程日志用于生产排查**：必须通过 `dev-services.py logs` 获取
- ✅ **先获取日志再分析**：禁止凭经验猜测

### 第二部分：本地日志位置

后端通过 `logging` 模块输出到控制台，使用 `dev-services.py logs backend` 查看实时日志。

### 第三部分：日志级别规范

```python
import logging

logger = logging.getLogger(__name__)

# 关键操作使用 INFO
logger.info(f"用户 {user_id} 创建了工具配置")

# 错误使用 ERROR，必须包含异常信息
try:
    # 业务逻辑
except Exception as e:
    logger.error(f"操作失败: {str(e)}", exc_info=True)
    raise
```

### 强制规则

- ✅ **后端关键代码必须包含日志记录**
- ✅ **异常必须使用 `logger.error(..., exc_info=True)` 记录完整堆栈**
- ✅ **敏感信息（密码、密钥）禁止写入日志**

---

## 后端开发规范（FastAPI）

### 第一部分：路由设计

#### 核心原则

- ✅ **RESTful 风格**：使用标准 HTTP 方法和状态码
- ✅ **版本化路由**：`/api/v1/` 前缀用于新 API
- ✅ **统一的响应格式**：使用 Pydantic 模型定义响应结构
- ❌ **禁止** 在路由函数中直接写业务逻辑，必须调用 Service 层

#### 标准路由模板

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.tool import ToolCreate, ToolResponse
from app.services.tool_service import ToolService

router = APIRouter()

@router.post("/tools", response_model=ToolResponse)
def create_tool(tool: ToolCreate, db: Session = Depends(get_db)):
    """创建工具"""
    service = ToolService(db)
    return service.create(tool)

@router.get("/tools/{tool_id}", response_model=ToolResponse)
def get_tool(tool_id: int, db: Session = Depends(get_db)):
    """获取工具详情"""
    service = ToolService(db)
    tool = service.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    return tool
```

### 第二部分：Service 层规范

#### 核心原则

- ✅ **单一职责**：每个 Service 类只负责一个业务领域
- ✅ **依赖注入**：通过构造函数注入数据库会话
- ✅ **事务管理**：Service 方法内部处理事务提交/回滚

#### 标准 Service 模板

```python
from sqlalchemy.orm import Session
from app.models.tool import Tool
from app.schemas.tool import ToolCreate

class ToolService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, tool_data: ToolCreate) -> Tool:
        """创建工具"""
        tool = Tool(**tool_data.dict())
        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)
        return tool

    def get(self, tool_id: int) -> Tool | None:
        """获取工具"""
        return self.db.query(Tool).filter(Tool.id == tool_id).first()
```

### 第三部分：数据库操作规范

#### 核心原则

- ✅ **使用 SQLAlchemy ORM**：禁止直接写 SQL（除非性能优化需要）
- ✅ **使用 Session 管理事务**：禁止手动管理连接
- ✅ **使用 Pydantic 验证输入**：所有 API 输入必须经过 Pydantic 模型验证
- ❌ **禁止** 在路由函数中直接操作数据库

### 第四部分：错误处理规范

#### 核心原则

- ✅ **使用 HTTPException**：FastAPI 标准异常
- ✅ **统一错误格式**：`{"detail": "错误信息"}`
- ✅ **记录异常日志**：所有 500 错误必须记录完整堆栈
- ❌ **禁止** 吞掉异常（空 except）
- ❌ **禁止** 返回自定义错误格式

---

## 前端开发规范（React + TypeScript）

### 第一部分：组件设计

#### 核心原则

- ✅ **函数组件 + Hooks**：禁止使用类组件
- ✅ **单一职责**：每个组件只负责一个功能
- ✅ **Props 类型定义**：所有 Props 必须定义 TypeScript 接口
- ❌ **禁止** 在组件中直接调用 API，必须通过 Service 层

#### 标准组件模板

```typescript
import React from 'react';

interface ToolCardProps {
  id: number;
  name: string;
  description: string;
  onClick: (id: number) => void;
}

export const ToolCard: React.FC<ToolCardProps> = ({ id, name, description, onClick }) => {
  return (
    <div className="card" onClick={() => onClick(id)}>
      <h3>{name}</h3>
      <p>{description}</p>
    </div>
  );
};
```

### 第二部分：状态管理规范

#### 核心原则

- ✅ **使用 Zustand**：全局状态使用 Zustand 管理
- ✅ **局部状态用 useState**：组件内部状态使用 useState
- ✅ **异步数据用 React Query**：服务端状态使用 React Query（如果已集成）
- ❌ **禁止** 使用 Redux（项目统一用 Zustand）

#### 标准 Store 模板

```typescript
import { create } from 'zustand';

interface ToolStore {
  tools: Tool[];
  loading: boolean;
  fetchTools: () => Promise<void>;
}

export const useToolStore = create<ToolStore>((set) => ({
  tools: [],
  loading: false,
  fetchTools: async () => {
    set({ loading: true });
    try {
      const tools = await toolService.getAll();
      set({ tools, loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },
}));
```

### 第三部分：API 调用规范

#### 核心原则

- ✅ **统一 Service 层**：所有 API 调用封装在 `services/` 目录
- ✅ **类型安全**：请求和响应必须定义 TypeScript 类型
- ✅ **错误处理**：统一在 Service 层处理错误
- ❌ **禁止** 在组件中直接使用 `fetch` / `axios`

#### 标准 Service 模板

```typescript
import axios from 'axios';
import { Tool, ToolCreate } from '../types/tool';

const API_BASE = import.meta.env.VITE_API_BASE_URL;

export const toolService = {
  getAll: async (): Promise<Tool[]> => {
    const response = await axios.get(`${API_BASE}/api/tools`);
    return response.data;
  },

  create: async (tool: ToolCreate): Promise<Tool> => {
    const response = await axios.post(`${API_BASE}/api/tools`, tool);
    return response.data;
  },
};
```

### 第四部分：样式规范

#### 核心原则

- ✅ **使用 Tailwind CSS**：优先使用 utility classes
- ✅ **自定义样式用 CSS Modules**：复杂样式使用 `.module.css`
- ✅ **响应式设计**：必须适配移动端（使用 `sm:`、`md:`、`lg:` 前缀）
- ❌ **禁止** 使用内联样式（`style={{}}`）
- ❌ **禁止** 引入外部 CSS 框架（Bootstrap、Ant Design 等）

---

## 热加载与重启规则（强制）

**本规范整合了热加载、服务重启的所有要求。**

### 第一部分：热加载判断逻辑

#### 不需要重启的场景（热加载自动生效）

- **前端源码**：修改 `.tsx`、`.ts`、`.css` 等源码文件（Vite 热重载）
- **后端源码**：修改 `.py` 文件（uvicorn --reload 自动重载）

#### 需要重启的场景

- **前端配置**：修改 `vite.config.ts`、`tsconfig.json`、`.env`、`package.json` 等配置文件
- **后端配置**：修改 `config.py`、`.env` 等配置文件
- **依赖变更**：修改 `requirements.txt` 或 `package.json` 后

### 第二部分：服务管理

#### 核心原则

- ✅ **必须使用 dev-services.py**：统一通过脚本管理服务
- ❌ **禁止** 手动使用 `uvicorn` 或 `npm run dev` 启动服务
- ❌ **禁止** 在仅修改了源码文件后重启服务（热加载会自动生效）

#### 标准流程

```bash
# 修改代码后
# 1. 等待热加载自动生效（前端/后端源码）
# 2. 如果需要重启（配置变更）
python dev-services.py restart

# 或仅重启特定服务
python dev-services.py restart backend  # 仅后端
python dev-services.py restart frontend # 仅前端

# 3. 确认服务状态
python dev-services.py status
```

---

## 测试规范（强制）

### 第一部分：后端测试（pytest）

#### 核心原则

- ✅ **单元测试**：Service 层必须有单元测试
- ✅ **集成测试**：关键 API 必须有集成测试
- ✅ **测试覆盖率**：核心业务逻辑覆盖率 ≥ 80%
- ✅ **使用 pytest**：统一使用 pytest 框架
- ❌ **禁止** 使用 unittest（项目统一用 pytest）

#### 标准测试模板

```python
import pytest
from app.services.tool_service import ToolService
from app.schemas.tool import ToolCreate

def test_create_tool(db_session):
    """测试创建工具"""
    service = ToolService(db_session)
    tool_data = ToolCreate(name="测试工具", description="测试描述")
    tool = service.create(tool_data)

    assert tool.id is not None
    assert tool.name == "测试工具"
    assert tool.description == "测试描述"

def test_get_tool_not_found(db_session):
    """测试获取不存在的工具"""
    service = ToolService(db_session)
    tool = service.get(99999)
    assert tool is None
```

### 第二部分：前端测试（Vitest + React Testing Library）

#### 核心原则

- ✅ **组件测试**：关键组件必须有测试
- ✅ **使用 React Testing Library**：测试用户行为而非实现细节
- ✅ **使用 Vitest**：统一使用 Vitest 框架（与 Vite 集成）
- ❌ **禁止** 使用 Jest（项目统一用 Vitest）

#### 标准测试模板

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { ToolCard } from './ToolCard';

describe('ToolCard', () => {
  it('renders tool name and description', () => {
    render(
      <ToolCard
        id={1}
        name="测试工具"
        description="测试描述"
        onClick={() => {}}
      />
    );

    expect(screen.getByText('测试工具')).toBeInTheDocument();
    expect(screen.getByText('测试描述')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(
      <ToolCard
        id={1}
        name="测试工具"
        description="测试描述"
        onClick={handleClick}
      />
    );

    fireEvent.click(screen.getByText('测试工具'));
    expect(handleClick).toHaveBeenCalledWith(1);
  });
});
```

---

## 安全规范（强制）

### 第一部分：敏感信息管理

#### 核心原则

- ✅ **使用环境变量**：API 密钥、数据库密码等通过 `.env` 管理
- ✅ **禁止硬编码**：代码中禁止硬编码任何敏感信息
- ✅ **禁止提交 .env**：`.env` 文件必须在 `.gitignore` 中
- ❌ **禁止** 在代码中写死密码、密钥、Token
- ❌ **禁止** 在日志中打印敏感信息

### 第二部分：API 安全

#### 核心原则

- ✅ **JWT 认证**：所有需要认证的 API 必须使用 JWT
- ✅ **权限校验**：敏感操作必须校验用户权限
- ✅ **输入验证**：所有 API 输入必须经过 Pydantic 验证
- ✅ **SQL 注入防护**：使用 SQLAlchemy ORM，禁止拼接 SQL
- ❌ **禁止** 信任客户端输入
- ❌ **禁止** 返回详细错误信息给前端（如数据库错误堆栈）

### 第三部分：CORS 配置

#### 核心原则

- ✅ **明确允许的域名**：只允许特定域名跨域访问
- ✅ **生产环境限制**：生产环境禁止使用 `*` 通配符
- ✅ **开发环境宽松**：开发环境可允许 `http://localhost:5178`

---

## 部署规范（强制）

### 第一部分：部署前检查

#### 核心原则

- ✅ **本地验证通过**：所有测试必须通过
- ✅ **代码规范检查**：`ruff check` 和 `npm run lint` 必须无错误
- ✅ **构建成功**：`npm run build` 必须成功
- ✅ **数据库迁移**：如果有数据库变更，必须先执行迁移
- ❌ **禁止** 在未测试的情况下部署

### 第二部分：部署流程

#### 标准部署流程

```bash
# 1. 更新代码
git pull --rebase origin master

# 2. 安装依赖（如果有变更）
cd backend && pip install -r requirements.txt
cd frontend && npm install

# 3. 运行测试
cd backend && pytest
cd frontend && npm run test

# 4. 构建前端
cd frontend && npm run build

# 5. 重启服务
cd .. && python dev-services.py restart

# 6. 验证部署
python dev-services.py status
```

---

## 常用 API 端点

### 后端 API 文档

启动后端后访问：
- Swagger UI: http://localhost:19092/docs
- ReDoc: http://localhost:19092/redoc

### 核心 API 端点

| 模块 | 路径前缀 | 说明 |
|------|---------|------|
| 认证 | `/api/auth` | 用户登录、注册、JWT |
| 工具集合 | `/api` | OCR、ASR、数据库、Redis、SSH 等 |
| Agent | `/api/v1` | Product Manager Agent (LLM) |

---

## 测试账号（仅供本地浏览器验证使用）

- **用户名**: `<由部署者自行配置>`
- **密码**: `<由部署者自行配置>`
- **用途**: Claude 在本地通过 `agent-browser` 自动化验证需要登录态的页面（如 Token Usage、个人中心等）时使用
- **注意**: 开源版本不内置默认账号，部署者请在 `.env` 中自行配置；仅限本地开发环境验证，不得用于生产或外部分享

---

**END**
