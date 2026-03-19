# CrossShare 预览功能改进设计

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 CrossShare 文件预览添加一键复制功能，并修复视频/音频格式无法播放的问题

**Architecture:**
- 文本类预览器（JSON/Markdown/Text）添加复制按钮，使用 Clipboard API 复制原始内容
- 视频/音频预览器改用后端代理加载媒体流，解决 OSS 跨域限制问题

**Tech Stack:**
- React 18, TypeScript, Tailwind CSS
- Navigator Clipboard API
- HTML5 `<video>` and `<audio>` tags
- FastAPI 后端代理

**Problem:**
- OSS 签名 URL 直接访问存在 CORS 限制，导致视频/音频无法在浏览器中播放
- 文本类文件预览时缺少快速复制原始内容的功能

---

## 功能设计

### 1. 一键复制功能

**目标文件：**
- `JsonViewer.tsx` - JSON 文件复制
- `MarkdownViewer.tsx` - Markdown 文件复制
- `TextViewer.tsx` - 纯文本文件复制

**交互设计：**
- 在预览器内容区域右上角添加"复制"按钮
- 点击后复制文件完整原始内容到剪贴板
- 复制成功后显示"已复制"提示，2 秒后自动消失
- 复制失败时显示错误提示

**实现要点：**
- 使用 `navigator.clipboard.writeText(content)` API
- 需要 HTTPS 或 localhost 环境
- 复制的内容与预览内容保持一致

### 2. 视频预览修复

**目标文件：**
- `VideoViewer.tsx`
- `backend/app/routes/cross_share.py`

**问题根因：**
- OSS 签名 URL 直接访问时，浏览器因 CORS 策略阻止加载
- `react-player` 无法跨域加载 OSS 资源

**解决方案：**
- 前端通过后端代理 `/api/cross-share/files/{fileId}/content` 获取视频流
- 后端从 OSS 读取文件并以 `video/mp4` 等正确 Content-Type 返回
- 使用 HTML5 `<video>` 标签替代 `react-player`，更轻量可控

### 3. 音频预览修复

**目标文件：**
- `AudioViewer.tsx`

**解决方案：**
- 与视频修复方案一致，使用后端代理加载
- 使用 HTML5 `<audio>` 标签播放

---

## 后端改动

### 新增/修改接口

**`GET /api/cross-share/files/{fileId}/content`**

现有接口已支持文本文件内容获取，需要扩展支持媒体文件：

```python
@router.get("/files/{fileId}/content")
async def get_file_content(
    fileId: str,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """获取文件原始内容 - 支持文本和媒体文件"""
    file = service.get_file_by_id(fileId, current_user)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # 从 OSS 获取文件内容
    oss_content = oss_service.bucket.get_object(file.oss_key)

    # 根据文件类型设置 Content-Type
    content_type = get_content_type_by_file_type(file.file_type, file.file_name)

    return Response(
        content=oss_content.read(),
        media_type=content_type,
    )
```

---

## 前端改动

### JsonViewer.tsx
```tsx
// 新增：复制按钮状态
const [copySuccess, setCopySuccess] = React.useState(false);

// 新增：复制处理函数
const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  } catch (err) {
    console.error('Failed to copy:', err);
  }
};

// UI：在预览区域右上角添加复制按钮
<button onClick={handleCopy} className="absolute top-2 right-2 ...">
  {copySuccess ? '✓ 已复制' : '📋 复制'}
</button>
```

### MarkdownViewer.tsx
```tsx
// 类似 JsonViewer，复制 content 变量
const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(content);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  } catch (err) {
    console.error('Failed to copy:', err);
  }
};
```

### TextViewer.tsx
```tsx
// 类似 JsonViewer，复制 content 变量
```

### VideoViewer.tsx
```tsx
// 改为使用后端代理 URL
const videoUrl = `/api/cross-share/files/${fileId}/content`;

// 使用原生 video 标签
<video
  controls
  width="100%"
  height="100%"
  crossOrigin="anonymous"
>
  <source src={videoUrl} type="video/mp4" />
  Your browser does not support video playback
</video>
```

### AudioViewer.tsx
```tsx
// 类似 VideoViewer，使用 audio 标签
<audio controls src={`/api/cross-share/files/${fileId}/content`} />
```

---

## 测试验证

### 手动测试清单
1. JSON 文件预览 → 点击复制 → 粘贴验证内容
2. Markdown 文件预览 → 点击复制 → 粘贴验证内容
3. 文本文件预览 → 点击复制 → 粘贴验证内容
4. MP4 文件预览 → 视频能正常播放、拖动进度条
5. MP3 文件预览 → 音频能正常播放、拖动进度条
6. 浏览器 Console 无 CORS 错误

### 兼容性说明
- Clipboard API 需要 HTTPS 或 localhost 环境
- 现代浏览器支持（Chrome 66+, Firefox 63+, Safari 13.1+）
