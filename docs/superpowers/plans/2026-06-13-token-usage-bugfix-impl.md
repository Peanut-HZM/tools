# Token 消耗统计页面 Bug 修复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Token 消耗统计页面右上角刷新时间不准及图表横坐标日期重复问题

**Architecture:** 后端扩展 `ChartSeriesItem` 增加 input/output/cache 字段,新增全局最新记录时间字段;前端切换图表数据源从分页明细到聚合后的 chart_series,右上角时间改用全局最新记录时间

**Tech Stack:** Python FastAPI, SQLAlchemy, React TypeScript, Recharts

---

## 文件结构

| 文件 | 改动类型 | 职责 |
|------|---------|------|
| `backend/app/routes/token_usage.py` | 修改 | 扩展 schema,聚合逻辑,新增全局时间查询函数 |
| `frontend/src/api/tokenUsageApi.ts` | 修改 | 同步后端 schema 变更 |
| `frontend/src/components/Tools/TokenUsage.tsx` | 修改 | 切换数据源,修复时间显示 |

---

## Task 1: 后端扩展 ChartSeriesItem Schema

**Files:**
- Modify: `backend/app/routes/token_usage.py:647-651`

- [ ] **Step 1: 扩展 ChartSeriesItem 增加三个字段**

将 `ChartSeriesItem` schema 从:

```python
class ChartSeriesItem(BaseModel):
    date: str
    group_key: Optional[str] = None
    total_tokens: int
    total_cost: float
```

改为:

```python
class ChartSeriesItem(BaseModel):
    date: str
    group_key: Optional[str] = None
    total_tokens: int
    total_cost: float
    input_tokens: int = 0
    output_tokens: int = 0
    cache_tokens: int = 0
```

- [ ] **Step 2: 运行后端验证 schema 语法正确**

```bash
cd G:\IdeaProjects\tools\backend
python -c "from app.routes.token_usage import ChartSeriesItem; item = ChartSeriesItem(date='2026-06-13', total_tokens=100, total_cost=1.0); print('Schema OK:', item.dict())"
```

Expected: `Schema OK: {'date': '2026-06-13', 'group_key': None, 'total_tokens': 100, 'total_cost': 1.0, 'input_tokens': 0, 'output_tokens': 0, 'cache_tokens': 0}`

- [ ] **Step 3: Commit**

```bash
cd G:\IdeaProjects\tools
git add backend/app/routes/token_usage.py
git commit -m "feat(token-usage): 扩展 ChartSeriesItem 增加 input/output/cache 字段"
```

---

## Task 2: 后端改造 build_chart_series 聚合逻辑

**Files:**
- Modify: `backend/app/routes/token_usage.py:1791-1831`

- [ ] **Step 1: 修改 bucket 初始化**

将 `token_usage.py:1815-1817` 的 bucket 初始化:

```python
bucket = series_map.setdefault(
    key, {"date": date_key, "group_key": gk, "total_tokens": 0, "total_cost": 0.0}
)
```

改为:

```python
bucket = series_map.setdefault(
    key, {
        "date": date_key, "group_key": gk,
        "total_tokens": 0, "total_cost": 0.0,
        "input_tokens": 0, "output_tokens": 0, "cache_tokens": 0,
    }
)
```

- [ ] **Step 2: 在现有聚合后追加三个字段聚合**

在 `token_usage.py:1818-1819` 两行之后追加:

```python
bucket["input_tokens"] += int(getattr(row, "input_tokens", 0) or 0)
bucket["output_tokens"] += int(getattr(row, "output_tokens", 0) or 0)
bucket["cache_tokens"] += (
    int(getattr(row, "cache_creation_tokens", 0) or 0)
    + int(getattr(row, "cache_read_tokens", 0) or 0)
)
```

- [ ] **Step 3: 修改 result 输出包含新字段**

将 `token_usage.py:1821-1829` 的 result 构建:

```python
result = [
    {
        "date": v["date"],
        "group_key": v["group_key"],
        "total_tokens": v["total_tokens"],
        "total_cost": round(v["total_cost"], 4),
    }
    for v in series_map.values()
]
```

改为:

```python
result = [
    {
        "date": v["date"],
        "group_key": v["group_key"],
        "total_tokens": v["total_tokens"],
        "total_cost": round(v["total_cost"], 4),
        "input_tokens": v["input_tokens"],
        "output_tokens": v["output_tokens"],
        "cache_tokens": v["cache_tokens"],
    }
    for v in series_map.values()
]
```

- [ ] **Step 4: 运行 Python 语法检查**

```bash
cd G:\IdeaProjects\tools\backend
python -m py_compile app/routes/token_usage.py
```

Expected: 无输出(成功)

- [ ] **Step 5: Commit**

```bash
cd G:\IdeaProjects\tools
git add backend/app/routes/token_usage.py
git commit -m "feat(token-usage): build_chart_series 聚合 input/output/cache 字段"
```

---

## Task 3: 后端新增 _latest_record_at_global 函数并填充 latest_record_at

**Files:**
- Modify: `backend/app/routes/token_usage.py:621-631` (SyncMeta schema)
- Modify: `backend/app/routes/token_usage.py:1997-2010` (新增函数)
- Modify: `backend/app/routes/token_usage.py:2134-2148` (_get_sync_meta 末尾)

- [ ] **Step 1: 扩展 SyncMeta 增加 latest_record_at 字段**

将 `token_usage.py:621-628`:

```python
class SyncMeta(BaseModel):
    last_synced_at: Optional[str] = None
    last_success_at: Optional[str] = None
    cache_written_at: Optional[str] = None
    cache_ttl_seconds: int = 0
    cache_expires_at: Optional[str] = None
    data_age_seconds: Optional[int] = None
    is_stale: bool = False
    stale_reason: Optional[str] = None
    refresh_lock: RefreshLockMeta = Field(default_factory=RefreshLockMeta)
    sources_status: list[dict] = Field(default_factory=list)
```

改为:

```python
class SyncMeta(BaseModel):
    last_synced_at: Optional[str] = None
    last_success_at: Optional[str] = None
    latest_record_at: Optional[str] = None
    cache_written_at: Optional[str] = None
    cache_ttl_seconds: int = 0
    cache_expires_at: Optional[str] = None
    data_age_seconds: Optional[int] = None
    is_stale: bool = False
    stale_reason: Optional[str] = None
    refresh_lock: RefreshLockMeta = Field(default_factory=RefreshLockMeta)
    sources_status: list[dict] = Field(default_factory=list)
```

- [ ] **Step 2: 新增 _latest_record_at_global 函数**

在 `token_usage.py:1997` 的 `_latest_record_updated_at` 函数之后新增:

```python
def _latest_record_at_global(db, user_id: str) -> Optional[datetime]:
    """取该用户全局最新记录的写入时间,不受任何筛选影响。
    优先 updated_at,缺失时 fallback created_at。
    """
    row = (
        db.query(
            func.max(TokenUsageRecord.updated_at).label("updated_at"),
            func.max(TokenUsageRecord.created_at).label("created_at"),
        )
        .filter(TokenUsageRecord.user_id == user_id)
        .first()
    )
    if not row:
        return None
    return row.updated_at or row.created_at
```

- [ ] **Step 3: 在 _get_sync_meta 末尾填充 latest_record_at**

将 `token_usage.py:2138-2148`:

```python
return _build_sync_meta_from_values(
    now=datetime.now(),
    last_success_at=last_success_at,
    cache_written_at=_parse_cache_time(
        (cached_payload or {}).get("cache_written_at")
    ),
    cache_ttl_seconds=int((cached_payload or {}).get("_cache_ttl_seconds") or 0),
    configured_ttl_seconds=settings.CACHE_REDIS_TOKEN_USAGE_TTL,
    sources_status=sources_status,
    refresh_lock={"locked": False, "owner": None, "ttl_seconds": 0},
)
```

改为:

```python
result = _build_sync_meta_from_values(
    now=datetime.now(),
    last_success_at=last_success_at,
    cache_written_at=_parse_cache_time(
        (cached_payload or {}).get("cache_written_at")
    ),
    cache_ttl_seconds=int((cached_payload or {}).get("_cache_ttl_seconds") or 0),
    configured_ttl_seconds=settings.CACHE_REDIS_TOKEN_USAGE_TTL,
    sources_status=sources_status,
    refresh_lock={"locked": False, "owner": None, "ttl_seconds": 0},
)
result["latest_record_at"] = _to_iso(_latest_record_at_global(db, user_id))
return result
```

- [ ] **Step 4: 运行语法检查**

```bash
cd G:\IdeaProjects\tools\backend
python -m py_compile app/routes/token_usage.py
```

Expected: 无输出(成功)

- [ ] **Step 5: Commit**

```bash
cd G:\IdeaProjects\tools
git add backend/app/routes/token_usage.py
git commit -m "feat(token-usage): SyncMeta 新增 latest_record_at 全局最新记录时间"
```

---

## Task 4: 前端扩展 TypeScript 接口

**Files:**
- Modify: `frontend/src/api/tokenUsageApi.ts:52-73` (SyncMeta)
- Modify: `frontend/src/api/tokenUsageApi.ts:177-182` (ChartSeriesItem)

- [ ] **Step 1: 扩展 SyncMeta 接口**

将 `tokenUsageApi.ts:52-73`:

```typescript
export interface SyncMeta {
  last_synced_at?: string | null;
  last_success_at?: string | null;
  cache_written_at?: string | null;
  cache_ttl_seconds: number;
  cache_expires_at?: string | null;
  data_age_seconds?: number | null;
  is_stale: boolean;
  stale_reason?: string | null;
  refresh_lock: {
    locked: boolean;
    owner?: string | null;
    ttl_seconds: number;
  };
  sources_status: Array<{
    source: string;
    status: string;
    records_count: number;
    synced_at?: string | null;
    error_message?: string | null;
  }>;
}
```

改为:

```typescript
export interface SyncMeta {
  last_synced_at?: string | null;
  last_success_at?: string | null;
  latest_record_at?: string | null;
  cache_written_at?: string | null;
  cache_ttl_seconds: number;
  cache_expires_at?: string | null;
  data_age_seconds?: number | null;
  is_stale: boolean;
  stale_reason?: string | null;
  refresh_lock: {
    locked: boolean;
    owner?: string | null;
    ttl_seconds: number;
  };
  sources_status: Array<{
    source: string;
    status: string;
    records_count: number;
    synced_at?: string | null;
    error_message?: string | null;
  }>;
}
```

- [ ] **Step 2: 扩展 ChartSeriesItem 接口**

将 `tokenUsageApi.ts:177-182`:

```typescript
export interface ChartSeriesItem {
  date: string;
  group_key?: string | null;
  total_tokens: number;
  total_cost: number;
}
```

改为:

```typescript
export interface ChartSeriesItem {
  date: string;
  group_key?: string | null;
  total_tokens: number;
  total_cost: number;
  input_tokens?: number;
  output_tokens?: number;
  cache_tokens?: number;
}
```

- [ ] **Step 3: 运行 TypeScript 编译检查**

```bash
cd G:\IdeaProjects\tools\frontend
npm run build -- --check
```

Expected: 无 TypeScript 错误

- [ ] **Step 4: Commit**

```bash
cd G:\IdeaProjects\tools
git add frontend/src/api/tokenUsageApi.ts
git commit -m "feat(token-usage): 前端接口同步扩展 SyncMeta 和 ChartSeriesItem"
```

---

## Task 5: 前端修复右上角时间显示

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx:521`

- [ ] **Step 1: 修改右上角时间显示逻辑**

将 `TokenUsage.tsx:521`:

```tsx
<span className="text-xs text-slate-400">{formatDateTime(summary.data.sync_meta?.last_success_at)}</span>
```

改为:

```tsx
<span className="text-xs text-slate-400">
  {formatDateTime(
    summary.data.sync_meta?.latest_record_at ||
    summary.data.sync_meta?.last_success_at
  )}
</span>
```

- [ ] **Step 2: 运行 TypeScript 编译检查**

```bash
cd G:\IdeaProjects\tools\frontend
npm run build -- --check
```

Expected: 无 TypeScript 错误

- [ ] **Step 3: Commit**

```bash
cd G:\IdeaProjects\tools
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "fix(token-usage): 右上角时间改用 latest_record_at,fallback last_success_at"
```

---

## Task 6: 前端切换图表数据源

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx:351-361`

- [ ] **Step 1: 修改 chartData 数据源**

将 `TokenUsage.tsx:351-361`:

```tsx
const chartData = useMemo(
  () => [...details.data.items].sort((a, b) => a.date.localeCompare(b.date)).map(item => ({
    date: item.date,
    inputTokens: item.input_tokens,
    outputTokens: item.output_tokens,
    cacheTokens: item.cache_creation_tokens + item.cache_read_tokens,
    totalTokens: item.total_tokens,
    cost: item.total_cost,
  })),
  [details.data.items]
);
```

改为:

```tsx
const chartData = useMemo(
  () =>
    [...summary.data.chart_series]
      .filter(s => s.group_key == null)
      .sort((a, b) => a.date.localeCompare(b.date))
      .map(item => ({
        date: item.date,
        inputTokens: item.input_tokens ?? 0,
        outputTokens: item.output_tokens ?? 0,
        cacheTokens: item.cache_tokens ?? 0,
        totalTokens: item.total_tokens,
        cost: item.total_cost,
      })),
  [summary.data.chart_series]
);
```

- [ ] **Step 2: 运行 TypeScript 编译检查**

```bash
cd G:\IdeaProjects\tools\frontend
npm run build -- --check
```

Expected: 无 TypeScript 错误

- [ ] **Step 3: Commit**

```bash
cd G:\IdeaProjects\tools
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "fix(token-usage): 图表数据源从 details 切换到 chart_series 解决日期重复"
```

---

## Task 7: 后端重启与验证

- [ ] **Step 1: 重启后端服务**

```bash
cd G:\IdeaProjects\tools
python dev_services.py restart backend
```

- [ ] **Step 2: 检查后端日志无报错**

```bash
cd G:\IdeaProjects\tools
python dev_services.py logs backend
```

Expected: 服务正常启动,无异常堆栈

- [ ] **Step 3: 调用 summary API 验证新字段**

```bash
curl -s -X POST http://localhost:19092/token-usage/summary \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(cat ~/.token_usage_token 2>/dev/null || echo '')" \
  -d '{"type":"daily","days":30,"group_by":"none","source":"all"}' \
  | python -c "import sys,json; d=json.load(sys.stdin); print('latest_record_at:', d.get('sync_meta',{}).get('latest_record_at')); print('chart_series sample:', d.get('chart_series',[])[:1])"
```

Expected:
- `latest_record_at` 显示下午时间(如 `2026-06-13T13:xx:xx`)
- `chart_series` 样本包含 `input_tokens`, `output_tokens`, `cache_tokens` 字段

- [ ] **Step 4: Commit (如果有调整)**

```bash
cd G:\IdeaProjects\tools
git status
# 如果有未提交的修改
git add -A
git commit -m "fix: 调整验证过程中发现的问题"
```

---

## Task 8: 前端验证

- [ ] **Step 1: 重启前端服务**

```bash
cd G:\IdeaProjects\tools
python dev_services.py restart frontend
```

- [ ] **Step 2: 浏览器验证右上角时间**

1. 打开 `http://localhost:5178`
2. 登录(用户名 `peanut`,密码 `Peanut2817*#`)
3. 进入 Token 消耗统计页面
4. 验证右上角时间显示下午时间(不是凌晨 04:50)
5. 切换筛选(工具/模型/设备),确认右上角时间不变

- [ ] **Step 3: 浏览器验证图表日期不重复**

1. 查看 Token 消耗趋势图
2. 确认 X 轴每个日期只出现一次
3. 确认柱形是 input(蓝)+cache(黄)+output(绿) 堆叠
4. 切换 groupBy 为 device/tool/model,确认分组图表正常

- [ ] **Step 4: 回归检查**

- 明细表分页翻页正常
- 导出 CSV 功能正常
- 同步数据按钮正常
- 手动刷新按钮正常
- 时间筛选范围变更时图表正常刷新

---

## 自审清单

### Spec 覆盖检查

- [x] Bug 1(右上角时间): Task 3 新增 `_latest_record_at_global`, Task 5 前端使用 `latest_record_at`
- [x] Bug 2(日期重复): Task 2 扩展 `build_chart_series`, Task 6 前端切换数据源
- [x] Schema 扩展: Task 1, Task 4
- [x] 测试验证: Task 7, Task 8

### Placeholder 扫描

无 TBD/TODO/待填充内容

### 类型一致性检查

- 后端 `ChartSeriesItem.input_tokens` → 前端 `ChartSeriesItem.input_tokens` ✓
- 后端 `SyncMeta.latest_record_at` → 前端 `SyncMeta.latest_record_at` ✓
- 前端 `item.input_tokens ?? 0` fallback 与后端默认值 0 一致 ✓
