# Token Usage 统计架构优化实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 Token Usage 统计页面从"CLI 直查/DB 查询双模式"统一为"缓存优先查询"，删除割裂的双模式切换按钮

**架构:** 页面查询统一走 `/token-usage/query` 端点，Redis 缓存命中 → DB 降级 → 返回结果。后台定时任务每小时采集 CLI 数据写入 DB 并刷新 Redis。删除所有 CLI 直查端点。

**Tech Stack:** FastAPI (Python 3.12), Redis, PostgreSQL, SQLAlchemy, React + TypeScript

**前置设计文档:** `docs/plans/2026-04-29-token-usage-architecture-design.md`

---

## Phase 1: 后端统一查询端点

### Task 1: 新增 GET /token-usage/devices 端点

**Files:**
- Modify: `backend/app/routes/token_usage.py` (新增 devices 端点，~第505行后)

**Step 1: 实现 devices 端点**

在 `token_usage.py` 文件末尾（`/refresh` 路由之后）添加：

```python
@router.get("/devices")
async def get_user_devices(
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """获取当前用户的设备列表"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    db = SessionLocal()
    try:
        regs = db.query(DeviceRegistry).filter(
            DeviceRegistry.user_id == user_id
        ).all()

        if regs:
            devices = [
                {"id": reg.device_id, "name": reg.display_name or reg.default_display_name or reg.device_id}
                for reg in regs
            ]
        else:
            # 兼容：回退到 token_usage_records 表
            device_ids = db.query(TokenUsageRecord.device_id).filter(
                TokenUsageRecord.user_id == user_id
            ).distinct().all()
            devices = [{"id": row[0], "name": row[0]} for row in device_ids]

        return {"devices": devices}
    finally:
        db.close()
```

**Step 2: 添加必要的 import**

在文件顶部确保有这些 import：
```python
from app.models.token_usage_models import DeviceRegistry
from app.utils.auth import get_current_user_id
```

**Step 3: 验证**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend && source venv/bin/activate && python -c "
import ast, sys
with open('app/routes/token_usage.py') as f:
    ast.parse(f.read())
print('语法检查通过')
"
```
Expected: `语法检查通过`

**Step 4: 检查 lsp diagnostics**

检查 `backend/app/routes/token_usage.py` 无新 error/warning。

**Step 5: Commit**

```bash
git add backend/app/routes/token_usage.py
git commit -m "feat(token-usage): 新增 /devices 端点获取用户设备列表"
```

---

### Task 2: 新增 POST /token-usage/query 统一查询端点

**Files:**
- Modify: `backend/app/routes/token_usage.py` (新增 query 端点)
- Modify: `backend/app/services/token_usage_cache.py` (扩展缓存 key 构建)

**Step 1: 扩展缓存服务支持用户/设备维度**

在 `token_usage_cache.py` 末尾添加：

```python
def _build_query_cache_key(
    source: str,
    report_type: str,
    days: int,
    group_by: str,
    user_id: str,
    device_id: str = None,
) -> str:
    """构建用户维度的查询缓存 Key"""
    parts = [
        "token_usage:query",
        source,
        report_type,
        str(days),
        group_by,
        user_id,
        device_id or "",
    ]
    return ":".join(parts)


def get_query_cached_data(
    source: str,
    report_type: str,
    days: int,
    group_by: str,
    user_id: str,
    device_id: str = None,
) -> Optional[dict]:
    """从 Redis 获取用户维度的查询缓存"""
    client = get_redis_client()
    if not client:
        return None

    key = _build_query_cache_key(source, report_type, days, group_by, user_id, device_id)
    try:
        data = client.get(key)
        if data:
            logger.info(f"查询缓存命中: {key}")
            return json.loads(data)
        logger.info(f"查询缓存未命中: {key}")
        return None
    except Exception as e:
        logger.warning(f"Redis 查询缓存读取失败: {e}")
        return None


def set_query_cached_data(
    source: str,
    report_type: str,
    days: int,
    group_by: str,
    user_id: str,
    device_id: str = None,
    data: dict = None,
) -> bool:
    """将用户维度的查询数据写入 Redis 缓存"""
    client = get_redis_client()
    if not client:
        return False

    key = _build_query_cache_key(source, report_type, days, group_by, user_id, device_id)
    try:
        client.setex(
            key,
            settings.CACHE_REDIS_TOKEN_USAGE_TTL,
            json.dumps(data, ensure_ascii=False),
        )
        logger.info(f"查询缓存已写入: {key}, TTL={settings.CACHE_REDIS_TOKEN_USAGE_TTL}s")
        return True
    except Exception as e:
        logger.warning(f"Redis 查询缓存写入失败: {e}")
        return False
```

**Step 2: 实现 /query 端点**

在 `token_usage.py` 中 `/db-query` 端点之后添加：

```python
@router.post("/query", response_model=DbUsageResponse)
async def query_token_usage(
    req: DbQueryRequest,
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """统一查询端点：优先 Redis 缓存 → 降级 DB
    替代原有的 /db-query，去掉 CLI 直查链路"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    # 1. 优先查 Redis 缓存
    cached = get_query_cached_data(
        source=req.source,
        report_type=req.type,
        days=req.days,
        group_by=req.group_by,
        user_id=user_id,
        device_id=req.device_id,
    )
    if cached:
        logger.info(f"查询: Redis 缓存命中 /{req.source}/{req.type}/{req.days}天")
        return DbUsageResponse(
            items=[DbUsageItem(**item) for item in cached["items"]],
            summary=UsageSummary(**cached["summary"]),
            devices=cached.get("devices", []),
            cached=True,
        )

    # 2. Redis 未命中，查 DB
    db = SessionLocal()
    try:
        # 获取设备列表
        regs = db.query(DeviceRegistry).filter(
            DeviceRegistry.user_id == user_id
        ).all()
        if regs:
            devices = [
                {"id": reg.device_id, "name": reg.display_name or reg.default_display_name or reg.device_id}
                for reg in regs
            ]
        else:
            device_ids = db.query(TokenUsageRecord.device_id).filter(
                TokenUsageRecord.user_id == user_id
            ).distinct().all()
            devices = [{"id": row[0], "name": row[0]} for row in device_ids]

        # 如果 source 过滤，只显示该 source 下有数据的设备
        if req.source != "all":
            active_ids = set(
                row[0] for row in db.query(TokenUsageRecord.device_id).filter(
                    TokenUsageRecord.user_id == user_id,
                    TokenUsageRecord.source == req.source,
                ).distinct().all()
            )
            devices = [d for d in devices if d["id"] in active_ids]

        since_date = datetime.now() - timedelta(days=req.days)
        items = _execute_db_query(db, user_id, req, since_date)

        # 自动扩大时间范围逻辑（保持与原有 db-query 一致）
        auto_expanded = False
        actual_days = req.days
        if not items and req.days < 365:
            source_filter = [TokenUsageRecord.user_id == user_id]
            if req.source != "all":
                source_filter.append(TokenUsageRecord.source == req.source)
            if req.device_id:
                source_filter.append(TokenUsageRecord.device_id == req.device_id)
            has_any_data = db.query(TokenUsageRecord).filter(*source_filter).first() is not None
            if has_any_data:
                since_date = datetime.now() - timedelta(days=365)
                items = _execute_db_query(db, user_id, req, since_date)
                auto_expanded = True
                actual_days = 365

        summary = compute_db_summary(items)

        if not items and "claude" == req.source:
            return await _fallback_to_cli_for_query(req)

        # 3. 写入 Redis 缓存
        cache_payload = {
            "items": [item.model_dump() if hasattr(item, "model_dump") else item for item in items],
            "summary": summary.model_dump(),
            "devices": devices,
        }
        set_query_cached_data(
            source=req.source,
            report_type=req.type,
            days=req.days,
            group_by=req.group_by,
            user_id=user_id,
            device_id=req.device_id,
            data=cache_payload,
        )

        result = DbUsageResponse(
            items=items,
            summary=summary,
            devices=devices,
            cached=False,
            actual_days=actual_days if auto_expanded else None,
            auto_expanded=auto_expanded,
        )
        return result
    finally:
        db.close()
```

**Step 3: 添加 compute_db_summary 辅助函数**

在文件 `_execute_db_query` 函数之前添加：

```python
def compute_db_summary(items: list[DbUsageItem]) -> UsageSummary:
    """从 DB 查询结果计算汇总统计"""
    total_input = sum(i.input_tokens for i in items)
    total_output = sum(i.output_tokens for i in items)
    total_cache_creation = sum(i.cache_creation_tokens for i in items)
    total_cache_read = sum(i.cache_read_tokens for i in items)
    total_tokens = total_input + total_output + total_cache_creation + total_cache_read
    total_cost = sum(i.total_cost for i in items)
    days_count = len(items) if items else 1
    return UsageSummary(
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_tokens=total_tokens,
        total_cost=round(total_cost, 4),
        days_count=days_count,
        avg_daily_cost=round(total_cost / days_count, 4) if days_count else 0,
    )
```

**Step 4: 保留 _fallback_to_cli_for_query 作为最后降级**

添加降级函数（当 DB 为空且 source=claude 时）：

```python
async def _fallback_to_cli_for_query(req: DbQueryRequest) -> DbUsageResponse:
    """DB 无数据时的最后降级（仅 claude source）"""
    loop = asyncio.get_event_loop()
    since = (datetime.now() - timedelta(days=req.days)).strftime("%Y%m%d")
    
    raw = await loop.run_in_executor(None, lambda: UsageFetcher.fetch_claude(
        report_type="daily", since=since, breakdown=False
    ))
    
    if "error" in raw:
        return DbUsageResponse(items=[], summary=UsageSummary(
            total_input_tokens=0, total_output_tokens=0, total_tokens=0,
            total_cost=0, days_count=0, avg_daily_cost=0
        ), devices=[])
    
    items = normalize_entries(raw, req.type)
    items = apply_aggregation(items, req.type)
    summary = compute_summary(items)
    
    return DbUsageResponse(
        items=[DbUsageItem(**i.model_dump()) for i in items],
        summary=summary,
        devices=[],
        cached=False,
    )
```

**Step 5: 验证**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend && source venv/bin/activate && python -c "
import ast
with open('app/routes/token_usage.py') as f:
    ast.parse(f.read())
with open('app/services/token_usage_cache.py') as f:
    ast.parse(f.read())
print('语法检查通过')
"
```

**Step 6: lsp_diagnostics 检查两个修改文件**

**Step 7: Commit**

```bash
git add backend/app/routes/token_usage.py backend/app/services/token_usage_cache.py
git commit -m "feat(token-usage): 新增 /query 统一查询端点，Redis 优先 DB 降级"
```

---

### Task 3: 移除 CLI 直查端点

**Files:**
- Modify: `backend/app/routes/token_usage.py` (删除 GET /token-usage 和 POST /token-usage/aggregate)

**Step 1: 删除 GET 根端点和 POST /aggregate**

在 `token_usage.py` 中找到以下端点并删除：
- `@router.get("/")` 或 `@router.get("/token-usage")` — CLI 直查端点
- `@router.post("/aggregate")` — CLI 聚合端点

**Step 2: 保留需要的端点**

保留：
- `@router.get("/health")` — 健康检查
- `@router.post("/refresh")` — 手动刷新缓存
- `@router.post("/db-query")` — 暂时保留（后续前端迁移后删除）
- `@router.post("/query")` — 新增统一端点
- `@router.get("/devices")` — 设备列表

**Step 3: 验证**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend && source venv/bin/activate && python -c "
import ast
with open('app/routes/token_usage.py') as f:
    tree = ast.parse(f.read())
endpoints = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
print(f'端点函数: {endpoints}')
"
```

**Step 4: Commit**

```bash
git add backend/app/routes/token_usage.py
git commit -m "refactor(token-usage): 移除 CLI 直查和 CLI 聚合端点"
```

---

## Phase 2: 前端重构

### Task 4: 删除 useDbQuery 状态和模式切换 UI

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

**Step 1: 简化状态**

打开 `TokenUsage.tsx`，找到：
```typescript
const [useDbQuery, setUseDbQuery] = useState(false);
```

改为：
```typescript
// useDbQuery 已废弃，所有查询统一走 /query 端点
```

**Step 2: 删除模式切换按钮**

在 UI 中找到这部分代码并删除：
```tsx
{/* 模式切换 */}
<div className="flex items-center gap-2">
  <span className="text-xs text-slack-text-muted">模式:</span>
  <button
    className={`px-2 py-1 text-xs rounded ${!useDbQuery ? 'bg-blue-600' : 'bg-slack-card'} text-slack-text`}
    onClick={() => setUseDbQuery(false)}
  >CLI 直查</button>
  <button ...
  >数据库查询</button>
</div>
```

删除整个"模式"切换区块。

**Step 3: 修改 fetchData 逻辑**

将 `fetchData` 中的查询逻辑统一为调用 `/query` 端点：

```typescript
// 所有查询统一走 getDbTokenUsage（内部已改为调用 /query）
const result = await getDbTokenUsage({
  type: reportType,
  days,
  group_by: groupBy,
  source,
  device_id: selectedDevice || undefined,
});
```

**Step 4: 修改 buildCacheKey**

```typescript
const buildCacheKey = useCallback((params: Record<string, unknown>) => {
  const sorted = Object.entries(params).sort(([a], [b]) => a.localeCompare(b));
  return `tokenUsage:${sorted.map(([k, v]) => `${k}=${v}`).join('&')}`;
}, []);
```

去掉 `mode` 参数。

**Step 5: 提交**

```bash
cd frontend && git add src/components/Tools/TokenUsage.tsx
git commit -m "refactor(frontend): 删除 useDbQuery 状态和模式切换按钮"
```

---

### Task 5: API 层改为 /query 端点

**Files:**
- Modify: `frontend/src/api/tokenUsageApi.ts`

**Step 1: 修改 getDbTokenUsage 调用 /query**

```typescript
export async function getDbTokenUsage(params: DbQueryParams): Promise<DbUsageResponse> {
  const response = await fetch(`${BASE_URL}/query`, {  // /db-query → /query
    method: 'POST',
    headers: { ... },
    body: JSON.stringify(params),
  });
  // ...
}
```

**Step 2: 保留旧 /db-query 作为别名（过渡期）**

```typescript
// 别名，与 /query 相同
export async function getDbTokenUsageLegacy(params: DbQueryParams): Promise<DbUsageResponse> {
  return getDbTokenUsage(params);
}
```

**Step 3: 添加 getDevices API**

```typescript
export async function getUserDevices(): Promise<{ devices: DeviceInfo[] }> {
  const response = await fetch(`${BASE_URL}/devices`, {
    headers: getAuthHeaders(),
    signal: AbortSignal.timeout(REQUEST_TIMEOUT),
  });
  if (!response.ok) {
    throw new Error('获取设备列表失败');
  }
  return response.json();
}
```

**Step 4: Commit**

```bash
git add src/api/tokenUsageApi.ts
git commit -m "feat(frontend): API 层切换至 /query 端点，新增 /devices 接口"
```

---

### Task 6: 设备下拉框接入 /devices 接口

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

**Step 1: 加载设备列表**

```typescript
const [availableDevices, setAvailableDevices] = useState<DeviceInfo[]>([]);

useEffect(() => {
  getUserDevices().then(res => setAvailableDevices(res.devices)).catch(console.error);
}, []);
```

**Step 2: 设备下拉框数据源改为 availableDevices**

```tsx
<select value={selectedDevice} onChange={...}>
  <option value="">全部设备</option>
  {availableDevices.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
</select>
```

**Step 3: Commit**

```bash
git add src/components/Tools/TokenUsage.tsx
git commit -m "feat(frontend): 设备下拉框接入 /devices 接口"
```

---

### Task 7: "同步数据"按钮改为"刷新缓存"

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`
- Modify: `frontend/src/api/tokenUsageApi.ts`

**Step 1: API 层新增刷新缓存（已有 `/refresh` 端点）**

`refreshTokenUsage()` 已存在，无需修改。

**Step 2: UI 更名**

在 TokenUsage.tsx 中找到"同步数据"按钮，将文案改为"刷新缓存"。

**Step 3: Commit**

```bash
git add src/components/Tools/TokenUsage.tsx
git commit -m "ui(frontend): '同步数据'按钮更名为'刷新缓存'"
```

---

### Task 8: 浏览器验证

**验证清单：**
1. 页面不显示"CLI 直查"和"数据库查询"按钮
2. 切换"工具合计"不报错
3. 切换"按天/周/月"正常
4. 切换"按日期汇总/按设备对比/按模型分析"正常
5. 设备下拉框正确加载设备列表
6. 浏览器 Console 无 error
7. API 请求都走 `/token-usage/query`（DevTools Network 面板确认）

---

## Phase 3: 后端定时采集优化

### Task 9: 定时采集改为按用户维度

**Files:**
- Modify: `backend/app/main.py` (refresh_token_usage_cache_periodically)

**Step 1: 修改定时任务**

```python
async def refresh_token_usage_cache_periodically():
    """每小时刷新 Token Usage 缓存（按用户维度）"""
    REFRESH_INTERVAL = 3600

    while True:
        try:
            # 1. 系统级别同步（保留原有逻辑）
            sync_token_usage(user_id="system", days=90)

            # 2. 获取活跃用户列表
            active_users = await get_active_user_ids()
            for user_id in active_users:
                await refresh_user_cache(user_id)

        except Exception as e:
            logger.error(f"缓存刷新失败: {e}")

        await asyncio.sleep(REFRESH_INTERVAL)
```

**Step 2: 实现 get_active_user_ids**

```python
async def get_active_user_ids() -> list[str]:
    """获取活跃用户 ID 列表（从活跃会话或已登录用户）"""
    # 简化版：从 device_registry 获取所有有数据的用户
    db = SessionLocal()
    try:
        user_ids = db.query(TokenUsageRecord.user_id).distinct().all()
        return [row[0] for row in user_ids]
    finally:
        db.close()
```

**Step 3: 实现 refresh_user_cache**

```python
async def refresh_user_cache(user_id: str):
    """刷新指定用户的 Redis 缓存"""
    # 同步该用户的数据到 DB
    sync_token_usage(user_id=user_id, days=90)

    # 刷新常用查询的缓存
    for source in ["claude", "opencode"]:
        for days in [7, 30, 90]:
            await _refresh_single_cache(source, "daily", days, user_id)

    # 刷新聚合缓存
    for days in [7, 14, 30]:
        await _refresh_aggregate_cache("daily", days, user_id)
```

**Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(token-usage): 定时采集改为按用户维度刷新缓存"
```

---

### Task 10: 最终验证与清理

**Step 1: 完整浏览器验证**

- 打开 http://localhost:5178/tools/token-usage
- 验证所有功能正常
- Console 无 error
- Network 面板确认请求走 `/query` 端点
- Redis 缓存命中（可通过日志确认）

**Step 2: 清理旧代码**

- 删除 `/db-query` 端点（前端已全部迁移到 `/query`）
- 清理未使用的 import
- Lsp diagnostics 全项目检查

**Step 3: 提交**

```bash
git add .
git commit -m "chore(token-usage): 清理旧代码，完成架构迁移"
```

---

**Plan 完成。两个执行选项：**

1. **Subagent-Driven（当前会话）** — 我逐 task 分发子 agent 执行，中间 review，快速迭代
2. **Parallel Session（新会话）** — 新会话用 executing-plans，批量执行带检查点

选哪个？
