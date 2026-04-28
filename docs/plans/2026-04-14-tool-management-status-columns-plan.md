# 工具管理表格状态列拆分 + 行内开关 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将工具管理表格的"状态"列拆分为三个独立列（上线状态、PC展示、移动展示），每列使用 Toggle 开关支持行内直接操作

**Architecture:** 纯前端改造，只修改 `ToolManagement.tsx` 的表格部分。复用现有 `updateToolStatus` API（上线/下线）和 `updateTool` API（PC/移动展示）。新增两个 toggle handler 函数。

**Tech Stack:** React 18, TypeScript, Tailwind CSS, FastAPI backend

**设计文档:** `docs/plans/2026-04-14-tool-management-status-columns-design.md`

---

### Task 1: 新增 PC/移动 Toggle Handler

**Files:**
- Modify: `frontend/src/components/Admin/ToolManagement.tsx:86-87`（在 `handleStatusChange` 函数之后插入）

**Step 1: 插入两个新的 handler 函数**

在 `handleStatusChange` 函数（第 77-86 行）之后、`handleEditTool` 函数（第 88 行）之前，插入：

```tsx
  const handlePcToggle = async (toolId: string, currentValue: boolean) => {
    try {
      await updateTool(toolId, { show_pc: !currentValue });
      setTools(tools.map(t => t.id === toolId ? { ...t, show_pc: !currentValue } : t));
      success(`PC 展示已${!currentValue ? '开启' : '关闭'}`);
    } catch (e) {
      error('更新失败');
    }
  };

  const handleMobileToggle = async (toolId: string, currentValue: boolean) => {
    try {
      await updateTool(toolId, { show_mobile: !currentValue });
      setTools(tools.map(t => t.id === toolId ? { ...t, show_mobile: !currentValue } : t));
      success(`移动展示已${!currentValue ? '开启' : '关闭'}`);
    } catch (e) {
      error('更新失败');
    }
  };
```

**Step 2: 验证编译**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep "ToolManagement"
```
Expected: no output (no errors)

**Step 3: Commit**

```bash
git add frontend/src/components/Admin/ToolManagement.tsx
git commit -m "feat(admin): 新增 PC/移动展示 Toggle handler"
```

---

### Task 2: 修改表头（4列 → 6列）

**Files:**
- Modify: `frontend/src/components/Admin/ToolManagement.tsx:393-399`

**Step 1: 替换表头**

将第 393-399 行的表头：

```tsx
            <thead className="bg-slate-700 text-slate-100 uppercase text-xs">
              <tr>
                <th className="px-6 py-3">工具名称</th>
                <th className="px-6 py-3">分类</th>
                <th className="px-6 py-3">状态</th>
                <th className="px-6 py-3">操作</th>
              </tr>
            </thead>
```

替换为：

```tsx
            <thead className="bg-slate-700 text-slate-100 uppercase text-xs">
              <tr>
                <th className="px-6 py-3">工具名称</th>
                <th className="px-6 py-3">分类</th>
                <th className="px-6 py-3 text-center w-[100px]">上线状态</th>
                <th className="px-6 py-3 text-center w-[100px]">PC 展示</th>
                <th className="px-6 py-3 text-center w-[100px]">移动展示</th>
                <th className="px-6 py-3 w-[80px]">操作</th>
              </tr>
            </thead>
```

**关键点**：
- `text-center` 让开关居中对齐
- `w-[100px]` 固定宽度避免列宽跳动
- 操作列 `w-[80px]` 紧凑

**Step 2: 验证编译**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep "ToolManagement"
```
Expected: no output

**Step 3: Commit**

```bash
git add frontend/src/components/Admin/ToolManagement.tsx
git commit -m "feat(admin): 表格表头拆分为6列"
```

---

### Task 3: 修改表格行内容（状态列拆分为 Toggle 开关）

**Files:**
- Modify: `frontend/src/components/Admin/ToolManagement.tsx:416-445`

**Step 1: 替换 tbody 行内容**

将第 416-445 行的 `<td className="px-6 py-4">` 状态列 + 操作列：

```tsx
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      tool.status === 'online'
                        ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                        : 'bg-slate-600 text-slate-400 border border-slate-500'
                    }`}>
                      {tool.status === 'online' ? '已上线' : '已下线'}
                    </span>
                    <div className="mt-1 text-xs text-slate-500">
                      PC: {tool.show_pc !== false ? '✅' : '❌'} | 移动: {tool.show_mobile !== false ? '✅' : '❌'}
                    </div>
                  </td>
                  <td className="px-6 py-4 flex space-x-3">
                    <button
                      onClick={() => handleEditTool(tool)}
                      className="text-blue-400 hover:text-blue-300 text-sm font-medium"
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => handleStatusChange(tool.id, tool.status)}
                      className={`text-sm font-medium transition-colors ${
                        tool.status === 'online'
                          ? 'text-red-400 hover:text-red-300'
                          : 'text-green-400 hover:text-green-300'
                      }`}
                    >
                      {tool.status === 'online' ? '下线' : '上线'}
                    </button>
                  </td>
```

替换为三列 Toggle + 一列编辑按钮：

```tsx
                  {/* 上线状态 */}
                  <td className="px-6 py-4 text-center">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={tool.status === 'online'}
                        onChange={() => handleStatusChange(tool.id, tool.status)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-[18px] after:w-[18px] after:transition-all peer-checked:bg-green-500"></div>
                    </label>
                  </td>

                  {/* PC 展示 */}
                  <td className="px-6 py-4 text-center">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={tool.show_pc !== false}
                        onChange={() => handlePcToggle(tool.id, tool.show_pc !== false)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-[18px] after:w-[18px] after:transition-all peer-checked:bg-blue-500"></div>
                    </label>
                  </td>

                  {/* 移动展示 */}
                  <td className="px-6 py-4 text-center">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={tool.show_mobile !== false}
                        onChange={() => handleMobileToggle(tool.id, tool.show_mobile !== false)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-[18px] after:w-[18px] after:transition-all peer-checked:bg-purple-500"></div>
                    </label>
                  </td>

                  {/* 操作 */}
                  <td className="px-6 py-4">
                    <button
                      onClick={() => handleEditTool(tool)}
                      className="text-blue-400 hover:text-blue-300 text-sm font-medium transition-colors cursor-pointer"
                    >
                      编辑
                    </button>
                  </td>
```

**关键点**：
- 开关尺寸：`w-9 h-5`（紧凑版，与弹窗中的 `w-11 h-6` 区分）
- 颜色区分：`peer-checked:bg-green-500`（上线）、`peer-checked:bg-blue-500`（PC）、`peer-checked:bg-purple-500`（移动）
- 关闭状态统一：`bg-slate-600`
- 默认值：`tool.show_pc !== false`（undefined 视为 true，即默认展示）
- 操作列只保留"编辑"按钮，去掉"上线/下线"文字按钮

**Step 2: 验证编译**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep "ToolManagement"
```
Expected: no output

**Step 3: 浏览器验证**

导航到 http://localhost:5178/admin/tools 确认：
- 表格显示 6 列：工具名称、分类、上线状态、PC 展示、移动展示、操作
- 三个 Toggle 开关居中显示，颜色正确（绿色/蓝色/紫色）
- 点击开关立即切换状态，显示 Toast 提示
- 操作列只有"编辑"按钮
- 浏览器 Console 无错误

**Step 4: Commit**

```bash
git add frontend/src/components/Admin/ToolManagement.tsx
git commit -m "feat(admin): 状态列拆分为三个 Toggle 开关列"
```

---

### Task 4: 删除不再使用的 handleStatusChange 调用（可选清理）

**Files:**
- Modify: `frontend/src/components/Admin/ToolManagement.tsx:77-86`

**Step 1: 确认 `handleStatusChange` 仍被使用**

检查 `handleStatusChange` 是否还在被 Toggle 开关调用（Task 3 中已改为 Toggle 调用）。如果是，保留不变。

**Note:** `handleStatusChange` 仍被上线状态 Toggle 调用，不需要删除。

**Step 2: Commit（如果有清理）**

仅当有额外清理时才提交，否则跳过。

---

## 执行顺序

1. Task 1 → Task 2 → Task 3 → Task 4
2. 每个 Task 完成后在浏览器中验证再进入下一个
3. 所有任务都是纯前端改造，无需后端改动

## 关键补充点

1. **Toggle 样式参考**：使用与编辑弹窗中（第 609-643 行）相同的 Toggle 结构，但尺寸改为 `w-9 h-5` 更紧凑
2. **颜色方案**：上线=绿色(`green-500`)，PC=蓝色(`blue-500`)，移动=紫色(`purple-500`)
3. **默认值处理**：`tool.show_pc !== false` 和 `tool.show_mobile !== false`，因为 undefined 表示默认展示
4. **API 复用**：`handleStatusChange` 复用 `updateToolStatus`，`handlePcToggle`/`handleMobileToggle` 复用 `updateTool`
5. **状态更新**：点击后立即更新本地 state（optimistic update），不等待 API 返回再刷新整页
6. **错误处理**：API 失败时显示 Toast 错误提示，但本地 state 已更新（可接受的不一致，刷新页面会恢复）
