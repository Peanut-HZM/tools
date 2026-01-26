# -*- coding: utf-8 -*-
import os
import sys

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

script_dir = r'F:\CodeProjects\tools\docs'

# 文件重命名映射（GBK编码的文件名 -> UTF-8编码的文件名）
# 这些文件名在Windows文件系统中可能是GBK编码存储的
rename_pairs = [
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

# 获取所有文件（使用GBK编码）
try:
    all_files_gbk = os.listdir(script_dir)
except:
    all_files_gbk = []

print(f'找到 {len(all_files_gbk)} 个文件\n')

for old_name, new_name in rename_pairs:
    # 尝试多种编码方式查找文件
    found = False
    actual_old_name = None
    
    # 方法1: 直接匹配
    if old_name in all_files_gbk:
        actual_old_name = old_name
        found = True
    else:
        # 方法2: 尝试将UTF-8文件名编码为GBK再匹配
        try:
            old_name_gbk = old_name.encode('utf-8').decode('gbk', errors='ignore')
            for f in all_files_gbk:
                if f == old_name_gbk or f.encode('gbk', errors='ignore').decode('utf-8', errors='ignore') == old_name:
                    actual_old_name = f
                    found = True
                    break
        except:
            pass
    
    if found and actual_old_name:
        old_path = os.path.join(script_dir, actual_old_name)
        new_path = os.path.join(script_dir, new_name)
        
        # 检查新文件是否已存在
        if new_name in all_files_gbk:
            print(f'跳过: {new_name} 已存在')
            skip_count += 1
            continue
        
        try:
            os.rename(old_path, new_path)
            print(f'成功: {actual_old_name} -> {new_name}')
            success_count += 1
        except Exception as e:
            print(f'失败: {actual_old_name} -> {new_name}, 错误: {str(e)}')
            fail_count += 1
    else:
        print(f'文件不存在: {old_name}')

print(f'\n重命名完成！成功: {success_count}, 跳过: {skip_count}, 失败: {fail_count}')
