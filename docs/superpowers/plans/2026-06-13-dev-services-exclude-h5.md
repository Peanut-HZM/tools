---
author: Peanut
created_at: 2026-06-13
purpose: dev-services.py 默认排除 H5 服务的实现计划
---

# dev-services.py 默认排除 H5 服务 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `dev-services.py` 默认跳过 mini-program H5 相关目录，仅在用户显式声明时才启动。

**Architecture:** 新增 `DEFAULT_EXCLUDE_DIRS` 常量作为默认排除集合，通过新增的 `--all` / `--exclude` / `--include` CLI 参数动态调整。排除集合透传到 `discover_services()` → `_scan_directory()`，在进入目录前按目录名跳过。

**Tech Stack:** Python 3.10+, argparse, pathlib（脚本自身无外部依赖新增）

**规范文档:** `docs/superpowers/specs/2026-06-13-dev-services-exclude-h5-design.md`

---

## 文件改动清单

| 文件 | 操作 | 职责 |
|------|------|------|
| `dev-services.py` | 修改 | 唯一被修改的源码文件，5 处改动 |
| `tests/test_dev_services_exclude.py` | 新建 | 排除集合计算逻辑的单元测试 |

---

### Task 1: 新增 `DEFAULT_EXCLUDE_DIRS` 常量

**Files:**
- Modify: `dev-services.py:52-56`（`SKIP_DIRS` / `AUXILIARY_DIRS` 附近）

- [ ] **Step 1: 在 `AUXILIARY_DIRS` 定义之后添加常量**

在 `dev-services.py` 中找到：

```python
AUXILIARY_DIRS = {"tools", "scripts", "script", "bin", ".superpowers", ".gstack"}
```

在其**下一行**插入：

```python
# 默认排除的服务目录（仅当用户显式 --include 或 --all 时才扫描）
DEFAULT_EXCLUDE_DIRS = {"mini-program", "tools-mini-program"}
```

- [ ] **Step 2: 验证脚本仍可正常运行**

```bash
python dev-services.py discover
```

预期：输出与修改前完全一致（新常量尚未被引用，行为不变）。

- [ ] **Step 3: 提交**

```bash
git add dev-services.py
git commit -m "feat(dev-services): 新增 DEFAULT_EXCLUDE_DIRS 常量"
```

---

### Task 2: 修改 `_scan_directory` 支持排除集

**Files:**
- Modify: `dev-services.py:166-189`（`_scan_directory` 函数）

- [ ] **Step 1: 修改函数签名，添加 `exclude_dirs` 参数**

将函数签名从：

```python
def _scan_directory(current: Path, root: Path, max_depth: int, services: list):
```

改为：

```python
def _scan_directory(current: Path, root: Path, max_depth: int, services: list, exclude_dirs: Optional[set[str]] = None):
```

- [ ] **Step 2: 在函数体开头的 `SKIP_DIRS` 检查之后，添加排除逻辑**

找到现有跳过逻辑：

```python
    # 跳过黑名单
    if current != root and (current.name in SKIP_DIRS or current.name in AUXILIARY_DIRS):
        return
```

在其**紧下方**插入：

```python
    # 跳过用户排除的目录
    if exclude_dirs and current != root and current.name.lower() in exclude_dirs:
        return
```

> **要点**：`current != root` 确保 `target` 指定的根目录不受排除影响（设计第 5.3 节）。

- [ ] **Step 3: 验证脚本仍可正常运行**

```bash
python dev-services.py discover
```

预期：输出与修改前完全一致（`exclude_dirs` 默认 `None`，新逻辑不触发）。

- [ ] **Step 4: 提交**

```bash
git add dev-services.py
git commit -m "feat(dev-services): _scan_directory 支持 exclude_dirs 参数"
```

---

### Task 3: 修改 `discover_services` 透传排除集

**Files:**
- Modify: `dev-services.py:158-163`（`discover_services` 函数）

- [ ] **Step 1: 修改函数签名，添加 `exclude_dirs` 参数**

将：

```python
def discover_services(root_dir: Optional[Path] = None, max_depth: int = MAX_SCAN_DEPTH) -> list[Service]:
    """递归扫描目录，发现所有服务"""
    base = root_dir or CWD
    services = []
    _scan_directory(base, base, max_depth, services)
    return services
```

改为：

```python
def discover_services(root_dir: Optional[Path] = None, max_depth: int = MAX_SCAN_DEPTH, exclude_dirs: Optional[set[str]] = None) -> list[Service]:
    """递归扫描目录，发现所有服务"""
    base = root_dir or CWD
    services = []
    _scan_directory(base, base, max_depth, services, exclude_dirs or set())
    return services
```

- [ ] **Step 2: 验证脚本仍可正常运行**

```bash
python dev-services.py discover
```

预期：输出与修改前完全一致。

- [ ] **Step 3: 提交**

```bash
git add dev-services.py
git commit -m "feat(dev-services): discover_services 透传 exclude_dirs"
```

---

### Task 4: 新增 CLI 参数 `--all` / `--exclude` / `--include`

**Files:**
- Modify: `dev-services.py:1969-1971`（argparse 参数定义区）

- [ ] **Step 1: 在 `--foreground` 参数定义之后添加 3 个新参数**

找到：

```python
    parser.add_argument("--foreground", "-f", action="store_true", help="前台模式运行")
```

在其**紧下方**插入：

```python
    parser.add_argument("--all", action="store_true", help="清空默认排除列表，扫描所有目录")
    parser.add_argument("--exclude", action="append", metavar="DIR", help="追加排除指定目录名（可多次使用）")
    parser.add_argument("--include", action="append", metavar="DIR", help="从排除列表中移除指定目录名（可多次使用，优先级高于 --exclude）")
```

- [ ] **Step 2: 验证参数解析无报错**

```bash
python dev-services.py discover --help
```

预期：帮助信息中出现 `--all`、`--exclude DIR`、`--include DIR` 三个新选项。

- [ ] **Step 3: 提交**

```bash
git add dev-services.py
git commit -m "feat(dev-services): 新增 --all/--exclude/--include CLI 参数"
```

---

### Task 5: 在 `main()` 中计算 `effective_exclude` 并透传

**Files:**
- Modify: `dev-services.py:1987-1989`（`main()` 中调用 `discover_services` 之前）

- [ ] **Step 1: 在 `discover_services` 调用之前插入排除集合计算逻辑**

找到：

```python
    # 发现服务
    services = discover_services(root_dir=root_dir)
```

替换为：

```python
    # 计算有效排除集合
    effective_exclude = set(DEFAULT_EXCLUDE_DIRS)
    if args.all:
        effective_exclude = set()
    for d in (args.exclude or []):
        effective_exclude.add(d.lower())
    for d in (args.include or []):
        effective_exclude.discard(d.lower())

    # 发现服务
    services = discover_services(root_dir=root_dir, exclude_dirs=effective_exclude)
```

- [ ] **Step 2: 验证默认行为变化**

```bash
python dev-services.py discover
```

预期：**不再输出** `mini-program` 和 `tools-mini-program` 下的服务，只剩 `backend` 和 `frontend`。

- [ ] **Step 3: 验证 `--all` 恢复全扫描**

```bash
python dev-services.py discover --all
```

预期：输出包含 `mini-program` 下的 Taro H5 服务（恢复旧行为）。

- [ ] **Step 4: 验证 `--include` 可按需包含**

```bash
python dev-services.py discover --include mini-program
```

预期：输出包含 `mini-program` 下的服务，但 `tools-mini-program` 仍被排除。

- [ ] **Step 5: 验证 `--exclude` 可追加排除**

```bash
python dev-services.py discover --all --exclude frontend
```

预期：输出包含 `backend` 和 `mini-program`，但不含 `frontend`。

- [ ] **Step 6: 验证 `--include` 优先级高于 `--exclude`**

```bash
python dev-services.py discover --all --exclude mini-program --include mini-program
```

预期：`mini-program` **被包含**（`--include` 覆盖 `--exclude`）。

- [ ] **Step 7: 验证 target 指定的根目录不受排除影响**

```bash
python dev-services.py discover mini-program
```

预期：输出 `mini-program` 目录下的服务（target 作为 root_dir，排除集对其不生效）。

- [ ] **Step 8: 提交**

```bash
git add dev-services.py
git commit -m "feat(dev-services): main() 计算 effective_exclude 并透传"
```

---

### Task 6: 排除集合计算逻辑的单元测试

**Files:**
- Create: `tests/test_dev_services_exclude.py`

- [ ] **Step 1: 创建测试文件**

```python
"""
dev-services.py 排除集合计算逻辑的单元测试。

覆盖规范第 4 节的所有规则：
- 默认排除列表生效
- --all 清空默认排除
- --exclude 追加排除
- --include 移除排除（优先级高于 --exclude）
- 大小写不敏感
- 静默忽略未知目录
"""
import sys
from pathlib import Path

# 让测试能导入项目根目录的 dev-services 模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# dev-services.py 含有连字符，需要 importlib 导入
import importlib.util
_spec = importlib.util.spec_from_file_location("dev_services", PROJECT_ROOT / "dev-services.py")
dev_services = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dev_services)


DEFAULT_EXCLUDE_DIRS = dev_services.DEFAULT_EXCLUDE_DIRS


def compute_effective_exclude(args_all: bool, args_exclude: list[str] | None, args_include: list[str] | None) -> set[str]:
    """复制 main() 中的计算逻辑，便于单元测试。

    注意：此函数必须与 dev-services.py main() 中的逻辑保持一致。
    """
    effective = set(DEFAULT_EXCLUDE_DIRS)
    if args_all:
        effective = set()
    for d in (args_exclude or []):
        effective.add(d.lower())
    for d in (args_include or []):
        effective.discard(d.lower())
    return effective


class TestDefaultExclude:
    """默认排除列表应包含 mini-program 相关目录。"""

    def test_contains_mini_program(self):
        assert "mini-program" in DEFAULT_EXCLUDE_DIRS

    def test_contains_tools_mini_program(self):
        assert "tools-mini-program" in DEFAULT_EXCLUDE_DIRS

    def test_does_not_contain_backend(self):
        assert "backend" not in DEFAULT_EXCLUDE_DIRS

    def test_does_not_contain_frontend(self):
        assert "frontend" not in DEFAULT_EXCLUDE_DIRS


class TestAllFlag:
    """--all 应清空默认排除。"""

    def test_all_clears_defaults(self):
        result = compute_effective_exclude(args_all=True, args_exclude=None, args_include=None)
        assert result == set()

    def test_all_with_exclude_adds_back(self):
        result = compute_effective_exclude(args_all=True, args_exclude=["frontend"], args_include=None)
        assert result == {"frontend"}

    def test_all_does_not_restore_defaults(self):
        result = compute_effective_exclude(args_all=True, args_exclude=None, args_include=None)
        assert "mini-program" not in result


class TestExcludeFlag:
    """--exclude 应追加排除项。"""

    def test_exclude_adds_to_defaults(self):
        result = compute_effective_exclude(args_all=False, args_exclude=["frontend"], args_include=None)
        assert "frontend" in result
        assert "mini-program" in result  # 默认排除仍保留

    def test_exclude_multiple(self):
        result = compute_effective_exclude(args_all=False, args_exclude=["frontend", "logs"], args_include=None)
        assert "frontend" in result
        assert "logs" in result
        assert "mini-program" in result

    def test_exclude_case_insensitive(self):
        result = compute_effective_exclude(args_all=False, args_exclude=["Frontend"], args_include=None)
        assert "frontend" in result


class TestIncludeFlag:
    """--include 应从排除集中移除（优先级高于 --exclude）。"""

    def test_include_removes_from_defaults(self):
        result = compute_effective_exclude(args_all=False, args_exclude=None, args_include=["mini-program"])
        assert "mini-program" not in result
        assert "tools-mini-program" in result  # 其他默认排除不受影响

    def test_include_overrides_exclude(self):
        """同一目录同时被 --exclude 和 --include 指定，--include 优先。"""
        result = compute_effective_exclude(
            args_all=False, args_exclude=["mini-program"], args_include=["mini-program"]
        )
        assert "mini-program" not in result

    def test_include_unknown_dir_silent(self):
        """--include 一个不存在的目录，静默忽略不报错。"""
        result = compute_effective_exclude(args_all=False, args_exclude=None, args_include=["nonexistent"])
        assert "nonexistent" not in result
        # 默认排除不受影响
        assert "mini-program" in result

    def test_include_case_insensitive(self):
        result = compute_effective_exclude(args_all=False, args_exclude=None, args_include=["Mini-Program"])
        assert "mini-program" not in result


class TestCombinedFlags:
    """组合标志的边界情况。"""

    def test_all_exclude_include_same_dir(self):
        """--all --exclude X --include X → X 不被排除。"""
        result = compute_effective_exclude(
            args_all=True, args_exclude=["foo"], args_include=["foo"]
        )
        assert "foo" not in result

    def test_defaults_only(self):
        """无任何标志时，只有默认排除生效。"""
        result = compute_effective_exclude(args_all=False, args_exclude=None, args_include=None)
        assert result == DEFAULT_EXCLUDE_DIRS

    def test_empty_lists_same_as_none(self):
        result_none = compute_effective_exclude(args_all=False, args_exclude=None, args_include=None)
        result_empty = compute_effective_exclude(args_all=False, args_exclude=[], args_include=[])
        assert result_none == result_empty
```

- [ ] **Step 2: 运行测试，确认全部通过**

```bash
cd G:/IdeaProjects/tools && python -m pytest tests/test_dev_services_exclude.py -v
```

预期：所有测试 PASS。

- [ ] **Step 3: 提交**

```bash
git add tests/test_dev_services_exclude.py
git commit -m "test(dev-services): 新增排除集合计算逻辑的单元测试"
```

---

### Task 7: 全流程集成验证

**Files:** 无代码改动，纯验证

- [ ] **Step 1: 验证 `start` 默认不启动 mini-program**

```bash
python dev-services.py start
```

验证：
- ✅ 仅 backend + frontend 启动
- ✅ mini-program 端口（5173 或类似）未被本脚本占用
- ✅ 日志中无 mini-program 相关启动信息

- [ ] **Step 2: 验证 `start --all` 启动所有服务**

```bash
python dev-services.py start --all
```

验证：所有服务（含 mini-program）都启动。

- [ ] **Step 3: 验证 `restart` 默认不重启 mini-program**

```bash
python dev-services.py restart
```

验证：仅 backend + frontend 重启。

- [ ] **Step 4: 验证 `status` 与 `status --all` 的输出差异**

```bash
python dev-services.py status
echo "---"
python dev-services.py status --all
```

验证：`status` 不含 mini-program；`status --all` 包含。

- [ ] **Step 5: 清理 — 停止所有服务**

```bash
python dev-services.py stop --all
```

- [ ] **Step 6: 最终提交（若有遗漏的修复）**

```bash
git status
# 若有改动
git add -A && git commit -m "fix(dev-services): 集成验证后的修复"
# 若无改动，跳过
```

---

## 自查清单

**1. 规范覆盖检查：**

| 规范章节 | 对应 Task | 状态 |
|---------|----------|------|
| §3 CLI 接口 | Task 4 | ✅ |
| §4 排除集合计算规则 | Task 5 + Task 6 | ✅ |
| §5 服务发现逻辑改动 | Task 2 + Task 3 | ✅ |
| §5.3 target 优先级 | Task 5 Step 7 | ✅ |
| §6 常量定义 | Task 1 | ✅ |
| §7 代码改动点 | Task 1-5 | ✅ |
| §8 向后兼容性 | Task 5 + Task 7 | ✅ |
| §9 测试要点（10 条） | Task 5（9 条）+ Task 6（1 条由单元测试覆盖） | ✅ |

**2. 占位符扫描：** 无 TBD / TODO / "implement later" / "similar to" / 缺失代码块。

**3. 类型/签名一致性：**
- `exclude_dirs: Optional[set[str]]` — 在 Task 2、Task 3 签名中一致
- `compute_effective_exclude` 测试辅助函数 — 参数名 `args_all` / `args_exclude` / `args_include` 与 argparse 的 `args.all` / `args.exclude` / `args.include` 对应
- `DEFAULT_EXCLUDE_DIRS` — Task 1 定义，Task 5 / Task 6 引用，名称一致
