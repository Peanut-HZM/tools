---
author: Peanut
created_at: 2026-05-30
purpose: 修复 dev-services.py 在 Windows 重启服务时的 psutil.AccessDenied 崩溃，并增强进程身份验证防止误杀其他项目进程
---

# dev-services.py 服务重启可靠性增强设计

## 1. 问题描述

执行 `python dev-services.py restart` 时，`kill_process` 函数在 `proc.wait(timeout=3)` 阶段抛出 `psutil.AccessDenied`，导致整个脚本崩溃、服务无法完成重启。

```
psutil.AccessDenied: (pid=31116, name='python.exe')
```

触发路径：
```
restart_service → stop_service_wrapper → stop_service → kill_process_tree → kill_process → proc.wait(timeout=3)
```

## 2. 根因分析

### 2.1 `kill_process` 异常处理不完整

当前 `kill_process` 只捕获了 `psutil.TimeoutExpired` 和 `ChildProcessError`，**未捕获 `psutil.AccessDenied`**。

当进程被系统锁定、UAC 权限不匹配、或进程句柄被其他安全软件占用时，`wait()` 会抛出 `AccessDenied`，脚本直接崩溃。

### 2.2 缺乏进程身份验证

`find_process_by_port` 仅通过端口找 PID，未验证该 PID 是否确实属于当前项目。如果其他项目的 Python 服务恰好使用了相同端口，存在误杀风险。

### 2.3 子进程清理在权限不足时失效

`_iter_child_processes` 在 `AccessDenied` 时返回空列表，导致子进程（如 uvicorn --reload 产生的子进程）残留。

## 3. 设计目标

1. **绝不崩溃**：无论进程处于什么状态（僵尸、挂起、权限锁定），`restart` 必须成功完成。
2. **绝不误杀**：只能终止属于当前项目的进程，必须通过 `cwd` + `cmdline` + 端口三重验证。
3. **跨平台**：Windows 和 macOS（Linux）都必须正常工作。
4. **最小改动**：不修改现有架构，只增强 `kill_process`、`kill_process_tree`、`stop_service` 三个核心函数。

## 4. 设计方案

### 4.1 进程身份验证模块

新增 `verify_belongs_to_service(pid: int, svc: Service) -> bool` 函数，三层验证策略：

**第一层：cwd 验证**
```python
# 注意：此处不使用 assert，assert 在 -O 模式下会被跳过且失败时抛出 AssertionError
cwd = Path(proc.cwd()).resolve()
project_dir = svc.project_dir.resolve()
if cwd == project_dir or project_dir in cwd.parents:
    return True
```

**第二层：cmdline 特征验证**
```python
cmdline = " ".join(proc.cmdline())

# 排除通用参数，避免误匹配
GENERIC_ARGS = {"--port", "--host", "--reload", "-m", "--workers", "--loop", "--http"}

# 从 start_cmd 中提取非通用特征进行匹配
for part in svc.start_cmd:
    if part in GENERIC_ARGS:
        continue
    if part in cmdline:
        return True

# 类型特定特征（要求至少两个特征同时匹配，降低误报）
if svc.project_type == "python":
    python_indicators = [k for k in ["uvicorn", "fastapi", "app.main", "gunicorn", "flask", "django"] if k in cmdline]
    if len(python_indicators) >= 2:
        return True
    # 如果只匹配到一个通用标识，再要求 cwd 或端口验证通过（由外层逻辑保证）

if svc.project_type in ["vite", "uniapp", "taro"]:
    if "vite" in cmdline and str(svc.project_dir) in cmdline:
        return True
```

**第三层：端口验证**
```python
# 确认该进程确实在监听目标端口
# 注意：端口验证仅作为辅助，因为其他项目也可能恰好使用相同端口
for conn in proc.connections(kind='inet'):
    if conn.laddr and conn.laddr.port == svc.port:
        return True
```

**验证失败处理：**
- 任一验证通过即视为合法进程
- 全部验证因 `AccessDenied` 无法执行时，**保守策略：不杀**，记录 WARN 日志提示用户手动处理
- `kill_process` 的强制终止降级**仅在已验证的 PID 上使用**，绝不绕过身份验证

### 4.2 kill_process 异常处理增强

```python
def kill_process(pid: int, graceful: bool = True, use_taskkill: bool = True):
    """终止进程，支持跨平台降级。注意：此函数只应接收已通过身份验证的 PID。"""
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
    except psutil.NoSuchProcess:
        log(f"进程 {pid} 已不存在", "INFO")
        return

    if graceful:
        try:
            proc.terminate()
            proc.wait(timeout=3)
            log(f"{proc_name} (PID {pid}) 已停止", "SUCCESS")
            return
        except psutil.AccessDenied:
            log(f"终止 {proc_name} (PID {pid}) 权限不足，尝试系统级强制终止", "WARN")
        except (psutil.TimeoutExpired, ChildProcessError, psutil.NoSuchProcess):
            pass  # 继续到强制终止

    # 强制终止阶段
    killed = False
    try:
        proc.kill()
        killed = True  # kill 信号已成功发送
        proc.wait(timeout=2)
    except psutil.AccessDenied:
        log(f"强制终止 {proc_name} (PID {pid}) 权限不足", "WARN")
    except (psutil.TimeoutExpired, ChildProcessError, psutil.NoSuchProcess):
        pass  # 进程已在终止中或已消失

    if not killed and use_taskkill:
        # 跨平台系统级强制终止
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    killed = True
                else:
                    stderr = result.stderr.decode("utf-8", errors="ignore") if result.stderr else ""
                    log(f"taskkill 失败 (PID {pid}): {stderr}", "ERROR")
            except Exception as e:
                log(f"taskkill 执行异常 (PID {pid}): {e}", "ERROR")
        else:
            try:
                result = subprocess.run(
                    ["kill", "-9", str(pid)],
                    capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    killed = True
                else:
                    stderr = result.stderr.decode("utf-8", errors="ignore") if result.stderr else ""
                    log(f"kill -9 失败 (PID {pid}): {stderr}", "ERROR")
            except Exception as e:
                log(f"kill -9 执行异常 (PID {pid}): {e}", "ERROR")

    if killed:
        log(f"{proc_name} (PID {pid}) 已强制终止", "WARN")
    else:
        log(f"无法终止 {proc_name} (PID {pid})，请手动处理", "ERROR")
```

### 4.3 kill_process_tree 增强

```python
def kill_process_tree(pid: int, graceful: bool = True, use_taskkill: bool = True):
    """终止进程树，子进程优先"""
    children = _iter_child_processes(pid)

    def _depth(proc):
        try:
            return len(proc.parents())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0

    # 先杀子进程（深度大的优先）
    for child in sorted(children, key=_depth, reverse=True):
        if child.pid == os.getpid():
            continue
        kill_process(child.pid, graceful=graceful, use_taskkill=use_taskkill)

    # 最后杀父进程
    kill_process(pid, graceful=graceful, use_taskkill=use_taskkill)
```

### 4.4 stop_service / kill_service 增强

修改 `stop_service` 和 `kill_service` 签名，接受 `Service` 对象以便进行身份验证：

```python
def verify_belongs_to_service(pid: int, svc: Service) -> bool:
    """验证 PID 是否属于指定的服务。任一验证通过即返回 True，全部失败返回 False。"""
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        log(f"无法验证 PID {pid}（权限不足），跳过", "WARN")
        return False

    project_dir = svc.project_dir.resolve()

    # 第一层：cwd 验证
    try:
        cwd = Path(proc.cwd()).resolve()
        if cwd == project_dir or project_dir in cwd.parents:
            return True
    except (psutil.AccessDenied, OSError):
        pass

    # 第二层：cmdline 特征验证
    try:
        cmdline = " ".join(proc.cmdline())
        GENERIC_ARGS = {"--port", "--host", "--reload", "-m", "--workers", "--loop", "--http"}
        for part in svc.start_cmd:
            if part in GENERIC_ARGS:
                continue
            if part in cmdline:
                return True
        if svc.project_type == "python":
            indicators = [k for k in ["uvicorn", "fastapi", "app.main", "gunicorn", "flask", "django"] if k in cmdline]
            if len(indicators) >= 2:
                return True
        if svc.project_type in ["vite", "uniapp", "taro"]:
            if "vite" in cmdline and str(project_dir) in cmdline:
                return True
    except (psutil.AccessDenied, OSError):
        pass

    # 第三层：端口验证
    try:
        for conn in proc.connections(kind='inet'):
            if conn.laddr and conn.laddr.port == svc.port:
                return True
    except (psutil.AccessDenied, OSError):
        pass

    return False


def stop_service(svc: Service):
    """优雅停止指定服务，带身份验证"""
    log(f"停止 {svc.name} (端口 {svc.port})...", "INFO")
    pids = find_process_by_port(svc.port)
    if not pids:
        log(f"{svc.name} 未运行", "INFO")
        return

    verified = []
    for pid in pids:
        if verify_belongs_to_service(pid, svc):
            verified.append(pid)
        else:
            log(f"PID {pid} 不属于 {svc.name}，跳过", "WARN")

    if not verified:
        log(f"端口 {svc.port} 被占用，但未找到属于 {svc.name} 的进程", "WARN")
        return

    for pid in verified:
        kill_process_tree(pid, graceful=True)


def kill_service(svc: Service):
    """强制终止指定服务，带身份验证"""
    log(f"强制终止 {svc.name} (端口 {svc.port})...", "WARN")
    pids = find_process_by_port(svc.port)
    if not pids:
        log(f"{svc.name} 未运行", "INFO")
        return

    verified = []
    for pid in pids:
        if verify_belongs_to_service(pid, svc):
            verified.append(pid)
        else:
            log(f"PID {pid} 不属于 {svc.name}，跳过", "WARN")

    if not verified:
        log(f"端口 {svc.port} 被占用，但未找到属于 {svc.name} 的进程", "WARN")
        return

    for pid in verified:
        kill_process_tree(pid, graceful=False)
```

### 4.5 cleanup_orphan_python_children 增强

该函数同样存在 `kill_process` 未处理 `AccessDenied` 的问题。修改调用处传入 `use_taskkill=True`：

```python
def cleanup_orphan_python_children(project_dir: Path):
    # ... 现有逻辑 ...
    kill_process(proc.pid, graceful=False, use_taskkill=True)
```

## 5. 跨平台兼容性

| 功能 | Windows | macOS/Linux |
|------|---------|-------------|
| `psutil.terminate()` | ✅ 正常 | ✅ 正常 |
| `psutil.kill()` | ✅ 正常 | ✅ 正常 |
| `psutil.wait()` AccessDenied | 降级到 `taskkill /F /T /PID` | 降级到 `kill -9` |
| 进程身份验证（cwd/cmdline） | ✅ | ✅ |
| `_get_pids_by_port_fallback` | `netstat` / PowerShell | `lsof` |

**注意：** `taskkill /T` 会自动终止整个进程树，因此在 Windows 上即使 `_iter_child_processes` 因权限返回空，系统命令也能确保子进程被清理。

## 6. 改动文件清单

仅修改 `dev-services.py`：

| 函数/区域 | 改动类型 | 说明 |
|-----------|----------|------|
| `kill_process` | 修改签名 + 增强异常处理 | 新增 `use_taskkill` 参数，捕获 `AccessDenied` |
| `kill_process_tree` | 修改签名 | 透传 `use_taskkill` |
| `stop_service` | 修改签名 + 增强验证 | 接受 `Service` 对象，增加身份验证 |
| `kill_service` | 修改签名 + 增强验证 | 同上 |
| `verify_belongs_to_service` | 新增 | 三层验证函数 |
| `stop_service_wrapper` | 修改 | 内部调用 `stop_service(svc.name, svc.port)` → `stop_service(svc)` |
| `restart_service` | 无改动 | 保持不变 |
| `cleanup_orphan_python_children` | 修改调用 | 传入 `use_taskkill=True` |
| `start_service` | 修改调用 | 第 1310 行 `kill_service(svc.name, svc.port)` → `kill_service(svc)` |
| `main()` kill action | 修改调用 | 第 1672-1674 行 `kill_service(svc.name, svc.port)` → `kill_service(svc)` |

## 7. 测试验证计划

### 7.1 Windows 验证
1. 正常启动后端：`python dev-services.py start backend`
2. 执行重启：`python dev-services.py restart backend` → 应成功，无 `AccessDenied` 崩溃
3. 启动两个不同项目的后端（不同端口）→ 重启其中一个 → 另一个不应被影响
4. 权限不足场景：以更高权限启动 Python 进程占用端口 → 以普通用户运行重启 → 应记录错误并提示用户手动处理（taskkill 同样需要提升权限）
5. 验证孤儿子进程清理：启动 `uvicorn --reload` 后重启 → 确认无残留 Python 子进程

### 7.2 macOS 验证
1. 正常启动后端：`python dev-services.py start backend`
2. 执行重启：`python dev-services.py restart backend` → 应成功
3. 验证 `kill -9` 降级路径
4. 权限不足场景：以 `sudo` 启动进程 → 普通用户重启 → 应记录错误并提示用户手动处理

## 8. 回滚策略

由于仅修改 `dev-services.py` 单个文件，回滚即为恢复 git 上一个版本：
```bash
git checkout -- dev-services.py
```
