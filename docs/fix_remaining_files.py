# -*- coding: utf-8 -*-
import os
import sys
import glob

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 获取脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# 获取所有md文件
all_files = glob.glob(os.path.join(script_dir, '*.md'))

# 文件重命名映射（根据实际文件名和内容推断）
rename_map = [
    ('HLS瑙嗛鏀寔.md', 'HLS视频支持.md'),
    ('Pornhub涓嬭浇闂.md', 'Pornhub下载问题.md'),
    ('涓嬭浇鐩綍鍙樻洿.md', '下载目录变更.md'),
    ('瑙嗛杩囨护閫昏緫鏇存柊.md', '视频过滤逻辑更新.md'),
    ('瑙嗛涓嬭浇澧炲己.md', '视频下载增强.md'),
    ('瑙嗛鎻愬彇淇.md', '视频提取修复.md'),
    ('鍓嶇yt-dlp闆嗘垚.md', '前端yt-dlp集成.md'),
    ('鍥剧墖涓嬭浇淇.md', '图片下载修复.md'),
    ('鍥剧墖鏌ョ湅鍘熷浘淇.md', '图片查看原图修复.md'),
]

success_count = 0
fail_count = 0
skip_count = 0

# 先列出所有实际存在的文件
print('正在查找需要重命名的文件...\n')

for old_name, new_name in rename_map:
    old_path = os.path.join(script_dir, old_name)
    new_path = os.path.join(script_dir, new_name)
    
    # 检查文件是否存在（使用实际的文件系统）
    found = False
    for f in all_files:
        if os.path.basename(f) == old_name:
            found = True
            old_path = f
            break
    
    if found:
        # 检查新文件名是否已存在
        new_exists = False
        for f in all_files:
            if os.path.basename(f) == new_name:
                new_exists = True
                break
        
        if new_exists:
            print(f'跳过: {new_name} 已存在')
            skip_count += 1
            continue
        
        try:
            os.rename(old_path, new_path)
            print(f'成功: {old_name} -> {new_name}')
            success_count += 1
        except Exception as e:
            print(f'失败: {old_name} -> {new_name}, 错误: {str(e)}')
            fail_count += 1
    else:
        print(f'文件不存在: {old_name}')

print(f'\n重命名完成！成功: {success_count}, 跳过: {skip_count}, 失败: {fail_count}')
