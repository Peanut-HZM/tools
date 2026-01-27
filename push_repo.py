#!/usr/bin/env python3
"""
Git Repository Push Script
自动提交本地变更并推送到远程仓库
支持分批次提交大量文件
"""

import subprocess
import sys
import os
from typing import Tuple, List
from pathlib import Path


def run_command(command: str, show_output: bool = False) -> Tuple[int, str, str]:
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        if show_output and result.stdout:
            print(result.stdout)
        return result.returncode, result.stdout, result.stderr
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


def get_current_branch():
    """获取当前分支名"""
    code, stdout, stderr = run_command("git branch --show-current")
    if code != 0:
        return None
    return stdout.strip()


def get_changed_files() -> Tuple[List[str], List[str], List[str]]:
    """获取变更的文件列表"""
    # 获取已修改的文件
    code, stdout, _ = run_command("git diff --name-only")
    modified = [f.strip() for f in stdout.split('\n') if f.strip()]
    
    # 获取已暂存的文件
    code, stdout, _ = run_command("git diff --cached --name-only")
    staged = [f.strip() for f in stdout.split('\n') if f.strip()]
    
    # 获取未跟踪的文件
    code, stdout, _ = run_command("git ls-files --others --exclude-standard")
    untracked = [f.strip() for f in stdout.split('\n') if f.strip()]
    
    return modified, staged, untracked


def show_changes_summary():
    """显示变更摘要"""
    modified, staged, untracked = get_changed_files()
    
    total = len(modified) + len(staged) + len(untracked)
    
    if total == 0:
        print_status("没有检测到任何变更", "INFO")
        return False
    
    print_status(f"\n检测到 {total} 个文件变更:", "INFO")
    
    if modified:
        print_status(f"  已修改: {len(modified)} 个文件", "WARNING")
        for f in modified[:5]:
            print(f"    - {f}")
        if len(modified) > 5:
            print(f"    ... 还有 {len(modified) - 5} 个文件")
    
    if staged:
        print_status(f"  已暂存: {len(staged)} 个文件", "INFO")
        for f in staged[:5]:
            print(f"    - {f}")
        if len(staged) > 5:
            print(f"    ... 还有 {len(staged) - 5} 个文件")
    
    if untracked:
        print_status(f"  未跟踪: {len(untracked)} 个文件", "WARNING")
        for f in untracked[:5]:
            print(f"    - {f}")
        if len(untracked) > 5:
            print(f"    ... 还有 {len(untracked) - 5} 个文件")
    
    return True


def get_commit_message() -> str:
    """获取用户输入的 commit message"""
    print_status("\n请输入 commit message:", "INFO")
    print_status("(输入空行结束，支持多行)", "INFO")
    
    lines = []
    while True:
        try:
            line = input("> " if not lines else "  ")
            if not line and lines:
                break
            if line:
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            print()
            if not lines:
                return None
            break
    
    return '\n'.join(lines) if lines else None


def batch_commit_files(commit_message: str, batch_size: int = 200) -> bool:
    """分批次提交文件"""
    modified, staged, untracked = get_changed_files()
    
    # 如果已经有暂存的文件，先提交它们
    if staged:
        print_status(f"\n提交已暂存的 {len(staged)} 个文件...", "INFO")
        code, stdout, stderr = run_command(f'git commit -m "{commit_message}"')
        if code != 0:
            print_status(f"提交失败: {stderr}", "ERROR")
            return False
        print_status("已暂存文件提交成功", "SUCCESS")
    
    # 合并修改和未跟踪的文件
    all_files = modified + untracked
    
    if not all_files:
        return True
    
    total_files = len(all_files)
    
    # 如果文件数量较少，一次性提交
    if total_files <= batch_size:
        print_status(f"\n添加并提交 {total_files} 个文件...", "INFO")
        code, _, stderr = run_command("git add .")
        if code != 0:
            print_status(f"添加文件失败: {stderr}", "ERROR")
            return False
        
        code, stdout, stderr = run_command(f'git commit -m "{commit_message}"')
        if code != 0:
            print_status(f"提交失败: {stderr}", "ERROR")
            return False
        
        print_status("提交成功", "SUCCESS")
        return True
    
    # 分批次提交
    print_status(f"\n文件数量较多 ({total_files} 个)，将分批次提交...", "WARNING")
    
    batches = (total_files + batch_size - 1) // batch_size
    
    for i in range(batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, total_files)
        batch_files = all_files[start_idx:end_idx]
        
        print_status(f"\n批次 {i + 1}/{batches}: 提交 {len(batch_files)} 个文件...", "INFO")
        
        # 添加这批文件
        for file in batch_files:
            code, _, _ = run_command(f'git add "{file}"')
        
        # 提交这批文件
        batch_message = f"{commit_message} (batch {i + 1}/{batches})"
        code, stdout, stderr = run_command(f'git commit -m "{batch_message}"')
        
        if code != 0:
            print_status(f"批次 {i + 1} 提交失败: {stderr}", "ERROR")
            return False
        
        print_status(f"批次 {i + 1} 提交成功", "SUCCESS")
    
    return True


def push_to_remote(force: bool = False) -> bool:
    """推送到远程仓库"""
    branch = get_current_branch()
    if not branch:
        print_status("无法获取当前分支名", "ERROR")
        return False
    
    print_status(f"\n推送到 origin/{branch}...", "INFO")
    
    if force:
        command = f"git push --force-with-lease origin {branch}"
    else:
        command = f"git push origin {branch}"
    
    code, stdout, stderr = run_command(command, show_output=True)
    
    if code != 0:
        print_status("推送失败", "ERROR")
        print(stderr)
        
        if "rejected" in stderr and not force:
            print_status("\n远程分支有新的提交，建议:", "WARNING")
            print_status("1. 运行 python update_repo.py 更新本地代码", "INFO")
            print_status("2. 或使用 python push_repo.py --force 强制推送", "INFO")
        
        return False
    
    print_status("推送成功!", "SUCCESS")
    return True


def main():
    """主函数"""
    print_status("=" * 60, "INFO")
    print_status("Git Repository Commit & Push", "INFO")
    print_status("=" * 60, "INFO")
    
    # 检查是否使用 force 参数
    force = "--force" in sys.argv or "-f" in sys.argv
    
    # 获取当前分支
    branch = get_current_branch()
    if not branch:
        print_status("无法获取当前分支", "ERROR")
        sys.exit(1)
    
    print_status(f"当前分支: {branch}", "INFO")
    
    # 显示变更摘要
    if not show_changes_summary():
        # 检查是否有未推送的提交
        code, stdout, _ = run_command("git status")
        if "Your branch is ahead of" in stdout:
            print_status("\n检测到有未推送的提交", "INFO")
            response = input("是否直接推送? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                if push_to_remote(force):
                    print_status("\n✓ 推送完成!", "SUCCESS")
                    sys.exit(0)
            else:
                print_status("取消操作", "INFO")
        else:
            print_status("工作区是干净的，无需操作", "INFO")
        sys.exit(0)
    
    # 获取 commit message
    commit_message = get_commit_message()
    
    if not commit_message:
        print_status("\n未输入 commit message，取消操作", "WARNING")
        sys.exit(1)
    
    print_status(f"\nCommit message: {commit_message}", "INFO")
    
    # 确认提交
    response = input("\n确认提交并推送? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print_status("取消操作", "INFO")
        sys.exit(0)
    
    # 分批次提交文件
    if not batch_commit_files(commit_message):
        sys.exit(1)
    
    # 推送到远程
    if not push_to_remote(force):
        sys.exit(1)
    
    # 显示最终状态
    print_status("\n当前仓库状态:", "INFO")
    run_command("git status", show_output=True)
    
    print_status("\n✓ 提交并推送完成!", "SUCCESS")


if __name__ == "__main__":
    main()
