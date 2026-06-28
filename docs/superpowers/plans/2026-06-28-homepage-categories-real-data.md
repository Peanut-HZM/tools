# 首页工具分类真实性改造 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让首页工具分类严格以 admin 后台维护的真实分类为准，去除写死种子/翻译兜底，启动时清洗分类歧义并校验悬空引用。

**Architecture:** 后端在 `_init_db` 末尾增加"清洗 + 校验"独立事务；新增 `get_used_categories()` 替代 `get_all_categories()` 作为 `GET /categories` 的内部实现；admin 分类管理接口追加 `tool_count` 字段 + 删除 409 保护 + 改名可选级联；前端移除 `t.categories` 硬编码翻译映射，分类 tab 直接显示后台名称。

**Tech Stack:** Python 3.10 + FastAPI + SQLAlchemy (raw SQL via psycopg2) + pytest；React 18 + TypeScript + Vite + Tailwind + Zustand。

**Spec:** `docs/superpowers/specs/2026-06-28-homepage-categories-real-data-design.md`

---

## 文件清单

**后端新建**
- `backend/tests/test_tools_categories.py` — 清洗 / 校验 / `get_used_categories` / 删除保护 / 改名级联的测试

**后端修改**
- `backend/app/data/tools_data.py:46-236` — 把 `"AI 工具"` 全部改为 `"AI工具"`
- `backend/app/services/tools_service.py`
  - `_init_db`（约 98-122 行）— 在种子之后追加清洗 + 校验独立事务
  - 新增方法 `get_used_categories()`（接在 `get_all_categories` 之后）
  - 新增方法 `get_categories_with_tool_count()`（同上）
  - 新增方法 `_normalize_category_variants()` / `_validate_tool_category_refs()`（供 `_init_db` 调用）
  - `update_tool_status`（257-275）— 成功后 `invalidate` `used_categories` 与 `tools:*` 缓存
  - `update_tool`（311-371）— 成功后同上
  - `update_category`（643-677）— 增加可选 `cascade` 参数；成功后 `invalidate` `used_categories` + `categories`
  - `delete_category`（679-697）— 增加前置引用计数检查，命中则 `raise HTTPException(409)`
  - `create_category`（609-641）— 成功后 `invalidate` `used_categories` + `categories`
- `backend/app/routes/tools.py:9-12` — `GET /categories` 改调 `get_used_categories()`
- `backend/app/routes/admin.py` — 找到分类相关路由（在 `tools_service` 调用处）：
  - `GET /admin/categories`（或 admin 内分类列表路由）— 改调 `get_categories_with_tool_count()`
  - `PUT /admin/categories/{id}` — 增加 `cascade` query 参数
  - `DELETE /admin/categories/{id}` — 捕获 409 并返回

**前端修改**
- `frontend/src/i18n/locales/zh-CN.ts:83-93` — 删除 `categories: { ... }` 字段
- `frontend/src/i18n/locales/en-US.ts:82-92` — 删除 `categories: { ... }` 字段
- `frontend/src/components/Hero/CategoryTabs.tsx:14-26` — 渲染改为直接显示 `{category}`
- `frontend/src/App.tsx:100-140` — `loadCategories` 失败时 `setError(...)` 而非 fallback
- `frontend/src/api/adminApi.ts:16-60` — `ToolCategory` 增加 `tool_count?: number`；`updateCategory` 增加 `cascade` 参数

---

## Task 1: 修正种子数据 `tools_data.py` 的 `"AI 工具"` → `"AI工具"`

**Files:**
- Modify: `backend/app/data/tools_data.py`（5 处左右）

- [ ] **Step 1: 全局替换空格变体**

打开 `backend/app/data/tools_data.py`，把所有 `category="AI 工具"`（带空格）改为 `category="AI工具"`（不带空格）。

预期命中位置（按当前源码）：
- 行 53（ai-assistant）
- 行 93（ocr-tool）
- 行 103（asr-tool）
- 行 143（product-manager）
- 行 234（openclaw）

- [ ] **Step 2: 静态校验**

Run:
```bash
cd backend && python -c "from app.data.tools_data import TOOLS_DATA; cats = set(t.category for t in TOOLS_DATA); print(sorted(cats))"
```

Expected: 列表里**不应**出现 `"AI 工具"`（带空格）；应该出现 `"AI工具"`（不带空格）。

- [ ] **Step 3: Commit**

```bash
git add backend/app/data/tools_data.py
git commit -m "fix：统一 TOOLS_DATA 中 AI 类工具的分类名为「AI工具」（去除空格变体）"
```

---

## Task 2: 在 `_init_db` 增加启动清洗 + 校验

**Files:**
- Modify: `backend/app/services/tools_service.py`
- Test: `backend/tests/test_tools_categories.py`（本任务先写失败测试，Task 3 实现方法后再让其通过）

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_tools_categories.py`：

```python
"""
Tests for tools_service category dedup / validation / get_used_categories.

注意：这些测试是逻辑级单元测试，通过 mock psycopg2 连接来隔离业务逻辑。
"""
from unittest.mock import MagicMock, patch
import pytest


class FakeCursor:
    """模拟 psycopg2 DictCursor，记录所有 execute 调用"""
    def __init__(self):
        self.calls = []  # list of (sql, params)
        self.next_results = []  # queue of result sets to return
        self._rowcount = 0

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        # 返回队列中的下一个结果集
        if self.next_results:
            self._result = self.next_results.pop(0)
        else:
            self._result = []

    def fetchall(self):
        return self._result

    def fetchone(self):
        return self._result[0] if self._result else None

    @property
    def rowcount(self):
        return self._rowcount

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class TestNormalizeCategoryVariants:
    """测试 _normalize_category_variants 合并空格变体的逻辑"""

    def test_merge_space_variant(self):
        """存在「AI工具」和「AI 工具」两条，应合并到 sort_order 较小的"""
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        # 第一次 fetchall：返回两条分类
        fake_cursor.next_results = [
            [  # SELECT id, name, sort_order FROM tool_categories
                {"id": "c1", "name": "AI工具", "sort_order": 1},
                {"id": "c2", "name": "AI 工具", "sort_order": 5},
            ],
            [],  # UPDATE tools 之后
            [],  # DELETE FROM tool_categories 之后
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            tools_service._normalize_category_variants(fake_conn)

        # 应该执行一次 UPDATE tools SET category=规范名
        update_calls = [c for c in fake_cursor.calls if c[0].startswith("UPDATE tools SET category")]
        assert len(update_calls) == 1
        sql, params = update_calls[0]
        assert params[0] == "AI工具"  # 规范名
        assert set(params[1]) == {"AI 工具"}  # 被合并的变体

        # 应该执行一次 DELETE 删除多余分类
        delete_calls = [c for c in fake_cursor.calls if c[0].startswith("DELETE FROM tool_categories")]
        assert len(delete_calls) == 1
        _, params = delete_calls[0]
        assert params[0] == ["c2"]

    def test_no_variants_noop(self):
        """库里已一致时，不执行任何写操作"""
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [  # 只有两条，规范名各不相同（去空格后不重复）
                {"id": "c1", "name": "AI工具", "sort_order": 1},
                {"id": "c3", "name": "实用工具", "sort_order": 2},
            ],
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            tools_service._normalize_category_variants(fake_conn)

        # 不应该执行 UPDATE / DELETE
        write_calls = [c for c in fake_cursor.calls
                       if c[0].startswith("UPDATE tools SET category")
                       or c[0].startswith("DELETE FROM tool_categories")]
        assert write_calls == []


class TestValidateToolCategoryRefs:
    """测试 _validate_tool_category_refs 悬空引用校验"""

    def test_logs_error_for_dangling(self, caplog):
        """存在悬空引用时应记 ERROR 日志"""
        import logging
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [{"category": "未分类X"}, {"category": "未分类Y"}],
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"), \
             caplog.at_level(logging.ERROR, logger="app.services.tools_service"):
            tools_service._validate_tool_category_refs(fake_conn)

        assert any("未分类X" in r.message and "不存在的分类" in r.message for r in caplog.records)
        assert any("未分类Y" in r.message for r in caplog.records)

    def test_no_dangling_no_error(self, caplog):
        """无悬空引用时不应记 ERROR"""
        import logging
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [[]]  # 空结果

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"), \
             caplog.at_level(logging.ERROR, logger="app.services.tools_service"):
            tools_service._validate_tool_category_refs(fake_conn)

        assert not any("不存在的分类" in r.message for r in caplog.records)
```

- [ ] **Step 2: 跑测试确认失败**

Run:
```bash
cd backend && python -m pytest tests/test_tools_categories.py -v
```

Expected: FAIL —— `tools_service` 还没有 `_normalize_category_variants` 和 `_validate_tool_category_refs` 方法（`AttributeError`）。

- [ ] **Step 3: 在 `tools_service.py` 实现两个私有方法**

在 `ToolsService` 类内（建议接在 `get_all_categories` 方法之后，`create_category` 之前）追加：

```python
def _normalize_category_variants(self, conn) -> None:
    """合并 tool_categories 中的空格变体（在传入的 conn 事务内执行）

    幂等：库里已一致时不执行任何写操作。
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, sort_order FROM tool_categories")
            all_cats = cur.fetchall()

            groups: Dict[str, List[dict]] = {}
            for row in all_cats:
                key = row["name"].replace(" ", "")
                groups.setdefault(key, []).append(dict(row))

            merged_info = []
            for _key, members in groups.items():
                if len(members) <= 1:
                    continue
                members.sort(key=lambda r: r["sort_order"])
                canonical_name = members[0]["name"]
                drop_names = [m["name"] for m in members[1:]]
                drop_ids = [m["id"] for m in members[1:]]
                if drop_names:
                    cur.execute(
                        "UPDATE tools SET category = %s WHERE category = ANY(%s)",
                        (canonical_name, drop_names),
                    )
                    affected = cur.rowcount
                    cur.execute(
                        "DELETE FROM tool_categories WHERE id = ANY(%s)",
                        (drop_ids,),
                    )
                    merged_info.append({
                        "canonical": canonical_name,
                        "dropped": drop_names,
                        "affected_tools": affected,
                    })
            if merged_info:
                logger.info("启动清洗：合并分类变体 %s", merged_info)
            else:
                logger.info("启动清洗：无需合并的分类变体")
    except Exception as e:
        logger.error("启动清洗失败（不阻止启动）: %s", e)

def _validate_tool_category_refs(self, conn) -> None:
    """校验 tools.category 是否都有 tool_categories 记录；悬空引用记 ERROR 日志。

    不抛异常、不写默认值、不改数据（遵守「没有就是没有」规则）。
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT t.category
                FROM tools t
                WHERE t.category IS NOT NULL
                  AND t.category NOT IN (SELECT name FROM tool_categories)
            """)
            dangling = [row["category"] for row in cur.fetchall()]
            if dangling:
                for cat in dangling:
                    logger.error("启动校验：工具引用了不存在的分类: category=%s", cat)
            else:
                logger.info("启动校验通过：所有 tools.category 均有对应 tool_categories 记录")
    except Exception as e:
        logger.error("启动校验失败（不阻止启动）: %s", e)
```

- [ ] **Step 4: 跑测试确认通过**

Run:
```bash
cd backend && python -m pytest tests/test_tools_categories.py::TestNormalizeCategoryVariants -v
cd backend && python -m pytest tests/test_tools_categories.py::TestValidateToolCategoryRefs -v
```

Expected: 4 个测试全部 PASS。

- [ ] **Step 5: 在 `_init_db` 末尾接入清洗 + 校验**

在 `backend/app/services/tools_service.py` 的 `_init_db` 方法里，找到 `conn.commit()` 之前的位置，在"种子工具"循环结束后、`conn.commit()` 之前，插入：

```python
                # --- 分类清洗 + 校验（独立事务语义，失败仅记日志） ---
                self._normalize_category_variants(conn)
                self._validate_tool_category_refs(conn)
```

注意：这两步复用 `_init_db` 的同一个 `conn` 与 `cur` 上下文，放在 `conn.commit()` 之前、最后一次 `cur.execute` 之后。失败时由现有 `_init_db` 外层 `try/except` 捕获 → 整个 `_init_db` 回滚。

**如果希望"清洗失败不影响建表与种子"**，可以把清洗 + 校验包到独立事务里（独立 conn）：

```python
                # 提交核心建表 + 种子
                conn.commit()
            finally:
                if conn:
                    release_db_connection(conn)

        # --- 独立事务：分类清洗 + 校验 ---
        wash_conn = None
        try:
            wash_conn = get_pooled_db_connection()
            self._normalize_category_variants(wash_conn)
            self._validate_tool_category_refs(wash_conn)
            wash_conn.commit()
        except Exception as e:
            logger.error("分类清洗/校验事务失败（不阻止启动）: %s", e)
            if wash_conn:
                wash_conn.rollback()
        finally:
            if wash_conn:
                release_db_connection(wash_conn)
```

推荐采用"独立事务"写法，避免清洗失败导致整个 `_init_db` 回滚。

- [ ] **Step 6: 启动后端，观察日志**

Run:
```bash
python dev_services.py restart backend
```

Expected：
- 首次启动日志出现 `启动清洗：合并分类变体 {...}` 一行（或 `无需合并`，取决于库里现状）
- 随后出现 `启动校验通过：...`（或 `悬空引用` 警告）
- 服务正常启动、端口 19092 可用

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/tools_service.py backend/tests/test_tools_categories.py
git commit -m "feat：tools_service 启动时清洗分类变体 + 校验悬空引用"
```

---

## Task 3: 新增 `get_used_categories()` + 缓存失效

**Files:**
- Modify: `backend/app/services/tools_service.py`
- Modify: `backend/app/routes/tools.py:9-12`
- Test: `backend/tests/test_tools_categories.py`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_tools_categories.py` 末尾追加：

```python
class TestGetUsedCategories:
    """测试 get_used_categories 只返回被在线工具引用的分类"""

    def test_only_used_categories_returned(self):
        from app.services.tools_service import tools_service
        from app.models import Category

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [  # SELECT DISTINCT c.* FROM tool_categories c JOIN tools t ...
                {"id": "c1", "name": "AI工具", "description": None,
                 "icon": None, "sort_order": 1,
                 "created_at": None, "updated_at": None},
                {"id": "c2", "name": "实用工具", "description": None,
                 "icon": None, "sort_order": 2,
                 "created_at": None, "updated_at": None},
            ],
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"), \
             patch.object(tools_service, "_row_to_category", side_effect=lambda r: Category(**r)):
            # 绕过缓存
            from app.services.tools_service import _tools_cache
            _tools_cache.invalidate("used_categories")

            result = tools_service.get_used_categories()

        assert [c.name for c in result] == ["AI工具", "实用工具"]
        # SQL 必须 JOIN tools 且过滤 status='online'
        sql = fake_cursor.calls[0][0]
        assert "JOIN tools" in sql
        assert "t.status = 'online'" in sql

    def test_empty_when_no_tools(self):
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [[]]  # 没有工具 → 没有分类

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            from app.services.tools_service import _tools_cache
            _tools_cache.invalidate("used_categories")
            result = tools_service.get_used_categories()

        assert result == []
```

- [ ] **Step 2: 跑测试确认失败**

Run:
```bash
cd backend && python -m pytest tests/test_tools_categories.py::TestGetUsedCategories -v
```

Expected: FAIL —— `tools_service` 没有 `get_used_categories` 方法。

- [ ] **Step 3: 实现 `get_used_categories` 与辅助方法 `_row_to_category`**

在 `ToolsService` 类内（接在 `get_all_categories` 之后）追加：

```python
def get_used_categories(self) -> List[Category]:
    """只返回被至少一个在线工具引用的分类，按 sort_order 排序。

    用作前台 GET /categories 的数据源。
    """
    cache_key = "used_categories"
    cached = _tools_cache.get(cache_key)
    if cached is not None:
        return cached

    conn = None
    try:
        conn = get_pooled_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT c.*
                FROM tool_categories c
                JOIN tools t ON t.category = c.name
                WHERE t.status = 'online'
                ORDER BY c.sort_order ASC, c.name ASC
            """)
            rows = cur.fetchall()
            result = [self._row_to_category(row) for row in rows]
        _tools_cache.set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Error fetching used categories: {e}")
        return []
    finally:
        if conn:
            release_db_connection(conn)

def _row_to_category(self, row) -> Category:
    """将 DB row 转换为 Category 模型，处理 datetime 序列化"""
    cat_data = dict(row)
    if isinstance(cat_data.get("created_at"), datetime):
        cat_data["created_at"] = cat_data["created_at"].isoformat()
    if isinstance(cat_data.get("updated_at"), datetime):
        cat_data["updated_at"] = cat_data["updated_at"].isoformat()
    return Category(**cat_data)
```

- [ ] **Step 4: 在 `tools.py` 把 `GET /categories` 改调 `get_used_categories()`**

修改 `backend/app/routes/tools.py` 第 9-12 行：

```python
@router.get("/categories", response_model=List[Category])
def get_categories():
    """获取所有被在线工具使用的分类（前台首页用）"""
    return tools_service.get_used_categories()
```

- [ ] **Step 5: 在 `update_tool_status` / `update_tool` 追加缓存失效**

在 `tools_service.py` 的 `update_tool_status` 方法里，`conn.commit()` 成功返回之前，追加：

```python
                conn.commit()
                success = cur.rowcount > 0
                if success:
                    _tools_cache.invalidate("used_categories")
                    # 工具状态改变可能影响"全部工具"与任意分类的列表缓存
                    for key in list(_tools_cache._data.keys()):
                        if key.startswith("tools:"):
                            _tools_cache.invalidate(key)
                return success
```

> 说明：`SimpleTTLCache` 如果没有暴露 `_data`，改为失效已知 key：
> ```python
> _tools_cache.invalidate("used_categories")
> _tools_cache.invalidate("tools:pc:all")
> _tools_cache.invalidate("tools:mobile:all")
> ```

同样在 `update_tool` 方法的 `conn.commit()` 后追加同样的失效逻辑。

**确认 `SimpleTTLCache` API**：先执行
```bash
cd backend && grep -n "def \|class " app/services/simple_cache.py
```
按实际 API 调用失效方法。

- [ ] **Step 6: 在 `create_category` / `update_category` / `delete_category` 追加缓存失效**

三个方法分别在 `conn.commit()` 后追加：

```python
                _tools_cache.invalidate("used_categories")
                _tools_cache.invalidate("categories")
```

- [ ] **Step 7: 跑全部新测试**

Run:
```bash
cd backend && python -m pytest tests/test_tools_categories.py -v
```

Expected: 所有测试 PASS。

- [ ] **Step 8: 重启后端，浏览器验证**

```bash
python dev_services.py restart backend
```

用浏览器（或 Playwright MCP）打开 `http://localhost:5178`：

- 顶部"全部工具" tab 仍在
- 后续 tab 列表严格等于 admin 里**被至少一个在线工具使用**的分类
- 点击每个 tab，下面的工具数量 ≥ 1

再打开浏览器 DevTools → Network → 看 `GET /categories` 响应：

- 响应里的每个 name 都能在 admin「工具管理 → 分类管理」找到
- 响应里**不**包含 admin 里"使用计数 = 0"的分类

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/tools_service.py backend/app/routes/tools.py backend/tests/test_tools_categories.py
git commit -m "feat：GET /categories 改为只返回被在线工具使用的分类 + 缓存失效"
```

---

## Task 4: admin 分类管理增强（使用计数 + 删除 409 + 改名级联）

**Files:**
- Modify: `backend/app/services/tools_service.py`
- Modify: `backend/app/routes/admin.py`（或分类路由所在文件）
- Modify: `frontend/src/api/adminApi.ts`
- Modify: `frontend/src/components/Admin/ToolManagement.tsx`
- Test: `backend/tests/test_tools_categories.py`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_tools_categories.py` 末尾追加：

```python
class TestDeleteCategoryProtection:
    """测试 delete_category 的 409 保护"""

    def test_delete_category_with_tools_raises_409(self):
        """分类下仍有工具时，应抛出 409，不删除"""
        from fastapi import HTTPException
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        # 第一次 fetchone：计数 = 3
        fake_cursor.next_results = [[{"count": 3}]]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            with pytest.raises(HTTPException) as exc_info:
                tools_service.delete_category("some-id")
            assert exc_info.value.status_code == 409

        # 不应执行 UPDATE deleted = TRUE
        write_calls = [c for c in fake_cursor.calls
                       if c[0].startswith("UPDATE tool_categories SET deleted")]
        assert write_calls == []

    def test_delete_category_without_tools_succeeds(self):
        """分类下无工具时，应正常软删除并失效缓存"""
        from app.services.tools_service import tools_service, _tools_cache

        fake_cursor = FakeCursor()
        # 计数 = 0 → 软删除 rowcount = 1
        fake_cursor.next_results = [
            [{"count": 0}],
            [],  # UPDATE deleted = TRUE
        ]
        fake_cursor._rowcount = 1

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"), \
             patch.object(_tools_cache, "invalidate") as mock_inv:
            result = tools_service.delete_category("some-id")

        assert result is True
        mock_inv.assert_any_call("used_categories")
        mock_inv.assert_any_call("categories")
```

- [ ] **Step 2: 实现 `delete_category` 的 409 保护**

改写 `tools_service.py` 里的 `delete_category`：

```python
def delete_category(self, cat_id: str) -> bool:
    """软删除分类。若分类下仍有工具，抛 HTTPException(409)"""
    conn = None
    try:
        conn = get_pooled_db_connection()
        with conn.cursor() as cur:
            # 先查分类名
            cur.execute("SELECT name FROM tool_categories WHERE id = %s AND deleted = FALSE", (cat_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Category not found")
            cat_name = row["name"]

            # 检查引用计数
            cur.execute("SELECT COUNT(*) AS count FROM tools WHERE category = %s", (cat_name,))
            cnt = cur.fetchone()["count"]
            if cnt > 0:
                raise HTTPException(
                    status_code=409,
                    detail=f"该分类下仍有 {cnt} 个工具，请先迁移后再删除",
                )

            cur.execute(
                "UPDATE tool_categories SET deleted = TRUE WHERE id = %s", (cat_id,)
            )
            conn.commit()
            success = cur.rowcount > 0
            if success:
                _tools_cache.invalidate("used_categories")
                _tools_cache.invalidate("categories")
            return success
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(f"Error deleting category {cat_id}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            release_db_connection(conn)
```

注意：文件顶部已有 `from fastapi import HTTPException`；若没有，在 `tools_service.py` 顶部追加：

```python
from fastapi import HTTPException
```

- [ ] **Step 3: 跑测试确认通过**

Run:
```bash
cd backend && python -m pytest tests/test_tools_categories.py::TestDeleteCategoryProtection -v
```

Expected: 2 个测试 PASS。

- [ ] **Step 4: 实现 `get_categories_with_tool_count()`**

在 `ToolsService` 类追加：

```python
def get_categories_with_tool_count(self) -> List[Dict]:
    """admin 用：返回所有未删除分类，每个带 tool_count（在线工具数）"""
    conn = None
    try:
        conn = get_pooled_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.*, COUNT(t.id) AS tool_count
                FROM tool_categories c
                LEFT JOIN tools t ON t.category = c.name AND t.status = 'online'
                WHERE c.deleted = FALSE
                GROUP BY c.id
                ORDER BY c.sort_order ASC, c.name ASC
            """)
            rows = cur.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                if isinstance(d.get("created_at"), datetime):
                    d["created_at"] = d["created_at"].isoformat()
                if isinstance(d.get("updated_at"), datetime):
                    d["updated_at"] = d["updated_at"].isoformat()
                result.append(d)
            return result
    except Exception as e:
        logger.error(f"Error fetching categories with tool count: {e}")
        return []
    finally:
        if conn:
            release_db_connection(conn)
```

- [ ] **Step 5: 改 admin 路由的"分类列表"**

先确认 admin 分类路由位置：
```bash
grep -n "categories\|listCategories" backend/app/routes/admin.py backend/app/routes/tools.py
```

把 admin 里"分类列表"端点（若它调用 `get_all_categories`）改为调用 `get_categories_with_tool_count()`；返回模型需能容纳 `tool_count` 字段（可直接返回 `List[dict]`）。

- [ ] **Step 6: admin 改名支持可选级联**

修改 `tools_service.py` 里的 `update_category`，增加 `cascade` 参数：

```python
def update_category(
    self, cat_id: str, request: CategoryCreateRequest, cascade: bool = False
) -> Optional[Category]:
    conn = None
    try:
        conn = get_pooled_db_connection()
        with conn.cursor() as cur:
            # 查旧名字
            cur.execute(
                "SELECT name FROM tool_categories WHERE id = %s AND deleted = FALSE",
                (cat_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Category not found")
            old_name = row["name"]
            new_name = request.name

            # 若改名且该分类下有工具：必须 cascade=True，否则拒绝
            if old_name != new_name:
                cur.execute(
                    "SELECT COUNT(*) AS count FROM tools WHERE category = %s",
                    (old_name,),
                )
                cnt = cur.fetchone()["count"]
                if cnt > 0 and not cascade:
                    raise HTTPException(
                        status_code=409,
                        detail=f"该分类下有 {cnt} 个工具，请确认是否级联更新",
                    )
                if cnt > 0 and cascade:
                    cur.execute(
                        "UPDATE tools SET category = %s WHERE category = %s",
                        (new_name, old_name),
                    )

            cur.execute(
                """
                UPDATE tool_categories
                SET name = %s, description = %s, icon = %s, sort_order = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND deleted = FALSE
                RETURNING *
                """,
                (new_name, request.description, request.icon, request.sort_order, cat_id),
            )
            row = cur.fetchone()
            conn.commit()
            if row:
                _tools_cache.invalidate("used_categories")
                _tools_cache.invalidate("categories")
                return Category(**self._row_to_category_dict(row))
            return None
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(f"Error updating category {cat_id}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            release_db_connection(conn)
```

如果 `_row_to_category` 已经返回 `Category` 实例，可直接：
```python
return self._row_to_category(row)
```

按现有代码选择合适写法。

- [ ] **Step 7: 改 admin 路由的"改名"端点**

在 admin 路由里为 `PUT /admin/categories/{id}`（或等价端点）追加 query 参数 `cascade: bool = False`，透传给 `tools_service.update_category(..., cascade=cascade)`。

捕获 `HTTPException` 让 FastAPI 自动返回 409。

- [ ] **Step 8: 前端 `adminApi.ts` 适配**

修改 `frontend/src/api/adminApi.ts`：

```typescript
export interface ToolCategory {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  sort_order: number;
  tool_count?: number;  // 新增
  created_at?: string;
  updated_at?: string;
}

export async function updateCategory(
  id: string,
  data: Partial<ToolCategory>,
  cascade: boolean = false,
): Promise<ToolCategory> {
  const url = `${API_BASE_URL}/admin/categories/${id}?cascade=${cascade}`;
  const response = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errText = await response.text();
    throw new Error(errText || `Failed to update category (${response.status})`);
  }
  return response.json();
}
```

（`authHeaders`、`API_BASE_URL` 按现有文件里的写法使用，不强行复制。）

- [ ] **Step 9: 前端 `ToolManagement.tsx` 增加使用计数 + 级联确认**

在分类管理列表里追加"使用计数"列（`{cat.tool_count ?? 0}`，0 时灰色标"未使用"）。

改写分类改名的提交逻辑：

```tsx
const handleSaveCategory = async () => {
  try {
    await updateCategory(categoryForm.id!, categoryForm, false);
    success("分类已更新");
    fetchData();
  } catch (e: any) {
    if (e.message.includes("409") || /该分类下有/.test(e.message)) {
      const confirmed = window.confirm(
        "该分类下有工具正在使用，是否一并更新工具的 category 字段？"
      );
      if (confirmed) {
        try {
          await updateCategory(categoryForm.id!, categoryForm, true);
          success("分类已更新（工具的 category 已级联）");
          fetchData();
        } catch (e2) {
          error("更新失败：" + (e2 as Error).message);
        }
      }
    } else {
      error("更新失败：" + e.message);
    }
  }
};
```

改写分类删除的错误处理：

```tsx
const handleDeleteCategory = async (id: string) => {
  if (!window.confirm("确认删除该分类？")) return;
  try {
    await deleteCategory(id);
    success("分类已删除");
    fetchData();
  } catch (e: any) {
    if (e.message.includes("409") || /仍有/.test(e.message)) {
      error("该分类下仍有工具，请先迁移后再删除");
    } else {
      error("删除失败：" + e.message);
    }
  }
};
```

- [ ] **Step 10: 浏览器验证 admin**

用浏览器打开 `http://localhost:5178/admin/tools`，切换到「分类管理」tab：

- 每行显示"使用计数"，0 的灰色标"未使用"
- 改一个被工具使用的分类名 → 弹级联确认框 → 确认 → 工具 category 字段跟随更新
- 改一个空分类名 → 直接保存
- 删一个被工具使用的分类 → toast 提示"该分类下仍有工具..."
- 删一个空分类 → 成功

- [ ] **Step 11: Commit**

```bash
git add backend/app/services/tools_service.py backend/app/routes/admin.py \
       frontend/src/api/adminApi.ts frontend/src/components/Admin/ToolManagement.tsx \
       backend/tests/test_tools_categories.py
git commit -m "feat：admin 分类管理增加使用计数 / 删除保护 / 改名级联"
```

---

## Task 5: 前端 — 移除 i18n 硬编码翻译 + 首页错误处理

**Files:**
- Modify: `frontend/src/i18n/locales/zh-CN.ts:83-93`
- Modify: `frontend/src/i18n/locales/en-US.ts:82-92`
- Modify: `frontend/src/components/Hero/CategoryTabs.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 删除 `zh-CN.ts` 的 `categories` 字段**

打开 `frontend/src/i18n/locales/zh-CN.ts`，删除第 83-93 行：

```typescript
  // Categories
  categories: {
    '全部工具': '全部工具',
    '文本工具': '文本工具',
    '转换工具': '转换工具',
    '计算工具': '计算工具',
    '设计工具': '设计工具',
    '实用工具': '实用工具',
    '开发工具': '开发工具',
    'AI 工具': 'AI 工具',
  },
```

- [ ] **Step 2: 删除 `en-US.ts` 的 `categories` 字段**

打开 `frontend/src/i18n/locales/en-US.ts`，删除第 82-92 行：

```typescript
  // Categories
  categories: {
    '全部工具': 'All Tools',
    '文本工具': 'Text Tools',
    '转换工具': 'Conversion',
    '计算工具': 'Calculation',
    '设计工具': 'Design',
    '实用工具': 'Utilities',
    '开发工具': 'Dev Tools',
    'AI 工具': 'AI Tools',
  },
```

- [ ] **Step 3: 全仓 grep 清理引用**

Run:
```bash
grep -rn "t\.categories\|t\['categories'\]\|i18n.*categories" frontend/src/
```

Expected：仅剩 `CategoryTabs.tsx` 一处。

- [ ] **Step 4: 改写 `CategoryTabs.tsx`**

替换为：

```tsx
import { CategoryTabsProps } from '../../types';

export default function CategoryTabs({ categories, activeCategory, onCategoryChange }: CategoryTabsProps) {
  // 当只有一个分类（"全部工具"）时，不显示分类筛选区域
  if (categories.length <= 1) {
    return null;
  }

  return (
    <div className="flex flex-wrap justify-center gap-3 mb-12">
      {categories.map((category) => (
        <button
          key={category}
          onClick={() => onCategoryChange(category)}
          className={`category-tab bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg transition-colors ${
            activeCategory === category ? 'active' : ''
          }`}
        >
          {category}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: 改写 `App.tsx` 的 `loadCategories`**

替换 `App.tsx` 中 `HomePage` 的 `loadCategories`：

```tsx
const loadCategories = async () => {
  try {
    const cats = await fetchCategories();
    const catNames = ["全部工具", ...cats.map(c => c.name)];
    setCategories(Array.from(new Set(catNames)));
  } catch (e) {
    console.error("Failed to load categories", e);
    setError(t.errors.categoryLoadFailed ?? "加载分类失败");
    // 不 fallback 到本地写死的分类列表（遵守「禁止兜底」规则）
  }
};
```

- [ ] **Step 6: 新增 i18n key**

在 `zh-CN.ts` 的 `errors: { ... }` 块里追加：

```typescript
    categoryLoadFailed: '加载分类失败，请稍后刷新重试',
```

在 `en-US.ts` 的 `errors: { ... }` 块里追加：

```typescript
    categoryLoadFailed: 'Failed to load categories. Please refresh later.',
```

- [ ] **Step 7: 前端编译校验**

Run:
```bash
cd frontend && npm run build
```

Expected：编译通过、无 TypeScript 报错（若有 `t.categories` 残留引用会在这里爆出来）。

- [ ] **Step 8: 浏览器验证首页**

用浏览器打开 `http://localhost:5178`：

- 顶部分类 tab 栏显示「全部工具」+ 后台真实分类名（与 admin 分类管理里的名字**字符串完全相等**）
- 点击每个分类 tab，下面的工具 ≥ 1 个
- 每个工具的"分类"字段在 admin 里能查到对应记录
- 打开 DevTools Console → 不应有 `t.categories` 相关的 undefined 报错

模拟 API 失败：临时把 `API_BASE_URL` 改错，刷新首页：

- 顶部出现红色错误条"加载分类失败..."
- 分类 tab 区域**不渲染**
- Console 有 `Failed to load categories` 的 error 日志

- [ ] **Step 9: Commit**

```bash
git add frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts \
       frontend/src/components/Hero/CategoryTabs.tsx frontend/src/App.tsx
git commit -m "refactor：首页分类 tab 直接显示后台名称，移除 i18n 硬编码翻译"
```

---

## Task 6: 端到端回归验证

**Files:** 无代码改动，纯回归

- [ ] **Step 1: 启动服务**

```bash
python dev_services.py restart
```

- [ ] **Step 2: 浏览器回归首页**

打开 `http://localhost:5178`，按下列清单逐项打钩：

| # | 验证项 | 期望 |
|---|---|---|
| 1 | 首 tab | "全部工具" |
| 2 | 后续 tab | **严格等于** admin 分类管理里"使用计数 > 0"的分类 |
| 3 | 点击每个 tab | 工具列表非空，每个工具的 category 与 tab 名**字符串相等** |
| 4 | 搜索框 | 与 tab 过滤相互独立，搜索时 tab 状态保留 |
| 5 | 空分类 | admin 里"使用计数 = 0"的分类**不**出现在首页 tab |

- [ ] **Step 3: 浏览器回归 admin**

打开 `http://localhost:5178/admin/tools`：

| # | 验证项 | 期望 |
|---|---|---|
| 6 | 分类管理 - 使用计数列 | 显示每个分类的在线工具数 |
| 7 | 删除空分类 | 成功 |
| 8 | 删除被使用分类 | toast 提示"该分类下仍有工具..." |
| 9 | 改名空分类 | 直接成功 |
| 10 | 改名被使用分类（取消级联） | 保存被拒，分类不变 |
| 11 | 改名被使用分类（确认级联） | 成功，工具的 category 字段跟随更新 |

- [ ] **Step 4: 后端日志检查**

```bash
python dev_services.py logs backend | tail -30
```

Expected：
- 启动段有 `启动清洗：...` 与 `启动校验通过：...`（或悬空引用警告）
- 无意外 ERROR
- 第二次启动 `启动清洗：无需合并的分类变体`

- [ ] **Step 5: 全仓死代码扫描**

```bash
grep -rn "t\.categories" frontend/src/ || echo "OK: 无残留"
grep -rn "\"AI 工具\"" backend/app/ || echo "OK: 无空格变体残留"
```

Expected：两条都输出 `OK`。

- [ ] **Step 6: 全部提交**

```bash
git status
# 如有未提交改动，按文件分次提交
```

---

## Self-Review 记录

**Spec coverage**：
- §1 背景 → Task 1 + Task 2 解决
- §2 目标 → Task 3（严格真实性 + 严格过滤）、Task 2（无歧义）、Task 5（禁止兜底）、Task 4（可维护性）
- §3 数据流 → Task 3 的 `GET /categories` 改造
- §4 后端 → Task 2（清洗校验）、Task 3（get_used_categories + 缓存失效）、Task 4（admin 增强）
- §5 前端 → Task 5
- §6 admin 改名手动级联 → Task 4
- §7 边界 → Task 4（409 保护）+ Task 5（错误条）+ Task 6（回归覆盖）
- §8 验收 → Task 6 全量回归
- §9 不在范围 → 未触碰（多语言 / 软删除 / 路由动态化 / 图标）

**Placeholder scan**：无 TBD / TODO / "similar to Task N" 等占位符；每个步骤都给出可执行代码或命令。

**Type consistency**：
- `_normalize_category_variants(conn)` / `_validate_tool_category_refs(conn)` 在 Task 2 定义、Task 2 测试、Task 2 Step 5 接入 `_init_db`，签名一致
- `get_used_categories() -> List[Category]` 在 Task 3 定义、Task 3 测试、Task 3 Step 4 路由调用，返回类型一致
- `update_category(..., cascade: bool = False)` 在 Task 4 定义、Task 4 Step 7 路由透传、Task 4 Step 8 前端调用，参数一致
- `ToolCategory.tool_count?: number` 在 Task 4 Step 8 定义、Task 4 Step 9 使用
