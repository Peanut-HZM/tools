# -*- coding: utf-8 -*-
import os
import sys

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

script_dir = r'F:\CodeProjects\tools\docs'

# 获取所有文件
all_files = os.listdir(script_dir)
md_files = [f for f in all_files if f.endswith('.md')]

print(f'找到 {len(md_files)} 个md文件\n')

# 需要删除的重复文件和乱码文件
files_to_remove = [
    '涓嬭浇鐩綍鍙樻洿.md',
    '鍓嶇yt-dlp闆嗘垚.md',
]

# 需要重命名的文件（根据内容）
rename_map = {
    '下载目录变更.md': 'yt-dlp集成进度报告.md',  # 内容实际上是yt-dlp集成进度报告
}

removed_count = 0
renamed_count = 0

# 删除乱码文件
for filename in files_to_remove:
    filepath = os.path.join(script_dir, filename)
    if os.path.exists(filepath):
        try:
            # 检查是否有对应的正确文件名已存在
            # 如果"下载目录变更.md"存在且内容是yt-dlp相关，则删除乱码文件
            download_dir_file = os.path.join(script_dir, '下载目录变更.md')
            if os.path.exists(download_dir_file):
                with open(download_dir_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(200)
                    if 'yt-dlp' in content and '集成' in content:
                        # 这是错误的内容，应该删除
                        os.remove(filepath)
                        print(f'删除乱码文件: {filename}')
                        removed_count += 1
        except Exception as e:
            print(f'删除失败: {filename}, 错误: {str(e)}')

# 重命名文件
for old_name, new_name in rename_map.items():
    old_path = os.path.join(script_dir, old_name)
    new_path = os.path.join(script_dir, new_name)
    
    if os.path.exists(old_path) and not os.path.exists(new_path):
        try:
            os.rename(old_path, new_path)
            print(f'重命名: {old_name} -> {new_name}')
            renamed_count += 1
        except Exception as e:
            print(f'重命名失败: {old_name} -> {new_name}, 错误: {str(e)}')

print(f'\n处理完成！删除: {removed_count}, 重命名: {renamed_count}')
