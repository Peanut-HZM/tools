# Redis 工具页面增强设计

**日期**: 2026-05-14
**目标**: 优化 http://localhost:5178/tools/redis-tool，增加批量操作、监控分析、新数据结构支持和运维工具

---

## 现状

Redis 工具当前支持：
- 多连接配置管理（CRUD、分组、连接测试）
- 键值浏览（SCAN、搜索、刷新）
- 数据类型：String、List、Set、ZSet、Hash
- Lua 脚本执行（含模板管理）
- 数据导入导出（JSON）
- CLI 命令执行
- 单键内存分析

**前端布局**: 三栏式（连接列表 | 键列表 | 键详情）
**后端**: 20 个 API 端点，`/redis-tool` 前缀

---

## 设计概览

在键列表区域顶部新增 **Tab 导航**：
- **键值浏览** — 现有功能 + 批量模式
- **监控面板** — 实时指标 + 慢查询
- **运维工具** — 配置管理 + 数据迁移 + 危险操作

右侧 KeyDetail 保持不变，内部按数据类型渲染不同编辑器。

---

## 一、批量操作（键值浏览 Tab）

### UI 设计
- 键列表每行增加 checkbox，顶部出现批量工具栏（进入批量模式时显示）
- 批量模式切换按钮放在搜索框右侧

### 功能
| 操作 | 说明 |
|------|------|
| 批量删除 | 选中后一键删除，显示确认弹窗（含 key 数量和总大小预估） |
| 批量修改 TTL | 统一设置过期时间（秒），或设为永久（PERSIST） |
| 批量重命名 | 前缀替换（如 `old:*` → `new:*`）和正则替换 |
| 批量导出 | 导出选中键为 JSON（复用现有导出功能） |

### 新增 API
```
POST /configs/{id}/keys/batch-ttl    # 批量设置 TTL
POST /configs/{id}/keys/batch-rename # 批量重命名
```
现有 `DELETE /configs/{id}/keys` 已支持批量删除，无需改动。

---

## 二、监控分析面板（监控 Tab）

### 指标卡片（每 5 秒自动刷新）
| 指标 | 数据来源 |
|------|---------|
| 内存使用 | `used_memory` / `used_memory_rss` / `used_memory_peak`，带进度条和百分比 |
| 连接数 | `connected_clients` / `maxclients` |
| 命中率 | `keyspace_hits / (hits + misses)` × 100% |
| OPS | `instantaneous_ops_per_sec` |
| 数据库 Key 分布 | 按 `db` 统计 Key 数量和过期 Key 数量 |

### 慢查询日志面板
- 表格展示 `SLOWLOG GET 50` 结果：命令、耗时、执行时间
- 支持按命令过滤

### 新增 API
```
GET /configs/{id}/monitor        # INFO 解析后的结构化数据
GET /configs/{id}/monitor/slowlog # SLOWLOG GET
```

---

## 三、新数据结构支持

当前 KeyDetail 只支持 String/List/Set/ZSet/Hash 的 JSON 编辑。**新增以下类型的专用渲染器：**

### Stream
- 顶部显示长度（XLEN）、消费者组列表
- 条目表格：ID、字段-值对
- 操作按钮：XADD（新增条目）、XDEL、XTRIM、创建/删除消费者组

### Bitmap
- 可视化位图（0/1 网格），支持翻页查看
- 操作：SETBIT（指定 offset）、BITCOUNT、BITPOS

### HyperLogLog
- 显示基数（PFCOUNT）
- 操作：PFADD、PFMERGE（选择另一个 HLL 合并）

### Geo
- 列表展示成员名称和坐标
- 操作：GEOADD（添加成员+经纬度）、GEODIST（两点距离）、GEORADIUS（按半径搜索）

### 新增 API
```
GET    /configs/{id}/keys/{key}/stream      # XRANGE - + 获取全部
POST   /configs/{id}/keys/{key}/stream      # XADD / XDEL / XGROUP
GET    /configs/{id}/keys/{key}/bitmap      # BITCOUNT + 分段数据
POST   /configs/{id}/keys/{key}/bitmap      # SETBIT
GET    /configs/{id}/keys/{key}/hyperloglog # PFCOUNT
POST   /configs/{id}/keys/{key}/hyperloglog # PFADD / PFMERGE
GET    /configs/{id}/keys/{key}/geo         # GEOPOS 全部成员
POST   /configs/{id}/keys/{key}/geo         # GEOADD / GEODIST / GEORADIUS
```

---

## 四、运维工具（运维 Tab）

### 配置管理
- 表格展示 `CONFIG GET *` 结果（支持搜索过滤）
- 可修改的配置项直接内联编辑，调用 `CONFIG SET`
- 危险配置项（如 `requirepass`）二次确认

### 数据迁移
- 向导式界面：源连接（下拉选择已有配置）→ 目标连接 → Pattern 过滤 → 预览 Key 列表 → 执行迁移
- 支持 `REPLACE` 和 `NX` 模式

### 复制信息
- `INFO replication` 结构化展示：角色（master/slave）、连接状态、同步偏移量、延迟

### 危险操作（带红色警告和二次确认）
- FLUSHDB（清空当前 DB）
- FLUSHALL（清空全部 DB）

### 大 Key 扫描
- 调用 `MEMORY USAGE` 遍历，找出 Top N 大 Key
- 按内存排序表格展示

### 新增 API
```
GET    /configs/{id}/config        # CONFIG GET *
POST   /configs/{id}/config        # CONFIG SET key value
GET    /configs/{id}/replication   # INFO replication
POST   /configs/{id}/flush         # FLUSHDB / FLUSHALL
POST   /configs/{id}/migrate       # 数据迁移
GET    /configs/{id}/bigkeys       # 大 Key 扫描
```

---

## 文件变更清单

### 前端新增文件
- `frontend/src/components/Tools/RedisTool/BatchToolbar.tsx`
- `frontend/src/components/Tools/RedisTool/MonitorPanel.tsx`
- `frontend/src/components/Tools/RedisTool/OperationsPanel.tsx`
- `frontend/src/components/Tools/RedisTool/StreamEditor.tsx`
- `frontend/src/components/Tools/RedisTool/BitmapEditor.tsx`
- `frontend/src/components/Tools/RedisTool/HyperLogLogEditor.tsx`
- `frontend/src/components/Tools/RedisTool/GeoEditor.tsx`
- `frontend/src/components/Tools/RedisTool/MigrateWizard.tsx`

### 前端修改文件
- `frontend/src/components/Tools/RedisTool/RedisTool.tsx` — 增加 Tab 导航
- `frontend/src/components/Tools/RedisTool/KeyExplorer.tsx` — 增加批量模式
- `frontend/src/components/Tools/RedisTool/KeyDetail.tsx` — 增加类型分发
- `frontend/src/api/redisToolApi.ts` — 增加新 API 调用

### 后端修改文件
- `backend/app/routes/redis_tool.py` — 增加约 15 个端点
- `backend/app/services/redis_tool_service.py` — 增加业务逻辑
- `backend/app/models/redis_tool_models.py` — 增加请求/响应模型

---

## 验证标准

- [ ] 键列表支持多选，批量删除/TTL/重命名/导出正常工作
- [ ] 监控面板实时刷新，指标数据正确
- [ ] Stream/Bitmap/HyperLogLog/Geo 类型能正确展示和编辑
- [ ] 运维工具中配置管理、数据迁移、复制信息、FLUSH 操作正常
- [ ] 浏览器 Console 无报错，页面热加载正常
