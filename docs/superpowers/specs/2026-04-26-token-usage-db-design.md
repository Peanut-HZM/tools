---
author: Claude Code
created_at: 2026-04-26
purpose: Token 消耗统计功能完善设计 — 多设备支持、数据入库 PostgreSQL、增量同步、按设备/日期/模型维度查询
---

# Token 消耗统计数据库化设计

## 背景

当前 Token 消耗统计从 CLI 工具（ccusage / opencode-usage）实时获取数据，使用 Redis 缓存。用户希望：
- 支持多设备场景（同一用户在不同设备运行，共享数据库）
- 数据持久化到 PostgreSQL
- 支持按设备、按日期、按模型等多维度查询
- 增量同步（历史数据不变，只写入缺失数据）
- 按用户隔离数据

## 目标

- 建立持久化的 Token 使用数据存储
- 实现增量同步机制
- 支持多维度聚合查询
- 保持与现有功能兼容

## 关键设计决策

1. **设备标识**：`用户名@主机名`（如 `peanut@MacBook-Pro`），并在本地配置文件中持久化设备 UUID 作为稳定标识
2. **存储粒度**：最细粒度 — 每天、每个模型、每个设备、每个数据源一条记录
3. **缓存策略**：数据库作为主存储，Redis 仅缓存聚合查询结果

## 架构设计

### 1. 数据模型（SQLAlchemy 定义，兼容 PostgreSQL 和 SQLite）

#### 1.1 TokenUsageRecord 模型

```python
class TokenUsageRecord(Base):
    __tablename__ = "token_usage_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    device_id = Column(String(128), nullable=False, index=True)
    record_date = Column(Date, nullable=False, index=True)
    source = Column(String(32), nullable=False)        # 'claude' | 'opencode'
    model = Column(String(128), nullable=False)
    input_tokens = Column(BigInteger, nullable=False, default=0)
    output_tokens = Column(BigInteger, nullable=False, default=0)
    cache_creation_tokens = Column(BigInteger, nullable=False, default=0)
    cache_read_tokens = Column(BigInteger, nullable=False, default=0)
    total_tokens = Column(BigInteger, nullable=False, default=0)
    total_cost = Column(Numeric(12, 4), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "device_id", "record_date", "source", "model"),
        Index("idx_token_usage_query", "user_id", "record_date", "source", "device_id"),
    )
```

**说明**：
- 使用 SQLAlchemy 模型定义，自动适配 PostgreSQL 和 SQLite
- `Numeric(12,4)` 在 PostgreSQL 中映射为 `DECIMAL`，在 SQLite 中映射为 `NUMERIC`
- `updated_at` 使用 SQLAlchemy 的 `onupdate=func.now()`，不依赖数据库触发器
- 联合唯一索引防止重复写入
- 复合索引 `(user_id, record_date, source, device_id)` 覆盖主要查询场景

#### 1.2 TokenUsageSyncLog 模型

```python
class TokenUsageSyncLog(Base):
    __tablename__ = "token_usage_sync_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    device_id = Column(String(128), nullable=False)
    source = Column(String(32), nullable=False)
    sync_date = Column(Date, nullable=False)
    status = Column(String(32), nullable=False)        # 'success' | 'failed' | 'partial'
    records_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "device_id", "source", "sync_date"),
    )
```

**说明**：
- 新增 `user_id` 字段，确保多用户隔离
- 联合唯一索引改为 `(user_id, device_id, source, sync_date)`

### 2. 增量同步逻辑

**文件**: `backend/app/services/token_usage_sync_service.py`

核心流程：
1. 获取当前 `device_id`：优先读取本地配置文件 `~/.tools/device_id`，不存在则生成 UUID 并保存，同时记录 `username@hostname` 作为显示名
2. 从 CLI 工具获取最近 N 天（默认 90 天）的 daily 数据
3. 解析数据，按 `(date, model)` 分组
4. 对每条记录，查询数据库是否存在 `(user_id, device_id, date, source, model)`
5. **不存在则 `INSERT`；存在则比较字段值（input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, total_tokens, total_cost），任一字段不同则 `UPDATE`**
6. 记录同步日志到 `token_usage_sync_log`

增量判断逻辑：
```python
existing = db.query(TokenUsageRecord).filter_by(
    user_id=user_id,
    device_id=device_id,
    record_date=date,
    source=source,
    model=model
).first()

if not existing:
    db.add(TokenUsageRecord(...))
else:
    # 比较各字段，如有变化则更新
    if (existing.input_tokens != new_input_tokens or
        existing.output_tokens != new_output_tokens or
        existing.total_tokens != new_total_tokens or
        existing.total_cost != new_total_cost):
        existing.input_tokens = new_input_tokens
        existing.output_tokens = new_output_tokens
        existing.cache_creation_tokens = new_cache_creation_tokens
        existing.cache_read_tokens = new_cache_read_tokens
        existing.total_tokens = new_total_tokens
        existing.total_cost = new_total_cost
```

### 3. 查询 API 设计

**文件**: `backend/app/routes/token_usage.py`

新增 `POST /token-usage/db-query` 端点：

**认证**：从 `Authorization: Bearer <token>` 请求头中提取 `user_id`（复用现有 `get_current_user_id` 依赖）

请求模型：
```python
class DbQueryRequest(BaseModel):
    type: str = "daily"                  # daily | weekly | monthly
    days: int = 30
    group_by: str = "none"             # none | device | model
    source: str = "all"                # claude | opencode | all
    device_id: Optional[str] = None    # 不传则查该用户的所有设备
```

响应模型（复用现有 `UsageResponse`，items 增加可选的 `group_key` 字段）：
```python
class DbUsageItem(UsageItem):
    group_key: Optional[str] = None    # 当 group_by != 'none' 时，标识分组键（设备名或模型名）

class DbUsageResponse(BaseModel):
    items: list[DbUsageItem]
    summary: UsageSummary
    devices: list[str]                 # 该用户有数据的设备列表
    cached: bool = False
```

查询逻辑：
- `group_by=none`：按日期聚合，返回单 series
- `group_by=device`：按设备分组，返回多 series
- `group_by=model`：按模型分组，返回多 series

聚合 SQL 示例（SQLAlchemy 查询）：
```python
query = db.query(
    TokenUsageRecord.record_date.label("date"),
    func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
    func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
    func.sum(TokenUsageRecord.cache_creation_tokens).label("cache_creation_tokens"),
    func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
    func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
    func.sum(TokenUsageRecord.total_cost).label("total_cost"),
).filter(
    TokenUsageRecord.user_id == user_id,
    TokenUsageRecord.record_date >= since_date,
)

if source != "all":
    query = query.filter(TokenUsageRecord.source == source)
if device_id:
    query = query.filter(TokenUsageRecord.device_id == device_id)

results = query.group_by(TokenUsageRecord.record_date).order_by(TokenUsageRecord.record_date).all()
```

### 4. 前端展示

**文件**: `frontend/src/components/Tools/TokenUsage.tsx`

新增控件：
1. **设备筛选下拉框**："全部设备" + 当前用户有数据的设备列表（从 `DbUsageResponse.devices` 获取）
2. **分组维度切换**：`按日期汇总` / `按设备对比` / `按模型分析`
3. 图表适配：
   - `按日期`：单 series 趋势图（与现有一致）
   - `按设备`：多 series 堆叠/分组柱状图
   - `按模型`：多 series 趋势图 + 饼图占比

### 5. 定时任务

**文件**: `backend/app/main.py`

扩展 `refresh_token_usage_cache_periodically`：

```python
async def refresh_token_usage_cache_periodically():
    REFRESH_INTERVAL = 3600
    while True:
        try:
            logger.info("开始 Token Usage 数据同步...")
            # 1. 同步数据到数据库（增量）
            await sync_token_usage_to_db()
            # 2. 刷新 Redis 聚合缓存（基于数据库数据）
            await refresh_aggregated_cache_from_db()
            logger.info("Token Usage 同步完成")
        except Exception as e:
            logger.error(f"Token Usage 同步失败: {e}")
        await asyncio.sleep(REFRESH_INTERVAL)
```

### 6. 降级策略

- 数据库查询无数据时，降级到现有 Redis/CLI 直查模式
- CLI 获取失败时，使用数据库中的历史数据（即使不是最新）
- 设备标识获取失败时，使用 `unknown` 作为 fallback

## 数据流

```
CLI 工具 (ccusage / opencode-usage)
  ↓
定时任务 → 解析数据 → 增量判断（INSERT 或 UPDATE） → 写入 PostgreSQL
  ↓
查询 API → 从 JWT 提取 user_id → 数据库聚合查询 → 返回结果
  ↓ (可选)
Redis 缓存聚合结果（周/月汇总）
```

## 跨平台兼容

- **设备标识**：优先使用本地持久化的 UUID（`~/.tools/device_id`），fallback 到 `username@hostname`。`socket.gethostname()` 和 `getpass.getuser()` 在 Windows/Linux/macOS 均可工作
- **数据库模型**：SQLAlchemy 自动适配 PostgreSQL 和 SQLite，无需手动 DDL
- **定时任务**：使用 asyncio，跨平台无差异

## 迁移路径

1. 启动时自动创建数据库表（SQLAlchemy `Base.metadata.create_all`）
2. 首次运行时，同步最近 90 天历史数据到数据库（增量写入）
3. 后续运行按增量逻辑处理（INSERT 或 UPDATE）
4. 现有 Redis 缓存保持运行，新查询优先从数据库读取
5. 当数据库中有数据时，不再调用 CLI 工具（减少 API 调用）

## 设备标识持久化

在应用启动时检查并生成稳定的设备标识：

```python
def get_device_id():
    config_dir = Path.home() / ".tools"
    config_dir.mkdir(parents=True, exist_ok=True)
    device_file = config_dir / "device_id"

    if device_file.exists():
        return device_file.read_text().strip()

    # 生成新的 UUID
    import uuid
    device_id = str(uuid.uuid4())
    device_file.write_text(device_id)
    return device_id
```

设备显示名使用 `username@hostname`，但数据库中以 UUID 作为稳定的 `device_id`。
