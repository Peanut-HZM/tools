---
author: Peanut
created_at: 2026-06-28
purpose: 首页工具分类严格以 admin 后台维护的真实分类为准，去除写死种子/翻译兜底，启动时清洗分类歧义并校验悬空引用
---

# 首页工具分类真实性改造设计

## 1. 背景

首页工具分类 tab 当前存在三类问题：

1. **分类名来源不纯**：`backend/app/services/tools_service.py` 的 `_init_db` 硬编码种子了 7 个默认分类（`文本工具 / 转换工具 / 计算工具 / 设计工具 / 实用工具 / 开发工具 / AI工具`），其中一些分类可能从未被任何工具使用，却仍然显示在首页 tab 栏。
2. **名字歧义导致过滤对不上**：种子默认 `AI工具`（无空格），而 `backend/app/data/tools_data.py` 里大量工具写的是 `AI 工具`（有空格）。`tools.category` 字段存的是字符串，首页按 `tool_categories.name` 做精确匹配过滤，结果"AI工具"分类下过滤不出任何工具。
3. **i18n 翻译与业务数据混在一起**：`frontend/src/i18n/locales/zh-CN.ts` 与 `en-US.ts` 硬编码了 `categories: { ... }` 翻译映射，未在映射里的分类名就直接显示原始字符串。分类是业务数据（admin 维护），不应由代码层兜底翻译。

此外前端 `App.tsx` 的 `loadCategories` 已经调用了真实 API（`GET /categories`），**不是写死数据**。问题主要集中在后端的种子数据、命名一致性、以及前端的 i18n 兜底渲染。

## 2. 目标（按优先级）

1. **严格真实性**：首页分类 tab 列表 **⊆** admin「工具分类」管理页里真实维护的分类，**不显示**写死/兜底/从未被使用的分类。
2. **严格过滤**：tab 名与 `tools.category` 字段字符串完全相等才计入过滤结果，过滤结果与 admin 工具管理里的分类筛选完全一致。
3. **无歧义**：启动时清洗掉 `"AI工具"` 与 `"AI 工具"` 这类空格变体，统一为规范名。
4. **禁止兜底**：API 失败如实报错，不写默认值、不伪造分类、不静默吞异常（遵守全局 CLAUDE.md「禁止 Mock 与兜底规则」）。
5. **可维护性**：admin 改分类名/增删分类，首页刷新即同步；admin 能看到每个分类的"使用计数"，能阻止误删正在被使用的分类。

**不做的事（YAGNI）**：

- 不做分类软删除业务逻辑（表里 `deleted` 字段已存在但未使用，本次不引入）。
- 不做分类的多语言字段（已确认直接走后台名称）。
- 不做分类图标/排序的高级编辑（admin 现有表单已够用）。
- 不做分类改名的自动级联（改为 admin 手动弹窗确认）。

## 3. 数据流

```
首页 CategoryTabs
   │ fetch('/categories') → GET /categories (现有 URL，内部改为 get_used_categories)
   │                         SELECT DISTINCT c.*
   │                         FROM tool_categories c
   │                         JOIN tools t ON t.category = c.name
   │                         WHERE t.status = 'online'
   │                         ORDER BY c.sort_order
   ▼
首页首 tab 固定为"全部工具"（UI 约定，非后台数据）
   + 后端返回的每个真实分类作为后续 tab
   │
   ▼ 点击某个分类 tab
   │
loadToolsDataByCategory(name) → GET /tools/category/{name}
                                  （现有接口，严格精确匹配 tools.category）
```

**"全部工具" 约定**：继续作为首页首 tab 保留。这是 UI 层约定，不是 `tool_categories` 里的数据。后端 `get_tools_by_category` 与 `get_tools_for_platform` 对 `"全部工具"` 做特殊处理（= 不过滤），此约定本次不动。

## 4. 后端改造

### 4.1 `tools_service.py`

**新增 `get_used_categories() -> List[Category]`**

```python
def get_used_categories(self) -> List[Category]:
    """只返回被至少一个在线工具引用的分类，按 sort_order 排序"""
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
```

**修改 `get_all_categories()` 的调用方**：

- 前台 `GET /categories` → 改调 `get_used_categories()`（URL 不变，返回类型不变 `List[Category]`）
- admin `GET /admin/categories`（在 `admin.py` 里）→ 仍调 `get_all_categories()`，并追加 `tool_count` 字段

**admin 接口增强**：`listCategories` 返回 `{...category, tool_count: int}`

```sql
SELECT c.*, COUNT(t.id) AS tool_count
FROM tool_categories c
LEFT JOIN tools t ON t.category = c.name AND t.status = 'online'
WHERE c.deleted = FALSE
GROUP BY c.id
ORDER BY c.sort_order
```

**启动时清洗 + 校验**（接在 `_init_db` 现有"种子分类 + 种子工具"完成之后、`conn.commit()` 之前）

```python
# --- 分类清洗（合并空格变体） ---
try:
    cur.execute("SELECT id, name, sort_order FROM tool_categories")
    all_cats = cur.fetchall()
    groups: Dict[str, List[dict]] = {}
    for row in all_cats:
        key = row["name"].replace(" ", "")
        groups.setdefault(key, []).append(dict(row))

    merged_info = []
    for key, members in groups.items():
        if len(members) <= 1:
            continue
        members.sort(key=lambda r: r["sort_order"])
        canonical = members[0]
        drop_names = [m["name"] for m in members[1:]]
        drop_ids = [m["id"] for m in members[1:]]
        if drop_names:
            cur.execute(
                "UPDATE tools SET category = %s WHERE category = ANY(%s)",
                (canonical["name"], drop_names),
            )
            cur.execute(
                "DELETE FROM tool_categories WHERE id = ANY(%s)",
                (drop_ids,),
            )
            merged_info.append({key: canonical["name"], "dropped": drop_names, "affected_tools": cur.rowcount})
    if merged_info:
        logger.info("启动清洗：合并分类变体 %s", merged_info)
    else:
        logger.info("启动清洗：无需合并的分类变体")
except Exception as e:
    logger.error("启动清洗失败（不阻止启动）: %s", e)

# --- 悬空引用校验 ---
try:
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

**关键约束**：

- 清洗和校验都在**独立 `try/except`** 里，失败仅记日志，**不**阻止服务启动，**不**回滚核心 `_init_db`。
- 清洗**幂等**：库里已一致时 `groups` 全部 size=1，不执行任何写操作。
- 校验命中悬空时**只报警、不写默认值、不改数据**（遵守「没有就是没有」规则）。

### 4.2 `tools_data.py`

全文把 `"AI 工具"` 改为 `"AI工具"`（约 4 处）。保证种子数据与清洗后的规范名一致，避免每次启动又产生新变体。

### 4.3 路由层 `tools.py`

- `GET /categories` 端点内部调用从 `tools_service.get_all_categories()` 改为 `tools_service.get_used_categories()`。入参 / 出参类型不变（`List[Category]`），前端无需改请求层。
- `GET /admin/categories`（`admin.py`）追加 `tool_count` 字段。

### 4.4 缓存失效

| 触发点 | 失效 key |
|---|---|
| 分类增 / 删 / 改 | `categories`、`used_categories` |
| 工具上线 / 下线（`update_tool_status`） | `used_categories`、`tools:<platform>:<category>` |
| 工具改分类（`update_tool` 修改 category 字段） | `used_categories`、`tools:<platform>:<category>`、`tools:<platform>:all` |
| 工具删除 | 同上 |

现有的 `_tools_cache.invalidate(...)` 调用点补齐上述 key。

### 4.5 admin 删除分类的保护

`DELETE /categories/{id}` 增加前置检查：

```python
cur.execute("SELECT COUNT(*) FROM tools WHERE category = %s", (cat_name,))
if cur.fetchone()[0] > 0:
    raise HTTPException(status_code=409, detail="该分类下仍有工具，请先迁移后再删除")
```

## 5. 前端改造

### 5.1 `App.tsx` — `HomePage.loadCategories`

- 现有调用 `fetchCategories()` 拉真实数据，**保留**。
- 失败处理改为：`setError("加载分类失败")`，**不** fallback 到本地写死的 `["全部工具"]`。错误条显示在首页顶部，分类 tab 区域不渲染。

```ts
const loadCategories = async () => {
  try {
    const cats = await fetchCategories();
    const catNames = ["全部工具", ...cats.map(c => c.name)];
    setCategories(Array.from(new Set(catNames)));
  } catch (e) {
    console.error("Failed to load categories", e);
    setError(t.errors.categoryLoadFailed); // 新增 i18n key
  }
};
```

### 5.2 `CategoryTabs.tsx`

```tsx
// 旧
{t.categories[category as keyof typeof t.categories] || category}

// 新：后台叫什么就显示什么
{category}
```

`key={category}`（`name` 在 `tool_categories` 有 UNIQUE 约束）。

保留"只有 1 个分类（即只有"全部工具"）时不显示 tab 栏"的逻辑。

### 5.3 i18n 清理

- 删除 `frontend/src/i18n/locales/zh-CN.ts` 与 `en-US.ts` 中的 `categories: { ... }` 字段。
- 全仓 grep `t.categories` 确认无残留引用（目前只在 `CategoryTabs.tsx`）。
- 新增 key：`errors.categoryLoadFailed`（"加载分类失败" / `"Failed to load categories"`）。

### 5.4 `useCategory.ts`

保持不变。`Category = string`，`activeCategory` 初始值仍为 `"全部工具"`。

### 5.5 admin `ToolManagement.tsx` 分类管理页

- 分类列表新增「使用计数」列，0 的灰色标记"未使用"。
- 删除分类时若计数 > 0，后端会返回 409，前端弹 toast 显示错误信息。

### 5.6 `services/api.ts`

`fetchCategories` 返回类型仍是 `ToolCategory[]`，请求层不改。缓存策略（`localStorage` + `promiseCache` 30s 去重）不变。

## 6. admin 分类改名的手动级联

admin 编辑分类名时（`PUT /categories/{id}`）：

1. 后端先查出当前使用该分类的工具数 N。
2. 若 N = 0：直接改名。
3. 若 N > 0：前端弹窗 `当前有 N 个工具使用该分类，是否一并更新工具的 category 字段？`
   - 用户确认 → 调用 `PUT /categories/{id}?cascade=true`，后端事务内同时 UPDATE `tool_categories.name` 与 `tools.category`。
   - 用户取消 → 拒绝保存（409 或前端拦截）。

不做自动静默级联，避免违反"最小惊讶原则"。

## 7. 边界情况

| 场景 | 处理 |
|---|---|
| 所有工具都 offline | 首页 tab 栏不显示（只有"全部工具" 1 个 → `CategoryTabs` 现有逻辑返回 null） |
| 管理员改名分类 X→Y 但没勾选级联 | 拒绝保存（409 提示先迁移工具） |
| 管理员删除正在被使用的分类 | 409 拒绝 |
| 管理员新建分类但还没工具用 | 首页 tab 不显示；admin 分类列表里能看到（"使用计数 = 0"） |
| 缓存未刷新 | 分类变更时 `invalidate("used_categories")` + `invalidate("categories")`；前端 localStorage 30s TTL |
| `/categories` API 失败 | 首页顶部错误条，分类 tab 区域不渲染（不兜底） |
| `/tools/category/{name}` 返回空数组 | 正常显示"该分类下暂无工具"（真实数据状态，非错误） |
| 分类名为空字符串 | 校验阶段记 ERROR，但不在首页展示（JOIN 不到在线工具 → 自动被过滤掉） |

## 8. 验收标准

**后端启动**：

- 首次部署后日志出现 `启动清洗：合并分类变体 {...}` 一行，随后 `启动校验通过：...`。
- 第二次启动日志出现 `启动清洗：无需合并的分类变体` 与 `启动校验通过：...`。
- 全程无 ERROR 级别日志（除非历史数据真有悬空引用需管理员处理）。

**浏览器（首页）**：

1. `GET /categories` 返回的分类列表 **⊆** admin「工具分类」管理页里能看到的分类。
2. 点击每个分类 tab，下面的工具都至少 1 个；每个工具的"分类"字段在 admin 里能查到对应记录。
3. "全部工具" 仍是首 tab，显示所有在线工具。
4. 搜索框与分类过滤相互独立，搜索时不破坏分类过滤状态（保持现状）。

**浏览器（admin）**：

5. admin 分类管理列表显示"使用计数"，0 的灰色标记"未使用"。
6. 删除正在被使用的分类 → 返回 409，弹 toast 提示。
7. 改名正在被使用的分类 → 弹窗询问是否级联；确认后工具 category 字段同步更新。

**回归**：

- admin 工具管理：分类筛选下拉、编辑工具改分类、上下线工具
- admin 分类管理：增 / 删 / 改分类
- 首页：分类 tab 显示、点击过滤、"全部工具"、搜索框

## 9. 不在本次范围

- 分类的多语言字段（后台维护中文名即前台显示中文名）。
- 分类的软删除业务逻辑（`deleted` 字段保留但不引入新流程）。
- 工具路由表 `toolRoutes` 的动态化（仍由前端硬编码 `toolId → route`，不在本次处理）。
- 分类的图标展示（`tool_categories.icon` 字段保留但首页暂不使用）。
