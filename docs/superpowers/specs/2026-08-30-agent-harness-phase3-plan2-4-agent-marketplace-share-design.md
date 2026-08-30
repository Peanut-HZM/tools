# P2-④ Agent 市场 / 分享 设计文档

**日期**：2026-08-30
**Phase**：3-Plan-2-4（对应原 P2 列表第 8 项 "Agent 市场 / 分享"）
**状态**：已实现（2026-08-30；验证：pytest tests/harness 720 passed / 前端 build + tsc 通过）
**对应规划 ID**：Phase 3 设计文档 §11.4 P2 列表第 8 项

---

## 1. 背景与目标

### 1.1 背景

`Agent.visibility`（`public/private/unlisted`）与 `owner_id` 列已存在（Phase 1），但**后端无任何过滤逻辑**：所有列表接口 admin-only，聊天入口按 agent_id 加载时不校验可见性——字段形同虚设。同时没有 Agent 的导出/导入与市场目录能力。

### 1.2 目标

1. **visibility 语义落地**：聊天入口校验（public/unlisted 所有人可用；private 仅 owner 与 admin）
2. **市场（基础版）**：普通用户可浏览 public Agent 目录、一键 fork 到自己名下（private 副本）
3. **分享**：admin 导出 Agent 定义（JSON bundle）/ 导入恢复（含工具绑定按名称重挂）

### 1.3 非目标

- 不做评分/评论/下载计数
- 不做跨实例分享服务（导出文件手工流通）
- 不做 unlisted 的 secret-link 分享（unlisted 仅语义=不进目录但可直接用）
- 不做 fork 后的版本追踪/上游同步
- 不导出记忆/轨迹/技能（用户数据不随 Agent 流转）

---

## 2. 架构总览

### 2.1 组件布局

```
backend/app/api/routes/
└── marketplace.py            # 新增：目录浏览 + fork
（agents.py 增 2 端点：export / import；chat_stream.py 增可见性校验）

frontend/src/
├── pages/MarketplacePage.tsx          # 新增：市场页
├── api/marketplaceApi.ts              # 新增
├── components/Admin/AgentManagement.tsx  # + visibility 选择 + 导出/导入按钮
└── App.tsx                            # + /marketplace 路由
```

### 2.2 数据模型

**零新表零新列**——复用 `agents.visibility / owner_id` 与 `agent_tools` 绑定表。

### 2.3 导出 bundle 格式

```json
{
  "format_version": 1,
  "exported_at": "2026-08-30T00:00:00Z",
  "agent": {
    "name": "...", "description": "...", "system_prompt": "...",
    "icon": "...", "icon_color": "...", "category": "...",
    "welcome_message": "...", "handoff_instruction": "...",
    "generation_params": {}, "memory_short_term_policy": "...",
    "memory_short_term_window": 20, "max_steps_per_turn": 20,
    "error_strategy": "fallback_message", "max_retries": 2,
    "memory_procedural_enabled": false, "sandbox_enabled": false,
    "memory_long_term_enabled": false, "memory_long_term_config": {}
  },
  "tool_bindings": [
    {"tool_name": "db_query", "parameter_overrides": {...}, "priority": 0, "is_enabled": true}
  ]
}
```

- 剥离：id/slug/is_default/visibility/owner_id/时间戳/统计字段/`can_handoff_to`（slug 引用跨实例无意义）
- `parameter_overrides` 原样保留（admin-only 端点、平台内流通；**导出文件不要外传**——可能含连接配置，文档明示）

---

## 3. 关键设计

### 3.1 API 清单

| 方法 | 路径 | 鉴权 | 行为 |
|---|---|---|---|
| GET | `/api/v1/marketplace/agents` | 登录用户 | public + is_active 目录（分页 skip/limit；返回 id/name/description/icon/icon_color/category/updated_at） |
| POST | `/api/v1/marketplace/agents/{id}/fork` | 登录用户 | 复制 public agent → 新 Agent（owner=当前用户、visibility=private、name+"（副本）"、is_default=False）+ 复制 tool_bindings（tool_id 直拷）；非 public → 403 |
| POST | `/api/v1/harness/agents/{id}/export` | admin | 返回 bundle JSON（Attachment 下载） |
| POST | `/api/v1/harness/agents/import` | admin | 由 bundle 创建；name 冲突自动加 `-imported` 后缀；tool 按 name 匹配，缺失跳过并列入 `warnings` |

### 3.2 聊天入口可见性校验（安全修复）

`chat_stream.py` 第 4 步加载 Agent 后：

```python
def _can_use_agent(agent, user) -> bool:
    if agent.visibility == "private":
        # private：owner 或 admin
        return str(agent.owner_id) == str(user["id"]) or user.get("role") == "admin"
    return True  # public / unlisted 对所有登录用户可用
```

不通过 → 403"该 Agent 为私有"。`get_default_agent()` 结果同样过校验（默认 agent 应保持 public；若被改 private 且非 owner 则 403）。

### 3.3 fork 语义

- 深拷贝字段：spec §2.3 `agent` 子集 + `tool_bindings`（同库内 tool_id 有效，直拷）
- 不拷贝：会话/记忆/检查点/轨迹（用户数据）；`can_handoff_to`（slug 引用重建复杂，YAGNI）
- fork 后 owner 拥有完整编辑权（Admin 入口编辑副本）

### 3.4 错误处理表

| 场景 | 行为 |
|---|---|
| fork 非 public agent | 403 |
| fork 不存在 | 404 |
| import bundle 版本不识别 | 400 "不支持的 bundle 格式" |
| import 缺 agent 字段 | 422（Pydantic 校验） |
| import 工具名不存在 | 跳过 + warnings 列表返回（不阻断） |
| export 非 admin | 403 |

---

## 4. 测试策略

| 文件 | 用例 |
|---|---|
| `test_marketplace.py` | 目录只含 public+active；fork 深拷贝（字段+bindings，owner/visibility/name 副本语义）；fork private 403；fork 后原 agent 不变；未登录 401 |
| `test_agent_export_import.py` | export bundle 形状（剥离字段不在）；import 重建（name 冲突后缀、tool 缺失 warnings、bindings 重挂）；admin 门控 |
| `test_chat_visibility.py` | private agent：owner 可用/admin 可用/他人 403；public 任何人可用 |
| `test_admin_agents_api.py` 追加 | visibility 更新生效 |
| 前端 | build + tsc |

---

## 5. 已知限制 / 不做清单

| 不做 | 留给 |
|---|---|
| 评分/下载计数/搜索排序 | 市场增长后 |
| unlisted secret link | 候选续作 |
| can_handoff_to 的 fork 重建 | 候选续作（需 slug 稳定性保证） |
| 导出文件脱敏选项 | 候选续作 |

---

## 6. 决策记录

### 6.1 为什么 fork 而不是"订阅/引用"

引用共享会让 owner 的后续修改影响所有使用者（权限与责任边界模糊）。fork = 复制所有权，与平台"admin 管理 Agent"的现有模型兼容，实现和理解成本最低。

### 6.2 为什么 export/import 是 admin-only 而市场对普通用户开放

export 含 parameter_overrides（可能带连接配置）。普通用户的分享需求由 fork 覆盖（平台内）；跨平台流通是运维级操作。

---

## 7. 参考 / 相关

- `backend/app/models/agent.py:73-74` —— visibility/owner_id 现状
- `backend/app/api/routes/chat_stream.py:97-99` —— 聊天入口 Agent 加载点
- `backend/app/api/routes/agents.py:259-268` —— harness 白名单（visibility 已可更新）
