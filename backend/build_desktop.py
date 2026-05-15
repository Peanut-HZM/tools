#!/usr/bin/env python3
"""
桌面应用一键构建脚本。

用法:
    python build_desktop.py              # 默认构建
    python build_desktop.py --dev         # 开发模式（不压缩，保留调试）
    python build_desktop.py --clean       # 清理之前构建产物
    python build_desktop.py --skip-frontend  # 跳过前端构建
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DIST_DIR = SCRIPT_DIR / "dist"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """运行命令并打印输出。"""
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)


def step_build_frontend():
    """构建前端。"""
    print("\n" + "=" * 60)
    print("Step 1: 构建前端")
    print("=" * 60)

    os.chdir(FRONTEND_DIR)
    run(["npm", "install"])
    run(["npm", "run", "build"])
    os.chdir(SCRIPT_DIR)

    dist = FRONTEND_DIR / "dist"
    if not dist.exists():
        print("❌ 前端构建失败: dist 目录不存在")
        sys.exit(1)

    files = list(dist.rglob("*"))
    print(f"✅ 前端构建完成: {len(files)} 个文件")


def step_install_deps():
    """安装桌面打包依赖。"""
    print("\n" + "=" * 60)
    print("Step 2: 安装桌面打包依赖")
    print("=" * 60)

    req_file = SCRIPT_DIR / "requirements-desktop.txt"
    if not req_file.exists():
        print(f"⚠️  {req_file} 不存在，跳过")
        return

    run([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
    print("✅ 依赖安装完成")


def step_clean():
    """清理之前构建产物。"""
    print("\n" + "=" * 60)
    print("清理构建产物")
    print("=" * 60)

    for d in [SCRIPT_DIR / "build", SCRIPT_DIR / "dist", SCRIPT_DIR / "__pycache__"]:
        if d.exists():
            shutil.rmtree(d)
            print(f"  已删除: {d}")

    cache = SCRIPT_DIR / ".pyinstaller_cache"
    if cache.exists():
        shutil.rmtree(cache)

    print("✅ 清理完成")


def step_pyinstaller(dev_mode: bool):
    """执行 PyInstaller 打包。"""
    print("\n" + "=" * 60)
    print("Step 3: PyInstaller 打包")
    print("=" * 60)

    cmd = [sys.executable, "-m", "PyInstaller", str(SCRIPT_DIR / "desktop.spec")]

    if dev_mode:
        cmd += ["--debug", "all", "--log-level", "DEBUG"]
    else:
        cmd += ["--log-level", "INFO"]

    run(cmd)

    # 检查输出
    if sys.platform == "darwin":
        output = DIST_DIR / "ToolBox.app"
    else:
        output = DIST_DIR / "ToolBox" / "ToolBox.exe"

    if output.exists():
        size = sum(f.stat().st_size for f in output.rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"✅ 打包完成: {output}")
        print(f"   大小: {size:.1f} MB")
    else:
        print(f"⚠️  未找到输出文件: {output}")
        print("   请检查 PyInstaller 日志")


def main():
    parser = argparse.ArgumentParser(description="桌面应用一键构建")
    parser.add_argument("--dev", action="store_true", help="开发模式（不压缩，保留调试符号）")
    parser.add_argument("--clean", action="store_true", help="清理之前构建产物")
    parser.add_argument("--skip-frontend", action="store_true", help="跳过前端构建")
    args = parser.parse_args()

    print("🔧 工具箱桌面应用构建脚本")
    print(f"   平台: {sys.platform}")
    print(f"   Python: {sys.version}")
    print(f"   模式: {'开发' if args.dev else '生产'}")

    if args.clean:
        step_clean()
        return

    if not args.skip_frontend:
        step_build_frontend()

    step_install_deps()
    step_pyinstaller(args.dev)

    print("\n" + "=" * 60)
    print("🎉 构建完成！")
    print("=" * 60)

    if sys.platform == "darwin":
        print("\n运行方式:")
        print(f"  open dist/ToolBox.app")
    else:
        print("\n运行方式:")
        print(f"  dist/ToolBox/ToolBox.exe")


if __name__ == "__main__":
    main()
