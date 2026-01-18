# -*- coding: utf-8 -*-
import os
import sys

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 文件重命名映射（乱码文件名 -> 正确的中文文件名）
rename_map = [
    ('HLS瑙嗛鏀寔.md', 'HLS视频支持.md'),
    ('Pornhub涓嬭浇闂.md', 'Pornhub下载问题.md'),
    ('娴嬭瘯鎸囧崡.md', 'yt-dlp集成测试指南.md'),
    ('椤圭洰缁撴瀯璇存槑.md', '项目结构说明.md'),
    ('浠诲姟7瀹屾垚鎬荤粨.md', '任务7完成总结-HLS流媒体视频支持.md'),
    ('浠诲姟8瀹屾垚鎬荤粨.md', '任务8完成总结-yt-dlp前端集成.md'),
    ('涓嬭浇鐩綍鍙樻洿.md', '下载目录变更.md'),
    ('瑙嗛杩囨护閫昏緫鏇存柊.md', '视频过滤逻辑更新.md'),
    ('瑙嗛涓嬭浇澧炲己.md', '视频下载增强.md'),
    ('瑙嗛鎻愬彇淇.md', '视频提取修复.md'),
    ('鍓嶇yt-dlp闆嗘垚.md', '前端yt-dlp集成.md'),
    ('鍥剧墖涓嬭浇淇.md', '图片下载修复.md'),
    ('鍥剧墖鏌ョ湅鍘熷浘淇.md', '图片查看原图修复.md'),
    ('閮ㄧ讲鎸囧崡.md', '部署指南.md'),
    ('yt-dlp闆嗘垚杩涘害鎶ュ憡.md', 'yt-dlp集成进度报告.md'),
]

# 获取脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# 执行重命名
success_count = 0
fail_count = 0
skip_count = 0

for old_name, new_name in rename_map:
    old_path = os.path.join(script_dir, old_name)
    new_path = os.path.join(script_dir, new_name)
    
    if os.path.exists(old_path):
        # 检查新文件名是否已存在
        if os.path.exists(new_path):
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
