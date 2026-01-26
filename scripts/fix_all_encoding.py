# -*- coding: utf-8 -*-
import os
import sys

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 获取脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# 获取所有md文件的实际文件名
all_files = [f for f in os.listdir(script_dir) if f.endswith('.md')]

print(f'找到 {len(all_files)} 个md文件\n')

# 文件重命名映射（使用实际的文件名）
# 这些文件名可能是GBK编码的，需要正确识别
rename_map = {
    # 根据file_list.txt中的文件名进行映射
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

for old_name, new_name in rename_map.items():
    old_path = os.path.join(script_dir, old_name)
    new_path = os.path.join(script_dir, new_name)
    
    # 检查文件是否存在
    if old_name in all_files:
        # 检查新文件名是否已存在
        if new_name in all_files:
            print(f'跳过: {new_name} 已存在')
            skip_count += 1
            continue
        
        try:
            os.rename(old_path, new_path)
            print(f'成功: {old_name} -> {new_name}')
            success_count += 1
            # 更新all_files列表
            all_files.remove(old_name)
            all_files.append(new_name)
        except Exception as e:
            print(f'失败: {old_name} -> {new_name}, 错误: {str(e)}')
            fail_count += 1
    else:
        # 尝试使用不同的编码来查找文件
        found = False
        for f in all_files:
            try:
                # 尝试将文件名编码为GBK再解码为UTF-8
                if f.encode('gbk').decode('utf-8', errors='ignore') == old_name:
                    old_path = os.path.join(script_dir, f)
                    os.rename(old_path, new_path)
                    print(f'成功(编码转换): {f} -> {new_name}')
                    success_count += 1
                    all_files.remove(f)
                    all_files.append(new_name)
                    found = True
                    break
            except:
                pass
        
        if not found:
            print(f'文件不存在: {old_name}')

print(f'\n重命名完成！成功: {success_count}, 跳过: {skip_count}, 失败: {fail_count}')
