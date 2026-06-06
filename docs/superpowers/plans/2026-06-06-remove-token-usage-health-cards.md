# 移除 Token Usage 页面旧工具状态卡片

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移除 Token Usage 页面上展示旧 CLI 工具安装状态的 4 个卡片组件，以及相关的 health check API。

**Architecture:** 纯删除任务，涉及前端组件、前端 API 层、后端路由三层。opencode 数据同步逻辑完全保留不动。

**Tech Stack:** React 18 + TypeScript, FastAPI, Python 3.10+

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/components/Tools/TokenUsage.tsx` | 修改 | 删除状态卡片、health state、相关 import |
| `frontend/src/api/tokenUsageApi.ts` | 修改 | 删除 `UsageHealthCheck` 接口和 `checkTokenUsageHealth` 函数 |
| `backend/app/routes/token_usage.py` | 修改 | 删除 `/health` 路由 |
| `backend/app/utils/usage_fetcher.py` | 修改 | 删除 `health_check()` 方法 |

---

### Task 1: 删除前端 TokenUsage.tsx 中的状态卡片及相关代码

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: 删除 `CheckCircle2` 的 import**

  找到文件顶部的 lucide-react import 区域（约第 1-15 行），删除 `CheckCircle2`：

  ```typescript
  import {
    Activity,
    AlertTriangle,
    BarChart3,
    // CheckCircle2,  // ← 删除这一行
    Clock,
    Database,
    Download,
    Edit3,
    HardDrive,
    Loader2,
    RefreshCw,
    Trash2,
  } from 'lucide-react';
  ```

- [ ] **Step 2: 删除 `checkTokenUsageHealth` 和 `UsageHealthCheck` 的 import**

  找到 API import 区域（约第 28-44 行），从 import 列表中移除 `checkTokenUsageHealth` 和 `UsageHealthCheck`：

  ```typescript
  import {
    // checkTokenUsageHealth,  // ← 删除
    clearTokenUsageData,
    getDbTokenUsage,
    getUserDevices,
    refreshTokenUsage,
    renameDevice,
    type DbUsageItem,
    type DeviceInfo,
    type ModelSummaryItem,
    type SyncMeta,
    type TokenUsageGroupBy,
    type TokenUsageReportType,
    type TokenUsageSortBy,
    type TokenUsageSortOrder,
    type TokenUsageSource,
    // type UsageHealthCheck,  // ← 删除
  } from '../../api/tokenUsageApi';
  ```

- [ ] **Step 3: 删除 `health` 和 `healthError` state**

  找到组件内的 state 声明区域（约第 139-160 行），删除以下两行：

  ```typescript
  // 删除这两行：
  // const [health, setHealth] = useState<UsageHealthCheck | null>(null);
  // const [healthError, setHealthError] = useState<string | null>(null);
  ```

  删除后的 state 列表应包含：`devices`, `reportType`, `days`, `groupBy`, `selectedDevice`, `selectedTool`, `selectedModel`, `sortBy`, `chartType`, `currentPage`, `refreshing`, `clearing`, `syncing`, `syncError`, `error`, `deviceError`, `pollError`, `lastSyncMessage`, `backgroundRefreshing`, `refreshError`

- [ ] **Step 4: 删除 `useEffect` 中调用 `checkTokenUsageHealth` 的代码**

  找到 `useEffect`（约第 242-254 行），删除其中的 health check 调用，保留 `loadDevices()` 调用：

  ```typescript
  useEffect(() => {
    // 删除以下代码块：
    // checkTokenUsageHealth()
    //   .then(result => {
    //     setHealth(result);
    //     setHealthError(null);
    //   })
    //   .catch((err: any) => {
    //     setHealth(null);
    //     setHealthError(err.message || '健康检查失败');
    //   });
    void loadDevices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  ```

  修改后：

  ```typescript
  useEffect(() => {
    void loadDevices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  ```

- [ ] **Step 5: 删除状态卡片 JSX（第 632-649 行）**

  找到并删除以下整块代码：

  ```tsx
  {/* 删除以下整块： */}
  {health && (
    <div className="mb-4 grid gap-3 md:grid-cols-4">
      {[
        { name: 'ccusage', ok: health.ccusage_installed, detail: 'Claude Code' },
        { name: 'opencode-usage', ok: health.opencode_usage_installed, detail: 'OpenCode' },
        { name: 'ccusage-opencode', ok: health.ccusage_opencode_installed, detail: 'OpenCode 历史数据' },
        { name: 'Codex/OpenClaw', ok: null, detail: '待接入真实 usage 数据' },
      ].map(({ name, ok, detail }) => (
        <div key={name} className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-900 px-3 py-2">
          <span className="text-sm text-slate-300" title={detail}>{name}</span>
          <span className={`inline-flex items-center gap-1 text-xs ${ok === true ? 'text-emerald-300' : ok === false ? 'text-red-300' : 'text-slate-500'}`}>
            <CheckCircle2 className="h-3.5 w-3.5" />
            {ok === null ? '待接入' : healthLabel(Boolean(ok))}
          </span>
        </div>
      ))}
    </div>
  )}
  ```

- [ ] **Step 6: 检查 `healthLabel` 辅助函数是否仍被使用**

  在文件中搜索 `healthLabel(` 的使用。如果只在已删除的状态卡片中使用，则删除该函数定义（约第 66-68 行）：

  ```typescript
  // 如果不再使用，删除：
  // function healthLabel(ok: boolean): string {
  //   return ok ? '可用' : '不可用';
  // }
  ```

- [ ] **Step 7: 验证前端编译**

  Run: `cd frontend && npx tsc --noEmit`
  Expected: 无 TypeScript 错误

- [ ] **Step 8: Commit**

  ```bash
  git add frontend/src/components/Tools/TokenUsage.tsx
  git commit -m "feat: 移除 Token Usage 页面旧工具状态卡片"
  ```

---

### Task 2: 删除前端 tokenUsageApi.ts 中的 health check 代码

**Files:**
- Modify: `frontend/src/api/tokenUsageApi.ts`

- [ ] **Step 1: 删除 `UsageHealthCheck` 接口**

  找到并删除（约第 40-44 行）：

  ```typescript
  // 删除：
  // export interface UsageHealthCheck {
  //   ccusage_installed: boolean;
  //   opencode_usage_installed: boolean;
  //   ccusage_opencode_installed: boolean;
  // }
  ```

- [ ] **Step 2: 删除 `checkTokenUsageHealth` 函数**

  找到并删除（约第 236-244 行）：

  ```typescript
  // 删除：
  // export async function checkTokenUsageHealth(): Promise<UsageHealthCheck> {
  //   const response = await fetch(`${BASE_URL}/health`, {
  //     headers: getAuthHeaders(),
  //   });
  //   if (!response.ok) {
  //     throw await readError(response, '健康检查失败');
  //   }
  //   return response.json();
  // }
  ```

- [ ] **Step 3: 验证前端编译**

  Run: `cd frontend && npx tsc --noEmit`
  Expected: 无 TypeScript 错误

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/api/tokenUsageApi.ts
  git commit -m "feat: 移除 tokenUsageApi 中的 health check 接口和函数"
  ```

---

### Task 3: 删除后端 `/health` 路由

**Files:**
- Modify: `backend/app/routes/token_usage.py`

- [ ] **Step 1: 找到并删除 `/health` 路由**

  在 `token_usage.py` 中搜索 `@router.get("/health")`，找到后删除整个路由函数（约第 350-353 行附近）：

  ```python
  # 删除以下代码块：
  # @router.get("/health")
  # async def health_check():
  #     ...
  #     return UsageFetcher.health_check()
  ```

  **注意**：确认该路由只返回 health check 数据，不处理其他业务逻辑。

- [ ] **Step 2: 检查并移除未使用的 import**

  如果 `UsageFetcher` 的 import 只在 health check 中使用，检查是否需要删除。但 `UsageFetcher` 可能还被其他路由使用，不要误删。

- [ ] **Step 3: 验证后端语法**

  Run: `cd backend && python -m py_compile app/routes/token_usage.py`
  Expected: 无语法错误

- [ ] **Step 4: Commit**

  ```bash
  git add backend/app/routes/token_usage.py
  git commit -m "feat: 移除 token_usage /health 路由"
  ```

---

### Task 4: 删除 usage_fetcher.py 中的 health_check 方法

**Files:**
- Modify: `backend/app/utils/usage_fetcher.py`

- [ ] **Step 1: 找到并删除 `health_check` 方法**

  在 `usage_fetcher.py` 中搜索 `def health_check`，找到 `UsageFetcher` 类中的该方法，删除整个方法（约第 272-281 行附近）。

  该方法大致内容：
  ```python
  # 删除以下方法：
  # @staticmethod
  # def health_check() -> dict:
  #     return {
  #         "ccusage_installed": shutil.which("ccusage") is not None,
  #         "opencode_usage_installed": shutil.which("opencode-usage") is not None,
  #         "ccusage_opencode_installed": shutil.which("ccusage-opencode") is not None,
  #     }
  ```

- [ ] **Step 2: 检查 `shutil` import 是否仍被使用**

  搜索文件中其他使用 `shutil` 的地方。如果 `shutil` 只在 `health_check` 中使用，则删除顶部的 `import shutil`。

  Run: `grep -n "shutil" backend/app/utils/usage_fetcher.py`

- [ ] **Step 3: 更新模块 docstring**

  如果模块顶部的 docstring 提到了 "统一三种数据源（ccusage / opencode-usage / ccusage-opencode）"，更新为只提及 ccusage：

  ```python
  """CLI 子进程调用封装，统一使用 ccusage 获取数据源"""
  ```

- [ ] **Step 4: 验证后端语法**

  Run: `cd backend && python -m py_compile app/utils/usage_fetcher.py`
  Expected: 无语法错误

- [ ] **Step 5: Commit**

  ```bash
  git add backend/app/utils/usage_fetcher.py
  git commit -m "feat: 移除 usage_fetcher 中的 health_check 方法"
  ```

---

### Task 5: 端到端验证

**Files:**
- 无需修改文件，仅验证

- [ ] **Step 1: 启动前后端服务**

  ```bash
  python dev-services.py restart
  ```

- [ ] **Step 2: 打开 Token Usage 页面**

  浏览器访问 http://localhost:5178/tools/token-usage

  **预期结果**：
  - 页面顶部不再显示 4 个状态卡片（ccusage / opencode-usage / ccusage-opencode / Codex/OpenClaw）
  - 页面其余功能正常（统计数字、图表、明细表格）
  - 浏览器 DevTools Network 面板中不再出现 `/token-usage/health` 请求

- [ ] **Step 3: 验证数据同步不受影响**

  1. 点击页面上的"刷新"或"同步数据"按钮
  2. **预期结果**：数据同步成功，opencode 数据正常展示

- [ ] **Step 4: 验证后端 API**

  ```bash
  curl -s http://127.0.0.1:19092/token-usage/health
  ```
  **预期结果**：返回 404 Not Found（路由已删除）

- [ ] **Step 5: Commit（如无问题则无需额外提交）**

  ```bash
  git log --oneline -6
  ```

---

## Self-Review Checklist

- [ ] **Spec 覆盖**：前端卡片删除 ✅、前端 API 删除 ✅、后端路由删除 ✅、usage_fetcher health_check 删除 ✅
- [ ] **无占位符**：所有步骤包含完整代码和命令
- [ ] **保留确认**：未涉及 `sync_token_usage_v2`、`_fetch_opencode_daily`、`_parse_opencode_entries`、`SYNC_SOURCES`、`TOOL_NAME_MAP`、`MODEL_ALIASES`
- [ ] **路径正确**：所有文件路径使用项目相对路径
