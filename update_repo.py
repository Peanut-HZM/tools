#!/usr/bin/env python3
"""
Git Repository Update Script
使用 rebase 方式更新本地仓库代码
"""

import subprocess
import sys
from typing import Tuple


def run_command(command: str, timeout: int = 30) -> Tuple[int, str, str]:
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='gbk',  # Windows 中文系统使用 GBK 编码
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except UnicodeDecodeError:
        # 非中文系统 fallback 到 UTF-8
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", f"命令超时 ({timeout}s): {command}"
        except Exception as e:
            return 1, "", str(e)
    except subprocess.TimeoutExpired:
        return 1, "", f"命令超时 ({timeout}s): {command}"
    except Exception as e:
        return 1, "", str(e)


def print_status(message: str, status: str = "INFO"):
    """打印状态信息"""
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m"
    }
    color = colors.get(status, colors["INFO"])
    reset = colors["RESET"]
    print(f"{color}[{status}]{reset} {message}")


def check_git_status():
    """检查 Git 状态"""
    print_status("检查 Git 状态...", "INFO")
    code, stdout, stderr = run_command("git status")
    if code != 0:
        print_status(f"无法获取 Git 状态: {stderr}", "ERROR")
        return False
    print(stdout)
    return True


def fetch_remote():
    """获取远程更新"""
    print_status("获取远程更新...", "INFO")
    code, stdout, stderr = run_command("git fetch origin")
    if code != 0:
        print_status(f"获取远程更新失败: {stderr}", "ERROR")
        return False
    if stdout:
        print(stdout)
    print_status("远程更新获取成功", "SUCCESS")
    return True


def rebase_origin():
    """使用 rebase 更新本地代码"""
    print_status("开始 rebase origin/master...", "INFO")
    code, stdout, stderr = run_command("git rebase origin/master")
    
    if code != 0:
        print_status("Rebase 遇到冲突或错误", "ERROR")
        print(stderr)
        print_status("请手动解决冲突后运行:", "WARNING")
        print_status("  git rebase --continue  (解决冲突后继续)", "WARNING")
        print_status("  git rebase --abort     (取消 rebase)", "WARNING")
        return False
    
    print(stdout)
    print_status("Rebase 成功完成!", "SUCCESS")
    return True


def show_final_status():
    """显示最终状态"""
    print_status("\n当前仓库状态:", "INFO")
    code, stdout, stderr = run_command("git status")
    if code == 0:
        print(stdout)


def main():
    """主函数"""
    print_status("=" * 60, "INFO")
    print_status("Git Repository Update (Rebase Mode)", "INFO")
    print_status("=" * 60, "INFO")
    
    # 检查初始状态
    if not check_git_status():
        sys.exit(1)
    
    # 获取远程更新
    if not fetch_remote():
        sys.exit(1)
    
    # 执行 rebase
    if not rebase_origin():
        sys.exit(1)
    
    # 显示最终状态
    show_final_status()
    
    print_status("\n[OK] 仓库更新完成!", "SUCCESS")
    print_status("如需推送到远程，请运行: python push_repo.py", "INFO")


if __name__ == "__main__":
    main()
