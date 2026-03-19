# CrossShare 预览功能改进实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 CrossShare 文件预览添加一键复制功能，并修复视频/音频格式无法播放的问题

**Architecture:**
- 文本类预览器（JSON/Markdown/Text）添加复制按钮和状态提示
- 视频/音频预览器改用后端代理加载媒体流，解决 OSS 跨域限制问题

**Tech Stack:**
- React 18, TypeScript, Tailwind CSS
- Navigator Clipboard API
- HTML5 `<video>` and `<audio>` tags
- FastAPI 后端代理

---

## Task 1: 后端文件内容接口扩展

**Files:**
- Modify: `backend/app/routes/cross_share.py`
- Test: 使用 curl 测试接口

**Step 1: 确认现有 `/files/{fileId}/content` 接口实现**

读取文件查看现有实现：
```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
grep -n "files.*content" app/routes/cross_share.py
```

**Step 2: 扩展现有接口支持媒体文件**

在现有接口中添加媒体文件类型处理，确保返回正确的 Content-Type：

```python
@router.get("/files/{fileId}/content")
async def get_file_content(
    fileId: str,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """获取文件原始内容 - 支持文本和媒体文件"""
    from app.services.oss_service import oss_service
    from fastapi.responses import StreamingResponse
    import io

    # 获取文件记录
    file = service.get_file_by_id(fileId, current_user)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # 从 OSS 获取文件内容
    try:
        oss_object = oss_service.bucket.get_object(file.oss_key)
        file_content = oss_object.read()
    except Exception as e:
        logger.error(f"Failed to get file from OSS: {e}")
        raise HTTPException(status_code=500, detail="Failed to read file content")

    # 根据文件扩展名设置 Content-Type
    ext = file.file_name.lower().split('.')[-1] if '.' in file.file_name else ''
    content_types = {
        # 文本类
        'json': 'application/json',
        'md': 'text/markdown',
        'markdown': 'text/markdown',
        'txt': 'text/plain',
        'log': 'text/plain',
        'xml': 'application/xml',
        'csv': 'text/csv',
        # 视频类
        'mp4': 'video/mp4',
        'webm': 'video/webm',
        'avi': 'video/x-msvideo',
        'mov': 'video/quicktime',
        'mkv': 'video/x-matroska',
        # 音频类
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'aac': 'audio/aac',
        'ogg': 'audio/ogg',
        'flac': 'audio/flac',
        'm4a': 'audio/mp4',
    }
    content_type = content_types.get(ext, 'application/octet-stream')

    # 返回流式响应
    return StreamingResponse(io.BytesIO(file_content), media_type=content_type)
```

**Step 3: 测试接口**

```bash
# 重启后端
cd /Users/huazhongmin/IdeaProjects/tools/backend
lsof -ti:19092 | xargs kill -9 2>/dev/null
nohup uvicorn app.main:app --reload --port 19092 > /tmp/backend.log 2>&1 &
sleep 3

# 获取 token
TOKEN=$(curl -s -X POST http://localhost:19092/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# 获取文件列表，找到一个视频文件 ID
FILE_ID=$(curl -s -X GET "http://localhost:19092/api/cross-share/files?limit=10" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; d=json.load(sys.stdin); print([f['id'] for f in d['files'] if f['file_type']=='video'][0] if any(f['file_type']=='video' for f in d['files']) else '')")

echo "Testing video file: $FILE_ID"

# 测试视频文件内容接口
curl -I -X GET "http://localhost:19092/api/cross-share/files/$FILE_ID/content" \
  -H "Authorization: Bearer $TOKEN"
```

Expected: Response should include `Content-Type: video/mp4`

**Step 4: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/routes/cross_share.py
git commit -m "feat: 扩展文件内容接口支持媒体文件流式传输"
```

---

## Task 2: JSON Viewer 添加复制功能

**Files:**
- Modify: `frontend/src/components/Tools/CrossShare/preview/JsonViewer.tsx`

**Step 1: 添加复制按钮状态和处理函数**

修改 `JsonViewer.tsx`：

```tsx
export const JsonViewer: React.FC<PreviewProps> = ({ url, fileName, fileId }) => {
  const [data, setData] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);
  const [copySuccess, setCopySuccess] = React.useState(false);

  React.useEffect(() => {
    const fetchJson = async () => {
      try {
        const response = await fetch(`/api/cross-share/files/${fileId}/content`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });
        if (!response.ok) {
          throw new Error('Failed to fetch JSON file');
        }
        const jsonData = await response.json();
        setData(jsonData);
      } catch (err) {
        console.error('Failed to load JSON:', err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchJson();
  }, [fileId]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // ... rest of component
```

**Step 2: 在 UI 中添加复制按钮**

在返回的 JSX 中添加复制按钮（在加载成功后的渲染中）：

```tsx
return (
  <div className="relative w-full h-full overflow-auto bg-slate-800 p-4">
    <button
      onClick={handleCopy}
      className="absolute top-4 right-4 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-lg transition-colors flex items-center space-x-1 z-10"
    >
      <span>{copySuccess ? '✓ 已复制' : '📋 复制'}</span>
    </button>
    <ReactJsonView
      src={data}
      theme="monokai"
      collapsed={2}
      enableClipboard={true}
      displayDataTypes={true}
      displayObjectSize={true}
      name={null}
      style={{
        backgroundColor: 'transparent',
        fontSize: '14px',
      }}
    />
  </div>
);
```

**Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/CrossShare/preview/JsonViewer.tsx
git commit -m "feat: JSON 预览器添加一键复制功能"
```

---

## Task 3: Markdown Viewer 添加复制功能

**Files:**
- Modify: `frontend/src/components/Tools/CrossShare/preview/MarkdownViewer.tsx`

**Step 1: 添加复制按钮状态和处理函数**

修改 `MarkdownViewer.tsx`，添加与 JsonViewer 类似的逻辑：

```tsx
export const MarkdownViewer: React.FC<PreviewProps> = ({ url, fileName, fileId }) => {
  const [content, setContent] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);
  const [copySuccess, setCopySuccess] = React.useState(false);

  // ... existing useEffect ...

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

**Step 2: 在 UI 中添加复制按钮**

```tsx
return (
  <div className="relative w-full h-full overflow-auto bg-slate-800 p-6">
    <button
      onClick={handleCopy}
      className="absolute top-4 right-4 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-lg transition-colors flex items-center space-x-1 z-10"
    >
      <span>{copySuccess ? '✓ 已复制' : '📋 复制'}</span>
    </button>
    <div className="max-w-4xl mx-auto prose prose-invert prose-slate">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  </div>
);
```

**Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/CrossShare/preview/MarkdownViewer.tsx
git commit -m "feat: Markdown 预览器添加一键复制功能"
```

---

## Task 4: Text Viewer 添加复制功能

**Files:**
- Modify: `frontend/src/components/Tools/CrossShare/preview/TextViewer.tsx`

**Step 1: 添加复制按钮状态和处理函数**

修改 `TextViewer.tsx`：

```tsx
export const TextViewer: React.FC<PreviewProps> = ({ url, fileName, fileId }) => {
  const [content, setContent] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);
  const [copySuccess, setCopySuccess] = React.useState(false);

  // ... existing useEffect ...

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

**Step 2: 在 UI 中添加复制按钮**

```tsx
return (
  <div className="relative w-full h-full overflow-auto bg-slate-800 p-6">
    <button
      onClick={handleCopy}
      className="absolute top-4 right-4 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-lg transition-colors flex items-center space-x-1 z-10"
    >
      <span>{copySuccess ? '✓ 已复制' : '📋 复制'}</span>
    </button>
    <pre className="text-slate-300 text-sm font-mono whitespace-pre-wrap break-words">
      {content}
    </pre>
  </div>
);
```

**Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/CrossShare/preview/TextViewer.tsx
git commit -m "feat: 文本预览器添加一键复制功能"
```

---

## Task 5: 修复 Video Viewer 播放问题

**Files:**
- Modify: `frontend/src/components/Tools/CrossShare/preview/VideoViewer.tsx`

**Step 1: 改用后端代理 URL 和原生 video 标签**

完全重写 `VideoViewer.tsx`：

```tsx
/**
 * 视频预览器
 */
import React from 'react';
import { PreviewProps } from './types';

export const VideoViewer: React.FC<PreviewProps> = ({ fileName, fileId }) => {
  const [error, setError] = React.useState(false);
  const videoUrl = `/api/cross-share/files/${fileId}/content`;

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center text-red-400">
        <div className="text-center">
          <div className="text-4xl mb-2">❌</div>
          <div>视频加载失败</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex items-center justify-center bg-slate-900">
      <video
        controls
        width="100%"
        height="100%"
        className="max-w-full max-h-full"
        crossOrigin="anonymous"
      >
        <source src={videoUrl} type="video/mp4" />
        Your browser does not support video playback
      </video>
    </div>
  );
};
```

**Step 2: 移除 react-player 依赖（如果不再使用）**

检查是否有其他组件使用 `react-player`：
```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
grep -r "react-player" src/
```

如果只有 VideoViewer 使用，可以考虑移除依赖。

**Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/CrossShare/preview/VideoViewer.tsx
git commit -m "fix: 修复视频预览器播放问题，改用后端代理加载"
```

---

## Task 6: 修复 Audio Viewer 播放问题

**Files:**
- Modify: `frontend/src/components/Tools/CrossShare/preview/AudioViewer.tsx`

**Step 1: 读取当前 AudioViewer 实现**

```bash
cat frontend/src/components/Tools/CrossShare/preview/AudioViewer.tsx
```

**Step 2: 改用后端代理 URL 和原生 audio 标签**

```tsx
/**
 * 音频预览器
 */
import React from 'react';
import { PreviewProps } from './types';

export const AudioViewer: React.FC<PreviewProps> = ({ fileName, fileId }) => {
  const [error, setError] = React.useState(false);
  const audioUrl = `/api/cross-share/files/${fileId}/content`;

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center text-red-400">
        <div className="text-center">
          <div className="text-4xl mb-2">❌</div>
          <div>音频加载失败</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex items-center justify-center bg-slate-900">
      <audio controls className="w-full max-w-md" crossOrigin="anonymous">
        <source src={audioUrl} type="audio/mpeg" />
        Your browser does not support audio playback
      </audio>
    </div>
  );
};
```

**Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/CrossShare/preview/AudioViewer.tsx
git commit -m "fix: 修复音频预览器播放问题，改用后端代理加载"
```

---

## Task 7: 浏览器验证测试

**Files:**
- 手动测试所有修改的功能

**Step 1: 启动服务**

```bash
# 后端
cd /Users/huazhongmin/IdeaProjects/tools/backend
lsof -ti:19092 | xargs kill -9 2>/dev/null
nohup uvicorn app.main:app --reload --port 19092 > /tmp/backend.log 2>&1 &

# 前端
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run dev
```

**Step 2: 使用浏览器测试**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
agent-browser open http://localhost:5178/tools/cross-share
```

**Step 3: 测试清单**

1. **JSON 复制功能**
   - 点击 JSON 文件预览按钮
   - 点击"复制"按钮
   - 验证显示"✓ 已复制"提示

2. **Markdown 复制功能**
   - 点击 Markdown 文件预览按钮
   - 点击"复制"按钮
   - 验证显示"✓ 已复制"提示

3. **文本复制功能**
   - 点击文本文件预览按钮
   - 点击"复制"按钮
   - 验证显示"✓ 已复制"提示

4. **视频播放功能**
   - 点击视频文件预览按钮
   - 验证视频能正常加载
   - 验证能播放、暂停、拖动进度条

5. **音频播放功能**
   - 点击音频文件预览按钮
   - 验证音频能正常加载
   - 验证能播放、暂停、拖动进度条

**Step 4: 检查浏览器 Console 无错误**

```bash
agent-browser eval --stdin <<'EVALEOF'
(() => {
  const errors = [];
  const originalError = console.error;
  console.error = (...args) => {
    errors.push(args.join(' '));
    originalError(...args);
  };
  return errors;
})()
EVALEOF
```

---

## Task 8: 代码清理和最终提交

**Files:**
- 检查是否有未提交的更改

**Step 1: 检查 git 状态**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git status
```

**Step 2: 确保所有更改已提交**

如果有未提交的文件：
```bash
git add .
git commit -m "chore: 完成 CrossShare 预览功能改进"
```

**Step 3: 查看完整提交历史**

```bash
git log --oneline -10
```

应该包含以下提交：
1. `feat: 扩展文件内容接口支持媒体文件流式传输`
2. `feat: JSON 预览器添加一键复制功能`
3. `feat: Markdown 预览器添加一键复制功能`
4. `feat: 文本预览器添加一键复制功能`
5. `fix: 修复视频预览器播放问题，改用后端代理加载`
6. `fix: 修复音频预览器播放问题，改用后端代理加载`

---

## 完成检查清单

- [ ] 后端接口支持媒体文件流式传输
- [ ] JSON 预览器复制功能正常
- [ ] Markdown 预览器复制功能正常
- [ ] 文本预览器复制功能正常
- [ ] 视频文件能正常播放
- [ ] 音频文件能正常播放
- [ ] 浏览器 Console 无错误
- [ ] 所有代码已提交到 git
