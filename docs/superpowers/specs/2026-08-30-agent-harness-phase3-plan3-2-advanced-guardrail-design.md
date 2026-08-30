# P3-⑩ 高级 Guardrail（内置规则引擎）设计文档

**日期**：2026-08-30
**Phase**：3-Plan-3-2（对应原 P3 列表第 10 项 "高级 Guardrail"）
**状态**：已实现（2026-08-30；验证：pytest tests/harness 740 passed；本期为后端功能，无前端改动）

---

## 1. 背景与目标

现有 guardrail 每条都必须绑定一个已注册工具（`tool_id`），配置一条"禁止出现竞品名"这么简单的规则也要先实现一个工具——成本倒挂。本期给 guardrail 增加**内置规则类型**（无需工具）：

| type | config | 行为 |
|---|---|---|
| `keyword` | `{"keywords": [str], "case_sensitive": false}` | 内容含任一关键词 → 违规 |
| `regex` | `{"pattern": str}` | 内容匹配正则 → 违规（正则编译失败 → fail-closed 异常路径） |
| `max_length` | `{"max_chars": int > 0}` | 内容长度超限 → 违规 |

## 2. 设计

### 2.1 条目格式（input_guardrails / output_guardrails JSONB 列表元素）

```json
{"name": "竞品过滤", "type": "keyword", "config": {"keywords": ["FooAI"], "case_sensitive": false}}
{"name": "防注入", "type": "regex", "config": {"pattern": "ignore (previous|above) instructions"}}
{"name": "限长", "type": "max_length", "config": {"max_chars": 4000}}
```

判定分发：条目含 `tool_id` → 走现有工具路径（零改动）；含 `type` → 内置规则路径；两者都缺 → 配置错误（fail-closed，同工具异常路径）。违规后的 block/warn 语义复用 `guardrail_on_violation`。

### 2.2 实现

`guardrail.py` 重构：
- `_evaluate_rule(gr: dict, content: str) -> Optional[str]`：返回违规原因或 None（纯函数，好测）
- `_decide(on_violation, name, reason, stage, warned=False) -> GuardrailResult`：统一 block/warn 决策（消除两份重复分支）
- 两个 runner 循环体内：`tool_id` 分支（原逻辑）→ `type` 分支（`_evaluate_rule`；违规 reason 传入 `_decide`）→ 否则按配置错误走 fail-closed
- 配置校验提前到**评估时**（keyword 空 keywords / regex 编译失败 / max_chars 非正整数 → 抛 ValueError → 走异常 fail-closed 路径），并 INFO 日志

### 2.3 Schema 校验（agents.py harness 更新）

`AgentHarnessUpdate.input_guardrails / output_guardrails` 元素校验（Pydantic validator）：
- 每项必须是 dict 且含 `name`
- `tool_id` 存在 → 放行；否则必须有合法 `type` + 形状正确的 `config`（keyword: 非空字符串数组；regex: 可编译；max_length: 正整数）——不合法返回 422
- 不改变字段类型（仍是 `Record<string, any>[]` JSONB），向后兼容

### 2.4 范围界定

- 前端无 guardrail UI（现状如此），本期不加；配置继续走 API（curl / HTTP 客户端工具）
- 不做 LLM-as-judge guardrail（成本高，属另一档方案）
- 不做规则命中统计（trace 已有 `guardrail_triggered` 事件）

## 3. 测试策略

| 用例 | 覆盖 |
|---|---|
| keyword 命中/未命中/大小写开关 | `_evaluate_rule` 分支 |
| regex 命中/不匹配/非法 pattern fail-closed | 同上 + 异常路径 |
| max_length 边界（==max 不违规，+1 违规） | 边界 |
| dispatch：tool_id 条目行为不变（现有 test_guardrail.py 零回归） | 兼容 |
| 无 tool_id 无 type → blocked（fail-closed） | 配置错误 |
| warn 模式下规则违规 → warned=True 不阻断 | 语义复用 |
| API：非法条目 422；合法 keyword 条目保存成功 | schema 校验 |

## 4. 不做清单

规则热更新（改 guardrail_on_violation 已实时生效，规则本身存 JSONB 也是实时）——无需做；规则库/模板市场——候选续作。
