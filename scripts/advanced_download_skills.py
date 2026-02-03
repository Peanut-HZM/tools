#!/usr/bin/env python3
"""
高级并行下载 Skills - 支持实时进度条和状态显示
需要安装: pip install tqdm
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

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("[WARNING] 未安装 tqdm，将使用简单进度显示")
    print("[INFO] 安装命令: pip install tqdm")
    print()

# 全局锁
print_lock = Lock()

def load_skills_data(json_file: str = "skills_raw.txt") -> List[Dict]:
    """从 JSON 文件加载 skills 数据"""
    with open(json_file, 'r', encoding='utf-8') as f:
        content = f.read().strip().replace('\\"', '"')
        return json.loads(content)

def cleanup_temp_dirs(output_dir: Path):
    """清理所有临时目录"""
    for temp_dir in output_dir.glob("_temp_*"):
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

def download_skill_with_progress(skill: Dict, output_dir: Path, pbar=None) -> tuple:
    """
    下载单个 skill 并更新进度条
    """
    source = skill.get("source", "")
    skill_id = skill.get("skillId", "")
    name = skill.get("name", "")
    
    skill_dir = output_dir / skill_id
    
    # 更新进度条描述
    if pbar and HAS_TQDM:
        pbar.set_description(f"下载: {name[:30]}")
    
    # 如果已存在，跳过
    if skill_dir.exists():
        if pbar:
            pbar.update(1)
        return (True, skill_id, "SKIP", name)
    
    github_url = f"https://github.com/{source}.git"
    
    try:
        # 克隆仓库
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", github_url, str(skill_dir)],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0 and skill_dir.exists():
            # 删除 .git 目录
            git_dir = skill_dir / ".git"
            if git_dir.exists():
                shutil.rmtree(git_dir, ignore_errors=True)
            
            if pbar:
                pbar.update(1)
            return (True, skill_id, "SUCCESS", name)
        else:
            if skill_dir.exists():
                shutil.rmtree(skill_dir, ignore_errors=True)
            if pbar:
                pbar.update(1)
            return (False, skill_id, "FAILED", name)
        
    except subprocess.TimeoutExpired:
        if skill_dir.exists():
            shutil.rmtree(skill_dir, ignore_errors=True)
        if pbar:
            pbar.update(1)
        return (False, skill_id, "TIMEOUT", name)
    
    except Exception as e:
        if skill_dir.exists():
            shutil.rmtree(skill_dir, ignore_errors=True)
        if pbar:
            pbar.update(1)
        return (False, skill_id, f"ERROR", name)

def main():
    """主函数"""
    print("=" * 70)
    print("Skills 高级并行下载工具")
    print("=" * 70)
    print()
    
    # 加载数据
    print("[1/5] 加载 skills 数据...")
    skills = load_skills_data()
    print(f"      成功加载 {len(skills)} 个 skills")
    
    # 创建输出目录
    output_dir = Path("skills")
    output_dir.mkdir(exist_ok=True)
    
    # 清理临时目录
    print("[2/5] 清理临时文件...")
    cleanup_temp_dirs(output_dir)
    
    # 统计已下载的
    existing = [d.name for d in output_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
    print(f"      已下载: {len(existing)} 个 skills")
    
    # 询问用户
    print(f"[3/5] 配置下载参数")
    total = len(skills)
    
    try:
        limit_input = input(f"      要下载多少个? (1-{total}, 默认全部): ").strip()
        if limit_input:
            limit = int(limit_input)
            skills = skills[:limit]
        
        threads_input = input("      使用多少个线程? (建议 5-10, 默认 8): ").strip()
        max_workers = int(threads_input) if threads_input else 8
        
    except ValueError:
        print("[ERROR] 无效的数字")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户取消")
        sys.exit(0)
    
    print(f"[4/5] 开始下载 {len(skills)} 个 skills (使用 {max_workers} 个线程)")
    print()
    
    start_time = time.time()
    results = {'success': 0, 'failed': 0, 'skipped': 0}
    failed_skills = []
    
    # 使用 tqdm 进度条
    if HAS_TQDM:
        with tqdm(total=len(skills), desc="总进度", unit="skill", 
                  bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pbar:
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(download_skill_with_progress, skill, output_dir, pbar): skill
                    for skill in skills
                }
                
                for future in as_completed(futures):
                    try:
                        success, skill_id, status, name = future.result()
                        if status == "SKIP":
                            results['skipped'] += 1
                        elif success:
                            results['success'] += 1
                        else:
                            results['failed'] += 1
                            failed_skills.append((skill_id, name, status))
                    except Exception as e:
                        results['failed'] += 1
    else:
        # 简单进度显示
        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(download_skill_with_progress, skill, output_dir, None): skill
                for skill in skills
            }
            
            for future in as_completed(futures):
                try:
                    success, skill_id, status, name = future.result()
                    completed += 1
                    
                    if status == "SKIP":
                        results['skipped'] += 1
                    elif success:
                        results['success'] += 1
                        print(f"[{completed}/{len(skills)}] ✓ {name}")
                    else:
                        results['failed'] += 1
                        failed_skills.append((skill_id, name, status))
                        print(f"[{completed}/{len(skills)}] ✗ {name} ({status})")
                except Exception as e:
                    results['failed'] += 1
                    completed += 1
    
    elapsed_time = time.time() - start_time
    
    # 打印总结
    print()
    print("=" * 70)
    print("[5/5] 下载完成!")
    print("=" * 70)
    print(f"总计: {len(skills)} 个 skills")
    print(f"✓ 成功: {results['success']}")
    print(f"⊙ 跳过: {results['skipped']}")
    print(f"✗ 失败: {results['failed']}")
    print(f"⏱  耗时: {elapsed_time:.1f} 秒 ({elapsed_time/60:.1f} 分钟)")
    
    if results['success'] > 0:
        avg_time = elapsed_time / (results['success'] + results['skipped'])
        print(f"⚡ 平均速度: {avg_time:.2f} 秒/skill")
    
    # 显示失败的 skills
    if failed_skills:
        print(f"\n失败的 skills ({len(failed_skills)} 个):")
        for skill_id, name, status in failed_skills[:10]:
            print(f"  - {name} ({status})")
        if len(failed_skills) > 10:
            print(f"  ... 还有 {len(failed_skills) - 10} 个")
    
    print()

if __name__ == "__main__":
    main()
