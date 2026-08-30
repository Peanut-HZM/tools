# P2-③ 多模态沙箱（file_read / file_write / code_execute）设计文档

**日期**：2026-08-30
**Phase**：3-Plan-2-3（对应原 P2 列表第 7 项 "多模态工具（file_read、file_write、code_execute 沙箱）"）
**状态**：已实现（2026-08-30；验证：pytest tests/harness 704 passed / 前端 build + tsc 通过）
**对应规划 ID**：Phase 3 设计文档 §11.4 P2 列表第 7 项

---

## 1. 背景与目标

### 1.1 背景

当前 Agent 工具集（web_search / db_query / image_gen / memory / skills）均为"无副作用服务调用"，Agent 无法处理文件与运行代码。Phase 1 已有消息级多模态附件（`messages.attachments` JSONB）与 OSS 存储服务，但缺少 Agent 侧的文件操作与代码执行能力——这限制了数据处理、报告生成、格式转换类任务。

### 1.2 目标

为 Agent 提供三个新内置工具（`agent.sandbox_enabled=True` 时可用）：

1. **file_read(path)**：读取工作区内文本文件（截断保护）
2. **file_write(path, content, mode)**：写入工作区文件（overwrite / append）
3. **file_list(path?)**：列出工作区文件
4. **code_execute(code, language?, timeout_seconds?)**：在工作区内执行 Python 代码，返回 stdout/stderr/退出码

### 1.3 非目标（明确不做）

- 不做容器/微 VM 级隔离（Docker/gVisor）——**轻量沙箱**：进程级隔离 + 工作区路径限制 + 超时/输出上限；生产如需强隔离另立 plan（见 §5）
- 不做非 Python 语言执行（language 参数预留校验，v1 仅 python）
- 不做依赖安装/pip——`python -I` 隔离模式，仅标准库
- 不做文件版本历史/回收站
- 不做 OSS 同步——工作区为后端本地目录；导出到 OSS 是候选续作

---

## 2. 架构总览

### 2.1 工作区模型

```
backend/data/agent_workspaces/
└── {agent_id}/
    └── {user_id}/            # 按 (agent, user) 隔离，与记忆体系一致
        └── ...（Agent 读写的工作文件）
```

- 根目录：`WORKSPACE_ROOT` 环境变量可覆盖，默认 `<backend>/data/agent_workspaces`
- **路径安全**：所有工具入参 path 先 join 再 `resolve()`，结果必须 `is_relative_to(workspace_root)`，否则拒绝（防 `../` 逃逸与符号链接逃逸）

### 2.2 工具定义

| 工具 | 参数 | 行为 |
|---|---|---|
| `file_read` | path(必填), max_bytes(可选，默认 64KB，上限 1MB) | 文本读取（utf-8，decode 失败→error）；超限截断并标注 `truncated: true` |
| `file_write` | path(必填), content(必填), mode(overwrite/append，默认 overwrite) | 写入；单次上限 1MB；自动创建父目录 |
| `file_list` | path(可选，默认工作区根) | 递归列出 {path, size_bytes}，上限 200 条 |
| `code_execute` | code(必填), language(可选，仅 python), timeout_seconds(可选，默认 15，上限 30) | 子进程执行，cwd=工作区；返回 {stdout, stderr, exit_code, timed_out} |

### 2.3 code_execute 执行模型

```
code_execute(code, timeout)
    │
    ▼
subprocess.run(
    [sys.executable, "-I", "-c", code],   # -I：隔离模式（无 user site / 忽略 PYTHONPATH）
    cwd=workspace_dir,                    # 工作区为 cwd，代码可用相对路径访问工作文件
    capture_output=True,
    timeout=timeout,                      # 超时 kill 进程
    text=True, encoding="utf-8", errors="replace",
)
    │
    ▼
{stdout: 截断至 10KB, stderr: 截断至 10KB, exit_code, timed_out}
```

- 门控：`Agent.sandbox_enabled`（新列 Boolean default False），四个工具 `is_available` 同一查询（复用 memory/skill 工具的门控模式，异常保守 False）
- 注册：`chat_stream.py` 与其他 builtin 一起注册

### 2.4 组件布局

```
backend/app/
├── models/agent.py                      # + sandbox_enabled 列
├── services/harness/
│   ├── workspace.py                     # 新增：WorkspaceService（路径安全 + 读写 + 列表）
│   └── tools/
│       ├── file_read.py                 # 新增
│       ├── file_write.py                # 新增
│       ├── file_list.py                 # 新增
│       └── code_execute.py              # 新增
├── api/routes/chat_stream.py            # 注册 4 个工具
├── api/routes/agents.py                 # 白名单 + 序列化 + sandbox_enabled
└── alembic/versions/20260830c_sandbox_enabled.py

frontend/src/
├── services/agentApi.ts                 # 类型 +字段
└── components/Admin/AgentManagement.tsx # sandbox 开关（镜像 procedural 模式）
```

---

## 3. 关键设计

### 3.1 安全模型（轻量沙箱边界）

| 防护 | 机制 | 限制（明示） |
|---|---|---|
| 路径逃逸 | resolve + is_relative_to 白名单 | 符号链接若指向外部目录，resolve 后同样被拒 |
| 资源耗尽 | 单文件 1MB / 输出 10KB 截断 / 超时 30s 上限 / file_list 200 条 | 不限磁盘总量（候选续作配额） |
| 进程隔离 | `python -I` 子进程，cwd=工作区，超时 kill | **无网络/文件系统强隔离**：子进程仍可访问宿主 FS 与网络。信任模型=启用该开关的 admin 明知此风险（与 stdio MCP 同级） |
| 误启用风险 | 默认关闭（sandbox_enabled=False），admin 逐 Agent 开启 | 同上 |

### 3.2 为什么 per-(agent, user) 目录而非全局

与记忆/技能的隔离模型一致：一个用户教 Agent 处理的文件不应泄漏给其他用户。同一 agent 不同用户的任务文件天然隔离。

### 3.3 错误处理表

| 场景 | 行为 |
|---|---|
| path 逃逸工作区 | `ToolResult.error("path 超出工作区范围")` |
| 文件不存在 | `ToolResult.error("文件不存在: ...")` |
| decode 失败（二进制） | `ToolResult.error("非文本文件")` |
| code_execute 超时 | 返回 `timed_out: true` + 已捕获的部分输出（kill 后 run 抛 TimeoutExpired，捕获 stdout/stderr） |
| code_execute 非零退出 | 正常返回 exit_code 与 stderr（不是 error——失败输出对 LLM 同样有价值） |
| 未启用 sandbox | 工具不出现在可用列表 |
| Windows/Linux 差异 | 统一 `sys.executable -I`；路径用 pathlib；超时 kill 语义跨平台一致 |

---

## 4. 测试策略

| 文件 | 用例 |
|---|---|
| `test_workspace_service.py` | 路径安全（`../` 逃逸拒绝/绝对路径拒绝/嵌套正常）、读写、append、截断、file_list 上限、自动建父目录 |
| `test_code_execute_tool.py` | 正常执行/非零退出/超时 kill（sleep 超限）/stdout 截断/工作区 cwd（代码读工作区文件）/门控开关 |
| `test_file_tools.py` | 三个文件工具全分支 + 门控 |
| `test_models.py` 追加 | sandbox_enabled 列 |
| `test_admin_agents_api.py` 追加 | 白名单可更新 sandbox_enabled |
| 前端 | build + tsc |

---

## 5. 已知限制 / 不做清单

| 不做 | 留给 |
|---|---|
| 容器级隔离（Docker/gVisor/微 VM） | 生产强隔离需求时另立 plan |
| 非 Python 语言 | 候选续作 |
| 依赖安装（pip/uv 预热环境） | 候选续作（预热镜像方案） |
| 工作区配额（磁盘上限） | 候选续作 |
| OSS 导出/持久化 | 候选续作 |
| 流式输出（stdout 实时回传） | 候选续作 |

---

## 6. 决策记录

### 6.1 为什么不做容器隔离

容器是部署面变更（Windows 开发机不可用、生产需要镜像仓库与运行时依赖），远超单 plan 范围。进程级轻量沙箱 + 默认关闭 + admin 显式开启，已覆盖"受控试点"场景；文档明示边界，强隔离作为独立 plan（可复用本 plan 的 WorkspaceService 接口，仅替换执行器）。

### 6.2 为什么失败退出码不算 ToolResult.error

LLM 需要 stderr/exit_code 来自我修正（这正是 code_execute 的价值）。只有基础设施故障（超时无法启动、路径非法）才返回 error。

---

## 7. 参考 / 相关

- `backend/app/services/harness/tools/memory_read.py` —— 门控与参数校验模式
- `backend/app/services/harness/tools/skill_save.py` —— `_check_procedural_enabled` 同构门控
- `backend/app/services/oss_service.py` —— 候选续作（OSS 导出）的对接面
