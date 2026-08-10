---
purpose: 修复 /details 端点因 Redis 脏缓存（total=0）导致明细无法显示——之前 DB 连接池爆期间空结果被错误写入缓存，现 cache 命中后端持续返回 0 条。
date: 2026-08-10
---

# Token Usage 明细脏缓存修复设计

## 背景

本机 token-usage 页面 summary 有1129 亿 token 数据但 details 明细显示 0 条。根因是 Redis 缓存中有一个 `(days=30, group_by=none, source=all, sort_by=date, sort_order=desc)` 的脏缓存 `total=0`，是之前 postgres 连接池爆、DB 查询失败/返回空时写入的。`/details` 端点在 `offset=0` 且无 device/tool/model 筛选时走缓存命中分支，直接返回 `total=0`。

## 方案

代码层：让 `set_query_cached_data` 跳过空结果（`summary.total_tokens == 0` 且 `total == 0` 且 items 空 → 不写），避免后续相同条件再次被空结果污染。
运营层：立即清掉 Redis 中 `token_usage:query:*` 键，释放当前脏缓存。

## 改动

### A. `backend/app/services/token_usage_cache.py` `set_query_cached_data`

在 `payload.setdefault("cache_written_at", ...)` 之前增加空结果跳过：

```python
        payload = dict(data or {})
        # 避免空结果污染缓存（之前 DB 失败时被错误写入 total=0，命中后端持续返回 0）
        summary_tokens = 0
        if isinstance(payload.get("summary"), dict):
            summary_tokens = payload.get("summary", {}).get("total_tokens", 0)
        total = payload.get("total", 0)
        items = payload.get("items", [])
        if (summary_tokens == 0) and (total == 0) and (not items):
            logger.info(f"查询缓存跳过(空结果): {key}")
            return False
        payload.setdefault("cache_written_at", datetime.now().isoformat())
        ...
```

### B. 运营：清 Redis 脏缓存

本地后端 venv 内执行：

```bash
backend/.venv/Scripts/python.exe - <<'PY'
import sys; sys.path.insert(0, "backend")
from app.services.token_usage_cache import get_redis_client
client = get_redis_client()
keys = client.keys("token_usage:query:*") if client else []
if keys:
    n = client.delete(*keys)
    print(f"删除 {n} 键")
else:
    print("(无匹配键)")
PY
```

## 不动

- 缓存键结构（保持向后兼容）
- `warm_query_cache` 预热逻辑
- 缓存读取分支（脏缓存清掉后即可恢复）
- 其他数据源 / 后台同步

## 验证

1. 后端自动 reload（`--reload` 已开）
2. 立即清缓存后 curl `details`：`total > 0`、`items` 非空、`cached=False`
3. 第二次相同请求应命中正常缓存（`cached=True`）
4. 浏览器 `http://localhost:5178/tools/token-usage` 明细表格有行

## 回滚

```bash
git checkout HEAD -- backend/app/services/token_usage_cache.py
```
（清掉的 Redis 键 TTL 过期后自动消失，无需反向恢复）