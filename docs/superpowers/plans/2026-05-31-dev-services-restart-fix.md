# dev-services.py 重启可靠性增强实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `dev-services.py` 重启服务时的 `psutil.AccessDenied` 崩溃，并增强进程身份验证防止误杀其他项目进程

**Architecture:** 新增 `verify_belongs_to_service` 三层验证函数，增强 `kill_process` 异常处理（捕获 `AccessDenied`/`NoSuchProcess` + 跨平台 `taskkill`/`kill -9` 降级），将 `stop_service`/`kill_service` 改为接受 `Service` 对象并执行身份验证

**Tech Stack:** Python 3.10+, psutil, subprocess

---

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `dev-services.py` | 修改 | 唯一改动文件，新增验证函数 + 增强进程终止 + 更新调用点 |

---

### Task 1: 新增进程身份验证函数 `verify_belongs_to_service`

**Files:**
- Modify: `dev-services.py`（在 `kill_process` 函数之前插入新函数）

- [ ] **Step 1: 在 `kill_process` 函数定义之前插入 `verify_belongs_to_service`**

在 `dev-services.py:1078` 之前插入以下函数：

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

    # 第二层：cmdline 特征验证（排除通用参数，避免误匹配）
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
```

- [ ] **Step 2: Commit**

```bash
git add dev-services.py
git commit -m "feat: 新增进程身份验证函数 verify_belongs_to_service"
```

---

### Task 2: 增强 `kill_process` 异常处理与跨平台降级

**Files:**
- Modify: `dev-services.py:1078-1106`

- [ ] **Step 1: 替换 `kill_process` 函数**

将 `dev-services.py:1078-1106` 的 `kill_process` 函数替换为：

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

- [ ] **Step 2: Commit**

```bash
git add dev-services.py
git commit -m "fix: 增强 kill_process 异常处理，支持 taskkill/kill-9 跨平台降级"
```

---

### Task 3: 增强 `kill_process_tree` 透传 `use_taskkill` 参数

**Files:**
- Modify: `dev-services.py:1117-1130`

- [ ] **Step 1: 替换 `kill_process_tree` 函数**

将 `dev-services.py:1117-1130` 替换为：

```python
def kill_process_tree(pid: int, graceful: bool = True, use_taskkill: bool = True):
    """终止进程树，避免 uvicorn --reload 子进程残留并继续占用数据库连接。"""
    children = _iter_child_processes(pid)
    def _depth(proc):
        try:
            return len(proc.parents())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0

    for child in sorted(children, key=_depth, reverse=True):
        if child.pid == os.getpid():
            continue
        kill_process(child.pid, graceful=graceful, use_taskkill=use_taskkill)
    kill_process(pid, graceful=graceful, use_taskkill=use_taskkill)
```

- [ ] **Step 2: Commit**

```bash
git add dev-services.py
git commit -m "fix: kill_process_tree 透传 use_taskkill 参数"
```

---

### Task 4: 修改 `stop_service` / `kill_service` 签名并增加身份验证

**Files:**
- Modify: `dev-services.py:1155-1174`

- [ ] **Step 1: 替换 `stop_service` 和 `kill_service` 函数**

将 `dev-services.py:1155-1174` 替换为：

```python
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

- [ ] **Step 2: Commit**

```bash
git add dev-services.py
git commit -m "feat: stop_service/kill_service 增加进程身份验证"
```

---

### Task 5: 更新所有调用点

**Files:**
- Modify: `dev-services.py:1310`, `dev-services.py:1385`, `dev-services.py:1674`, `dev-services.py:1147`

- [ ] **Step 1: 修改 `start_service` 中的 `kill_service` 调用**

在 `dev-services.py:1310`，将：
```python
            kill_service(svc.name, svc.port)
```
替换为：
```python
            kill_service(svc)
```

- [ ] **Step 2: 修改 `stop_service_wrapper` 中的 `stop_service` 调用**

在 `dev-services.py:1385`，将：
```python
    stop_service(svc.name, svc.port)
```
替换为：
```python
    stop_service(svc)
```

- [ ] **Step 3: 修改 `main()` kill action 中的 `kill_service` 调用**

在 `dev-services.py:1674`，将：
```python
                    kill_service(svc.name, svc.port)
```
替换为：
```python
                    kill_service(svc)
```

- [ ] **Step 4: 修改 `cleanup_orphan_python_children` 中的 `kill_process` 调用**

在 `dev-services.py:1147`，将：
```python
                kill_process(proc.pid, graceful=False)
```
替换为：
```python
                kill_process(proc.pid, graceful=False, use_taskkill=True)
```

- [ ] **Step 5: Commit**

```bash
git add dev-services.py
git commit -m "fix: 更新所有 stop_service/kill_service 调用点，适配新签名"
```

---

### Task 6: 语法检查

**Files:**
- Modify: `dev-services.py`

- [ ] **Step 1: 运行 Python 语法检查**

```bash
cd G:\IdeaProjects\tools
python -m py_compile dev-services.py
```

Expected: 无输出（表示语法正确）

- [ ] **Step 2: 如有语法错误，修复后重新检查**

---

### Task 7: 功能验证

**Files:**
- Modify: `dev-services.py`

- [ ] **Step 1: 查看服务状态**

```bash
cd G:\IdeaProjects\tools
python dev-services.py status
```

Expected: 正常显示服务状态，无异常

- [ ] **Step 2: 启动后端服务**

```bash
python dev-services.py start backend
```

Expected: 后端成功启动，日志显示服务就绪

- [ ] **Step 3: 重启后端服务（核心测试）**

```bash
python dev-services.py restart backend
```

Expected:
- 停止阶段：显示 `停止 Backend 后端 (端口 19092)...`
- 如果端口被占用：显示验证日志，进程被终止
- 启动阶段：后端重新启动成功
- **绝不出现 `psutil.AccessDenied` 崩溃**

- [ ] **Step 4: 停止所有服务**

```bash
python dev-services.py stop
```

Expected: 所有服务正常停止

---

## 回滚策略

如实施过程中出现问题，一键回滚：
```bash
git checkout -- dev-services.py
```

---

## Spec 覆盖检查

| Spec 要求 | 对应任务 | 状态 |
|-----------|----------|------|
| 修复 `psutil.AccessDenied` 崩溃 | Task 2 | ✅ |
| 捕获 `psutil.NoSuchProcess` | Task 2 | ✅ |
| 跨平台 `taskkill` / `kill -9` 降级 | Task 2 | ✅ |
| 进程身份验证（cwd + cmdline + 端口） | Task 1, Task 4 | ✅ |
| cmdline 排除通用参数 | Task 1 | ✅ |
| `stop_service`/`kill_service` 接受 Service 对象 | Task 4 | ✅ |
| 更新所有调用点 | Task 5 | ✅ |
| `kill_process_tree` 透传 `use_taskkill` | Task 3 | ✅ |
| `cleanup_orphan_python_children` 更新 | Task 5 Step 4 | ✅ |
| 语法检查 | Task 6 | ✅ |
| 功能验证 | Task 7 | ✅ |
