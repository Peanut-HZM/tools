# 服务器监控子项目设计文档

**日期**: 2026-08-15
**状态**: 已评审通过
**目标**: 将现有「系统监控」工具升级为对标宝塔/1Panel 监控模块的多服务器监控体系，作为完整服务器管理面板的第一个子项目

---

## 1. 背景与目标

现有「系统监控」工具（`backend/app/services/system_monitor_service.py` + `frontend/src/components/Tools/SystemMonitor.tsx`）仅支持本机实时监控，具备系统信息、资源占用（CPU/内存/交换分区/磁盘/网络/磁盘IO/GPU）、进程列表（排序/搜索/项目类型过滤/分页/结束进程）功能。

本次升级目标：
1. 支持监控多台远程 Linux 服务器（对标宝塔/1Panel 监控模块）
2. 历史趋势图表（时间范围选择、降采样）
3. 进程/服务管理能力（远程）
4. 告警规则与通知（Webhook + 站内通知）
5. 现有本机监控整合进同一套页签体系

**定位**: 这是「完整服务器管理面板」规划的第一个子项目。后续子项目（文件管理、防火墙、计划任务、网站管理等）独立规划推进。

---

## 2. 关键决策（已与用户确认）

| 决策点 | 结论 |
|--------|------|
| 采集方式 | SSH 无代理采集（paramiko 执行内嵌 bash 脚本） |
| 采集频率 | 30 秒/次 |
| 数据保留 | 7 天（每日清理） |
| 服务器管理 | 独立 `monitor_servers` 表，支持从 SSH 配置一键导入，本机为内置节点 |
| 告警通知 | 通用 Webhook（兼容钉钉/企业微信/飞书格式）+ 站内通知，本轮不做邮件 |
| 页签结构 | 六页签：服务器列表/总览/历史趋势/进程/服务/告警，现有系统监控页合并进新结构 |
| 采集架构 | 方案 A：单 asyncio 后台任务轮询 + 内嵌 bash 脚本一次采集 |

---

## 3. 数据模型

### 3.1 `monitor_servers`（监控服务器，per-user）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | UUID |
| user_id | VARCHAR(64) | 所属用户（FK users） |
| name | VARCHAR(64) | 服务器别名 |
| server_type | VARCHAR(16) | `local`（本机）/ `ssh`（远程） |
| host | VARCHAR(255) | 远程地址（local 时为空） |
| port | INT | 默认 22 |
| username | VARCHAR(128) | SSH 用户名 |
| password_encrypted | TEXT | 密码（复用现有 EncryptionUtils 加密） |
| private_key_encrypted | TEXT | 私钥 |
| passphrase_encrypted | TEXT | 私钥口令 |
| source_ssh_id | VARCHAR(64) | 可选：从哪个 SSH 配置导入（引用 ssh_configs.id） |
| group_name | VARCHAR(64) | 分组 |
| status | VARCHAR(16) | `online` / `offline` / `error` / `disabled` |
| last_error | TEXT | 最近一次采集错误信息（卡片上展示） |
| last_seen_at | TIMESTAMP | 最近成功采集时间 |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |
| deleted | BOOLEAN | 软删除，默认 FALSE |

规则：
- 首次初始化自动插入一条 `local` 类型记录（本机），不可删除但可禁用（`disabled`）
- 导入 SSH 配置时复制连接凭据，后续独立管理，与 ssh_configs 解耦

### 3.2 `monitor_metrics`（时序指标）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL PK | |
| server_id | VARCHAR(64) | |
| collected_at | TIMESTAMP | 采集时间 |
| cpu_percent | FLOAT | 总 CPU 使用率 |
| cpu_per_core | JSONB | 各核心使用率数组 |
| load_avg | JSONB | 1/5/15 分钟负载 [l1, l5, l15] |
| mem_total | BIGINT | 内存总量 bytes |
| mem_used | BIGINT | 已用 bytes |
| mem_percent | FLOAT | 使用率 |
| swap_total | BIGINT | |
| swap_used | BIGINT | |
| swap_percent | FLOAT | |
| disk_total | BIGINT | 根分区总量 |
| disk_used | BIGINT | 已用 |
| disk_percent | FLOAT | |
| net_recv_rate | FLOAT | 网络接收速率 B/s |
| net_sent_rate | FLOAT | 网络发送速率 B/s |
| disk_read_rate | FLOAT | 磁盘读速率 B/s |
| disk_write_rate | FLOAT | 磁盘写速率 B/s |
| process_count | INT | 进程数 |
| uptime_seconds | BIGINT | 运行时长 |

索引：`(server_id, collected_at)`。磁盘分区明细不落库（变化小，实时查询）。

### 3.3 `monitor_alerts`（告警规则，per-user）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | |
| user_id | VARCHAR(64) | |
| server_id | VARCHAR(64) | `all` 表示全部服务器 |
| metric | VARCHAR(32) | `cpu_percent` / `memory_percent` / `disk_percent` / `load_avg` / `net_recv_rate` / `net_sent_rate` |
| operator | VARCHAR(8) | `>` / `<` / `>=` / `<=` |
| threshold | FLOAT | 阈值 |
| duration | INT | 持续 N 次采样才触发（防抖动），默认 3 |
| enabled | BOOLEAN | 默认 TRUE |
| created_at | TIMESTAMP | |

触发去重：同规则同服务器进入 `firing` 状态后不再重复通知，指标恢复后重置为待触发。

### 3.4 `monitor_alert_logs`（触发记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL PK | |
| rule_id | VARCHAR(64) | |
| server_id | VARCHAR(64) | |
| server_name | VARCHAR(64) | 快照，防止服务器改名后无法追溯 |
| metric | VARCHAR(32) | |
| actual_value | FLOAT | 触发时的实际值 |
| status | VARCHAR(16) | `firing` / `recovered` |
| is_read | BOOLEAN | 站内通知已读标记，默认 FALSE |
| notified_at | TIMESTAMP | |

---

## 4. 后端架构

### 4.1 模块结构

```
backend/app/services/monitor/
├── __init__.py
├── collector.py        # 采集引擎（asyncio 后台任务）
├── script.py           # 内嵌 bash 采集脚本（模板字符串）+ 输出解析纯函数
├── ssh_client.py       # paramiko 连接封装（连接复用 LRU、超时、重连）
├── metric_repo.py      # 时序数据写入/查询/降采样/清理（PostgreSQL）
├── alert_engine.py     # 告警规则评估与去重
├── server_service.py   # 监控服务器 CRUD + SSH 导入 + 凭据加密
└── webhook_notify.py   # Webhook 推送（钉钉/企业微信/飞书兼容格式）
```

模型文件：`backend/app/models/monitor_models.py`（沿用现有 SQLAlchemy-free 手写 SQL + psycopg2 模式，参考 `ssh_tool_models.py`）。
路由文件：`backend/app/routes/monitor.py`。

### 4.2 采集引擎流程

- FastAPI `startup` 事件启动单例 asyncio 后台任务，每 30s 一个周期
- 每周期：
  1. 加载所有 `enabled` 服务器（含 local）
  2. 本机：复用 `system_monitor_service.py` 的 psutil 逻辑，组装相同指标格式
  3. 远程：paramiko 执行内嵌 bash 脚本（10s 超时），解析单行 JSON
  4. 写入 `monitor_metrics`
  5. 更新 `monitor_servers.status` / `last_seen_at` / `last_error`
  6. 失败重试 1 次，仍失败标记 `offline`
  7. 采样结果送入 `alert_engine` 评估
- 单台失败隔离：`asyncio.gather` + 逐台 try/except，互不影响
- 服务器数量较多时（>5 台）可用 `asyncio.gather` 并发采集；当前串行即可（单台 <1s）

### 4.3 SSH 连接复用

- `ssh_client.py` 维护按 `server_id` 的 LRU 连接缓存（上限 8 个）
- 空闲 5 分钟关闭；命令执行失败自动重连一次
- 所有凭据解密后不落日志

### 4.4 内嵌 bash 采集脚本

约 100 行 bash，一次 `exec_command` 输出单行 JSON，不依赖 vmstat/iostat/psutil：
- CPU：`/proc/stat` 两次采样（间隔 200ms）计算各核心与总使用率
- 内存：`/proc/meminfo`（MemTotal/MemAvailable/swap）
- 负载：`/proc/loadavg`
- 网络速率：`/proc/net/dev` 两次采样差值（按接口汇总，排除 loopback）
- 磁盘速率：`/proc/diskstats` 两次采样差值（汇总所有物理盘）
- 磁盘容量：`df -P`（根分区）
- 进程数：`/proc` 下 PID 数量统计
- 运行时长：`/proc/uptime`
- 输出格式：`MONITOR_DATA_BEGIN<json>MONITOR_DATA_END`，解析时取中间段，防脚本错误输出混入

### 4.5 API 路由（`/monitor` 前缀）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/monitor/servers` | 服务器列表（含分组、实时状态） |
| POST | `/monitor/servers` | 新建监控服务器 |
| PUT | `/monitor/servers/{id}` | 更新（凭据、分组、启停） |
| DELETE | `/monitor/servers/{id}` | 删除（软删除） |
| POST | `/monitor/servers/import-ssh` | 从 SSH 配置导入（body: ssh_config_id） |
| POST | `/monitor/servers/{id}/retry` | 手动重试采集（error 状态恢复） |
| GET | `/monitor/servers/{id}/overview` | 当前实时状态（失败降级返回最近缓存） |
| GET | `/monitor/servers/{id}/metrics?range=1h\|6h\|24h\|7d` | 历史趋势（7d 按小时降采样聚合） |
| GET | `/monitor/servers/{id}/partitions` | 磁盘分区明细（实时） |
| GET | `/monitor/servers/{id}/processes` | 远程进程列表（ps 命令，支持搜索/排序/分页） |
| POST | `/monitor/servers/{id}/processes/{pid}/kill` | 结束远程进程 |
| GET | `/monitor/servers/{id}/services` | systemd 服务列表 |
| POST | `/monitor/servers/{id}/services/{name}/action` | start/stop/restart（body: action） |
| GET | `/monitor/servers/{id}/privileges` | sudo 可用性检测 |
| GET | `/monitor/alerts` | 告警规则列表 |
| POST | `/monitor/alerts` | 新建规则 |
| PUT | `/monitor/alerts/{id}` | 更新规则 |
| DELETE | `/monitor/alerts/{id}` | 删除规则 |
| GET | `/monitor/alerts/logs` | 触发记录（分页） |
| PUT | `/monitor/alerts/logs/read` | 标记全部触发记录已读 |
| GET/PUT | `/monitor/settings` | 监控设置（Webhook 地址、采集间隔等） |

### 4.6 告警引擎

- 每次采样完成后，对每条 enabled 规则评估
- 满足条件且连续 `duration` 次 → 触发：写 `monitor_alert_logs(firing)` + 推送 Webhook + 存站内通知
- 触发后进入去重状态，同规则同服务器不再重复推送（即使仍超阈值），直到指标恢复正常（写 `recovered` 记录）
- Webhook 推送格式：`{"msgtype": "markdown", "markdown": {"content": "..."}}`，兼容钉钉/企业微信/飞书机器人；发送失败记日志不阻塞采集
- 站内通知：复用 `monitor_alert_logs` 记录（新增 `is_read` 字段标记已读），前端 Alerts 页签轮询未读记录显示红点标记（页签①服务器列表顶部「告警」入口 + 页签⑥触发记录时间线），点击后调用 `PUT /monitor/alerts/logs/read` 标记已读；不额外建通知表，不引入全局角标（后续子项目如有全局通知需求再规划）

### 4.7 权限处理（服务管理）

- 服务启停执行 `sudo -n systemctl ...`（要求无密码 sudo），失败返回明确提示
- `privileges` 接口执行 `sudo -n true` 检测可用性
- 远程进程 kill 执行 `kill -9 <pid>`（当前用户可 kill 自己的进程）

### 4.8 清理任务

- 每 6 小时执行 `DELETE FROM monitor_metrics WHERE collected_at < now() - interval '7 days'`
- 数据量估算：单服务器 2880 条/天，7 天约 2 万条；10 台约 20 万条，PostgreSQL 无压力

### 4.9 关键日志（遵循 AGENTS.md 规范）

- 采集周期开始/结束（服务器数量、成功数、失败数、耗时）
- 单台服务器采集失败：错误信息（首次 + 状态变化时，避免重复刷屏）
- 告警触发/恢复/Webhook 推送结果
- 清理任务执行结果
- 所有日志中文

---

## 5. 前端架构

### 5.1 目录结构

```
frontend/src/components/Tools/SystemMonitor/
├── index.tsx              # 主容器：页签栏 + 选中服务器 + 路由状态
├── ServerList.tsx         # 页签①：服务器列表
├── Overview.tsx           # 页签②：总览（实时仪表盘）
├── History.tsx            # 页签③：历史趋势
├── Processes.tsx          # 页签④：进程管理
├── Services.tsx           # 页签⑤：服务管理
├── Alerts.tsx             # 页签⑥：告警设置
└── components/
    ├── ServerCard.tsx     # 服务器状态卡片
    ├── MetricChart.tsx    # 通用趋势图封装（recharts）
    ├── ServerSelector.tsx # 服务器选择器
    ├── ResourceCards.tsx  # 资源卡片（从现有 SystemMonitor.tsx 提取复用）
    ├── SystemInfoCards.tsx # 系统信息卡片（提取复用）
    └── AddServerModal.tsx # 添加服务器弹窗（手动/导入 SSH）
```

原 `SystemMonitor.tsx` 拆分迁移，组件按 K8sTool 目录模式组织。

### 5.2 页签交互

1. **服务器列表**：状态卡片网格（名称/分组/状态灯/CPU/内存/磁盘/网络小指标/最后采集时间/错误信息），点击进入详情页签；「添加服务器」弹窗（手动填写 或 选择 SSH 配置导入）；error 状态卡片显示「重试」按钮
2. **总览**：系统信息卡片（8 张网格）+ 资源卡片（CPU/内存/磁盘/网络/磁盘IO/GPU）+ 实时刷新（5s 轮询），数据源按选中服务器切换（local 用 psutil 接口，ssh 用监控接口）；GPU 卡片仅本机模式显示（远程 bash 脚本不采集 GPU）
3. **历史趋势**：时间范围选择（实时/1h/6h/24h/7d）+ 指标组切换（CPU/内存/磁盘IO/网络IO/负载），recharts 折线图；7d 范围后端按小时聚合
4. **进程管理**：现有进程表格改造，数据源切到监控 API；保留搜索/排序/项目类型/分页/结束进程；远程模式项目类型检测退化为按进程名+命令路径匹配
5. **服务管理**：systemd 服务列表（服务名/状态/描述/最近激活时间），启停/重启按钮 + 确认弹窗；无权限时展示提示
6. **告警设置**：规则列表 + 新建/编辑表单（指标/操作符/阈值/持续时间/服务器范围）+ Webhook 配置区 + 触发记录时间线（含未读红点）

### 5.3 状态管理与数据请求

- 新增 zustand store：`monitorStore`（服务器列表缓存、当前选中服务器 id、当前页签、轮询控制）
- 新增 `frontend/src/api/monitorApi.ts`（axios 封装，参照现有 api 模式）
- 轮询策略：服务器列表页 10s、总览页 5s、进程/服务页 10s、历史页不轮询；页面隐藏时暂停（复用现有 hooks 模式）

---

## 6. 错误处理与运维

| 场景 | 处理 |
|------|------|
| SSH 连接失败 | 重试 1 次 → 标记 offline + 记录 last_error（显示在卡片）→ 下周期自动重试 |
| 认证失败/权限不足 | 标记 offline + 明确错误信息；连续失败 10 次 → 暂停采集（status=error），需手动重试 |
| 脚本输出解析失败 | 丢弃该次数据，记录警告日志 |
| 单台失败 | 隔离处理，不影响其他服务器 |
| 服务启停无权限 | 返回明确提示（需要 root 或无密码 sudo） |
| Webhook 推送失败 | 记录日志，不阻塞采集；站内通知仍保留 |
| 数据库写入失败 | 记录错误日志，本轮数据丢弃，不重试（避免积压） |

---

## 7. 测试策略

### 7.1 后端（pytest）

- `script.py`：bash 脚本输出解析纯函数测试（mock 命令输出，覆盖 CentOS/Ubuntu 格式差异、字段缺失、异常格式、带前缀校验）
- `collector.py`：mock paramiko，测试成功/失败/超时/重试/离线标记/降级缓存
- `ssh_client.py`：连接复用 LRU、空闲关闭、断线重连
- `metric_repo.py`：临时 PostgreSQL（或 mock）测试写入/查询/降采样/清理
- `alert_engine.py`：规则触发/连续次数/去重/恢复/Webhook 调用（mock）
- `server_service.py`：CRUD + SSH 导入 + 凭据加密解密
- API 路由：TestClient 集成测试

### 7.2 前端（vitest + Testing Library）

- MetricChart 渲染（mock recharts）
- 页签切换、ServerSelector 交互、AddServerModal 表单校验
- Alerts 规则表单校验、触发记录渲染
- 现有 SystemMonitor 相关测试迁移适配

---

## 8. 兼容性与迁移

- 现有 `system-monitor/info`、`system-monitor/usage`、`system-monitor/processes` API 保留（本机模块继续使用），新监控模块提供本地数据源时复用 `system_monitor_service.py`
- 现有 SystemMonitor 页面组件迁移后，`/tools/system-monitor` 路由指向新 index.tsx，旧文件删除
- 原有进程「项目类型检测」逻辑保留用于本机模式

---

## 9. 范围外（后续子项目规划）

- 文件管理（Web 文件管理器）
- 防火墙管理
- 计划任务（Cron）
- 网站/域名/SSL 管理
- 邮件告警
- 多语言国际化完善（现有 i18n 框架需补充监控模块文案）
