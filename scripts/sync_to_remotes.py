#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双远程仓库同步脚本

功能：将本地代码变更同时推送到 GitHub 和 Gitee 仓库
支持配置多个远程仓库，自动检测并推送到所有已配置的仓库
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import List, Tuple, Optional


# 设置控制台编码为 UTF-8 (Windows)
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')


class GitRemoteSync:
    """Git 双远程仓库同步器"""

    def __init__(self, repo_path: Optional[str] = None):
        """
        初始化同步器

        Args:
            repo_path: Git 仓库路径，默认为当前目录
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.remotes: List[Tuple[str, str]] = []

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

    def get_remotes(self) -> List[Tuple[str, str]]:
        """获取所有远程仓库配置"""
        result = self.run_git(["remote", "-v"])
        if result.returncode != 0:
            print(f"[ERROR] 获取远程仓库失败：{result.stderr}")
            return []

        remotes = []
        seen = set()
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                remote_name = parts[0]
                remote_url = parts[1]
                key = (remote_name, remote_url)
                if key not in seen:
                    seen.add(key)
                    remotes.append((remote_name, remote_url))

        self.remotes = remotes
        return remotes

    def get_current_branch(self) -> Optional[str]:
        """获取当前分支名称"""
        result = self.run_git(["branch", "--show-current"])
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def fetch_remote(self, remote_name: str) -> bool:
        """从远程仓库获取最新代码"""
        print(f"[FETCH] 从 {remote_name} 获取最新代码...")
        result = self.run_git(["fetch", remote_name], capture_output=False)
        if result.returncode == 0:
            print(f"[OK]    获取 {remote_name} 更新成功")
            return True
        else:
            print(f"[FAIL]  获取 {remote_name} 更新失败")
            return False

    def rebase_onto_remote(self, remote_name: str, branch: str) -> bool:
        """
        使用 rebase 方式更新本地分支到远程状态

        Args:
            remote_name: 远程仓库名称
            branch: 分支名称

        Returns:
            rebase 是否成功
        """
        print(f"[REBASE] 使用 rebase 更新到 {remote_name}/{branch}...")
        result = self.run_git(["rebase", f"{remote_name}/{branch}"], capture_output=False)
        if result.returncode == 0:
            print(f"[OK]     Rebase 成功")
            return True
        else:
            print(f"[FAIL]   Rebase 失败")
            return False

    def abort_rebase(self) -> bool:
        """中止正在进行的 rebase"""
        result = self.run_git(["rebase", "--abort"], capture_output=False)
        return result.returncode == 0

    def has_rebase_in_progress(self) -> bool:
        """检查是否有进行中的 rebase"""
        result = self.run_git(["rev-parse", "--git-path", "rebase-merge"])
        if result.returncode == 0:
            rebase_dir = result.stdout.strip()
            if rebase_dir and (self.repo_path / rebase_dir).exists():
                return True
        return False

    def check_uncommitted_changes(self) -> bool:
        """检查是否有未提交的更改"""
        result = self.run_git(["status", "--porcelain"])
        return bool(result.stdout.strip())

    def check_remote_branch_exists(self, remote_name: str, branch: str) -> bool:
        """检查远程仓库是否存在指定分支"""
        result = self.run_git(["ls-remote", "--heads", remote_name, branch])
        if result.returncode != 0:
            return False
        # 如果有输出，说明分支存在
        return bool(result.stdout.strip())

    def set_upstream(self, remote_name: str, branch: str) -> bool:
        """设置当前分支跟踪远程分支"""
        result = self.run_git(["branch", "--set-upstream-to", f"{remote_name}/{branch}", branch])
        return result.returncode == 0

    def push_with_upstream(self, remote_name: str, branch: str, force: bool = False) -> bool:
        """
        推送到指定远程仓库，首次推送时自动设置上游分支

        Args:
            remote_name: 远程仓库名称
            branch: 分支名称
            force: 是否强制推送

        Returns:
            推送是否成功
        """
        force_flag = "--force" if force else ""
        # 首次推送时使用 -u 设置上游
        upstream_flag = "-u" if not force else ""
        cmd = ["push", upstream_flag, force_flag, remote_name, branch]
        # 移除空参数
        cmd = [c for c in cmd if c]

        print(f"[PUSH] 推送到 {remote_name}...")
        result = self.run_git(cmd, capture_output=False)

        if result.returncode == 0:
            print(f"[OK]   推送到 {remote_name} 成功")
            return True
        else:
            print(f"[FAIL] 推送到 {remote_name} 失败")
            return False

    def sync(self, branch: Optional[str] = None, force: bool = False,
             exclude_remotes: Optional[List[str]] = None,
             skip_rebase: bool = False) -> bool:
        """
        同步到所有远程仓库

        Args:
            branch: 指定分支，默认为当前分支
            force: 是否强制推送
            exclude_remotes: 要排除的远程仓库名称列表
            skip_rebase: 是否跳过 rebase 更新（默认先 rebase 再推送）

        Returns:
            是否全部推送成功
        """
        print("=" * 60)
        print("Git 双远程仓库同步")
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
            print("[WARN] 存在未提交的更改，请先提交或暂存")
            print("       运行 'git status' 查看详情")
            return False

        # 检查是否有进行中的 rebase
        if self.has_rebase_in_progress():
            print("[WARN] 检测到进行中的 rebase")
            print("       请先解决或运行 'git rebase --abort' 中止")
            return False

        # 获取所有远程仓库
        remotes = self.get_remotes()
        if not remotes:
            print("[ERROR] 未配置任何远程仓库")
            return False

        # 过滤远程仓库
        if exclude_remotes:
            remotes = [(name, url) for name, url in remotes if name not in exclude_remotes]

        if not remotes:
            print("[ERROR] 没有可推送的远程仓库")
            return False

        print(f"[INFO] 配置的远程仓库 ({len(remotes)}):")
        for name, url in remotes:
            print(f"       - {name}: {url}")
        print()

        # 推送前处理：检查远程分支并 rebase 更新
        if not skip_rebase:
            print("-" * 60)
            print("推送前检查与更新")
            print("-" * 60)

            # 获取第一个远程作为更新源（通常是 origin/gitee）
            primary_remote = remotes[0][0]

            # 先 fetch 所有远程
            print(f"[INFO] 获取所有远程仓库最新状态...")
            self.run_git(["fetch", "--all"], capture_output=True)

            # 检查远程分支是否存在
            remote_branches_status = []
            for remote_name, remote_url in remotes:
                exists = self.check_remote_branch_exists(remote_name, current_branch)
                remote_branches_status.append((remote_name, exists))
                status = "存在" if exists else "不存在"
                print(f"[INFO] {remote_name}/{current_branch}: {status}")

            # 如果有远程分支不存在，提示将首次推送
            missing_remotes = [name for name, exists in remote_branches_status if not exists]
            if missing_remotes:
                print(f"[INFO] 以下远程仓库将首次推送分支：{', '.join(missing_remotes)}")

            # 检查是否需要 rebase 更新（只要有任一远程分支存在且本地落后）
            existing_remotes = [name for name, exists in remote_branches_status if exists]
            if existing_remotes:
                # 使用第一个存在的远程分支进行 rebase
                update_remote = existing_remotes[0]

                # 检查是否需要更新
                result = self.run_git([
                    "rev-list", "--left-right", "--count",
                    f"{update_remote}/{current_branch}...{current_branch}"
                ])
                if result.returncode == 0:
                    parts = result.stdout.strip().split()
                    if len(parts) >= 2:
                        behind = int(parts[0])  # 落后远程
                        ahead = int(parts[1])   # 领先远程

                        if behind > 0:
                            print()
                            print(f"[INFO] 本地落后 {update_remote}/{current_branch} {behind} 个提交")
                            print(f"[INFO] 开始 rebase 更新...")
                            print()

                            if not self.fetch_remote(update_remote):
                                print("[ERROR] fetch 失败，中止")
                                return False

                            if not self.rebase_onto_remote(update_remote, current_branch):
                                print("[ERROR] rebase 失败，请手动解决冲突")
                                print("       解决后运行：git rebase --continue")
                                print("       或运行：git rebase --abort 中止")
                                return False

                            print()
                            print("[INFO] Rebase 完成，开始推送...")
                            print()
                        elif ahead > 0 and behind == 0:
                            print(f"[INFO] 本地领先远程 {ahead} 个提交，无需更新")
                        else:
                            print(f"[INFO] 本地与远程同步，无需更新")

            print("-" * 60)
            print()

        # 推送到所有远程仓库
        success_count = 0
        failed_remotes = []

        for remote_name, remote_url in remotes:
            # 检查远程分支是否存在，决定是否使用 -u 参数
            branch_exists = self.check_remote_branch_exists(remote_name, current_branch)

            if not branch_exists:
                print(f"[INFO] {remote_name}/{current_branch} 不存在，将首次推送并设置上游")

            # 对于不存在的分支，强制使用 -u 设置上游
            if self.push_with_upstream(remote_name, current_branch, force):
                success_count += 1
            else:
                failed_remotes.append(remote_name)
            print()

        # 汇总结果
        print("=" * 60)
        print(f"同步结果：{success_count}/{len(remotes)} 成功")

        if failed_remotes:
            print(f"[FAIL] 失败的仓库：{', '.join(failed_remotes)}")
            return False
        else:
            print("[SUCCESS] 所有远程仓库同步成功!")
            return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Git 双远程仓库同步脚本 - 同时推送到 GitHub 和 Gitee"
    )
    parser.add_argument(
        "-p", "--path",
        help="Git 仓库路径，默认为当前目录"
    )
    parser.add_argument(
        "-b", "--branch",
        help="指定要推送的分支，默认为当前分支"
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="强制推送"
    )
    parser.add_argument(
        "-e", "--exclude",
        nargs="+",
        help="要排除的远程仓库名称"
    )
    parser.add_argument(
        "--skip-rebase",
        action="store_true",
        help="跳过推送前的 rebase 更新"
    )
    parser.add_argument(
        "--auto-rebase",
        action="store_true",
        default=True,
        help="推送前自动 rebase 更新（默认行为）"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细信息"
    )

    args = parser.parse_args()

    syncer = GitRemoteSync(repo_path=args.path)
    success = syncer.sync(
        branch=args.branch,
        force=args.force,
        exclude_remotes=args.exclude,
        skip_rebase=args.skip_rebase
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
