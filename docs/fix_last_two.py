# -*- coding: utf-8 -*-
import os
import sys
import shutil

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

script_dir = r'F:\CodeProjects\tools\docs'

# 获取所有文件
all_files = os.listdir(script_dir)
md_files = [f for f in all_files if f.endswith('.md')]

# 需要处理的最后两个文件
remaining_files = [
    ('涓嬭浇鐩綍鍙樻洿.md', '下载目录变更.md', ['下载', '目录']),
    ('鍓嶇yt-dlp闆嗘垚.md', '前端yt-dlp集成.md', ['前端', 'yt-dlp']),
]

success_count = 0

for old_name_pattern, new_name, keywords in remaining_files:
    new_path = os.path.join(script_dir, new_name)
    
    # 如果新文件已存在，跳过
    if os.path.exists(new_path):
        print(f'跳过: {new_name} 已存在')
        continue
    
    # 尝试找到匹配的旧文件
    found_old_file = None
    for old_file in md_files:
        # 检查文件名是否匹配模式（可能是编码问题）
        if '下载' in old_file and '目录' in old_file:
            found_old_file = old_file
            break
        elif 'yt-dlp' in old_file and ('前端' in old_file or '集成' in old_file):
            found_old_file = old_file
            break
        else:
            # 读取文件内容来匹配
            old_path = os.path.join(script_dir, old_file)
            try:
                with open(old_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(500)
                    if all(keyword in content for keyword in keywords):
                        found_old_file = old_file
                        break
            except:
                pass
    
    if found_old_file:
        old_path = os.path.join(script_dir, found_old_file)
        try:
            # 复制文件内容到新文件
            shutil.copy2(old_path, new_path)
            # 删除旧文件
            os.remove(old_path)
            print(f'成功: {found_old_file} -> {new_name}')
            success_count += 1
        except Exception as e:
            print(f'失败: {found_old_file} -> {new_name}, 错误: {str(e)}')
    else:
        # 尝试直接使用old_name_pattern
        old_path = os.path.join(script_dir, old_name_pattern)
        if os.path.exists(old_path):
            try:
                shutil.copy2(old_path, new_path)
                os.remove(old_path)
                print(f'成功(直接): {old_name_pattern} -> {new_name}')
                success_count += 1
            except Exception as e:
                print(f'失败(直接): {old_name_pattern} -> {new_name}, 错误: {str(e)}')
        else:
            print(f'未找到文件: {old_name_pattern}')

print(f'\n处理完成！成功: {success_count}')
