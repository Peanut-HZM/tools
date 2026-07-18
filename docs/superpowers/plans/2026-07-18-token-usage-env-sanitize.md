# Token Usage Env 防御式净化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 ccusage 调用在 Linux 服务器上因非字符串环境变量导致 `subprocess.run` 抛出 `TypeError: environment can only contain strings` 的问题。

**Architecture:** 在 `ccusage_invoker._execute_and_parse` 中提取 `env` 净化为独立 helper 函数 `_sanitize_env`，在传给 `subprocess.run` 之前对 `env` 字典做防御式清洗，并添加 `TypeError` 独立异常分支。

**Tech Stack:** Python 3.9+, pytest, subprocess

---

## File Structure

| 文件 | 操作 | 职责 |
|---|---|---|
| `backend/app/utils/ccusage_invoker.py` | **Modify** | 新增 `_sanitize_env()` 函数 + 修改 `_execute_and_parse()` 调用它 + 新增 `TypeError` 异常分支 |
| `backend/tests/test_ccusage_env_sanitize.py` | **Create** | `_sanitize_env` 的单元测试 |

---

### Task 1: 提取 `_sanitize_env` 函数并编写失败测试

**Files:**
- Modify: `backend/app/utils/ccusage_invoker.py`
- Create: `backend/tests/test_ccusage_env_sanitize.py`

- [ ] **Step 1: 在 `_execute_and_parse` 之前添加 `_sanitize_env` 函数**

在 `ccusage_invoker.py` 的 `_execute_and_parse` 函数（第 209 行）之前，新增以下函数：

```python
def _sanitize_env(env: dict) -> tuple[dict, list[tuple[str, str]]]:
    """净化环境变量字典，确保所有值都是字符串。

    Python 3.9+ 的 subprocess.run 严格要求 env 值都是字符串类型。
    Linux 服务器的 systemd/Docker 可能注入 bytes/None/int 等非字符串值，
    此函数负责清洗这些异常值，并返回被跳过的 key 列表供日志记录。

    Returns:
        (sanitized_env, skipped_keys) — sanitized_env 是只含 str 值的 dict，
        skipped_keys 是 [(key, type_description), ...] 列表。
    """
    sanitized = {}
    skipped_keys = []
    for key, value in env.items():
        if value is None:
            skipped_keys.append((key, "None"))
            continue
        if isinstance(value, bytes):
            try:
                sanitized[key] = value.decode("utf-8", errors="replace")
            except Exception:
                skipped_keys.append((key, f"{type(value).__name__}"))
                continue
        elif not isinstance(value, str):
            try:
                sanitized[key] = str(value)
            except Exception:
                skipped_keys.append((key, f"{type(value).__name__}"))
                continue
        else:
            sanitized[key] = value
    return sanitized, skipped_keys
```

- [ ] **Step 2: 修改 `_execute_and_parse` 使用 `_sanitize_env`**

将 `_execute_and_parse` 函数中第 225-231 行：

```python
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
```

改为：

```python
        env, skipped_keys = _sanitize_env(env)
        if skipped_keys:
            logger.warning(
                "[ccusage-invoker] env 净化：跳过 %d 个非字符串值: %s",
                len(skipped_keys),
                ", ".join(f"{k}({t})" for k, t in skipped_keys),
            )

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
```

- [ ] **Step 3: 在 `except PermissionError` 之后、`except Exception` 之前添加 `TypeError` 分支**

在 `ccusage_invoker.py` 第 252-261 行（`except FileNotFoundError`）之后，添加：

```python
    except TypeError as e:
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

- [ ] **Step 4: 创建测试文件 `backend/tests/test_ccusage_env_sanitize.py`**

```python
"""_sanitize_env 单元测试"""
from app.utils.ccusage_invoker import _sanitize_env


class TestSanitizeEnv:
    """验证 _sanitize_env 对各类非字符串值的处理"""

    def test_all_strings_passed_through(self):
        """全字符串 env 原样返回，skipped_keys 为空"""
        env = {"PATH": "/usr/bin", "HOME": "/home/user", "LANG": "en_US.UTF-8"}
        result, skipped = _sanitize_env(env)
        assert result == env
        assert skipped == []

    def test_none_value_is_skipped(self):
        """None 值被跳过，不进入结果 dict"""
        env = {"PATH": "/usr/bin", "BAD": None}
        result, skipped = _sanitize_env(env)
        assert "BAD" not in result
        assert result["PATH"] == "/usr/bin"
        assert ("BAD", "None") in skipped

    def test_bytes_value_is_decoded(self):
        """bytes 值用 utf-8 解码"""
        env = {"PATH": b"/usr/bin", "HOME": "/home/user"}
        result, skipped = _sanitize_env(env)
        assert result["PATH"] == "/usr/bin"
        assert result["HOME"] == "/home/user"
        assert skipped == []

    def test_bytes_with_non_utf8_uses_replace(self):
        """含非 UTF-8 字节的 bytes 用 replace 模式解码"""
        env = {"BAD": b"\xff\xfe"}
        result, skipped = _sanitize_env(env)
        assert result["BAD"] == "��"
        assert skipped == []

    def test_int_value_is_converted(self):
        """int 值被 str() 转换"""
        env = {"PORT": 8080, "PATH": "/usr/bin"}
        result, skipped = _sanitize_env(env)
        assert result["PORT"] == "8080"
        assert result["PATH"] == "/usr/bin"
        assert skipped == []

    def test_float_value_is_converted(self):
        """float 值被 str() 转换"""
        env = {"RATE": 3.14}
        result, skipped = _sanitize_env(env)
        assert result["RATE"] == "3.14"
        assert skipped == []

    def test_bool_value_is_converted(self):
        """bool 值被 str() 转换"""
        env = {"DEBUG": True, "VERBOSE": False}
        result, skipped = _sanitize_env(env)
        assert result["DEBUG"] == "True"
        assert result["VERBOSE"] == "False"
        assert skipped == []

    def test_empty_env(self):
        """空 dict 返回空 dict"""
        result, skipped = _sanitize_env({})
        assert result == {}
        assert skipped == []

    def test_mixed_types(self):
        """混合多种类型，验证各自处理"""
        env = {
            "STR": "ok",
            "NONE": None,
            "BYTES": b"bytes_val",
            "INT": 42,
            "FLOAT": 2.5,
            "BOOL": True,
        }
        result, skipped = _sanitize_env(env)
        assert result["STR"] == "ok"
        assert result["BYTES"] == "bytes_val"
        assert result["INT"] == "42"
        assert result["FLOAT"] == "2.5"
        assert result["BOOL"] == "True"
        assert "NONE" not in result
        assert len(skipped) == 1
        assert skipped[0] == ("NONE", "None")
```

- [ ] **Step 5: 运行测试确认全部通过**

```bash
cd G:/IdeaProjects/tools/backend
python -m pytest tests/test_ccusage_env_sanitize.py -v
```

期望输出：全部 PASS（10 个测试）

- [ ] **Step 6: 运行已有的 ccusage_invoker 测试确保无破坏**

```bash
cd G:/IdeaProjects/tools/backend
python -m pytest tests/test_ccusage_invoker.py -v
```

期望输出：全部 PASS

- [ ] **Step 7: 语法检查**

```bash
cd G:/IdeaProjects/tools/backend
python -m py_compile app/utils/ccusage_invoker.py
```

- [ ] **Step 8: 提交**

```bash
cd G:/IdeaProjects/tools
git add backend/app/utils/ccusage_invoker.py backend/tests/test_ccusage_env_sanitize.py
git commit -m "fix：ccusage 调用增加 env 防御式净化，修复 Linux 服务器非字符串环境变量导致 subprocess 报错

- 新增 _sanitize_env() 函数，净化 bytes/None/int 等非字符串 env 值
- subprocess.run 前调用净化，添加 WARNING 日志记录跳过的 key
- 新增 TypeError 独立异常分支，暴露真实环境问题
- 新增 test_ccusage_env_sanitize.py 单元测试（10 个用例）
- 跨平台兼容：Windows/macOS 零开销，Linux 解决 systemd/Docker 注入问题

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## 自审

| 检查项 | 结果 |
|---|---|
| Spec 覆盖 | ✅ env 净化、日志、TypeError 分支、单元测试 — 全部在 Task 1 中实现 |
| 占位符扫描 | ✅ 无 TBD/TODO，所有代码完整 |
| 类型一致性 | ✅ `_sanitize_env` 返回 `tuple[dict, list[tuple[str, str]]]`，与调用方一致 |
