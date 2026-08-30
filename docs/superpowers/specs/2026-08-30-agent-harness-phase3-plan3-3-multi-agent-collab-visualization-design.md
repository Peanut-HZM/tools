# P3-⑪ 多 Agent 协作可视化 设计文档

**日期**：2026-08-30
**Phase**：3-Plan-3-3（对应原 P3 列表第 11 项 "多 Agent 协作可视化"）
**状态**：已实现（2026-08-30；验证：pytest tests/harness 741 passed / 前端 build + vitest 4 passed）

---

## 1. 背景与目标

Handoff（agent 间委派）已在 runtime 工作，但**不落 TraceStep**——协作过程在 trace 里不可见；前端 TraceViewer 也没有协作视角。目标：一次多 Agent 会话结束后，用户能在追踪详情里看到"谁在什么时候把任务交给了谁"。

## 2. 设计

### 2.1 后端：handoff 落 TraceStep（缺口修复）

`agent_runtime.py` handoff 分支（yield Event.handoff 之后）：

```python
# P3-⑪: 记录 handoff step（协作可视化数据源）
try:
    recorder = getattr(self.ctx, "trace_recorder", None)
    if recorder is not None and getattr(self, "_trace_id", None):
        recorder.start_step(self._trace_id, "handoff")
        recorder.end_step(
            ..., metadata={"from_agent": from_agent_info,
                           "to_agent": to_agent_info, "reason": "handoff requested"}
        )
except Exception:  # best-effort，不影响 handoff 主流程
    logger.warning("记录 handoff step 失败: %s", type(e).__name__)
```

- trace_id 引用方式以 runtime 内现有 trace 使用为准（实现时对齐，若 runtime 持有的是 trace 对象则传其 id）
- `end_step` 已支持 metadata 参数则直接用；否则补一个可选参数（`trace_recorder.py`，向后兼容默认 None）

### 2.2 前端：TraceViewer 协作时间线

- 新组件 `CollabTimeline`（`src/components/Harness/`）：入参 `steps: TraceStep[]`
  - 过滤 `step_type === "handoff"` 的 steps，读 `metadata.from_agent / to_agent`
  - 渲染：顶部"协作链"徽章序列（A → B → C，去重连续同名）；下方按 step_index 列出每次交接（时间点 step_index、from → to、reason）
  - 无 handoff steps → 不渲染（单 Agent 会话零打扰）
- TraceViewer 在 Steps 表格上方嵌入 `<CollabTimeline steps={selected.steps} />`
- Steps 表格中 handoff 行高亮（`bg-amber-50` + "→ 移交"徽章），列显示 from → to

### 2.3 数据契约

handoff step metadata：`{"from_agent": {"id", "name"}, "to_agent": {"id", "name"}, "reason": str}`（trace 详情 API 已透出 metadata，零后端 API 改动）

## 3. 测试策略

| 层 | 用例 |
|---|---|
| 后端 | runtime handoff 测试扩展：handoff 发生后存在 `step_type="handoff"` 的 TraceStep 且 metadata 含 from/to（mock trace_recorder 断言调用） |
| 前端 | CollabTimeline：有 handoff steps → 渲染链 A → B；无 → 返回 null；TraceViewer 手动验证路径写入验收 |
| 回归 | 既有 handoff/runtime/trace 测试零回归 |

## 4. 不做清单

| 不做 | 留给 |
|---|---|
| 实时（流式）协作可视化 | 候选续作（事件流已具备，需前端 SSE 订阅 UI） |
| 泳道图（每 agent 一行） | 候选续作 |
| 跨 turn 协作历史聚合 | 候选续作 |
