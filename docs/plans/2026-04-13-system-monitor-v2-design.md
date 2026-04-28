# 系统监控页面二次优化设计

**目标**: 将顶部系统信息改为网格卡片布局，并新增服务概览卡片行展示 Java/MySQL/PostgreSQL/Redis 等服务类型汇总信息

**架构**: 后端新增进程类型聚合接口 + 前端纯展示改造，只修改 `SystemMonitor.tsx` 和 `system_monitor_service.py`

**设计原则**: 与资源卡片风格统一，网格化布局，紧凑高密度

---

## 改造清单

### 1. 顶部系统信息卡片化

**当前状态**: flex-wrap 标签行 + `|` 分隔符，2 行展示 8 个字段

**改造方案**:
- 布局: `grid grid-cols-2 md:grid-cols-4 gap-3`，8 张卡片 2 行排列
- 每张卡片内部：
  - 顶部：FontAwesome 图标 + 标签名（`text-xs text-slate-500`）
  - 中间：主信息（`text-sm text-white font-medium`）
  - 底部：辅助信息（`text-xs text-slate-600`，如 CPU 显示物理/逻辑核心数）
- 卡片样式: `bg-slate-900 rounded-xl p-3 border border-slate-800`，与资源卡片完全统一
- 8 张卡片及图标：
  1. 主机（`fa-server`）: 主机名 + 平台信息
  2. 系统（`fa-laptop`）: OS 名称 + 版本号
  3. CPU（`fa-microchip`）: CPU 型号 + 8C16T
  4. 内存（`fa-memory`）: 总容量 32 GB
  5. 磁盘（`fa-hdd`）: 总容量 931.55 GB
  6. 启动时间（`fa-calendar`）: 2026-04-08
  7. 运行时间（`fa-clock`）: 5天5小时
  8. Python（`fa-code`）: 3.12.10

### 2. 服务概览卡片行

**位置**: 资源卡片行（CPU/内存/磁盘/网络/GPU）正下方

**后端改动** (`system_monitor_service.py`):
- `get_process_list()` 返回值新增 `type_summary` 字段
- 聚合逻辑：遍历进程列表，按 `project_type` 分组，统计：
  - `count`: 进程数量
  - `cpu_percent`: 总 CPU 占用（求和）
  - `memory_percent`: 总内存占用（求和）
  - `memory_rss`: 总 RSS（求和，bytes）
- 过滤规则：排除 "Other" 类型，只返回 `count > 0` 的类型
- 排序：按 `cpu_percent` 降序

**前端展示** (`SystemMonitor.tsx`):
- 布局: `grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3` 自适应
- 每张服务卡片：
  - 顶部：服务名称 + 对应图标（Spring Boot→`fa-leaf`，MySQL→`fa-database`，Redis→`fa-bolt`，Node.js→`fa-node-js` 等）
  - 中间：进程数（`text-sm text-white`）
  - 底部：总 CPU%（颜色按占用程度：>50% 红，>20% 橙，其他灰）+ 总内存（格式化显示）
- 卡片样式: `bg-slate-900 rounded-xl p-3 border border-slate-800`，与资源卡片统一
- 标题行: "服务概览" + 类型数量提示

### 3. 服务类型图标映射

前端定义服务类型到 FontAwesome 图标的映射：
- Spring Boot → `fa-leaf` (绿色)
- Java → `fa-coffee` (橙色)
- Node.js → `fa-node-js` (绿色)
- Python → `fa-python` (蓝色)
- MySQL → `fa-database` (蓝色)
- PostgreSQL → `fa-database` (蓝色)
- Redis → `fa-bolt` (红色)
- Nginx → `fa-server` (绿色)
- Docker → `fa-docker` (蓝色)
- Go → `fa-golang` (青色)
- FastAPI → `fa-fire` (橙色)
- 其他 → `fa-cube` (灰色)

### 4. 整体页面结构

```
┌─────────────────────────────────────┐
│ 工具栏（返回 + 标题 | 间隔 | 刷新）  │
├─────────────────────────────────────┤
│ 系统信息卡片 (2行4列，8张卡片)      │
├─────────────────────────────────────┤
│ 资源卡片 (1行4列：CPU/内存/磁盘/网络)│
│ GPU 卡片（如有）                     │
├─────────────────────────────────────┤
│ 服务概览卡片 (1行自适应，N张卡片)   │
├─────────────────────────────────────┤
│ 进程列表（搜索 + 过滤 + 表格 + 分页）│
└─────────────────────────────────────┘
```
