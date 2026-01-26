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

print(f'找到 {len(md_files)} 个md文件\n')

# 查找剩余的乱码文件
remaining_garbled = []
for f in md_files:
    # 检查文件名是否包含乱码字符（非ASCII且不是常见中文）
    try:
        # 如果文件名包含特殊Unicode字符，可能是乱码
        if any(ord(c) > 0x4e00 and ord(c) < 0x9fff for c in f) or 'yt-dlp' in f:
            # 检查是否已经是正确的中文名
            if f not in ['yt-dlp快速开始.md', 'yt-dlp集成测试指南.md', 'yt-dlp集成进度报告.md', 
                         '前端yt-dlp集成.md', '下载目录变更.md']:
                remaining_garbled.append(f)
    except:
        pass

print(f'找到 {len(remaining_garbled)} 个可能的乱码文件:')
for f in remaining_garbled:
    print(f'  - {f}')

# 尝试读取文件内容来确定正确名称
for garbled_file in remaining_garbled:
    filepath = os.path.join(script_dir, garbled_file)
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(1000)
            first_line = content.split('\n')[0] if content else ''
            
            # 根据内容推断文件名
            if '下载' in content and '目录' in content and '变更' in content:
                new_name = '下载目录变更.md'
            elif '前端' in content and 'yt-dlp' in content and '集成' in content:
                new_name = '前端yt-dlp集成.md'
            else:
                # 从第一行提取标题
                if first_line.startswith('#'):
                    title = first_line[1:].strip()
                    new_name = title + '.md' if not title.endswith('.md') else title
                else:
                    new_name = None
            
            if new_name and new_name != garbled_file:
                new_path = os.path.join(script_dir, new_name)
                if not os.path.exists(new_path):
                    shutil.copy2(filepath, new_path)
                    os.remove(filepath)
                    print(f'\n成功: {garbled_file} -> {new_name}')
                else:
                    # 如果新文件已存在，删除旧文件
                    os.remove(filepath)
                    print(f'\n删除重复文件: {garbled_file} (已存在: {new_name})')
    except Exception as e:
        print(f'\n处理失败: {garbled_file}, 错误: {str(e)}')

print('\n处理完成！')
