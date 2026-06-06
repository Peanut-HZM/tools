---
author: Peanut
created_at: 2026-06-06
purpose: 移除 Token Usage 页面旧工具状态卡片及后端 health check API
---

# 移除 Token Usage 页面旧工具状态卡片

## 背景

Token Usage 页面（`/tools/token-usage`）顶部有 4 个状态卡片展示旧 CLI 工具的安装状态：
- ccusage 可用
- opencode-usage 可用
- ccusage-opencode 可用
- Codex/OpenClaw 待接入

现在统一使用 ccusage 统计所有 token 用量，这些旧工具状态卡片不再需要。

## 目标

1. 移除前端页面上的旧工具状态卡片组件
2. 移除前端相关的 health check API 调用
3. 移除后端 `/health` 路由
4. **保留** opencode 数据的同步和统计逻辑（`sync_token_usage_v2` 等）

## 设计原则

- **只删展示层**：只移除 UI 组件和 health check API，不动数据同步逻辑
- **保留数据流**：opencode 通过 `_fetch_opencode_daily` → `UsageFetcher.fetch_opencode` 的数据链路完全保留

## 前端删除范围

### TokenUsage.tsx

删除内容：
- 第 632-649 行：4 个状态卡片 JSX（ccusage / opencode-usage / ccusage-opencode / Codex/OpenClaw）
- `health` state（`useState<UsageHealthCheck | null>(null)`）
- `healthError` state（`useState<string | null>(null)`）
- `CheckCircle2` 的 lucide-react import
- `checkTokenUsageHealth` 和 `UsageHealthCheck` 的 API import
- `useEffect` 中调用 `checkTokenUsageHealth()` 的代码（约第 242-253 行）
- `healthLabel()` 辅助函数（如不再使用）

### tokenUsageApi.ts

删除内容：
- `UsageHealthCheck` 接口（第 40-44 行）
- `checkTokenUsageHealth()` 函数（第 236-244 行）

## 后端删除范围

### token_usage.py

删除内容：
- `@router.get("/health")` 路由及 `health_check()` 函数

### usage_fetcher.py

删除内容：
- `health_check()` 方法（第 272-281 行）
- 或简化为只返回 ccusage 安装状态

## 明确保留（不动）

| 文件 | 保留内容 |
|------|----------|
| `usage_fetcher.py` | `fetch_opencode()`、`_fetch_opencode_merged()`、`_fetch_opencode_current()`、`_fetch_opencode_legacy()` |
| `token_usage_sync_service.py` | `_fetch_opencode_daily()`、`_parse_opencode_entries()`、`SYNC_SOURCES` 中的 opencode 条目、`TOOL_NAME_MAP`、`MODEL_ALIASES` |
| `sync_token_usage_v2()` | opencode 数据源的同步逻辑 |

## 验收标准

1. Token Usage 页面不再显示 4 个旧工具状态卡片
2. 页面加载时不再调用 `/token-usage/health` API
3. 后端 `/token-usage/health` 路由已移除
4. opencode 数据的同步和展示不受影响
