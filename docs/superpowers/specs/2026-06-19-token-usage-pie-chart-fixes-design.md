---
author: Peanut
created_at: 2026-06-19
purpose: 修复 /tools/token-usage 页面四个饼图中设备名称不同步、同名设备未合并、工具列出现 other、模型饼图被工具维度污染的四个问题
---

# Token Usage 饼图修复设计

## 背景

`http://localhost:5178/tools/token-usage` 页面顶部展示四个饼图：

1. 设备 Token 占比
2. 工具 Token 占比
3. 模型 Token 占比
4. 模型成本占比

当前出现以下四个问题：

1. **设备饼图标签未跟随重命名**：用户在「设备管理」中重命名设备后，饼图仍显示旧名称
2. **同名设备数据未合并**：两个不同 `device_id` 但显示名相同的设备各自占一片，没有合并
3. **工具维度出现 `other` 项**：用户的 ccusage 输出里每个 Agent 都有自己的名字，理论上不应再出现 `other`
4. **模型 Token / 模型成本饼图被工具维度污染**：同一个模型在不同工具下被拆成多个切片

## 根因定位

| # | 现象 | 根因（文件:行） |
|---|------|---|
| 1 | 设备名对不上 | `backend/app/routes/token_usage.py:1503` `_normalize_record_dimensions` 优先使用记录里冗余的 `TokenUsageRecord.device_name` 字段；该字段在同步时被写死，重命名 `DeviceRegistry.display_name` 不会回写 |
| 2 | 同名设备未合并 | `backend/app/routes/token_usage.py:1648` 设备桶 key 是 `device_id`（UUID），不同 UUID 即使重命名为同一个名字也分桶 |
| 3 | 出现 `other` | `backend/app/services/token_usage_sync_service.py:618、653、671` `_infer_agent` 将无法归属的模型硬编码为 `"other"`，并通过 `AGENT_DISPLAY_NAMES["other"] = "Other"` 持久化进数据库 |
| 4 | 模型饼图含工具维度 | `backend/app/routes/token_usage.py:1649` 模型桶 key 是 `f"{tool_id}:{model}"`；前端 `modelCostSlices` 直接用按 `(source, model)` 聚合的 `model_summary` |

## 设计方案

### 1. 后端 `_normalize_record_dimensions` — 设备名权威来源改为 `device_names` map

**文件：** `backend/app/routes/token_usage.py`

`_load_device_names` 已经加载了最新 `DeviceRegistry.display_name` 并合并了 alias，应作为唯一权威来源。`TokenUsageRecord.device_name` 字段是同步时刻的快照，仅作为记录元数据保留，不再用于展示。

```python
def _normalize_record_dimensions(row, device_names: dict[str, str]) -> dict:
    ...
    device_id = getattr(row, "device_id", None) or "unknown"
    # 改动：不再优先用 row.device_name；统一从 device_names map 取
    device_name = device_names.get(device_id) or device_id
    ...
```

### 2. 后端 `_build_dimension_data` — 设备维度按 display_name 合并

**文件：** `backend/app/routes/token_usage.py:1640`

设备桶分桶 key 从 `device_id` 改为 `device_name`，使两个不同 device_id 但显示名相同的设备汇总成一个切片。

```python
device_key = dims["device_name"]   # 改为按显示名合并
device_bucket = device_buckets.setdefault(
    device_key,
    {
        "dimension": "device",
        "key": dims["device_id"],         # 切片选中传给后端的 id（任一 canonical id）
        "label": dims["device_name"],
        "device_id": dims["device_id"],
        ...
    }
)
```

`filter_options.devices` 同步使用 `label` 作为 device 区分键，避免重复条目。

### 3. 后端 `_build_record_filters` — 设备筛选支持同名集合

**文件：** `backend/app/routes/token_usage.py:1996`

由于设备饼图按显示名合并，用户点击切片时传入的 `device_id` 仅是该名称下任一 canonical id。筛选时需找出所有同显示名的 device_id 一并查询。

```python
def _build_record_filters(user_id, req, since_date=None, alias_map=None):
    ...
    if getattr(req, "device_id", None):
        # 改动：先反查同显示名的所有 device_id 集合
        same_name_ids = _resolve_same_display_name_ids(
            user_id, req.device_id, alias_map  # 需新增辅助函数
        )
        if same_name_ids:
            filters.append(TokenUsageRecord.device_id.in_(same_name_ids))
        elif alias_map:
            filters.extend(build_alias_aware_device_filter(req.device_id, alias_map))
        else:
            filters.append(TokenUsageRecord.device_id == req.device_id)
    ...
```

新增辅助函数 `_resolve_same_display_name_ids(db, user_id, device_id, alias_map)`：
1. 用 `device_id` 反查 `DeviceRegistry` 拿到 `display_name`
2. 找出所有 `display_name` 相同的 `device_id` 集合
3. 把集合中的 alias 也加进去
4. 返回完整 device_id 列表

由于该函数需要 db 会话，将其参数签名为 `(db, user_id, device_id, alias_map)`，`_build_record_filters` 改为接收一个可选的 `device_id_resolver` 回调；在四个调用点（`/summary`、`/details`、`/query`、`db_query_token_usage`）注入闭包以避免循环依赖。

### 4. 后端 `_infer_agent` — 移除 `other` 兜底，改为合理回退或抛错

**文件：** `backend/app/services/token_usage_sync_service.py:596`

ccusage 在每个 Agent 的 `daily --json` 中都返回 `modelsUsed`。如果某个模型确实不在任何 agent 的 `modelsUsed` 中，说明数据反常，不应静默归 `other`。

```python
def _infer_agent(model_name, date_str, agent_models_dict) -> str:
    day_agents = agent_models_dict.get(date_str, {})
    candidates = [agent for agent, models in day_agents.items() if model_name in models]
    if not candidates:
        # 当日只有 1 个 agent → 唯一推断
        if len(day_agents) == 1:
            return next(iter(day_agents.keys()))
        # 否则抛错让上层 skip 该条记录
        raise ValueError(
            f"模型 {model_name}（{date_str}）未在任何 agent 的 modelsUsed 中"
        )
    for priority_agent in AGENT_PRIORITY:
        if priority_agent in candidates:
            return priority_agent
    return candidates[0]
```

**`_parse_ccusage_records` 配套修改：**

```python
try:
    agent = _infer_agent(model_name, period, agent_models_dict)
except ValueError as exc:
    logger.warning(f"[ccusage] 跳过无法归属的记录: {exc}")
    continue   # 不再写入 'other'
```

**清理 `AGENT_DISPLAY_NAMES` / `AGENT_PRIORITY`** 中的 `"other"` 项。

### 5. 一次性清理脚本 — 删除历史 `source='other'` 数据

**文件：** `backend/scripts/cleanup_other_token_usage.py`（新建）

```python
"""
Author: Peanut
Created: 2026-06-19
Purpose: 一次性清理 token_usage_records / token_usage_sync_log 中
         历史遗留的 source='other' 记录。仅手动执行一次。
"""
from app.models.base import SessionLocal
from app.models.token_usage_models import TokenUsageRecord, TokenUsageSyncLog

def main():
    db = SessionLocal()
    try:
        records_deleted = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.source == 'other')
            .delete(synchronize_session=False)
        )
        logs_deleted = (
            db.query(TokenUsageSyncLog)
            .filter(TokenUsageSyncLog.source == 'other')
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"已删除 {records_deleted} 条 records, {logs_deleted} 条 sync_log")
    finally:
        db.close()

if __name__ == "__main__":
    main()
```

执行方式：`python -m backend.scripts.cleanup_other_token_usage`（仅手动执行一次）。

### 6. 后端 `_build_dimension_data` — 模型维度按纯 model 分组

**文件：** `backend/app/routes/token_usage.py:1699-1728`

模型桶 key 改为只用 `dims["model"]`，并去除 `tool_id` / `source` 维度绑定：

```python
model_key = dims["model"]
model_bucket = model_buckets.setdefault(
    model_key,
    {
        "dimension": "model",
        "key": model_key,
        "label": dims["model"],   # 不再带工具前缀
        "device_id": None,
        "tool_id": None,
        "source": None,
        "model": dims["model"],
        ...
    }
)
_rollup_dimension(
    model_bucket, row,
    {"label": dims["model"], "tool_id": None, "source": None, "model": dims["model"]},
)
```

### 7. 前端 `modelCostSlices` — 按 model 二次合并

**文件：** `frontend/src/components/Tools/TokenUsage.tsx:493-501`

后端 `model_summary` 仍按 `(source, model)` 返回（保留 source 信息供其他用途）；饼图层在前端再做一次 reduce 去掉 source 维度：

```typescript
const modelCostSlices: PieSlice[] = useMemo(() => {
  const map = new Map<string, { tokens: number; cost: number }>();
  summary.data.model_summary.forEach(item => {
    const cur = map.get(item.model) || { tokens: 0, cost: 0 };
    map.set(item.model, {
      tokens: cur.tokens + item.total_tokens,
      cost: cur.cost + item.total_cost,
    });
  });
  return Array.from(map.entries()).map(([model, v]) => ({
    key: model,
    label: model,            // 纯模型名，不再带 "Claude · " 等前缀
    tokens: v.tokens,
    cost: v.cost,
  }));
}, [summary.data.model_summary]);
```

## 联动与影响

- **缓存**：所有维度计算都在 `/summary`、`/query` 实时查询，不走 Redis 聚合缓存。改动后无需主动清缓存
- **筛选交互**：设备饼图选中后，列表查询会自动包含同名设备的所有记录
- **数据库 schema 不变**：仅修改聚合逻辑，无 alembic 迁移
- **设备同名筛选退路**：`_resolve_same_display_name_ids` 在 `DeviceRegistry` 表为空时退化为单 `device_id` 过滤（保持兼容）

## 验收标准

1. 在「设备管理」中重命名当前设备后，刷新页面，设备饼图标签变为新名称
2. 手动把两个不同 `device_id` 命名为同一名字，设备饼图只显示一个切片，数值是两者之和
3. 拉一遍 `/refresh-ccusage` 后，工具饼图中不再出现 `Other` 切片；后端日志中如有跳过记录会有 WARNING
4. 模型 Token 占比 / 模型成本占比饼图中，相同模型名只显示一个切片，不再出现 `Claude · model-x` / `OpenCode · model-x` 这类同模型双切片
5. 浏览器 Console 无报错；页面整体功能正常

## 实施顺序

1. 后端：`_normalize_record_dimensions` 改设备名优先级
2. 后端：`_build_dimension_data` 设备桶按 name 合并 + 模型桶去掉 tool 维度
3. 后端：`_build_record_filters` 同名设备 IN 查询，新增 `_resolve_same_display_name_ids`
4. 后端：`_infer_agent` / `_parse_ccusage_records` 移除 `other` 兜底；清理 `AGENT_DISPLAY_NAMES` / `AGENT_PRIORITY`
5. 后端：新增 `backend/scripts/cleanup_other_token_usage.py`，手动跑一次
6. 前端：`modelCostSlices` 改为按 model 二次合并
7. `python dev_services.py restart backend`，前端走热更新
8. 浏览器登录 `peanut/Peanut2817*#`，进入 `/tools/token-usage`，验证四个饼图全部符合验收标准
