#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署脚本 - 用于部署前后端项目到服务器
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path

# 服务器配置
SERVER_HOST = "39.107.229.30"
SERVER_USER = "root"  # 根据实际情况修改
FRONTEND_DEPLOY_PATH = "/data/www/tools"
BACKEND_DEPLOY_PATH = "/data/programs/tools"

# 项目路径
PROJECT_ROOT = Path(__file__).parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"


def run_command(cmd, check=True, cwd=None, env=None):
    """执行命令"""
    print(f"执行命令: {cmd}")
    if cwd:
        print(f"工作目录: {cwd}")
    result = subprocess.run(
        cmd,
        shell=True,
        check=check,
        cwd=cwd,
        env=env,
        capture_output=False
    )
    if result.returncode != 0 and check:
        print(f"命令执行失败: {cmd}")
        sys.exit(1)
    return result


def check_ssh_connection():
    """检查SSH连接"""
    print("检查SSH连接...")
    cmd = f"ssh -o ConnectTimeout=5 {SERVER_USER}@{SERVER_HOST} \"export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && echo OK\""
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
    run_command("npm install", cwd=FRONTEND_DIR)
    
    # 构建前端项目
    print("\n构建前端项目...")
    # 设置生产环境API地址
    env = os.environ.copy()
    env["VITE_API_BASE_URL"] = "https://tools.peanuthzm.com.cn/api"
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
        f"tar -czf {temp_archive} -C {FRONTEND_DIR} dist",
        cwd=PROJECT_ROOT
    )
    
    # 上传到服务器
    print(f"\n上传前端文件到服务器 {FRONTEND_DEPLOY_PATH}...")
    run_command(
        f"ssh {SERVER_USER}@{SERVER_HOST} \"export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && mkdir -p {FRONTEND_DEPLOY_PATH}\""
    )
    
    run_command(
        f"scp {temp_archive} {SERVER_USER}@{SERVER_HOST}:/tmp/frontend_deploy.tar.gz"
    )
    
    # 解压并部署
    print("\n在服务器上部署前端文件...")
    run_command(
        f"ssh {SERVER_USER}@{SERVER_HOST} "
        f"\"export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && "
        f"cd {FRONTEND_DEPLOY_PATH} && "
        f"rm -rf * && "
        f"tar -xzf /tmp/frontend_deploy.tar.gz && "
        f"mv dist/* . && "
        f"rm -rf dist && "
        f"rm -f /tmp/frontend_deploy.tar.gz\""
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
        f"tar -czf {temp_archive} -C {PROJECT_ROOT} backend_deploy",
        cwd=PROJECT_ROOT
    )
    
    # 上传到服务器
    print(f"\n上传后端文件到服务器 {BACKEND_DEPLOY_PATH}...")
    run_command(
        f"ssh {SERVER_USER}@{SERVER_HOST} \"export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && mkdir -p {BACKEND_DEPLOY_PATH}\""
    )
    
    run_command(
        f"scp {temp_archive} {SERVER_USER}@{SERVER_HOST}:/tmp/backend_deploy.tar.gz"
    )
    
    # 解压并部署
    print("\n在服务器上部署后端文件...")
    run_command(
        f"ssh {SERVER_USER}@{SERVER_HOST} "
        f"\"export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && "
        f"cd {BACKEND_DEPLOY_PATH} && "
        f"rm -rf app alembic data utils middleware models routes services bin migrations && "
        f"tar -xzf /tmp/backend_deploy.tar.gz && "
        f"cp -r backend_deploy/* . && "
        f"rm -rf backend_deploy && "
        f"rm -f /tmp/backend_deploy.tar.gz\""
    )
    
    # 在服务器上安装依赖
    print("\n在服务器上安装Python依赖...")
    run_command(
        f"ssh {SERVER_USER}@{SERVER_HOST} "
        f"\"export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && "
        f"cd {BACKEND_DEPLOY_PATH} && "
        f"python3 -m venv venv 2>/dev/null || true && "
        f"source venv/bin/activate && "
        f"pip install --upgrade pip && "
        f"pip install -r requirements.txt\""
    )
    
    # 清理临时文件
    shutil.rmtree(temp_deploy_dir)
    temp_archive.unlink()
    
    print("\n后端部署完成！")


def restart_backend_service():
    """重启后端服务"""
    print("\n重启后端服务...")
    run_command(
        f"ssh {SERVER_USER}@{SERVER_HOST} "
        f"\"export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && "
        f"systemctl restart tools-backend.service || echo 服务可能未配置\""
    )
    print("后端服务重启完成")


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
    
    print("\n" + "="*50)
    print("部署完成！")
    print("="*50)
    print(f"\n前端访问地址: https://tools.peanuthzm.com.cn")
    print(f"后端API地址: https://tools.peanuthzm.com.cn/api")


if __name__ == "__main__":
    main()
