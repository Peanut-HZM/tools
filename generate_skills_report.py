#!/usr/bin/env python3
"""
生成 Skills 下载报告
"""

import json
from pathlib import Path

# 加载 skills 数据
with open("skills_raw.txt", 'r', encoding='utf-8') as f:
    content = f.read().strip().replace('\\"', '"')
    all_skills = json.loads(content)

# 获取已下载的 skills
skills_dir = Path("skills")
downloaded = {d.name for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith("_")}

# 生成报告
print("=" * 70)
print("SKILLS 下载报告")
print("=" * 70)
print(f"\n总计: {len(all_skills)} 个 skills")
print(f"已下载: {len(downloaded)} 个 skills")
print(f"未下载: {len(all_skills) - len(downloaded)} 个 skills")
print(f"下载进度: {len(downloaded) / len(all_skills) * 100:.1f}%")

print("\n" + "=" * 70)
print("已下载的 SKILLS (按安装量排序)")
print("=" * 70)

# 找出已下载的 skills 信息
downloaded_skills = []
for skill in all_skills:
    if skill['skillId'] in downloaded:
        downloaded_skills.append(skill)

# 按安装量排序
downloaded_skills.sort(key=lambda x: x['installs'], reverse=True)

for i, skill in enumerate(downloaded_skills, 1):
    print(f"\n{i}. {skill['name']}")
    print(f"   安装量: {skill['installs']:,}")
    print(f"   来源: {skill['source']}")
    print(f"   ID: {skill['skillId']}")

# 生成 Markdown 报告
with open("SKILLS_REPORT.md", 'w', encoding='utf-8') as f:
    f.write("# Skills 下载报告\n\n")
    f.write(f"- **总计**: {len(all_skills)} 个 skills\n")
    f.write(f"- **已下载**: {len(downloaded)} 个 skills\n")
    f.write(f"- **未下载**: {len(all_skills) - len(downloaded)} 个 skills\n")
    f.write(f"- **下载进度**: {len(downloaded) / len(all_skills) * 100:.1f}%\n\n")
    
    f.write("## 已下载的 Skills\n\n")
    f.write("| # | Name | Installs | Source |\n")
    f.write("|---|------|----------|--------|\n")
    
    for i, skill in enumerate(downloaded_skills, 1):
        f.write(f"| {i} | **{skill['name']}** | {skill['installs']:,} | `{skill['source']}` |\n")
    
    f.write("\n## 热门未下载的 Skills (前 50)\n\n")
    f.write("| # | Name | Installs | Source |\n")
    f.write("|---|------|----------|--------|\n")
    
    not_downloaded = [s for s in all_skills if s['skillId'] not in downloaded]
    not_downloaded.sort(key=lambda x: x['installs'], reverse=True)
    
    for i, skill in enumerate(not_downloaded[:50], 1):
        f.write(f"| {i} | {skill['name']} | {skill['installs']:,} | `{skill['source']}` |\n")

print("\n\n已生成 SKILLS_REPORT.md")
