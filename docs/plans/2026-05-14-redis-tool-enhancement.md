# Redis 工具页面增强实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 Redis 工具页面增加批量操作、监控分析面板、Stream/Bitmap/HyperLogLog/Geo 数据结构支持、运维工具（配置管理/数据迁移/危险操作）。

**Architecture:** 前端在键列表区域增加 Tab 导航（键值浏览/监控/运维），KeyDetail 增加类型分发渲染器。后端在现有 `/redis-tool` 路由下新增约 15 个 API 端点，扩展服务层处理新 Redis 命令。

**Tech Stack:** React 18 + TypeScript + Tailwind CSS（前端），FastAPI + redis-py（后端）

---

### Task 1: 扩展后端模型 — 批量操作与监控

**Files:**
- Modify: `backend/app/models/redis_tool_models.py`

**Step 1: 在文件末尾追加新模型**

```python
class BatchTTLRequest(BaseModel):
    keys: List[str]
    ttl: int = Field(..., ge=-1, description="TTL 秒数，-1 表示永久")

class BatchRenameRequest(BaseModel):
    keys: List[str]
    pattern: str = Field(..., description="匹配模式，支持 * 通配符")
    replacement: str = Field(..., description="替换字符串")

class MonitorInfo(BaseModel):
    used_memory: int
    used_memory_human: str
    used_memory_rss: int
    used_memory_peak: int
    connected_clients: int
    maxclients: int
    keyspace_hits: int
    keyspace_misses: int
    hit_rate: float
    ops_per_sec: int
    db_keyspace: Dict[str, Dict[str, int]]

class SlowLogEntry(BaseModel):
    id: int
    timestamp: int
    duration_ms: int
    command: str

class SlowLogResponse(BaseModel):
    entries: List[SlowLogEntry]
```

**Step 2: 确认文件无语法错误**

Run: `cd backend && python -m py_compile app/models/redis_tool_models.py`
Expected: 无输出（成功）

**Step 3: Commit**

```bash
git add backend/app/models/redis_tool_models.py
git commit -m "feat: 增加 Redis 工具批量操作与监控模型"
```

---

### Task 2: 扩展后端模型 — 新数据结构

**Files:**
- Modify: `backend/app/models/redis_tool_models.py`

**Step 1: 在文件末尾追加新模型**

```python
class StreamEntry(BaseModel):
    id: str
    fields: Dict[str, str]

class StreamInfo(BaseModel):
    length: int
    entries: List[StreamEntry]
    groups: List[Dict[str, Any]]

class StreamAddRequest(BaseModel):
    id: str = Field("*", description="条目 ID，* 表示自动生成")
    fields: Dict[str, str]

class StreamOperationRequest(BaseModel):
    action: str = Field(..., description="add|delete|trim|create_group|destroy_group")
    entry_id: Optional[str] = None
    fields: Optional[Dict[str, str]] = None
    group_name: Optional[str] = None
    trim_count: Optional[int] = None

class BitmapInfo(BaseModel):
    bit_count: int
    size_in_bytes: int
    bit_length: int

class BitmapOperationRequest(BaseModel):
    action: str = Field(..., description="getbit|setbit|bitcount|bitpos")
    offset: Optional[int] = None
    value: Optional[int] = Field(None, ge=0, le=1)
    start: Optional[int] = None
    end: Optional[int] = None

class HyperLogLogInfo(BaseModel):
    cardinality: int

class HyperLogLogOperationRequest(BaseModel):
    action: str = Field(..., description="add|count|merge")
    elements: Optional[List[str]] = None
    source_keys: Optional[List[str]] = None

class GeoPoint(BaseModel):
    member: str
    longitude: float
    latitude: float

class GeoInfo(BaseModel):
    members: List[GeoPoint]

class GeoOperationRequest(BaseModel):
    action: str = Field(..., description="add|dist|radius|pos")
    member: Optional[str] = None
    member2: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    radius: Optional[float] = None
    unit: Optional[str] = Field("km", description="m|km|mi|ft")
```

**Step 2: 确认语法**

Run: `cd backend && python -m py_compile app/models/redis_tool_models.py`
Expected: 无输出

**Step 3: Commit**

```bash
git add backend/app/models/redis_tool_models.py
git commit -m "feat: 增加 Stream/Bitmap/HyperLogLog/Geo 数据模型"
```

---

### Task 3: 扩展后端模型 — 运维工具

**Files:**
- Modify: `backend/app/models/redis_tool_models.py`

**Step 1: 在文件末尾追加新模型**

```python
class RedisConfigItem(BaseModel):
    key: str
    value: str
    editable: bool = False

class RedisConfigUpdateRequest(BaseModel):
    key: str
    value: str

class ReplicationInfo(BaseModel):
    role: str
    connected_slaves: int
    master_replid: Optional[str] = None
    master_repl_offset: Optional[int] = None
    slave_info: List[Dict[str, Any]] = []

class FlushRequest(BaseModel):
    mode: str = Field(..., description="db|all")
    db: Optional[int] = None

class MigrateRequest(BaseModel):
    source_config_id: str
    target_config_id: str
    pattern: str = "*"
    replace: bool = False

class MigrateResponse(BaseModel):
    migrated_count: int
    failed_count: int
    errors: List[str] = []

class BigKeyInfo(BaseModel):
    key: str
    type: str
    memory_usage: int
    ttl: int

class BigKeysResponse(BaseModel):
    keys: List[BigKeyInfo]
```

**Step 2: 确认语法**

Run: `cd backend && python -m py_compile app/models/redis_tool_models.py`
Expected: 无输出

**Step 3: Commit**

```bash
git add backend/app/models/redis_tool_models.py
git commit -m "feat: 增加 Redis 运维工具模型"
```

---

### Task 4: 扩展后端服务 — 批量操作

**Files:**
- Modify: `backend/app/services/redis_tool_service.py`

**Step 1: 在 RedisToolService 类中添加批量操作方法**

找到 `delete_keys` 方法之后的位置，添加：

```python
    @staticmethod
    def batch_update_ttl(config_id: str, user_id: str, keys: List[str], ttl: int) -> int:
        """批量更新 key 的 TTL"""
        client = RedisToolService._get_client(config_id, user_id)
        updated = 0
        for key in keys:
            if ttl == -1:
                if client.persist(key):
                    updated += 1
            else:
                if client.expire(key, ttl):
                    updated += 1
        return updated

    @staticmethod
    def batch_rename(config_id: str, user_id: str, keys: List[str], pattern: str, replacement: str) -> int:
        """批量重命名 key，pattern 支持 * 通配符"""
        import fnmatch
        client = RedisToolService._get_client(config_id, user_id)
        renamed = 0
        for key in keys:
            if fnmatch.fnmatch(key, pattern):
                new_key = key.replace(pattern.replace("*", ""), replacement, 1) if "*" not in pattern else key.replace(pattern.strip("*"), replacement)
                # 如果 pattern 包含 *，使用更简单的替换逻辑
                if "*" in pattern:
                    prefix = pattern.split("*")[0] if pattern.split("*")[0] else ""
                    suffix = pattern.split("*")[-1] if pattern.split("*")[-1] else ""
                    if key.startswith(prefix) and key.endswith(suffix):
                        middle = key[len(prefix):len(key)-len(suffix)] if suffix else key[len(prefix):]
                        new_key = replacement.replace("*", middle)
                    else:
                        continue
                else:
                    new_key = key.replace(pattern, replacement, 1)
                if client.rename(key, new_key):
                    renamed += 1
        return renamed
```

**Step 2: 确认语法**

Run: `cd backend && python -m py_compile app/services/redis_tool_service.py`
Expected: 无输出

**Step 3: Commit**

```bash
git add backend/app/services/redis_tool_service.py
git commit -m "feat: Redis 服务层增加批量 TTL 和重命名"
```

---

### Task 5: 扩展后端服务 — 监控

**Files:**
- Modify: `backend/app/services/redis_tool_service.py`

**Step 1: 添加监控相关方法**

```python
    @staticmethod
    def get_monitor_info(config_id: str, user_id: str) -> dict:
        """获取 Redis 监控信息"""
        client = RedisToolService._get_client(config_id, user_id)
        info = client.info()
        
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        hit_rate = hits / (hits + misses) * 100 if (hits + misses) > 0 else 0
        
        # 解析 db keyspace
        db_keyspace = {}
        for key, val in info.items():
            if key.startswith("db"):
                db_keyspace[key] = {
                    "keys": val.get("keys", 0),
                    "expires": val.get("expires", 0)
                }
        
        return {
            "used_memory": info.get("used_memory", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "used_memory_rss": info.get("used_memory_rss", 0),
            "used_memory_peak": info.get("used_memory_peak", 0),
            "connected_clients": info.get("connected_clients", 0),
            "maxclients": info.get("maxclients", 0),
            "keyspace_hits": hits,
            "keyspace_misses": misses,
            "hit_rate": round(hit_rate, 2),
            "ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
            "db_keyspace": db_keyspace
        }

    @staticmethod
    def get_slowlog(config_id: str, user_id: str, count: int = 50) -> List[dict]:
        """获取慢查询日志"""
        client = RedisToolService._get_client(config_id, user_id)
        entries = client.slowlog_get(count)
        result = []
        for entry in entries:
            # entry 格式: [id, timestamp, duration, command_parts]
            command = " ".join(str(x) for x in entry.get("command", [])) if isinstance(entry, dict) else " ".join(str(x) for x in entry[3]) if len(entry) > 3 else ""
            result.append({
                "id": entry.get("id") if isinstance(entry, dict) else entry[0],
                "timestamp": entry.get("time") if isinstance(entry, dict) else entry[1],
                "duration_ms": entry.get("duration") if isinstance(entry, dict) else entry[2],
                "command": command
            })
        return result
```

**Step 2: 确认语法**

Run: `cd backend && python -m py_compile app/services/redis_tool_service.py`
Expected: 无输出

**Step 3: Commit**

```bash
git add backend/app/services/redis_tool_service.py
git commit -m "feat: Redis 服务层增加监控和慢查询功能"
```

---

### Task 6: 扩展后端服务 — Stream 操作

**Files:**
- Modify: `backend/app/services/redis_tool_service.py`

**Step 1: 添加 Stream 操作方法**

```python
    @staticmethod
    def get_stream_info(config_id: str, user_id: str, key: str) -> dict:
        """获取 Stream 信息"""
        client = RedisToolService._get_client(config_id, user_id)
        length = client.xlen(key)
        
        # 获取消费者组信息
        groups = []
        try:
            group_info = client.xinfo_groups(key)
            for g in group_info:
                groups.append({
                    "name": g.get("name", g.get("group")),
                    "consumers": g.get("consumers", 0),
                    "pending": g.get("pending", 0),
                    "last_delivered_id": g.get("last-delivered-id", "")
                })
        except Exception:
            pass
        
        # 获取条目（最多 100 条）
        entries_raw = client.xrange(key, min="-", max="+", count=100)
        entries = []
        for entry_id, fields in entries_raw:
            entries.append({
                "id": entry_id,
                "fields": dict(fields)
            })
        
        return {
            "length": length,
            "entries": entries,
            "groups": groups
        }

    @staticmethod
    def operate_stream(config_id: str, user_id: str, key: str, action: str, **kwargs) -> dict:
        """执行 Stream 操作"""
        client = RedisToolService._get_client(config_id, user_id)
        
        if action == "add":
            entry_id = client.xadd(key, kwargs.get("fields", {}), id=kwargs.get("entry_id", "*"))
            return {"success": True, "entry_id": entry_id}
        elif action == "delete":
            count = client.xdel(key, kwargs.get("entry_id"))
            return {"success": True, "deleted": count}
        elif action == "trim":
            count = client.xtrim(key, maxlen=kwargs.get("trim_count", 1000))
            return {"success": True, "trimmed": count}
        elif action == "create_group":
            client.xgroup_create(key, kwargs.get("group_name"), id="0", mkstream=True)
            return {"success": True}
        elif action == "destroy_group":
            client.xgroup_destroy(key, kwargs.get("group_name"))
            return {"success": True}
        
        return {"success": False, "error": "Unknown action"}
```

**Step 2: 确认语法**

Run: `cd backend && python -m py_compile app/services/redis_tool_service.py`
Expected: 无输出

**Step 3: Commit**

```bash
git add backend/app/services/redis_tool_service.py
git commit -m "feat: Redis 服务层增加 Stream 操作"
```

---

### Task 7: 扩展后端服务 — Bitmap 操作

**Files:**
- Modify: `backend/app/services/redis_tool_service.py`

**Step 1: 添加 Bitmap 操作方法**

```python
    @staticmethod
    def get_bitmap_info(config_id: str, user_id: str, key: str) -> dict:
        """获取 Bitmap 信息"""
        client = RedisToolService._get_client(config_id, user_id)
        bit_count = client.bitcount(key)
        size = client.memory_usage(key) or 0
        # 获取字符串长度作为 bit 长度参考
        str_len = client.strlen(key) or 0
        return {
            "bit_count": bit_count,
            "size_in_bytes": size,
            "bit_length": str_len * 8
        }

    @staticmethod
    def operate_bitmap(config_id: str, user_id: str, key: str, action: str, **kwargs) -> dict:
        """执行 Bitmap 操作"""
        client = RedisToolService._get_client(config_id, user_id)
        
        if action == "getbit":
            bit = client.getbit(key, kwargs.get("offset", 0))
            return {"bit": bit}
        elif action == "setbit":
            old_bit = client.setbit(key, kwargs.get("offset", 0), kwargs.get("value", 0))
            return {"old_bit": old_bit}
        elif action == "bitcount":
            count = client.bitcount(key, start=kwargs.get("start"), end=kwargs.get("end"))
            return {"count": count}
        elif action == "bitpos":
            pos = client.bitpos(key, kwargs.get("value", 1))
            return {"position": pos}
        
        return {"error": "Unknown action"}
```

**Step 2: 确认语法**

Run: `cd backend && python -m py_compile app/services/redis_tool_service.py`
Expected: 无输出

**Step 3: Commit**

```bash
git add backend/app/services/redis_tool_service.py
git commit -m "feat: Redis 服务层增加 Bitmap 操作"
```

---

### Task 8: 扩展后端服务 — HyperLogLog 和 Geo 操作

**Files:**
- Modify: `backend/app/services/redis_tool_service.py`

**Step 1: 添加 HyperLogLog 和 Geo 操作方法**

```python
    @staticmethod
    def get_hyperloglog_info(config_id: str, user_id: str, key: str) -> dict:
        """获取 HyperLogLog 信息"""
        client = RedisToolService._get_client(config_id, user_id)
        cardinality = client.pfcount(key)
        return {"cardinality": cardinality}

    @staticmethod
    def operate_hyperloglog(config_id: str, user_id: str, key: str, action: str, **kwargs) -> dict:
        """执行 HyperLogLog 操作"""
        client = RedisToolService._get_client(config_id, user_id)
        
        if action == "add":
            elements = kwargs.get("elements", [])
            if elements:
                updated = client.pfadd(key, *elements)
                return {"updated": updated}
            return {"updated": 0}
        elif action == "count":
            count = client.pfcount(key)
            return {"cardinality": count}
        elif action == "merge":
            source_keys = kwargs.get("source_keys", [])
            if source_keys:
                client.pfmerge(key, *source_keys)
                return {"success": True}
            return {"success": False, "error": "No source keys"}
        
        return {"error": "Unknown action"}

    @staticmethod
    def get_geo_info(config_id: str, user_id: str, key: str) -> dict:
        """获取 Geo 信息"""
        client = RedisToolService._get_client(config_id, user_id)
        members = client.zrange(key, 0, -1)
        result = []
        if members:
            positions = client.geopos(key, *members)
            for member, pos in zip(members, positions):
                result.append({
                    "member": member,
                    "longitude": pos[0] if pos else None,
                    "latitude": pos[1] if pos else None
                })
        return {"members": result}

    @staticmethod
    def operate_geo(config_id: str, user_id: str, key: str, action: str, **kwargs) -> dict:
        """执行 Geo 操作"""
        client = RedisToolService._get_client(config_id, user_id)
        
        if action == "add":
            client.geoadd(key, (kwargs["longitude"], kwargs["latitude"], kwargs["member"]))
            return {"success": True}
        elif action == "dist":
            dist = client.geodist(key, kwargs["member"], kwargs["member2"], unit=kwargs.get("unit", "km"))
            return {"distance": dist}
        elif action == "radius":
            results = client.georadius(
                key, kwargs["longitude"], kwargs["latitude"],
                kwargs["radius"], unit=kwargs.get("unit", "km"),
                withdist=True, withcoord=True
            )
            members = []
            for item in results:
                members.append({
                    "member": item[0],
                    "distance": item[1],
                    "longitude": item[2][0],
                    "latitude": item[2][1]
                })
            return {"members": members}
        elif action == "pos":
            positions = client.geopos(key, kwargs["member"])
            pos = positions[0] if positions else None
            return {"longitude": pos[0] if pos else None, "latitude": pos[1] if pos else None}
        
        return {"error": "Unknown action"}
```

**Step 2: 确认语法**

Run: `cd backend && python -m py_compile app/services/redis_tool_service.py`
Expected: 无输出

**Step 3: Commit**

```bash
git add backend/app/services/redis_tool_service.py
git commit -m "feat: Redis 服务层增加 HyperLogLog 和 Geo 操作"
```

---

### Task 9: 扩展后端服务 — 运维工具

**Files:**
- Modify: `backend/app/services/redis_tool_service.py`

**Step 1: 添加运维工具方法**

```python
    @staticmethod
    def get_redis_config(config_id: str, user_id: str) -> List[dict]:
        """获取 Redis 配置参数"""
        client = RedisToolService._get_client(config_id, user_id)
        config = client.config_get("*")
        # 标记一些危险的配置项
        dangerous_keys = {"requirepass", "masterauth", "bind"}
        return [
            {"key": k, "value": str(v), "editable": True, "dangerous": k in dangerous_keys}
            for k, v in config.items()
        ]

    @staticmethod
    def update_redis_config(config_id: str, user_id: str, key: str, value: str) -> bool:
        """更新 Redis 配置参数"""
        client = RedisToolService._get_client(config_id, user_id)
        client.config_set(key, value)
        return True

    @staticmethod
    def get_replication_info(config_id: str, user_id: str) -> dict:
        """获取复制信息"""
        client = RedisToolService._get_client(config_id, user_id)
        info = client.info("replication")
        slave_info = []
        for key, val in info.items():
            if key.startswith("slave") and isinstance(val, dict):
                slave_info.append(val)
        return {
            "role": info.get("role", "unknown"),
            "connected_slaves": info.get("connected_slaves", 0),
            "master_replid": info.get("master_replid"),
            "master_repl_offset": info.get("master_repl_offset"),
            "slave_info": slave_info
        }

    @staticmethod
    def flush_db(config_id: str, user_id: str, mode: str, db: Optional[int] = None) -> dict:
        """清空数据库"""
        client = RedisToolService._get_client(config_id, user_id)
        if mode == "all":
            client.flushall()
            return {"message": "All databases flushed"}
        else:
            if db is not None:
                client.execute_command("SELECT", db)
            client.flushdb()
            return {"message": f"Database {db if db is not None else 'current'} flushed"}

    @staticmethod
    def migrate_data(config_id: str, user_id: str, source_config_id: str, target_config_id: str, pattern: str, replace: bool = False) -> dict:
        """数据迁移"""
        source_client = RedisToolService._get_client(source_config_id, user_id)
        target_client = RedisToolService._get_client(target_config_id, user_id)
        
        migrated = 0
        failed = 0
        errors = []
        
        cursor = 0
        while True:
            cursor, keys = source_client.scan(cursor=cursor, match=pattern, count=100)
            for key in keys:
                try:
                    key_type = source_client.type(key)
                    ttl = source_client.ttl(key)
                    ttl = ttl if ttl > 0 else 0
                    
                    # 使用 dump/restore 迁移
                    data = source_client.dump(key)
                    target_client.restore(key, ttl, data, replace=replace)
                    migrated += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"{key}: {str(e)}")
            
            if cursor == 0:
                break
        
        return {"migrated_count": migrated, "failed_count": failed, "errors": errors}

    @staticmethod
    def scan_big_keys(config_id: str, user_id: str, count: int = 50) -> List[dict]:
        """扫描大 Key"""
        client = RedisToolService._get_client(config_id, user_id)
        big_keys = []
        cursor = 0
        scanned = 0
        while scanned < 5000:  # 最多扫描 5000 个 key
            cursor, keys = client.scan(cursor=cursor, count=100)
            for key in keys:
                try:
                    usage = client.memory_usage(key) or 0
                    key_type = client.type(key)
                    ttl = client.ttl(key)
                    big_keys.append({
                        "key": key,
                        "type": key_type,
                        "memory_usage": usage,
                        "ttl": ttl if ttl > 0 else -1
                    })
                except Exception:
                    pass
            scanned += len(keys)
            if cursor == 0:
                break
        
        big_keys.sort(key=lambda x: x["memory_usage"], reverse=True)
        return big_keys[:count]
```

**Step 2: 确认语法**

Run: `cd backend && python -m py_compile app/services/redis_tool_service.py`
Expected: 无输出

**Step 3: Commit**

```bash
git add backend/app/services/redis_tool_service.py
git commit -m "feat: Redis 服务层增加运维工具方法"
```

---

### Task 10: 扩展后端路由 — 批量操作与监控

**Files:**
- Modify: `backend/app/routes/redis_tool.py`

**Step 1: 在导入处增加新模型**

在现有导入末尾追加：

```python
    BatchTTLRequest, BatchRenameRequest,
    MonitorInfo, SlowLogResponse,
    StreamInfo, StreamOperationRequest,
    BitmapInfo, BitmapOperationRequest,
    HyperLogLogInfo, HyperLogLogOperationRequest,
    GeoInfo, GeoOperationRequest,
    RedisConfigItem, RedisConfigUpdateRequest,
    ReplicationInfo, FlushRequest,
    MigrateRequest, MigrateResponse,
    BigKeysResponse
```

**Step 2: 在路由文件末尾追加新端点**

```python
@router.post("/configs/{id}/keys/batch-ttl")
async def batch_update_ttl(
    request: BatchTTLRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """批量更新 key TTL"""
    try:
        count = RedisToolService.batch_update_ttl(id, user_id, request.keys, request.ttl)
        return {"message": f"Updated TTL for {count} keys", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/keys/batch-rename")
async def batch_rename(
    request: BatchRenameRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """批量重命名 key"""
    try:
        count = RedisToolService.batch_rename(id, user_id, request.keys, request.pattern, request.replacement)
        return {"message": f"Renamed {count} keys", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configs/{id}/monitor")
async def get_monitor(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """获取 Redis 监控信息"""
    try:
        return RedisToolService.get_monitor_info(id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configs/{id}/monitor/slowlog")
async def get_slowlog(
    id: str = PathParam(..., description="Configuration ID"),
    count: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id)
):
    """获取慢查询日志"""
    try:
        entries = RedisToolService.get_slowlog(id, user_id, count)
        return {"entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 3: 确认语法**

Run: `cd backend && python -m py_compile app/routes/redis_tool.py`
Expected: 无输出

**Step 4: Commit**

```bash
git add backend/app/routes/redis_tool.py
git commit -m "feat: Redis 路由增加批量操作和监控端点"
```

---

### Task 11: 扩展后端路由 — 新数据结构

**Files:**
- Modify: `backend/app/routes/redis_tool.py`

**Step 1: 追加新数据结构端点**

```python
@router.get("/configs/{id}/keys/{key}/stream")
async def get_stream(
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """获取 Stream 信息"""
    try:
        return RedisToolService.get_stream_info(id, user_id, key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/keys/{key}/stream")
async def operate_stream(
    request: StreamOperationRequest,
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """执行 Stream 操作"""
    try:
        return RedisToolService.operate_stream(
            id, user_id, key, request.action,
            entry_id=request.entry_id,
            fields=request.fields,
            group_name=request.group_name,
            trim_count=request.trim_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configs/{id}/keys/{key}/bitmap")
async def get_bitmap(
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """获取 Bitmap 信息"""
    try:
        return RedisToolService.get_bitmap_info(id, user_id, key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/keys/{key}/bitmap")
async def operate_bitmap(
    request: BitmapOperationRequest,
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """执行 Bitmap 操作"""
    try:
        return RedisToolService.operate_bitmap(
            id, user_id, key, request.action,
            offset=request.offset, value=request.value,
            start=request.start, end=request.end
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configs/{id}/keys/{key}/hyperloglog")
async def get_hyperloglog(
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """获取 HyperLogLog 信息"""
    try:
        return RedisToolService.get_hyperloglog_info(id, user_id, key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/keys/{key}/hyperloglog")
async def operate_hyperloglog(
    request: HyperLogLogOperationRequest,
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """执行 HyperLogLog 操作"""
    try:
        return RedisToolService.operate_hyperloglog(
            id, user_id, key, request.action,
            elements=request.elements,
            source_keys=request.source_keys
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configs/{id}/keys/{key}/geo")
async def get_geo(
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """获取 Geo 信息"""
    try:
        return RedisToolService.get_geo_info(id, user_id, key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/keys/{key}/geo")
async def operate_geo(
    request: GeoOperationRequest,
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """执行 Geo 操作"""
    try:
        return RedisToolService.operate_geo(
            id, user_id, key, request.action,
            member=request.member, member2=request.member2,
            longitude=request.longitude, latitude=request.latitude,
            radius=request.radius, unit=request.unit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: 确认语法**

Run: `cd backend && python -m py_compile app/routes/redis_tool.py`
Expected: 无输出

**Step 3: Commit**

```bash
git add backend/app/routes/redis_tool.py
git commit -m "feat: Redis 路由增加 Stream/Bitmap/HyperLogLog/Geo 端点"
```

---

### Task 12: 扩展后端路由 — 运维工具

**Files:**
- Modify: `backend/app/routes/redis_tool.py`

**Step 1: 追加运维工具端点**

```python
@router.get("/configs/{id}/config")
async def get_redis_config(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """获取 Redis 配置参数"""
    try:
        return RedisToolService.get_redis_config(id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/config")
async def update_redis_config(
    request: RedisConfigUpdateRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """更新 Redis 配置参数"""
    try:
        RedisToolService.update_redis_config(id, user_id, request.key, request.value)
        return {"message": "Configuration updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configs/{id}/replication")
async def get_replication(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """获取复制信息"""
    try:
        return RedisToolService.get_replication_info(id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/flush")
async def flush_db(
    request: FlushRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """清空数据库"""
    try:
        return RedisToolService.flush_db(id, user_id, request.mode, request.db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/migrate")
async def migrate_data(
    request: MigrateRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """数据迁移"""
    try:
        result = RedisToolService.migrate_data(
            id, user_id,
            request.source_config_id, request.target_config_id,
            request.pattern, request.replace
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configs/{id}/bigkeys")
async def get_big_keys(
    id: str = PathParam(..., description="Configuration ID"),
    count: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id)
):
    """扫描大 Key"""
    try:
        keys = RedisToolService.scan_big_keys(id, user_id, count)
        return {"keys": keys}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: 确认语法**

Run: `cd backend && python -m py_compile app/routes/redis_tool.py`
Expected: 无输出

**Step 3: Commit**

```bash
git add backend/app/routes/redis_tool.py
git commit -m "feat: Redis 路由增加运维工具端点"
```

---

### Task 13: 扩展前端 API 层

**Files:**
- Modify: `frontend/src/api/redisToolApi.ts`

**Step 1: 在文件末尾追加新接口**

```typescript
export const batchUpdateTTL = (id: string, keys: string[], ttl: number) => {
  return request<{ message: string; count: number }>(`${REDIS_API_URL}/configs/${id}/keys/batch-ttl`, {
    method: 'POST',
    body: JSON.stringify({ keys, ttl }),
  });
};

export const batchRename = (id: string, keys: string[], pattern: string, replacement: string) => {
  return request<{ message: string; count: number }>(`${REDIS_API_URL}/configs/${id}/keys/batch-rename`, {
    method: 'POST',
    body: JSON.stringify({ keys, pattern, replacement }),
  });
};

export const getMonitorInfo = (id: string) => {
  return request<any>(`${REDIS_API_URL}/configs/${id}/monitor`);
};

export const getSlowLog = (id: string, count: number = 50) => {
  return request<{ entries: any[] }>(`${REDIS_API_URL}/configs/${id}/monitor/slowlog?count=${count}`);
};

export const getStreamInfo = (id: string, key: string) => {
  return request<any>(`${REDIS_API_URL}/configs/${id}/keys/${encodeURIComponent(key)}/stream`);
};

export const operateStream = (id: string, key: string, data: any) => {
  return request<any>(`${REDIS_API_URL}/configs/${id}/keys/${encodeURIComponent(key)}/stream`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const getBitmapInfo = (id: string, key: string) => {
  return request<any>(`${REDIS_API_URL}/configs/${id}/keys/${encodeURIComponent(key)}/bitmap`);
};

export const operateBitmap = (id: string, key: string, data: any) => {
  return request<any>(`${REDIS_API_URL}/configs/${id}/keys/${encodeURIComponent(key)}/bitmap`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const getHyperLogLogInfo = (id: string, key: string) => {
  return request<any>(`${REDIS_API_URL}/configs/${id}/keys/${encodeURIComponent(key)}/hyperloglog`);
};

export const operateHyperLogLog = (id: string, key: string, data: any) => {
  return request<any>(`${REDIS_API_URL}/configs/${id}/keys/${encodeURIComponent(key)}/hyperloglog`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const getGeoInfo = (id: string, key: string) => {
  return request<any>(`${REDIS_API_URL}/configs/${id}/keys/${encodeURIComponent(key)}/geo`);
};

export const operateGeo = (id: string, key: string, data: any) => {
  return request<any>(`${REDIS_API_URL}/configs/${id}/keys/${encodeURIComponent(key)}/geo`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const getRedisConfig = (id: string) => {
  return request<any[]>(`${REDIS_API_URL}/configs/${id}/config`);
};

export const updateRedisConfig = (id: string, key: string, value: string) => {
  return request<{ message: string }>(`${REDIS_API_URL}/configs/${id}/config`, {
    method: 'POST',
    body: JSON.stringify({ key, value }),
  });
};

export const getReplicationInfo = (id: string) => {
  return request<any>(`${REDIS_API_URL}/configs/${id}/replication`);
};

export const flushDB = (id: string, mode: string, db?: number) => {
  return request<any>(`${REDIS_API_URL}/configs/${id}/flush`, {
    method: 'POST',
    body: JSON.stringify({ mode, db }),
  });
};

export const migrateData = (id: string, data: any) => {
  return request<any>(`${REDIS_API_URL}/configs/${id}/migrate`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const getBigKeys = (id: string, count: number = 50) => {
  return request<{ keys: any[] }>(`${REDIS_API_URL}/configs/${id}/bigkeys?count=${count}`);
};
```

**Step 2: 确认 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit src/api/redisToolApi.ts`
Expected: 无输出或仅提示缺少 React 类型（可忽略）

**Step 3: Commit**

```bash
git add frontend/src/api/redisToolApi.ts
git commit -m "feat: 前端 API 层增加 Redis 增强功能接口"
```

---

### Task 14: 修改 KeyExplorer 增加批量模式

**Files:**
- Modify: `frontend/src/components/Tools/RedisTool/KeyExplorer.tsx`

**Step 1: 修改导入和状态**

在现有导入后增加：

```typescript
import { batchUpdateTTL, batchRename } from '../../../api/redisToolApi';
import { BatchToolbar } from './BatchToolbar';
```

在组件内增加状态：

```typescript
  const [batchMode, setBatchMode] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
```

**Step 2: 修改渲染部分**

在搜索框右侧增加批量模式切换按钮（在刷新按钮之前）：

```tsx
            <button
              onClick={() => {
                setBatchMode(!batchMode);
                setSelectedKeys(new Set());
              }}
              className={`px-3 py-2 border rounded-md text-sm transition-colors ${
                batchMode 
                  ? 'bg-blue-600 text-white border-blue-600' 
                  : 'bg-slate-800 text-slate-300 border-slate-700 hover:text-white hover:bg-slate-700'
              }`}
              title={batchMode ? t.redis.exitBatch || 'Exit Batch' : t.redis.batchMode || 'Batch Mode'}
            >
              <i className="fas fa-check-square"></i>
            </button>
```

**Step 3: 在键列表渲染中增加 checkbox 和批量工具栏**

在 `<div className="space-y-1">` 之前插入：

```tsx
            {batchMode && (
              <BatchToolbar
                selectedCount={selectedKeys.size}
                configId={configId}
                selectedKeys={Array.from(selectedKeys)}
                onBatchDelete={async (keys) => {
                  await deleteRedisKeys(configId, keys);
                  addToast(t.redis.deleteSuccess, 'success');
                  setSelectedKeys(new Set());
                  loadKeys();
                }}
                onBatchTTL={async (keys, ttl) => {
                  await batchUpdateTTL(configId, keys, ttl);
                  addToast('TTL updated', 'success');
                  setSelectedKeys(new Set());
                  loadKeys();
                }}
                onBatchRename={async (keys, pattern, replacement) => {
                  await batchRename(configId, keys, pattern, replacement);
                  addToast('Keys renamed', 'success');
                  setSelectedKeys(new Set());
                  loadKeys();
                }}
                onClear={() => setSelectedKeys(new Set())}
              />
            )}
```

修改键列表项的渲染，在点击区域增加 checkbox：

```tsx
              {keys.map((k) => (
                <div
                  key={k.key}
                  className={`p-2 rounded cursor-pointer flex items-center group ${
                    selectedKey === k.key && !batchMode
                        ? 'bg-blue-600 text-white' 
                        : selectedKeys.has(k.key) && batchMode
                        ? 'bg-blue-900/40 text-white'
                        : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                  onClick={() => {
                    if (batchMode) {
                      const newSet = new Set(selectedKeys);
                      if (newSet.has(k.key)) newSet.delete(k.key);
                      else newSet.add(k.key);
                      setSelectedKeys(newSet);
                    } else {
                      setSelectedKey(k.key);
                    }
                  }}
                >
                  {batchMode && (
                    <input
                      type="checkbox"
                      checked={selectedKeys.has(k.key)}
                      onChange={(e) => {
                        e.stopPropagation();
                        const newSet = new Set(selectedKeys);
                        if (e.target.checked) newSet.add(k.key);
                        else newSet.delete(k.key);
                        setSelectedKeys(newSet);
                      }}
                      className="mr-2 w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-600 focus:ring-blue-500"
                    />
                  )}
                  <div className="truncate flex-1 mr-2">
                    ...
                  </div>
                  ...
                </div>
              ))}
```

**Step 4: Commit**

```bash
git add frontend/src/components/Tools/RedisTool/KeyExplorer.tsx
git commit -m "feat: KeyExplorer 增加批量模式和多选功能"
```

---

### Task 15: 创建 BatchToolbar 组件

**Files:**
- Create: `frontend/src/components/Tools/RedisTool/BatchToolbar.tsx`

**Step 1: 创建组件**

```typescript
import React, { useState } from 'react';

interface Props {
  selectedCount: number;
  configId: string;
  selectedKeys: string[];
  onBatchDelete: (keys: string[]) => void;
  onBatchTTL: (keys: string[], ttl: number) => void;
  onBatchRename: (keys: string[], pattern: string, replacement: string) => void;
  onClear: () => void;
}

export const BatchToolbar: React.FC<Props> = ({
  selectedCount,
  selectedKeys,
  onBatchDelete,
  onBatchTTL,
  onBatchRename,
  onClear,
}) => {
  const [showTTLModal, setShowTTLModal] = useState(false);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [ttl, setTtl] = useState(3600);
  const [pattern, setPattern] = useState('*');
  const [replacement, setReplacement] = useState('');

  const handleDelete = () => {
    if (!confirm(`确定删除选中的 ${selectedCount} 个 key？`)) return;
    onBatchDelete(selectedKeys);
  };

  const handleTTL = () => {
    onBatchTTL(selectedKeys, ttl);
    setShowTTLModal(false);
  };

  const handleRename = () => {
    onBatchRename(selectedKeys, pattern, replacement);
    setShowRenameModal(false);
  };

  if (selectedCount === 0) {
    return (
      <div className="p-2 text-xs text-slate-500 flex justify-between items-center">
        <span>批量模式：点击选择 key</span>
        <button onClick={onClear} className="text-slate-400 hover:text-white">取消</button>
      </div>
    );
  }

  return (
    <div className="p-2 bg-slate-800/80 border-b border-slate-700 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-300">已选择 {selectedCount} 个 key</span>
        <div className="flex space-x-1">
          <button onClick={() => setShowTTLModal(true)} className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700">修改 TTL</button>
          <button onClick={() => setShowRenameModal(true)} className="px-2 py-1 text-xs bg-purple-600 text-white rounded hover:bg-purple-700">重命名</button>
          <button onClick={handleDelete} className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700">删除</button>
          <button onClick={onClear} className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded hover:bg-slate-600">清空</button>
        </div>
      </div>

      {showTTLModal && (
        <div className="flex items-center space-x-2">
          <input
            type="number"
            value={ttl}
            onChange={(e) => setTtl(parseInt(e.target.value))}
            className="w-24 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
            placeholder="TTL (秒)"
          />
          <button onClick={handleTTL} className="px-2 py-1 text-xs bg-green-600 text-white rounded">确认</button>
          <button onClick={() => setShowTTLModal(false)} className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded">取消</button>
        </div>
      )}

      {showRenameModal && (
        <div className="flex items-center space-x-2">
          <input
            type="text"
            value={pattern}
            onChange={(e) => setPattern(e.target.value)}
            className="w-32 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
            placeholder="匹配模式"
          />
          <span className="text-slate-400">→</span>
          <input
            type="text"
            value={replacement}
            onChange={(e) => setReplacement(e.target.value)}
            className="w-32 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
            placeholder="替换为"
          />
          <button onClick={handleRename} className="px-2 py-1 text-xs bg-green-600 text-white rounded">确认</button>
          <button onClick={() => setShowRenameModal(false)} className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded">取消</button>
        </div>
      )}
    </div>
  );
};
```

**Step 2: Commit**

```bash
git add frontend/src/components/Tools/RedisTool/BatchToolbar.tsx
git commit -m "feat: 创建 Redis 批量操作工具栏组件"
```

---

### Task 16: 修改 KeyDetail 增加类型分发

**Files:**
- Modify: `frontend/src/components/Tools/RedisTool/KeyDetail.tsx`

**Step 1: 修改导入和类型分发**

在现有导入后增加：

```typescript
import { StreamEditor } from './StreamEditor';
import { BitmapEditor } from './BitmapEditor';
import { HyperLogLogEditor } from './HyperLogLogEditor';
import { GeoEditor } from './GeoEditor';
```

替换值渲染部分（`<pre>` 标签区域），在 `formatValue` 之后增加类型分发：

```tsx
      <div className="flex-1 p-4 overflow-hidden flex flex-col">
        {editing ? (
          <div className="h-full flex flex-col">
            ...
          </div>
        ) : (
          <div className="flex-1 bg-slate-800 rounded-md border border-slate-700 p-4 overflow-auto">
            {content.type === 'stream' && (
              <StreamEditor configId={configId} keyName={keyName} />
            )}
            {content.type === 'bitmap' && (
              <BitmapEditor configId={configId} keyName={keyName} />
            )}
            {content.type === 'hyperloglog' && (
              <HyperLogLogEditor configId={configId} keyName={keyName} />
            )}
            {content.type === 'geo' && (
              <GeoEditor configId={configId} keyName={keyName} />
            )}
            {['string', 'list', 'set', 'zset', 'hash'].includes(content.type) && (
              <pre className="font-mono text-sm text-slate-300 whitespace-pre-wrap break-all">
                {formatValue(content.value)}
              </pre>
            )}
          </div>
        )}
      </div>
```

**Step 2: Commit**

```bash
git add frontend/src/components/Tools/RedisTool/KeyDetail.tsx
git commit -m "feat: KeyDetail 增加新数据类型分发"
```

---

### Task 17: 创建 StreamEditor 组件

**Files:**
- Create: `frontend/src/components/Tools/RedisTool/StreamEditor.tsx`

**Step 1: 创建组件**

```typescript
import React, { useState, useEffect } from 'react';
import { getStreamInfo, operateStream } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';

interface Props {
  configId: string;
  keyName: string;
}

export const StreamEditor: React.FC<Props> = ({ configId, keyName }) => {
  const { addToast } = useToast();
  const [info, setInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [newFields, setNewFields] = useState<{ key: string; value: string }[]>([{ key: '', value: '' }]);

  const load = async () => {
    try {
      const data = await getStreamInfo(configId, keyName);
      setInfo(data);
    } catch (e) {
      addToast('Failed to load stream', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [configId, keyName]);

  const handleAdd = async () => {
    const fields: Record<string, string> = {};
    newFields.forEach(f => { if (f.key) fields[f.key] = f.value; });
    if (Object.keys(fields).length === 0) return;
    try {
      await operateStream(configId, keyName, { action: 'add', fields });
      addToast('Entry added', 'success');
      setNewFields([{ key: '', value: '' }]);
      load();
    } catch (e) {
      addToast('Failed to add entry', 'error');
    }
  };

  const handleDelete = async (entryId: string) => {
    if (!confirm(`Delete entry ${entryId}?`)) return;
    try {
      await operateStream(configId, keyName, { action: 'delete', entry_id: entryId });
      addToast('Entry deleted', 'success');
      load();
    } catch (e) {
      addToast('Failed to delete', 'error');
    }
  };

  if (loading) return <div className="text-slate-400">Loading...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-400">Length: {info?.length || 0} | Groups: {info?.groups?.length || 0}</div>
      </div>

      <div className="border border-slate-700 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="px-3 py-2 text-left">ID</th>
              <th className="px-3 py-2 text-left">Fields</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {info?.entries?.map((entry: any) => (
              <tr key={entry.id} className="border-t border-slate-700 hover:bg-slate-800/50">
                <td className="px-3 py-2 font-mono text-slate-300">{entry.id}</td>
                <td className="px-3 py-2">
                  {Object.entries(entry.fields).map(([k, v]) => (
                    <span key={k} className="inline-block mr-2 text-xs bg-slate-700 px-1.5 py-0.5 rounded">
                      {k}: {String(v)}
                    </span>
                  ))}
                </td>
                <td className="px-3 py-2 text-right">
                  <button onClick={() => handleDelete(entry.id)} className="text-red-400 hover:text-red-300 text-xs">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="border border-slate-700 rounded-md p-3">
        <div className="text-sm font-medium text-slate-300 mb-2">Add Entry</div>
        {newFields.map((f, i) => (
          <div key={i} className="flex space-x-2 mb-2">
            <input value={f.key} onChange={e => {
              const nf = [...newFields];
              nf[i].key = e.target.value;
              setNewFields(nf);
            }} placeholder="Field" className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200" />
            <input value={f.value} onChange={e => {
              const nf = [...newFields];
              nf[i].value = e.target.value;
              setNewFields(nf);
            }} placeholder="Value" className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200" />
          </div>
        ))}
        <div className="flex space-x-2">
          <button onClick={() => setNewFields([...newFields, { key: '', value: '' }])} className="text-xs text-blue-400 hover:text-blue-300">+ Add field</button>
          <button onClick={handleAdd} className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">Add Entry</button>
        </div>
      </div>
    </div>
  );
};
```

**Step 2: Commit**

```bash
git add frontend/src/components/Tools/RedisTool/StreamEditor.tsx
git commit -m "feat: 创建 Stream 数据类型编辑器"
```

---

### Task 18: 创建 BitmapEditor 组件

**Files:**
- Create: `frontend/src/components/Tools/RedisTool/BitmapEditor.tsx`

**Step 1: 创建组件**

```typescript
import React, { useState, useEffect } from 'react';
import { getBitmapInfo, operateBitmap } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';

interface Props {
  configId: string;
  keyName: string;
}

export const BitmapEditor: React.FC<Props> = ({ configId, keyName }) => {
  const { addToast } = useToast();
  const [info, setInfo] = useState<any>(null);
  const [offset, setOffset] = useState(0);
  const [bitValue, setBitValue] = useState(1);

  const load = async () => {
    try {
      const data = await getBitmapInfo(configId, keyName);
      setInfo(data);
    } catch (e) {
      addToast('Failed to load bitmap', 'error');
    }
  };

  useEffect(() => { load(); }, [configId, keyName]);

  const handleSetBit = async () => {
    try {
      await operateBitmap(configId, keyName, { action: 'setbit', offset, value: bitValue });
      addToast('Bit updated', 'success');
      load();
    } catch (e) {
      addToast('Failed to set bit', 'error');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-4 text-sm text-slate-400">
        <span>Bit count: {info?.bit_count || 0}</span>
        <span>Size: {info?.size_in_bytes || 0} bytes</span>
        <span>Bit length: {info?.bit_length || 0}</span>
      </div>

      <div className="border border-slate-700 rounded-md p-3 space-y-3">
        <div className="text-sm font-medium text-slate-300">Set Bit</div>
        <div className="flex space-x-2 items-center">
          <input
            type="number"
            value={offset}
            onChange={e => setOffset(parseInt(e.target.value) || 0)}
            placeholder="Offset"
            className="w-32 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
          />
          <select
            value={bitValue}
            onChange={e => setBitValue(parseInt(e.target.value))}
            className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
          >
            <option value={1}>1</option>
            <option value={0}>0</option>
          </select>
          <button onClick={handleSetBit} className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">Set</button>
        </div>
      </div>
    </div>
  );
};
```

**Step 2: Commit**

```bash
git add frontend/src/components/Tools/RedisTool/BitmapEditor.tsx
git commit -m "feat: 创建 Bitmap 数据类型编辑器"
```

---

### Task 19: 创建 HyperLogLogEditor 组件

**Files:**
- Create: `frontend/src/components/Tools/RedisTool/HyperLogLogEditor.tsx`

**Step 1: 创建组件**

```typescript
import React, { useState, useEffect } from 'react';
import { getHyperLogLogInfo, operateHyperLogLog } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';

interface Props {
  configId: string;
  keyName: string;
}

export const HyperLogLogEditor: React.FC<Props> = ({ configId, keyName }) => {
  const { addToast } = useToast();
  const [info, setInfo] = useState<any>(null);
  const [element, setElement] = useState('');

  const load = async () => {
    try {
      const data = await getHyperLogLogInfo(configId, keyName);
      setInfo(data);
    } catch (e) {
      addToast('Failed to load HLL', 'error');
    }
  };

  useEffect(() => { load(); }, [configId, keyName]);

  const handleAdd = async () => {
    if (!element.trim()) return;
    try {
      await operateHyperLogLog(configId, keyName, { action: 'add', elements: [element.trim()] });
      addToast('Element added', 'success');
      setElement('');
      load();
    } catch (e) {
      addToast('Failed to add', 'error');
    }
  };

  return (
    <div className="space-y-4">
      <div className="text-sm text-slate-400">
        Cardinality (estimated unique elements): <span className="text-white font-mono text-lg">{info?.cardinality || 0}</span>
      </div>

      <div className="border border-slate-700 rounded-md p-3 space-y-2">
        <div className="text-sm font-medium text-slate-300">Add Element</div>
        <div className="flex space-x-2">
          <input
            value={element}
            onChange={e => setElement(e.target.value)}
            placeholder="Element value"
            className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
          />
          <button onClick={handleAdd} className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">Add</button>
        </div>
      </div>
    </div>
  );
};
```

**Step 2: Commit**

```bash
git add frontend/src/components/Tools/RedisTool/HyperLogLogEditor.tsx
git commit -m "feat: 创建 HyperLogLog 数据类型编辑器"
```

---

### Task 20: 创建 GeoEditor 组件

**Files:**
- Create: `frontend/src/components/Tools/RedisTool/GeoEditor.tsx`

**Step 1: 创建组件**

```typescript
import React, { useState, useEffect } from 'react';
import { getGeoInfo, operateGeo } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';

interface Props {
  configId: string;
  keyName: string;
}

export const GeoEditor: React.FC<Props> = ({ configId, keyName }) => {
  const { addToast } = useToast();
  const [info, setInfo] = useState<any>(null);
  const [member, setMember] = useState('');
  const [longitude, setLongitude] = useState('');
  const [latitude, setLatitude] = useState('');

  const load = async () => {
    try {
      const data = await getGeoInfo(configId, keyName);
      setInfo(data);
    } catch (e) {
      addToast('Failed to load geo', 'error');
    }
  };

  useEffect(() => { load(); }, [configId, keyName]);

  const handleAdd = async () => {
    if (!member || !longitude || !latitude) return;
    try {
      await operateGeo(configId, keyName, {
        action: 'add',
        member,
        longitude: parseFloat(longitude),
        latitude: parseFloat(latitude)
      });
      addToast('Location added', 'success');
      setMember('');
      setLongitude('');
      setLatitude('');
      load();
    } catch (e) {
      addToast('Failed to add', 'error');
    }
  };

  return (
    <div className="space-y-4">
      <div className="border border-slate-700 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr><th className="px-3 py-2 text-left">Member</th><th className="px-3 py-2 text-left">Longitude</th><th className="px-3 py-2 text-left">Latitude</th></tr>
          </thead>
          <tbody>
            {info?.members?.map((m: any) => (
              <tr key={m.member} className="border-t border-slate-700">
                <td className="px-3 py-2 text-slate-300">{m.member}</td>
                <td className="px-3 py-2 font-mono text-slate-400">{m.longitude?.toFixed(6) || '-'}</td>
                <td className="px-3 py-2 font-mono text-slate-400">{m.latitude?.toFixed(6) || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="border border-slate-700 rounded-md p-3 space-y-2">
        <div className="text-sm font-medium text-slate-300">Add Location</div>
        <div className="flex space-x-2">
          <input value={member} onChange={e => setMember(e.target.value)} placeholder="Member" className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200" />
          <input value={longitude} onChange={e => setLongitude(e.target.value)} placeholder="Longitude" className="w-28 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200" />
          <input value={latitude} onChange={e => setLatitude(e.target.value)} placeholder="Latitude" className="w-28 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200" />
          <button onClick={handleAdd} className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">Add</button>
        </div>
      </div>
    </div>
  );
};
```

**Step 2: Commit**

```bash
git add frontend/src/components/Tools/RedisTool/GeoEditor.tsx
git commit -m "feat: 创建 Geo 数据类型编辑器"
```

---

### Task 21: 创建 MonitorPanel 组件

**Files:**
- Create: `frontend/src/components/Tools/RedisTool/MonitorPanel.tsx`

**Step 1: 创建组件**

```typescript
import React, { useState, useEffect } from 'react';
import { getMonitorInfo, getSlowLog } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';

interface Props {
  configId: string;
}

export const MonitorPanel: React.FC<Props> = ({ configId }) => {
  const { addToast } = useToast();
  const [monitor, setMonitor] = useState<any>(null);
  const [slowLog, setSlowLog] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [m, s] = await Promise.all([
        getMonitorInfo(configId),
        getSlowLog(configId, 50)
      ]);
      setMonitor(m);
      setSlowLog(s.entries || []);
    } catch (e) {
      addToast('Failed to load monitor data', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [configId]);

  if (loading) return <div className="flex justify-center items-center h-full text-slate-400">Loading...</div>;

  const memPercent = monitor?.maxclients ? Math.min((monitor.used_memory / (monitor.used_memory_rss || 1)) * 100, 100) : 0;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      {/* 指标卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <div className="text-xs text-slate-400">内存使用</div>
          <div className="text-xl font-mono text-white mt-1">{monitor?.used_memory_human || '0B'}</div>
          <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${Math.min(memPercent, 100)}%` }} />
          </div>
        </div>
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <div className="text-xs text-slate-400">连接数</div>
          <div className="text-xl font-mono text-white mt-1">{monitor?.connected_clients || 0} <span className="text-xs text-slate-500">/ {monitor?.maxclients || 0}</span></div>
        </div>
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <div className="text-xs text-slate-400">命中率</div>
          <div className="text-xl font-mono text-white mt-1">{monitor?.hit_rate?.toFixed(2) || 0}%</div>
        </div>
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <div className="text-xs text-slate-400">OPS</div>
          <div className="text-xl font-mono text-white mt-1">{monitor?.ops_per_sec || 0}</div>
        </div>
      </div>

      {/* 数据库分布 */}
      {monitor?.db_keyspace && Object.keys(monitor.db_keyspace).length > 0 && (
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <div className="text-sm font-medium text-slate-300 mb-3">数据库 Key 分布</div>
          <div className="grid grid-cols-4 gap-2">
            {Object.entries(monitor.db_keyspace).map(([db, data]: [string, any]) => (
              <div key={db} className="bg-slate-900 rounded p-2">
                <div className="text-xs text-slate-400">{db}</div>
                <div className="text-sm text-white">{data.keys} keys</div>
                <div className="text-xs text-slate-500">{data.expires} expires</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 慢查询日志 */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700 text-sm font-medium text-slate-300">慢查询日志（最近 50 条）</div>
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr><th className="px-4 py-2 text-left">ID</th><th className="px-4 py-2 text-left">命令</th><th className="px-4 py-2 text-right">耗时 (ms)</th></tr>
          </thead>
          <tbody>
            {slowLog.map((entry) => (
              <tr key={entry.id} className="border-t border-slate-700 hover:bg-slate-800/50">
                <td className="px-4 py-2 font-mono text-slate-400">{entry.id}</td>
                <td className="px-4 py-2 text-slate-300 font-mono text-xs">{entry.command}</td>
                <td className="px-4 py-2 text-right text-slate-300">{entry.duration_ms}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
```

**Step 2: Commit**

```bash
git add frontend/src/components/Tools/RedisTool/MonitorPanel.tsx
git commit -m "feat: 创建 Redis 监控面板组件"
```

---

### Task 22: 创建 OperationsPanel 组件

**Files:**
- Create: `frontend/src/components/Tools/RedisTool/OperationsPanel.tsx`

**Step 1: 创建组件**

```typescript
import React, { useState, useEffect } from 'react';
import { getRedisConfig, updateRedisConfig, getReplicationInfo, flushDB, getBigKeys } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';
import { MigrateWizard } from './MigrateWizard';

interface Props {
  configId: string;
}

export const OperationsPanel: React.FC<Props> = ({ configId }) => {
  const { addToast } = useToast();
  const [configs, setConfigs] = useState<any[]>([]);
  const [replication, setReplication] = useState<any>(null);
  const [bigKeys, setBigKeys] = useState<any[]>([]);
  const [showMigrate, setShowMigrate] = useState(false);
  const [filter, setFilter] = useState('');

  const load = async () => {
    try {
      const [c, r, b] = await Promise.all([
        getRedisConfig(configId),
        getReplicationInfo(configId),
        getBigKeys(configId, 50)
      ]);
      setConfigs(c);
      setReplication(r);
      setBigKeys(b.keys || []);
    } catch (e) {
      addToast('Failed to load operations data', 'error');
    }
  };

  useEffect(() => { load(); }, [configId]);

  const handleConfigUpdate = async (key: string, value: string) => {
    try {
      await updateRedisConfig(configId, key, value);
      addToast('Config updated', 'success');
      load();
    } catch (e) {
      addToast('Failed to update config', 'error');
    }
  };

  const handleFlush = async (mode: string) => {
    const msg = mode === 'all' ? '确定要清空所有数据库吗？此操作不可撤销！' : '确定要清空当前数据库吗？此操作不可撤销！';
    if (!confirm(msg)) return;
    try {
      const result = await flushDB(configId, mode);
      addToast(result.message, 'success');
    } catch (e) {
      addToast('Flush failed', 'error');
    }
  };

  const filteredConfigs = configs.filter(c => c.key.toLowerCase().includes(filter.toLowerCase()));

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      {/* 危险操作 */}
      <div className="bg-red-900/20 border border-red-800 rounded-lg p-4">
        <div className="text-sm font-medium text-red-400 mb-3">危险操作</div>
        <div className="flex space-x-2">
          <button onClick={() => handleFlush('db')} className="px-3 py-1.5 bg-red-700 text-white text-xs rounded hover:bg-red-600">FLUSHDB</button>
          <button onClick={() => handleFlush('all')} className="px-3 py-1.5 bg-red-700 text-white text-xs rounded hover:bg-red-600">FLUSHALL</button>
        </div>
      </div>

      {/* 数据迁移 */}
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <div className="flex justify-between items-center mb-3">
          <div className="text-sm font-medium text-slate-300">数据迁移</div>
          <button onClick={() => setShowMigrate(!showMigrate)} className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">
            {showMigrate ? '关闭' : '开始迁移'}
          </button>
        </div>
        {showMigrate && <MigrateWizard configId={configId} onClose={() => setShowMigrate(false)} />}
      </div>

      {/* 复制信息 */}
      {replication && (
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <div className="text-sm font-medium text-slate-300 mb-3">复制信息</div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="text-slate-400">Role:</div><div className="text-white">{replication.role}</div>
            <div className="text-slate-400">Connected Slaves:</div><div className="text-white">{replication.connected_slaves}</div>
            {replication.master_replid && <><div className="text-slate-400">Repl ID:</div><div className="text-white font-mono text-xs">{replication.master_replid}</div></>}
          </div>
        </div>
      )}

      {/* 配置管理 */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700 flex justify-between items-center">
          <div className="text-sm font-medium text-slate-300">配置参数</div>
          <input
            value={filter}
            onChange={e => setFilter(e.target.value)}
            placeholder="搜索配置项..."
            className="w-48 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200"
          />
        </div>
        <div className="max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-900 text-slate-400 sticky top-0">
              <tr><th className="px-4 py-2 text-left">Key</th><th className="px-4 py-2 text-left">Value</th></tr>
            </thead>
            <tbody>
              {filteredConfigs.map((c) => (
                <tr key={c.key} className="border-t border-slate-700 hover:bg-slate-800/50">
                  <td className="px-4 py-2 font-mono text-xs text-slate-400">{c.key}</td>
                  <td className="px-4 py-2">
                    {c.editable ? (
                      <input
                        defaultValue={c.value}
                        onBlur={e => handleConfigUpdate(c.key, e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200"
                      />
                    ) : (
                      <span className="text-slate-300">{c.value}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 大 Key 扫描 */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700 text-sm font-medium text-slate-300">大 Key Top 50</div>
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr><th className="px-4 py-2 text-left">Key</th><th className="px-4 py-2 text-left">Type</th><th className="px-4 py-2 text-right">Memory</th></tr>
          </thead>
          <tbody>
            {bigKeys.map((k) => (
              <tr key={k.key} className="border-t border-slate-700 hover:bg-slate-800/50">
                <td className="px-4 py-2 font-mono text-xs text-slate-300">{k.key}</td>
                <td className="px-4 py-2"><span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-700 text-slate-300">{k.type}</span></td>
                <td className="px-4 py-2 text-right text-slate-300">{(k.memory_usage / 1024).toFixed(2)} KB</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
```

**Step 2: Commit**

```bash
git add frontend/src/components/Tools/RedisTool/OperationsPanel.tsx
git commit -m "feat: 创建 Redis 运维工具面板组件"
```

---

### Task 23: 创建 MigrateWizard 组件

**Files:**
- Create: `frontend/src/components/Tools/RedisTool/MigrateWizard.tsx`

**Step 1: 创建组件**

```typescript
import React, { useState } from 'react';
import { migrateData } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';

interface Props {
  configId: string;
  onClose: () => void;
}

export const MigrateWizard: React.FC<Props> = ({ configId, onClose }) => {
  const { addToast } = useToast();
  const [step, setStep] = useState(1);
  const [targetConfigId, setTargetConfigId] = useState('');
  const [pattern, setPattern] = useState('*');
  const [replace, setReplace] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [migrating, setMigrating] = useState(false);

  const handleMigrate = async () => {
    if (!targetConfigId) {
      addToast('请选择目标连接', 'error');
      return;
    }
    setMigrating(true);
    try {
      const res = await migrateData(configId, {
        source_config_id: configId,
        target_config_id: targetConfigId,
        pattern,
        replace
      });
      setResult(res);
      setStep(4);
      addToast(`迁移完成：成功 ${res.migrated_count} 个，失败 ${res.failed_count} 个`, 'success');
    } catch (e) {
      addToast('迁移失败', 'error');
    } finally {
      setMigrating(false);
    }
  };

  return (
    <div className="mt-3 space-y-3">
      {step === 1 && (
        <div className="space-y-2">
          <div className="text-xs text-slate-400">目标连接 ID</div>
          <input
            value={targetConfigId}
            onChange={e => setTargetConfigId(e.target.value)}
            placeholder="输入目标 Redis 配置 ID"
            className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
          />
          <button onClick={() => setStep(2)} className="px-3 py-1 bg-blue-600 text-white text-xs rounded">下一步</button>
        </div>
      )}
      {step === 2 && (
        <div className="space-y-2">
          <div className="text-xs text-slate-400">Key 匹配模式</div>
          <input value={pattern} onChange={e => setPattern(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200" />
          <div className="flex items-center space-x-2">
            <input type="checkbox" checked={replace} onChange={e => setReplace(e.target.checked)} className="w-4 h-4" />
            <span className="text-xs text-slate-400">覆盖已存在的 key</span>
          </div>
          <div className="flex space-x-2">
            <button onClick={() => setStep(1)} className="px-3 py-1 bg-slate-700 text-slate-300 text-xs rounded">上一步</button>
            <button onClick={() => setStep(3)} className="px-3 py-1 bg-blue-600 text-white text-xs rounded">下一步</button>
          </div>
        </div>
      )}
      {step === 3 && (
        <div className="space-y-2">
          <div className="text-sm text-slate-300">确认迁移配置：</div>
          <div className="text-xs text-slate-400">源连接: {configId}</div>
          <div className="text-xs text-slate-400">目标连接: {targetConfigId}</div>
          <div className="text-xs text-slate-400">Pattern: {pattern}</div>
          <div className="text-xs text-slate-400">Replace: {replace ? 'Yes' : 'No'}</div>
          <div className="flex space-x-2">
            <button onClick={() => setStep(2)} className="px-3 py-1 bg-slate-700 text-slate-300 text-xs rounded">上一步</button>
            <button onClick={handleMigrate} disabled={migrating} className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50">
              {migrating ? '迁移中...' : '执行迁移'}
            </button>
          </div>
        </div>
      )}
      {step === 4 && result && (
        <div className="space-y-2">
          <div className="text-sm text-green-400">迁移完成</div>
          <div className="text-xs text-slate-400">成功: {result.migrated_count}</div>
          <div className="text-xs text-slate-400">失败: {result.failed_count}</div>
          {result.errors?.length > 0 && (
            <div className="text-xs text-red-400">错误: {result.errors.slice(0, 5).join(', ')}</div>
          )}
          <button onClick={onClose} className="px-3 py-1 bg-slate-700 text-slate-300 text-xs rounded">关闭</button>
        </div>
      )}
    </div>
  );
};
```

**Step 2: Commit**

```bash
git add frontend/src/components/Tools/RedisTool/MigrateWizard.tsx
git commit -m "feat: 创建 Redis 数据迁移向导组件"
```

---

### Task 24: 修改 RedisTool 增加 Tab 导航

**Files:**
- Modify: `frontend/src/components/Tools/RedisTool/RedisTool.tsx`

**Step 1: 修改导入**

```typescript
import { MonitorPanel } from './MonitorPanel';
import { OperationsPanel } from './OperationsPanel';
```

**Step 2: 增加 Tab 状态**

```typescript
  const [activeTab, setActiveTab] = useState<'keys' | 'monitor' | 'ops'>('keys');
```

**Step 3: 修改渲染部分**

替换 `<div className="flex-1 overflow-hidden bg-slate-900">...</div>` 区域：

```tsx
      <div className="flex-1 overflow-hidden bg-slate-900 flex flex-col">
        {selectedConfigId ? (
          <>
            {/* Tab 导航 */}
            <div className="flex border-b border-slate-700 bg-slate-800">
              <button
                onClick={() => setActiveTab('keys')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === 'keys' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <i className="fas fa-key mr-1"></i> 键值浏览
              </button>
              <button
                onClick={() => setActiveTab('monitor')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === 'monitor' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <i className="fas fa-chart-line mr-1"></i> 监控
              </button>
              <button
                onClick={() => setActiveTab('ops')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === 'ops' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <i className="fas fa-tools mr-1"></i> 运维
              </button>
            </div>

            {/* Tab 内容 */}
            <div className="flex-1 overflow-hidden">
              {activeTab === 'keys' && <KeyExplorer configId={selectedConfigId} />}
              {activeTab === 'monitor' && <MonitorPanel configId={selectedConfigId} />}
              {activeTab === 'ops' && <OperationsPanel configId={selectedConfigId} />}
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <i className="fas fa-server text-6xl mb-4 opacity-20"></i>
            <p className="text-lg">{t.redis.selectConnection}</p>
          </div>
        )}
      </div>
```

**Step 4: 验证编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误（或仅有不相关错误）

**Step 5: Commit**

```bash
git add frontend/src/components/Tools/RedisTool/RedisTool.tsx
git commit -m "feat: RedisTool 主组件增加 Tab 导航"
```

---

### Task 25: 端到端验证

**Step 1: 启动前后端服务**

Run: `python dev_services.py`
Expected: 前后端启动成功

**Step 2: 浏览器访问验证**

访问 http://localhost:5178/tools/redis-tool
验证：
- Tab 导航（键值浏览/监控/运维）正常切换
- 键列表批量模式 checkbox 和多选正常
- 选中 key 后批量删除/TTL/重命名按钮可用
- Stream/Bitmap/HyperLogLog/Geo 类型 key 点击后显示专用编辑器
- 监控面板显示内存/连接数/命中率/OPS 卡片和慢查询日志
- 运维面板显示配置参数表格、复制信息、大 Key 列表
- FLUSHDB 按钮带确认弹窗
- 浏览器 Console 无报错

**Step 3: Commit**

```bash
git add .
git commit -m "feat: Redis 工具页面完整增强（批量操作/监控/新数据结构/运维工具）"
```
