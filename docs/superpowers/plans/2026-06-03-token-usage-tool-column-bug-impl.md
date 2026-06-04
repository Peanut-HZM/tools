# Token Usage 明细"工具"列空白 Bug 修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Token Usage 页面"明细数据"表格中"工具"列始终显示 `-` 的 bug，让后端返回 `tool_id`，前端用它显示工具名称。

**Architecture:** 后端 `DbUsageItem` 模型添加 `tool_id` 字段，构造明细数据时传入 `r.tool_id`；前端类型和渲染逻辑相应更新。

**Tech Stack:** Python 3.10+, FastAPI, React/TypeScript

---

## 文件改动映射

| 动作 | 文件 | 说明 |
|---|---|---|
| 修改 | `backend/app/routes/token_usage.py:510-523` | DbUsageItem 添加 tool_id 字段 |
| 修改 | `backend/app/routes/token_usage.py:900-913` | 构造 DbUsageItem 时传入 tool_id |
| 修改 | `frontend/src/api/tokenUsageApi.ts:150-152` | DbUsageItem 接口添加 tool_id |
| 修改 | `frontend/src/components/Tools/TokenUsage.tsx:472-476` | getRowToolLabel 使用 item.tool_id |

---

### Task 1: 后端 DbUsageItem 添加 tool_id 字段

**Files:**
- Modify: `backend/app/routes/token_usage.py` (L510-523)

- [ ] **Step 1: 确认当前 DbUsageItem 模型**

当前模型（L510-523）：
```python
class DbUsageItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    date: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float
    models_used: list[str] = Field(default_factory=list)
    model_breakdowns: list[dict] = Field(default_factory=list)
    group_key: Optional[str] = Field(
        default=None, description="设备名或模型名（分组时）"
    )
```

- [ ] **Step 2: 添加 tool_id 字段到 DbUsageItem**

在 `model_breakdowns` 和 `group_key` 之间添加 `tool_id`：

```python
class DbUsageItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    date: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float
    models_used: list[str] = Field(default_factory=list)
    model_breakdowns: list[dict] = Field(default_factory=list)
    tool_id: Optional[str] = Field(default=None, description="工具ID")
    group_key: Optional[str] = Field(
        default=None, description="设备名或模型名（分组时）"
    )
```

- [ ] **Step 3: 语法验证**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python -m py_compile backend/app/routes/token_usage.py && echo "✅ 通过"
```

- [ ] **Step 4: Commit**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "fix(backend): DbUsageItem 添加 tool_id 字段用于明细工具列"
```

---

### Task 2: 后端填充 tool_id 到明细数据

**Files:**
- Modify: `backend/app/routes/token_usage.py` (L900-913，构造 DbUsageItem 处)

- [ ] **Step 1: 修改 DbUsageItem 构造代码**

当前代码（约 L900-913）：
```python
items.append(
    DbUsageItem(
        date=date_key,
        ...
        models_used=[r.model] if r.model else [],
        model_breakdowns=[],
        group_key=group_key,
    )
)
```

修改后：
```python
items.append(
    DbUsageItem(
        date=date_key,
        input_tokens=int(r.input_tokens or 0),
        output_tokens=int(r.output_tokens or 0),
        cache_creation_tokens=int(r.cache_creation_tokens or 0),
        cache_read_tokens=int(r.cache_read_tokens or 0),
        total_tokens=int(r.total_tokens or 0),
        total_cost=float(r.total_cost or 0),
        models_used=[r.model] if r.model else [],
        model_breakdowns=[],
        tool_id=r.tool_id,
        group_key=group_key,
    )
)
```

**注意**：`r.tool_id` 来自 `TokenUsageRecord` ORM 模型，该字段已存在于模型中（L29 定义的 `tool_id = Column(String(64), nullable=True, index=True)`）。

- [ ] **Step 2: 语法验证**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python -m py_compile backend/app/routes/token_usage.py && echo "✅ 通过"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "fix(backend): 明细接口返回 tool_id 字段"
```

---

### Task 3: 前端类型和渲染逻辑更新

**Files:**
- Modify: `frontend/src/api/tokenUsageApi.ts` (L150-152)
- Modify: `frontend/src/components/Tools/TokenUsage.tsx` (L472-476)

- [ ] **Step 1: 前端 DbUsageItem 类型添加 tool_id**

当前类型（L150-152）：
```typescript
export interface DbUsageItem extends UsageItem {
  group_key?: string;
}
```

修改后：
```typescript
export interface DbUsageItem extends UsageItem {
  group_key?: string;
  tool_id?: string;
}
```

- [ ] **Step 2: 修改 getRowToolLabel 使用 item.tool_id**

当前代码（L472-476）：
```typescript
const getRowToolLabel = (item: DbUsageItem) => {
  if (groupBy === 'tool' && item.group_key) return getToolLabel(item.group_key);
  if (selectedTool) return getToolLabel(selectedTool);
  return '-';
};
```

修改后：
```typescript
const getRowToolLabel = (item: DbUsageItem) => {
  if (item.tool_id) return getToolLabel(item.tool_id);
  return '-';
};
```

- [ ] **Step 3: TypeScript 类型检查**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npx tsc --noEmit 2>&1 | grep "TokenUsage" | head -5
```

预期：零新增错误（预存的 `replaceAll` 错误可忽略）

- [ ] **Step 4: 浏览器验证**

打开 `http://localhost:5178/tools/token-usage`，确认：
- Console 0 errors
- 明细表格"工具"列显示工具名称（如 Claude Code, OpenCode 等）

- [ ] **Step 5: Commit**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/api/tokenUsageApi.ts frontend/src/components/Tools/TokenUsage.tsx
git commit -m "fix(frontend): 明细工具列使用后端返回的 tool_id 字段"
```

---

## Self-Review

| 检查项 | 结果 |
|---|---|
| **规范覆盖** | 4 处修改全部覆盖（后端模型+构造 + 前端类型+渲染）|
| **Placeholder 扫描** | ✅ 无占位符 |
| **类型一致性** | ✅ `tool_id` 在后端是 Optional[str]，前端是 `string?`，一致 |
| **无 "Similar to Task N"** | ✅ 每个任务独立完整 |
