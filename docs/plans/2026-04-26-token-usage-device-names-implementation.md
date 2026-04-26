# Token Usage 设备名称优化实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Token 消耗统计页面的设备下拉框显示可读的设备名称（如 `huazhongmin@MacBook-Pro`）而非 UUID，并支持用户手动重命名。

**Architecture:** 新增 `device_registry` 表管理设备 ID 与显示名称的映射。同步时自动注册设备，查询时返回设备对象 `{id, name}` 替代纯字符串。前端下拉框显示名称，并提供 ✏️ 按钮重命名。

**Tech Stack:** Python/FastAPI + SQLAlchemy + PostgreSQL, React/TypeScript + Tailwind

---

## 前置准备：启动服务

确保前后端服务已启动。如果服务在运行中，可以跳过。

---

### Task 1: 数据库 — 创建 device_registry 表并迁移旧数据

**Files:** 无需创建新文件，直接在数据库中执行 SQL

**Step 1: 执行建表 SQL**

```sql
CREATE TABLE IF NOT EXISTS device_registry (
    id            BIGSERIAL PRIMARY KEY,
    user_id       VARCHAR(64) NOT NULL,
    device_id     VARCHAR(128) NOT NULL,
    display_name  VARCHAR(128),
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, device_id)
);
```

```bash
# 通过 psql 执行
cd backend
psql $DATABASE_URL -c "CREATE TABLE IF NOT EXISTS device_registry (
    id            BIGSERIAL PRIMARY KEY,
    user_id       VARCHAR(64) NOT NULL,
    device_id     VARCHAR(128) NOT NULL,
    display_name  VARCHAR(128),
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, device_id)
);"
```

**Step 2: 从现有 token_usage_records 补录设备数据**

```sql
INSERT INTO device_registry (user_id, device_id, display_name)
SELECT DISTINCT user_id, device_id, NULL
FROM token_usage_records
ON CONFLICT (user_id, device_id) DO NOTHING;
```

```bash
psql $DATABASE_URL -c "INSERT INTO device_registry (user_id, device_id, display_name)
SELECT DISTINCT user_id, device_id, NULL
FROM token_usage_records
ON CONFLICT (user_id, device_id) DO NOTHING;"
```

**Step 3: 验证**

```bash
psql $DATABASE_URL -c "SELECT device_id, user_id, display_name FROM device_registry ORDER BY user_id;"
```

应该看到两条记录，`display_name` 都为 NULL。

**Step 4: 提交**

```bash
# 此 Task 不涉及代码文件变更，仅数据库操作
```

---

### Task 2: 后端 — 新增 DeviceRegistry 模型

**Files:**
- Modify: `backend/app/models/token_usage_models.py`

**Step 1: 新增 DeviceRegistry 模型**

在 `backend/app/models/token_usage_models.py` 末尾追加：

```python
class DeviceRegistry(Base):
    """设备注册表 — 管理设备 ID 与显示名称的映射"""
    __tablename__ = "device_registry"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    device_id = Column(String(128), nullable=False)
    display_name = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "device_id"),)
```

**Step 2: 验证模型加载**

```bash
cd backend
python -c "from app.models.token_usage_models import DeviceRegistry; print('Model OK:', DeviceRegistry.__tablename__)"
```

**Step 3: 提交**

```bash
git add backend/app/models/token_usage_models.py
git commit -m "feat: 新增 DeviceRegistry 设备注册模型"
```

---

### Task 3: 后端 — 同步时自动注册设备

**Files:**
- Modify: `backend/app/services/token_usage_sync_service.py`

**Step 1: 修改 import**

第 8 行，导入 `DeviceRegistry`：

```python
from app.models.token_usage_models import TokenUsageRecord, TokenUsageSyncLog, DeviceRegistry
```

**Step 2: 在 sync_token_usage() 中注册设备**

第 173 行 `device_id = get_device_id()` 之后，插入设备注册逻辑：

```python
    device_id = get_device_id()
    db = SessionLocal()
    result = {"sources_synced": [], "total_records": 0, "errors": []}

    # 确保设备已注册
    try:
        existing = db.query(DeviceRegistry).filter_by(
            user_id=user_id, device_id=device_id
        ).first()
        if not existing:
            db.add(DeviceRegistry(
                user_id=user_id,
                device_id=device_id,
                display_name=None,
            ))
            db.commit()
    except Exception as e:
        logger.warning(f"设备注册失败: {e}")
```

**Step 3: 验证语法**

```bash
cd backend
python -m py_compile app/services/token_usage_sync_service.py && echo "OK"
```

**Step 4: 提交**

```bash
git add backend/app/services/token_usage_sync_service.py
git commit -m "feat: 同步时自动注册设备到 device_registry"
```

---

### Task 4: 后端 — 修改 db-query 返回设备名称 + 新增重命名接口

**Files:**
- Modify: `backend/app/routes/token_usage.py`

**Step 1: 修改 import**

第 23 行附近，导入 `DeviceRegistry` 和 `get_device_display_name`：

```python
from app.models.token_usage_models import TokenUsageRecord, TokenUsageSyncLog, DeviceRegistry
```

第 23 行，修改 `get_device_id` 的 import：

```python
from app.utils.device_id import get_device_id, get_device_display_name
```

**Step 2: 新增 DeviceInfo 模型类**

在 `DbUsageResponse` 之前（约第 530 行）添加：

```python
class DeviceInfo(BaseModel):
    id: str
    name: str
```

**Step 3: 修改 DbUsageResponse 的 devices 字段类型**

第 538 行：

```python
class DbUsageResponse(BaseModel):
    items: list[DbUsageItem]
    summary: UsageSummary
    devices: list[DeviceInfo] = Field(default_factory=list)
    cached: bool = False
```

**Step 4: 修改 db_query_token_usage() 中的设备查询逻辑**

第 566-572 行替换为：

```python
        # 获取设备列表（从 device_registry）
        regs = db.query(DeviceRegistry).filter(
            DeviceRegistry.user_id == user_id
        ).all()

        if regs:
            devices = []
            for reg in regs:
                if reg.display_name:
                    name = reg.display_name
                else:
                    name = get_device_display_name()
                devices.append({"id": reg.device_id, "name": name})
        else:
            # 兼容：旧数据没有 device_registry 记录，回退到 token_usage_records
            device_ids = db.query(TokenUsageRecord.device_id).filter(
                TokenUsageRecord.user_id == user_id
            ).distinct().all()
            devices = [{"id": row[0], "name": row[0]} for row in device_ids]

        # 如果有 source 过滤，只显示该 source 下有数据的设备
        if req.source != "all":
            active_ids = set(
                row[0] for row in db.query(TokenUsageRecord.device_id).filter(
                    TokenUsageRecord.user_id == user_id,
                    TokenUsageRecord.source == req.source,
                ).distinct().all()
            )
            devices = [d for d in devices if d["id"] in active_ids]
```

**Step 5: 修改 _fallback_to_cli() 返回值**

第 643 行：

```python
    return DbUsageResponse(items=db_items, summary=summary, devices=[])
```

改为：

```python
    return DbUsageResponse(items=db_items, summary=summary, devices=[])
```

（此处无需改动，空列表兼容新类型）

**Step 6: 新增重命名接口**

在 `/sync` 端点之后（约第 603 行之后）添加：

```python
@router.put("/devices/{device_id}/rename")
async def rename_device(
    device_id: str,
    name: str = Body(..., embed=True, description="设备显示名称，空字符串表示重置为默认"),
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """重命名设备（display_name 为空时回退到 username@hostname）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    db = SessionLocal()
    try:
        reg = db.query(DeviceRegistry).filter_by(
            user_id=user_id, device_id=device_id
        ).first()
        if not reg:
            raise HTTPException(status_code=404, detail="设备不存在")

        reg.display_name = name.strip()[:128] if name.strip() else None
        db.commit()

        return {"device_id": device_id, "display_name": reg.display_name}
    finally:
        db.close()
```

**Step 7: 验证语法**

```bash
cd backend
python -m py_compile app/routes/token_usage.py && echo "OK"
```

**Step 8: 提交**

```bash
git add backend/app/routes/token_usage.py
git commit -m "feat: db-query 返回设备名称 + 新增重命名接口"
```

---

### Task 5: 前端 — 更新 API 类型和重命名函数

**Files:**
- Modify: `frontend/src/api/tokenUsageApi.ts`

**Step 1: 新增 DeviceInfo 类型**

在 `DbQueryParams` 之前（约第 122 行）添加：

```typescript
export interface DeviceInfo {
  id: string;
  name: string;
}
```

**Step 2: 修改 DbUsageResponse 的 devices 类型**

第 139 行：

```typescript
export interface DbUsageResponse {
  items: DbUsageItem[];
  summary: UsageSummary;
  devices: DeviceInfo[];
  cached?: boolean;
}
```

**Step 3: 新增重命名 API 函数**

文件末尾添加：

```typescript
export async function renameDevice(
  deviceId: string,
  name: string
): Promise<{ device_id: string; display_name: string | null }> {
  const response = await fetch(`${BASE_URL}/devices/${deviceId}/rename`, {
    method: 'PUT',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || '重命名设备失败');
  }
  return response.json();
}
```

**Step 4: 验证类型检查**

```bash
cd frontend
npx tsc --noEmit 2>&1 | head -20
```

**Step 5: 提交**

```bash
git add frontend/src/api/tokenUsageApi.ts
git commit -m "feat: 新增 DeviceInfo 类型和重命名 API"
```

---

### Task 6: 前端 — 修改设备下拉框和添加重命名入口

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

**Step 1: 导入重命名 API**

第 2 行附近，修改 import：

```typescript
import { getTokenUsage, getAggregatedTokenUsage, checkTokenUsageHealth, refreshTokenUsage, getDbTokenUsage, syncTokenUsage, renameDevice, UsageItem, UsageSummary } from '../../api/tokenUsageApi';
```

同时导入 `DeviceInfo`：

```typescript
import type { DbUsageItem, DbUsageResponse, DeviceInfo } from '../../api/tokenUsageApi';
```

**Step 2: 修改设备下拉框显示逻辑**

第 377-379 行：

```tsx
{(dbData.devices || []).map(d => (
  <option key={d} value={d}>{d}</option>
))}
```

改为：

```tsx
{(dbData.devices || []).map((d: DeviceInfo) => (
  <option key={d.id} value={d.id}>{d.name}</option>
))}
```

**Step 3: 添加重命名按钮**

在设备下拉框的 `</div>` 闭合标签（约第 381 行）之后，添加重命名按钮：

```tsx
            <button
              onClick={() => handleRenameDevice(selectedDevice)}
              className="p-1.5 text-slate-400 hover:text-slate-200 rounded transition-colors"
              title="重命名设备"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </button>
```

**Step 4: 添加重命名处理函数**

在 `fetchDbData` 函数之后（约第 115 行），添加：

```tsx
  const handleRenameDevice = useCallback(async (deviceId: string) => {
    if (!deviceId) {
      alert('请先选择一个设备');
      return;
    }
    const currentDevice = dbData?.devices?.find((d: DeviceInfo) => d.id === deviceId);
    const currentName = currentDevice?.name || deviceId;
    const newName = prompt('请输入设备名称（留空恢复默认）:', currentName);
    if (newName === null) return; // 用户取消

    try {
      setLoading(true);
      await renameDevice(deviceId, newName);
      // 重新拉取数据
      const result = await getDbTokenUsage({
        type: reportType,
        days,
        group_by: groupBy,
        source,
        device_id: selectedDevice || undefined,
      });
      setDbData(result);
    } catch (e: any) {
      alert(e.message || '重命名失败');
    } finally {
      setLoading(false);
    }
  }, [dbData, reportType, days, groupBy, source, selectedDevice]);
```

**Step 5: 验证类型检查**

```bash
cd frontend
npx tsc --noEmit 2>&1 | head -20
```

**Step 6: 提交**

```bash
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "feat: 设备下拉框显示名称 + 重命名按钮"
```

---

### Task 7: 验证 — 浏览器测试完整功能

**Step 1: 重启后端服务（因新增路由）**

```bash
python dev_services.py restart
```

等待两个服务都就绪。

**Step 2: 在浏览器中访问 Token 消耗统计页面**

使用 agent-browser 或手动打开 http://localhost:5178，导航到 Token 消耗统计页面。

**Step 3: 验证设备下拉框显示名称**

- 点击"数据库查询"模式
- 查看设备下拉框，应该显示 `root@k8s-master` 而非 UUID
- 下拉框应该有 2 个设备选项

**Step 4: 验证重命名功能**

- 选择一个设备
- 点击 ✏️ 重命名按钮
- 输入新名称如 "MacBook Pro"
- 确认下拉框更新显示新名称

**Step 5: 验证切换设备过滤数据**

- 切换不同设备
- 确认图表和数据随设备变化

**Step 6: 验证重置名称（空字符串回退）**

- 重命名时留空或清空
- 确认回退到 `root@k8s-master`

---
