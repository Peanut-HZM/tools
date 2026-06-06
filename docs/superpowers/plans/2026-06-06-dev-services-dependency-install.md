# dev-services.py 启动前依赖自动安装 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 dev-services.py 启动服务前自动检查并安全安装缺失的依赖（Python pip / npm install）。

**Architecture:** 在现有 `dev-services.py` 中新增 `install_dependencies(svc)` 函数，按服务类型分发安装策略。在 `start_service()` 的端口检查之后、进程启动之前插入调用。安装失败不阻断启动，仅记录警告。

**Tech Stack:** Python 3.10+, subprocess, psutil

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `dev-services.py` | 修改 | 新增依赖安装函数，修改启动流程 |

---

### Task 1: 新增 Python 依赖检查辅助函数

**Files:**
- Modify: `dev-services.py`（在 `# 启动/停止` 章节之前插入新函数，约第 1413 行）

- [ ] **Step 1: 新增 `_parse_requirements_packages()` 函数**

  在 `dev-services.py` 中，找到 `# ============================================================` `# 启动/停止` 这一行（约第 1413 行），在其上方插入以下函数：

  ```python
  def _parse_requirements_packages(req_file: Path) -> list[str]:
      """从 requirements.txt 中提取包名列表（去掉版本约束）。

      跳过空行、注释行、以及 -e / -r / -c 等选项行。
      """
      packages = []
      if not req_file.exists():
          return packages
      try:
          for line in req_file.read_text(encoding="utf-8").splitlines():
              line = line.strip()
              if not line or line.startswith("#") or line.startswith("-"):
                  continue
              # 提取包名（忽略版本约束，如 "requests>=2.0" -> "requests"）
              pkg = re.split(r"[~=!<>,;\[\]]", line)[0].strip()
              if pkg:
                  packages.append(pkg)
      except Exception:
          pass
      return packages
  ```

- [ ] **Step 2: 新增 `_check_python_import()` 函数**

  在同一位置继续插入：

  ```python
  def _check_python_import(python_exe: str, package: str) -> bool:
      """检查指定 Python 解释器是否可以导入某个包。"""
      try:
          result = subprocess.run(
              [python_exe, "-c", f"import {package}"],
              capture_output=True,
              timeout=5,
          )
          return result.returncode == 0
      except Exception:
          return False
  ```

- [ ] **Step 3: 新增 `_get_service_python()` 函数**

  在同一位置继续插入：

  ```python
  def _get_service_python(svc: Service) -> str:
      """获取服务对应的 Python 解释器路径。"""
      if svc.project_type == "python":
          # 从 start_cmd 中提取 python 解释器
          if svc.start_cmd and svc.start_cmd[0].endswith("python.exe"):
              return svc.start_cmd[0]
          # 尝试从项目目录找 venv
          for venv_path in [svc.project_dir / "venv", svc.project_dir / ".venv"]:
              venv_py = venv_path / "Scripts" / "python.exe" if sys.platform == "win32" else venv_path / "bin" / "python"
              if venv_py.exists():
                  return str(venv_py)
      return sys.executable
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add dev-services.py
  git commit -m "feat: 新增 Python 依赖检查辅助函数"
  ```

---

### Task 2: 实现 `install_dependencies()` 主函数

**Files:**
- Modify: `dev-services.py`（紧接 Task 1 的函数之后插入）

- [ ] **Step 1: 新增 `install_dependencies()` 函数**

  ```python
  def install_dependencies(svc: Service) -> bool:
      """根据服务类型安装缺失的依赖。

      返回 True 表示依赖已满足（或无需安装），
      False 表示检测到缺失但安装失败（不阻断启动）。
      """
      if svc.project_type == "python":
          return _install_python_dependencies(svc)
      if svc.project_type in ("vite", "taro", "uniapp", "next", "node-backend"):
          return _install_node_dependencies(svc)
      # spring-boot 依赖由 mvn/gradle 自动处理，暂不干预
      return True
  ```

- [ ] **Step 2: 新增 `_install_python_dependencies()` 函数**

  ```python
  def _install_python_dependencies(svc: Service) -> bool:
      """检查并安装 Python 缺失依赖。"""
      req_file = svc.project_dir / "requirements.txt"
      if not req_file.exists():
          return True

      packages = _parse_requirements_packages(req_file)
      if not packages:
          return True

      python_exe = _get_service_python(svc)

      # 取前 5 个关键包检查（避免过多导入检查耗时）
      check_packages = packages[:5]
      missing = [pkg for pkg in check_packages if not _check_python_import(python_exe, pkg)]

      if not missing:
          log(f"[{svc.name}] Python 依赖已满足", "DEBUG")
          return True

      log(f"[{svc.name}] 检测到缺失依赖: {', '.join(missing)}，开始安装...", "INFO")

      try:
          result = subprocess.run(
              [python_exe, "-m", "pip", "install", "-r", str(req_file)],
              capture_output=True,
              text=True,
              timeout=120,
          )
          if result.returncode == 0:
              log(f"[{svc.name}] pip install 成功", "SUCCESS")
              return True
          else:
              stderr = result.stderr[-500:] if result.stderr else ""
              log(f"[{svc.name}] pip install 失败: {stderr}", "WARN")
              return False
      except subprocess.TimeoutExpired:
          log(f"[{svc.name}] pip install 超时（120s）", "WARN")
          return False
      except Exception as e:
          log(f"[{svc.name}] pip install 异常: {e}", "WARN")
          return False
  ```

- [ ] **Step 3: 新增 `_install_node_dependencies()` 函数**

  ```python
  def _install_node_dependencies(svc: Service) -> bool:
      """检查并安装 Node.js 缺失依赖。"""
      node_modules = svc.project_dir / "node_modules"
      if node_modules.exists() and any(node_modules.iterdir()):
          log(f"[{svc.name}] node_modules 已存在", "DEBUG")
          return True

      pkg_manager = _get_package_manager(svc.project_dir)
      log(f"[{svc.name}] node_modules 缺失，开始安装依赖...", "INFO")

      try:
          result = subprocess.run(
              [pkg_manager, "install"],
              cwd=str(svc.project_dir),
              capture_output=True,
              text=True,
              timeout=180,
          )
          if result.returncode == 0:
              log(f"[{svc.name}] {pkg_manager} install 成功", "SUCCESS")
              return True
          else:
              stderr = result.stderr[-500:] if result.stderr else ""
              log(f"[{svc.name}] {pkg_manager} install 失败: {stderr}", "WARN")
              return False
      except subprocess.TimeoutExpired:
          log(f"[{svc.name}] {pkg_manager} install 超时（180s）", "WARN")
          return False
      except Exception as e:
          log(f"[{svc.name}] {pkg_manager} install 异常: {e}", "WARN")
          return False
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add dev-services.py
  git commit -m "feat: 实现 install_dependencies() 按类型分发安装"
  ```

---

### Task 3: 修改 `start_service()` 启动流程

**Files:**
- Modify: `dev-services.py:1417-1470`（`start_service` 函数）

- [ ] **Step 1: 在端口检查后插入依赖安装步骤**

  找到 `start_service()` 函数，定位到以下代码段（约第 1436 行，端口检查之后）：

  ```python
      # 检查端口占用
      in_use, pids = check_port(svc.port)
      if in_use:
          ...

      # 启动进程
      cmd = svc.start_cmd
  ```

  在 `# 启动进程` 注释之前插入：

  ```python
      # 安装缺失依赖（失败不阻断启动）
      install_dependencies(svc)
  ```

  修改后的代码结构应为：

  ```python
  def start_service(svc: Service) -> bool:
      """启动单个服务"""
      log_section(f"启动 {svc.name} ({svc.type_label()})")

      # 确保目录存在
      if not svc.project_dir.exists():
          log(f"项目目录不存在: {svc.project_dir}", "ERROR")
          return False

      if svc.project_type == "python":
          cleanup_orphan_python_children(svc.project_dir)

      # 检查端口占用
      in_use, pids = check_port(svc.port)
      if in_use:
          alive_pids = [pid for pid in pids if _pid_alive(pid)]
          if alive_pids:
              log(f"端口 {svc.port} 已被占用 (PID: {', '.join(map(str, alive_pids))})，先停止...", "WARN")
              kill_service(svc)
              time.sleep(3)
          else:
              log(f"端口 {svc.port} 有残留连接 (PID 已不存在)，直接启动...", "WARN")

      # 【新增】安装缺失依赖（失败不阻断启动）
      install_dependencies(svc)

      # 启动进程
      cmd = svc.start_cmd
      ...
  ```

- [ ] **Step 2: Commit**

  ```bash
  git add dev-services.py
  git commit -m "feat: 启动服务前自动检查并安装缺失依赖"
  ```

---

### Task 4: 功能验证

**Files:**
- 无需修改文件，仅验证

- [ ] **Step 1: 验证 Python 后端依赖自动安装**

  1. 先停止后端：`python dev-services.py stop backend`
  2. 在虚拟环境中卸载一个已安装的包：
     ```bash
     cd backend
     .\venv\Scripts\python.exe -m pip uninstall apscheduler -y
     ```
  3. 重启后端：`python dev-services.py restart backend`
  4. **预期结果**：
     - 日志中出现 `[Backend 后端] 检测到缺失依赖: apscheduler，开始安装...`
     - 随后出现 `pip install 成功`
     - 后端正常启动，健康检查通过

- [ ] **Step 2: 验证前端依赖自动安装**

  1. 先停止前端：`python dev-services.py stop frontend`
  2. 临时重命名 `frontend/node_modules`：
     ```bash
     cd frontend
     mv node_modules node_modules.bak
     ```
  3. 重启前端：`python dev-services.py restart frontend`
  4. **预期结果**：
     - 日志中出现 `[Toolbox 前端] node_modules 缺失，开始安装依赖...`
     - 随后出现 `npm install 成功`（或 `pnpm install 成功`）
     - 前端正常启动，健康检查通过
  5. 恢复：`mv node_modules.bak node_modules`

- [ ] **Step 3: 验证依赖已满足时跳过安装**

  1. 确保前后端依赖都已安装
  2. 再次运行 `python dev-services.py restart`
  3. **预期结果**：
     - DEBUG 日志中出现 `Python 依赖已满足` / `node_modules 已存在`
     - 启动速度不受影响

- [ ] **Step 4: Commit 验证结果（如无问题则无需额外提交）**

  ```bash
  git log --oneline -5
  ```

---

## Self-Review Checklist

- [ ] **Spec 覆盖**：设计要求中「Python 后端检查 key imports」「前端检查 node_modules」「安装失败不阻断启动」均有对应 Task
- [ ] **无占位符**：所有步骤包含完整代码和命令，无 "TBD"/"TODO"
- [ ] **类型一致**：`_parse_requirements_packages` 返回 `list[str]`，`install_dependencies` 返回 `bool`，与使用处一致
- [ ] **路径正确**：所有文件路径使用正斜杠或 `Path` 对象，跨平台兼容
