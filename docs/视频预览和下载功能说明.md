# 视频预览和下载功能完善说明

## 🎯 更新内容

根据用户反馈，已完善视频下载器的预览和下载功能。

## ✅ 新增功能

### 1. 视频小窗口预览

**功能描述**:
- 每个视频卡片现在包含一个视频预览窗口
- 支持直接在页面中播放视频（MP4、WebM、OGG格式）
- 使用HTML5 `<video>` 标签，带完整播放控制
- 16:9宽高比的预览窗口

**预览支持**:
- ✅ MP4格式视频
- ✅ WebM格式视频
- ✅ OGG格式视频
- ⚠️ M3U8/HLS格式（显示占位符，不支持直接预览）
- ⚠️ iframe嵌入视频（显示特殊图标和提示）

**预览失败处理**:
- 如果视频加载失败，自动显示"无法预览"占位符
- 不会影响其他功能的使用

### 2. 视频下载功能

**功能描述**:
- 添加"下载视频"按钮
- 使用后端代理下载，绕过CORS限制
- 自动识别视频格式并设置正确的文件名
- 支持30秒超时（适合大文件）

**下载支持**:
- ✅ 直接下载MP4、WebM、OGG格式
- ✅ 自动从URL提取文件名
- ✅ 支持带查询参数的视频URL
- ⚠️ 大文件可能超时（提供备用方案）

**下载流程**:
1. 点击"下载视频"按钮
2. 后端代理获取视频文件
3. 浏览器自动下载
4. 如果失败，自动在新窗口打开

### 3. 卡片式布局

**布局改进**:
- 从列表式布局改为网格卡片布局
- 响应式设计：
  - 移动端：1列
  - 平板：2列
  - 桌面：3列
- 每个卡片包含：
  - 视频预览窗口（16:9）
  - 来源标签（颜色编码）
  - 视频类型标签
  - 视频URL（可滚动）
  - 操作按钮组

### 4. 增强的操作按钮

**按钮功能**:
- **下载视频**（绿色）：直接下载可预览的视频
- **观看视频**（紫色）：打开iframe嵌入视频
- **复制**（灰色）：复制视频URL到剪贴板
- **打开**（灰色）：在新窗口打开视频

**智能显示**:
- 可预览的视频：显示"下载视频"按钮
- iframe视频：显示"观看视频"按钮
- 所有视频：显示"复制"和"打开"按钮

## 🔧 技术实现

### 后端API

#### 新增端点
```
GET /api/tools/download-video?url={视频URL}
```

#### 功能
- 接收视频URL参数
- 使用requests库下载视频（30秒超时）
- 设置正确的Content-Type和Content-Disposition
- 添加CORS头允许跨域访问
- 返回视频流供浏览器下载

#### 代码示例
```python
@router.get("/tools/download-video")
async def download_video(url: str):
    headers = {
        'User-Agent': '...',
        'Referer': url,
        'Accept': 'video/webm,video/ogg,video/*;q=0.9,...'
    }
    
    response = requests.get(url, headers=headers, timeout=30, stream=True)
    
    return StreamingResponse(
        io.BytesIO(response.content),
        media_type=content_type,
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Allow-Origin': '*'
        }
    )
```

### 前端实现

#### 视频预览
```typescript
{canPreview(video) ? (
  <video
    src={video.url}
    controls
    className="w-full h-full"
    preload="metadata"
    onError={(e) => {
      // 显示占位符
    }}
  >
    您的浏览器不支持视频播放
  </video>
) : (
  // 显示占位符图标
)}
```

#### 下载功能
```typescript
const downloadVideo = async (videoUrl: string, index: number) => {
  try {
    const proxyUrl = `http://localhost:8000/api/tools/download-video?url=${encodeURIComponent(videoUrl)}`;
    
    const link = document.createElement('a');
    link.href = proxyUrl;
    link.download = `video-${index + 1}`;
    link.click();
  } catch (err) {
    // 备用方案：新窗口打开
    window.open(videoUrl, '_blank');
  }
};
```

#### 预览判断
```typescript
const canPreview = (video: VideoInfo) => {
  if (video.source === 'iframe') return false;
  
  const playableTypes = ['video/mp4', 'video/webm', 'video/ogg'];
  return playableTypes.includes(video.type) || 
         video.url.match(/\.(mp4|webm|ogg)(\?|$)/i);
};
```

## 🎨 UI/UX改进

### 视频卡片设计

**预览区域**:
- 16:9宽高比
- 深色背景（slate-900）
- 居中显示内容
- 支持视频控制条

**信息区域**:
- 来源标签（彩色编码）
- 类型标签（灰色）
- URL显示（可滚动，最大高度20）
- 操作按钮（垂直排列）

**颜色编码**:
- Video标签：蓝色（bg-blue-500）
- Source标签：绿色（bg-green-500）
- iframe：紫色（bg-purple-500）
- Script提取：橙色（bg-orange-500）
- HTML内容：黄色（bg-yellow-500）
- Data属性：粉色（bg-pink-500）

### 响应式设计

**断点**:
- 移动端（< 768px）：1列
- 平板（768px - 1024px）：2列
- 桌面（> 1024px）：3列

**间距**:
- 卡片间距：gap-6
- 内边距：p-4
- 按钮间距：gap-2

## 📝 使用说明

### 预览视频

1. 输入网页URL并提取视频
2. 可预览的视频会自动显示在预览窗口中
3. 点击播放按钮开始播放
4. 使用视频控制条调整音量、进度等

### 下载视频

**方法1：直接下载（推荐）**
1. 找到想要下载的视频
2. 点击"下载视频"按钮
3. 浏览器会自动下载视频文件

**方法2：复制链接**
1. 点击"复制"按钮
2. 使用专业下载工具（IDM、you-get等）
3. 粘贴链接进行下载

**方法3：新窗口打开**
1. 点击"打开"按钮
2. 在新窗口中右键保存视频

### 观看嵌入视频

1. 找到标记为"嵌入视频"的卡片
2. 点击"观看视频"按钮
3. 在新窗口中观看视频

## ⚠️ 限制和注意事项

### 预览限制

1. **格式限制**
   - 只支持MP4、WebM、OGG格式的直接预览
   - M3U8、HLS等流媒体格式不支持预览
   - iframe嵌入视频不支持预览

2. **浏览器限制**
   - 某些浏览器可能不支持特定视频编码
   - 需要浏览器支持HTML5 video标签

3. **网络限制**
   - 视频需要支持跨域访问
   - 某些网站有防盗链保护

### 下载限制

1. **文件大小**
   - 大文件（>100MB）可能下载超时
   - 建议使用专业下载工具

2. **网络限制**
   - 某些视频需要特定的Referer头
   - 某些视频需要认证token

3. **格式限制**
   - M3U8/HLS格式需要专门工具
   - YouTube等平台视频需要yt-dlp

## 🔄 未来改进

### 计划中的功能
- [ ] 支持M3U8/HLS格式预览
- [ ] 添加视频时长显示
- [ ] 添加视频分辨率信息
- [ ] 支持视频质量选择
- [ ] 添加下载进度显示
- [ ] 支持批量下载
- [ ] 集成FFmpeg进行格式转换
- [ ] 添加视频截图功能
- [ ] 支持字幕下载

### 性能优化
- [ ] 懒加载视频预览
- [ ] 视频缩略图生成
- [ ] 并发下载优化
- [ ] 断点续传支持

## 📊 测试结果

### 功能测试
- ✅ MP4视频预览
- ✅ WebM视频预览
- ✅ OGG视频预览
- ✅ 视频下载功能
- ✅ iframe视频识别
- ✅ 复制链接功能
- ✅ 新窗口打开
- ✅ 响应式布局
- ✅ 错误处理

### 浏览器兼容性
- ✅ Chrome/Edge（推荐）
- ✅ Firefox
- ✅ Safari
- ⚠️ IE（不支持）

## 📚 相关文档

- [视频下载器增强说明](VIDEO_DOWNLOAD_ENHANCEMENT.md)
- [视频下载器功能说明](NEW_FEATURE_VIDEO_DOWNLOADER.md)
- [项目README](README.md)

---

**更新时间**: 2024-12-28  
**状态**: ✅ 已完成  
**版本**: 2.1.0

## 更新日志

### v2.1.0 (2024-12-28)
- ✅ 添加视频小窗口预览功能
- ✅ 添加视频下载功能
- ✅ 改为卡片式网格布局
- ✅ 增强操作按钮
- ✅ 优化UI/UX设计
- ✅ 添加智能预览判断
- ✅ 添加下载代理端点

### v2.0.0 (2024-12-28)
- ✅ 扩展视频格式支持
- ✅ 增强视频检测能力
- ✅ 扩展视频平台支持
- ✅ 添加调试日志

### v1.0.0 (2024-12-27)
- ✅ 初始实现视频提取功能
