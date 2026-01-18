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

# 根据文件内容确定正确的中文名称
# 读取文件的第一行来确定内容
file_content_map = {}

for filename in md_files:
    filepath = os.path.join(script_dir, filename)
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().strip()
            if first_line.startswith('#'):
                title = first_line[1:].strip()
                file_content_map[filename] = title
    except:
        pass

# 手动映射（根据已知的文件内容）
manual_map = {
    'HLS瑙嗛鏀寔.md': 'HLS视频支持.md',
    'Pornhub涓嬭浇闂.md': 'Pornhub下载问题.md',
    '涓嬭浇鐩綍鍙樻洿.md': '下载目录变更.md',
    '瑙嗛杩囨护閫昏緫鏇存柊.md': '视频过滤逻辑更新.md',
    '瑙嗛涓嬭浇澧炲己.md': '视频下载增强.md',
    '瑙嗛鎻愬彇淇.md': '视频提取修复.md',
    '鍓嶇yt-dlp闆嗘垚.md': '前端yt-dlp集成.md',
    '鍥剧墖涓嬭浇淇.md': '图片下载修复.md',
    '鍥剧墖鏌ョ湅鍘熷浘淇.md': '图片查看原图修复.md',
}

success_count = 0
fail_count = 0
skip_count = 0

# 尝试重命名
for old_name, new_name in manual_map.items():
    # 尝试找到实际的文件名（可能是GBK编码的）
    actual_old_name = None
    for f in md_files:
        # 尝试匹配
        try:
            # 如果文件名包含非ASCII字符，尝试编码转换
            if f == old_name or (f.encode('gbk', errors='ignore').decode('utf-8', errors='ignore') == old_name):
                actual_old_name = f
                break
        except:
            if f == old_name:
                actual_old_name = f
                break
    
    if actual_old_name:
        old_path = os.path.join(script_dir, actual_old_name)
        new_path = os.path.join(script_dir, new_name)
        
        # 检查新文件是否已存在
        if new_name in md_files:
            print(f'跳过: {new_name} 已存在')
            skip_count += 1
            continue
        
        try:
            # 使用shutil.move来确保跨文件系统也能工作
            shutil.move(old_path, new_path)
            print(f'成功: {actual_old_name} -> {new_name}')
            success_count += 1
            md_files.remove(actual_old_name)
            md_files.append(new_name)
        except Exception as e:
            print(f'失败: {actual_old_name} -> {new_name}, 错误: {str(e)}')
            fail_count += 1
    else:
        # 如果找不到，尝试直接使用old_name
        old_path = os.path.join(script_dir, old_name)
        if os.path.exists(old_path):
            new_path = os.path.join(script_dir, new_name)
            if not os.path.exists(new_path):
                try:
                    shutil.move(old_path, new_path)
                    print(f'成功(直接): {old_name} -> {new_name}')
                    success_count += 1
                except Exception as e:
                    print(f'失败(直接): {old_name} -> {new_name}, 错误: {str(e)}')
                    fail_count += 1
            else:
                print(f'跳过: {new_name} 已存在')
                skip_count += 1
        else:
            print(f'文件不存在: {old_name}')

print(f'\n重命名完成！成功: {success_count}, 跳过: {skip_count}, 失败: {fail_count}')
