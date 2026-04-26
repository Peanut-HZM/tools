# Token Usage 设备名称优化设计

## 背景

Token 消耗统计页面的设备下拉框当前只显示 UUID（如 `3a7aa0b9-4424-4728-89a7-f2b46b39ff5d`），用户无法区分不同设备。需要支持设备名称显示和手动重命名。

## 方案概述

- 新增 `device_registry` 表管理设备 ID 与显示名称的映射
- 同步时自动注册设备，记录 `username@hostname`
- 用户可手动重命名设备
- `device_id` 保留作为唯一主键

## 数据库设计

### 新表：device_registry

```sql
CREATE TABLE device_registry (
    id            BIGSERIAL PRIMARY KEY,
    user_id       VARCHAR(64) NOT NULL,
    device_id     VARCHAR(128) NOT NULL,
    display_name  VARCHAR(128),          -- 用户自定义名称，NULL 表示使用默认
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, device_id)
);
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `user_id` | 用户 ID，与 token_usage_records 关联 |
| `device_id` | 设备 UUID，与 token_usage_records.device_id 关联 |
| `display_name` | 用户自定义名称；NULL 时自动显示 `username@hostname` |

## 后端改动

### 1. 新增 SQLAlchemy 模型

`backend/app/models/token_usage_models.py`：

```python
class DeviceRegistry(Base):
    __tablename__ = "device_registry"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    device_id = Column(String(128), nullable=False)
    display_name = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "device_id"),)
```

### 2. 同步时自动注册设备

`backend/app/services/token_usage_sync_service.py`：`sync_token_usage()` 函数开始处：

```python
from app.utils.device_id import get_device_id, get_device_display_name

device_id = get_device_id()
display_name = get_device_display_name()  # username@hostname
```

在 `_upsert_records` 写入记录之前，确保 `device_registry` 中有该设备记录：

```python
existing = db.query(DeviceRegistry).filter_by(
    user_id=user_id, device_id=device_id
).first()
if not existing:
    db.add(DeviceRegistry(
        user_id=user_id,
        device_id=device_id,
        display_name=None,  # NULL 表示使用默认名称
    ))
    db.commit()
```

### 3. 查询时返回设备名称

`backend/app/routes/token_usage.py`：`db_query_token_usage()` 中查询设备列表的逻辑修改为：

```python
from app.utils.device_id import get_device_display_name

device_rows = db.query(DeviceRegistry).filter(
    DeviceRegistry.user_id == user_id
).all()

devices = []
for reg in device_rows:
    name = reg.display_name if reg.display_name else get_device_display_name()
    devices.append({"id": reg.device_id, "name": name})

# 兼容：如果 device_registry 为空（旧数据），从 token_usage_records 回退
if not devices:
    device_ids = db.query(TokenUsageRecord.device_id).filter(
        TokenUsageRecord.user_id == user_id
    ).distinct().all()
    devices = [{"id": row[0], "name": row[0]} for row in device_ids]
```

`DbUsageResponse` 中 `devices` 类型从 `list[str]` 改为 `list[dict]`。

### 4. 重命名接口

新增 `PUT /token-usage/devices/{device_id}/rename`：

```python
@router.put("/devices/{device_id}/rename")
async def rename_device(
    device_id: str,
    body: dict = Body(...),
    authorization: Optional[str] = Header(None),
):
    """重命名设备"""
    user_id = get_current_user_id(authorization=authorization)
    display_name = body.get("display_name", "").strip()[:128]
    
    reg = db.query(DeviceRegistry).filter_by(
        user_id=user_id, device_id=device_id
    ).first()
    if not reg:
        raise HTTPException(404, "设备不存在")
    
    reg.display_name = display_name if display_name else None
    db.commit()
    return {"device_id": device_id, "display_name": reg.display_name}
```

## 前端改动

### 1. 设备下拉框

`frontend/src/components/Tools/TokenUsage.tsx`：

- `selectedDevice` 类型保持 `string`（存 device_id）
- 设备选项改为从 `dbData.devices` 数组对象中取 `name` 字段显示
- `{device.name} (${device.id})` 格式，让用户既能看懂也能看到原始 ID

### 2. 重命名功能

- 设备下拉框旁添加 ✏️ 按钮
- 点击弹出简单的 `prompt()` 对话框或 inline input
- 调用 `PUT /api/token-usage/devices/{id}/rename` 后刷新数据

### 3. API 类型调整

`frontend/src/api/tokenUsageApi.ts`：

```typescript
export interface DeviceInfo {
  id: string;
  name: string;
}

export interface DbUsageResponse {
  items: DbUsageItem[];
  summary: UsageSummary;
  devices: DeviceInfo[];
  cached?: boolean;
}
```

## 数据迁移

现有两个设备（`3a7aa0b9` 和 `d298ace1`）需要在 `device_registry` 中补录：

```sql
INSERT INTO device_registry (user_id, device_id, display_name)
SELECT DISTINCT user_id, device_id, NULL
FROM token_usage_records
WHERE user_id = '317efe5a-4a56-4ef2-879b-c96fc7593c08'
ON CONFLICT (user_id, device_id) DO NOTHING;
```

补录后默认显示 `root@k8s-master`（因为同步发生在服务器上），用户可手动重命名。

## 影响范围

| 模块 | 变更 |
|------|------|
| `token_usage_models.py` | 新增 `DeviceRegistry` 模型 |
| `token_usage_sync_service.py` | 同步时自动注册设备 |
| `token_usage.py` (routes) | 修改 `/db-query` 返回值格式，新增 `/devices/{id}/rename` |
| `TokenUsage.tsx` | 下拉框显示名称，新增重命名入口 |
| `tokenUsageApi.ts` | `DeviceInfo` 类型，`DbUsageResponse.devices` 改为对象数组 |
