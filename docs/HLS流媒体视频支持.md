# HLS流媒体视频支持

## 📋 功能概述

我们的视频下载器现在可以智能识别HLS（HTTP Live Streaming）流媒体视频，并为用户提供正确的下载指导。

## 🎯 问题背景

用户报告的问题：
```
https://kv-h.phncdn.com/hls/videos/202406/06/453448092/1080P_4000K_453448092.mp4/seg-18-v1-a1.ts
```

这种URL是HLS流媒体的分段文件（.ts），视频在播放时会持续调用多个接口加载不同的分段。

## 🔍 什么是HLS

**HLS (HTTP Live Streaming)** 是Apple开发的流媒体协议：

- **播放列表文件**: `.m3u8` 文件，包含所有视频分段的索引
- **视频分段**: `.ts` 文件，实际的视频片段（通常每个2-10秒）
- **自适应码率**: 可以根据网络状况切换不同质量

### HLS结构示例
```
master.m3u8                          # 主播放列表
├── 1080P_playlist.m3u8             # 1080P播放列表
│   ├── seg-1-v1-a1.ts              # 分段1
│   ├── seg-2-v1-a1.ts              # 分段2
│   └── seg-N-v1-a1.ts              # 分段N
├── 720P_playlist.m3u8              # 720P播放列表
└── 480P_playlist.m3u8              # 480P播放列表
```

## ✅ 已实现的功能

### 1. 后端HLS检测

**位置**: `backend/app/routes/video_downloader.py`

```python
@router.get("/tools/download-video")
async def download_video(url: str):
    # 检查是否是HLS流媒体
    if '.m3u8' in url.lower() or '/hls/' in url.lower() or '.ts' in url.lower():
        # 构建master.m3u8地址
        if '.ts' in url:
            base_url = url.split('/seg-')[0]
            m3u8_url = f"{base_url}/master.m3u8"
        
        # 返回详细的下载指南
        raise HTTPException(status_code=400, detail=error_msg)
```

**检测规则**:
- URL包含 `.m3u8` → M3U8播放列表
- URL包含 `/hls/` → HLS目录
- URL包含 `.ts` → TS分段文件

**智能处理**:
- 如果是 `.ts` 分段，自动构建 `master.m3u8` 地址
- 提供详细的下载方法说明
- 包含ffmpeg、yt-dlp等工具的使用命令

### 2. 前端HLS识别

**位置**: `frontend/src/components/Tools/VideoDownloader.tsx`

```typescript
const isHLSVideo = (video: VideoInfo) => {
  return video.url.includes('.m3u8') || 
         video.url.includes('/hls/') || 
         video.url.includes('.ts');
};
```

**视觉标识**:
- 红色徽章显示 "HLS流媒体"
- 黄色按钮 "查看下载方法"
- 点击显示详细下载指南

### 3. 用户友好的错误提示

当用户尝试下载HLS视频时，会看到：

```
⚠️ 这是HLS流媒体视频（.ts分段文件），无法直接下载。

📝 推荐下载方法：

1️⃣ 使用 ffmpeg（推荐）：
   ffmpeg -i "https://xxx/master.m3u8" -c copy output.mp4

2️⃣ 使用 yt-dlp：
   yt-dlp "https://xxx/master.m3u8"

3️⃣ 使用 IDM 或其他专业下载工具

💡 M3U8播放列表地址：
https://xxx/master.m3u8

ℹ️ HLS视频由多个.ts分段组成，需要下载所有分段并合并。
```

## 🛠️ 下载HLS视频的方法

### 方法1: 使用 ffmpeg（推荐）

**安装**:
```bash
# macOS
brew install ffmpeg

# Windows
# 从 https://ffmpeg.org/download.html 下载

# Linux
sudo apt install ffmpeg
```

**下载命令**:
```bash
ffmpeg -i "https://xxx/master.m3u8" -c copy output.mp4
```

**优点**:
- 最快速（直接复制流，不重新编码）
- 支持所有HLS格式
- 自动下载所有分段并合并
- 保持原始质量

### 方法2: 使用 yt-dlp

**安装**:
```bash
# macOS/Linux
pip install yt-dlp

# Windows
# 从 https://github.com/yt-dlp/yt-dlp/releases 下载
```

**下载命令**:
```bash
# 下载最佳质量
yt-dlp "https://xxx/master.m3u8"

# 列出所有可用格式
yt-dlp -F "https://xxx/master.m3u8"

# 选择特定格式
yt-dlp -f best "https://xxx/master.m3u8"
```

**优点**:
- 支持1000+网站
- 自动选择最佳质量
- 支持字幕下载
- 支持播放列表

### 方法3: 使用 IDM (Internet Download Manager)

**步骤**:
1. 安装IDM
2. 在浏览器中播放视频
3. IDM会自动检测并弹出下载窗口
4. 选择质量并下载

**优点**:
- 图形界面，易于使用
- 支持断点续传
- 多线程下载

### 方法4: 使用在线工具

一些在线M3U8下载工具：
- https://m3u8downloader.org/
- https://www.hlsloader.com/

**注意**: 在线工具可能有文件大小限制

## 📊 功能对比

| 方法 | 速度 | 质量 | 易用性 | 支持格式 |
|------|------|------|--------|----------|
| ffmpeg | ⭐⭐⭐⭐⭐ | 原始 | ⭐⭐⭐ | 所有 |
| yt-dlp | ⭐⭐⭐⭐ | 原始 | ⭐⭐⭐⭐ | 所有 |
| IDM | ⭐⭐⭐⭐ | 原始 | ⭐⭐⭐⭐⭐ | 大部分 |
| 在线工具 | ⭐⭐⭐ | 原始 | ⭐⭐⭐⭐⭐ | 部分 |

## 🎯 使用流程

### 用户视角

1. **提取视频**
   - 输入网页URL
   - 点击"提取视频"

2. **识别HLS视频**
   - 看到红色"HLS流媒体"标记
   - 黄色"查看下载方法"按钮

3. **获取下载指南**
   - 点击"查看下载方法"
   - 看到详细的下载命令
   - 复制M3U8地址

4. **使用专业工具下载**
   - 选择合适的工具（ffmpeg/yt-dlp/IDM）
   - 执行下载命令
   - 等待下载完成

### 技术流程

```
用户输入URL
    ↓
提取视频URL
    ↓
检测是否HLS (.m3u8/.ts/hls/)
    ↓
是 → 显示HLS标记 + 提供下载指南
    ↓
否 → 提供直接下载按钮
```

## 🔧 技术实现细节

### URL模式识别

```python
# .ts分段文件
https://xxx/hls/videos/xxx/1080P_4000K_xxx.mp4/seg-18-v1-a1.ts

# 提取base URL
base_url = url.split('/seg-')[0]
# https://xxx/hls/videos/xxx/1080P_4000K_xxx.mp4

# 构建master.m3u8
m3u8_url = f"{base_url}/master.m3u8"
# https://xxx/hls/videos/xxx/1080P_4000K_xxx.mp4/master.m3u8
```

### 错误处理

```python
# 在下载端点检测HLS
if is_hls_video(url):
    raise HTTPException(
        status_code=400,  # Bad Request
        detail=detailed_guide
    )
```

### 前端处理

```typescript
// 检测HLS并显示指南
const response = await fetch(downloadUrl);
if (!response.ok) {
    const errorData = await response.json();
    alert(errorData.detail);  // 显示下载指南
}
```

## 📝 测试案例

### 测试URL
```
https://kv-h.phncdn.com/hls/videos/202406/06/453448092/1080P_4000K_453448092.mp4/seg-18-v1-a1.ts
```

### 预期行为
1. ✅ 后端检测到 `.ts` 扩展名
2. ✅ 构建 master.m3u8 地址
3. ✅ 返回400错误和详细指南
4. ✅ 前端显示HLS标记
5. ✅ 点击按钮显示下载方法

### 实际测试结果
```bash
curl "http://localhost:8000/api/tools/download-video?url=https://xxx.ts"

# 返回:
{
  "detail": "⚠️ 这是HLS流媒体视频...\n\n📝 推荐下载方法：..."
}
```

✅ 测试通过

## 🚀 未来改进

### 短期
- [ ] 添加M3U8解析功能，显示可用质量
- [ ] 提供一键复制ffmpeg命令
- [ ] 添加视频时长估算

### 中期
- [ ] 集成ffmpeg到后端，支持服务器端下载
- [ ] 添加下载进度显示
- [ ] 支持选择视频质量

### 长期
- [ ] 完整的HLS下载服务
- [ ] 支持加密的HLS流
- [ ] 云端下载和存储

## 📚 相关资源

- [HLS规范](https://datatracker.ietf.org/doc/html/rfc8216)
- [ffmpeg文档](https://ffmpeg.org/documentation.html)
- [yt-dlp GitHub](https://github.com/yt-dlp/yt-dlp)
- [HLS.js](https://github.com/video-dev/hls.js/) - 浏览器HLS播放器

## 🎓 学习资源

### 理解HLS
- [什么是HLS](https://www.cloudflare.com/learning/video/what-is-http-live-streaming/)
- [HLS vs DASH](https://www.wowza.com/blog/hls-vs-dash)

### 工具教程
- [ffmpeg完整教程](https://www.ffmpeg.org/ffmpeg.html)
- [yt-dlp使用指南](https://github.com/yt-dlp/yt-dlp#usage-and-options)

---

**创建时间**: 2024-12-28  
**状态**: ✅ 已实现并测试  
**版本**: 1.0.0
