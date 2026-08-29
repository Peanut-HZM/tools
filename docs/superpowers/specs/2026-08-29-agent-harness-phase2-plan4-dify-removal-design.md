# Agent Harness — Dify 完全移除 设计文档

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完全移除 Dify 图像生成子系统，折叠流量切换基础设施，chat 路径直接使用 harness ImageGenTool。解决 P2-Plan-3 最终评审的 4 个 Important 缺口（通过消除产生缺口的机制本身）。

**Architecture:** Plan-3 阶段 1 的流量切换基础设施（Factory / 3 模式 / dual shadow / metrics）是为 Dify→Harness 过渡设计的。Dify 移除后这些机制失去存在意义。本设计直接删除整个过渡机制 + Dify 全家桶，保留 Plan-1/2 已验证的 harness 核心（ImageGenTool + ImageModelProvider + Prompt 润色 + ImageGenRenderer）。

**Tech Stack:** 同项目现有技术栈（FastAPI / SQLAlchemy / Pydantic v2 / Alembic / React 18）

## Global Constraints

- 所有对话和代码注释使用中文
- 最小变更：只删除/简化必要代码，不动 Plan-1/2 已稳定的 harness 核心
- 异常日志脱敏（继承自 Plan-1/2）
- 编译验证：修改后必须能正常编译
- 后端关键代码必须包含日志记录
- DB 迁移不可逆：drop 表前确认无外部依赖

## 范围

### 删除（Dify 相关）

**后端代码：**
- `backend/app/services/dify_client.py`
- `backend/app/services/dify_config_service.py`
- `backend/app/services/image_gen/` 整个目录（`dify_backend.py` / `base.py` / `backends.py` / `agent_orchestrator.py` / `conversation_repo.py` / `selfdev_backend.py` / `tool_executor.py` / `__init__.py`）
- `backend/app/routes/image_generation.py`（旧 Dify 路由）
- `backend/app/routes/admin_image_generation.py`（Dify 管理路由）
- `backend/app/models/image_generation_models.py`
- `backend/app/models/image_gen_conversation.py`
- `backend/app/schemas/image_generation.py`
- `backend/app/services/image_generation_service.py`
- `backend/app/services/image_gen_history_service.py`
- `backend/app/services/image_gen_prompt_polisher.py`（已迁移到 harness 的 `tools/image_gen.py` 内）
- `backend/app/services/image_gen_retention_scheduler.py`
- `backend/app/llm/image_gen_base.py`
- `backend/app/llm/image_gen_factory.py`
- `backend/app/utils/image_gen_constants.py`（如存在）

**Plan-3 流量切换基础设施（也一并删除）：**
- `backend/app/services/harness/image_gen_backend/` 整个目录（`factory.py` / `executors.py` / `metrics.py` / `__init__.py`）
- `chat_stream.py` 中的 `_run_image_gen_with_shadow` + `tool_call_start`/`tool_result` shadow hook
- `image_generation.py` 中的 `get_image_gen_executor` Depends 注入点（随路由删除）

**测试：**
- `backend/tests/test_dify_*.py`
- `backend/tests/test_image_generation_*.py`（旧）
- `backend/tests/test_chat_text2img.py`
- `backend/tests/harness/test_image_gen_backend_config.py`
- `backend/tests/harness/test_image_gen_backend_factory.py`
- `backend/tests/harness/test_image_gen_backend_metrics.py`
- `backend/tests/harness/test_image_gen_chat_stream_dual.py`
- `backend/tests/harness/test_image_gen_routes_dual.py`

**文档：**
- `docs/harness/image-gen-traffic-switch.md`（Phase 1/2/3 切换手册）—— 重写为「Dify 已移除 + harness 是唯一后端」的简短说明，或删除

### 修改（删除后的缝合）

- `backend/app/config/config.py` — 移除 `IMAGE_GEN_BACKEND` 字段 + Dify 相关配置字段（`DIFY_*`）
- `backend/app/main.py` — 移除 Dify 路由注册（`image_generation` / `admin_image_generation`）
- `backend/app/models/__init__.py` — 移除 Dify 模型导出（`image_generation_models` / `image_gen_conversation`）
- `backend/app/api/routes/chat_stream.py` — 移除 shadow hook，ImageGenTool 注册保持原样（Plan-1 已就位）
- `backend/app/api/routes/admin_tools.py` — 检查是否有 Dify 工具引用（Plan-2 添加了 Memory 工具，可能还引用了 ImageGenTool 旧路径）
- `backend/app/routes/__init__.py`（如存在）— 移除 `image_generation` 导入
- 前端：检查 admin 页面是否有 Dify 配置入口（如 admin_image_generation 的路由入口）

### DB 迁移

- Alembic migration drop `image_gen_conversations` 表（不可逆）
- 前置条件：grep 全代码库确认无外部引用

### 保留（Plan-1/2 成果）

- `backend/app/services/harness/tools/image_gen.py` — ImageGenTool（核心）
- `backend/app/services/harness/image_provider/` — Tongyi / Hailuo / Doubao + base / registry
- `backend/app/services/harness/tools/prompt_refine.py`（Plan-1 prompt refiner，如已独立存在）
- `backend/app/services/harness/tools/memory_read.py` / `memory_write.py`（Plan-2）
- `backend/app/models/agent_memory.py`（Plan-2）
- `frontend/src/components/Chat/ToolRenderers/ImageGenRenderer.tsx`
- Plan-1/2 全部测试

## 设计决策记录

| 决策点 | 选择 | 理由 |
|---|---|---|
| `IMAGE_GEN_BACKEND` env var | 完全删除 | harness 是唯一后端，flag 失去意义 |
| 旧 `image_generation` 路由 | 完全删除 | 依赖 Dify，移除后无意义 |
| `image_gen_conversations` 表 | Drop via migration | 不再写入，保留死数据无价值 |
| `ImageGenBackendFactory` + 执行器 | 删除 | 单一后端无需工厂 |
| Dual shadow / metrics | 删除 | 双写对比目的已达成（Dify 下线） |
| chat_stream shadow hook | 删除 | 无 Dify 可 shadow |

## 风险与回滚

**风险：**
- 删除文件过多可能误删有用代码（如 `image_gen_retention_scheduler` 是否独立于 Dify）
- DB drop 表不可逆
- 前端 admin 可能有 Dify 配置的 UI 残留

**缓解：**
- 实施前 grep 全代码库确认引用点
- DB drop 前先 `pg_dump` 备份（或至少 `SELECT COUNT(*) FROM image_gen_conversations` 记录现状）
- 实施过程中逐文件 commit，便于回滚

**回滚方案：**
- 实施过程中每个文件删除单独 commit，发现误删可从 git 历史恢复
- DB drop 是最后一步，实施完成前保留表

## 实施顺序

1. **Task 1**: Grep 确认文件清单 + 引用点（发现阶段，不写代码）
2. **Task 2**: DB 迁移准备（drop 表，先不执行，等所有代码改完）
3. **Task 3**: 删除 Plan-3 流量切换基础设施（factory / executors / metrics / shadow hook）+ 简化 chat_stream
4. **Task 4**: 删除旧 `image_generation` 路由 + 相关 schemas/services/models
5. **Task 5**: 删除 Dify 核心代码（dify_client / dify_config_service / image_gen/* 旧实现）
6. **Task 6**: 删除 Dify 配置（`IMAGE_GEN_BACKEND` / `DIFY_*`）+ 修改 main.py / models/__init__.py / admin 路由注册
7. **Task 7**: 删除测试 + 前端 Dify 残留 + 重写 runbook
8. **Task 8**: 执行 DB 迁移（drop 表）
9. **Task 9**: 集成测试 + 文档（确认 chat 路径图像生成仍可用，admin 页面正常）
10. **最终整分支评审**

## 验收标准

- `grep -rn "dify\|Dify\|IMAGE_GEN_BACKEND" backend/ frontend/` 返回 0（或仅剩文档历史记录）
- 全量 harness 测试通过
- chat 路径的图像生成可用（用户发消息「画一只猫」，返回图片）
- admin 页面正常加载（无 Dify 配置入口，无 broken imports）
- DB 中 `image_gen_conversations` 表已 drop
