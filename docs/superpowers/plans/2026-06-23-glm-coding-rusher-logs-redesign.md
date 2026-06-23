# GLM Coding Rusher 日志与交互重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复日志 404、持久化抢购记录与日志到 DB、前端增加成功弹窗与右侧分区布局。

**Architecture:** 后端新增 `GlmCodingRusherTask` DB 模型 + 任务生命周期钩子，`_append_log` 双写内存与 DB；前端按钮状态机 + 成功 Modal + 右侧上下分区（记录列表 + 实时日志） + 自适应轮询。

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic（后端）；React + TypeScript + Tailwind CSS（前端）；PostgreSQL（数据库）

---

## File Structure

```
backend/
├── app/
│   ├── models/glm_coding_rusher_models.py     # 新增 GlmCodingRusherTask
│   ├── schemas/glm_coding_rusher_schemas.py   # 新增 TaskSummary / TaskDetail / TaskListResponse
│   ├── services/glm_coding_rusher_service.py  # 日志双写 + 任务生命周期 + DB 查询方法
│   └── routes/glm_coding_rusher.py            # 修复 /logs 装饰器 + 新增 /tasks 路由

frontend/
└── src/
    ├── api/glmCodingRusherApi.ts              # 新增 getTasks / getTaskLogs API
    └── components/Tools/GlmCodingRusher/
        └── GlmCodingRusher.tsx                # 按钮状态机 + 成功弹窗 + 右侧分区 + 轮询降频
```

---

## Task 1: 修复 `/logs` 404 + 补 `task_id` 参数

**Files:**
- Modify: `backend/app/routes/glm_coding_rusher.py:173-179`

- [ ] **Step 1: 给 `logs` 函数添加路由装饰器和 `task_id` 参数**

打开 `backend/app/routes/glm_coding_rusher.py`，找到第 173 行的 `def logs(limit: int = 100):`，改为：

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

- [ ] **Step 2: 重启后端验证 404 已修复**

Run: `python dev_services.py restart backend`

然后在浏览器打开 http://localhost:5178/tools/glm-coding-rusher ，打开 DevTools Network 面板，确认 `/api/glm-coding-rusher/logs` 请求返回 200（不再是 404）。

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/glm_coding_rusher.py
git commit -m "fix: 修复 GLM Coding Rusher /logs 404（补 @router.get 装饰器 + task_id 参数）"
```

---

## Task 2: 新增 `GlmCodingRusherTask` 数据库模型

**Files:**
- Modify: `backend/app/models/glm_coding_rusher_models.py`

- [ ] **Step 1: 在模型文件末尾添加 Task 模型**

打开 `backend/app/models/glm_coding_rusher_models.py`，在文件末尾追加：

```python
class GlmCodingRusherTask(Base):
    """抢购任务记录表"""
    __tablename__ = "glm_coding_rusher_tasks"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    config_snapshot = Column(Text, nullable=False, default="{}")
    result = Column(String(32), nullable=False, default="running")
    refresh_count = Column(Integer, nullable=False, default=0)
    payment_url = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: 重启后端，确认表自动创建**

Run: `python dev_services.py restart backend`

检查后端启动日志，应看到 SQLAlchemy 创建 `glm_coding_rusher_tasks` 表。如果项目启动时调用 `Base.metadata.create_all()`，表会自动创建；否则需手动执行建表（下一步验证）。

- [ ] **Step 3: 验证表存在**

用数据库客户端或后端日志确认 `glm_coding_rusher_tasks` 表已创建。

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/glm_coding_rusher_models.py
git commit -m "feat: 新增 GlmCodingRusherTask 抢购任务记录表"
```

---

## Task 3: 新增 Pydantic Schema

**Files:**
- Modify: `backend/app/schemas/glm_coding_rusher_schemas.py`

- [ ] **Step 1: 在 schema 文件末尾添加 Task 相关 schema**

打开 `backend/app/schemas/glm_coding_rusher_schemas.py`，在末尾追加：

```python
import json


class TaskSummary(BaseModel):
    """抢购任务摘要"""
    id: str
    result: str
    target_package: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    refresh_count: int
    payment_url: Optional[str] = None


class TaskDetail(TaskSummary):
    """抢购任务详情（含完整配置快照）"""
    config_snapshot: dict


class TaskListResponse(BaseModel):
    """抢购任务列表响应"""
    items: List[TaskSummary]
    total: int
```

注意：`TaskDetail.config_snapshot` 在 route 层通过 `json.loads(task.config_snapshot)` 从 DB 的 Text 字段解析而来。`TaskSummary.target_package` 也在 route 层从 `config_snapshot` JSON 中提取。

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/glm_coding_rusher_schemas.py
git commit -m "feat: 新增 TaskSummary/TaskDetail/TaskListResponse schema"
```

---

## Task 4: Service 层 — 日志双写 + 任务生命周期

**Files:**
- Modify: `backend/app/services/glm_coding_rusher_service.py`

本任务改动最大，分 4 个子步骤。

- [ ] **Step 1: 添加 DB 导入和辅助函数**

在 `backend/app/services/glm_coding_rusher_service.py` 顶部 import 区域添加：

```python
import json
from app.models.base import SessionLocal
from app.models.glm_coding_rusher_models import GlmCodingRusherLog, GlmCodingRusherTask
```

在 `_append_log` 函数上方添加辅助函数：

```python
def _get_db():
    """获取 DB session（非请求上下文，直接创建）"""
    return SessionLocal()


def _save_log_to_db(log_entry: dict):
    """将日志条目写入 DB"""
    db = _get_db()
    try:
        db_log = GlmCodingRusherLog(
            id=log_entry["id"],
            task_id=log_entry["task_id"],
            user_id="system",  # 当前单用户
            phase=log_entry["phase"],
            message=log_entry["message"],
        )
        db.add(db_log)
        db.commit()
    except Exception as e:
        logger.warning(f"日志写 DB 失败: {e}")
        db.rollback()
    finally:
        db.close()


def _create_task_record(task_id: str, config: dict):
    """创建抢购任务记录"""
    db = _get_db()
    try:
        db_task = GlmCodingRusherTask(
            id=task_id,
            user_id="system",
            config_snapshot=json.dumps(config, ensure_ascii=False),
            result="running",
            refresh_count=0,
            started_at=datetime.now(),
        )
        db.add(db_task)
        db.commit()
    except Exception as e:
        logger.warning(f"创建任务记录失败: {e}")
        db.rollback()
    finally:
        db.close()


def _update_task_record(task_id: str, **kwargs):
    """更新抢购任务记录"""
    db = _get_db()
    try:
        db.query(GlmCodingRusherTask).filter(
            GlmCodingRusherTask.id == task_id
        ).update(kwargs)
        db.commit()
    except Exception as e:
        logger.warning(f"更新任务记录失败: {e}")
        db.rollback()
    finally:
        db.close()
```

- [ ] **Step 2: 修改 `_append_log` 为双写**

找到 `_append_log` 函数（约第 377 行），改为：

```python
def _append_log(phase: str, message: str, task_id: str):
    """追加日志到缓冲区（内存 + DB 双写）"""
    entry = {
        "id": str(uuid.uuid4()),
        "task_id": task_id,
        "phase": phase,
        "message": message,
        "created_at": datetime.now(),
    }
    _logs_buffer.append(entry)
    # 内存只保留最近 500 条
    if len(_logs_buffer) > 500:
        _logs_buffer[:] = _logs_buffer[-500:]
    # 异步写 DB（不阻塞主线程）
    try:
        _save_log_to_db(entry)
    except Exception as e:
        logger.debug(f"日志写 DB 异常（已忽略）: {e}")
    logger.info(f"[{phase}] {message}")
```

- [ ] **Step 3: 在任务生命周期中调用 `_create_task_record` / `_update_task_record`**

**3a. `start_rush` 函数**（约第 680 行），在 `_update_task(is_running=True, ...)` 之后、线程启动之前添加：

```python
    _create_task_record(task_id, config)
```

**3b. `_execute_rush` 函数 — 成功分支**（约第 641 行 `_append_log("success", ...)` 之后）添加：

```python
    _update_task_record(
        task_id,
        result="success",
        refresh_count=retry_count,
        payment_url=payment_url,
        ended_at=datetime.now(),
    )
```

**3c. `_execute_rush` 函数 — 超时分支**（约第 664 行 `_append_log("failed", ...)` 之后）添加：

```python
    _update_task_record(
        task_id,
        result="timeout",
        refresh_count=retry_count,
        ended_at=datetime.now(),
    )
```

**3d. `_execute_rush` 函数 — 异常分支**（约第 672 行 `_append_log("failed", ...)` 之后）添加：

```python
    _update_task_record(
        task_id,
        result="error",
        ended_at=datetime.now(),
    )
```

**3e. `stop_rush` 函数**（约第 708 行），在 `_update_task(...)` 之后添加：

```python
    task_id = _current_task.get("task_id")
    if task_id:
        _update_task_record(task_id, result="stopped", ended_at=datetime.now())
```

- [ ] **Step 4: 添加 DB 查询方法（供 route 层调用）**

在 `get_task_logs` 函数之后添加：

```python
def list_task_records(limit: int = 50) -> list:
    """从 DB 查询抢购任务记录列表（按 started_at 倒序）"""
    db = _get_db()
    try:
        tasks = (
            db.query(GlmCodingRusherTask)
            .order_by(GlmCodingRusherTask.started_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": t.id,
                "result": t.result,
                "target_package": json.loads(t.config_snapshot).get("target_package", "pro"),
                "started_at": t.started_at,
                "ended_at": t.ended_at,
                "refresh_count": t.refresh_count,
                "payment_url": t.payment_url,
                "config_snapshot": json.loads(t.config_snapshot),
            }
            for t in tasks
        ]
    finally:
        db.close()


def get_task_logs_from_db(task_id: str, limit: int = 500) -> list:
    """从 DB 查询指定任务的日志"""
    db = _get_db()
    try:
        logs = (
            db.query(GlmCodingRusherLog)
            .filter(GlmCodingRusherLog.task_id == task_id)
            .order_by(GlmCodingRusherLog.created_at.asc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": l.id,
                "task_id": l.task_id,
                "phase": l.phase,
                "message": l.message,
                "created_at": l.created_at,
            }
            for l in logs
        ]
    finally:
        db.close()
```

- [ ] **Step 5: 重启后端验证无语法错误**

Run: `python dev_services.py restart backend`

确认启动无报错。

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/glm_coding_rusher_service.py
git commit -m "feat: GLM Rusher 日志双写 DB + 任务生命周期钩子 + DB 查询方法"
```

---

## Task 5: 新增 `/tasks` API 路由

**Files:**
- Modify: `backend/app/routes/glm_coding_rusher.py`

- [ ] **Step 1: 更新 import 并添加路由**

在 `backend/app/routes/glm_coding_rusher.py` 顶部 import 中补充：

```python
from app.schemas.glm_coding_rusher_schemas import (
    RusherConfigRequest, RusherConfigResponse,
    LoginStatusResponse, RusherStatusResponse, PaymentInfoResponse,
    RusherLogItem, RusherLogListResponse,
    LoginRequest, StartRequest,
    TaskSummary, TaskDetail, TaskListResponse,
)
from app.services.glm_coding_rusher_service import (
    open_login_window, check_login_valid, state_file_exists, get_state_path,
    validate_config, ConfigError,
    get_task_status, get_task_logs, start_rush, stop_rush,
    close_payment_window,
    next_sale_time, format_countdown,
    list_task_records, get_task_logs_from_db,
)
```

在 `logs` 函数之后添加三个路由：

```python
@router.get("/tasks", response_model=TaskListResponse)
def tasks(limit: int = 50):
    """获取抢购任务记录列表"""
    records = list_task_records(limit=limit)
    summaries = [
        TaskSummary(
            id=r["id"],
            result=r["result"],
            target_package=r["target_package"],
            started_at=r["started_at"],
            ended_at=r["ended_at"],
            refresh_count=r["refresh_count"],
            payment_url=r["payment_url"],
        )
        for r in records
    ]
    return TaskListResponse(items=summaries, total=len(summaries))


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def task_detail(task_id: str):
    """获取单个任务详情"""
    records = list_task_records(limit=1000)
    matched = next((r for r in records if r["id"] == task_id), None)
    if not matched:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskDetail(**matched)


@router.get("/tasks/{task_id}/logs", response_model=RusherLogListResponse)
def task_logs(task_id: str, limit: int = 500):
    """获取指定任务的日志（从 DB 查询）"""
    items = get_task_logs_from_db(task_id=task_id, limit=limit)
    return RusherLogListResponse(
        items=[RusherLogItem(**item) for item in items],
        total=len(items),
    )
```

- [ ] **Step 2: 重启后端并验证 API**

Run: `python dev_services.py restart backend`

验证：
- `GET /api/glm-coding-rusher/tasks` 返回 200（空列表 `{"items":[],"total":0}`）
- `GET /api/glm-coding-rusher/logs` 返回 200
- `GET /api/glm-coding-rusher/logs?task_id=xxx` 返回 200

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/glm_coding_rusher.py
git commit -m "feat: 新增 /tasks /tasks/{id} /tasks/{id}/logs API"
```

---

## Task 6: 前端 API 客户端扩展

**Files:**
- Modify: `frontend/src/api/glmCodingRusherApi.ts`

- [ ] **Step 1: 添加 Task 相关类型和 API 函数**

在 `frontend/src/api/glmCodingRusherApi.ts` 末尾追加：

```typescript
export interface TaskSummary {
  id: string;
  result: string;
  target_package: string;
  started_at: string;
  ended_at: string | null;
  refresh_count: number;
  payment_url: string | null;
}

export interface TaskDetail extends TaskSummary {
  config_snapshot: Record<string, unknown>;
}

export interface TaskListResponse {
  items: TaskSummary[];
  total: number;
}

/** 获取抢购任务记录列表 */
export async function getTasks(limit = 50): Promise<TaskListResponse> {
  return request(`/tasks?limit=${limit}`);
}

/** 获取指定任务的日志（从 DB） */
export async function getTaskLogs(taskId: string, limit = 500): Promise<LogListResponse> {
  return request(`/tasks/${taskId}/logs?limit=${limit}`);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/glmCodingRusherApi.ts
git commit -m "feat: 前端新增 getTasks / getTaskLogs API"
```

---

## Task 7: 前端 — 按钮状态机 + 成功弹窗

**Files:**
- Modify: `frontend/src/components/Tools/GlmCodingRusher/GlmCodingRusher.tsx`

- [ ] **Step 1: 添加 `justStarted` state 和导入**

在组件顶部 import 中确认已导入 `startRush`, `stopRush`, `getPaymentInfo`。

在组件内（`useState` 区域）添加：

```typescript
  const [justStarted, setJustStarted] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successPaymentUrl, setSuccessPaymentUrl] = useState<string | null>(null);
```

- [ ] **Step 2: 修改 `handleStart`，点击后立即设置 `justStarted`**

找到 `handleStart` 函数，修改为：

```typescript
  const handleStart = async () => {
    setLoading(true);
    setError(null);
    setJustStarted(true);
    try {
      const res = await startRush();
      if (!res.success) {
        throw new Error(res.message);
      }
      // 保持 justStarted=true，等轮询确认 is_running 后再清除
    } catch (e: any) {
      setError(e.message);
      setJustStarted(false);
    } finally {
      setLoading(false);
    }
  };
```

- [ ] **Step 3: 修改轮询回调，检测 `is_running` 和 `success`**

找到 `poll` 函数中的 `setStatus(s)` 之后，添加状态同步逻辑：

```typescript
  const poll = useCallback(async () => {
    try {
      const [s, l, ls, p] = await Promise.all([
        getStatus(), getLogs(), getLoginStatus(), getPaymentInfo(),
      ]);
      setStatus(s);
      setLogs(l.items);
      setLoginStatus(ls);
      setPaymentInfo(p);

      // 轮询确认任务已启动 → 清除 justStarted
      if (justStarted && s.is_running) {
        setJustStarted(false);
      }

      // 检测抢购成功 → 弹窗 + 记录支付 URL
      if (s.current_phase === 'success' && !showSuccessModal) {
        setSuccessPaymentUrl(s.payment_url || null);
        setShowSuccessModal(true);
      }
    } catch {
      // 忽略轮询错误
    }
  }, [justStarted, showSuccessModal]);
```

- [ ] **Step 4: 修改轮询间隔逻辑（降频优化）**

找到 `useEffect` 中的 `setInterval(poll, 1000)`，改为根据状态自适应：

```typescript
  useEffect(() => {
    poll();
    // 成功弹窗中 → 暂停轮询；运行中 → 1s；空闲 → 5s
    const interval = showSuccessModal
      ? null
      : status.is_running || status.current_phase !== 'idle'
        ? 1000
        : 5000;
    if (interval === null) return;
    const timer = setInterval(poll, interval);
    return () => clearInterval(timer);
  }, [poll, showSuccessModal, status.is_running, status.current_phase]);
```

- [ ] **Step 5: 修改按钮区域，加入状态机**

找到现有的 `{!status.is_running ? (...) : (...)}` 按钮区域（约第 308-326 行），替换为：

```tsx
              <div className="flex justify-center gap-3">
                {justStarted ? (
                  <button
                    disabled
                    className="px-6 py-2 bg-amber-600/50 rounded-lg text-sm font-bold cursor-not-allowed"
                  >
                    <i className="fas fa-spinner fa-spin mr-2" />
                    抢购中...
                  </button>
                ) : status.is_running ? (
                  <button
                    onClick={handleStop}
                    disabled={loading}
                    className="px-6 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-bold disabled:opacity-50"
                  >
                    停止抢购
                  </button>
                ) : (
                  <button
                    onClick={handleStart}
                    disabled={!loginStatus?.logged_in || loading}
                    className="px-6 py-2 bg-amber-600 hover:bg-amber-700 rounded-lg text-sm font-bold disabled:opacity-50"
                  >
                    {status.current_phase === 'success' ? '再次抢购' : '开始抢购'}
                  </button>
                )}
              </div>
```

- [ ] **Step 6: 在组件 return 的最外层 `</div>` 之前添加成功弹窗**

```tsx
        {/* 抢购成功弹窗 */}
        {showSuccessModal && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div className="bg-slate-800 rounded-2xl p-8 max-w-md w-full mx-4 border border-green-500/30 shadow-2xl">
              <div className="text-center mb-6">
                <div className="text-5xl mb-4">✅</div>
                <h2 className="text-2xl font-bold text-green-400">抢购成功！</h2>
                <p className="text-slate-400 mt-2">
                  支付页面已打开，请在浏览器窗口中完成支付
                </p>
              </div>

              {successPaymentUrl && (
                <div className="bg-slate-900 rounded-lg p-3 mb-6">
                  <div className="text-xs text-slate-500 mb-1">支付链接</div>
                  <div className="text-sm text-slate-300 break-all font-mono">
                    {successPaymentUrl}
                  </div>
                </div>
              )}

              <div className="flex gap-3">
                {successPaymentUrl && (
                  <button
                    onClick={() => window.open(successPaymentUrl, '_blank')}
                    className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium"
                  >
                    在浏览器中打开
                  </button>
                )}
                <button
                  onClick={() => {
                    setShowSuccessModal(false);
                    setSuccessPaymentUrl(null);
                  }}
                  className="flex-1 px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg text-sm font-medium"
                >
                  我知道了
                </button>
              </div>
            </div>
          </div>
        )}
```

- [ ] **Step 7: 浏览器验证**

前端热加载后（无需重启），在页面上：
1. 点击"开始抢购" → 按钮应立即变为"抢购中..."且不可点击
2. 等后端确认 `is_running=true` 后 → 按钮变为"停止抢购"
3. 如果抢购成功 → 应弹出绿色成功 Modal

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/Tools/GlmCodingRusher/GlmCodingRusher.tsx
git commit -m "feat: GLM Rusher 按钮状态机 + 成功弹窗 + 轮询降频"
```

---

## Task 8: 前端 — 右侧面板分区（抢购记录 + 实时日志）

**Files:**
- Modify: `frontend/src/components/Tools/GlmCodingRusher/GlmCodingRusher.tsx`

- [ ] **Step 1: 导入新 API 并添加 state**

在顶部 import 中追加 `getTasks`, `getTaskLogs`, `TaskSummary`：

```typescript
import {
  getLoginStatus, getConfig, saveConfig,
  startLogin, startRush, stopRush,
  getStatus, getLogs, getPaymentInfo, closePaymentBrowser,
  getTasks, getTaskLogs,
  RusherConfig, LoginStatus, RusherStatus, RusherLog, PaymentInfo, TaskSummary,
} from '../../../api/glmCodingRusherApi';
```

在组件 state 区域添加：

```typescript
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
```

- [ ] **Step 2: 在 poll 中加载任务列表**

在 `poll` 函数中，在 `Promise.all` 之后添加：

```typescript
      // 加载抢购记录
      const t = await getTasks();
      setTasks(t.items);
```

- [ ] **Step 3: 添加任务日志加载逻辑**

添加一个 useEffect，当 `selectedTaskId` 变化时从 DB 加载该任务的完整日志：

```typescript
  useEffect(() => {
    if (!selectedTaskId) {
      // 未选中任务 → 使用 poll 中的实时日志
      return;
    }
    getTaskLogs(selectedTaskId).then((res) => setLogs(res.items)).catch(() => {});
  }, [selectedTaskId]);
```

- [ ] **Step 4: 替换右侧面板为分区布局**

找到右侧面板区域（以 `{/* 右侧：实时日志区 */}` 开头的 `<div>`），整个替换为：

```tsx
          {/* 右侧：抢购记录 + 实时日志 */}
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 lg:sticky lg:top-6 lg:self-start lg:h-[calc(100vh-3rem)] lg:flex lg:flex-col">
            {/* 上半区：抢购记录 */}
            <div className="mb-4 shrink-0" style={{ maxHeight: '40%' }}>
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-lg font-semibold">
                  <i className="fas fa-clipboard-list text-amber-400 mr-2" />
                  抢购记录
                </h2>
                {selectedTaskId && (
                  <button
                    onClick={() => { setSelectedTaskId(null); }}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    显示全部日志
                  </button>
                )}
              </div>
              <div className="overflow-y-auto space-y-1" style={{ maxHeight: 'calc(40vh - 80px)' }}>
                {tasks.length === 0 ? (
                  <div className="text-slate-500 text-center py-4 text-sm">暂无记录</div>
                ) : (
                  tasks.map((task) => {
                    const RESULT_ICON: Record<string, string> = {
                      success: '✅',
                      timeout: '❌',
                      stopped: '⏹',
                      error: '💥',
                      running: '🔄',
                    };
                    const isSelected = task.id === selectedTaskId;
                    return (
                      <div
                        key={task.id}
                        onClick={() => setSelectedTaskId(isSelected ? null : task.id)}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-blue-600/20 border border-blue-500/40'
                            : 'bg-slate-900/50 hover:bg-slate-700/50 border border-transparent'
                        }`}
                      >
                        <span>{RESULT_ICON[task.result] || '❓'}</span>
                        <span className="text-slate-400 shrink-0">
                          {new Date(task.started_at).toLocaleString('zh-CN', {
                            month: '2-digit', day: '2-digit',
                            hour: '2-digit', minute: '2-digit',
                          })}
                        </span>
                        <span className="text-slate-300 truncate">
                          {task.target_package}
                        </span>
                        <span className="ml-auto text-slate-500 shrink-0">
                          {task.refresh_count}次刷新
                        </span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* 分割线 */}
            <div className="border-t border-slate-700 my-2 shrink-0" />

            {/* 下半区：实时日志 */}
            <div className="flex-1 flex flex-col min-h-0">
              <h2 className="text-lg font-semibold mb-2 shrink-0">
                <i className="fas fa-terminal text-green-400 mr-2" />
                实时日志
                {selectedTaskId && (
                  <span className="text-xs text-blue-400 font-normal ml-2">
                    (筛选中)
                  </span>
                )}
              </h2>
              <div className="bg-slate-900 rounded-lg p-4 overflow-y-auto font-mono text-xs space-y-1 flex-1 min-h-0">
                {logs.length === 0 ? (
                  <div className="text-slate-500 text-center py-8">暂无日志</div>
                ) : (
                  logs.map((log) => (
                    <div key={log.id} className="flex gap-2">
                      <span className="text-slate-500 shrink-0">
                        {new Date(log.created_at).toLocaleTimeString()}
                      </span>
                      <span className={`shrink-0 px-1.5 rounded ${PHASE_COLORS[log.phase] || 'bg-slate-600'} text-white text-[10px]`}>
                        {log.phase}
                      </span>
                      <span className="text-slate-300 break-all">{log.message}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
```

- [ ] **Step 5: 浏览器验证**

热加载后检查：
1. 右侧面板分为上下两区：上部"抢购记录"，下部"实时日志"
2. 每次抢购后，记录列表出现新条目
3. 点击某条记录 → 下方日志切换为该任务的 DB 日志
4. 点击"显示全部日志" → 恢复实时日志

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Tools/GlmCodingRusher/GlmCodingRusher.tsx
git commit -m "feat: GLM Rusher 右侧分区布局（抢购记录 + 实时日志）"
```

---

## Task 9: 端到端验证

- [ ] **Step 1: 完整流程测试**

1. 打开 http://localhost:5178/tools/glm-coding-rusher
2. 确认登录状态正常显示
3. 确认"开始抢购"按钮可用
4. 点击"开始抢购" → 按钮变"抢购中..."
5. 等状态变为运行中 → 按钮变"停止抢购"
6. 查看右侧"抢购记录"出现一条新记录
7. 实时日志区正常输出日志
8. 点击"停止抢购"
9. 抢购记录结果变为 ⏹（stopped）
10. 再次点击该记录 → 下方日志显示该任务的 DB 日志
11. 点"显示全部日志" → 恢复全部日志

- [ ] **Step 2: Commit all remaining changes (if any)**

```bash
git status  # 确认无遗漏
git add -A
git commit -m "chore: GLM Rusher 重构完成"
```

---

## Self-Review Checklist

- ✅ Spec coverage: 404 修复（Task 1）、DB 持久化（Task 2/3/4）、任务记录 API（Task 5）、前端按钮状态机（Task 7）、成功弹窗（Task 7）、右侧分区（Task 8）、轮询降频（Task 7）
- ✅ No placeholders: 所有步骤含完整代码
- ✅ Type consistency: `TaskSummary`/`TaskDetail`/`TaskListResponse` 在 schema、API、前端类型中保持一致
