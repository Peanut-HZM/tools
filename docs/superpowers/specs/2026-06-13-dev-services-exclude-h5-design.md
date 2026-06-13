---
author: Peanut
created_at: 2026-06-13
purpose: 设计 dev-services.py 的默认排除 mini-program H5 服务方案，使 start/restart/stop 默认只操作 backend + frontend
---

# dev-services.py 默认排除 H5 服务设计

## 1. 背景与目标

`dev-services.py` 是一个通用服务管理脚本（2100+ 行），通过递归扫描当前目录（深度 3 层）自动发现 Vite / Taro / UniApp / Next.js / Python / Spring Boot / Node.js 等各类服务。

在 `tools/` 项目根目录下运行默认命令时，脚本会扫描到：

| 目录 | 类型 | 说明 |
|------|------|------|
| `backend/` | Python FastAPI | 后端，端口 19092 |
| `frontend/` | Vite React | 管理后台前端，端口 5178 |
| `mini-program/` | Taro H5 | 小程序 H5，端口 5173 |
| `tools-mini-program/` | Taro H5 | 另一个 Taro 项目（可能） |

**当前问题**：`start` / `restart` / `stop` 默认启动所有服务，包括日常开发中很少用到的 mini-program H5，浪费资源并拖慢启动速度。

**目标**：默认只操作 backend + frontend，mini-program H5 仅在用户显式声明时才启动。

## 2. 方案选型

经过 3 种方案的对比，选择**方案 B：`--exclude` / `--include` 通用标志 + 默认排除列表**。

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A | `DEFAULT_EXCLUDE_DIRS` 常量 + `--all` | 最简单 | 不灵活，新增排除项需改常量 |
| **B ✅** | **`--exclude` / `--include` 标志 + 默认排除列表** | **通用、可扩展、符合脚本定位** | **多两个 CLI 参数** |
| C | 专用 `--h5` 标志 | 语义明确 | 不通用，未来无法复用 |

## 3. 命令行接口

新增 3 个 CLI 参数，与现有 `--type` / `--port` 平级：

```bash
# 默认：排除 mini-program 相关目录
python dev-services.py start

# 恢复全扫描（启动所有服务）
python dev-services.py start --all

# 仅把 mini-program 从排除列表移除
python dev-services.py start --include mini-program

# 在默认排除基础上再排除 frontend
python dev-services.py start --exclude frontend

# 全扫描但排除 logs
python dev-services.py start --all --exclude logs

# 查看被默认排除的服务
python dev-services.py discover --all
```

**参数规格**：

| 参数 | 类型 | 重复 | 说明 |
|------|------|------|------|
| `--all` | flag | 否 | 清空默认排除列表，恢复全扫描 |
| `--exclude <dir>` | str | 是（append） | 追加排除指定目录名 |
| `--include <dir>` | str | 是（append） | 从排除列表中移除指定目录名 |

- 参数值是**目录名**（如 `mini-program`），不是服务类型，不是完整路径
- 这 3 个标志对所有命令生效：`start` / `stop` / `restart` / `status` / `kill` / `logs` / `discover`

## 4. 排除集合计算规则

排除集合（`exclude_dirs`）按以下顺序计算：

```python
# 1. 初始值：默认排除列表
effective = set(DEFAULT_EXCLUDE_DIRS)

# 2. --all：清空默认排除
if args.all:
    effective = set()

# 3. --exclude：追加用户排除项
for d in (args.exclude or []):
    effective.add(d.lower())

# 4. --include：移除指定目录（优先级高于 --exclude）
for d in (args.include or []):
    effective.discard(d.lower())
```

**关键规则**：

1. **`--all` 优先级**：高于 `DEFAULT_EXCLUDE_DIRS`，但低于 `--exclude`
   - `--all` 清空默认排除，但 `--all --exclude X` 时 X 仍被排除
2. **`--include` 优先级高于 `--exclude`**：显式包含的意图更明确
   - `--exclude foo --include foo` 最终 foo **不被排除**
3. **静默忽略**：未命中已知目录的 `--include` / `--exclude` 值不报错
4. **大小写不敏感**：比较时统一用目录名小写

## 5. 服务发现逻辑改动

### 5.1 函数签名

```python
def discover_services(
    root_dir: Optional[Path] = None,
    max_depth: int = MAX_SCAN_DEPTH,
    exclude_dirs: Optional[set[str]] = None,   # 新增
) -> list[Service]:
    ...

def _scan_directory(
    current: Path,
    root: Path,
    max_depth: int,
    services: list,
    exclude_dirs: set[str],                    # 新增
):
    ...
```

### 5.2 排除检查点

在 `_scan_directory()` 中，现有 `SKIP_DIRS` 检查之后，新增排除逻辑：

```python
# 现有：跳过黑名单目录
if current != root and (current.name in SKIP_DIRS or current.name in AUXILIARY_DIRS):
    return

# 新增：跳过用户排除的目录
if current != root and current.name.lower() in exclude_dirs:
    return
```

**关键点**：

- 排除检查在**进入目录之前**发生，被排除目录内部的任何服务都不会被发现
- 排除基于**目录名**（`current.name.lower()`），不是完整路径——与 `SKIP_DIRS` 模式一致
- `current != root` 条件确保 `root_dir` 本身不受排除影响

### 5.3 target 参数的优先级

当用户用 `target` 位置参数直接指定目录作为 `root_dir` 时（如 `dev-services start mini-program`），`exclude_dirs` **不适用**于 `root_dir` 本身，只对 `root_dir` 的子目录生效。

**理由**：`target` 的显式意图优先——用户明确指定"扫描这个目录"，不应被默认排除覆盖。

## 6. 常量定义

在 `SKIP_DIRS` / `AUXILIARY_DIRS` 附近新增：

```python
# 默认排除的服务目录（仅当用户显式 --include 或 --all 时才扫描）
DEFAULT_EXCLUDE_DIRS = {"mini-program", "tools-mini-program"}
```

## 7. 代码改动点

共 5 处改动，都是小改动：

| # | 位置 | 改动 |
|---|------|------|
| 1 | 常量区（L52-56 附近） | 新增 `DEFAULT_EXCLUDE_DIRS` 常量 |
| 2 | `_scan_directory()`（L166） | 签名加 `exclude_dirs: set[str]`，跳过逻辑加 2 行 |
| 3 | `discover_services()`（L158） | 签名加 `exclude_dirs`，透传给 `_scan_directory` |
| 4 | `argparse` 区（L1956-1971） | 新增 `--all`、`--exclude`、`--include` 三个参数定义 |
| 5 | `main()` 服务发现前（L1988 附近） | 计算 `effective_exclude`，传入 `discover_services` |

## 8. 向后兼容性

| 命令 | 行为变化 |
|------|----------|
| `dev-services.py start` | **变化**：不再启动 mini-program（本次需求核心） |
| `dev-services.py restart` | **变化**：不再重启 mini-program |
| `dev-services.py stop` | **变化**：不会停止 mini-program（若已在运行） |
| `dev-services.py status` | **变化**：不显示 mini-program（用 `--all` 查看） |
| `dev-services.py --type vite` | 不变：`--type` 过滤在发现之后，互不干扰 |
| `dev-services.py start mini-program` | **不变**：target 指定根目录，仍可单独启动 H5 |
| `dev-services.py start --all` | **不变**：完全恢复旧行为，启动所有服务 |
| `dev-services.py kill all` | **变化**：不会强杀 mini-program（用 `--all` 包含） |

**破坏性变更**：`start` / `restart` / `stop` 的默认行为变化。用户若依赖"默认启动所有"，需改用 `--all`。

## 9. 测试要点

实现后需验证：

1. `dev-services.py discover` — 只输出 backend + frontend
2. `dev-services.py discover --all` — 输出包含 mini-program
3. `dev-services.py discover --include mini-program` — 输出包含 mini-program
4. `dev-services.py start` — 只启动 backend + frontend，mini-program 端口未被占用
5. `dev-services.py start --all` — 启动所有服务
6. `dev-services.py start mini-program` — 单独启动 mini-program（target 作为 root_dir）
7. `dev-services.py start --exclude backend` — 只启动 frontend（mini-program 仍被排除）
8. `dev-services.py start --all --exclude mini-program` — 启动除 mini-program 外的所有服务
9. `dev-services.py start --exclude foo --include foo` — foo 不被排除（`--include` 优先）
10. `dev-services.py status --all` — 显示所有服务状态

## 10. 未来扩展

此设计为"通用服务管理脚本"留好了扩展点：

- 若后续新增其他"可选"项目（如移动端 App、文档站点），只需追加到 `DEFAULT_EXCLUDE_DIRS`
- 若需要按"角色"分组启动（如 `--group core` / `--group full`），可在本设计基础上再加 `--group` 参数
- 若需要持久化排除配置（如 `.dev-services.json`），可将 `effective_exclude` 的计算逻辑扩展为从配置文件读取
