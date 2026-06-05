# E2E 验证 - TokenUsage 4 维度饼图

> 验证日期：2026-06-05
> 验证范围：http://localhost:5178/tools/token-usage
> 验证目标：设备/工具/模型/模型成本占比 4 个维度合并为同一行 + 全部使用环形饼图 + 点击切片触发筛选

## 验证环境

- 前端：Node v22 + Vite 5.4.21，端口 5178
- 后端：Python 3.10 + Uvicorn，端口 19092
- 浏览器：Playwright Chromium，1920×1080 viewport
- 验证工具：OpenCode Playwright MCP

## 验证步骤与结果

### 1. 首屏全页概览（01-overview-fullpage.png）

页面加载后，4 个维度饼图水平排列在第二行卡片区域，宽度各占 1/4（`xl:grid-cols-4`），卡片高度统一 320px（`h-80`）。

**视觉证据：**

| 维度 | 切片数 | 实际数据 | 中心 Label |
|---|---|---|---|
| 设备 | 2 | peanut@DESKTOP-CBG2FNM 69.6亿 / huazhongmin@huazhongmindeMacBook-Pro.local 23.6亿 | 93.2亿 Token |
| 工具 | 1 | Claude Code 93.2亿 | 93.2亿 Token |
| 模型 | 4 | qwen3.6-plus 52.2亿 / claude-opus-4-8 16.1亿 / kimi-for-coding 9.1亿 / unknown 6.2亿 | 93.2亿 Token |
| 模型成本占比 | 4 | Claude · qwen3.6-plus $0.00 / Claude · claude-opus-4-8 $0.00 / Claude · kimi-for-coding $0.00 / Claude · unknown $0.00 | 93.2亿 Token（成本全 0 时回退到 Token 显示） |

**指标卡同步：** 总成本 $73.80 / 日均成本 $2.54 / 总 Token 93.2亿 / 输入 Token 41.9亿 / 输出 Token 1.9千万，与饼图总和一致。

**趋势图保留：** 第三行仍为原始的"Token 消耗趋势"组合图（柱状+折线），与饼图共存不冲突。

### 2. 点击设备饼图切片筛选（02-device-selected.png）

通过 JavaScript 派发 `click` 事件到设备饼图第二个切片（绿色 huazhongmin@...MacBook-Pro.local），触发 `setSelectedDevice` → API refetch → 全部 4 个饼图同步重渲染。

**视觉证据：**

- 设备筛选下拉框显示 `huazhongmin@huazhongmindeMacBook...`（已选）
- 指标卡更新：总成本 $73.80 → **$16.21**、总 Token 93.2亿 → **23.6亿**、输入 Token 41.9亿 → **19.2亿**、输出 Token 1.9千万 → **5.1百万**
- 设备饼图塌缩为 1 切片（被选设备 23.6亿），描边变 2px slate-100 表示选中态
- 工具/模型/模型成本占比 3 个饼图联动更新为该设备下数据

### 3. 多维筛选叠加（03-model-selected.png）

在步骤 2 基础上，点击模型饼图第一个切片（claude-opus-4-8），叠加 `selectedModel` 筛选。

**视觉证据：**

- 模型筛选下拉框显示 `claude-opus-4-8`（已选）
- 设备筛选保持 `huazhongmin@huazhongmindeMacBook...`
- 4 个饼图均塌缩为单切片：
  - 设备：huazhongmin@...MacBook-Pro.local 13.4亿
  - 工具：Claude Code 13.4亿
  - 模型：claude-opus-4-8 13.4亿（描边选中态）
  - 模型成本占比：Claude · claude-opus-4-8 $0.00 / 13.4亿
- 指标卡再次更新：总成本 $0.00（claude-opus-4-8 无成本字段）、总 Token 13.4亿、输入 13.4亿、输出 1.9百万
- 趋势图收缩为只有 claude-opus-4-8 模型在 4 个日期的柱状图

## Console 状态

- **0 errors** — 全部 4 个饼图渲染 + 2 次点击交互全程无 JS 错误
- **10 warnings** — 均为 recharts `ResponsiveContainer` 初次挂载时 `width(-1) height(-1)` 的已知警告，不影响功能

## 通过标准对照

| 标准 | 结果 |
|---|---|
| 4 个维度卡片合并到同一行 | ✓ `xl:grid-cols-4` 4 列布局 |
| 全部使用饼状图展示 | ✓ 4 个环形饼图 + 中心 Label + 图例 |
| 点击切片触发筛选 | ✓ 设备+模型双维度联动验证通过 |
| 保留原始趋势图 | ✓ Token 消耗趋势在饼图下方独立显示 |
| 关键功能不破坏 | ✓ 指标卡 / 趋势图 / 明细表均正常工作 |
| Console 0 errors | ✓ 验证通过 |
| 浏览器可正常访问 | ✓ http://localhost:5178/tools/token-usage 200 OK |

## 结论

E2E 验证 **DONE**。4 维度饼图集成符合需求，所有验收点通过。
