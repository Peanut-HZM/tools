#!/usr/bin/env python3
"""快速查看下载进度"""

import json
from pathlib import Path

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

print("=" * 60)
print("Skills 下载进度")
print("=" * 60)
print(f"总计: {total} 个 skills")
print(f"已下载: {current} 个 skills")
print(f"未下载: {total - current} 个 skills")
print(f"进度: {percentage:.2f}%")

# 进度条
bar_length = 50
filled = int(bar_length * percentage / 100)
bar = "█" * filled + "░" * (bar_length - filled)
print(f"\n[{bar}] {percentage:.2f}%")

print(f"\n最近下载的 10 个:")
for skill in sorted(downloaded)[-10:]:
    print(f"  - {skill}")
