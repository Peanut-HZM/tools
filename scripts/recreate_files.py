# -*- coding: utf-8 -*-
import os
import sys
import shutil

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

script_dir = r'F:\CodeProjects\tools\docs'

# 需要重命名的文件映射（根据文件内容推断）
file_mappings = [
    ('HLS视频支持.md', ['HLS', '流媒体', '视频']),
    ('Pornhub下载问题.md', ['Pornhub', '下载', '问题']),
    ('下载目录变更.md', ['下载', '目录', '变更']),
    ('视频过滤逻辑更新.md', ['视频', '过滤', '逻辑', '更新']),
    ('视频下载增强.md', ['视频', '下载', '增强']),
    ('视频提取修复.md', ['视频', '提取', '修复']),
    ('前端yt-dlp集成.md', ['前端', 'yt-dlp', '集成']),
    ('图片下载修复.md', ['图片', '下载', '修复']),
    ('图片查看原图修复.md', ['图片', '查看', '原图', '修复']),
]

# 获取所有文件
all_files = os.listdir(script_dir)
md_files = [f for f in all_files if f.endswith('.md')]

print(f'找到 {len(md_files)} 个md文件\n')

success_count = 0
fail_count = 0

for new_name, keywords in file_mappings:
    new_path = os.path.join(script_dir, new_name)
    
    # 如果新文件已存在，跳过
    if new_name in md_files or os.path.exists(new_path):
        print(f'跳过: {new_name} 已存在')
        continue
    
    # 尝试找到匹配的旧文件
    found_old_file = None
    for old_file in md_files:
        # 读取文件内容来匹配
        old_path = os.path.join(script_dir, old_file)
        try:
            with open(old_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(500)  # 读取前500个字符
                # 检查是否包含关键词
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
            md_files.remove(found_old_file)
            md_files.append(new_name)
        except Exception as e:
            print(f'失败: {found_old_file} -> {new_name}, 错误: {str(e)}')
            fail_count += 1
    else:
        print(f'未找到匹配文件: {new_name}')

print(f'\n处理完成！成功: {success_count}, 失败: {fail_count}')
