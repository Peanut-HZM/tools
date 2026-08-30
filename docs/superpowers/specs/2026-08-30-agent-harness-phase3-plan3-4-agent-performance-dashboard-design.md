# P3-⑫ Agent 性能仪表盘 设计文档

**日期**：2026-08-30
**Phase**：3-Plan-3-4（对应原 P3 列表第 12 项 "Agent 性能分析仪表盘"）
**状态**：设计完成（自主决策模式）

---

## 1. 背景与目标

`GET /api/v1/admin/agents/{id}/harness/stats` 已提供基础统计（对话数/消息数/trace 数/总 token/总耗时/工具使用频率），但没有可视化界面，也缺成功率与趋势维度。目标：admin 在管理界面点开单个 Agent 即可看到性能全貌。

## 2. 设计

### 2.1 后端：新增 dashboard 聚合端点

`GET /api/v1/admin/agents/{agent_id}/dashboard`（admin）：

```json
{
  "agent_id": "...",
  "basics": {                      // 复用 get_agent_harness_stats 的返回
    "conversation_count": 0, "message_count": 0, "trace_count": 0,
    "total_tokens": 0, "total_duration_ms": 0,
    "tool_usage": [{"tool_name": "...", "count": 0}]
  },
  "status_breakdown": {"success": 10, "error": 2, "timeout": 0, ...},  // traces 按 status 计数
  "success_rate": 0.83,            // success / total（total=0 时为 null）
  "avg_duration_ms": 1234,         // total_duration / trace_count（total=0 时为 null）
  "daily_trend": [                 // 最近 14 天（含今天，缺数据日补零）
    {"date": "2026-08-17", "trace_count": 0, "tokens": 0}, ...
  ]
}
```

- `daily_trend` 实现：查询 `created_at >= today-13d` 的 traces（`.limit(5000)` 防御），**Python 端**按日期分组——避免 SQLite/PostgreSQL 日期函数差异，测试环境零特殊处理
- 基础统计直接调用现有 `get_agent_harness_stats` 函数（同文件，零重复）

### 2.2 前端：DashboardDialog

- AgentManagement 行操作加"仪表盘"按钮 → `DashboardDialog`（新组件 `src/components/Admin/DashboardDialog.tsx`）
- 内容：
  - 顶部统计卡片 6 个：对话数 / 消息数 / Trace 数 / 总 Token / 成功率 / 平均耗时
  - 14 天趋势：纯 div 条形图（高度∝trace_count，title 显示明细），零图表库依赖
  - 工具使用 Top 10：水平条形（宽度∝count）
- `agentApi.getAgentDashboard(id)` 新方法

## 3. 测试策略

| 层 | 用例 |
|---|---|
| 后端 `test_agent_dashboard_api.py` | 空数据形状（success_rate=null、trend 14 天补零）；有数据聚合（status 计数/成功率/趋势分组）；admin 门控 403；agent 不存在 404 |
| 前端 | tsc + build；DashboardDialog 渲染（mock api 返回，卡片数值断言）走既有 vitest 模式 |
| 回归 | 既有 stats/harness 测试零回归 |

## 4. 不做清单

图表库引入（recharts/echarts）——零依赖条形图够用，美化候选续作；跨 Agent 对比视图——候选续作；自动刷新——YAGNI。
