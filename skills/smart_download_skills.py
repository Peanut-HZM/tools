#!/usr/bin/env python3
"""
智能下载 skills - 尝试多种方法
1. 直接克隆整个仓库（如果 skill_id 就是仓库名）
2. 克隆仓库并提取子目录（如果 skill 在仓库的子目录中）
"""

import json
import subprocess
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import time

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

def run_command(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 60) -> tuple:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)

def download_skill_method1(source: str, skill_id: str, output_dir: Path) -> bool:
    """
    方法1: 假设整个仓库就是一个 skill
    例如: vercel-labs/agent-browser -> agent-browser skill
    """
    skill_dir = output_dir / skill_id
    if skill_dir.exists():
        return True
    
    github_url = f"https://github.com/{source}.git"
    
    print(f"  [尝试] 方法1: 克隆整个仓库...")
    success, stdout, stderr = run_command([
        "git", "clone", "--depth", "1", github_url, str(skill_dir)
    ])
    
    if success and skill_dir.exists():
        # 删除 .git 目录以节省空间
        git_dir = skill_dir / ".git"
        if git_dir.exists():
            try:
                shutil.rmtree(git_dir, ignore_errors=True)
            except:
                pass
        print(f"  [SUCCESS] 方法1成功")
        return True
    
    # 清理失败的下载
    if skill_dir.exists():
        try:
            shutil.rmtree(skill_dir, ignore_errors=True)
        except:
            pass
    
    return False

def download_skill_method2(source: str, skill_id: str, output_dir: Path) -> bool:
    """
    方法2: skill 在仓库的子目录中
    例如: vercel-labs/agent-skills/vercel-react-best-practices
    """
    skill_dir = output_dir / skill_id
    if skill_dir.exists():
        return True
    
    github_url = f"https://github.com/{source}.git"
    temp_dir = output_dir / f"_temp_{skill_id}"
    
    print(f"  [尝试] 方法2: 克隆仓库并提取子目录...")
    
    try:
        # 克隆整个仓库
        success, stdout, stderr = run_command([
            "git", "clone", "--depth", "1", github_url, str(temp_dir)
        ])
        
        if not success:
            return False
        
        # 查找 skill 目录
        skill_source = temp_dir / skill_id
        if skill_source.exists() and skill_source.is_dir():
            # 移动到目标位置
            shutil.move(str(skill_source), str(skill_dir))
            print(f"  [SUCCESS] 方法2成功")
            return True
        
        return False
        
    finally:
        # 清理临时目录
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass

def download_skill(source: str, skill_id: str, output_dir: Path) -> bool:
    """
    智能下载 skill - 尝试多种方法
    """
    skill_dir = output_dir / skill_id
    
    # 如果已存在，跳过
    if skill_dir.exists():
        print(f"[SKIP] {skill_id} (已存在)")
        return True
    
    print(f"[DOWNLOAD] {skill_id}")
    print(f"  来源: {source}")
    
    # 尝试方法1: 整个仓库就是 skill
    if download_skill_method1(source, skill_id, output_dir):
        return True
    
    # 尝试方法2: skill 在仓库子目录中
    if download_skill_method2(source, skill_id, output_dir):
        return True
    
    print(f"  [FAILED] 所有方法都失败了")
    return False

def main():
    """主函数"""
    print("=" * 60)
    print("Skills 智能下载工具")
    print("=" * 60)
    print()
    
    # 加载 skills 数据
    skills = load_skills_data()
    
    # 创建输出目录
    output_dir = Path("skills")
    output_dir.mkdir(exist_ok=True)
    
    # 询问用户要下载多少个
    total = len(skills)
    print(f"\n找到 {total} 个 skills")
    print("注意: 下载所有 skills 可能需要很长时间和大量磁盘空间")
    
    try:
        limit_input = input("\n要下载多少个 skills? (输入数字，或按 Enter 下载全部): ").strip()
        if limit_input:
            limit = int(limit_input)
            skills = skills[:limit]
            print(f"\n将下载前 {limit} 个 skills")
        else:
            print(f"\n将下载全部 {total} 个 skills")
    except ValueError:
        print("[ERROR] 无效的数字")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户取消")
        sys.exit(0)
    
    # 统计信息
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    print("\n开始下载...\n")
    
    # 下载每个 skill
    for i, skill in enumerate(skills, 1):
        source = skill.get("source", "")
        skill_id = skill.get("skillId", "")
        name = skill.get("name", "")
        installs = skill.get("installs", 0)
        
        print(f"\n[{i}/{len(skills)}] {name} ({installs:,} installs)")
        
        if not source or not skill_id:
            print(f"[SKIP] 缺少必要信息")
            skipped_count += 1
            continue
        
        # 检查是否已存在
        if (output_dir / skill_id).exists():
            print(f"[SKIP] 已存在")
            skipped_count += 1
            continue
        
        # 下载
        if download_skill(source, skill_id, output_dir):
            success_count += 1
        else:
            failed_count += 1
        
        # 短暂延迟
        time.sleep(0.5)
    
    # 打印总结
    print("\n" + "=" * 60)
    print("下载完成!")
    print("=" * 60)
    print(f"总计: {len(skills)} 个 skills")
    print(f"成功: {success_count}")
    print(f"跳过: {skipped_count}")
    print(f"失败: {failed_count}")
    print()
    
    # 生成 README
    readme_path = output_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write("# Downloaded Skills\n\n")
        f.write(f"Total: {len(skills)} skills attempted\n")
        f.write(f"- Success: {success_count}\n")
        f.write(f"- Skipped: {skipped_count}\n")
        f.write(f"- Failed: {failed_count}\n\n")
        f.write("## Skills List\n\n")
        
        for skill in sorted(skills, key=lambda x: x.get("installs", 0), reverse=True):
            name = skill.get("name", "")
            source = skill.get("source", "")
            installs = skill.get("installs", 0)
            skill_id = skill.get("skillId", "")
            
            status = "✓" if (output_dir / skill_id).exists() else "✗"
            f.write(f"{status} **{name}** ({installs:,} installs)\n")
            f.write(f"  - Source: `{source}`\n")
            f.write(f"  - ID: `{skill_id}`\n")
            f.write(f"  - URL: https://github.com/{source}\n\n")
    
    print(f"已生成 {readme_path}")

if __name__ == "__main__":
    main()
