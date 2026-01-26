@echo off
chcp 65001 >nul
cd /d F:\CodeProjects\tools\docs

echo 开始重命名文件...

if exist "HLS瑙嗛鏀寔.md" ren "HLS瑙嗛鏀寔.md" "HLS视频支持.md" && echo 成功: HLS视频支持.md
if exist "Pornhub涓嬭浇闂.md" ren "Pornhub涓嬭浇闂.md" "Pornhub下载问题.md" && echo 成功: Pornhub下载问题.md
if exist "涓嬭浇鐩綍鍙樻洿.md" ren "涓嬭浇鐩綍鍙樻洿.md" "下载目录变更.md" && echo 成功: 下载目录变更.md
if exist "瑙嗛杩囨护閫昏緫鏇存柊.md" ren "瑙嗛杩囨护閫昏緫鏇存柊.md" "视频过滤逻辑更新.md" && echo 成功: 视频过滤逻辑更新.md
if exist "瑙嗛涓嬭浇澧炲己.md" ren "瑙嗛涓嬭浇澧炲己.md" "视频下载增强.md" && echo 成功: 视频下载增强.md
if exist "瑙嗛鎻愬彇淇.md" ren "瑙嗛鎻愬彇淇.md" "视频提取修复.md" && echo 成功: 视频提取修复.md
if exist "鍓嶇yt-dlp闆嗘垚.md" ren "鍓嶇yt-dlp闆嗘垚.md" "前端yt-dlp集成.md" && echo 成功: 前端yt-dlp集成.md
if exist "鍥剧墖涓嬭浇淇.md" ren "鍥剧墖涓嬭浇淇.md" "图片下载修复.md" && echo 成功: 图片下载修复.md
if exist "鍥剧墖鏌ョ湅鍘熷浘淇.md" ren "鍥剧墖鏌ョ湅鍘熷浘淇.md" "图片查看原图修复.md" && echo 成功: 图片查看原图修复.md

echo.
echo 重命名完成！
