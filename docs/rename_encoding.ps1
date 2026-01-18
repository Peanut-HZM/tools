# PowerShell脚本：修复乱码文件名
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$base = "F:\CodeProjects\tools\docs"

# 文件重命名映射
$renameMap = @{
    "HLS瑙嗛鏀寔.md" = "HLS视频支持.md"
    "Pornhub涓嬭浇闂.md" = "Pornhub下载问题.md"
    "涓嬭浇鐩綍鍙樻洿.md" = "下载目录变更.md"
    "瑙嗛杩囨护閫昏緫鏇存柊.md" = "视频过滤逻辑更新.md"
    "瑙嗛涓嬭浇澧炲己.md" = "视频下载增强.md"
    "瑙嗛鎻愬彇淇.md" = "视频提取修复.md"
    "鍓嶇yt-dlp闆嗘垚.md" = "前端yt-dlp集成.md"
    "鍥剧墖涓嬭浇淇.md" = "图片下载修复.md"
    "鍥剧墖鏌ョ湅鍘熷浘淇.md" = "图片查看原图修复.md"
}

$successCount = 0
$failCount = 0
$skipCount = 0

foreach ($pair in $renameMap.GetEnumerator()) {
    $oldName = $pair.Key
    $newName = $pair.Value
    $oldPath = Join-Path $base $oldName
    $newPath = Join-Path $base $newName
    
    if (Test-Path $oldPath) {
        if (Test-Path $newPath) {
            Write-Host "跳过: $newName 已存在"
            $skipCount++
        } else {
            try {
                Move-Item -Path $oldPath -Destination $newPath -Force
                Write-Host "成功: $oldName -> $newName"
                $successCount++
            } catch {
                Write-Host "失败: $oldName -> $newName, 错误: $_"
                $failCount++
            }
        }
    } else {
        Write-Host "文件不存在: $oldName"
    }
}

Write-Host ""
Write-Host "重命名完成！成功: $successCount, 跳过: $skipCount, 失败: $failCount"
