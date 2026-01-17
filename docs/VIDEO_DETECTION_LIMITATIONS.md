# 视频检测限制说明

## 🔍 当前检测能力

我们的视频提取器已经实现了多层检测策略，但仍然存在一些限制。

## ⚠️ 为什么有些长视频检测不到

### 1. 动态加载问题

**问题描述**:
- 很多现代视频网站使用JavaScript动态加载视频
- 完整视频URL只在用户点击播放后才加载
- 初始HTML中只包含缩略图或预览视频

**示例**:
```
初始HTML中: 360P_360K_xxx_fb.mp4 (预览视频，几秒钟)
点击播放后: 1080P_4000K_xxx.mp4 (完整视频，10分钟+)
```

**当前提取到的**:
- ✅ 预览视频（360P, 180P）- 几秒钟
- ❌ 完整视频 - 需要JavaScript执行才能获取

### 2. 需要用户交互

**问题描述**:
- 某些网站的视频URL需要用户点击才生成
- 视频URL可能包含临时token
- 需要登录才能访问完整视频

### 3. 加密和混淆

**问题描述**:
- 视频URL被加密或混淆
- 使用专有的流媒体协议
- URL在JavaScript中动态构建

## ✅ 已实现的改进

### 1. 过滤缩略图视频
```python
# 过滤掉明显的缩略图视频
if '360P' not in video_url and '180P' not in video_url and '_fb.mp4' not in video_url:
    # 添加到结果
```

### 2. 查找高质量视频
```python
quality_patterns = [
    r'https?://[^\s<>"\']+?(?:1080P|720P|480P|original)[^\s<>"\']*?\.mp4',
    r'https?://[^\s<>"\']+?/(?:hd|high|full)[^\s<>"\']*?\.mp4',
]
```

### 3. 多种URL模式匹配
- 标准video/source标签
- data属性
- JavaScript脚本
- HTML内容直接搜索
- 高质量标识搜索

### 4. HLS流媒体检测 ⭐ 新增
- 自动检测 .m3u8、.ts 和 /hls/ URL
- 提供详细的下载指南
- 自动构建 master.m3u8 地址
- 前端显示 HLS 标记
- 点击按钮显示专业工具下载方法

## 💡 解决方案

### 方案1：使用浏览器开发者工具（推荐）

**步骤**:
1. 打开网页
2. 按F12打开开发者工具
3. 切换到"网络"（Network）标签
4. 筛选"媒体"（Media）类型
5. 播放视频
6. 查看实际加载的视频URL
7. 右键复制URL

**优点**:
- 可以获取真实的视频URL
- 包含所有认证token
- 看到实际的视频质量

### 方案2：使用专业下载工具

**推荐工具**:

1. **yt-dlp** (最强大)
   ```bash
   yt-dlp "网页URL"
   ```
   - 支持1000+网站
   - 自动处理JavaScript
   - 支持选择视频质量

2. **you-get**
   ```bash
   you-get "网页URL"
   ```
   - 支持中国视频网站
   - 简单易用

3. **IDM (Internet Download Manager)**
   - 图形界面
   - 自动检测视频
   - 支持断点续传

4. **Video DownloadHelper** (浏览器扩展)
   - 直接在浏览器中使用
   - 自动检测页面视频

### 方案3：使用我们的工具 + 手动获取URL

**步骤**:
1. 使用浏览器开发者工具获取真实视频URL
2. 在我们的工具中，可以添加一个"手动输入URL"功能
3. 直接下载该URL

## 🔄 未来改进计划

### 短期改进
- [ ] 添加"手动输入视频URL"功能
- [ ] 提供更详细的检测日志
- [ ] 添加视频质量过滤选项

### 中期改进
- [ ] 集成Selenium/Playwright进行JavaScript渲染
- [ ] 支持模拟点击播放按钮
- [ ] 添加等待时间让视频加载

### 长期改进
- [ ] 集成yt-dlp作为后端
- [ ] 支持更多视频网站的专门解析
- [ ] 添加视频下载队列管理

## 📝 当前最佳实践

### 对于普通视频网站
1. 使用我们的工具提取
2. 查看提取到的视频
3. 如果只有短视频，使用方案1或方案2

### 对于YouTube、Bilibili等平台
1. 直接使用yt-dlp
   ```bash
   yt-dlp -F "视频URL"  # 列出所有格式
   yt-dlp -f best "视频URL"  # 下载最佳质量
   ```

### 对于需要登录的网站
1. 在浏览器中登录
2. 使用开发者工具获取视频URL
3. 复制URL和Cookie
4. 使用下载工具时提供Cookie

## 🎯 实际案例

### 案例1：提取到的都是短视频

**问题**:
```
提取到: 360P_360K_xxx_fb.mp4 (2.5秒)
期望: 完整视频 (10分钟+)
```

**解决**:
1. 打开开发者工具
2. 播放视频
3. 在Network标签中找到类似这样的URL:
   ```
   https://xxx.com/videos/xxx/1080P_4000K_xxx.mp4
   ```
4. 复制该URL使用下载工具

### 案例2：视频需要token

**问题**:
```
URL包含: ?hdnea=st=xxx~exp=xxx~hmac=xxx
```

**解决**:
- 这些token有时效性
- 必须在有效期内下载
- 使用开发者工具获取最新URL

## 📚 相关资源

- [yt-dlp GitHub](https://github.com/yt-dlp/yt-dlp)
- [you-get GitHub](https://github.com/soimort/you-get)
- [Chrome DevTools 文档](https://developer.chrome.com/docs/devtools/)

---

**更新时间**: 2024-12-28  
**状态**: 📝 说明文档  
**版本**: 1.0.0
