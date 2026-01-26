#!/usr/bin/env python3
"""
监控 Skills 下载进度
"""

import json
from pathlib import Path
import time
import os

def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_progress():
    """获取下载进度"""
    # 加载总数
    with open("skills_raw.txt", 'r', encoding='utf-8') as f:
        content = f.read().strip().replace('\\"', '"')
        all_skills = json.loads(content)
    
    # 获取已下载的
    skills_dir = Path("skills")
    downloaded = [d.name for d in skills_dir.iterdir() 
                  if d.is_dir() and not d.name.startswith("_")]
    
    total = len(all_skills)
    current = len(downloaded)
    percentage = (current / total) * 100
    
    return total, current, percentage, downloaded

def main():
    """主函数"""
    print("Skills 下载进度监控")
    print("按 Ctrl+C 退出")
    print("=" * 60)
    
    last_count = 0
    
    try:
        while True:
            total, current, percentage, downloaded = get_progress()
            
            # 清屏并显示进度
            clear_screen()
            print("=" * 60)
            print("Skills 下载进度监控")
            print("=" * 60)
            print(f"\n总计: {total} 个 skills")
            print(f"已下载: {current} 个 skills")
            print(f"未下载: {total - current} 个 skills")
            print(f"进度: {percentage:.2f}%")
            
            # 显示进度条
            bar_length = 50
            filled = int(bar_length * percentage / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"\n[{bar}] {percentage:.2f}%")
            
            # 显示速度
            if last_count > 0:
                speed = current - last_count
                if speed > 0:
                    remaining = total - current
                    eta_seconds = remaining / speed * 10  # 10秒更新一次
                    eta_minutes = eta_seconds / 60
                    eta_hours = eta_minutes / 60
                    
                    print(f"\n下载速度: {speed} skills/10秒")
                    if eta_hours > 1:
                        print(f"预计剩余时间: {eta_hours:.1f} 小时")
                    else:
                        print(f"预计剩余时间: {eta_minutes:.1f} 分钟")
            
            last_count = current
            
            # 显示最近下载的 5 个
            print(f"\n最近下载的 skills:")
            for skill in downloaded[-5:]:
                print(f"  - {skill}")
            
            print(f"\n更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("\n按 Ctrl+C 退出监控")
            
            # 等待 10 秒
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n监控已停止")

if __name__ == "__main__":
    main()
