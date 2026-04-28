# Token 消耗统计工具 — 设计文档

## 1. 需求概述

**目标**：在本机工具箱中新增 Token 消耗统计工具，聚合 Claude Code（通过 `ccusage`）和 OpenCode（通过 `opencode-usage` / `@ccusage/opencode`）的 token 使用数据，提供按天/周/月/模型/Agent 维度的可视化统计。

**核心价值**：用户可以在一个统一的前端界面中查看本机所有 AI 编码工具的 token 消耗，支持丰富的过滤、排序、可视化图表和导出功能。

## 2. 外部依赖工具

| 工具 | 用途 | 安装状态 | 数据源 | 安装命令 |
|------|------|---------|--------|---------|
| `ccusage` | Claude Code token 统计 | ✅ 已安装 | `~/.config/claude/projects/` | 已有的全局安装 |
| `opencode-usage` | OpenCode 3月后 token 统计 | ✅ 已安装 | `~/.local/share/opencode/opencode.db` | 已有的 Python 包 |
| `@ccusage/opencode`（npx） | OpenCode 3月前 token 统计 | ✅ 可用（npx 调用） | `~/.local/share/opencode/storage/` | `npx @ccusage/opencode@latest` |

**统一 JSON 输出格式**（所有工具均支持 `--json`）：
```json
{
  "daily/weekly/monthly": [
    {
      "date/week/month": "2026-04-23",
      "inputTokens": 123,
      "outputTokens": 456,
      "cacheCreationTokens": 100,
      "cacheReadTokens": 200,
      "totalTokens": 879,
      "totalCost": 0.05,
      "modelsUsed": ["model-a"],
      "modelBreakdowns": [{"modelName": "model-a", "inputTokens": 123, ...}]
    }
  ]
}
```

## 3. 方案选择

**采用方案 A：后端统一聚合 API + 纯前端仪表盘**（纯前端纯后端分离）

- 后端封装三种 CLI 工具的调用，统一字段结构返回
- 前端负责 UI 展示、过滤、排序、图表可视化
- 无实时查询，无需预缓存

## 4. 后端设计

### 4.1 文件清单

| 文件 | 作用 |
|------|------|
| `backend/app/routes/token_usage.py` | FastAPI 路由，处理所有统计维度请求 |
| `backend/app/utils/usage_fetcher.py` | 子进程调用封装，统一三种数据源 |

### 4.2 API 端点

```
POST /api/token-usage
  Request Body:
    source: "claude" | "opencode"
    type: "daily" | "weekly" | "monthly"
    since: "YYYYMMDD"    (可选，默认最近 30 天)
    until: "YYYYMMDD"    (可选)
    by: "model" | "agent" | "provider" | "session" | null
  Response:
    { "items": [...], "summary": {...} }
```

### 4.3 usage_fetcher 实现策略

```python
class UsageFetcher:
    @staticmethod
    def fetch_claude(type: str, since: str, until: str, breakdown: bool = False) -> dict:
        cmd = ["ccusage", type, "--json", "--offline"]
        if since: cmd += ["--since", since]
        if until: cmd += ["--until", until]
        if breakdown: cmd.append("--breakdown")
        return _run_cmd(cmd)

    @staticmethod
    def fetch_opencode(type: str, days: int, since: str, by: str = None) -> dict:
        # 以 3 月为界，自动选择 opencode-usage 或 ccusage-opencode
        cut_date = datetime(2026, 3, 1)
        if since and since < cut_date:
            cmd = ["npx", "@ccusage/opencode@latest", type, "--json"]
        else:
            cmd = ["opencode-usage", "run", "--json", f"--days={days}"]
            if by: cmd.append(f"--by={by}")
        return _run_cmd(cmd)

    @staticmethod
    def _run_cmd(cmd: list[str]) -> dict:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return json.loads(proc.stdout)
```

### 4.4 数据结构（Pydantic 响应模型）

```python
class UsageItem(BaseModel):
    date: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float
    models_used: list[str]
    model_breakdowns: list[dict]

class UsageSummary(BaseModel):
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost: float
    days_count: int
    avg_daily_cost: float

class UsageResponse(BaseModel):
    items: list[UsageItem]
    summary: UsageSummary
```

## 5. 前端设计

### 5.1 文件清单

| 文件 | 作用 |
|------|------|
| `frontend/src/components/Tools/TokenUsage.tsx` | 仪表盘主组件 |
| `frontend/src/api/tokenUsageApi.ts` | API 封装 |
| `frontend/src/App.tsx` | 路由注册（修改） |
| `frontend/src/i18n/locales/zh-CN.ts` | 国际化（修改） |
| `frontend/src/i18n/locales/en-US.ts` | 国际化（修改） |

### 5.2 页面布局

```
┌───────────────────────────────────────────────────────────────┐
│ 🔝 Top Bar                                                     │
│  [🤖 工具切换: Claude Code | OpenCode]                          │
│  [📅 时间范围: 最近 7 天 | 14 天 | 30 天 | 自定义]               │
│  [📊 维度: 按天 | 按周 | 按月]                                    │
│  [🔍 按模型/Agent 过滤]                                           │
├───────────────────────────────────────────────────────────────┤
│ 📊 统计卡片行                                                     │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐    │
│  │ 💵 总成本   │ 📝 总 Token │ 📥 输入    │ 📤 输出    │ 💰 日均   │
│  │ $1,234.56 │ 2,345,678 │ 1,000,000 │ 1,345,678 │ $41.15   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘    │
├───────────────────────────────────────────────────────────────┤
│ 📈 图表区域                                                       │
│  ┌────────────────────────┬──────────────────────────────┐   │
│  │  📊 日/周/月 消耗趋势  │  🥧 模型消耗占比（饼图）       │   │
│  │  (柱状图/折线图)        │                               │   │
│  └────────────────────────┴──────────────────────────────┘   │
├───────────────────────────────────────────────────────────────┤
│ 📋 数据表格                                                       │
│  ┌───────┬─────────┬───────┬───────┬───────┬───────┬────────┐ │
│  │ 日期   │ 模型     │ 输入   │ 输出   │ 缓存   │ 总计   │ 成本   │ │
│  ├───────┼─────────┼───────┼───────┼───────┼───────┼────────┤ │
│  │ 04-23 │ qwen... │ 1.2M  │ 34K   │ 3.6M  │ 8.6M  │ $0.00  │ │
│  │ 04-22 │ claude.. │ 500K  │ 120K  │ 1.5M  │ 2.1M  │ $12.30 │ │
│  └───────┴─────────┴───────┴───────┴───────┴───────┴────────┘ │
│  [📥 导出 CSV]                                                    │
└───────────────────────────────────────────────────────────────┘
```

### 5.3 技术选型

| 功能 | 选型 |
|------|------|
| 图表库 | `recharts`（已安装在项目中） |
| 表格组件 | 原生 table + Tailwind |
| 日期选择 | 自定义 Select + Input range |
| 图标 | FontAwesome（项目已有） |

## 6. 数据流

```
用户选择工具/时间范围/维度
    ↓
前端 tokenUsageApi.getUsage({ source, type, since, until, by })
    ↓
后端 POST /api/token-usage
    ↓
UsageFetcher 根据 source 类型选择 CLI 子进程
    ├─ Claude Code → ccusage daily|weekly|monthly --json
    ├─ OpenCode 3 月后 → opencode-usage run --json --by=xxx
    └─ OpenCode 3 月前 → npx @ccusage/opencode daily|weekly|monthly --json
    ↓
后端合并结果 + 计算 summary
    ↓
返回 JSON 响应
    ↓
前端渲染统计卡片、图表、表格
```

### 4.3 usage_fetcher 实现策略（P0 修复版）

```python
import os
import json
import time
from datetime import datetime, timedelta
from typing import Optional
import subprocess

# 简单内存缓存（P1-#5），5 分钟过期
_cache = {}
_CACHE_TTL = 300  # 5 分钟


def _get_from_cache(key: str) -> Optional[dict]:
    cached = _cache.get(key)
    if cached and time.time() - cached["ts"] < _CACHE_TTL:
        return cached["data"]
    _cache.pop(key, None)
    return None


def _set_cache(key: str, data: dict):
    _cache[key] = {"ts": time.time(), "data": data}


def _run_cmd(cmd: list[str], timeout: int = 60) -> dict:
    """执行 CLI 命令并解析 JSON 输出（P1-#4 错误包装）"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return {"error": result.stderr[:500] or "CLI 执行失败"}

        output = result.stdout
        json_start = -1
        for i, ch in enumerate(output):
            if ch in ("{", "["):
                json_start = i
                break
        if json_start == -1:
            return {"error": "未找到 JSON 输出"}

        return json.loads(output[json_start:])
    except subprocess.TimeoutExpired:
        return {"error": "CLI 执行超时（60 秒）"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON 解析失败: {str(e)}"}
    except FileNotFoundError:
        return {"error": f"CLI 未安装: {cmd[0]}，请先安装"}
    except Exception as e:
        return {"error": f"未知错误: {str(e)}"}


OPEND_CODE_CUTOFF = datetime(2026, 3, 1)  # 3 月为界


class UsageFetcher:
    @staticmethod
    def fetch_claude(
        report_type: str = "daily",
        since: Optional[str] = None,
        until: Optional[str] = None,
        breakdown: bool = False,
    ) -> dict:
        """调用 ccusage 获取 Claude Code token 统计"""
        cache_key = f"claude:{report_type}:{since}:{until}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        cmd = ["ccusage", report_type, "--json", "--offline"]
        if since:
            cmd += ["--since", since]
        if until:
            cmd += ["--until", until]
        if breakdown:
            cmd.append("--breakdown")

        result = _run_cmd(cmd)
        if "error" not in result:
            _set_cache(cache_key, result)
        return result

    @staticmethod
    def fetch_opencode(
        days: int = 30,
        by: Optional[str] = None,
    ) -> dict:
        """智能选择数据源（P0-#1 自动切换 3 月前/3 月后）"""
        # 计算时间范围
        since_date = datetime.now() - timedelta(days=days)
        if since_date < OPEND_CODE_CUTOFF:
            # 包含 3 月前数据，用 ccusage-opencode（全局安装版，P0-#2）
            cmd = ["ccusage-opencode", "daily", "--json"]
        else:
            # 3 月后数据，用 opencode-usage（已全局安装）
            cmd = ["opencode-usage", "run", "--json", f"--days={days}"]
            if by:
                cmd.append(f"--by={by}")

        cache_key = f"opencode:days={days}:by={by}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        result = _run_cmd(cmd)
        if "error" not in result:
            _set_cache(cache_key, result)
        return result

    @staticmethod
    def fetch_all() -> dict:
        """合并 Claude Code + OpenCode 数据（P1-#7 合计对比视图）"""
        claude = UsageFetcher.fetch_claude()
        opencode = UsageFetcher.fetch_opencode()
        return {"claude": claude, "opencode": opencode}
```

### 4.4 数据聚合层（P0-#3）

```python
def aggregate_by_week(items: list[dict]) -> list[dict]:
    """按周聚合（ISO 周）"""
    from collections import defaultdict
    weekly = defaultdict(lambda: {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0,
                                   "totalCost": 0, "cacheCreationTokens": 0, "cacheReadTokens": 0,
                                   "modelsUsed": set()})
    for item in items:
        date_str = item.get("date", "")
        if not date_str:
            continue
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            iso_week = dt.strftime("%Y-W%W")
        except ValueError:
            iso_week = date_str

        w = weekly[iso_week]
        w["inputTokens"] += item.get("inputTokens", 0)
        w["outputTokens"] += item.get("outputTokens", 0)
        w["totalTokens"] += item.get("totalTokens", 0)
        w["totalCost"] += item.get("totalCost", 0)
        w["cacheCreationTokens"] += item.get("cacheCreationTokens", 0)
        w["cacheReadTokens"] += item.get("cacheReadTokens", 0)
        for m in item.get("modelsUsed", []):
            w["modelsUsed"].add(m)

    return [{"date": k, **v, "modelsUsed": list(v["modelsUsed"])} for k, v in sorted(weekly.items())]


def aggregate_by_month(items: list[dict]) -> list[dict]:
    """按月聚合"""
    from collections import defaultdict
    monthly = defaultdict(lambda: {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0,
                                    "totalCost": 0, "cacheCreationTokens": 0, "cacheReadTokens": 0,
                                    "modelsUsed": set()})
    for item in items:
        date_str = item.get("date", "")
        if not date_str:
            continue
        month_str = date_str[:7]  # "YYYY-MM"
        m = monthly[month_str]
        m["inputTokens"] += item.get("inputTokens", 0)
        m["outputTokens"] += item.get("outputTokens", 0)
        m["totalTokens"] += item.get("totalTokens", 0)
        m["totalCost"] += item.get("totalCost", 0)
        m["cacheCreationTokens"] += item.get("cacheCreationTokens", 0)
        m["cacheReadTokens"] += item.get("cacheReadTokens", 0)
        for mod in item.get("modelsUsed", []):
            m["modelsUsed"].add(mod)

    return [{"date": k, **v, "modelsUsed": list(v["modelsUsed"])} for k, v in sorted(monthly.items())]
```

### 4.5 数据规范化（改进版）

```python
def normalize_data(raw: dict, report_type: str) -> list[UsageItem]:
    """统一规范化三种数据源的输出"""
    key = report_type
    entries = raw.get(key, raw.get("data", raw.get("daily", [])))
    if isinstance(entries, dict):
        entries = [entries]
    elif not isinstance(entries, list):
        entries = []

    items = []
    for entry in entries:
        items.append(UsageItem(
            date=entry.get("date") or entry.get("week") or entry.get("month") or entry.get("timestamp", ""),
            input_tokens=_safe_int(entry, "inputTokens"),
            output_tokens=_safe_int(entry, "outputTokens"),
            cache_creation_tokens=_safe_int(entry, "cacheCreationTokens"),
            cache_read_tokens=_safe_int(entry, "cacheReadTokens"),
            total_tokens=_safe_int(entry, "totalTokens"),
            total_cost=_safe_float(entry, "totalCost", "costUSD", "cost"),
            models_used=entry.get("modelsUsed", entry.get("models_used", [])),
            model_breakdowns=entry.get("modelBreakdowns", entry.get("modelBreakdowns", [])),
        ))
    return items


def _safe_int(d: dict, *keys: str) -> int:
    for k in keys:
        v = d.get(k)
        if v is not None:
            try:
                return int(v)
            except (ValueError, TypeError):
                pass
    return 0


def _safe_float(d: dict, *keys: str) -> float:
    for k in keys:
        v = d.get(k)
        if v is not None:
            try:
                return float(v)
            except (ValueError, TypeError):
                pass
    return 0.0
```

### 5.5 图表升级（P1-#8 成本折线）

```tsx
{/* 双轴图表：堆叠柱状图 + 成本折线 */}
<ResponsiveContainer width="100%" height={300}>
  <ComposedChart data={chartData}>
    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} />
    <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={formatNumber} />
    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#94a3b8' }}
           tickFormatter={(v) => `$${v}`} />
    <Tooltip
      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#e2e8f0' }}
    />
    <Legend />
    <Bar yAxisId="left" dataKey="inputTokens" stackId="a" fill="#3b82f6" name="输入" />
    <Bar yAxisId="left" dataKey="outputTokens" stackId="a" fill="#10b981" name="输出" />
    <Bar yAxisId="left" dataKey="cacheTokens" stackId="a" fill="#f59e0b" name="缓存" />
    <Line yAxisId="right" type="monotone" dataKey="cost" stroke="#ef4444" strokeWidth={2} name="成本 ($)" dot={{ r: 3 }} />
  </ComposedChart>
</ResponsiveContainer>
```

## 7. 错误处理（P1-#4 改进）

- CLI 未安装 → `{"error": "CLI 未安装: ccusage，请先安装"}` → 前端显示安装指引
- 数据源路径不存在 → `{"error": "未找到数据目录"}` 
- JSON 解析失败 → `{"error": "JSON 解析失败: ..."}`
- 超时 → `{"error": "CLI 执行超时（60 秒）"}`
- 网络/未知错误 → `{"error": "未知错误: ..."}`

所有错误统一返回 HTTP 500 + 友好消息前端 toast

## 10. 新增：安装准备步骤

在实现任务开始前，确保：
```bash
# 全局安装 @ccusage/opencode（P0-#2 避免 npx 慢查询）
npm install -g @ccusage/opencode

# 验证安装
ccusage-opencode daily --json
```

## 8. 不做的（YAGNI）

- ❌ 定时任务采集 + 数据库存储（增加复杂度，无此需求场景）
- ❌ 用户鉴权（本地工具，不需要）
- ❌ 多用户支持（本机使用）
- ❌ 实时推送/WebSocket

## 9. 迁移脚本

无需迁移 — 纯 CLI 调用，不涉及数据库变更。
