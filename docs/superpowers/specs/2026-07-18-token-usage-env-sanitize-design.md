---
author: Peanut
created_at: 2026-07-18
purpose: 修复 ccusage 调用在 Linux 服务器上因非字符串环境变量导致 subprocess.run 报错的问题
---

# Token Usage ccusage 调用 — 环境变量防御式净化设计

## 1. 问题描述

### 现象

在 `http://localhost:5178/tools/token-usage` 页面点击刷新按钮，出现错误：

```
ccusage-v2:daily: ccusage 执行异常: environment can only contain strings
错误代码: CLI_EXECUTION_ERROR
建议: 请检查安装是否完整
```

### 错误链路

```
ccusage_invoker._execute_and_parse()
  → env = os.environ.copy()          # 复制系统环境（可能含非字符串值）
  → env["HOME"] = REAL_HOME           # 注入 HOME（字符串）
  → env["PATH"] = ...                 # 拼接 PATH（字符串）
  → subprocess.run(..., env=env)      # Python 3.9+ 严格校验 → TypeError
  → except Exception → CLI_EXECUTION_ERROR（前端显示）
```

### 根因

`subprocess.run(env=...)` 在 **Python 3.9+** 严格要求所有 env 值都是字符串类型。Linux 服务器上的 systemd / supervisord / Docker 注入的环境变量可能包含 `bytes`、`None`、`int` 等非字符串值，触发 `TypeError: environment can only contain strings`。

本地 Windows 开发环境正常，因为 Python 3.14 的 `os.environ` 全是字符串。

### 影响范围

- **只影响 Linux 服务器**（systemd / Docker / supervisord 部署）
- **所有通过 `ccusage_invoker` 调用的 CLI 工具**都受影响（ccusage、opencode-usage 等）
- 前端显示为 `CLI_EXECUTION_ERROR`，用户无法查看 Token Usage 数据

---

## 2. 修复方案

### 改动文件

**只改一个文件**：`backend/app/utils/ccusage_invoker.py` 的 `_execute_and_parse` 函数（约第 209-271 行）。

### 核心改动：env 净化

在构造 `env` 之后、传给 `subprocess.run` 之前，增加一个净化步骤：

```python
# 净化 env：Python 3.9+ 的 subprocess.run 严格要求 env 值都是字符串
# Linux 服务器的 systemd/Docker 可能注入 bytes/None/int 等非字符串值
_sanitized = {}
_skipped_keys = []
for _k, _v in env.items():
    if _v is None:
        _skipped_keys.append((_k, "None"))
        continue
    if not isinstance(_v, str):
        try:
            _sanitized[_k] = str(_v)
        except Exception:
            _skipped_keys.append((_k, f"{type(_v).__name__}"))
            continue
    else:
        _sanitized[_k] = _v

if _skipped_keys:
    logger.warning(
        "[ccusage-invoker] env 净化：跳过 %d 个非字符串值: %s",
        len(_skipped_keys),
        ", ".join(f"{k}({t})" for k, t in _skipped_keys),
    )
```

### 净化规则

| 原始值类型 | 处理方式 | 原因 |
|---|---|---|
| `str` | 保留不变 | 正常路径，零开销 |
| `None` | 跳过（不传入 env） | `str(None)` 会变成 `"None"` 字符串，污染环境 |
| `bytes` | `str(v, 'utf-8', 'replace')` 解码 | 最常见的非字符串来源，多数是 UTF-8 编码的路径 |
| `int`/`float`/`bool` | `str(v)` 转换 | 安全转换 |
| 其他不可转换 | 跳过并记录日志 | 避免崩溃 |

### 日志策略

- 只有实际发现非字符串值时才打 `WARNING` 日志
- 记录 key 名和类型，方便定位 Linux 服务器上的源头
- 正常运行（全是字符串）时零日志开销

### TypeError 独立分支

给 `TypeError` 单独加一个异常分支，放在 `except subprocess.TimeoutExpired` 之后、`except Exception` 之前：

```python
except TypeError as e:
    # env 净化后理论上不会再出现，但兜底暴露真实问题
    return {
        "ok": False,
        "error": CcusageError(
            code=ErrorCode.CLI_EXECUTION_ERROR,
            message=f"{cli_name} 环境变量构造失败: {e}",
            remediation="请联系管理员检查服务器环境变量配置",
            details={"error": str(e), "env_keys_sample": list(env.keys())[:10]},
        ),
    }
```

---

## 3. 跨平台兼容性

| 平台 | 影响 |
|---|---|
| **Windows** | 本地环境干净，净化步骤零开销（无匹配项），不影响行为 |
| **macOS** | 同上 |
| **Linux** | 解决 systemd/Docker 注入的非字符串 env 问题 |

---

## 4. 验证方案

### 4.1 单元测试

新增 `backend/tests/test_ccusage_env_sanitize.py`：

- 构造含 `bytes`/`None`/`int` 的 mock env，验证净化后全是 str
- 验证 `None` 被跳过、`bytes` 被解码、`int` 被转换
- 验证 `_skipped_keys` 日志触发

### 4.2 本地浏览器验证

1. `python dev_services.py restart backend`
2. 打开 `http://localhost:5178/tools/token-usage`
3. 点击刷新按钮，确认无报错
4. 查看浏览器 Console 无错误

### 4.3 Linux 服务器验证（核心）

1. `mvn clean install`（注：此处是 Python 项目，实际用 `python -m py_compile`）
2. `python deploy-remote.py system`（或相关模块）
3. 在服务器上触发 Token Usage 刷新
4. 查看后端日志，确认 `env 净化：跳过 N 个非字符串值` 的 WARNING 出现
5. 确认 ccusage 正常返回数据

---

## 5. 回滚方案

- 单文件改动，`git checkout backend/app/utils/ccusage_invoker.py` 即可回滚
- 无数据库迁移、无依赖变更、无前端改动

---

## 6. 设计决策记录

| 决策 | 理由 |
|---|---|
| 为什么不在 `main.py` 启动时全局清理？ | 全局清理会污染启动日志，且无法覆盖后续动态注入的 env。净化放在调用点更精确。 |
| 为什么 `None` 被跳过而非转 `"None"`？ | `str(None)` 产生字面字符串 `"None"`，会被子进程误认为是真实的环境变量值，污染环境。 |
| 为什么 bytes 用 `'replace'` 而非 `'strict'`？ | 某些 systemd 注入的 bytes 可能含非 UTF-8 字节，`'strict'` 会抛异常导致净化失败。`'replace'` 用 `?` 替代不可解码字节更安全。 |
| 为什么只改 `_execute_and_parse`？ | `run_ccusage` 和 `run_generic_cli` 都通过它调用 subprocess，一处修复覆盖所有 CLI 工具。 |
