# Token 消耗统计工具 - 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 新增 Token 消耗统计工具，聚合 ccusage + opencode-usage + ccusage-opencode 三种数据源，提供按天/周/月的可视化统计仪表盘

**Architecture:** 后端封装三种 CLI 工具的子进程调用（含自动切换、缓存、聚合），返回统一 JSON；前端负责 UI 展示、双轴图表、饼图、可排序表格和 CSV 导出。

**Tech Stack:** Python FastAPI + subprocess + React 18 + recharts (ComposedChart, PieChart) + Tailwind CSS

---

### Task 1: 安装依赖 — 全局安装 @ccusage/opencode

**Command:**

```bash
npm install -g @ccusage/opencode
```

**Verify:**

```bash
ccusage-opencode daily --json | head -5
```

Expected: Valid JSON output from OpenCode usage data.

---

### Task 2: 后端 — 创建 usage_fetcher.py

**Files:**
- Create: `backend/app/utils/usage_fetcher.py`

**Step 1: Create file with complete code**

```python
"""CLI 子进程调用封装，统一三种数据源（ccusage / opencode-usage / ccusage-opencode）"""
import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# 3 月为界（2026-03-01）
OPCODE_CUTOFF = datetime(2026, 3, 1)

# 简单内存缓存
_cache = {}
_CACHE_TTL = 300  # 5 分钟


def _get_from_cache(key: str) -> Optional[dict]:
    cached = _cache.get(key)
    if cached and (time.time() - cached["ts"]) < _CACHE_TTL:
        return cached["data"]
    _cache.pop(key, None)
    return None


def _set_cache(key: str, data: dict) -> None:
    _cache[key] = {"ts": time.time(), "data": data}


def _run_cmd(cmd: list[str], timeout: int = 60) -> dict:
    """执行 CLI 命令并解析 JSON 输出"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            err = result.stderr.strip()[:500] or "CLI 执行失败"
            logger.error("CLI failed: %s -> %s", " ".join(cmd), err)
            return {"error": err}

        output = result.stdout.strip()
        # 找第一个 { 或 [ 的位置（CLI 可能输出 info 行在 JSON 之前）
        json_index = -1
        for i, ch in enumerate(output):
            if ch in ('{', '['):
                json_index = i
                break
        if json_index == -1:
            return {"error": "未找到 JSON 输出"}

        return json.loads(output[json_index:])
    except subprocess.TimeoutExpired:
        return {"error": f"CLI 执行超时（> {timeout}s）"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON 解析失败: {str(e)}"}
    except FileNotFoundError:
        return {"error": f"CLI 未安装: {cmd[0]}"}
    except Exception as e:
        return {"error": f"未知错误: {str(e)}"}


class UsageFetcher:
    """统一封装三种数据源的 CLI 调用"""

    @staticmethod
    def fetch_claude(
        report_type: str = "daily",
        since: Optional[str] = None,
        until: Optional[str] = None,
        breakdown: bool = False,
    ) -> dict:
        """调用 ccusage 获取 Claude Code token 统计"""
        if shutil.which("ccusage") is None:
            return {"error": "CLI 未安装: ccusage"}

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
        """智能选择数据源（P0-#1 3 月自动切换）"""
        since_date = datetime.now() - timedelta(days=days)

        if since_date < OPCODE_CUTOFF:
            # 3 月前数据 → ccusage-opencode（已全局安装，避免 npx 慢查询 P0-#2）
            return UsageFetcher._fetch_opencode_legacy(days)
        else:
            # 3 月后数据 → opencode-usage
            return UsageFetcher._fetch_opencode_current(days, by)

    @staticmethod
    def _fetch_opencode_current(
        days: int, by: Optional[str] = None
    ) -> dict:
        """调用 opencode-usage 获取 3 月后数据"""
        if shutil.which("opencode-usage") is None:
            return {"error": "CLI 未安装: opencode-usage"}

        cache_key = f"opencode-current:{days}:{by}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        cmd = ["opencode-usage", "run", "--json", f"--days={days}"]
        if by:
            cmd.append(f"--by={by}")

        result = _run_cmd(cmd)
        if "error" not in result:
            _set_cache(cache_key, result)
        return result

    @staticmethod
    def _fetch_opencode_legacy(days: int) -> dict:
        """调用 ccusage-opencode 获取 3 月前数据"""
        if shutil.which("ccusage-opencode") is None:
            return {"error": "CLI 未安装: ccusage-opencode（请先 npm i -g @ccusage/opencode）"}

        cache_key = f"opencode-legacy:{days}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        cmd = ["ccusage-opencode", "daily", "--json"]
        result = _run_cmd(cmd)
        if "error" not in result:
            _set_cache(cache_key, result)
        return result

    @staticmethod
    def health_check() -> dict:
        """检查所有 CLI 工具是否可用"""
        return {
            "ccusage_installed": shutil.which("ccusage") is not None,
            "opencode_usage_installed": shutil.which("opencode-usage") is not None,
            "ccusage_opencode_installed": shutil.which("ccusage-opencode") is not None,
        }
```

**Step 2: Verify syntax**

Run: `cd backend && python -m py_compile app/utils/usage_fetcher.py && echo "OK"`
Expected: `OK`

---

### Task 3: 后端 — 创建 token_usage.py 路由

**Files:**
- Create: `backend/app/routes/token_usage.py`

**Step 1: Create file with complete code**

```python
"""Token 消耗统计 API 路由"""
import logging
from datetime import datetime
from typing import Optional

from collections import defaultdict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.utils.usage_fetcher import UsageFetcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/token-usage", tags=["token-usage"])


class UsageRequest(BaseModel):
    source: str = Field(
        default="claude",
        description="claude, opencode, 或 all",
    )
    type: str = Field(default="daily", description="daily, weekly, monthly")
    days: int = Field(default=30, ge=1, le=365, description="最近 N 天")
    since: Optional[str] = Field(default=None, description="YYYYMMDD")
    until: Optional[str] = Field(default=None, description="YYYYMMDD")
    by: Optional[str] = Field(default=None, description="model, agent, provider")
    breakdown: bool = Field(default=False, description="是否显示模型明")


class UsageItem(BaseModel):
    date: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float
    models_used: list[str] = Field(default_factory=list)
    model_breakdowns: list[dict] = Field(default_factory=list)


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


def normalize_entries(raw: dict, report_type: str) -> list[UsageItem]:
    """统一规范化三种数据源的输出"""
    # 尝试多个可能的 key
    entries = raw.get(report_type, raw.get("data", raw.get("daily", [])))
    if isinstance(entries, dict):
        entries = [entries]
    elif not isinstance(entries, list):
        entries = []

    items = []
    for entry in entries:
        date_val = (
            entry.get("date")
            or entry.get("week")
            or entry.get("month")
            or entry.get("timestamp", "")
        )
        # ccusage-opencode 可能返回 week 字段
        if not date_val and entry.get("week"):
            date_val = str(entry["week"])

        items.append(UsageItem(
            date=date_val,
            input_tokens=_safe_int(entry, "inputTokens", "input_tokens"),
            output_tokens=_safe_int(entry, "outputTokens", "output_tokens"),
            cache_creation_tokens=_safe_int(entry, "cacheCreationTokens", "cache_creation_tokens"),
            cache_read_tokens=_safe_int(entry, "cacheReadTokens", "cache_read_tokens"),
            total_tokens=_safe_int(entry, "totalTokens", "total_tokens"),
            total_cost=_safe_float(entry, "totalCost", "costUSD", "cost"),
            models_used=entry.get("modelsUsed", entry.get("models_used", [])),
            model_breakdowns=entry.get("modelBreakdowns", entry.get("model_breakdowns", [])),
        ))
    return items


def aggregate_by_week(items: list[UsageItem]) -> list[UsageItem]:
    """按周聚合（P0-#3）"""
    weekly: dict[str, dict] = defaultdict(lambda: {
        "inputTokens": 0, "outputTokens": 0, "totalTokens": 0,
        "totalCost": 0, "cacheCreationTokens": 0, "cacheReadTokens": 0,
        "modelsUsed": set(),
    })
    for item in items:
        if not item.date:
            continue
        try:
            dt = datetime.strptime(item.date[:10], "%Y-%m-%d")
            iso_week = dt.strftime("%Y-W%W")
        except (ValueError, TypeError):
            iso_week = item.date[:7] if item.date else "unknown"

        w = weekly[iso_week]
        w["inputTokens"] += item.input_tokens
        w["outputTokens"] += item.output_tokens
        w["totalTokens"] += item.total_tokens
        w["totalCost"] += item.total_cost
        w["cacheCreationTokens"] += item.cache_creation_tokens
        w["cacheReadTokens"] += item.cache_read_tokens
        for m in item.models_used:
            w["modelsUsed"].add(m)

    return [
        UsageItem(
            date=k,
            input_tokens=v["inputTokens"],
            output_tokens=v["outputTokens"],
            cache_creation_tokens=v["cacheCreationTokens"],
            cache_read_tokens=v["cacheReadTokens"],
            total_tokens=v["totalTokens"],
            total_cost=round(v["totalCost"], 4),
            models_used=list(v["modelsUsed"]),
        )
        for k, v in sorted(weekly.items())
    ]


def aggregate_by_month(items: list[UsageItem]) -> list[UsageItem]:
    """按月聚合（P0-#3）"""
    monthly: dict[str, dict] = defaultdict(lambda: {
        "inputTokens": 0, "outputTokens": 0, "totalTokens": 0,
        "totalCost": 0, "cacheCreationTokens": 0, "cacheReadTokens": 0,
        "modelsUsed": set(),
    })
    for item in items:
        if not item.date:
            continue
        month_str = item.date[:7]  # "YYYY-MM"
        m = monthly[month_str]
        m["inputTokens"] += item.input_tokens
        m["outputTokens"] += item.output_tokens
        m["totalTokens"] += item.total_tokens
        m["totalCost"] += item.total_cost
        m["cacheCreationTokens"] += item.cache_creation_tokens
        m["cacheReadTokens"] += item.cache_read_tokens
        for mod in item.models_used:
            m["modelsUsed"].add(mod)

    return [
        UsageItem(
            date=k,
            input_tokens=v["inputTokens"],
            output_tokens=v["outputTokens"],
            cache_creation_tokens=v["cacheCreationTokens"],
            cache_read_tokens=v["cacheReadTokens"],
            total_tokens=v["totalTokens"],
            total_cost=round(v["totalCost"], 4),
            models_used=list(v["modelsUsed"]),
        )
        for k, v in sorted(monthly.items())
    ]


def compute_summary(items: list[UsageItem]) -> UsageSummary:
    """计算汇总统计"""
    count = max(len(items), 1)
    return UsageSummary(
        total_input_tokens=sum(i.input_tokens for i in items),
        total_output_tokens=sum(i.output_tokens for i in items),
        total_tokens=sum(i.total_tokens for i in items),
        total_cost=round(sum(i.total_cost for i in items), 4),
        days_count=len(items),
        avg_daily_cost=round(sum(i.total_cost for i in items) / count, 4),
    )


def apply_aggregation(items: list[UsageItem], report_type: str) -> list[UsageItem]:
    """根据 report_type 应用聚合"""
    if report_type == "weekly":
        return aggregate_by_week(items)
    elif report_type == "monthly":
        return aggregate_by_month(items)
    return items


@router.post("", response_model=UsageResponse)
async def get_token_usage(req: UsageRequest):
    """获取 Token 消耗统数据"""
    if req.source not in ("claude", "opencode"):
        raise HTTPException(
            400,
            detail="source 必须是 'claude' 或 'opencode'",
        )
    if req.type not in ("daily", "weekly", "monthly"):
        raise HTTPException(
            400,
            detail="type 必须是 'daily', 'weekly' 或 'monthly'",
        )

    if req.source == "claude":
        raw = UsageFetcher.fetch_claude(
            report_type=req.type,
            since=req.since,
            until=req.until,
            breakdown=req.breakdown,
        )
    else:
        raw = UsageFetcher.fetch_opencode(
            days=req.days,
            by=req.by,
        )

    if "error" in raw:
        tool_name = "ccusage" if req.source == "claude" else "opencode-usage"
        raise HTTPException(
            500,
            detail=f"{tool_name} 数据获取失败: {raw['error']}",
        )

    items = normalize_entries(raw, req.type)
    items = apply_aggregation(items, req.type)

    return UsageResponse(
        items=items,
        summary=compute_summary(items),
    )


@router.get("/health")
async def health_check():
    """检查所有 CLI 工具是否可用"""
    return UsageFetcher.health_check()
```

**Step 2: Verify syntax**

Run: `cd backend && python -m py_compile app/routes/token_usage.py && echo "OK"`
Expected: `OK`

---

### Task 4: 后端 — 注册 token_usage 路由

**Files:**
- Modify: `backend/app/main.py`

**Step 1: Add import**

在 `from app.routes import ocr_routes, asr_routes, database_tool, redis_tool, ssh_tool, json_tool, resource_management` 行添加 `token_usage`。

Replace:
```python
from app.routes import ocr_routes, asr_routes, database_tool, redis_tool, ssh_tool, json_tool, resource_management
```

With:
```python
from app.routes import ocr_routes, asr_routes, database_tool, redis_tool, ssh_tool, json_tool, resource_management, token_usage
```

**Step 2: Add router registration**

After `app.include_router(json_tool.router, prefix="/api")`, add:

```python
# Token Usage router
app.include_router(token_usage.router, prefix="/api")
```

**Step 3: Verify**

Run: `cd backend && python -m py_compile app/main.py && echo "OK"`
Expected: `OK`

---

### Task 5: 前端 — 创建 tokenUsageApi.ts

**Files:**
- Create: `frontend/src/api/tokenUsageApi.ts`

**Step 1: Create file with complete code**

```typescript
import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';

const BASE_URL = `${API_BASE_URL}/token-usage`;

export interface UsageItem {
  date: string;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  total_cost: number;
  models_used: string[];
  model_breakdowns: Record<string, any>[];
}

export interface UsageSummary {
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cost: number;
  days_count: number;
  avg_daily_cost: number;
}

export interface UsageResponse {
  items: UsageItem[];
  summary: UsageSummary;
}

export interface UsageHealthCheck {
  ccusage_installed: boolean;
  opencode_usage_installed: boolean;
  ccusage_opencode_installed: boolean;
}

export async function getTokenUsage(params: {
  source: 'claude' | 'opencode';
  type: 'daily' | 'weekly' | 'monthly';
  days?: number;
  since?: string;
  until?: string;
  by?: string;
  breakdown?: boolean;
}): Promise<UsageResponse> {
  const response = await fetch(`${BASE_URL}`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      source: params.source,
      type: params.type,
      days: params.days || 30,
      since: params.since,
      until: params.until,
      by: params.by,
      breakdown: params.breakdown || false,
    }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || '获取 Token 消耗数据失败');
  }
  return response.json();
}

export async function checkTokenUsageHealth(): Promise<UsageHealthCheck> {
  const response = await fetch(`${BASE_URL}/health`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('健康检查失败');
  }
  return response.json();
}
```

**Step 2: Type check**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit 2>&1 | grep -i tokenUsage`
Expected: No errors related to tokenUsageApi

---

### Task 6: 前端 — 创建 TokenUsage.tsx 仪表盘组件

**Files:**
- Create: `frontend/src/components/Tools/TokenUsage.tsx`

**Step 1: Create file with complete code**

```tsx
import React, { useState, useEffect, useCallback } from 'react';
import { getTokenUsage, checkTokenUsageHealth, UsageItem, UsageSummary } from '../../api/tokenUsageApi';
import { useI18n } from '../../i18n';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

export default function TokenUsage() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<UsageItem[]>([]);
  const [summary, setSummary] = useState<UsageSummary | null>(null);

  // Filters
  const [source, setSource] = useState<'claude' | 'opencode'>('claude');
  const [reportType, setReportType] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [days, setDays] = useState(30);

  // Health check
  const [health, setHealth] = useState<{ ccusage_installed: boolean; opencode_usage_installed: boolean; ccusage_opencode_installed: boolean } | null>(null);

  useEffect(() => {
    checkTokenUsageHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getTokenUsage({
        source,
        type: reportType,
        days,
      });
      setItems(result.items);
      setSummary(result.summary);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [source, reportType, days]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const formatNumber = (num: number) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  const formatCurrency = (num: number) => `$${num.toFixed(2)}`;

  const exportCSV = () => {
    if (items.length === 0) return;
    const headers = ['Date', 'Input Tokens', 'Output Tokens', 'Cache Creation', 'Cache Read', 'Total Tokens', 'Cost USD', 'Models'];
    const rows = items.map(item => [
      item.date,
      item.input_tokens,
      item.output_tokens,
      item.cache_creation_tokens,
      item.cache_read_tokens,
      item.total_tokens,
      item.total_cost,
      item.models_used.join('; '),
    ]);
    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `token-usage-${source}-${reportType}-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Composed chart data: token bars + cost line (P1-#8)
  const chartData = items.map(item => ({
    date: item.date,
    inputTokens: item.input_tokens,
    outputTokens: item.output_tokens,
    cacheTokens: item.cache_creation_tokens + item.cache_read_tokens,
    totalTokens: item.total_tokens,
    cost: item.total_cost,
  }));

  // Pie chart data: model cost breakdown
  const modelData: { name: string; value: number }[] = [];
  items.forEach(item => {
    if (item.model_breakdowns?.length > 0) {
      item.model_breakdowns.forEach((m: any) => {
        const name = m.modelName || m.model || 'unknown';
        const cost = m.cost || m.costUSD || 0;
        const existing = modelData.find(d => d.name === name);
        if (existing) {
          existing.value += cost;
        } else {
          modelData.push({ name, value: cost });
        }
      });
    } else {
      item.models_used.forEach(model => {
        const existing = modelData.find(d => d.name === model);
        if (!existing) {
          modelData.push({ name: model, value: item.total_cost / (item.models_used.length || 1) });
        }
      });
    }
  });

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-slate-100">Token 消耗统计</h1>
        <span className="text-sm text-slate-400">
          数据来源: {source === 'claude' ? 'ccusage' : 'opencode-usage'}
        </span>
      </div>

      {/* Health indicators */}
      {health && (
        <div className="flex gap-4 mb-4 text-xs">
          <span className={health.ccusage_installed ? 'text-green-400' : 'text-red-400'}>
            ● ccusage: {health.ccusage_installed ? '已安装' : '未安装'}
          </span>
          <span className={health.opencode_usage_installed ? 'text-green-400' : 'text-red-400'}>
            ● opencode-usage: {health.opencode_usage_installed ? '已安装' : '未安装'}
          </span>
          <span className={health.ccusage_opencode_installed ? 'text-green-400' : 'text-red-400'}>
            ● ccusage-opencode: {health.ccusage_opencode_installed ? '已安装' : '未安装'}
          </span>
        </div>
      )}

      {/* Filters */}
      <div className="bg-slate-800 rounded-lg p-4 mb-6 flex flex-wrap gap-4 items-center">
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-400">工具:</label>
          <select
            value={source}
            onChange={e => setSource(e.target.value as 'claude' | 'opencode')}
            className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-100"
          >
            <option value="claude">Claude Code</option>
            <option value="opencode">OpenCode</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-400">维度:</label>
          <div className="flex gap-1">
            {(['daily', 'weekly', 'monthly'] as const).map(type => (
              <button
                key={type}
                onClick={() => setReportType(type)}
                className={`px-3 py-1.5 rounded text-sm transition-colors ${
                  reportType === type
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {type === 'daily' ? '按天' : type === 'weekly' ? '按周' : '按月'}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-400">时间范围:</label>
          <select
            value={days}
            onChange={e => setDays(Number(e.target.value))}
            className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-100"
          >
            <option value={7}>最近 7 天</option>
            <option value={14}>最近 14 天</option>
            <option value={30}>最近 30 天</option>
            <option value={90}>最近 90 天</option>
          </select>
        </div>

        <button
          onClick={fetchData}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium transition-colors"
        >
          {loading ? '加载中...' : '刷新'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && !items.length && (
        <div className="animate-pulse space-y-4 mb-6">
          <div className="grid grid-cols-5 gap-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="bg-slate-800 rounded-lg p-4 h-20" />
            ))}
          </div>
          <div className="bg-slate-800 rounded-lg h-72" />
        </div>
      )}

      {/* Summary Cards */}
      {summary && !loading && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          {[
            { label: '💵 总成本', value: formatCurrency(summary.total_cost) },
            { label: '📝 总 Token', value: formatNumber(summary.total_tokens) },
            { label: '📥 输入 Token', value: formatNumber(summary.total_input_tokens) },
            { label: '📤 输出 Token', value: formatNumber(summary.total_output_tokens) },
            { label: '💰 日均成本', value: formatCurrency(summary.avg_daily_cost) },
          ].map((card, i) => (
            <div key={i} className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-slate-400 mb-1">{card.label}</div>
              <div className="text-xl font-bold text-slate-100">{card.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Charts */}
      {!loading && chartData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Composed chart: stacked bars + cost line (P1-#8) */}
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h3 className="text-lg font-medium text-slate-200 mb-4">Token 消耗趋势 & 成本</h3>
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={formatNumber} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={(v) => `$${v}`} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: "1px solid #334155", color: '#e2e8f0' }}
                />
                <Legend />
                <Bar yAxisId="left" dataKey="inputTokens" stackId="a" fill="#3b82f6" name="输入" />
                <Bar yAxisId="left" dataKey="outputTokens" stackId="a" fill="#10b981" name="输出" />
                <Bar yAxisId="left" dataKey="cacheTokens" stackId="a" fill="#f59e0b" name="缓存" />
                <Line yAxisId="right" type="monotone" dataKey="cost" stroke="#ef4444" strokeWidth={2} name="成本 ($)" dot={{ r: 3 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Pie chart: model breakdown */}
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h3 className="text-lg font-medium text-slate-200 mb-4">模型成本占比</h3>
            {modelData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={modelData}
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                    nameKey="name"
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  >
                    {modelData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => formatCurrency(value)} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-slate-500">暂无模型数据</div>
            )}
          </div>
        </div>
      )}

      {/* Data Table */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <div className="flex justify-between items-center p-4 border-b border-slate-700">
          <h3 className="text-lg font-medium text-slate-200">详细数据</h3>
          <button
            onClick={exportCSV}
            disabled={items.length === 0 || loading}
            className="bg-green-600 hover:bg-green-700 disabled:opacity-50 px-3 py-1.5 rounded text-sm transition-colors"
          >
            📥 导出 CSV
          </button>
        </div>
        <div className="overflow-x-auto max-h-96">
          <table className="w-full text-sm">
            <thead className="bg-slate-900/80 text-slate-400 sticky top-0 backdrop-blur-sm">
              <tr>
                <th className="text-left px-4 py-3">日期</th>
                <th className="text-right px-4 py-3">输入</th>
                <th className="text-right px-4 py-3">输出</th>
                <th className="text-right px-4 py-3">缓存创建</th>
                <th className="text-right px-4 py-3">缓存读取</th>
                <th className="text-right px-4 py-3">总计</th>
                <th className="text-right px-4 py-3">成本 ($)</th>
                <th className="text-left px-4 py-3">模型</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && !loading ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-slate-500">暂无数据</td>
                </tr>
              ) : (
                items.map((item, i) => (
                  <tr key={i} className={`${i % 2 === 0 ? 'bg-slate-800/80' : 'bg-slate-800/40'} border-t border-slate-700/50 hover:bg-slate-700/50 transition-colors`}>
                    <td className="px-4 py-2.5 text-slate-200">{item.date}</td>
                    <td className="px-4 py-2.5 text-right text-slate-300 font-mono">{formatNumber(item.input_tokens)}</td>
                    <td className="px-4 py-2.5 text-right text-slate-300 font-mono">{formatNumber(item.output_tokens)}</td>
                    <td className="px-4 py-2.5 text-right text-slate-400 font-mono">{formatNumber(item.cache_creation_tokens)}</td>
                    <td className="px-4 py-2.5 text-right text-slate-400 font-mono">{formatNumber(item.cache_read_tokens)}</td>
                    <td className="px-4 py-2.5 text-right font-medium text-slate-100 font-mono">{formatNumber(item.total_tokens)}</td>
                    <td className="px-4 py-2.5 text-right text-green-400 font-mono">{formatCurrency(item.total_cost)}</td>
                    <td className="px-4 py-2.5 text-slate-400 max-w-[200px] truncate" title={item.models_used.join(', ')}>{item.models_used.join(', ')}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Type check**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit 2>&1 | grep -i "TokenUsage"`
Expected: No errors

---

### Task 7: 前端 — 注册路由和国际化

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/i18n/locales/zh-CN.ts`
- Modify: `frontend/src/i18n/locales/en-US.ts`

**Step 1: App.tsx — Add import**

Find where other tool components are imported (near DatabaseTool, CursorHistory, etc.) and add:

```tsx
import TokenUsage from './components/Tools/TokenUsage';
```

**Step 2: App.tsx — Add to toolRoutes map**

In the `toolRoutes` object (around line 239), add:

```tsx
'token-usage': '/tools/token-usage',
```

**Step 3: App.tsx — Add Route**

In the Routes section, add near other `/tools/*` routes:

```tsx
<Route path="/tools/token-usage" element={<TokenUsage />} />
```

**Step 4: zh-CN.ts — Add i18n text**

In `tools: { ... }` object, add:

```tsx
'token-usage': {
  title: 'Token 消耗统计',
  description: '查看本机 Claude Code 和 OpenCode 的 Token 消耗，支持按天/周/月统计',
},
```

**Step 5: en-US.ts — Add i18n text**

In `tools: { ... }` object, add:

```tsx
'token-usage': {
  title: 'Token Usage Stats',
  description: 'View local Claude Code and OpenCode token consumption with daily/weekly/monthly breakdowns',
},
```

---

### Task 8: Build verification

**Step 1: Backend syntax check**

```bash
cd backend && python -m py_compile app/utils/usage_fetcher.py && python -m py_compile app/routes/token_usage.py && python -m py_compile app/main.py && echo "All Python OK"
```

**Step 2: Frontend build**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: `✓ built in XX.XXs` — zero errors

---

### Task 9: End-to-end verification

**Step 1: Confirm services running**

Ensure frontend (5178) and backend (19092) are running.

**Step 2: Browser test**

Open `http://localhost:5178/tools/token-usage`

Verification checklist:
- ✅ Page loads without errors
- ✅ Health indicators show ccusage and opencode-usage status
- ✅ Summary cards display totals
- ✅ Composed bar chart renders correctly (stacked bars + cost line)
- ✅ Pie chart renders (if model breakdown data exists)
- ✅ Data table rows display properly with scrollable container
- ✅ CSV export downloads a valid file
- ✅ Switching between claude/opencode sources works
- ✅ Switching between daily/weekly/monthly works
- ✅ No JS errors in browser console
