"""
Author: Peanut
Created: 2026-04-25
Purpose: 前后端服务管理脚本，支持彩色日志、健康检查、前台/后台双模式、kill/logs 子命令
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import psutil
except ImportError:
    # 自动切换到后端虚拟环境重试
    venv_python = None
    script_dir = Path(__file__).parent.resolve()
    if sys.platform == "win32":
        venv_python = script_dir / "backend" / "venv" / "Scripts" / "python.exe"
    else:
        venv_python = script_dir / "backend" / "venv" / "bin" / "python"

    if venv_python.exists():
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)
    else:
        print("错误: 需要 psutil 库")
        print("  macOS/Linux: pip3 install psutil  或  python3 -m pip install psutil")
        print("  Windows:     pip install psutil")
        print("  或先启动后端虚拟环境: cd backend && source venv/bin/activate")
        sys.exit(1)

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import http.client
    import urllib.request

# ============================================================
# 常量定义
# ============================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_PORT = 19092
FRONTEND_PORT = 5178
LOG_DIR = PROJECT_ROOT / "logs"
BACKEND_LOG = LOG_DIR / "backend.log"
FRONTEND_LOG = LOG_DIR / "frontend.log"

LOG_DIR.mkdir(exist_ok=True)

NPM_EXE = shutil.which("pnpm") or shutil.which("npm") or "pnpm"

# ANSI 颜色码
COLORS = {
    "INFO": "\033[37m",       # 白色
    "SUCCESS": "\033[32m",    # 绿色
    "WARN": "\033[33m",       # 黄色
    "ERROR": "\033[31m",      # 红色
    "DEBUG": "\033[36m",      # 青色
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "DIM": "\033[2m",
}

# Windows 启用 ANSI 支持
if sys.platform == "win32":
    import ctypes
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# 确保 UTF-8 输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 健康检查配置
HEALTH_CONFIG = {
    "backend": {
        "keyword": "Application startup complete",
        "url": f"http://127.0.0.1:{BACKEND_PORT}/docs",
        "log_file": BACKEND_LOG,
        "keyword_timeout": 60,
        "http_timeout": 30,
    },
    "frontend": {
        "keyword": "ready in",
        "url": f"http://localhost:{FRONTEND_PORT}",
        "log_file": FRONTEND_LOG,
        "keyword_timeout": 30,
        "http_timeout": 30,
    },
}


# ============================================================
# 日志系统
# ============================================================

def log(msg: str, level: str = "INFO"):
    """输出带颜色和时间戳的日志，同时写入日志文件"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = COLORS.get(level, COLORS["INFO"])
    reset = COLORS["RESET"]

    # 控制台输出（带颜色）
    print(f"{color}[{timestamp}] [{level}]{reset} {msg}")

    # 日志文件输出（纯文本，无颜色）
    log_file = LOG_DIR / "dev_services.log"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{level}] {msg}\n")
    except Exception:
        pass


def log_separator():
    """输出分隔线"""
    print(f"\n{COLORS['DIM']}{'=' * 60}{COLORS['RESET']}\n")


def log_section(title: str):
    """输出章节标题"""
    print(f"\n{COLORS['BOLD']}  {title}{COLORS['RESET']}")
    print(f"{COLORS['DIM']}{'-' * 50}{COLORS['RESET']}")


# ============================================================
# 工具函数
# ============================================================

VENV_DIR = BACKEND_DIR / "venv"
VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe" if sys.platform == "win32" else VENV_DIR / "bin" / "python"


def get_backend_python() -> str:
    """获取后端使用的 Python 解释器路径
    优先级：backend/venv > 当前 Python
    """
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def ensure_venv() -> bool:
    """确保后端虚拟环境存在，如果不存在则创建并安装依赖"""
    if VENV_PYTHON.exists():
        return True

    log("后端虚拟环境不存在，正在创建...", "INFO")
    try:
        # 创建 venv
        subprocess.run(
            [sys.executable, "-m", "venv", str(VENV_DIR)],
            cwd=str(BACKEND_DIR),
            check=True,
            capture_output=True,
        )
        log(f"虚拟环境已创建: {VENV_DIR}", "SUCCESS")

        # 安装依赖
        req_file = BACKEND_DIR / "requirements.txt"
        if req_file.exists():
            log("正在安装后端依赖（可能需要几分钟）...", "INFO")
            result = subprocess.run(
                [str(VENV_PYTHON), "-m", "pip", "install", "-r", str(req_file)],
                cwd=str(BACKEND_DIR),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                log("后端依赖安装完成", "SUCCESS")
                return True
            else:
                log("依赖安装失败，请手动检查", "ERROR")
                log(result.stderr[-500:] if result.stderr else "", "ERROR")
                return False
        else:
            log("requirements.txt 不存在", "WARN")
            return True
    except subprocess.TimeoutExpired:
        log("依赖安装超时（5分钟），请手动运行 pip install", "ERROR")
        return False
    except Exception as e:
        log(f"创建虚拟环境失败: {e}", "ERROR")
        return False


def check_backend_dependencies() -> list[str]:
    """检查后端依赖是否满足，返回缺失的依赖列表"""
    missing = []
    python = get_backend_python()
    try:
        result = subprocess.run(
            [python, "-c", "import uvicorn, fastapi"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            missing.append("后端依赖")
    except Exception:
        missing.append("后端依赖")
    return missing


def _get_pids_by_port_fallback(port: int) -> list:
    """macOS/Linux 兼容：通过 lsof 获取占用指定端口的 PID"""
    pids = []
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                try:
                    pids.append(int(line.strip()))
                except ValueError:
                    continue
    except Exception:
        pass
    return pids


def check_port(port: int) -> tuple:
    """检查端口是否被占用，返回 (是否占用, 占用进程的PID列表)"""
    pids = []
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                if conn.pid:
                    pids.append(conn.pid)
    except psutil.AccessDenied:
        # macOS 非 root 用户禁止 net_connections，使用 lsof fallback
        pids = _get_pids_by_port_fallback(port)
    except Exception:
        pids = _get_pids_by_port_fallback(port)

    if pids:
        return True, pids
    return False, []


def _pid_alive(pid: int) -> bool:
    """检查进程是否存活"""
    try:
        psutil.Process(pid)
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def get_active_pid_on_port(port: int) -> Optional[int]:
    """获取端口上实际存活的 PID（过滤僵尸进程）"""
    in_use, pids = check_port(port)
    if not in_use:
        return None
    # 优先返回存活的进程
    for pid in pids:
        try:
            psutil.Process(pid)
            return pid
        except psutil.NoSuchProcess:
            continue
    # 如果都不存在，返回第一个
    return pids[0] if pids else None


def find_process_by_port(port: int) -> list:
    """查找占用指定端口的存活进程 PID（过滤僵尸进程）"""
    pids = set()
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr and conn.laddr.port == port:
                if conn.pid and conn.pid != os.getpid():
                    try:
                        psutil.Process(conn.pid)
                        pids.add(conn.pid)
                    except psutil.NoSuchProcess:
                        continue
    except psutil.AccessDenied:
        # macOS fallback
        for pid in _get_pids_by_port_fallback(port):
            if pid != os.getpid():
                try:
                    psutil.Process(pid)
                    pids.add(pid)
                except psutil.NoSuchProcess:
                    continue
    except Exception:
        for pid in _get_pids_by_port_fallback(port):
            if pid != os.getpid():
                try:
                    psutil.Process(pid)
                    pids.add(pid)
                except psutil.NoSuchProcess:
                    continue
    return sorted(pids)


def get_last_lines(file_path: Path, n: int = 20) -> list:
    """读取日志文件最后 N 行"""
    if not file_path.exists():
        return []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            return lines[-n:]
    except Exception:
        return []


def http_get(url: str, timeout: int = 10) -> bool:
    """发送 HTTP GET 请求，返回是否成功（200）"""
    if HAS_REQUESTS:
        try:
            resp = _requests.get(url, timeout=timeout)
            return resp.status_code == 200
        except Exception:
            return False
    else:
        # 标准库 fallback
        try:
            from urllib.request import urlopen
            resp = urlopen(url, timeout=timeout)
            return resp.status == 200
        except Exception:
            return False


# ============================================================
# 进程管理
# ============================================================

def kill_process(pid: int, graceful: bool = True):
    """终止进程
    graceful=True: 先 terminate，等待 3s 后未退出则 kill
    graceful=False: 直接 kill
    """
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
    except psutil.NoSuchProcess:
        log(f"进程 {pid} 已不存在", "INFO")
        return

    if graceful:
        proc.terminate()
        try:
            proc.wait(timeout=3)
            log(f"{proc_name} (PID {pid}) 已停止", "SUCCESS")
        except psutil.TimeoutExpired:
            try:
                proc.kill()
                proc.wait(timeout=2)
            except (psutil.TimeoutExpired, psutil.NoSuchProcess, OSError):
                # kill 后仍然超时或进程已消失，视为已终止
                pass
            log(f"{proc_name} (PID {pid}) 已强制终止", "WARN")
    else:
        proc.kill()
        try:
            proc.wait(timeout=2)
        except Exception:
            pass
        log(f"{proc_name} (PID {pid}) 已强制终止", "WARN")


def stop_service(name: str, port: int):
    """优雅停止指定服务"""
    log(f"停止 {name} 服务 (端口 {port})...", "INFO")
    pids = find_process_by_port(port)
    if pids:
        for pid in pids:
            kill_process(pid, graceful=True)
    else:
        log(f"{name} 未运行", "INFO")


def kill_service(name: str, port: int):
    """强制终止指定服务"""
    log(f"强制终止 {name} 服务 (端口 {port})...", "WARN")
    pids = find_process_by_port(port)
    if pids:
        for pid in pids:
            kill_process(pid, graceful=False)
    else:
        log(f"{name} 未运行", "INFO")


def stop_all(backend_only: bool = False, frontend_only: bool = False):
    """停止所有服务"""
    log_section("停止服务")
    if not frontend_only:
        stop_service("后端", BACKEND_PORT)
    if not backend_only:
        stop_service("前端", FRONTEND_PORT)
    log_separator()


# ============================================================
# 健康检查
# ============================================================

def wait_for_log_keyword(log_file: Path, keyword: str, timeout: int = 30) -> bool:
    """轮询日志文件，等待关键字出现"""
    log(f'等待日志关键字: "{keyword}"', "DEBUG")
    start_time = time.time()

    # 等待日志文件出现
    while time.time() - start_time < timeout:
        if log_file.exists():
            break
        time.sleep(0.5)

    # 额外等待 2 秒，让进程开始写入日志
    time.sleep(2)

    while time.time() - start_time < timeout:
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                # 每次重新读取整个文件，避免 "w" 模式覆盖导致位置失效
                content = f.read()
                if keyword in content:
                    return True
        except Exception:
            pass

        time.sleep(1)

    return False


def http_health_check(name: str, url: str, timeout: int = 10) -> bool:
    """HTTP 健康检查"""
    log(f"HTTP 健康检查: {url}", "DEBUG")
    start_time = time.time()

    while time.time() - start_time < timeout:
        if http_get(url):
            return True
        time.sleep(0.5)

    return False


def check_health(name: str) -> bool:
    """两阶段健康检查：先日志关键字，再 HTTP 探测"""
    config = HEALTH_CONFIG[name]
    log_file = config["log_file"]
    keyword = config["keyword"]
    url = config["url"]
    keyword_timeout = config["keyword_timeout"]
    http_timeout = config["http_timeout"]

    log(f"健康检查开始: {name}", "INFO")

    # 阶段 1：等待日志关键字
    if wait_for_log_keyword(log_file, keyword, keyword_timeout):
        log(f"[1/2] 日志就绪: {name}", "SUCCESS")
    else:
        log(f"[1/2] 日志关键字超时: {name}", "ERROR")
        _print_log_tail(name, log_file)
        return False

    # 阶段 2：HTTP 探测
    if http_health_check(name, url, http_timeout):
        log(f"[2/2] HTTP 就绪: {name} ({url})", "SUCCESS")
        return True
    else:
        log(f"[2/2] HTTP 健康检查失败: {name}", "ERROR")
        _print_log_tail(name, log_file)
        return False


def _print_log_tail(name: str, log_file: Path):
    """输出日志文件最后 20 行帮助诊断"""
    tail_lines = get_last_lines(log_file, 20)
    if tail_lines:
        log(f"{name} 日志最后 20 行:", "WARN")
        for line in tail_lines:
            print(f"  {line.rstrip()}")


# ============================================================
# 前台模式
# ============================================================

def run_foreground(backend_only: bool = False, frontend_only: bool = False):
    """前台模式运行服务，实时显示日志，Ctrl+C 优雅停止"""
    procs = []

    def cleanup():
        log("正在停止服务...", "WARN")
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        for p in procs:
            try:
                p.wait(timeout=3)
            except Exception:
                p.kill()
        log("所有服务已停止", "INFO")

    try:
        if not frontend_only:
            log_section("启动后端服务（前台模式）")
            be_proc = _start_backend_process(foreground=True)
            if be_proc:
                procs.append(be_proc)

        if not backend_only:
            log_section("启动前端服务（前台模式）")
            fe_proc = _start_frontend_process(foreground=True)
            if fe_proc:
                procs.append(fe_proc)

        log_separator()
        log("按 Ctrl+C 停止所有服务", "INFO")
        log_separator()

        # 等待第一个进程结束
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        cleanup()


def _start_backend_process(foreground: bool = False) -> subprocess.Popen:
    """启动后端进程"""
    python_exe = get_backend_python()

    cmd = [
        python_exe, "-m", "uvicorn",
        "app.main:app",
        "--reload",
        "--port", str(BACKEND_PORT),
        "--host", "127.0.0.1",
    ]

    try:
        if foreground:
            proc = subprocess.Popen(
                cmd,
                cwd=str(BACKEND_DIR),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )
        else:
            with open(BACKEND_LOG, "w", encoding="utf-8") as f:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(BACKEND_DIR),
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
                    stdin=subprocess.DEVNULL,
                )
        return proc
    except Exception as e:
        log(f"后端启动失败: {e}", "ERROR")
        return None


def _start_frontend_process(foreground: bool = False) -> subprocess.Popen:
    """启动前端进程"""
    try:
        node_exe = shutil.which("node") or "node"
        vite_js = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"

        if vite_js.exists():
            cmd = [node_exe, str(vite_js)]
        else:
            cmd = [NPM_EXE, "run", "dev"]

        if foreground:
            proc = subprocess.Popen(
                cmd,
                cwd=str(FRONTEND_DIR),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )
        else:
            with open(FRONTEND_LOG, "w", encoding="utf-8") as f:
                creationflags = 0
                if sys.platform == "win32":
                    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(FRONTEND_DIR),
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    creationflags=creationflags,
                )
        return proc
    except Exception as e:
        log(f"前端启动失败: {e}", "ERROR")
        return None


# ============================================================
# 启动服务（后台模式）
# ============================================================

def start_backend() -> bool:
    """启动后端服务并等待就绪"""
    log_section("启动后端服务")

    # 确保虚拟环境存在
    if not ensure_venv():
        log("虚拟环境准备失败，请手动检查", "ERROR")
        return False

    # 检查端口占用
    in_use, pids = check_port(BACKEND_PORT)
    if in_use:
        # 过滤出存活的 PID
        alive_pids = [pid for pid in pids if _pid_alive(pid)]
        if alive_pids:
            log(f"端口 {BACKEND_PORT} 已被占用 (PID: {', '.join(map(str, alive_pids))})，先停止...", "WARN")
            kill_service("后端", BACKEND_PORT)
            time.sleep(3)
        else:
            log(f"端口 {BACKEND_PORT} 有残留连接 (PID 已不存在)，直接启动...", "WARN")

    proc = _start_backend_process(foreground=False)
    if not proc:
        return False

    log(f"后端进程已启动 (PID: {proc.pid})", "INFO")

    # 健康检查
    if check_health("backend"):
        log(f"后端服务已就绪 http://127.0.0.1:{BACKEND_PORT}", "SUCCESS")
        return True
    else:
        log("后端服务启动失败", "ERROR")
        return False


def start_frontend() -> bool:
    """启动前端服务并等待就绪"""
    log_section("启动前端服务")

    # 检查端口占用
    in_use, pids = check_port(FRONTEND_PORT)
    if in_use:
        alive_pids = [pid for pid in pids if _pid_alive(pid)]
        if alive_pids:
            log(f"端口 {FRONTEND_PORT} 已被占用 (PID: {', '.join(map(str, alive_pids))})，先停止...", "WARN")
            kill_service("前端", FRONTEND_PORT)
            time.sleep(3)
        else:
            log(f"端口 {FRONTEND_PORT} 有残留连接 (PID 已不存在)，直接启动...", "WARN")

    proc = _start_frontend_process(foreground=False)
    if not proc:
        return False

    log(f"前端进程已启动 (PID: {proc.pid})", "INFO")

    # 健康检查
    if check_health("frontend"):
        log(f"前端服务已就绪 http://localhost:{FRONTEND_PORT}", "SUCCESS")
        return True
    else:
        log("前端服务启动失败", "ERROR")
        return False


# ============================================================
# 状态查询
# ============================================================

def status():
    """查看服务状态"""
    log_section("服务状态")

    for name, port in [("后端", BACKEND_PORT), ("前端", FRONTEND_PORT)]:
        pid = get_active_pid_on_port(port)
        if pid:
            try:
                proc = psutil.Process(pid)
                cpu = proc.cpu_percent(interval=0.1)
                mem = proc.memory_info().rss / 1024 / 1024
                status_icon = "运行中"
                color = COLORS["SUCCESS"]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                cpu = mem = 0
                status_icon = "异常"
                color = COLORS["ERROR"]

            reset = COLORS["RESET"]
            cpu_str = f"{cpu:.1f}%" if cpu else "-"
            mem_str = f"{mem:.1f}MB" if mem else "-"
            print(f"  {color}[{name}]{reset}  端口: {port}  状态: {status_icon}  PID: {pid}  CPU: {cpu_str}  内存: {mem_str}")
        else:
            print(f"  {COLORS['INFO']}[{name}]{COLORS['RESET']}  端口: {port}  状态: 未运行")

    log_separator()
    print(f"  {COLORS['BOLD']}访问地址:{COLORS['RESET']}")
    print(f"    前端: {COLORS['SUCCESS']}http://localhost:{FRONTEND_PORT}{COLORS['RESET']}")
    print(f"    后端: {COLORS['SUCCESS']}http://127.0.0.1:{BACKEND_PORT}{COLORS['RESET']}")
    print(f"    API 文档: {COLORS['SUCCESS']}http://127.0.0.1:{BACKEND_PORT}/docs{COLORS['RESET']}")

    log_separator()
    print(f"  {COLORS['BOLD']}日志文件:{COLORS['RESET']}")
    print(f"    后端: {BACKEND_LOG}")
    print(f"    前端: {FRONTEND_LOG}")
    log_separator()


# ============================================================
# 日志查看
# ============================================================

def tail_logs(target: str):
    """实时查看日志（tail -f 效果）"""
    log_file = None

    if target == "backend":
        log_file = BACKEND_LOG
    elif target == "frontend":
        log_file = FRONTEND_LOG
    elif target == "all":
        # 同时查看两个日志
        _tail_multi([BACKEND_LOG, FRONTEND_LOG])
        return
    else:
        log(f"未知目标: {target} (backend/frontend/all)", "ERROR")
        return

    if not log_file or not log_file.exists():
        log(f"日志文件不存在: {log_file}", "ERROR")
        return

    log(f"实时查看 {target} 日志 (Ctrl+C 退出)...", "INFO")

    if sys.platform == "win32":
        # Windows 使用 PowerShell Get-Content -Wait
        try:
            subprocess.run(
                ["powershell", "-Command", f"Get-Content -Wait -Tail 50 '{log_file}'"],
                check=True,
            )
        except KeyboardInterrupt:
            pass
        except Exception:
            # Fallback: Python 轮询
            _tail_python(log_file)
    else:
        try:
            subprocess.run(["tail", "-f", str(log_file)], check=True)
        except KeyboardInterrupt:
            pass


def _tail_multi(log_files: list):
    """同时查看多个日志文件（Python 轮询实现）"""
    positions = {}
    for lf in log_files:
        positions[lf] = 0

    log("实时查看所有日志 (Ctrl+C 退出)...", "INFO")

    try:
        while True:
            new_output = False
            for lf in log_files:
                try:
                    with open(lf, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(positions[lf])
                        lines = f.readlines()
                        positions[lf] = f.tell()
                        for line in lines:
                            prefix = "B " if lf == BACKEND_LOG else "F "
                            print(f"{prefix}{line.rstrip()}")
                            new_output = True
                except Exception:
                    pass

            if not new_output:
                time.sleep(1)
    except KeyboardInterrupt:
        pass


def _tail_python(log_file: Path):
    """Python 实现的 tail -f"""
    position = 0
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, 2)
            position = f.tell()
            # 先输出最后 50 行
            f.seek(0)
            lines = f.readlines()
            for line in lines[-50:]:
                print(line.rstrip())

        while True:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(position)
                lines = f.readlines()
                position = f.tell()
                for line in lines:
                    print(line.rstrip())

            if not lines:
                time.sleep(1)
    except KeyboardInterrupt:
        pass


# ============================================================
# 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="工具箱前后端服务管理脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python dev_services.py                  启动前后端服务（默认）
  python dev_services.py start            启动前后端服务
  python dev_services.py start -f         前台模式启动
  python dev_services.py stop             停止前后端服务
  python dev_services.py restart          重启前后端服务
  python dev_services.py status           查看服务状态
  python dev_services.py kill backend     强制终止后端服务
  python dev_services.py kill all         强制终止所有服务
  python dev_services.py logs backend     查看后端实时日志
  python dev_services.py start --backend-only   只启动后端
  python dev_services.py start --frontend-only  只启动前端
""",
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="start",
        choices=["start", "stop", "restart", "status", "kill", "logs"],
        help="操作: start|stop|restart|status|kill|logs (默认: start)",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="目标服务: backend|frontend|all (kill 和 logs 子命令使用)",
    )
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="只操作后端",
    )
    parser.add_argument(
        "--frontend-only",
        action="store_true",
        help="只操作前端",
    )
    parser.add_argument(
        "--foreground", "-f",
        action="store_true",
        help="前台模式运行（仅 start 有效）",
    )

    args = parser.parse_args()

    # ---- start ----
    if args.action == "start":
        if args.foreground:
            run_foreground(
                backend_only=args.backend_only,
                frontend_only=args.frontend_only,
            )
            return

        log_separator()
        log("工具箱服务管理器", "INFO")
        log_separator()

        if args.backend_only:
            ok = start_backend()
            sys.exit(0 if ok else 1)
        elif args.frontend_only:
            ok = start_frontend()
            sys.exit(0 if ok else 1)
        else:
            be_ok = start_backend()
            fe_ok = start_frontend()

            if be_ok and fe_ok:
                log_section("所有服务已就绪")
                print(f"  前端: {COLORS['SUCCESS']}http://localhost:{FRONTEND_PORT}{COLORS['RESET']}")
                print(f"  后端: {COLORS['SUCCESS']}http://127.0.0.1:{BACKEND_PORT}{COLORS['RESET']}")
                log_separator()
            elif be_ok or fe_ok:
                log("部分服务启动失败，请检查日志", "WARN")
                sys.exit(1)
            else:
                log("所有服务启动失败", "ERROR")
                sys.exit(1)
            return

    # ---- stop ----
    if args.action == "stop":
        stop_all(
            backend_only=args.backend_only,
            frontend_only=args.frontend_only,
        )
        log("所有服务已停止", "SUCCESS")
        return

    # ---- restart ----
    if args.action == "restart":
        stop_all(
            backend_only=args.backend_only,
            frontend_only=args.frontend_only,
        )
        time.sleep(1)
        # 直接调用 start 逻辑，避免递归调用 main()
        args.action = "start"
        # 执行 start 逻辑（内联）
        if args.foreground:
            run_foreground(
                backend_only=args.backend_only,
                frontend_only=args.frontend_only,
            )
            return

        log_separator()
        log("工具箱服务管理器", "INFO")
        log_separator()

        if args.backend_only:
            ok = start_backend()
            sys.exit(0 if ok else 1)
        elif args.frontend_only:
            ok = start_frontend()
            sys.exit(0 if ok else 1)
        else:
            be_ok = start_backend()
            fe_ok = start_frontend()

            if be_ok and fe_ok:
                log_section("所有服务已就绪")
                print(f"  前端: {COLORS['SUCCESS']}http://localhost:{FRONTEND_PORT}{COLORS['RESET']}")
                print(f"  后端: {COLORS['SUCCESS']}http://127.0.0.1:{BACKEND_PORT}{COLORS['RESET']}")
                log_separator()
            elif be_ok or fe_ok:
                log("部分服务启动失败，请检查日志", "WARN")
                sys.exit(1)
            else:
                log("所有服务启动失败", "ERROR")
                sys.exit(1)
            return

    # ---- status ----
    if args.action == "status":
        status()
        return

    # ---- kill ----
    if args.action == "kill":
        target = args.target or "all"
        log_section("强制终止服务")
        if target in ("backend", "all"):
            if not args.frontend_only:
                kill_service("后端", BACKEND_PORT)
        if target in ("frontend", "all"):
            if not args.backend_only:
                kill_service("前端", FRONTEND_PORT)
        log_separator()
        return

    # ---- logs ----
    if args.action == "logs":
        target = args.target or "all"
        tail_logs(target)
        return


if __name__ == "__main__":
    main()
