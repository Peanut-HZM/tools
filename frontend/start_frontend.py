"""
Author: Peanut
Created: 2026-04-15
Purpose: 跨平台前端开发服务器启动脚本，支持后台启动、端口管理、依赖检查等
"""

import argparse
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

# Windows 控制台 UTF-8 支持
if platform.system() == "Windows":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    # 确保 Windows PATH 中包含 Node.js（必须在 reconfigure 之前设置）
    node_paths = [
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "nodejs",
        Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "nodejs",
        Path(r"F:\Program Files") / "nodejs",
        Path(r"G:\Program Files") / "nodejs",
    ]
    for np in node_paths:
        if np.exists() and (np / "node.exe").exists():
            os.environ["PATH"] = str(np) + os.pathsep + os.environ.get("PATH", "")
            break

try:
    import urllib.request
except ImportError:
    import urllib2 as urllib_request  # Python 2 兼容（实际不会用到）


# ---------------------------------------------------------------------------
# 彩色输出（跨平台）
# ---------------------------------------------------------------------------
class Colors:
    """ANSI 颜色代码"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"

    @classmethod
    def enable(cls):
        """Windows 下启用 ANSI 颜色"""
        if platform.system() == "Windows":
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 7
            )


def _color(text, color_code):
    return f"{color_code}{text}{Colors.RESET}"


def info(msg):
    print(f"{_color('ℹ', Colors.BLUE)} {msg}")


def success(msg):
    print(f"{_color('✓', Colors.GREEN)} {msg}")


def warn(msg):
    print(f"{_color('⚠', Colors.YELLOW)} {msg}")


def error(msg):
    print(f"{_color('✗', Colors.RED)} {msg}")


def header(msg):
    print(f"\n{_color('═' * 60, Colors.CYAN)}")
    print(f"{_color('  ' + msg, Colors.BOLD + Colors.CYAN)}")
    print(f"{_color('═' * 60, Colors.CYAN)}\n")


# ---------------------------------------------------------------------------
# 端口管理
# ---------------------------------------------------------------------------
def find_process_on_port(port):
    """查找占用指定端口的进程 PID"""
    system = platform.system()

    if system == "Windows":
        # Windows: 使用 netstat
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, encoding="gbk", errors="replace"
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    if pid.isdigit():
                        return int(pid)
        except Exception as e:
            warn(f"检查端口 {port} 时出错: {e}")

    else:
        # Mac/Linux: 使用 lsof
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True, text=True
            )
            if result.stdout.strip():
                return int(result.stdout.strip().splitlines()[0])
        except Exception as e:
            warn(f"检查端口 {port} 时出错: {e}")

    return None


def kill_process(pid, port):
    """终止指定 PID 的进程"""
    system = platform.system()

    try:
        if system == "Windows":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True)
        else:
            os.kill(pid, signal.SIGKILL)

        # 验证进程是否已终止
        time.sleep(0.5)
        if find_process_on_port(port) is None:
            success(f"已终止进程 {pid}（端口 {port}）")
            return True
    except Exception as e:
        error(f"终止进程 {pid} 失败: {e}")

    return False


def release_port(port):
    """检查并释放指定端口"""
    pid = find_process_on_port(port)
    if pid is None:
        return True

    warn(f"端口 {port} 被进程 {pid} 占用")
    return kill_process(pid, port)


# ---------------------------------------------------------------------------
# 依赖检查
# ---------------------------------------------------------------------------
def check_node_modules(frontend_dir):
    """检查 node_modules 是否存在"""
    return (frontend_dir / "node_modules").exists()


def check_npm():
    """检查 npm 是否可用"""
    try:
        subprocess.run(["npm", "--version"],
                       capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_dependencies(frontend_dir, verbose=False):
    """安装前端依赖"""
    if not check_npm():
        error("未找到 npm，请先安装 Node.js")
        return False

    header("安装依赖")
    cmd = ["npm", "install"]
    info(f"执行: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=str(frontend_dir),
                            capture_output=True, text=True)

    if result.returncode != 0:
        error("依赖安装失败")
        if verbose:
            print(result.stderr)
        return False

    success("依赖安装完成")
    return True


# ---------------------------------------------------------------------------
# 配置管理
# ---------------------------------------------------------------------------
def update_env_file(env_path, port, host, backend_url):
    """更新 .env 文件中的配置"""
    if not env_path.exists():
        warn(f".env 文件不存在: {env_path}")
        return

    lines = env_path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    modified = False

    for line in lines:
        if line.startswith("FRONTEND_PORT="):
            new_lines.append(f"FRONTEND_PORT={port}")
            modified = True
        elif line.startswith("VITE_API_PROXY_TARGET="):
            if backend_url:
                new_lines.append(f"VITE_API_PROXY_TARGET={backend_url}")
                modified = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # 如果没有修改任何行（比如 backend_url 没指定但文件里已有配置），说明不需要写回
    if modified:
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        info(f"已更新 .env: FRONTEND_PORT={port}" +
             (f", VITE_API_PROXY_TARGET={backend_url}" if backend_url else ""))


# ---------------------------------------------------------------------------
# 启动服务
# ---------------------------------------------------------------------------
def start_vite(frontend_dir, port, host, timeout=90, verbose=False):
    """后台启动 Vite 开发服务器并等待就绪"""
    env = os.environ.copy()

    # 确保 Windows PATH 中包含 Node.js（Git Bash 环境可能不包含）
    if platform.system() == "Windows":
        node_paths = [
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "nodejs",
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "nodejs",
            Path("F:\\Program Files") / "nodejs",
            Path("G:\\Program Files") / "nodejs",
        ]
        for np in node_paths:
            if np.exists() and (np / "node.exe").exists():
                env["PATH"] = str(np) + os.pathsep + env.get("PATH", "")
                break

    # 使用 node 直接调用 vite.js，绕过 npm.cmd 的 PATH 问题
    vite_js = frontend_dir / "node_modules" / "vite" / "bin" / "vite.js"
    if not vite_js.exists():
        # 备用路径
        vite_js = frontend_dir / "node_modules" / ".bin" / "vite.js"
    if not vite_js.exists():
        error(f"找不到 vite.js: {vite_js}")
        sys.exit(1)

    cmd = ["node", str(vite_js), "--port", str(port), "--host", host]
    info(f"启动命令: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        cwd=str(frontend_dir),
        stdout=None,
        stderr=subprocess.STDOUT,
        env=env,
    )

    info(f"等待开发服务器启动（超时 {timeout}s）...")
    start_time = time.time()
    ready = False

    while time.time() - start_time < timeout:
        # 检查进程是否还在运行
        rc = process.poll()
        if rc is not None:
            error(f"Vite 进程已退出，退出码 {rc}")
            sys.exit(1)

        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            s.close()
            if result == 0:
                ready = True
                break
        except Exception:
            pass
        time.sleep(0.5)

    if ready:
        return process
    else:
        error("开发服务器启动超时")
        process.terminate()
        sys.exit(1)


def get_local_ip():
    """获取本机局域网 IP"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="前端开发服务器启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python start_frontend.py                    # 使用默认配置启动
  python start_frontend.py --port 3000         # 使用端口 3000
  python start_frontend.py --backend-url http://192.168.1.100:19092
                                              # 指定远程后端地址
  python start_frontend.py --install-deps     # 强制重新安装依赖
  python start_frontend.py --verbose          # 输出详细日志
        """
    )
    parser.add_argument(
        "--port", type=int, default=None,
        help="自定义端口号（默认使用 .env 中的配置）"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0",
        help="绑定地址（默认 0.0.0.0）"
    )
    parser.add_argument(
        "--install-deps", action="store_true",
        help="强制重新安装前端依赖"
    )
    parser.add_argument(
        "--no-check-port", action="store_true",
        help="跳过端口占用检查"
    )
    parser.add_argument(
        "--backend-url", type=str, default=None,
        help="自定义后端代理地址（如 http://192.168.1.100:19092）"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="输出详细日志"
    )
    return parser.parse_args()


def main():
    Colors.enable()
    args = parse_args()

    header("前端开发服务器")

    # 确定项目路径
    frontend_dir = Path(__file__).resolve().parent
    env_path = frontend_dir / ".env"

    # 读取默认端口（从 .env 或 vite.config.ts）
    default_port = 5178
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("FRONTEND_PORT="):
                default_port = int(line.split("=", 1)[1].strip())
                break

    port = args.port or default_port
    host = args.host

    info(f"端口: {port}")
    info(f"绑定地址: {host}")
    if args.backend_url:
        info(f"后端代理: {args.backend_url}")

    # 1. 端口检查与释放
    if not args.no_check_port:
        header("端口检查")
        if not release_port(port):
            error(f"端口 {port} 释放失败，无法启动")
            sys.exit(1)
    else:
        info("跳过端口检查")

    # 2. 依赖检查
    if args.install_deps or not check_node_modules(frontend_dir):
        if not args.install_deps:
            warn("未找到 node_modules，正在安装依赖...")
        if not install_dependencies(frontend_dir, args.verbose):
            sys.exit(1)
    else:
        success("依赖已存在")

    # 3. 更新 .env 配置
    if args.port or args.backend_url:
        header("更新配置")
        update_env_file(env_path, port, host, args.backend_url)

    # 4. 启动 Vite（含就绪等待）
    header("启动开发服务器")
    process = start_vite(frontend_dir, port, host, verbose=args.verbose)

    # 5. 输出访问地址
    success("开发服务器已启动！")

    print()
    print(f"  {_color('本地访问:', Colors.BOLD)} http://localhost:{port}")
    local_ip = get_local_ip()
    if local_ip:
        print(f"  {_color('网络访问:', Colors.BOLD)} http://{local_ip}:{port}")
    print(f"  {_color('进程 PID:', Colors.BOLD)} {process.pid}")
    print()
    info("按 Ctrl+C 可停止进程（如在前台运行）")
    print()


if __name__ == "__main__":
    main()
