# AGENTS.md - 项目智能代理规则

**所有项目规则详见 [CLAUDE.md](./CLAUDE.md)**

本文件是 CLAUDE.md 的引用入口，供不同 agent 加载。所有规则（Git 工作流、问题排查、部署流程、前后端规范等）均在 CLAUDE.md 中维护。

- 2026-10-29：按文件编辑器扩展名/重命名问题修复沉淀，CLAUDE.md 新增：文件名扩展名处理与重命名规范、IndexedDB 事务回调覆盖坑
- **最后同步：2026-10-29**
- 2026-10-26：按 Token 统计全原生化改造沉淀，CLAUDE.md 新增：用户目录访问必须使用真实家目录、Token 用量对账口径规范、新增 Agent 数据源接入门槛
- 2026-09-19：按全局通用规则对齐，CLAUDE.md 新增：数据库变更规范、验收测试数据规则（ZZTEST_）、语言规范、内部 ID 不展示在前端
- 初始版本：从 logistics-finance 项目规则适配而来
- 适配内容：
  - 删除 Java/Spring Boot/微服务特定规则
  - 删除 Vue3/Element Plus 前端特定规则
  - 删除菜单权限、对账业务等业务特定规则
  - 新增 Python/FastAPI 后端开发规范
  - 新增 React/TypeScript/Tailwind 前端开发规范
  - 新增 pytest/Vitest 测试规范
  - 保留通用工程实践（事后规则沉淀、问题排查、Git 工作流等）

**2026-10-13 新增规则**
- 「验收后提交与部署闭环规则（最高优先级）」—— 验收通过后必须提交推送远程；提交前必须先 fetch + pull --rebase --autostash；有部署脚本（deploy.py）必须服务器验收；未经允许禁止创建 worktree / 独立分支
- 「功能完成浏览器强制验收规则（最高优先级，绝对不允许跳过）」—— 代码写完 ≠ 完成，必须打开浏览器真实验收完整用户流程，逐条对照需求清单验全，未验收绝对禁止声称完成

---

## 快速参考

### 核心原则

1. **事后规则沉淀**：问题解决后必须沉淀规则，防止重复踩坑
2. **禁止 Mock 与兜底**：真实问题必须如实暴露，禁止掩盖
3. **问题排查强制规则**：必须找到代码级根因，禁止猜测
4. **Git 工作流**：统一使用 rebase，禁止 merge
5. **临时产物清理**：任务完成后必须清理所有临时文件
6. **禁止批量脚本修改**：所有代码修改必须逐个文件手动进行

### 技术栈

- **后端**: Python 3.10+ / FastAPI / SQLAlchemy / PostgreSQL
- **前端**: React 18 / TypeScript / Vite / Tailwind CSS / Zustand
- **存储**: 阿里云 OSS
- **测试**: pytest (后端) / Vitest (前端)

### 常用命令

```bash
# 服务管理
python dev-services.py              # 启动服务
python dev-services.py restart      # 重启服务
python dev-services.py status       # 查看状态

# 后端
cd backend
uvicorn app.main:app --reload --port 19092
ruff check .
pytest

# 前端
cd frontend
npm run dev
npm run build
npm run test
```

### 关键规则

- ✅ 所有对话和代码注释使用中文
- ✅ 优先使用热重载，非必要不重启服务
- ✅ 修改后必须在浏览器中验收（前端视觉验证 + 后端集成验证）
- ✅ 后端关键代码必须包含日志记录
- ✅ 使用 `dev-services.py` 管理服务，不要手动启动
- ❌ 禁止批量脚本修改代码
- ❌ 禁止 Mock 与兜底
- ❌ 禁止猜测式修复
- ❌ 禁止只改代码不验收就声称"已修复"
- ❌ 禁止 `git pull`（不带 `--rebase`）
- ❌ 禁止 `git merge` 更新本地分支
- ❌ 禁止硬编码敏感信息

---

## 文件名扩展名处理与重命名规范（速查 — 必须遵守）

- ✅ 文件扩展名判断统一用 `frontend/src/utils/filenameUtils.ts`（`hasFileExtension` / `ensureFileExtension` / `resolveRenameName`），语义对齐后端 `os.path.splitext`
- ✅ **仅当文件名完全没有扩展名时**才补默认 `.md`；`a.kubeconfig`、`a.txt` 等已有后缀的文件名保持原样
- ✅ 所有创建文件入口（编辑器「新建」、文件树右键「新建文件」、打开文件夹弹窗「新建文件」）都必须走 `ensureFileExtension`
- ✅ 文件夹名不追加扩展名；重命名只允许同级改名，禁止 `/`、`\`、`.`、`..`
- ✅ 重命名后必须同步 `currentFilePath` / `expandedNodes` 前缀，并清理 IndexedDB 中 `directory_tree_` 旧前缀缓存
- ❌ 禁止在组件里裸写 `endsWith('.md')` 判断扩展名；❌ 禁止自行实现与 `os.path.splitext` 不一致的扩展名语义

详细规则见 [CLAUDE.md](./CLAUDE.md) 的「文件名扩展名处理与重命名规范」章节。

---

## 验收后提交与部署闭环规则（速查 — 必须遵守）

- ✅ 需求变更验收通过后必须提交并推送到远程仓库，禁止"验收完不提交、代码留在本地"
- ✅ 分支约束：**开发分支（非 master/main）**上验收通过后自动提交推送；**master/main 分支**必须用户明确同意后才可提交推送
- ✅ 提交前必须先 `git fetch` + `git pull --rebase --autostash` 更新代码，避免弄丢他人代码、避免冲突
- ✅ 有部署脚本（`deploy.py` 等）的项目必须部署到服务器验收；无部署脚本的项目本地真实验收
- ❌ 未经允许禁止创建 worktree；❌ 未经允许禁止创建单独分支

详细规则见 [CLAUDE.md](./CLAUDE.md) 的「验收后提交与部署闭环规则」章节。

---

## 功能完成浏览器强制验收规则（速查 — 必须遵守）

- ✅ 代码写完 ≠ 完成：必须打开浏览器真实操作完整用户流程验收（渲染 + 交互 + Console 无错 + 接口真实成功）
- ✅ 逐条对照需求清单验收，所有需求点都要验到（含异常路径），功能必须完整实现（与「代码修改后浏览器验收规则」互补）
- ❌ 绝对禁止未验收就声称"完成 / 已修复"；❌ 禁止以编译通过 / 接口 200 代替验收；❌ 禁止虚假验收报告

详细规则见 [CLAUDE.md](./CLAUDE.md) 的「功能完成浏览器强制验收规则」章节。

---

## 用户目录访问必须使用真实家目录（速查 — 必须遵守）

- ✅ `config.py` 在非桌面模式下把 `HOME` 覆盖为 `backend/data/cache`，此后进程内的 `HOME` 是**假家目录**
- ✅ 读用户真实家目录（`~/.claude` / `~/.codex` / `~/.kimi` / `~/.zcode` / `~/.minimax` / `~/.local/share/opencode` / `~/.openclaw` / `~/.copilot`）或反推用户级工具位置（nvm / npm-global / pnpm）时，必须用 `REAL_HOME` 或 `real_home()`
- ✅ 解析环境变量路径里的 `~` 必须基于真实家目录展开（走 `path_utils.expand_user_path` / `agent_readers.base.expand_user_path`）
- ❌ 禁止在这些场景使用 `Path.home()` / `os.path.expanduser("~")` / `os.environ["HOME"]`
- ❌ 禁止假设 `HOME` 等于用户家目录

详细规则见 [CLAUDE.md](./CLAUDE.md) 的「用户目录访问必须使用真实家目录」章节。

---

## Token 用量对账口径规范（速查 — 必须遵守）

- ✅ 逐模型比对用**可见四桶**（input / output / cache_creation / cache_read）like-for-like：ccusage 的 per-model 明细不含 extra 桶，原生 `total_tokens` 含
- ✅ extra 桶用**按日总额**校验（ccusage 的 `daily[].totalTokens` 含 extra）
- ✅ 活跃写入的数据源用**二次采样夹逼**区分漂移与真实偏差：`原生第一次 ≤ ccusage ≤ 原生第二次` 判为漂移，不算口径不一致
- ❌ 禁止把原生 `total_tokens` 直接与 ccusage per-model 四桶和比对
- ❌ 禁止把"数据源活跃写入导致的当天漂移"当成口径错误去改读取器
- ❌ 禁止 ccusage 不可用时做 shadow 对账（结果全是假阳性）
- ❌ 禁止拿 ccusage 合并日报（`agent=all`）当 per-agent 基准

详细规则见 [CLAUDE.md](./CLAUDE.md) 的「Token 用量对账口径规范」章节。

---

## 新增 Agent 数据源接入门槛（速查 — 必须遵守）

- ✅ source id 必须与 ccusage 的 agent id 完全一致（唯一键含 source，id 不一致会产生重复行、汇总翻倍）
- ✅ 必须跑 `python -m scripts.verify_native_readers` 达到**零差异且退出码 0**，并补对应单测，才算通过
- ✅ 通过后才能登记 `VERIFIED_AGENTS` 与 `NATIVE_READER_SOURCES`，两者必须同步
- ✅ `native` 模式下无原生读取器的 source 必须列为结构化错误（`SOURCE_NOT_COVERED`），禁止静默丢数据
- ✅ "已验证"指的是**在当前机器上实测通过**（文件格式、压缩、路径布局差异会直接推翻结论）
- ❌ 禁止未对账就登记为"已验证"（codex 曾因此在本机读到 0 条、采集停摆）

详细规则见 [CLAUDE.md](./CLAUDE.md) 的「新增 Agent 数据源接入门槛」章节。

---

## 与 logistics-finance 项目的差异

本项目的规则是从 logistics-finance 项目适配而来，主要差异：

### 已删除的规则（不适用于本项目）

- ❌ keep-alive 缓存命名规则（Vue 特有）
- ❌ 物理删除实现规则（Java/MyBatis 特有）
- ❌ 业务表禁止冗余组织/部门字段（logistics-finance 业务）
- ❌ MyBatis-Plus 写法规则（Java 特有）
- ❌ 菜单与权限管理规则（logistics-finance 复杂权限系统）
- ❌ @RequiresPermission 通配符规则（Spring Security 特有）
- ❌ API 路由与 Gateway 配置规则（微服务特有）
- ❌ 双前端菜单独立性规则（logistics-finance 多前端）
- ❌ 移动端样式规则（小程序特有）
- ❌ 小程序包大小规则（Taro 特有）
- ❌ OCR 服务规则（logistics-finance 业务）
- ❌ 对账数据生成规则（logistics-finance 业务）
- ❌ 实体 update 方法的 String 字段规则（Java 特有）
- ❌ 内部 ID 字段不在前端页面展示规则（logistics-finance 业务）
- ❌ 清理与删除脚本必须先 SELECT 精确 ID 规则（logistics-finance 数据清理）
- ❌ 数据库唯一约束治理规则（logistics-finance 数据治理）
- ❌ 数据库操作执行方式强制规则（logistics-finance 数据库管理）
- ❌ 动态路由注册规则（Vue 特有）
- ❌ 动态 import 加载失败兜底规则（Vue 特有）

### 已新增的规则（本项目特有）

- ✅ FastAPI 路由设计规范
- ✅ SQLAlchemy ORM 使用规范
- ✅ React 函数组件 + Hooks 规范
- ✅ Zustand 状态管理规范
- ✅ Tailwind CSS 样式规范
- ✅ pytest 测试规范
- ✅ Vitest 测试规范
- ✅ FastAPI 错误处理规范
- ✅ CORS 配置规范
- ✅ JWT 认证规范

### 已保留并适配的规则（通用工程实践）

- ✅ 事后规则沉淀机制
- ✅ 禁止批量脚本修改代码
- ✅ 临时产物及时清理
- ✅ 禁止 Mock 与兜底
- ✅ 问题排查强制规则
- ✅ 客户端代码路径 DRY
- ✅ Git 工作流规范（rebase）
- ✅ 配置文件管理规范
- ✅ 浏览器进程管理
- ✅ ID 字段类型规则（适配 Python）
- ✅ 日志管理规范（适配 Python logging）
- ✅ 热加载与重启规则（适配 dev-services.py）
- ✅ 部署规范（简化）
- ✅ 安全规范（通用部分）

---

## 规则演进记录

### 2026-10-26 - Token 统计全原生化改造沉淀

- 新增「用户目录访问必须使用真实家目录」—— HOME 被 config.py 覆盖后必须用 REAL_HOME / real_home()
- 新增「Token 用量对账口径规范」—— 可见四桶 / extra 桶 / 活跃写入采样漂移 三层口径分离
- 新增「新增 Agent 数据源接入门槛」—— source id 对齐 + 零差异对账 + 双处登记 + 未覆盖来源显式暴露
- 事故来源：ccusage 发现失败导致四个来源停采一天、codex 因 `.jsonl.zst` 读到 0 条、对账脚本 extra 桶与漂移误报

### 2026-09-13 - 初始版本

- 从 logistics-finance 项目规则适配
- 删除所有 Java/Spring Boot/Vue3 特定规则
- 新增 Python/FastAPI/React 技术栈规范
- 保留通用工程实践
- 简化部署流程（单机部署，无微服务）
- 调整日志规范（Python logging 模块）

---

**所有详细规则请参见 [CLAUDE.md](./CLAUDE.md)**

## 任务完整交付与提交门禁规则（速查 — 必须遵守）

- ✅ 规则文件（CLAUDE.md / AGENTS.md / README / docs / .md 等）修改直接提交，不需要验收
- ✅ 代码文件（.py / .tsx / .ts / .sql / 配置等）修改必须在完整真实验收后才能提交
- ✅ 完整验收定义（缺一不可）：服务无报错 + 所有问题已解决 + git diff 只含本任务改动 + 无业务破坏
- ✅ 即使不是自己修改导致的问题，也必须修复
- ✅ 接到变更任务后**绝对不允许停下任务**，必须完整交付
- ❌ 未验收就提交代码 = 虚假完成报告（最严重诚信问题）
- ❌ 中途停下导致问题遗留 = 未完成任务

详细规则见 [CLAUDE.md](./CLAUDE.md) 的「任务完整交付与提交门禁规则」章节。

---

## 前端服务启动与验收规范（速查 — 必须遵守）

- ✅ 前端启动只能用 `python dev-services.py`（前端 5178 / 后端 19092 由 dev-services.py 统一管理），禁止手动 `npm run dev` / `uvicorn --reload` 直接起服务
- ✅ 端口固定（前端 5178、后端 19092），禁止更换端口或加 `--port` 参数；禁止占用其他项目 / 其他服务的端口
- ✅ 前端源码修改靠 Vite 热重载、后端 `.py` 修改靠 uvicorn `--reload`，禁止仅改源码就重启
- ✅ 只有改「必须重启才生效」的配置 / 代码（`vite.config.ts` / `.env` / `package.json` / `requirements.txt` / 依赖变更）才重启
- ✅ 前端 / 后端已在运行时直接用端口号（5178 / 19092）打开服务验收，禁止重复启动（本地资源不足尤其禁止）
- ✅ 任何启动问题（端口冲突、依赖缺失、启动失败等）先与用户确认再处理

详细规则见 [CLAUDE.md](./CLAUDE.md) 的「前端服务启动与验收规范」章节。

---

## 多 Agent 并行协作保护规则（速查 — 最高优先级中的最高优先级）

- ✅ 多 Agent 同时执行任务修改代码时，**绝对不允许破坏其他 Agent 的任务和修改**；他人未提交改动 = 他人任务成果，只能合入不能覆盖/丢弃
- ✅ 需要修改的文件/区域正被其他 Agent 修改时，**必须等待对方完成修改后再处理**，禁止抢先修改、并行抢写同一文件
- ✅ 只动自己任务范围内的文件；确需触碰共享文件必须先读取最新内容、在保留他人全部改动的基础上追加
- ✅ checkout / reset / clean / stash / rebase / merge 前先 `git status` 识别并保护他人改动；提交只显式 `git add` 自己任务的文件，禁止 `git add .`
- ✅ 必须确保**所有 Agent 的最终任务都能完整、成功完成**，绝不弄丢任何一个任务
- ❌ 禁止 `checkout .` / `reset --hard` / `clean` / `stash clear` 作用于含他人改动的路径；❌ 弄丢任务 = 最严重诚信问题

详细规则见 [CLAUDE.md](./CLAUDE.md) 的「多 Agent 并行协作保护规则」章节。

---

## 浏览器验收强制使用内置浏览器（速查 — 最高优先级中的最高优先级）

- ✅ 所有 Agent 打开浏览器进行验收时，**必须最最最最优先使用自己工具的内置浏览器**（ZCode、Claude Desktop / Claude Code、ChatGPT/Codex、Kimi Code、MiniMax Code、OpenCode 等一切自带内置浏览器的工具）
- ❌ **绝对禁止**在有内置浏览器时启动外部浏览器（Chrome / Edge 等）或第三方浏览器工具代替验收
- ✅ 仅当本工具确实没有内置浏览器时，才允许回退其他方案，并在验收报告中说明原因
- ❌ 用外部浏览器代替内置浏览器得出的验收结论无效，必须改用内置浏览器重新验收后才算交付
- 详细规则见 [CLAUDE.md](./CLAUDE.md) 的「浏览器验收强制使用本工具内置浏览器」章节。

**END**


---

## 页面轮询/定时刷新规范（强制）

适用于所有带轮询、定时刷新、手动"刷新"按钮的页面（数据看板、列表、监控页等）。

- ❌ **绝对禁止整页刷新**：数据更新禁止 `location.reload()`、`router.go(0)` 等整页重载；只能增量请求并更新需要更新的字段与数据块（唯一例外：前端部署后 chunk 加载失败的自愈刷新，见前端部署规范）。
- ✅ **保持用户状态不丢失**：局部响应式赋值（Vue 的 ref/reactive 局部 set、表格行 patch），必须保持用户输入、滚动位置、展开/选中、图表交互状态不丢失、不闪烁。
- ✅ **loading 全局最多一个**：同一页面同一时刻最多存在一个整页级 loading（遮罩/骨架屏），禁止多个 loading 重叠或先后叠加；局部小部件只允许自身区域内轻量加载状态，不得再次挂全屏遮罩。
- ✅ **失败不炸页**：刷新失败保留原数据并轻提示，同样禁止触发整页刷新。

---

## 单测验收最小化规则（强制）

- 单测验收默认**最小化执行**：只运行与本次代码变更直接相关的单测，禁止无差别全量跑测，不浪费 token 与时间。
- 定位方法：按「变更文件 → 所属模块/包 → 对应测试类」映射执行；Maven 用 -pl <模块> 限定模块 + -Dtest=XxxTest,YyyTest 指定测试类；Vitest/Jest 直接传测试文件路径；前端类型检查同理只查受影响项目。
- 影响面扩大原则（唯一例外）：变更涉及公共模块、共享工具类、接口/DTO、数据库迁移、全局配置时，必须把受影响的下游模块相关单测一并纳入；无法判定影响面时才允许扩大范围，且需说明理由。
- 验收编译同理：优先增量编译（如 mvn -pl <模块> -am compile、前端增量 tsc），非发布构建避免每次全量 clean package。
- 全量跑测仅限三种场景：发布前最终验收、架构级重构、任务规则中明确要求全量回归。

---

**2026-10-28 新增规则（用户明令，CodeProjects 全目录生效）**

## 设计/计划文档强制循环审查规则（最高优先级）

- ✅ 写完任何设计文档（specs/*-design.md）、实施计划（docs/plans/、docs/superpowers/plans/*.md）、openspec 变更、SQL 迁移脚本、代码变更方案后，**必须调用 spec-review-loop 技能做多轮循环审查**（连续 2 轮无新发现才终止，上限 10 轮；通用维度 SQL 幂等性/设计完整性必审，Java/Spring 等栈插件按技术栈加载）
- ✅ 审查发现持久化为台账（docs/reviews/YYYY-MM-DD-<topic>-review.md）：纯文档缺陷直接修复，关联代码白名单外问题记「待确认」由用户决策；全部发现修复/决策后才允许进入实施或提交
- ❌ 禁止未经循环审查就声称设计/计划完成；❌ 禁止跳过审查直接实施；❌ 绝对禁止虚假报告任务完成
