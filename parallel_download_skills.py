#!/usr/bin/env python3
"""
并行下载 Skills - 支持多线程和进度条
"""

import json
import subprocess
import sys
import shutil
from pathlib import Path
from typing import List, Dict
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import threading

# 全局锁和计数器
print_lock = Lock()
stats_lock = Lock()
stats = {
    'total': 0,
    'success': 0,
    'failed': 0,
    'skipped': 0,
    'current': 0
}

def load_skills_data(json_file: str = "skills_raw.txt") -> List[Dict]:
    """从 JSON 文件加载 skills 数据"""
    print(f"[INFO] 正在读取 {json_file}...")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            content = content.replace('\\"', '"')
            skills = json.loads(content)
        
        print(f"[SUCCESS] 成功加载 {len(skills)} 个 skills")
        return skills
    except Exception as e:
        print(f"[ERROR] 加载失败: {e}")
        sys.exit(1)

def cleanup_temp_dirs(output_dir: Path):
    """清理所有临时目录"""
    for temp_dir in output_dir.glob("_temp_*"):
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

def download_skill(skill: Dict, output_dir: Path, index: int, total: int) -> tuple:
    """
    下载单个 skill
    返回: (success: bool, skill_id: str, message: str)
    """
    source = skill.get("source", "")
    skill_id = skill.get("skillId", "")
    name = skill.get("name", "")
    installs = skill.get("installs", 0)
    
    skill_dir = output_dir / skill_id
    
    # 如果已存在，跳过
    if skill_dir.exists():
        with stats_lock:
            stats['skipped'] += 1
            stats['current'] += 1
        return (True, skill_id, "SKIP")
    
    # 显示开始下载
    with print_lock:
        progress = f"[{stats['current']}/{total}]"
        print(f"{progress} {name} ({installs:,} installs)")
        print(f"  来源: {source}")
        print(f"  [开始] 克隆仓库...")
    
    github_url = f"https://github.com/{source}.git"
    
    try:
        # 克隆仓库
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--progress", github_url, str(skill_dir)],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0 and skill_dir.exists():
            # 删除 .git 目录
            git_dir = skill_dir / ".git"
            if git_dir.exists():
                shutil.rmtree(git_dir, ignore_errors=True)
            
            with stats_lock:
                stats['success'] += 1
                stats['current'] += 1
            
            with print_lock:
                print(f"  [SUCCESS] {skill_id}")
            
            return (True, skill_id, "SUCCESS")
        else:
            # 清理失败的下载
            if skill_dir.exists():
                shutil.rmtree(skill_dir, ignore_errors=True)
            
            with stats_lock:
                stats['failed'] += 1
                stats['current'] += 1
            
            with print_lock:
                print(f"  [FAILED] {skill_id}")
            
            return (False, skill_id, "FAILED")
        
    except subprocess.TimeoutExpired:
        if skill_dir.exists():
            shutil.rmtree(skill_dir, ignore_errors=True)
        
        with stats_lock:
            stats['failed'] += 1
            stats['current'] += 1
        
        with print_lock:
            print(f"  [TIMEOUT] {skill_id}")
        
        return (False, skill_id, "TIMEOUT")
    
    except Exception as e:
        if skill_dir.exists():
            shutil.rmtree(skill_dir, ignore_errors=True)
        
        with stats_lock:
            stats['failed'] += 1
            stats['current'] += 1
        
        with print_lock:
            print(f"  [ERROR] {skill_id}: {str(e)}")
        
        return (False, skill_id, f"ERROR: {str(e)}")

def print_progress_bar(current: int, total: int, success: int, failed: int, skipped: int):
    """打印进度条"""
    percentage = (current / total) * 100
    bar_length = 50
    filled = int(bar_length * percentage / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    print(f"\n进度: [{bar}] {percentage:.2f}%")
    print(f"完成: {current}/{total} | 成功: {success} | 失败: {failed} | 跳过: {skipped}\n")

def main():
    """主函数"""
    print("=" * 60)
    print("Skills 并行下载工具 (多线程版)")
    print("=" * 60)
    print()
    
    # 加载 skills 数据
    skills = load_skills_data()
    
    # 创建输出目录
    output_dir = Path("skills")
    output_dir.mkdir(exist_ok=True)
    
    # 清理临时目录
    print("[INFO] 清理临时文件...")
    cleanup_temp_dirs(output_dir)
    
    # 统计已下载的
    existing = [d.name for d in output_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
    print(f"[INFO] 已下载: {len(existing)} 个 skills")
    
    # 询问用户
    total = len(skills)
    print(f"\n找到 {total} 个 skills")
    
    try:
        limit_input = input("\n要下载多少个? (输入数字，或按 Enter 下载全部): ").strip()
        if limit_input:
            limit = int(limit_input)
            skills = skills[:limit]
        
        # 询问线程数
        threads_input = input("使用多少个线程? (建议 5-10，默认 5): ").strip()
        max_workers = int(threads_input) if threads_input else 5
        
    except ValueError:
        print("[ERROR] 无效的数字")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户取消")
        sys.exit(0)
    
    # 初始化统计
    stats['total'] = len(skills)
    
    print(f"\n开始下载 {len(skills)} 个 skills，使用 {max_workers} 个线程...\n")
    
    start_time = time.time()
    
    # 使用线程池并行下载
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = {
            executor.submit(download_skill, skill, output_dir, i+1, len(skills)): skill
            for i, skill in enumerate(skills)
        }
        
        # 等待完成
        for future in as_completed(futures):
            try:
                success, skill_id, message = future.result()
            except Exception as e:
                print(f"[ERROR] 任务异常: {e}")
    
    # 计算耗时
    elapsed_time = time.time() - start_time
    
    # 打印总结
    print("\n" + "=" * 60)
    print("下载完成!")
    print("=" * 60)
    print(f"总计: {stats['total']} 个 skills")
    print(f"成功: {stats['success']}")
    print(f"跳过: {stats['skipped']}")
    print(f"失败: {stats['failed']}")
    print(f"耗时: {elapsed_time:.1f} 秒 ({elapsed_time/60:.1f} 分钟)")
    
    if stats['success'] > 0:
        avg_time = elapsed_time / stats['success']
        print(f"平均速度: {avg_time:.1f} 秒/skill")
    
    print()

if __name__ == "__main__":
    main()
