#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署脚本 - 用于部署前后端项目到服务器
"""

# ============ 依赖自举：缺包自动安装 ============
import importlib
import subprocess as _subprocess
import sys as _sys

_REQUIRED_PACKAGES = {
    "dotenv": "python-dotenv",
}

_missing = []
for _mod, _pip_name in _REQUIRED_PACKAGES.items():
    try:
        importlib.import_module(_mod)
    except ImportError:
        _missing.append(_pip_name)

if _missing:
    print(f"[deploy] 正在安装缺失依赖: {', '.join(_missing)}")
    _subprocess.check_call([_sys.executable, "-m", "pip", "install", *_missing])
    print("[deploy] 依赖安装完成，继续执行\n")

# ============ 正式导入 ============
import os
import sys
import subprocess
import shutil
import argparse
import shlex
import json
from pathlib import Path
from dotenv import load_dotenv

# 加载 deploy.env（可选，不存在则使用环境变量）
_deploy_env = Path(__file__).parent / "deploy.env"
if _deploy_env.exists():
    load_dotenv(_deploy_env)

# 服务器配置（从 deploy.env 或环境变量读取）
SERVER_HOST = os.getenv("SERVER_HOST", "")
SERVER_USER = os.getenv("SERVER_USER", "root")
SERVER_PORT = int(os.getenv("SERVER_PORT", "22"))
FRONTEND_DEPLOY_PATH = os.getenv("FRONTEND_DEPLOY_PATH", "/data/www/tools")
BACKEND_DEPLOY_PATH = os.getenv("BACKEND_DEPLOY_PATH", "/data/programs/tools")
DOMAIN = os.getenv("DOMAIN", "localhost")
BACKEND_SERVICE = os.getenv("BACKEND_SERVICE", "tools-backend.service")

# 部署校验：必须配置 SERVER_HOST
if not SERVER_HOST:
    print("错误: SERVER_HOST 未配置")
    print("请复制 deploy.env.example 为 deploy.env 并填入配置:")
    print("  cp deploy.env.example deploy.env")
    print("  然后编辑 deploy.env 填入你的服务器 IP")
    sys.exit(1)

# 项目路径
PROJECT_ROOT = Path(__file__).parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"


def _ssh_cmd(remote_cmd: str) -> list:
    """构建 SSH 命令列表，直接用列表传参避免 shell 引号嵌套问题"""
    return [
        "ssh", "-o", "ConnectTimeout=5",
        "-p", str(SERVER_PORT),
        f"{SERVER_USER}@{SERVER_HOST}",
        remote_cmd,
    ]


def _scp_cmd(local: str, remote: str) -> list:
    """构建 SCP 命令列表，直接用列表传参避免 shell 引号嵌套问题"""
    return [
        "scp", "-P", str(SERVER_PORT),
        local,
        f"{SERVER_USER}@{SERVER_HOST}:{remote}",
    ]


def run_command(cmd, check=True, cwd=None, env=None):
    """执行命令（自动识别列表或字符串，列表时 shell=False 避免引号问题）"""
    is_list = isinstance(cmd, list)
    if is_list:
        print(f"执行命令: {' '.join(cmd)}")
    else:
        print(f"执行命令: {cmd}")
    if cwd:
        print(f"工作目录: {cwd}")
    result = subprocess.run(
        cmd,
        shell=not is_list,
        check=check,
        cwd=cwd,
        env=env,
        capture_output=False
    )
    if result.returncode != 0 and check:
        if is_list:
            print(f"命令执行失败: {' '.join(cmd)}")
        else:
            print(f"命令执行失败: {cmd}")
        sys.exit(1)
    return result


def check_ssh_connection():
    """检查SSH连接"""
    print("检查SSH连接...")
    cmd = _ssh_cmd(
        "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && echo OK"
    )
    result = run_command(cmd, check=False)
    if result.returncode != 0:
        print(f"无法连接到服务器 {SERVER_HOST}")
        print("请确保已配置免密登录")
        sys.exit(1)
    print("SSH连接正常")


def deploy_frontend():
    """部署前端项目"""
    print("\n" + "="*50)
    print("开始部署前端项目")
    print("="*50)
    
    # 检查前端目录
    if not FRONTEND_DIR.exists():
        print(f"前端目录不存在: {FRONTEND_DIR}")
        sys.exit(1)
    
    # 安装依赖
    print("\n安装前端依赖...")
    run_command("npm install --legacy-peer-deps", cwd=FRONTEND_DIR)
    
    # 构建前端项目
    print("\n构建前端项目...")
    # 设置生产环境API地址
    env = os.environ.copy()
    env["VITE_API_BASE_URL"] = f"https://{DOMAIN}/api"
    run_command("npm run build", cwd=FRONTEND_DIR, env=env)
    
    # 检查构建结果
    dist_dir = FRONTEND_DIR / "dist"
    if not dist_dir.exists():
        print("前端构建失败，dist目录不存在")
        sys.exit(1)
    
    # 创建临时压缩包
    print("\n创建前端部署包...")
    temp_archive = PROJECT_ROOT / "frontend_deploy.tar.gz"
    if temp_archive.exists():
        temp_archive.unlink()

    run_command(
        ["tar", "-czf", str(temp_archive), "-C", str(FRONTEND_DIR), "dist"],
        cwd=PROJECT_ROOT
    )

    # 上传到服务器
    print(f"\n上传前端文件到服务器 {FRONTEND_DEPLOY_PATH}...")
    run_command(
        _ssh_cmd(
            f"export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && "
            f"mkdir -p {shlex.quote(FRONTEND_DEPLOY_PATH)}"
        )
    )

    run_command(
        _scp_cmd(str(temp_archive), "/tmp/frontend_deploy.tar.gz")
    )

    # 解压并部署
    print("\n在服务器上部署前端文件...")
    run_command(
        _ssh_cmd(
            f"export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && "
            f"cd {shlex.quote(FRONTEND_DEPLOY_PATH)} && "
            f"rm -rf * && "
            f"tar -xzf /tmp/frontend_deploy.tar.gz && "
            f"mv dist/* . && "
            f"rm -rf dist && "
            f"rm -f /tmp/frontend_deploy.tar.gz"
        )
    )
    
    # 清理临时文件
    temp_archive.unlink()
    
    print("\n前端部署完成！")


def deploy_backend():
    """部署后端项目"""
    print("\n" + "="*50)
    print("开始部署后端项目")
    print("="*50)
    
    # 检查后端目录
    if not BACKEND_DIR.exists():
        print(f"后端目录不存在: {BACKEND_DIR}")
        sys.exit(1)
    
    # 创建临时部署目录
    print("\n准备后端部署包...")
    temp_deploy_dir = PROJECT_ROOT / "backend_deploy"
    if temp_deploy_dir.exists():
        shutil.rmtree(temp_deploy_dir)
    temp_deploy_dir.mkdir()
    
    # 复制后端文件（排除不需要的文件）
    exclude_patterns = [
        "__pycache__",
        "*.pyc",
        ".pytest_cache",
        "venv",
        "*.db",
        "*.log",
        "temp",
        "tests"
    ]
    
    def should_exclude(path):
        path_str = str(path)
        for pattern in exclude_patterns:
            if pattern in path_str:
                return True
        return False
    
    for item in BACKEND_DIR.iterdir():
        if item.name.startswith('.') or should_exclude(item):
            continue
        if item.is_dir():
            shutil.copytree(item, temp_deploy_dir / item.name, ignore=shutil.ignore_patterns(*exclude_patterns))
        else:
            shutil.copy2(item, temp_deploy_dir / item.name)
    
    # 创建部署压缩包
    temp_archive = PROJECT_ROOT / "backend_deploy.tar.gz"
    if temp_archive.exists():
        temp_archive.unlink()

    run_command(
        ["tar", "-czf", str(temp_archive), "-C", str(PROJECT_ROOT), "backend_deploy"],
        cwd=PROJECT_ROOT
    )

    # 上传到服务器
    print(f"\n上传后端文件到服务器 {BACKEND_DEPLOY_PATH}...")
    run_command(
        _ssh_cmd(
            f"export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && "
            f"mkdir -p {shlex.quote(BACKEND_DEPLOY_PATH)}"
        )
    )

    run_command(
        _scp_cmd(str(temp_archive), "/tmp/backend_deploy.tar.gz")
    )

    # 解压并部署
    print("\n在服务器上部署后端文件...")
    run_command(
        _ssh_cmd(
            f"export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && "
            f"cd {shlex.quote(BACKEND_DEPLOY_PATH)} && "
            f"cp -f /root/.tools/device_id /tmp/tools_device_id.bak 2>/dev/null || true && "
            f"rm -rf app alembic data utils middleware models routes services bin migrations && "
            f"tar -xzf /tmp/backend_deploy.tar.gz && "
            f"cp -r backend_deploy/* . && "
            f"rm -rf backend_deploy && "
            f"rm -f /tmp/backend_deploy.tar.gz && "
            f"mkdir -p /root/.tools && "
            f"mv -f /tmp/tools_device_id.bak /root/.tools/device_id 2>/dev/null || true"
        )
    )

    # 在服务器上安装依赖
    print("\n在服务器上安装Python依赖...")
    run_command(
        _ssh_cmd(
            f"export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && "
            f"cd {shlex.quote(BACKEND_DEPLOY_PATH)} && "
            f"python3 -m venv venv 2>/dev/null || true && "
            f"source venv/bin/activate && "
            f"pip install --upgrade pip && "
            f"pip install -r requirements.txt"
        )
    )
    
    # 清理临时文件
    shutil.rmtree(temp_deploy_dir)
    temp_archive.unlink()
    
    print("\n后端部署完成！")


def restart_backend_service():
    """重启后端服务"""
    print("\n重启后端服务...")
    run_command(
        _ssh_cmd(
            f"export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && "
            f"systemctl restart {shlex.quote(BACKEND_SERVICE)} || echo 服务可能未配置"
        )
    )
    print("后端服务重启完成")


def write_deploy_timestamp():
    """部署完成后写入 UTC 时间戳到服务器"""
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).isoformat()
    json_data = json.dumps({"timestamp": timestamp})
    print(f"\n写入部署时间戳: {timestamp}")
    run_command(
        _ssh_cmd(f"echo '{json_data}' > {shlex.quote(BACKEND_DEPLOY_PATH)}/.deploy_timestamp")
    )


def main():
    parser = argparse.ArgumentParser(description="部署脚本")
    parser.add_argument(
        "--frontend-only",
        action="store_true",
        help="仅部署前端"
    )
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="仅部署后端"
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="部署后不重启服务"
    )
    
    args = parser.parse_args()
    
    # 检查SSH连接
    check_ssh_connection()
    
    # 部署前端
    if not args.backend_only:
        deploy_frontend()
    
    # 部署后端
    if not args.frontend_only:
        deploy_backend()
        if not args.no_restart:
            restart_backend_service()

    # 写入部署时间戳
    write_deploy_timestamp()

    print("\n" + "="*50)
    print("部署完成！")
    print("="*50)
    print(f"\n前端访问地址: https://{DOMAIN}")
    print(f"后端API地址: https://{DOMAIN}/api")


if __name__ == "__main__":
    main()
