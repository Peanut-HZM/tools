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

    def check_uncommitted_changes(self) -> bool:
        """检查是否有未提交的更改"""
        result = self.run_git(["status", "--porcelain"])
        return bool(result.stdout.strip())

    def push_to_remote(self, remote_name: str, branch: str, force: bool = False) -> bool:
        """
        推送到指定远程仓库

        Args:
            remote_name: 远程仓库名称
            branch: 分支名称
            force: 是否强制推送

        Returns:
            推送是否成功
        """
        force_flag = "--force" if force else ""
        cmd = ["push", remote_name, branch]
        if force_flag:
            cmd.insert(1, force_flag)

        print(f"[PUSH] 推送到 {remote_name}...")
        result = self.run_git(cmd, capture_output=False)

        if result.returncode == 0:
            print(f"[OK]   推送到 {remote_name} 成功")
            return True
        else:
            print(f"[FAIL] 推送到 {remote_name} 失败")
            return False

    def sync(self, branch: Optional[str] = None, force: bool = False,
             exclude_remotes: Optional[List[str]] = None) -> bool:
        """
        同步到所有远程仓库

        Args:
            branch: 指定分支，默认为当前分支
            force: 是否强制推送
            exclude_remotes: 要排除的远程仓库名称列表

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

        # 推送到所有远程仓库
        success_count = 0
        failed_remotes = []

        for remote_name, remote_url in remotes:
            if self.push_to_remote(remote_name, current_branch, force):
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
        "-v", "--verbose",
        action="store_true",
        help="显示详细信息"
    )

    args = parser.parse_args()

    syncer = GitRemoteSync(repo_path=args.path)
    success = syncer.sync(
        branch=args.branch,
        force=args.force,
        exclude_remotes=args.exclude
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
