# 工具管理表格状态列拆分 + 行内开关设计

**目标**: 将工具管理表格中的"状态"列拆分为三个独立列（上线状态、PC展示、移动展示），每列使用 Toggle 开关支持行内直接操作

**架构**: 纯前端改造，只修改 `ToolManagement.tsx` 的表格部分，复用现有 `updateToolStatus` 和 `updateTool` API

**设计原则**: 紧凑行内操作 + 颜色区分 + 与编辑弹窗 Toggle 样式一致

---

## 当前状态

**表头**（4列）：工具名称 | 分类 | 状态 | 操作

**状态列内容**：
- 上线/下线徽章（绿色/灰色）
- PC: ✅ | 移动: ✅ 文字提示

**操作列内容**：编辑按钮 + 上线/下线文字按钮

## 改造方案

**表头**（6列）：工具名称 | 分类 | 上线状态 | PC 展示 | 移动展示 | 操作

**每列内容**：
- **上线状态**：Toggle 开关（绿色开=在线，灰色关=离线）
- **PC 展示**：Toggle 开关（蓝色开=展示，灰色关=隐藏）
- **移动展示**：Toggle 开关（紫色开=展示，灰色关=隐藏）
- **操作**：只保留"编辑"按钮

**Toggle 开关样式**：
```tsx
// 紧凑版，与编辑弹窗中的一致
<label className="relative inline-flex items-center cursor-pointer">
  <input type="checkbox" checked={...} onChange={...} className="sr-only peer" />
  <div className="w-9 h-5 bg-slate-600 rounded-full peer peer-checked:bg-green-500 ..."></div>
</label>
```

**颜色方案**：
- 上线状态：`peer-checked:bg-green-500`（绿色）
- PC 展示：`peer-checked:bg-blue-500`（蓝色）
- 移动展示：`peer-checked:bg-purple-500`（紫色）

## 新增 Handler

```typescript
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

## 文件修改清单

- **Modify**: `frontend/src/components/Admin/ToolManagement.tsx:77-86` — 保留 `handleStatusChange`
- **Add**: 新增 `handlePcToggle` 和 `handleMobileToggle` 函数
- **Modify**: `frontend/src/components/Admin/ToolManagement.tsx:393-399` — 表头改为 6 列
- **Modify**: `frontend/src/components/Admin/ToolManagement.tsx:416-445` — 状态列拆分为三个 Toggle 开关列，操作列只保留编辑按钮

## 验证步骤

1. `cd frontend && npx tsc --noEmit` — 无 TypeScript 错误
2. 浏览器访问 http://localhost:5178/admin/tools — 表格显示 6 列
3. 点击上线状态开关 — 工具在线/离线状态切换，显示 Toast 提示
4. 点击 PC 展示开关 — PC 展示状态切换
5. 点击移动展示开关 — 移动展示状态切换
6. 浏览器 Console 无错误
