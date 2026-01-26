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

# 查找乱码文件
garbled_files = []
for f in md_files:
    # 检查是否包含乱码字符（Unicode范围外的字符）
    try:
        # 检查文件名中是否有不在常见中文Unicode范围内的字符
        has_garbled = False
        for char in f:
            code = ord(char)
            # 如果字符不在常见范围内，可能是乱码
            if code > 0x9fff or (0xe000 <= code <= 0xf8ff):
                has_garbled = True
                break
        if has_garbled and f not in ['yt-dlp快速开始.md', 'yt-dlp集成测试指南.md', 'yt-dlp集成进度报告.md']:
            garbled_files.append(f)
    except:
        pass

print(f'找到 {len(garbled_files)} 个乱码文件:')
for f in garbled_files:
    print(f'  - {f}')

# 处理每个乱码文件
for garbled_file in garbled_files:
    filepath = os.path.join(script_dir, garbled_file)
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(1000)
            first_line = content.split('\n')[0] if content else ''
            
            # 根据内容推断正确的文件名
            new_name = None
            if '下载' in content and '目录' in content:
                if '变更' in content or '修改' in content:
                    new_name = '下载目录变更.md'
                else:
                    new_name = '下载目录修改说明.md'
            elif '前端' in content and 'yt-dlp' in content:
                new_name = '前端yt-dlp集成.md'
            
            if new_name:
                new_path = os.path.join(script_dir, new_name)
                if not os.path.exists(new_path):
                    # 复制内容到新文件
                    shutil.copy2(filepath, new_path)
                    print(f'\n成功创建: {garbled_file} -> {new_name}')
                # 删除乱码文件
                try:
                    os.remove(filepath)
                    print(f'删除乱码文件: {garbled_file}')
                except:
                    print(f'无法删除: {garbled_file} (可能被占用)')
            else:
                print(f'\n无法确定文件名: {garbled_file}')
                print(f'  第一行: {first_line[:50]}')
    except Exception as e:
        print(f'\n处理失败: {garbled_file}, 错误: {str(e)}')

print('\n处理完成！')
