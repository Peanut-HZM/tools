---
author: Peanut
created_at: 2026-06-19
purpose: Token 消耗统计 ccusage 跨平台调用 + 结构化错误信息设计
status: 待审查
---

# Token 消耗统计 ccusage 跨平台与结构化错误

## 背景

`http://localhost:5178/tools/token-usage` 页面的"同步数据"按钮在 Windows 环境下失败率较高，排查发现根因有两条：

1. **后端服务进程的 PATH 不含 Node.js**：`ccusage` 是 Node.js CLI 工具，`ccusage.cmd` 内部依赖 `node` 命令。后端作为子进程调用时找不到 `node`，返回 `'"node"' 不是内部或外部命令` 错误，sync 接口静默返回 0 条记录。
2. **跨平台路径覆盖不全**：现有 `_find_ccusage` / `_find_node` 只覆盖 Windows 常见路径（`~/AppData/Roaming/npm/`）和 Linux 默认路径（`/usr/local/bin/`、`/usr/bin/`），缺少 macOS（Homebrew、NVM、pnpm）和 Linux 下的 NVM / pnpm 等安装位置。
3. **错误信息不可操作**：`usage_fetcher.py` 和 `usage_fetcher_v2.py` 返回的错误为纯文本字符串（`"CLI 未安装: ccusage"`、`"未知错误"`），前端只能展示给用户"同步失败"，无法区分"没装 ccusage"、"没装 Node.js"、"环境不兼容"等具体情况。

## 目标

1. **跨平台一致**：macOS、Windows、Linux 任意环境安装 ccusage 后，同步功能均可用。
2. **错误可定位**：用户看到错误时，立刻知道是哪种问题、怎么解决。
3. **改动一致**：v1（`usage_fetcher.py` 的 `fetch_claude` / `fetch_opencode` / `fetch_ccusage_opencode`）和 v2（`usage_fetcher_v2.py` 的 `fetch_ccusage_daily` / `fetch_ccusage_agent_daily`）共用同一套调用与错误逻辑。

## 解决方案

### 1. 新增统一 ccusage 调用器

新建 `backend/app/utils/ccusage_invoker.py`，集中处理 ccusage 路径发现、node 路径发现、命令构造、错误分类。

#### 1.1 跨平台路径发现

`find_ccusage() -> Optional[str]`，按当前 OS 分发到对应的搜索列表：

| OS | 搜索路径 |
|----|---------|
| **Windows** | `%APPDATA%\npm\ccusage.cmd`、`%APPDATA%\npm\ccusage.ps1`、`%LOCALAPPDATA%\pnpm\ccusage.cmd`、`%LOCALAPPDATA%\pnpm\ccusage`、`%ProgramFiles%\nodejs\ccusage.cmd`、`where ccusage` |
| **macOS** | `/opt/homebrew/bin/ccusage`（Apple Silicon Homebrew）、`/usr/local/bin/ccusage`（Intel Homebrew）、`~/.npm-global/bin/ccusage`、`~/.nvm/versions/node/*/bin/ccusage`（glob 展开）、`~/Library/pnpm/ccusage`、`which ccusage` |
| **Linux** | `/usr/local/bin/ccusage`、`/usr/bin/ccusage`、`~/.npm-global/bin/ccusage`、`~/.nvm/versions/node/*/bin/ccusage`、`~/.local/share/pnpm/ccusage`、`which ccusage` |

`find_node() -> Optional[str]` 类似策略，路径列表覆盖三平台。

#### 1.2 命令构造

`build_cmd(args: list[str]) -> list[str]`：

- Windows 下若 ccusage 是 `.cmd` / `.ps1`，改用 `[node_path, js_path] + args` 形式调用（node 直接执行 JS 入口，绕开 `.cmd` 内部 `node` 解析问题）。
- macOS / Linux 下直接 `[ccusage_path] + args`。
- 若找到的是可执行文件且不是 `.cmd`/`.ps1`，直接使用。

#### 1.3 结构化错误

```python
@dataclass
class CcusageError:
    code: str           # 错误代码
    message: str        # 开发者可读的原因
    remediation: str    # 给用户的修复命令或建议
    details: dict       # 调试信息（路径、异常等）
```

错误代码枚举：

| code | 触发条件 | remediation |
|------|---------|-------------|
| `CLI_NOT_FOUND` | `find_ccusage()` 返回 None | `请运行 npm i -g ccusage 安装 ccusage` |
| `NODE_NOT_FOUND` | Windows 下需要 node 调用 JS 入口但找不到 node | `请先安装 Node.js: https://nodejs.org` |
| `PERMISSION_DENIED` | subprocess 抛 `PermissionError` | `请检查 ccusage 可执行权限（chmod +x）` |
| `EXEC_TIMEOUT` | subprocess 超时 | `请稍后重试，或检查 ccusage 数据量是否过大` |
| `INVALID_JSON_OUTPUT` | stdout 找不到合法 JSON | `ccusage 输出异常，请检查 ccusage 版本（建议 ≥ 15.0）` |
| `CLI_EXECUTION_ERROR` | ccusage 退出码非 0 | 透传 ccusage stderr 前 500 字符 |

`_run_cmd` 改为抛出 `CcusageError` 异常或返回 `{"error": CcusageError(...) }` 形式，由调用方决定是上抛 HTTP 异常还是记日志。

### 2. 后端集成

#### 2.1 v2 调用器改造

`backend/app/utils/usage_fetcher_v2.py` 移除内嵌的 `_find_ccusage` / `_build_ccusage_cmd`，改为调用 `ccusage_invoker`：

```python
from app.utils.ccusage_invoker import run_ccusage

def fetch_ccusage_daily(since, until):
    return run_ccusage(["daily", "--json", f"--since={since}", f"--until={until}", "--offline"])
```

#### 2.2 v1 调用器改造

`backend/app/utils/usage_fetcher.py` 的 `fetch_claude` / `fetch_opencode` / `fetch_ccusage_opencode` 中的 Windows 特定路径分支替换为 `ccusage_invoker` 调用，复用 v2 改造后的逻辑。

#### 2.3 HTTP 错误响应

`/refresh-ccusage` 端点（`backend/app/routes/token_usage.py:1061`）的异常处理改为返回结构化错误：

```json
{
  "detail": "未找到 ccusage 命令",
  "error_code": "CLI_NOT_FOUND",
  "remediation": "请运行 npm i -g ccusage 安装 ccusage"
}
```

`/refresh` 端点（手动刷新）的 `errors` 列表中单条改为同样结构（保持向后兼容：`message` 字段保留为人类可读文本）。

### 3. 前端展示

`frontend/src/components/Tools/TokenUsage.tsx` 中：

- `handleSync` 失败时，从错误响应中读取 `error_code` / `remediation`，toast 标题显示 `同步失败：<code>`，副标题显示 `remediation`。
- `handleRefresh` 同步刷新多个数据源时，遍历 `errors` 列表，弹一个包含全部错误代码和修复命令的 toast。
- Toast 颜色按错误代码区分：环境类（`CLI_NOT_FOUND` / `NODE_NOT_FOUND`）用 amber 警告色，其他用 red 错误色。

## 设计决策

1. **新建独立模块而不是修改 v1/v2 文件**：`ccusage_invoker.py` 作为唯一职责清晰的单元，三平台路径发现、node 解析、错误分类都集中维护。
2. **结构化错误采用 dataclass**：避免 dict 拼写错误，IDE 可补全，便于单测。
3. **保持向后兼容**：`error_code` 和 `remediation` 是新增字段，原 `detail` / `message` 字段保留，前端改造期间旧客户端不会破坏。
4. **NVM 路径用 glob 展开**：macOS / Linux 下 NVM 装在 `~/.nvm/versions/node/<version>/bin/`，需用 `glob.glob(os.path.expanduser("~/.nvm/versions/node/*/bin/"))` 遍历，避免硬编码 Node 版本号。
5. **不引入新依赖**：所有路径发现使用 Python 标准库（`shutil.which`、`os.path`、`glob`）。

## 验证计划

### 单元测试（可选，新文件）

`backend/tests/test_ccusage_invoker.py`：

- mock `shutil.which` 和 `os.path.exists`，测试三个平台下 `find_ccusage` 返回正确路径。
- mock subprocess 抛 `FileNotFoundError` / `PermissionError` / `TimeoutExpired`，断言 `CcusageError.code` 正确。
- 模拟 `find_ccusage` 返回 None，断言返回 `CLI_NOT_FOUND` 错误。

### 手动验证（必做）

**Windows**：
1. 启动后端服务（uvicorn `--reload`）
2. 访问 `http://localhost:5178/tools/token-usage`，点击"同步数据"
3. 确认 toast 显示 `同步成功` 且明细数据出现本机记录
4. 临时把 ccusage 改名（`mv ccusage.cmd ccusage.cmd.bak`），再次点击"同步数据"，确认 toast 提示 `CLI_NOT_FOUND` + 修复命令
5. 恢复 ccusage

**macOS / Linux**（本机无环境，代码审查 + 路径搜索函数单测覆盖）：
1. 静态审查 `find_ccusage` 在 macOS / Linux 下的搜索路径是否覆盖 Homebrew / NVM / pnpm
2. 单测中 mock 各路径，验证发现函数返回值

### 前端验证

1. 故意触发 `CLI_NOT_FOUND` 错误（卸载 ccusage），确认 toast 出现错误代码 + 修复命令
2. 触发 `EXEC_TIMEOUT`，确认 toast 显示"执行超时"提示
3. 正常同步成功，toast 仍显示成功消息

## 影响评估

- **新增文件**：`backend/app/utils/ccusage_invoker.py`（约 200 行）、`backend/tests/test_ccusage_invoker.py`（可选，约 80 行）
- **修改文件**：
  - `backend/app/utils/usage_fetcher.py`：删除 Windows 特定路径分支，改为调用 `ccusage_invoker`
  - `backend/app/utils/usage_fetcher_v2.py`：删除内嵌 `_find_ccusage` / `_build_ccusage_cmd`，改为调用 `ccusage_invoker`
  - `backend/app/routes/token_usage.py`：`/refresh-ccusage` 端点返回结构化错误
  - `frontend/src/components/Tools/TokenUsage.tsx`：toast 展示错误代码 + 修复命令
- **Breaking Change**：无（新增字段，向后兼容）
- **风险等级**：中（涉及核心同步链路，需充分验证）

## 实施记录

- **实施日期**：待定
- **实施人**：待定
- **状态**：待实施

## 备注

本次改造是 v1/v2 统一化的第一步。后续可以考虑：
- 抽取 v1 三个 fetch 方法（`fetch_claude` / `fetch_opencode` / `fetch_ccusage_opencode`）到独立模块，去除 `usage_fetcher.py` 中的历史包袱
- 在前端增加"环境检测"按钮，一键展示 ccusage / node / 路径的检测结果
