#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git Rebase 更新脚本

功能：使用 rebase 方式从远程仓库更新本地代码
保持本地提交历史线性，避免合并提交
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Optional, List


# 设置控制台编码为 UTF-8 (Windows)
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')


class GitRebaseUpdater:
    """Git Rebase 更新器"""

    def __init__(self, repo_path: Optional[str] = None):
        """
        初始化更新器

        Args:
            repo_path: Git 仓库路径，默认为当前目录
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()

    def run_git(self, args: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """执行 git 命令"""
        cmd = ["git"] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=capture_output,
                text=True,
                check=False,
                encoding='utf-8'
            )
            return result
        except Exception as e:
            print(f"[ERROR] 执行命令失败：{' '.join(cmd)}")
            print(f"        错误：{e}")
            sys.exit(1)

    def get_current_branch(self) -> Optional[str]:
        """获取当前分支名称"""
        result = self.run_git(["branch", "--show-current"])
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def get_remote_for_branch(self, branch: str) -> Optional[str]:
        """获取分支跟踪的远程仓库"""
        result = self.run_git(["config", f"branch.{branch}.remote"])
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def check_uncommitted_changes(self) -> bool:
        """检查是否有未提交的更改"""
        result = self.run_git(["status", "--porcelain"])
        return bool(result.stdout.strip())

    def check_unpushed_commits(self, remote: str, branch: str) -> bool:
        """检查是否有未推送的提交"""
        result = self.run_git(["rev-list", "--left-right", f"{remote}/{branch}...{branch}"])
        if result.returncode == 0:
            output = result.stdout.strip()
            return bool(output and ">" in output)
        return False

    def fetch_remote(self, remote: str) -> bool:
        """
        获取远程更新

        Args:
            remote: 远程仓库名称

        Returns:
            是否成功
        """
        print(f"[FETCH] 从 {remote} 获取最新代码...")
        result = self.run_git(["fetch", remote], capture_output=False)

        if result.returncode == 0:
            print(f"[OK]    获取 {remote} 更新成功")
            return True
        else:
            print(f"[FAIL]  获取 {remote} 更新失败")
            return False

    def rebase_remote(self, remote: str, branch: str) -> bool:
        """
        使用 rebase 更新本地分支

        Args:
            remote: 远程仓库名称
            branch: 分支名称

        Returns:
            是否成功
        """
        print(f"[REBASE] 使用 rebase 更新 {branch}...")
        print(f"         基准：{remote}/{branch}")

        result = self.run_git(
            ["rebase", f"{remote}/{branch}"],
            capture_output=False
        )

        if result.returncode == 0:
            print(f"[OK]     Rebase 成功")
            return True
        else:
            print(f"[FAIL]   Rebase 失败")
            print()
            print("[WARN] 如果存在冲突，请手动解决：")
            print("       1. 编辑冲突文件，解决冲突标记")
            print("       2. 运行：git add <文件名>")
            print("       3. 运行：git rebase --continue")
            print("       或运行：git rebase --abort 取消 rebase")
            return False

    def abort_rebase(self) -> bool:
        """中止正在进行的 rebase"""
        print("[ABORT] 中止 rebase...")
        result = self.run_git(["rebase", "--abort"], capture_output=False)
        if result.returncode == 0:
            print("[OK]    Rebase 已中止")
            return True
        return False

    def update(self, remote: Optional[str] = None, branch: Optional[str] = None,
               abort_on_conflict: bool = False) -> bool:
        """
        使用 rebase 方式更新本地代码

        Args:
            remote: 远程仓库名称，默认使用分支跟踪的 remote
            branch: 分支名称，默认为当前分支
            abort_on_conflict: 冲突时是否自动中止 rebase

        Returns:
            是否更新成功
        """
        print("=" * 60)
        print("Git Rebase 更新")
        print("=" * 60)

        # 获取当前分支
        current_branch = branch or self.get_current_branch()
        if not current_branch:
            print("[ERROR] 无法获取当前分支名称")
            return False

        print(f"[INFO] 当前分支：{current_branch}")
        print(f"[INFO] 仓库路径：{self.repo_path}")
        print()

        # 检查未提交的更改
        if self.check_uncommitted_changes():
            print("[WARN] 存在未提交的更改")
            print("       请先提交或暂存更改：")
            print("       - git add . && git commit -m '...'")
            print("       - 或 git stash")
            return False

        # 确定远程仓库
        target_remote = remote or self.get_remote_for_branch(current_branch)
        if not target_remote:
            print("[ERROR] 无法确定远程仓库")
            print("        请指定 --remote 参数或设置分支跟踪")
            return False

        print(f"[INFO] 远程仓库：{target_remote}")
        print()

        # 检查是否有 rebase 在进行中
        rebase_path = self.run_git(["rev-parse", "--git-path", "rebase-merge"])
        if rebase_path.returncode == 0:
            rebase_dir = rebase_path.stdout.strip()
            # 检查目录是否实际存在
            if rebase_dir and (self.repo_path / rebase_dir).exists():
                print("[WARN] 检测到正在进行的 rebase")
                if abort_on_conflict:
                    self.abort_rebase()
                else:
                    print("       请先解决当前 rebase 或运行 --abort 中止")
                    return False

        # 获取远程更新
        if not self.fetch_remote(target_remote):
            return False

        # 检查是否需要更新
        result = self.run_git([
            "rev-list", "--left-right", "--count",
            f"{target_remote}/{current_branch}...{current_branch}"
        ])
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) >= 2:
                behind = int(parts[0])  # 落后远程多少提交
                ahead = int(parts[1])   # 领先远程多少提交

                print(f"[INFO] 分支状态:")
                print(f"       落后远程：{behind} 个提交")
                print(f"       领先远程：{ahead} 个提交")
                print()

                if behind == 0 and ahead == 0:
                    print("[OK] 本地已经是最新，无需更新")
                    return True

        # 执行 rebase
        print("-" * 60)
        if not self.rebase_remote(target_remote, current_branch):
            if abort_on_conflict:
                print("[WARN] 检测到冲突，自动中止 rebase")
                self.abort_rebase()
            return False

        print()
        print("=" * 60)
        print("更新完成!")
        print("=" * 60)

        # 显示更新后的状态
        result = self.run_git(["log", "--oneline", "-5"])
        if result.returncode == 0 and result.stdout.strip():
            print("最近 5 条提交记录:")
            for line in result.stdout.strip().split("\n"):
                print(f"  {line}")

        return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Git Rebase 更新脚本 - 使用 rebase 方式从远程更新本地代码"
    )
    parser.add_argument(
        "-p", "--path",
        help="Git 仓库路径，默认为当前目录"
    )
    parser.add_argument(
        "-b", "--branch",
        help="指定要更新的分支，默认为当前分支"
    )
    parser.add_argument(
        "-r", "--remote",
        help="指定远程仓库名称，默认使用分支跟踪的 remote"
    )
    parser.add_argument(
        "--abort",
        action="store_true",
        help="中止正在进行的 rebase"
    )
    parser.add_argument(
        "--abort-on-conflict",
        action="store_true",
        help="冲突时自动中止 rebase"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细信息"
    )

    args = parser.parse_args()

    updater = GitRebaseUpdater(repo_path=args.path)

    if args.abort:
        success = updater.abort_rebase()
    else:
        success = updater.update(
            branch=args.branch,
            remote=args.remote,
            abort_on_conflict=args.abort_on_conflict
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
