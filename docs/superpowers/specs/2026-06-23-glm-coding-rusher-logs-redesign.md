---
author: Claude
created_at: 2026-06-23
purpose: GLM Coding Rusher 日志/记录/交互 重构设计文档
---

# GLM Coding Rusher 日志与交互重构

## 背景

`http://localhost:5178/tools/glm-coding-rusher` 页面存在以下问题：

1. **日志 404**：后端 `/logs` 函数缺少 `@router.get("/logs")` 装饰器，前端每秒轮询都 404
2. **无历史记录**：日志只存内存 `_logs_buffer`，重启丢失；DB 模型 `GlmCodingRusherLog` 存在但从未使用
3. **无抢购记录**：没有持久化的任务概念，无法回溯"上次抢到了没"
4. **成功后无反馈**：后端停止循环并打开支付窗口，但前端无特殊提示，用户不知道成功了
5. **无效轮询**：前端每 1s 轮询 4 个接口，空闲时也不停

## 方案

方案 A：修复 + DB 持久化 + 弹窗阻断 + 右侧分区布局。不引入 WebSocket。

---

## 后端改动

### 1. 修复 `/logs` 404

**文件**：`backend/app/routes/glm_coding_rusher.py`

给 `logs` 函数（第 173 行）补上路由装饰器，并增加 `task_id` 可选参数：

```python
@router.get("/logs")
def logs(limit: int = 100, task_id: str = None):
    """获取抢购日志"""
    items = get_task_logs(task_id=task_id, limit=limit)
    return RusherLogListResponse(
        items=[RusherLogItem(**item) for item in items],
        total=len(items),
    )
```

### 2. 新增抢购记录表 `glm_coding_rusher_tasks`

**文件**：`backend/app/models/glm_coding_rusher_models.py`

```
字段：
- id (String PK)            - 任务 ID（同 task_id，UUID）
- user_id (String)           - 用户 ID
- config_snapshot (Text/JSON) - 启动时的配置快照（JSON 字符串）
- result (String)            - 结果：success / timeout / stopped / error
- refresh_count (Integer)    - 总刷新次数
- payment_url (String, nullable) - 支付页 URL（仅成功时有）
- started_at (DateTime)      - 开始时间
- ended_at (DateTime, nullable) - 结束时间
- created_at (DateTime)      - 记录创建时间（server_default now）
```

### 3. 日志双写（内存 + DB）

**文件**：`backend/app/services/glm_coding_rusher_service.py`

`_append_log` 改为同时写入：
- `_logs_buffer`（内存，保留最近 500 条，给前端轮询实时用）
- DB 表 `glm_coding_rusher_logs`（永久保存）

需要注入 DB session。通过 `app.database.get_db` 获取。

### 4. 任务生命周期钩子

在以下位置写入/更新 `glm_coding_rusher_tasks` 表：

| 时机 | 操作 |
|------|------|
| `start_rush()` 成功启动 | INSERT 新记录，result='running' |
| `_execute_rush` 成功点击 | UPDATE result='success', payment_url, ended_at |
| `_execute_rush` 超时 | UPDATE result='timeout', refresh_count, ended_at |
| `_execute_rush` 异常 | UPDATE result='error', ended_at |
| `stop_rush()` 手动停止 | UPDATE result='stopped', ended_at |

### 5. 新增 API

| 路由 | 用途 | 响应 |
|------|------|------|
| `GET /tasks` | 抢购记录列表（按 started_at 倒序） | `{ items: TaskSummary[], total: int }` |
| `GET /tasks/{task_id}` | 单个任务详情 | `TaskDetail`（含配置快照、结果、支付 URL） |
| `GET /tasks/{task_id}/logs` | 某个任务的全部日志 | `LogListResponse` |

### 6. 新增 Schema

**文件**：`backend/app/schemas/glm_coding_rusher_schemas.py`

```python
class TaskSummary(BaseModel):
    id: str
    result: str          # running / success / timeout / stopped / error
    target_package: str  # 从 config_snapshot JSON 中提取
    started_at: datetime
    ended_at: datetime | None
    refresh_count: int
    payment_url: str | None

class TaskDetail(TaskSummary):
    config_snapshot: dict  # 完整配置快照
```

---

## 前端改动

### 1. 按钮状态机

**文件**：`frontend/src/components/Tools/GlmCodingRusher/GlmCodingRusher.tsx`

| 状态 | 按钮文字 | 是否可点 | 触发条件 |
|------|---------|---------|---------|
| 待命 | 开始抢购 | ✅（需已登录） | `!is_running && phase !== 'success'` |
| 启动中 | 抢购中... | ❌ 禁用 | 点击后立即（`justStarted=true`），直到轮询确认 `is_running=true` |
| 运行中 | 停止抢购 | ✅ | `is_running === true` |
| 成功 | 再次抢购 | ✅ | `phase === 'success'`，弹窗关闭后 |

实现：新增本地 state `justStarted: boolean`，点击 `handleStart` 时立即置 true，轮询发现 `is_running=true` 后清除。

### 2. 成功弹窗（Modal）

检测到 `status.current_phase === 'success'` 时自动弹出，内容：

```
┌─────────────────────────────────┐
│  ✅ 抢购成功！                    │
│                                 │
│  支付页面已打开，请完成支付        │
│                                 │
│  支付链接：                      │
│  https://open.bigmodel.cn/...   │
│                                 │
│  [在浏览器中打开]   [我知道了]    │
└─────────────────────────────────┘
```

行为：
- 弹窗期间**停止轮询**（clearInterval）
- 点"我知道了"关闭弹窗，恢复轮询
- 点"在浏览器中打开"打开 `payment_url`

### 3. 右侧面板分区

```
┌──────────────────────────┐
│ 📋 抢购记录              │  ← 上半区（固定高度 ~40%）
│ ┌────────────────────┐   │
│ │ 06/23 10:00 ✅ 成功 │   │  ← 每条记录：时间 + 结果 + 套餐
│ │ 06/22 10:00 ❌ 超时 │   │
│ │ 06/21 10:00 ⏹ 停止  │   │
│ └────────────────────┘   │
│                          │
│ 📝 实时日志              │  ← 下半区（flex-1 占满）
│ ┌────────────────────┐   │
│ │ 10:00:01 预热 启动..│   │
│ │ 10:00:02 刷新 按钮..│   │
│ └────────────────────┘   │
└──────────────────────────┘
```

- 上半区：调用 `GET /tasks` 获取记录列表
- 点击某条记录 → 下方日志切换为该任务的日志（`GET /logs?task_id=xxx`）
- 点击"全部" → 显示所有日志（`GET /logs`）

### 4. 轮询降频优化

| 状态 | 轮询间隔 |
|------|---------|
| 空闲（`phase === 'idle'`） | 5s |
| 运行中（其他 phase） | 1s |
| 成功弹窗中 | 暂停 |

---

## 数据流

```
用户点击"开始抢购"
  → POST /start → 返回 task_id
  → 前端 justStarted=true，按钮变"抢购中..."
  → 后端 INSERT glm_coding_rusher_tasks (result='running')
  → 后端 _execute_rush 启动线程
    → _append_log 同时写内存 + DB
  → 轮询确认 is_running=true → justStarted=false → 按钮变"停止抢购"
  → 抢购成功
    → 后端 UPDATE tasks SET result='success', payment_url=...
    → 后端 _open_payment_window 打开支付浏览器
  → 前端轮询检测到 phase='success' → 停止轮询 → 弹出成功 Modal
  → 用户点"我知道了" → 恢复轮询 → 按钮变"再次抢购"
```

---

## 涉及文件清单

### 后端
- `backend/app/routes/glm_coding_rusher.py` — 修复装饰器 + 新增 /tasks 路由
- `backend/app/models/glm_coding_rusher_models.py` — 新增 GlmCodingRusherTask 模型
- `backend/app/services/glm_coding_rusher_service.py` — 日志双写 + 任务生命周期
- `backend/app/schemas/glm_coding_rusher_schemas.py` — 新增 TaskSummary / TaskDetail

### 前端
- `frontend/src/api/glmCodingRusherApi.ts` — 新增 getTasks / getTaskLogs API
- `frontend/src/components/Tools/GlmCodingRusher/GlmCodingRusher.tsx` — 按钮状态机 + 成功弹窗 + 右侧分区 + 轮询降频

---

## 非目标（明确不做）

- ❌ WebSocket 实时推送（保留轮询，降频即可）
- ❌ 多用户隔离（当前单实例，不涉及）
- ❌ 日志导出/分页（后续按需）
