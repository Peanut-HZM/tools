# 系统监控页面二次优化实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将系统信息顶部改为网格卡片布局，并新增服务概览卡片行

**Architecture:** 后端在进程列表接口返回中新增 `type_summary` 聚合字段，前端读取该字段渲染服务概览卡片行，同时将顶部系统信息从紧凑标签行改为网格卡片布局

**Tech Stack:** FastAPI (Python), psutil, React 18, TypeScript, Tailwind CSS

**设计文档:** `docs/plans/2026-04-13-system-monitor-v2-design.md`

---

### Task 1: 后端新增进程类型聚合逻辑

**Files:**
- Modify: `backend/app/services/system_monitor_service.py:182-247`

**Step 1: 在 `get_process_list()` 中计算聚合数据**

在 `get_process_list()` 函数的 `processes.sort(...)` **之前**（基于原始未排序的全量进程列表）插入聚合计算逻辑。注意：聚合应基于**全部进程**（分页前），这样 `type_summary` 始终是完整统计。

**性能优化**：聚合放在排序之前，避免先排序再聚合的额外开销。同时过滤掉只有 1 个进程且 CPU < 0.1% 的不活跃类型，减少前端渲染负担。

```python
    # 聚合进程类型统计（基于全量数据，排序前）
    type_map: Dict[str, Dict] = {}
    for p in processes:
        pt = p["project_type"]
        if pt == "Other":
            continue
        if pt not in type_map:
            type_map[pt] = {"count": 0, "cpu_percent": 0.0, "memory_percent": 0.0, "memory_rss": 0}
        type_map[pt]["count"] += 1
        type_map[pt]["cpu_percent"] += p["cpu_percent"]
        type_map[pt]["memory_percent"] += p["memory_percent"]
        type_map[pt]["memory_rss"] += p["memory_rss"]

    # 过滤：只返回 count > 1 或 cpu_percent > 0.1 的类型
    # 按 CPU 降序，格式化
    type_summary = sorted(
        [
            {
                "type": t,
                "count": v["count"],
                "cpu_percent": round(v["cpu_percent"], 1),
                "memory_percent": round(v["memory_percent"], 1),
                "memory_rss": v["memory_rss"],
            }
            for t, v in type_map.items()
            if v["count"] > 1 or v["cpu_percent"] > 0.1
        ],
        key=lambda x: x["cpu_percent"],
        reverse=True,
    )
```

**Step 2: 将 `type_summary` 加入返回值**

修改返回的 dict，新增 `type_summary` 字段：

```python
    return {
        "processes": page_data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "type_summary": type_summary,
    }
```

**Step 3: 验证 API 返回**

```bash
curl -s 'http://localhost:19092/api/system-monitor/processes?page=1&page_size=10' | python3 -m json.tool | grep -A 5 type_summary
```
Expected: JSON object with `type_summary` array containing entries like `{"type": "Spring Boot", "count": 7, "cpu_percent": 6.7, "memory_percent": 3.6, "memory_rss": 1216348160}`

**Step 4: Commit**

```bash
git add backend/app/services/system_monitor_service.py
git commit -m "feat(system-monitor): 进程列表接口新增 type_summary 聚合字段"
```

---

### Task 2: 前端新增服务类型图标映射

**Files:**
- Modify: `frontend/src/components/Tools/SystemMonitor.tsx:204-205`（在 `PAGE_SIZE_OPTIONS` 常量之前插入）

**Step 1: 添加服务类型图标和颜色映射**

在 `PROJECT_TYPE_COLORS` 定义之后、`PAGE_SIZE_OPTIONS` 之前，插入：

```tsx
// 服务类型图标映射（FontAwesome class）
const SERVICE_ICONS: Record<string, { icon: string; color: string }> = {
  'Spring Boot': { icon: 'fa-leaf', color: 'text-emerald-400' },
  'Java': { icon: 'fa-coffee', color: 'text-orange-400' },
  'Node.js': { icon: 'fa-node-js', color: 'text-green-400' },
  'Python': { icon: 'fa-python', color: 'text-blue-400' },
  'MySQL': { icon: 'fa-database', color: 'text-blue-400' },
  'PostgreSQL': { icon: 'fa-database', color: 'text-blue-400' },
  'Redis': { icon: 'fa-bolt', color: 'text-red-400' },
  'Nginx': { icon: 'fa-server', color: 'text-emerald-400' },
  'Docker': { icon: 'fa-docker', color: 'text-blue-400' },
  'Go': { icon: 'fa-golang', color: 'text-cyan-400' },
  'FastAPI': { icon: 'fa-fire', color: 'text-orange-400' },
  'Django': { icon: 'fa-python', color: 'text-blue-400' },
  'Flask': { icon: 'fa-python', color: 'text-blue-400' },
  'Celery': { icon: 'fa-python', color: 'text-blue-400' },
  'Tomcat': { icon: 'fa-coffee', color: 'text-orange-400' },
  'Vite': { icon: 'fa-bolt', color: 'text-cyan-400' },
};
```

**Step 2: 添加 ServiceCard 组件**

在 `InfoTag` 组件之后、`SystemMonitor` 函数之前（约第 226 行），插入：

**注意**：`formatBytes` 函数在第 87 行定义（模块级），ServiceCard 组件在第 227 行插入（模块级），可以正常访问。

```tsx
// 服务概览卡片
function ServiceCard({ type, count, cpuPercent, memoryRss, onClick }: {
  type: string; count: number; cpuPercent: number; memoryRss: number; onClick?: () => void;
}) {
  const iconInfo = SERVICE_ICONS[type] || { icon: 'fa-cube', color: 'text-slate-400' };
  const cpuColor = cpuPercent > 50 ? 'text-red-400' : cpuPercent > 20 ? 'text-amber-400' : 'text-slate-400';

  return (
    <div
      className={`bg-slate-900 rounded-xl p-3 border border-slate-800 ${onClick ? 'cursor-pointer hover:border-slate-600 transition-colors' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-center gap-1.5 mb-1">
        <i className={`fas ${iconInfo.icon} ${iconInfo.color} text-xs`}></i>
        <span className="text-xs text-slate-500 truncate">{type}</span>
      </div>
      <div className="text-sm font-bold text-white mb-1">{count}</div>
      <div className="flex items-center justify-between text-xs">
        <span className={cpuColor}>{cpuPercent}%</span>
        <span className="text-slate-600">{formatBytes(memoryRss)}</span>
      </div>
    </div>
  );
}
```

**可点击特性**：传入 `onClick` 时卡片变为可点击状态（`cursor-pointer` + `hover:border-slate-600`），用于点击服务卡片自动设置进程类型过滤器。

**Step 3: 验证编译**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -i "error"
```
Expected: no errors

**Step 4: Commit**

```bash
git add frontend/src/components/Tools/SystemMonitor.tsx
git commit -m "feat(system-monitor): 新增服务类型图标映射和 ServiceCard 组件"
```

---

### Task 3: 前端顶部系统信息改为网格卡片

**Files:**
- Modify: `frontend/src/components/Tools/SystemMonitor.tsx:482-503`

**Step 1: 删除旧的 InfoTag 紧凑行，替换为网格卡片**

将第 482-503 行的系统信息紧凑标签行（包含 `InfoTag` 组件的 `<div className="bg-slate-900 rounded-xl p-3 border border-slate-800">` 整块）替换为：

**空间优化**：使用 `p-2.5` 替代 `p-3`，`gap-2` 替代 `gap-3`，`mb-0.5` 替代 `mb-1`，压缩垂直空间约 40px，使网格卡片与紧凑行的空间差距控制在可接受范围内。

```tsx
        {/* 系统信息 — 网格卡片 */}
        {systemInfo && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {/* 主机 */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-server text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">主机</span>
              </div>
              <div className="text-sm text-white font-medium truncate" title={systemInfo.hostname}>
                {systemInfo.hostname}
              </div>
              <div className="text-xs text-slate-600">{systemInfo.platform.split('-')[0]}</div>
            </div>

            {/* 系统 */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-laptop text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">系统</span>
              </div>
              <div className="text-sm text-white font-medium">{osShort}</div>
              <div className="text-xs text-slate-600 truncate" title={systemInfo.os_version}>
                {osVersionShort}
              </div>
            </div>

            {/* CPU */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-microchip text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">CPU</span>
              </div>
              <div className="text-sm text-white font-medium truncate" title={systemInfo.cpu.model}>
                {systemInfo.cpu.model.split('@')[0].trim()}
              </div>
              <div className="text-xs text-slate-600">
                {systemInfo.cpu.physical_cores}C{systemInfo.cpu.logical_cores}T
                {systemInfo.cpu.frequency ? ` · ${(systemInfo.cpu.frequency / 1000).toFixed(1)}GHz` : ''}
              </div>
            </div>

            {/* 内存 */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-memory text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">内存</span>
              </div>
              <div className="text-sm text-white font-medium">{systemInfo.memory.total_gb} GB</div>
              <div className="text-xs text-slate-600">
                {resourceUsage ? `已用 ${resourceUsage.memory.used_gb} GB (${resourceUsage.memory.percent}%)` : '加载中...'}
              </div>
            </div>

            {/* 磁盘 */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-hdd text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">磁盘</span>
              </div>
              <div className="text-sm text-white font-medium">{systemInfo.disk.total_gb} GB</div>
              <div className="text-xs text-slate-600">
                {resourceUsage ? `已用 ${resourceUsage.disk.used_gb} GB (${resourceUsage.disk.percent}%)` : '加载中...'}
              </div>
            </div>

            {/* 启动时间 */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-calendar text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">启动</span>
              </div>
              <div className="text-sm text-white font-medium font-mono">{systemInfo.boot_time.split(' ')[0]}</div>
              <div className="text-xs text-slate-600">{systemInfo.boot_time.split(' ')[1]}</div>
            </div>

            {/* 运行时间 */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-clock text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">运行</span>
              </div>
              <div className="text-sm text-white font-medium">{systemInfo.uptime}</div>
              <div className="text-xs text-slate-600">自启动以来</div>
            </div>

            {/* Python */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-code text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">Python</span>
              </div>
              <div className="text-sm text-white font-medium font-mono">{systemInfo.python_version}</div>
              <div className="text-xs text-slate-600">后端运行时</div>
            </div>
          </div>
        )}
```

**注意**：内存和磁盘卡片的辅助信息改为内联三元表达式（`resourceUsage ? ... : '加载中...'`），确保 `resourceUsage` 为 null 时卡片高度一致，避免布局跳动。

**Step 2: 删除不再需要的 InfoTag 组件**

删除第 218-226 行的 `InfoTag` 组件定义（因为已改为网格卡片，不再需要紧凑标签）。

**Step 3: 验证编译**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -i "error"
```
Expected: no errors

**Step 4: 浏览器验证**

导航到 http://localhost:5178/tools/system-monitor 确认：
- 8 张系统信息卡片显示正确（2行×4列）
- 每张卡片有图标 + 标签 + 主信息 + 辅助信息
- 内存/磁盘卡片首次加载时显示"加载中..."，resourceUsage 到达后自动更新
- 与资源卡片视觉风格统一
- 垂直空间增加在可接受范围内

**Step 5: Commit**

```bash
git add frontend/src/components/Tools/SystemMonitor.tsx
git commit -m "feat(system-monitor): 顶部系统信息改为网格卡片布局"
```

---

### Task 4: 前端新增服务概览卡片行

**Files:**
- Modify: `frontend/src/components/Tools/SystemMonitor.tsx`

**Step 1: 添加 `typeSummary` 状态和 `TypeSummary` 接口**

在 `ProcessListResponse` 接口定义之后（约第 78 行）添加：

```tsx
interface TypeSummary {
  type: string;
  count: number;
  cpu_percent: number;
  memory_percent: number;
  memory_rss: number;
}
```

在 `processTotalPages` state 附近（约第 236 行）添加：

```tsx
  const [typeSummary, setTypeSummary] = useState<TypeSummary[]>([]);
```

**Step 2: 在 `fetchProcesses` 中读取 `type_summary`**

修改 `fetchProcesses` 函数中的数据解析部分（约第 323-326 行）：

```tsx
      const data: ProcessListResponse & { type_summary?: TypeSummary[] } = await res.json();
      setProcesses(data.processes);
      setProcessTotal(data.total);
      setProcessTotalPages(data.total_pages);
      setTypeSummary(data.type_summary || []);
```

**Step 3: 进程类型过滤器联动**

当前代码第 406 行：
```tsx
const availableProjectTypes = KNOWN_PROJECT_TYPES.filter(type => processes.some(p => p.project_type === type));
```
这是基于**分页后**的 `processes` 数据，会随翻页变化。替换为从 `typeSummary` 提取（全量数据，不受分页影响）：

```tsx
const availableProjectTypes = typeSummary.map(s => s.type);
```

不需要 `useMemo`，保持与当前代码风格一致。

**数据一致性说明**：服务概览始终显示全量统计（不受进程类型过滤器和搜索影响），这是设计预期。过滤器只影响进程表格，不影响服务概览卡片行。

**Step 4: 渲染服务概览卡片行**

在资源卡片区块结束处（`</div>` 闭合资源卡片的 `grid` div 之后，约第 643 行之后）插入：

```tsx
        {/* 服务概览 */}
        {typeSummary.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <i className="fas fa-cubes text-violet-400/60 text-xs"></i>
              <span className="text-xs text-slate-500">服务概览 ({typeSummary.length} 种类型)</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
              {typeSummary.map((svc) => (
                <ServiceCard
                  key={svc.type}
                  type={svc.type}
                  count={svc.count}
                  cpuPercent={svc.cpu_percent}
                  memoryRss={svc.memory_rss}
                  onClick={() => {
                    setSelectedProjectType(svc.type);
                    setProcessPage(1);
                  }}
                />
              ))}
            </div>
          </div>
        )}
```

**点击交互**：点击服务卡片自动设置进程类型过滤器为该类型，并跳回第一页，方便用户快速查看某类服务的进程详情。

**Step 5: 验证编译**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -i "error"
```
Expected: no errors

**Step 6: 浏览器验证**

刷新 http://localhost:5178/tools/system-monitor 确认：
- 服务概览卡片行出现在资源卡片下方
- 标题 "服务概览 (N 种类型)" 正确
- 每张卡片显示服务图标、名称、进程数、CPU%、内存
- CPU 颜色按占用程度正确（>50% 红，>20% 橙，其他灰）
- 自适应列数正确（手机 2 列，平板 4 列，桌面 6 列）
- 进程类型过滤器选项与服务概览一致

**Step 7: Commit**

```bash
git add frontend/src/components/Tools/SystemMonitor.tsx
git commit -m "feat(system-monitor): 新增服务概览卡片行"
```

---

### Task 5: 清理无用代码

**Files:**
- Modify: `frontend/src/components/Tools/SystemMonitor.tsx`

**Step 1: 检查并删除不再使用的 `InfoTag` 组件**

确认 `InfoTag` 已删除（在 Task 3 中已处理）。

**Step 2: 验证编译和浏览器**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -i "error"
```
Expected: no errors

**Step 3: Commit（如果有额外修改）**

```bash
git add frontend/src/components/Tools/SystemMonitor.tsx
git commit -m "refactor(system-monitor): 清理无用组件和代码"
```

---

## 执行顺序

1. Task 1 → Task 2 → Task 3 → Task 4 → Task 5
2. 每个 Task 完成后在浏览器中验证再进入下一个
3. 后端改动（Task 1）优先级最高，前端依赖此数据

## 关键补充点

1. **垂直空间优化**：网格卡片使用 `p-2.5`、`gap-2`、`mb-0.5` 压缩内边距和间距，使垂直空间增加控制在 ~40px
2. **内存/磁盘辅助信息**：使用内联三元表达式 `resourceUsage ? ... : '加载中...'` 确保首次加载时卡片高度一致
3. **进程类型过滤器联动**：从 `typeSummary` 提取可用类型（`typeSummary.map(s => s.type)`），确保过滤器与服务概览一致且不受分页影响。当前代码在第 406 行，基于分页后的 `processes`，需要替换
4. **后端聚合性能**：聚合放在排序之前，基于原始进程列表计算，过滤不活跃类型（count ≤ 1 且 cpu < 0.1%）
5. **formatBytes 可访问性**：`formatBytes` 在第 87 行定义（模块级），ServiceCard 在第 227 行插入（模块级），可以正常访问
6. **数据一致性**：服务概览始终显示全量统计，不受进程类型过滤器和搜索影响（设计预期）
7. **服务概览卡片可点击**：点击服务卡片自动设置进程类型过滤器为该类型，并跳回第一页，卡片显示 `cursor-pointer` + `hover:border-slate-600` 交互反馈
