#!/usr/bin/env python3
"""
Git Repository Push Script
自动提交本地变更并推送到远程仓库
支持分批次提交大量文件
支持 rebase 方式先更新再推送
"""

import subprocess
import sys
import os
import argparse
from typing import Tuple, List
from pathlib import Path


def run_command(command: str, show_output: bool = False, interactive: bool = False, capture_error: bool = True) -> Tuple[int, str, str]:
    """执行命令并返回结果"""
    try:
        if interactive:
            # 对于需要交互的命令（如 git push），直接显示输出
            result = subprocess.run(
                command,
                shell=True,
                text=True,
                encoding='utf-8'
            )
            return result.returncode, "", ""
        else:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=capture_error,
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


def get_unpushed_count() -> int:
    """获取已提交但未推送的 commit 数量"""
    code, stdout, stderr = run_command("git rev-list --count HEAD..@{u}")
    if code != 0:
        return 0
    try:
        return int(stdout.strip())
    except ValueError:
        return 0


def check_need_rebase() -> bool:
    """检查是否需要 rebase（远程有新提交）"""
    code, stdout, stderr = run_command("git status")
    if code != 0:
        return False
    # 如果当前分支落后于远程分支，需要 rebase
    return "Your branch is behind" in stdout or "can be fast-forwarded" in stdout


def is_working_dirty() -> bool:
    """检查工作目录是否有未提交的更改"""
    code, stdout, stderr = run_command("git status --porcelain")
    if code != 0:
        print_status(f"检查工作目录状态失败: {stderr}", "ERROR")
        return False
    return len(stdout.strip()) > 0


def stash_changes() -> bool:
    """执行 git stash 保存更改"""
    print_status("检测到未提交的更改，正在 stash 保存...", "INFO")
    code, stdout, stderr = run_command('git stash push -m "auto-stash-before-rebase"')
    if code != 0:
        print_status(f"Stash 保存失败: {stderr}", "ERROR")
        return False
    print_status("更改已保存到 stash", "SUCCESS")
    return True


def pop_stash() -> bool:
    """执行 git stash pop 恢复更改"""
    print_status("正在恢复 stash 中的更改...", "INFO")
    code, stdout, stderr = run_command("git stash pop")
    if code != 0:
        print_status("恢复 stash 时发生冲突，请手动解决", "WARNING")
        print(stderr)
        print_status("可用命令: git stash drop  (删除 stash)", "WARNING")
        return False
    print_status("更改已恢复", "SUCCESS")
    return True


def rebase_onto_remote() -> Tuple[bool, str]:
    """
    执行 rebase 操作，将本地提交变基到远程分支之上
    返回：(成功标志，错误信息)
    """
    branch = get_current_branch()
    if not branch:
        return False, "无法获取当前分支"

    print_status(f"\n正在变基到 origin/{branch}...", "INFO")
    print_status("提示：如果遇到冲突，请解决后运行 'git rebase --continue'", "WARNING")
    print_status("      或运行 'git rebase --abort' 放弃变基", "WARNING")
    print()

    # 先 fetch 获取远程最新状态
    print_status("正在获取远程状态...", "INFO")
    code, stdout, stderr = run_command("git fetch origin")
    if code != 0:
        return False, f"fetch 失败：{stderr}"

    # 检测是否需要 stash
    need_pop = False
    if is_working_dirty():
        if not stash_changes():
            return False, "Stash 保存失败"
        need_pop = True

    # 执行 rebase
    command = f"git rebase origin/{branch}"
    code, stdout, stderr = run_command(command, show_output=True)

    # rebase 结束后恢复 stash
    if need_pop:
        pop_stash()

    if code != 0:
        # 检查是否是冲突导致的失败
        if "conflict" in stderr.lower() or "conflict" in stdout.lower():
            return False, "变基遇到冲突，请手动解决后运行 'git rebase --continue'"
        return False, f"变基失败：{stderr or stdout}"

    print_status("变基成功！", "SUCCESS")
    return True, ""


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
        print_status(f"  已修改：{len(modified)} 个文件", "WARNING")
        for f in modified[:5]:
            print(f"    - {f}")
        if len(modified) > 5:
            print(f"    ... 还有 {len(modified) - 5} 个文件")

    if staged:
        print_status(f"  已暂存：{len(staged)} 个文件", "INFO")
        for f in staged[:5]:
            print(f"    - {f}")
        if len(staged) > 5:
            print(f"    ... 还有 {len(staged) - 5} 个文件")

    if untracked:
        print_status(f"  未跟踪：{len(untracked)} 个文件", "WARNING")
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


def batch_commit_files(commit_message: str, batch_size: int = 500) -> bool:
    """分批次提交文件"""
    modified, staged, untracked = get_changed_files()

    # 如果已经有暂存的文件，先提交它们
    if staged:
        print_status(f"\n提交已暂存的 {len(staged)} 个文件...", "INFO")
        code, stdout, stderr = run_command(f'git commit -m "{commit_message}"')
        if code != 0:
            print_status(f"提交失败：{stderr}", "ERROR")
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
            print_status(f"添加文件失败：{stderr}", "ERROR")
            return False

        code, stdout, stderr = run_command(f'git commit -m "{commit_message}"')
        if code != 0:
            print_status(f"提交失败：{stderr}", "ERROR")
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
            print_status(f"批次 {i + 1} 提交失败：{stderr}", "ERROR")
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
    print_status("(如需输入凭据，请在下方输入)", "INFO")
    print()

    if force:
        command = f"git push --force-with-lease origin {branch}"
    else:
        command = f"git push origin {branch}"

    # 使用 interactive 模式，允许用户输入凭据
    code, stdout, stderr = run_command(command, interactive=True)

    if code != 0:
        print()
        print_status("推送失败", "ERROR")

        # 尝试获取错误信息
        code2, stdout2, stderr2 = run_command("git push --dry-run 2>&1")
        if stderr2:
            print(stderr2)

        if not force:
            print_status("\n可能的原因:", "WARNING")
            print_status("1. 远程分支有新的提交 - 运行 python update_repo.py", "INFO")
            print_status("2. 需要强制推送 - 使用 python push_repo.py --force", "INFO")
            print_status("3. 认证失败 - 检查 Git 凭据配置", "INFO")

        return False

    print()
    print_status("推送成功!", "SUCCESS")
    return True


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Git Repository Commit & Push')
    parser.add_argument('--force', '-f', action='store_true', help='强制推送（使用 --force-with-lease）')
    parser.add_argument('--batch-size', type=int, default=500, help='每批次提交的文件数量（默认：500）')
    parser.add_argument('--no-rebase', action='store_true', help='跳过 rebase 直接推送')
    args = parser.parse_args()

    print_status("=" * 60, "INFO")
    print_status("Git Repository Commit & Push", "INFO")
    print_status("=" * 60, "INFO")

    # 获取当前分支
    branch = get_current_branch()
    if not branch:
        print_status("无法获取当前分支", "ERROR")
        sys.exit(1)

    print_status(f"当前分支：{branch}", "INFO")

    # 获取变更状态
    modified, staged, untracked = get_changed_files()
    has_uncommitted = bool(modified or staged or untracked)

    # 检查是否有已提交未推送的 commit
    unpushed_count = get_unpushed_count()
    has_unpushed = unpushed_count > 0

    print_status(f"未提交的变更：{'是' if has_uncommitted else '否'}", "INFO")
    print_status(f"已提交未推送：{unpushed_count} 个 commit", "INFO")

    # 场景 1: 有未提交的变更
    if has_uncommitted:
        show_changes_summary()

        # 获取 commit message
        commit_message = get_commit_message()

        if not commit_message:
            print_status("\n未输入 commit message，取消操作", "WARNING")
            sys.exit(1)

        print_status(f"\nCommit message: {commit_message}", "INFO")

        # 确认提交
        response = input("\n确认提交并推送？(yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print_status("取消操作", "INFO")
            sys.exit(0)

        # 分批次提交文件
        if not batch_commit_files(commit_message, batch_size=args.batch_size):
            sys.exit(1)

        # 提交后需要重新检查 unpushed 状态
        has_unpushed = True

    # 场景 2: 有已提交未推送的 commit，需要先 rebase
    if has_unpushed:
        print_status("\n检测到有未推送的提交", "INFO")

        # 检查是否需要 rebase（远程有新提交）
        if not args.no_rebase and check_need_rebase():
            print_status("远程仓库有新提交，需要先变基...", "WARNING")
            response = input("是否执行 git rebase？(yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                success, error_msg = rebase_onto_remote()
                if not success:
                    print_status(f"\n{error_msg}", "ERROR")
                    print_status("\n变基中止，请解决冲突后手动执行 git push", "WARNING")
                    sys.exit(1)
            else:
                print_status("跳过 rebase，直接推送可能导致失败", "WARNING")

        # 推送到远程
        if not push_to_remote(force=args.force):
            sys.exit(1)

    # 场景 3: 没有变更，也没有未推送的提交
    if not has_uncommitted and not has_unpushed:
        print_status("工作区是干净的，无需操作", "INFO")
        sys.exit(0)

    # 显示最终状态
    print_status("\n当前仓库状态:", "INFO")
    run_command("git status", show_output=True)

    print_status("\n✓ 提交并推送完成!", "SUCCESS")


if __name__ == "__main__":
    main()
