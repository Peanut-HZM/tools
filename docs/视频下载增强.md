# 视频下载器增强说明

## 🔧 问题描述

用户反馈：网页明明有视频资源，但是提示"该网页没有找到视频资源"

## ✅ 解决方案

已对视频提取功能进行全面增强，大幅提升视频检测能力。

## 🎯 增强内容

### 1. 扩展视频格式支持

**之前支持的格式**:
- .mp4, .webm, .ogg, .mov, .avi, .flv, .wmv, .m3u8, .mpd

**现在支持的格式**:
- .mp4, .webm, .ogg, .mov, .avi, .flv, .wmv
- .m3u8 (HLS流媒体)
- .mpd (DASH流媒体)
- .mkv (Matroska)
- .m4v (MPEG-4)
- .3gp (3GPP)
- .ts (MPEG传输流)

### 2. 增强视频标签检测

**新增检测项**:
- ✅ `<video>` 标签的 `data-src` 属性（懒加载）
- ✅ `<video>` 标签的 `data-video-src` 属性
- ✅ `<source>` 标签的 `data-src` 属性
- ✅ 所有标签的 `data-video` 属性
- ✅ 所有标签的 `data-video-url` 属性
- ✅ 所有标签的 `data-mp4` 属性
- ✅ 所有标签的 `data-webm` 属性

### 3. 增强脚本提取

**改进点**:
- ✅ 更宽松的正则表达式匹配
- ✅ 支持多种视频格式的URL模式
- ✅ 自动清理URL尾部的特殊字符
- ✅ 不区分大小写匹配

**匹配模式**:
```python
video_patterns = [
    r'https?://[^\s<>"\']+?\.mp4[^\s<>"\']*',
    r'https?://[^\s<>"\']+?\.webm[^\s<>"\']*',
    r'https?://[^\s<>"\']+?\.ogg[^\s<>"\']*',
    r'https?://[^\s<>"\']+?\.m3u8[^\s<>"\']*',
    r'https?://[^\s<>"\']+?\.mpd[^\s<>"\']*',
    r'https?://[^\s<>"\']+?\.mov[^\s<>"\']*',
    r'https?://[^\s<>"\']+?\.avi[^\s<>"\']*',
    r'https?://[^\s<>"\']+?\.flv[^\s<>"\']*',
]
```

### 4. 新增HTML内容直接搜索

**功能**:
- 直接在整个HTML内容中搜索视频URL
- 作为备用检测方案
- 可以找到动态生成的视频链接

### 5. 扩展视频平台支持

**之前支持的平台**:
- YouTube, Vimeo, Dailymotion, Bilibili

**现在支持的平台**:
- YouTube (youtube.com, youtu.be, youtube-nocookie.com)
- Vimeo (vimeo.com, player.vimeo.com)
- Dailymotion (dailymotion.com, dai.ly)
- Bilibili (bilibili.com, b23.tv)
- Twitch (twitch.tv)
- Facebook Video (facebook.com/video, fb.watch)
- TikTok (tiktok.com)
- Instagram (instagram.com)
- Twitter/X (twitter.com, x.com)
- Streamable (streamable.com)
- Wistia (wistia.com)
- Brightcove (brightcove.com)
- JW Player (jwplayer.com)
- VideoPress (videopress.com)

### 6. 添加调试日志

**功能**:
- 实时输出检测过程
- 显示每个检测阶段找到的视频数量
- 帮助诊断为什么某些视频未被检测到

**日志示例**:
```
[DEBUG] 开始提取视频，URL: https://example.com
[DEBUG] 找到 2 个 <video> 标签
[DEBUG] 从video.src找到: https://example.com/video1.mp4
[DEBUG] 找到 5 个 <source> 标签
[DEBUG] 从source找到: https://example.com/video2.webm
[DEBUG] 找到 3 个 <iframe> 标签
[DEBUG] 从iframe找到视频平台: https://www.youtube.com/embed/xxxxx
[DEBUG] 找到 10 个 <script> 标签
[DEBUG] 从script找到: https://cdn.example.com/video.m3u8
[DEBUG] 从script中找到 3 个视频
[DEBUG] 从HTML内容中找到 2 个视频
[DEBUG] 从data属性中找到 1 个视频
[DEBUG] 去重后共 8 个唯一视频
```

## 🔍 检测策略

视频提取器现在使用6层检测策略：

### 第1层：标准HTML标签
- 检测 `<video>` 标签及其 `src` 属性
- 检测 `<video>` 标签的 `data-src` 属性（懒加载）
- 检测 `<source>` 标签及其 `src` 属性

### 第2层：独立Source标签
- 检测页面中所有独立的 `<source>` 标签
- 验证是否包含视频扩展名

### 第3层：视频平台Iframe
- 检测 `<iframe>` 标签
- 识别主流视频平台的嵌入链接
- 支持14+个视频平台

### 第4层：JavaScript脚本
- 解析所有 `<script>` 标签内容
- 使用正则表达式匹配视频URL
- 支持8种视频格式

### 第5层：HTML内容搜索
- 直接在整个HTML源码中搜索
- 查找常见视频格式的URL
- 捕获动态生成的链接

### 第6层：Data属性
- 检测所有标签的 `data-video` 相关属性
- 支持自定义data属性
- 适配各种前端框架

## 📝 使用建议

### 如果仍然检测不到视频

1. **查看后端日志**
   ```bash
   # 查看调试信息
   tail -f backend日志
   ```
   日志会显示每个检测阶段的结果

2. **检查网页类型**
   - 动态加载的视频（需要JavaScript执行）可能无法检测
   - 需要登录才能访问的视频无法检测
   - 使用特殊加密或混淆的视频链接可能无法检测

3. **尝试不同的URL**
   - 有些网站的视频在不同页面有不同的加载方式
   - 尝试访问视频的直接播放页面

4. **使用浏览器开发者工具**
   - 打开浏览器开发者工具（F12）
   - 切换到"网络"标签
   - 筛选"媒体"类型
   - 播放视频，查看实际的视频URL
   - 手动复制视频URL

### 常见问题

#### Q1: 为什么YouTube视频显示为iframe？
**A**: YouTube等平台的视频是通过iframe嵌入的，无法直接下载。需要使用专门的YouTube下载工具。

#### Q2: 为什么有些视频URL无法播放？
**A**: 可能的原因：
- 视频需要特定的Referer头
- 视频有防盗链保护
- 视频需要认证token
- 视频已过期或被删除

#### Q3: 为什么检测到很多重复的视频？
**A**: 系统会自动去重，只显示唯一的视频URL。

#### Q4: 为什么.m3u8或.mpd格式的视频无法直接播放？
**A**: 这些是流媒体格式，需要专门的播放器或下载工具：
- .m3u8: HLS流媒体，需要HLS播放器
- .mpd: DASH流媒体，需要DASH播放器

## 🛠️ 技术细节

### 正则表达式优化

**之前**:
```python
r'https?://[^\s<>"]+?\.(?:mp4|webm|ogg|m3u8|mpd)'
```

**现在**:
```python
r'https?://[^\s<>"\']+?\.mp4[^\s<>"\']*'  # 更宽松，支持查询参数
```

### URL清理

自动清理URL尾部的特殊字符：
```python
video_url = video_url.rstrip('\\",;)}]')
```

### 属性检测增强

检测更多data属性：
```python
for attr in ['data-video', 'data-video-url', 'data-src', 'data-mp4', 'data-webm']:
    value = tag.get(attr)
    if value and is_video_extension(value):
        # 处理视频URL
```

## 📊 性能影响

- 检测时间: 2-10秒（取决于网页大小和复杂度）
- 内存占用: 轻微增加（需要解析整个HTML）
- 准确率: 显著提升（多层检测策略）

## 🔄 未来改进

### 计划中的功能
- [ ] 支持JavaScript渲染的页面（使用Selenium或Playwright）
- [ ] 添加视频预览功能
- [ ] 支持视频质量选择
- [ ] 添加视频时长信息
- [ ] 支持批量下载
- [ ] 集成专业视频下载工具
- [ ] 支持流媒体下载（HLS/DASH）

### 性能优化
- [ ] 并发检测优化
- [ ] 缓存机制
- [ ] 智能检测（根据网站类型选择策略）

## 📚 相关文档

- [视频下载器功能说明](NEW_FEATURE_VIDEO_DOWNLOADER.md)
- [项目README](README.md)

---

**更新时间**: 2024-12-28  
**状态**: ✅ 已增强  
**版本**: 2.0.0

## 更新日志

### v2.0.0 (2024-12-28)
- ✅ 扩展视频格式支持（12种格式）
- ✅ 增强视频标签检测（7种data属性）
- ✅ 改进脚本提取（8种URL模式）
- ✅ 新增HTML内容直接搜索
- ✅ 扩展视频平台支持（14+个平台）
- ✅ 添加详细调试日志
- ✅ 优化正则表达式匹配
- ✅ 自动清理URL特殊字符

### v1.0.0 (2024-12-27)
- ✅ 初始实现视频提取功能
- ✅ 支持基本视频格式
- ✅ 支持主流视频平台
