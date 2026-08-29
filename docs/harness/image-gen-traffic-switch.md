<!-- docs/harness/image-gen-traffic-switch.md -->
# 图像生成流量切换 + Dify 删除操作手册

## 概述

本手册描述 IMAGE_GEN_BACKEND 三阶段切换流程（dify → dual → harness），以及最终删除 Dify 代码的操作步骤。

## 当前状态

经过 P2-Plan-3 已实现：
- 配置项 `IMAGE_GEN_BACKEND`（默认 `dify`，保留回滚位）
- `ImageGenBackendFactory` 支持 3 模式
- chat_stream image_gen 工具调用自动按模式 dispatch
- 旧 image_generation 路由通过 factory 选择执行器
- dual 模式输出结构化指标日志（`image_gen_metric` 字段）

## 阶段 1: 双写（dual）

### 启用

设置环境变量：
```bash
# .env 或部署环境变量
IMAGE_GEN_BACKEND=dual
```

重启服务：
```bash
python dev-services.py restart
```

### 监控指标（1 周）

每日检查以下指标：

#### 1. 一致性
```bash
# 拉取最近 100 次调用的一致性
grep '"image_gen_metric"' backend.log | tail -100 | jq -s '
  map(select(.backend == "dual")) |
  {
    total: length,
    consistent: map(select(.consistent == true)) | length,
    rate: ((map(select(.consistent == true)) | length) / length)
  }
'
```

**通过标准**：一致性比率 ≥ 95%

#### 2. harness 成功率
```bash
grep '"image_gen_metric"' backend.log | tail -100 | jq -s '
  map(.primary_success) | add / length
'
```

**通过标准**：≥ 98%

#### 3. latency 对比
```bash
grep '"image_gen_metric"' backend.log | tail -100 | jq -s '
  {
    harness_p50: (map(.elapsed_ms_primary) | sort | .[length/2]),
    dify_p50: (map(.elapsed_ms_secondary) | sort | .[length/2])
  }
'
```

**期望**：harness latency 应与 Dify 持平或更优

#### 4. 失败模式分析
```bash
grep '"image_gen_metric"' backend.log | tail -100 | jq -s '
  map(select(.consistent == false)) |
  map(.diff_reasons) |
  flatten |
  group_by(.) |
  map({reason: .[0], count: length})
'
```

重点关注 `success_diff` 类目：若 harness 失败而 Dify 成功，需调查。

### 回滚

任何指标异常时，立即回滚：
```bash
IMAGE_GEN_BACKEND=dify
python dev-services.py restart
```

## 阶段 2: harness-only

### 前置条件

阶段 1 持续 1 周，所有指标通过。

### 启用

```bash
IMAGE_GEN_BACKEND=harness
python dev-services.py restart
```

Dify 代码保留但不调用，可随时回滚到 `dual` 或 `dify`。

### 验证（1 周）

观察 harness 单独运行：
- 成功率无显著下降
- 用户无报错投诉
- 性能稳定

### 回滚

```bash
IMAGE_GEN_BACKEND=dual  # 或 dify
```

## 阶段 3: 删除 Dify 代码

**⚠️ 不可逆操作，需二次确认。**

### 前置条件

阶段 2 持续 1 周无异常。

### 删除清单

后端（待删除文件，执行前需以 grep 复核实际引用点）：
- `backend/app/services/dify_client.py`
- `backend/app/services/dify_config_service.py`
- `backend/app/services/image_gen/dify_backend.py`
- `backend/app/services/image_gen/base.py`
- `backend/app/services/image_gen/backends.py`
- `backend/app/services/image_gen/agent_orchestrator.py`
- `backend/app/services/image_gen/conversation_repo.py`
- `backend/app/services/image_gen/selfdev_backend.py`
- `backend/app/services/image_gen/tool_executor.py`
- `backend/app/services/image_gen/__init__.py`
- `backend/app/routes/image_generation.py`（旧路径，替换为 harness-only）
- `backend/app/routes/admin_image_generation.py`
- `backend/app/models/image_generation_models.py`
- `backend/app/models/image_gen_conversation.py`
- `backend/app/schemas/image_generation.py`
- `backend/app/services/image_generation_service.py`
- `backend/app/services/image_gen_history_service.py`（保留 OSS 逻辑迁移）
- `backend/app/services/image_gen_prompt_polisher.py`（已迁移到 harness）
- `backend/app/services/image_gen_retention_scheduler.py`（保留）
- `backend/app/llm/image_gen_base.py`
- `backend/app/llm/image_gen_factory.py`
- `backend/app/utils/image_gen_constants.py`

测试：
- `backend/tests/test_dify_*.py`
- `backend/tests/test_image_generation_*.py`（旧路径）
- `backend/tests/test_chat_text2img.py`

前端：
- admin 页面 Dify 配置入口
- 旧 ImageGen 调用代码（已由 ImageGenRenderer 替代）

DB：
- 删除 `image_gen_conversations` 表 + migration

### 操作步骤

1. 在 `agent-harness-phase2-plan3-cleanup` 分支执行删除
2. 删除上述文件
3. 修改 `main.py` 移除 Dify 相关路由注册
4. 修改 `app/models/__init__.py` 移除相关导入
5. 跑全量测试确保无遗漏引用
6. 创建 Alembic migration 删除 `image_gen_conversations` 表
7. 提交 PR 并请求二次 code review
8. 合并到 master

### 回滚方案

阶段 3 删除前确保已备份 master 分支（`git tag pre-dify-cleanup`）。如发现严重问题，可从 tag 回滚。

## 验证清单

### 阶段 1 完成
- [ ] IMAGE_GEN_BACKEND=dual 持续 1 周
- [ ] 一致性比率 ≥ 95%
- [ ] harness 成功率 ≥ 98%
- [ ] harness latency ≤ Dify latency
- [ ] 无重大失败模式聚集

### 阶段 2 完成
- [ ] IMAGE_GEN_BACKEND=harness 持续 1 周
- [ ] 用户无报错投诉
- [ ] 性能稳定

### 阶段 3 准备
- [ ] 备份 master 分支（`git tag pre-dify-cleanup`）
- [ ] 列出 Dify 引用点（grep -rn "dify\|Dify" backend/app backend/tests）
- [ ] PR 二次 review
