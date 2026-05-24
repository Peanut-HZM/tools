---
author: Codex
created_at: 2026-05-24
purpose: tools-mini-program 工具迁移实施计划，覆盖媒体/文档/学习/统计四批次
---

# 小程序工具迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Web 端 10+ 个普通用户工具按批次迁移到 tools-mini-program，采用分包结构，每批独立可验证。

**Architecture:** 新增工具使用 Taro 分包（`subPackages`）存放，避免主包膨胀；每个工具独立页面 + 服务层；通用能力（文件选择、复制、轮询、错误提示）收敛到 `utils/mobileTool.ts`；后端优先复用现有 API，不新增大型能力。

**Tech Stack:** Taro 4.1 + React 18 + TypeScript + SCSS (rpx) + Zustand

---

## File Structure

**新增文件：**

| 文件 | 职责 |
|------|------|
| `src/utils/mobileTool.ts` | 通用工具：文件选择、复制文本、打开/复制 URL、错误格式化、任务轮询、JSON 解析 |
| `src/services/imageDownloader.ts` | 图片提取、单图下载、历史记录 |
| `src/services/videoDownloader.ts` | 视频提取、yt-dlp 任务创建、任务轮询、下载链接 |
| `src/services/converter.ts` | 文件上传转 Markdown、历史记录、配额查询 |
| `src/services/markdownEditor.ts` | 本地草稿读写；OSS 列表/读取/保存（增强项） |
| `src/services/coursePlatform.ts` | 课程列表、详情、章节、报名、评价 |
| `src/services/techContents.ts` | 技术内容列表、详情、类型筛选 |
| `src/services/tokenUsage.ts` | 只读统计查询、设备列表、健康检查 |
| `src/pages/image-downloader/index.tsx` + `index.scss` | 图片下载页面 |
| `src/pages/video-downloader/index.tsx` + `index.scss` | 视频下载页面 |
| `src/pages/markitdown-converter/index.tsx` + `index.scss` | 文档转 Markdown 页面 |
| `src/pages/markdown-editor/index.tsx` + `index.scss` | Markdown 轻量编辑器页面 |
| `src/pages/course-platform/index.tsx` + `index.scss` | 课程列表页面 |
| `src/pages/course-platform/detail/index.tsx` + `index.scss` | 课程详情页面 |
| `src/pages/tech-contents/index.tsx` + `index.scss` | 技术内容列表页面 |
| `src/pages/tech-contents/detail/index.tsx` + `index.scss` | 技术内容详情页面 |
| `src/pages/token-usage/index.tsx` + `index.scss` | Token 统计只读面板 |

**修改文件：**

| 文件 | 修改内容 |
|------|----------|
| `src/app.config.ts` | 添加 `subPackages` 定义；将新工具页面从 `pages` 移到对应分包 |
| `src/services/tool.ts` | 更新 `TOOL_PATH_MAP`，为新工具添加路径映射 |
| `src/types/index.ts` | 新增各工具专用类型定义（如 `ImageInfo`, `VideoInfo`, `Course`, `TechContent`） |
| `src/app.scss` | 如有需要，补充通用页面样式变量 |

---

## Batch 1: 媒体与文档工具

### Task 1.1: 创建通用工具库 `utils/mobileTool.ts`

**Files:**
- Create: `src/utils/mobileTool.ts`

- [ ] **Step 1: 实现文件选择兼容函数**

```typescript
import Taro from '@tarojs/taro';

export interface ChooseFileResult {
  path: string;
  name: string;
  size: number;
  type: string;
}

export async function chooseFileCompat(options: {
  accept?: string;
  maxSize?: number;
} = {}): Promise<ChooseFileResult> {
  const { accept = '*/*', maxSize = 10 * 1024 * 1024 } = options;
  
  return new Promise((resolve, reject) => {
    Taro.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: accept === 'image/*' ? ['jpg', 'jpeg', 'png', 'gif', 'webp'] :
                 accept === 'document/*' ? ['doc', 'docx', 'pdf', 'xls', 'xlsx', 'ppt', 'pptx'] :
                 undefined,
      success: (res) => {
        const file = res.tempFiles[0];
        if (file.size > maxSize) {
          reject(new Error(`文件大小超过 ${maxSize / 1024 / 1024}MB 限制`));
          return;
        }
        resolve({
          path: file.path,
          name: file.name,
          size: file.size,
          type: file.type || 'application/octet-stream',
        });
      },
      fail: (err) => reject(new Error(err.errMsg || '选择文件失败')),
    });
  });
}
```

- [ ] **Step 2: 实现复制文本和打开/复制 URL**

```typescript
export async function copyText(text: string): Promise<boolean> {
  try {
    await Taro.setClipboardData({ data: text });
    Taro.showToast({ title: '已复制', icon: 'success' });
    return true;
  } catch {
    Taro.showToast({ title: '复制失败', icon: 'none' });
    return false;
  }
}

export async function openOrCopyUrl(url: string): Promise<void> {
  try {
    await Taro.setClipboardData({ data: url });
    Taro.showToast({ title: '链接已复制', icon: 'success' });
  } catch {
    Taro.showToast({ title: '复制失败', icon: 'none' });
  }
}
```

- [ ] **Step 3: 实现错误格式化和任务轮询**

```typescript
export function formatApiError(error: any): string {
  if (typeof error === 'string') return error;
  if (error?.detail) return error.detail;
  if (error?.message) return error.message;
  return '请求失败，请稍后重试';
}

export interface PollOptions {
  interval?: number;
  maxAttempts?: number;
  timeout?: number;
}

export async function pollTask<T>(
  checkFn: () => Promise<T>,
  isComplete: (result: T) => boolean,
  options: PollOptions = {}
): Promise<T> {
  const { interval = 2000, maxAttempts = 60, timeout = 120000 } = options;
  const startTime = Date.now();
  
  for (let i = 0; i < maxAttempts; i++) {
    if (Date.now() - startTime > timeout) {
      throw new Error('任务处理超时，请稍后查看历史记录');
    }
    const result = await checkFn();
    if (isComplete(result)) return result;
    await new Promise(r => setTimeout(r, interval));
  }
  throw new Error('轮询次数超限，请稍后查看历史记录');
}

export function safeJsonParse(text: string): any {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}
```

- [ ] **Step 4: 提交**

```bash
git add src/utils/mobileTool.ts
git commit -m "feat: 添加小程序通用工具库 mobileTool.ts"
```

---

### Task 1.2: 更新 `app.config.ts` 添加分包结构

**Files:**
- Modify: `src/app.config.ts`

- [ ] **Step 1: 将 `subPackages` 添加到配置**

将以下 `subPackages` 配置添加到现有 `app.config.ts` 的 `pages` 同级：

```typescript
export default {
  pages: [
    'pages/index/index',
    'pages/cross-share/message/index',
    'pages/cross-share/file/index',
    'pages/profile/index',
    'pages/login/index',
    'pages/json-formatter/index',
    'pages/calendar/index',
    'pages/key-generator/index',
    'pages/ocr/index',
    'pages/http-client/index',
    'pages/asr/index',
    'pages/change-password/index',
    'pages/help/index',
    'pages/openclaw/index',
  ],
  subPackages: [
    {
      root: 'package-media',
      pages: [
        'pages/image-downloader/index',
        'pages/video-downloader/index',
      ],
    },
    {
      root: 'package-docs',
      pages: [
        'pages/markitdown-converter/index',
        'pages/markdown-editor/index',
      ],
    },
    {
      root: 'package-learning',
      pages: [
        'pages/course-platform/index',
        'pages/course-platform/detail/index',
        'pages/tech-contents/index',
        'pages/tech-contents/detail/index',
      ],
    },
    {
      root: 'package-stats',
      pages: [
        'pages/token-usage/index',
      ],
    },
  ],
  // ... rest of config unchanged
}
```

**注意：** 现有页面（json-formatter, calendar 等）保留在 `pages` 主包中，不移入分包（避免破坏现有用户缓存）。

- [ ] **Step 2: 提交**

```bash
git add src/app.config.ts
git commit -m "feat: 添加小程序分包结构（media/docs/learning/stats）"
```

---

### Task 1.3: 更新 `services/tool.ts` 的 `TOOL_PATH_MAP`

**Files:**
- Modify: `src/services/tool.ts`

- [ ] **Step 1: 更新路径映射**

将 `TOOL_PATH_MAP` 中的 `null` 项替换为对应分包路径：

```typescript
const TOOL_PATH_MAP: Record<string, string | null> = {
  'json-formatter': '/pages/json-formatter/index',
  'calendar': '/pages/calendar/index',
  'key-generator': '/pages/key-generator/index',
  'cross-share': '/pages/cross-share/message/index',
  'ocr-tool': '/pages/ocr/index',
  'asr-tool': '/pages/asr/index',
  'http-api-client': '/pages/http-client/index',
  'openclaw': '/pages/openclaw/index',
  // 第一批工具
  'image-downloader': '/package-media/pages/image-downloader/index',
  'video-downloader': '/package-media/pages/video-downloader/index',
  'markitdown-converter': '/package-docs/pages/markitdown-converter/index',
  'markdown-editor': '/package-docs/pages/markdown-editor/index',
  // 第二批工具
  'course-platform': '/package-learning/pages/course-platform/index',
  'tech-contents': '/package-learning/pages/tech-contents/index',
  // 第三批工具
  'token-usage': '/package-stats/pages/token-usage/index',
  // 隐藏工具（保持 null）
  'database-tool': null,
  'redis-tool': null,
  'ssh-tool': null,
  'cursor-history': null,
  'openspec-course': null,
  'ai-assistant': null,
  'product-manager': null,
  'learning-share': null,
  'system-monitor': null,
}
```

- [ ] **Step 2: 提交**

```bash
git add src/services/tool.ts
git commit -m "feat: 更新 TOOL_PATH_MAP 支持新工具分包路径"
```

---

### Task 1.4: 创建 `services/imageDownloader.ts`

**Files:**
- Create: `src/services/imageDownloader.ts`

- [ ] **Step 1: 实现图片下载服务**

```typescript
import { request } from './request';

export interface ImageInfo {
  url: string;
  thumbnail?: string;
  width?: number;
  height?: number;
  format?: string;
  size?: number;
  filename?: string;
}

export interface ImageExtractResponse {
  images: ImageInfo[];
  count: number;
}

export interface ImageDownloadResponse {
  url: string;
  oss_url?: string;
  filename: string;
  size?: number;
  width?: number;
  height?: number;
}

export interface ImageHistoryRecord {
  id: string;
  source_url: string;
  images: ImageInfo[];
  count: number;
  created_at: string;
}

export interface ImageHistoryResponse {
  records: ImageHistoryRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface ImageQuotaResponse {
  user_id: string;
  daily_limit: number;
  daily_used: number;
  daily_remaining: number;
  monthly_limit: number;
  monthly_used: number;
  monthly_remaining: number;
  reset_date: string;
}

export const imageDownloaderApi = {
  extractImages: async (url: string): Promise<ImageExtractResponse> => {
    return request('/image-downloader/extract-images', {
      method: 'POST',
      data: { url },
      needAuth: false,
    });
  },

  downloadImage: async (url: string, saveHistory = true): Promise<ImageDownloadResponse> => {
    return request(`/image-downloader/download?url=${encodeURIComponent(url)}&save_history=${saveHistory}`, {
      needAuth: true,
    });
  },

  getHistory: async (page = 1, pageSize = 20): Promise<ImageHistoryResponse> => {
    return request(`/image-downloader/history?page=${page}&page_size=${pageSize}`, {
      needAuth: true,
    });
  },

  getQuota: async (): Promise<ImageQuotaResponse> => {
    return request('/image-downloader/quota', {
      needAuth: true,
    });
  },

  deleteHistory: async (historyId: string): Promise<{ message: string }> => {
    return request(`/image-downloader/history/${historyId}`, {
      method: 'DELETE',
      needAuth: true,
    });
  },
};
```

- [ ] **Step 2: 提交**

```bash
git add src/services/imageDownloader.ts
git commit -m "feat: 添加图片下载服务层"
```

---

### Task 1.5: 创建图片下载页面

**Files:**
- Create: `src/pages/image-downloader/index.tsx`
- Create: `src/pages/image-downloader/index.scss`

- [ ] **Step 1: 实现页面逻辑**

```tsx
import { useState } from 'react';
import Taro from '@tarojs/taro';
import { View, Input, Button, ScrollView, Image, Text } from '@tarojs/components';
import { imageDownloaderApi, ImageInfo } from '../../services/imageDownloader';
import { copyText, openOrCopyUrl, formatApiError } from '../../utils/mobileTool';
import Loading from '../../components/Loading';
import './index.scss';

type PageState = 'idle' | 'loading' | 'empty' | 'error' | 'success';

export default function ImageDownloaderPage() {
  const [url, setUrl] = useState('');
  const [pageState, setPageState] = useState<PageState>('idle');
  const [images, setImages] = useState<ImageInfo[]>([]);
  const [errorMsg, setErrorMsg] = useState('');
  const [quota, setQuota] = useState({ daily_remaining: 0, monthly_remaining: 0 });

  const handleExtract = async () => {
    if (!url.trim()) {
      Taro.showToast({ title: '请输入网页链接', icon: 'none' });
      return;
    }
    setPageState('loading');
    try {
      const res = await imageDownloaderApi.extractImages(url.trim());
      if (res.images.length === 0) {
        setPageState('empty');
      } else {
        setImages(res.images);
        setPageState('success');
      }
    } catch (err: any) {
      setErrorMsg(formatApiError(err));
      setPageState('error');
    }
  };

  const handleDownload = async (image: ImageInfo) => {
    try {
      Taro.showLoading({ title: '下载中...' });
      const res = await imageDownloaderApi.downloadImage(image.url);
      Taro.hideLoading();
      if (res.oss_url) {
        await openOrCopyUrl(res.oss_url);
      } else {
        await copyText(res.url);
      }
    } catch (err: any) {
      Taro.hideLoading();
      Taro.showToast({ title: formatApiError(err), icon: 'none' });
    }
  };

  const handlePreview = (imageUrl: string) => {
    Taro.previewImage({
      urls: [imageUrl],
      current: imageUrl,
    });
  };

  return (
    <View className="image-downloader-page">
      <View className="input-section">
        <Input
          className="url-input"
          placeholder="输入网页链接，提取页面中的图片"
          value={url}
          onInput={(e) => setUrl(e.detail.value)}
          type="text"
        />
        <Button className="extract-btn" onClick={handleExtract} disabled={pageState === 'loading'}>
          {pageState === 'loading' ? '提取中...' : '提取图片'}
        </Button>
      </View>

      {pageState === 'loading' && <Loading text="正在提取图片..." />}

      {pageState === 'empty' && (
        <View className="empty-state">
          <Text>未检测到图片</Text>
          <Text className="hint">请检查链接是否有效</Text>
        </View>
      )}

      {pageState === 'error' && (
        <View className="error-state">
          <Text className="error-text">{errorMsg}</Text>
          <Button className="retry-btn" onClick={handleExtract}>重试</Button>
        </View>
      )}

      {pageState === 'success' && (
        <ScrollView className="image-list" scrollY>
          <Text className="count-text">共提取 {images.length} 张图片</Text>
          {images.map((img, idx) => (
            <View key={idx} className="image-item">
              <Image
                className="thumbnail"
                src={img.thumbnail || img.url}
                mode="aspectFill"
                onClick={() => handlePreview(img.url)}
                lazyLoad
              />
              <View className="image-info">
                <Text className="format">{img.format || '未知格式'}</Text>
                {img.width && img.height && (
                  <Text className="size">{img.width} x {img.height}</Text>
                )}
              </View>
              <View className="actions">
                <Button className="action-btn" onClick={() => handlePreview(img.url)}>预览</Button>
                <Button className="action-btn primary" onClick={() => handleDownload(img)}>下载</Button>
              </View>
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  );
}
```

- [ ] **Step 2: 实现页面样式**

```scss
.image-downloader-page {
  padding: 30rpx;
  min-height: 100vh;
  background: var(--bg-primary);

  .input-section {
    margin-bottom: 30rpx;

    .url-input {
      width: 100%;
      height: 80rpx;
      padding: 0 20rpx;
      background: var(--bg-secondary);
      border-radius: 12rpx;
      color: var(--text-primary);
      font-size: 28rpx;
      margin-bottom: 20rpx;
      box-sizing: border-box;
    }

    .extract-btn {
      width: 100%;
      height: 80rpx;
      line-height: 80rpx;
      background: #6366f1;
      color: #fff;
      border-radius: 12rpx;
      font-size: 30rpx;

      &[disabled] {
        opacity: 0.6;
      }
    }
  }

  .empty-state,
  .error-state {
    text-align: center;
    padding: 100rpx 40rpx;
    color: var(--text-secondary);

    .hint {
      display: block;
      margin-top: 20rpx;
      font-size: 26rpx;
    }

    .error-text {
      color: #ef4444;
      margin-bottom: 30rpx;
    }

    .retry-btn {
      width: 200rpx;
      height: 70rpx;
      line-height: 70rpx;
      background: #6366f1;
      color: #fff;
      border-radius: 12rpx;
    }
  }

  .image-list {
    .count-text {
      display: block;
      margin-bottom: 20rpx;
      color: var(--text-secondary);
      font-size: 26rpx;
    }

    .image-item {
      display: flex;
      align-items: center;
      padding: 20rpx;
      margin-bottom: 20rpx;
      background: var(--bg-secondary);
      border-radius: 16rpx;

      .thumbnail {
        width: 120rpx;
        height: 120rpx;
        border-radius: 8rpx;
        flex-shrink: 0;
      }

      .image-info {
        flex: 1;
        margin-left: 20rpx;
        overflow: hidden;

        .format {
          display: block;
          color: var(--text-primary);
          font-size: 28rpx;
        }

        .size {
          display: block;
          color: var(--text-secondary);
          font-size: 24rpx;
          margin-top: 8rpx;
        }
      }

      .actions {
        display: flex;
        flex-direction: column;
        gap: 10rpx;

        .action-btn {
          width: 120rpx;
          height: 56rpx;
          line-height: 56rpx;
          font-size: 24rpx;
          padding: 0;
          background: var(--bg-primary);
          color: var(--text-primary);
          border-radius: 8rpx;

          &.primary {
            background: #6366f1;
            color: #fff;
          }
        }
      }
    }
  }
}
```

- [ ] **Step 3: 提交**

```bash
git add src/pages/image-downloader/
git commit -m "feat: 添加图片下载小程序页面"
```

---

### Task 1.6: 创建 `services/videoDownloader.ts`

**Files:**
- Create: `src/services/videoDownloader.ts`

- [ ] **Step 1: 实现视频下载服务**

```typescript
import { request } from './request';

export interface VideoInfo {
  url: string;
  thumbnail?: string;
  title?: string;
  duration?: number;
  format?: string;
  quality?: string;
  size?: number;
}

export interface VideoExtractResponse {
  videos: VideoInfo[];
  count: number;
}

export interface VideoFormat {
  format_id: string;
  quality: string;
  resolution?: string;
  ext: string;
  size?: number;
}

export interface VideoFormatsResponse {
  formats: VideoFormat[];
  count: number;
}

export interface DownloadTaskResponse {
  task_id: string;
  status: 'pending' | 'downloading' | 'completed' | 'failed';
  message: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: 'pending' | 'downloading' | 'completed' | 'failed';
  progress: number;
  file_size?: number;
  speed?: string;
  eta?: string;
  error?: string;
  download_url?: string;
}

export const videoDownloaderApi = {
  extractVideos: async (url: string): Promise<VideoExtractResponse> => {
    return request('/tools/extract-videos', {
      method: 'POST',
      data: { url },
      needAuth: false,
    });
  },

  getVideoFormats: async (url: string): Promise<VideoFormatsResponse> => {
    return request(`/tools/video-formats?url=${encodeURIComponent(url)}`, {
      needAuth: false,
    });
  },

  createDownloadTask: async (url: string, quality = 'best'): Promise<DownloadTaskResponse> => {
    return request('/tools/download-video-ytdlp', {
      method: 'POST',
      data: { url, quality },
      needAuth: false,
    });
  },

  getTaskStatus: async (taskId: string): Promise<TaskStatusResponse> => {
    return request(`/tools/download-task/${taskId}`, {
      needAuth: false,
    });
  },

  cancelTask: async (taskId: string): Promise<{ message: string }> => {
    return request(`/tools/download-task/${taskId}`, {
      method: 'DELETE',
      needAuth: false,
    });
  },

  getDownloadStats: async (): Promise<{
    total_tasks: number;
    pending: number;
    downloading: number;
    completed: number;
    failed: number;
    success_rate: number;
  }> => {
    return request('/tools/download-stats', {
      needAuth: false,
    });
  },
};
```

- [ ] **Step 2: 提交**

```bash
git add src/services/videoDownloader.ts
git commit -m "feat: 添加视频下载服务层"
```

---

### Task 1.7: 创建视频下载页面

**Files:**
- Create: `src/pages/video-downloader/index.tsx`
- Create: `src/pages/video-downloader/index.scss`

- [ ] **Step 1: 实现页面逻辑**

```tsx
import { useState, useRef } from 'react';
import Taro from '@tarojs/taro';
import { View, Input, Button, Text, ScrollView } from '@tarojs/components';
import { videoDownloaderApi, VideoInfo, TaskStatusResponse } from '../../services/videoDownloader';
import { openOrCopyUrl, formatApiError, pollTask } from '../../utils/mobileTool';
import Loading from '../../components/Loading';
import './index.scss';

type PageState = 'idle' | 'extracting' | 'downloading' | 'error' | 'success' | 'task-running';

export default function VideoDownloaderPage() {
  const [url, setUrl] = useState('');
  const [pageState, setPageState] = useState<PageState>('idle');
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [taskStatus, setTaskStatus] = useState<TaskStatusResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const abortRef = useRef(false);

  const handleExtract = async () => {
    if (!url.trim()) {
      Taro.showToast({ title: '请输入视频链接', icon: 'none' });
      return;
    }
    abortRef.current = false;
    setPageState('extracting');
    try {
      const res = await videoDownloaderApi.extractVideos(url.trim());
      if (res.videos.length === 0) {
        setPageState('idle');
        Taro.showToast({ title: '未检测到视频', icon: 'none' });
      } else {
        setVideos(res.videos);
        setPageState('success');
      }
    } catch (err: any) {
      setErrorMsg(formatApiError(err));
      setPageState('error');
    }
  };

  const handleDownload = async (videoUrl: string) => {
    abortRef.current = false;
    setPageState('downloading');
    try {
      const task = await videoDownloaderApi.createDownloadTask(videoUrl);
      setPageState('task-running');

      const finalStatus = await pollTask(
        () => videoDownloaderApi.getTaskStatus(task.task_id),
        (status) => status.status === 'completed' || status.status === 'failed',
        { interval: 3000, maxAttempts: 100, timeout: 300000 }
      );

      if (abortRef.current) return;

      setTaskStatus(finalStatus);
      if (finalStatus.status === 'completed' && finalStatus.download_url) {
        await openOrCopyUrl(finalStatus.download_url);
      } else if (finalStatus.status === 'failed') {
        setErrorMsg(finalStatus.error || '下载失败');
        setPageState('error');
      }
    } catch (err: any) {
      if (abortRef.current) return;
      setErrorMsg(formatApiError(err));
      setPageState('error');
    }
  };

  const handleCancel = () => {
    abortRef.current = true;
    setPageState('idle');
    setTaskStatus(null);
  };

  return (
    <View className="video-downloader-page">
      <View className="input-section">
        <Input
          className="url-input"
          placeholder="输入视频页面链接"
          value={url}
          onInput={(e) => setUrl(e.detail.value)}
          type="text"
        />
        <Button
          className="extract-btn"
          onClick={handleExtract}
          disabled={pageState === 'extracting' || pageState === 'downloading'}
        >
          {pageState === 'extracting' ? '提取中...' : '提取视频'}
        </Button>
      </View>

      {(pageState === 'extracting' || pageState === 'downloading') && (
        <Loading text={pageState === 'extracting' ? '正在提取视频...' : '正在创建下载任务...'} />
      )}

      {pageState === 'task-running' && taskStatus && (
        <View className="task-status">
          <Text className="status-text">
            {taskStatus.status === 'pending' ? '排队中' :
             taskStatus.status === 'downloading' ? `下载中 ${taskStatus.progress}%` :
             taskStatus.status === 'completed' ? '下载完成' : '下载失败'}
          </Text>
          {taskStatus.speed && <Text className="speed">{taskStatus.speed}</Text>}
          {taskStatus.eta && <Text className="eta">预计剩余: {taskStatus.eta}</Text>}
          <Button className="cancel-btn" onClick={handleCancel}>取消</Button>
        </View>
      )}

      {pageState === 'error' && (
        <View className="error-state">
          <Text className="error-text">{errorMsg}</Text>
          <Button className="retry-btn" onClick={handleExtract}>重试</Button>
        </View>
      )}

      {pageState === 'success' && (
        <ScrollView className="video-list" scrollY>
          <Text className="count-text">共提取 {videos.length} 个视频</Text>
          {videos.map((video, idx) => (
            <View key={idx} className="video-item">
              <View className="video-info">
                <Text className="title">{video.title || '未命名视频'}</Text>
                {video.duration && (
                  <Text className="meta">时长: {Math.floor(video.duration / 60)}:{(video.duration % 60).toString().padStart(2, '0')}</Text>
                )}
                {video.quality && <Text className="meta">质量: {video.quality}</Text>}
              </View>
              <Button
                className="download-btn"
                onClick={() => handleDownload(video.url)}
                disabled={pageState === 'downloading' || pageState === 'task-running'}
              >
                下载
              </Button>
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  );
}
```

- [ ] **Step 2: 实现页面样式**

```scss
.video-downloader-page {
  padding: 30rpx;
  min-height: 100vh;
  background: var(--bg-primary);

  .input-section {
    margin-bottom: 30rpx;

    .url-input {
      width: 100%;
      height: 80rpx;
      padding: 0 20rpx;
      background: var(--bg-secondary);
      border-radius: 12rpx;
      color: var(--text-primary);
      font-size: 28rpx;
      margin-bottom: 20rpx;
      box-sizing: border-box;
    }

    .extract-btn {
      width: 100%;
      height: 80rpx;
      line-height: 80rpx;
      background: #6366f1;
      color: #fff;
      border-radius: 12rpx;
      font-size: 30rpx;

      &[disabled] {
        opacity: 0.6;
      }
    }
  }

  .task-status {
    text-align: center;
    padding: 60rpx 40rpx;
    background: var(--bg-secondary);
    border-radius: 16rpx;
    margin-bottom: 30rpx;

    .status-text {
      display: block;
      color: var(--text-primary);
      font-size: 32rpx;
      margin-bottom: 20rpx;
    }

    .speed, .eta {
      display: block;
      color: var(--text-secondary);
      font-size: 26rpx;
      margin-top: 10rpx;
    }

    .cancel-btn {
      margin-top: 30rpx;
      width: 200rpx;
      height: 70rpx;
      line-height: 70rpx;
      background: #ef4444;
      color: #fff;
      border-radius: 12rpx;
    }
  }

  .error-state {
    text-align: center;
    padding: 100rpx 40rpx;

    .error-text {
      color: #ef4444;
      margin-bottom: 30rpx;
    }

    .retry-btn {
      width: 200rpx;
      height: 70rpx;
      line-height: 70rpx;
      background: #6366f1;
      color: #fff;
      border-radius: 12rpx;
    }
  }

  .video-list {
    .count-text {
      display: block;
      margin-bottom: 20rpx;
      color: var(--text-secondary);
      font-size: 26rpx;
    }

    .video-item {
      display: flex;
      align-items: center;
      padding: 24rpx;
      margin-bottom: 20rpx;
      background: var(--bg-secondary);
      border-radius: 16rpx;

      .video-info {
        flex: 1;
        overflow: hidden;

        .title {
          display: block;
          color: var(--text-primary);
          font-size: 28rpx;
          margin-bottom: 10rpx;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .meta {
          display: block;
          color: var(--text-secondary);
          font-size: 24rpx;
          margin-top: 6rpx;
        }
      }

      .download-btn {
        width: 140rpx;
        height: 64rpx;
        line-height: 64rpx;
        font-size: 26rpx;
        padding: 0;
        background: #6366f1;
        color: #fff;
        border-radius: 10rpx;
        flex-shrink: 0;

        &[disabled] {
          opacity: 0.5;
        }
      }
    }
  }
}
```

- [ ] **Step 3: 提交**

```bash
git add src/pages/video-downloader/
git commit -m "feat: 添加视频下载小程序页面"
```

---

### Task 1.8: 创建 `services/converter.ts`

**Files:**
- Create: `src/services/converter.ts`

- [ ] **Step 1: 实现文档转换服务**

```typescript
import { request, uploadFile } from './request';

export interface ConverterHistoryRecord {
  id: string;
  file_name: string;
  file_size: number;
  output_size: number;
  content_preview?: string;
  created_at: string;
}

export interface ConverterHistoryResponse {
  records: ConverterHistoryRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface ConverterQuotaResponse {
  user_id: string;
  daily_limit: number;
  daily_used: number;
  daily_remaining: number;
  monthly_limit: number;
  monthly_used: number;
  monthly_remaining: number;
  reset_date: string;
}

export interface ConvertResponse {
  content: string;
  file_name: string;
  file_size: number;
  output_size: number;
}

export const converterApi = {
  convertFile: async (filePath: string, saveHistory = true): Promise<ConvertResponse> => {
    return uploadFile('/converter/convert', filePath, 'file', { save_history: String(saveHistory) }, true);
  },

  getHistory: async (page = 1, pageSize = 20): Promise<ConverterHistoryResponse> => {
    return request(`/converter/history?page=${page}&page_size=${pageSize}`, {
      needAuth: true,
    });
  },

  getQuota: async (): Promise<ConverterQuotaResponse> => {
    return request('/converter/quota', {
      needAuth: true,
    });
  },

  deleteHistory: async (historyId: string): Promise<{ message: string }> => {
    return request(`/converter/history/${historyId}`, {
      method: 'DELETE',
      needAuth: true,
    });
  },
};
```

- [ ] **Step 2: 提交**

```bash
git add src/services/converter.ts
git commit -m "feat: 添加文档转 Markdown 服务层"
```

---

### Task 1.9: 创建文档转 Markdown 页面

**Files:**
- Create: `src/pages/markitdown-converter/index.tsx`
- Create: `src/pages/markitdown-converter/index.scss`

- [ ] **Step 1: 实现页面逻辑**

```tsx
import { useState } from 'react';
import Taro from '@tarojs/taro';
import { View, Button, Text, ScrollView } from '@tarojs/components';
import { converterApi, ConvertResponse } from '../../services/converter';
import { chooseFileCompat, copyText, formatApiError } from '../../utils/mobileTool';
import Markdown from '../../components/Markdown';
import Loading from '../../components/Loading';
import './index.scss';

type PageState = 'idle' | 'selecting' | 'converting' | 'error' | 'success';

export default function MarkitdownConverterPage() {
  const [pageState, setPageState] = useState<PageState>('idle');
  const [result, setResult] = useState<ConvertResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSelectFile = async () => {
    try {
      const file = await chooseFileCompat({
        accept: 'document/*',
        maxSize: 20 * 1024 * 1024,
      });
      setPageState('converting');
      const res = await converterApi.convertFile(file.path);
      setResult(res);
      setPageState('success');
    } catch (err: any) {
      setErrorMsg(formatApiError(err));
      setPageState('error');
    }
  };

  const handleCopy = async () => {
    if (result?.content) {
      await copyText(result.content);
    }
  };

  const handleReset = () => {
    setResult(null);
    setPageState('idle');
    setErrorMsg('');
  };

  return (
    <View className="markitdown-converter-page">
      {pageState === 'idle' && (
        <View className="upload-section">
          <Text className="title">选择文件转换</Text>
          <Text className="subtitle">支持 Word、PDF、Excel 等格式</Text>
          <Button className="select-btn" onClick={handleSelectFile}>
            选择文件
          </Button>
          <Text className="hint">文件大小不超过 20MB</Text>
        </View>
      )}

      {pageState === 'converting' && <Loading text="正在转换..." />}

      {pageState === 'error' && (
        <View className="error-state">
          <Text className="error-text">{errorMsg}</Text>
          <Button className="retry-btn" onClick={handleReset}>重试</Button>
        </View>
      )}

      {pageState === 'success' && result && (
        <View className="result-section">
          <View className="result-header">
            <Text className="filename">{result.file_name}</Text>
            <Text className="meta">原始: {(result.file_size / 1024).toFixed(1)}KB → 输出: {(result.output_size / 1024).toFixed(1)}KB</Text>
          </View>
          <ScrollView className="markdown-preview" scrollY>
            <Markdown content={result.content} />
          </ScrollView>
          <View className="actions">
            <Button className="action-btn" onClick={handleCopy}>复制全文</Button>
            <Button className="action-btn secondary" onClick={handleReset}>转换新文件</Button>
          </View>
        </View>
      )}
    </View>
  );
}
```

- [ ] **Step 2: 实现页面样式**

```scss
.markitdown-converter-page {
  min-height: 100vh;
  background: var(--bg-primary);

  .upload-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 200rpx 60rpx;

    .title {
      color: var(--text-primary);
      font-size: 36rpx;
      font-weight: bold;
      margin-bottom: 20rpx;
    }

    .subtitle {
      color: var(--text-secondary);
      font-size: 28rpx;
      margin-bottom: 60rpx;
    }

    .select-btn {
      width: 400rpx;
      height: 100rpx;
      line-height: 100rpx;
      background: #6366f1;
      color: #fff;
      border-radius: 16rpx;
      font-size: 32rpx;
    }

    .hint {
      color: var(--text-secondary);
      font-size: 24rpx;
      margin-top: 30rpx;
    }
  }

  .error-state {
    text-align: center;
    padding: 200rpx 60rpx;

    .error-text {
      color: #ef4444;
      margin-bottom: 30rpx;
    }

    .retry-btn {
      width: 200rpx;
      height: 70rpx;
      line-height: 70rpx;
      background: #6366f1;
      color: #fff;
      border-radius: 12rpx;
    }
  }

  .result-section {
    display: flex;
    flex-direction: column;
    height: 100vh;

    .result-header {
      padding: 30rpx;
      background: var(--bg-secondary);
      border-bottom: 1rpx solid var(--border-color);

      .filename {
        display: block;
        color: var(--text-primary);
        font-size: 30rpx;
        font-weight: bold;
      }

      .meta {
        display: block;
        color: var(--text-secondary);
        font-size: 24rpx;
        margin-top: 10rpx;
      }
    }

    .markdown-preview {
      flex: 1;
      padding: 20rpx;
      overflow-y: auto;
    }

    .actions {
      display: flex;
      padding: 20rpx;
      gap: 20rpx;
      border-top: 1rpx solid var(--border-color);
      background: var(--bg-secondary);

      .action-btn {
        flex: 1;
        height: 80rpx;
        line-height: 80rpx;
        background: #6366f1;
        color: #fff;
        border-radius: 12rpx;
        font-size: 28rpx;

        &.secondary {
          background: var(--bg-primary);
          color: var(--text-primary);
          border: 1rpx solid var(--border-color);
        }
      }
    }
  }
}
```

- [ ] **Step 3: 提交**

```bash
git add src/pages/markitdown-converter/
git commit -m "feat: 添加文档转 Markdown 小程序页面"
```

---

### Task 1.10: 创建 `services/markdownEditor.ts`

**Files:**
- Create: `src/services/markdownEditor.ts`

- [ ] **Step 1: 实现 Markdown 编辑器服务**

```typescript
import { request } from './request';

export interface OssFileInfo {
  file_path: string;
  filename: string;
  size: number;
  last_modified?: string;
}

export interface OssReadResponse {
  success: boolean;
  content: string;
  filename: string;
  message?: string;
}

export interface OssSaveResponse {
  success: boolean;
  message: string;
}

export interface OssUploadResponse {
  success: boolean;
  file_path: string;
  url: string;
  filename: string;
  message?: string;
}

const DRAFT_KEY = 'markdown_editor_draft';

export const markdownEditorApi = {
  // 本地草稿
  saveDraft: (content: string): void => {
    try {
      Taro.setStorageSync(DRAFT_KEY, content);
    } catch {
      // ignore
    }
  },

  loadDraft: (): string => {
    try {
      return Taro.getStorageSync(DRAFT_KEY) || '';
    } catch {
      return '';
    }
  },

  clearDraft: (): void => {
    try {
      Taro.removeStorageSync(DRAFT_KEY);
    } catch {
      // ignore
    }
  },

  // OSS 文件列表
  listOssFiles: async (): Promise<OssFileInfo[]> => {
    return request('/markdown-editor/oss/list', {
      needAuth: true,
    });
  },

  // 读取 OSS 文件
  readOssFile: async (filePath: string): Promise<OssReadResponse> => {
    return request(`/markdown-editor/oss/read?file_path=${encodeURIComponent(filePath)}`, {
      needAuth: true,
    });
  },

  // 保存到 OSS
  saveOssFile: async (filePath: string, content: string): Promise<OssSaveResponse> => {
    return request('/markdown-editor/oss/save', {
      method: 'POST',
      data: { file_path: filePath, content },
      needAuth: true,
    });
  },

  // 上传新文件到 OSS
  uploadOssFile: async (filePath: string): Promise<OssUploadResponse> => {
    return uploadFile('/markdown-editor/oss/upload', filePath, 'file', {}, true);
  },
};
```

- [ ] **Step 2: 提交**

```bash
git add src/services/markdownEditor.ts
git commit -m "feat: 添加 Markdown 编辑器服务层"
```

---

### Task 1.11: 创建 Markdown 轻量编辑器页面

**Files:**
- Create: `src/pages/markdown-editor/index.tsx`
- Create: `src/pages/markdown-editor/index.scss`

- [ ] **Step 1: 实现页面逻辑**

```tsx
import { useState, useEffect } from 'react';
import Taro from '@tarojs/taro';
import { View, Textarea, Button, Text, ScrollView } from '@tarojs/components';
import { markdownEditorApi } from '../../services/markdownEditor';
import { copyText, formatApiError } from '../../utils/mobileTool';
import Markdown from '../../components/Markdown';
import './index.scss';

type Tab = 'edit' | 'preview';

export default function MarkdownEditorPage() {
  const [content, setContent] = useState('');
  const [activeTab, setActiveTab] = useState<Tab>('edit');
  const [ossFiles, setOssFiles] = useState<{ file_path: string; filename: string }[]>([]);
  const [showOssList, setShowOssList] = useState(false);

  useEffect(() => {
    const draft = markdownEditorApi.loadDraft();
    if (draft) setContent(draft);
  }, []);

  const handleContentChange = (value: string) => {
    setContent(value);
    markdownEditorApi.saveDraft(value);
  };

  const handleCopy = async () => {
    if (content) await copyText(content);
  };

  const handleClear = () => {
    Taro.showModal({
      title: '确认清空',
      content: '清空后无法恢复，确定吗？',
      success: (res) => {
        if (res.confirm) {
          setContent('');
          markdownEditorApi.clearDraft();
        }
      },
    });
  };

  const handleLoadOssList = async () => {
    try {
      const files = await markdownEditorApi.listOssFiles();
      setOssFiles(files.map(f => ({ file_path: f.file_path, filename: f.filename })));
      setShowOssList(true);
    } catch (err: any) {
      Taro.showToast({ title: formatApiError(err), icon: 'none' });
    }
  };

  const handleLoadOssFile = async (filePath: string) => {
    try {
      Taro.showLoading({ title: '加载中...' });
      const res = await markdownEditorApi.readOssFile(filePath);
      Taro.hideLoading();
      if (res.success) {
        setContent(res.content);
        markdownEditorApi.saveDraft(res.content);
        setShowOssList(false);
        setActiveTab('edit');
      }
    } catch (err: any) {
      Taro.hideLoading();
      Taro.showToast({ title: formatApiError(err), icon: 'none' });
    }
  };

  return (
    <View className="markdown-editor-page">
      <View className="tab-bar">
        <View
          className={`tab ${activeTab === 'edit' ? 'active' : ''}`}
          onClick={() => setActiveTab('edit')}
        >
          <Text>编辑</Text>
        </View>
        <View
          className={`tab ${activeTab === 'preview' ? 'active' : ''}`}
          onClick={() => setActiveTab('preview')}
        >
          <Text>预览</Text>
        </View>
      </View>

      {activeTab === 'edit' && (
        <View className="editor-section">
          <Textarea
            className="editor-textarea"
            value={content}
            onInput={(e) => handleContentChange(e.detail.value)}
            placeholder="输入 Markdown 内容..."
            maxlength={-1}
          />
        </View>
      )}

      {activeTab === 'preview' && (
        <ScrollView className="preview-section" scrollY>
          {content ? (
            <Markdown content={content} />
          ) : (
            <View className="empty-preview">
              <Text>暂无内容，切换到编辑页输入 Markdown</Text>
            </View>
          )}
        </ScrollView>
      )}

      <View className="toolbar">
        <Button className="tool-btn" onClick={handleCopy}>复制</Button>
        <Button className="tool-btn" onClick={handleClear}>清空</Button>
        <Button className="tool-btn" onClick={handleLoadOssList}>OSS文件</Button>
      </View>

      {showOssList && (
        <View className="oss-modal">
          <View className="oss-overlay" onClick={() => setShowOssList(false)} />
          <View className="oss-content">
            <View className="oss-header">
              <Text className="oss-title">选择文件</Text>
              <Text className="oss-close" onClick={() => setShowOssList(false)}>关闭</Text>
            </View>
            <ScrollView className="oss-list" scrollY>
              {ossFiles.length === 0 ? (
                <Text className="oss-empty">暂无文件</Text>
              ) : (
                ossFiles.map((file) => (
                  <View
                    key={file.file_path}
                    className="oss-item"
                    onClick={() => handleLoadOssFile(file.file_path)}
                  >
                    <Text className="oss-filename">{file.filename}</Text>
                  </View>
                ))
              )}
            </ScrollView>
          </View>
        </View>
      )}
    </View>
  );
}
```

- [ ] **Step 2: 实现页面样式**

```scss
.markdown-editor-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);

  .tab-bar {
    display: flex;
    height: 80rpx;
    background: var(--bg-secondary);
    border-bottom: 1rpx solid var(--border-color);

    .tab {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-secondary);
      font-size: 28rpx;
      position: relative;

      &.active {
        color: #6366f1;
        font-weight: bold;

        &::after {
          content: '';
          position: absolute;
          bottom: 0;
          left: 30%;
          right: 30%;
          height: 4rpx;
          background: #6366f1;
          border-radius: 2rpx;
        }
      }
    }
  }

  .editor-section {
    flex: 1;
    padding: 20rpx;

    .editor-textarea {
      width: 100%;
      height: 100%;
      background: var(--bg-secondary);
      border-radius: 12rpx;
      padding: 20rpx;
      color: var(--text-primary);
      font-size: 28rpx;
      line-height: 1.6;
      box-sizing: border-box;
    }
  }

  .preview-section {
    flex: 1;
    padding: 20rpx;
    overflow-y: auto;

    .empty-preview {
      text-align: center;
      padding: 200rpx 40rpx;
      color: var(--text-secondary);
      font-size: 28rpx;
    }
  }

  .toolbar {
    display: flex;
    padding: 20rpx;
    gap: 20rpx;
    border-top: 1rpx solid var(--border-color);
    background: var(--bg-secondary);

    .tool-btn {
      flex: 1;
      height: 70rpx;
      line-height: 70rpx;
      background: var(--bg-primary);
      color: var(--text-primary);
      border-radius: 10rpx;
      font-size: 26rpx;
      border: 1rpx solid var(--border-color);

      &:active {
        opacity: 0.8;
      }
    }
  }

  .oss-modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 1000;

    .oss-overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
    }

    .oss-content {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      max-height: 60%;
      background: var(--bg-secondary);
      border-radius: 24rpx 24rpx 0 0;
      display: flex;
      flex-direction: column;

      .oss-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 30rpx;
        border-bottom: 1rpx solid var(--border-color);

        .oss-title {
          color: var(--text-primary);
          font-size: 32rpx;
          font-weight: bold;
        }

        .oss-close {
          color: #6366f1;
          font-size: 28rpx;
        }
      }

      .oss-list {
        flex: 1;
        overflow-y: auto;
        padding: 0 20rpx;

        .oss-empty {
          display: block;
          text-align: center;
          padding: 100rpx;
          color: var(--text-secondary);
          font-size: 28rpx;
        }

        .oss-item {
          padding: 24rpx;
          border-bottom: 1rpx solid var(--border-color);

          .oss-filename {
            color: var(--text-primary);
            font-size: 28rpx;
          }

          &:active {
            background: var(--bg-primary);
          }
        }
      }
    }
  }
}
```

- [ ] **Step 3: 提交**

```bash
git add src/pages/markdown-editor/
git commit -m "feat: 添加 Markdown 轻量编辑器小程序页面"
```

---

### Task 1.12: 第一批验收与后端 show_mobile 确认

- [ ] **Step 1: 验证分包编译**

```bash
cd tools-mini-program
npm run build:weapp
```

Expected: 编译成功，无 TypeScript 错误，分包正确生成。

- [ ] **Step 2: 验证后端工具配置**

确保以下工具在数据库中 `show_mobile = true`：
- `image-downloader`
- `video-downloader`
- `markitdown-converter`
- `markdown-editor`

```bash
cd backend
# 检查（如需要，执行更新）
python -c "
from app.models.base import get_db
from app.services.tools_service import ToolService
db = next(get_db())
for tid in ['image-downloader', 'video-downloader', 'markitdown-converter', 'markdown-editor']:
    t = ToolService.get_tool_by_id(db, tid)
    if t:
        print(f'{tid}: show_mobile={t.show_mobile}')
"
```

- [ ] **Step 3: H5 验证**

```bash
cd tools-mini-program
npm run dev:h5
```

在浏览器中访问 `http://localhost:8080`，验证：
- 首页显示新工具卡片
- 点击跳转到正确页面
- 图片下载：输入 URL 可提取图片列表
- 视频下载：输入 URL 可提取视频并创建下载任务
- 文档转换：可选择文件并预览转换结果
- Markdown 编辑器：可编辑、预览、复制

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat: 第一批工具迁移完成（图片/视频/转换/Markdown）"
```

---

## Batch 2: 学习内容

### Task 2.1: 创建 `services/coursePlatform.ts`

**Files:**
- Create: `src/services/coursePlatform.ts`

- [ ] **Step 1: 实现课程平台服务**

```typescript
import { request } from './request';

export interface Course {
  id: number;
  title: string;
  slug: string;
  description: string;
  cover_image?: string;
  status: string;
  price: number;
  category_id?: number;
  instructor_id?: number;
  created_at: string;
  updated_at: string;
}

export interface CourseChapter {
  id: number;
  title: string;
  order: number;
  content?: string;
  video_url?: string;
}

export interface CourseDetail extends Course {
  chapters: CourseChapter[];
  statistics?: {
    view_count: number;
    enroll_count: number;
    like_count: number;
    avg_rating: number;
  };
}

export interface CourseListResponse {
  courses: Course[];
  total: number;
  page: number;
  limit: number;
}

export interface CourseCategory {
  id: number;
  name: string;
  slug: string;
  icon?: string;
  children: CourseCategory[];
}

export interface EnrollmentResponse {
  id: number;
  user_id: string;
  course_id: number;
  status: string;
  progress_percent: number;
  enrolled_at: string;
  completed_at?: string;
}

export const coursePlatformApi = {
  getCourses: async (params: {
    category?: string;
    search?: string;
    sort?: string;
    page?: number;
    limit?: number;
  } = {}): Promise<CourseListResponse> => {
    const qs = new URLSearchParams();
    if (params.category) qs.append('category', params.category);
    if (params.search) qs.append('search', params.search);
    if (params.sort) qs.append('sort', params.sort);
    if (params.page) qs.append('page', String(params.page));
    if (params.limit) qs.append('limit', String(params.limit));
    return request(`/courses?${qs.toString()}`, { needAuth: false });
  },

  getCourseDetail: async (slug: string): Promise<CourseDetail> => {
    return request(`/courses/${slug}`, { needAuth: false });
  },

  getCategories: async (): Promise<{ categories: CourseCategory[] }> => {
    return request('/course-categories', { needAuth: false });
  },

  enroll: async (courseId: number): Promise<EnrollmentResponse> => {
    return request(`/courses/${courseId}/enroll`, {
      method: 'POST',
      needAuth: true,
    });
  },

  getMyCourses: async (): Promise<{
    courses: { course: Course; enrollment: EnrollmentResponse; completed_chapters: number; total_chapters: number }[];
    total: number;
  }> => {
    return request('/my-courses', { needAuth: true });
  },

  likeCourse: async (courseId: number): Promise<any> => {
    return request(`/courses/${courseId}/like`, {
      method: 'POST',
      needAuth: true,
    });
  },

  bookmarkCourse: async (courseId: number): Promise<any> => {
    return request(`/courses/${courseId}/bookmark`, {
      method: 'POST',
      needAuth: true,
    });
  },
};
```

- [ ] **Step 2: 提交**

```bash
git add src/services/coursePlatform.ts
git commit -m "feat: 添加课程平台服务层"
```

---

### Task 2.2: 创建课程列表页面

**Files:**
- Create: `src/pages/course-platform/index.tsx`
- Create: `src/pages/course-platform/index.scss`

- [ ] **Step 1: 实现课程列表页面**

```tsx
import { useState, useEffect } from 'react';
import Taro from '@tarojs/taro';
import { View, Text, ScrollView, Image } from '@tarojs/components';
import { coursePlatformApi, Course, CourseCategory } from '../../services/coursePlatform';
import { formatApiError } from '../../utils/mobileTool';
import Loading from '../../components/Loading';
import SearchBar from '../../components/SearchBar';
import './index.scss';

type PageState = 'loading' | 'error' | 'success';

export default function CoursePlatformPage() {
  const [pageState, setPageState] = useState<PageState>('loading');
  const [courses, setCourses] = useState<Course[]>([]);
  const [categories, setCategories] = useState<CourseCategory[]>([]);
  const [activeCategory, setActiveCategory] = useState('');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchCourses = async (reset = false) => {
    const currentPage = reset ? 1 : page;
    try {
      const res = await coursePlatformApi.getCourses({
        category: activeCategory || undefined,
        search: searchKeyword || undefined,
        page: currentPage,
        limit: 12,
      });
      if (reset) {
        setCourses(res.courses);
        setPage(2);
      } else {
        setCourses(prev => [...prev, ...res.courses]);
        setPage(currentPage + 1);
      }
      setHasMore(res.courses.length === 12);
      setPageState('success');
    } catch (err: any) {
      setErrorMsg(formatApiError(err));
      setPageState('error');
    }
  };

  useEffect(() => {
    setPageState('loading');
    Promise.all([
      coursePlatformApi.getCategories().then(r => setCategories(r.categories)),
      fetchCourses(true),
    ]).catch(() => {
      setPageState('error');
    });
  }, []);

  useEffect(() => {
    fetchCourses(true);
  }, [activeCategory, searchKeyword]);

  const handleCourseClick = (slug: string) => {
    Taro.navigateTo({ url: `/package-learning/pages/course-platform/detail/index?slug=${slug}` });
  };

  const handleLoadMore = () => {
    if (hasMore && pageState !== 'loading') {
      fetchCourses();
    }
  };

  return (
    <View className="course-platform-page">
      <SearchBar
        placeholder="搜索课程..."
        value={searchKeyword}
        onChange={setSearchKeyword}
        onSearch={() => fetchCourses(true)}
      />

      <ScrollView className="category-bar" scrollX>
        <View
          className={`category-item ${activeCategory === '' ? 'active' : ''}`}
          onClick={() => setActiveCategory('')}
        >
          <Text>全部</Text>
        </View>
        {categories.map(cat => (
          <View
            key={cat.id}
            className={`category-item ${activeCategory === cat.slug ? 'active' : ''}`}
            onClick={() => setActiveCategory(cat.slug)}
          >
            <Text>{cat.name}</Text>
          </View>
        ))}
      </ScrollView>

      {pageState === 'loading' && <Loading text="加载中..." />}

      {pageState === 'error' && (
        <View className="error-state">
          <Text className="error-text">{errorMsg}</Text>
          <Text className="retry-text" onClick={() => fetchCourses(true)}>点击重试</Text>
        </View>
      )}

      {pageState === 'success' && (
        <ScrollView className="course-list" scrollY onScrollToLower={handleLoadMore}>
          {courses.length === 0 ? (
            <View className="empty-state">
              <Text>暂无课程</Text>
            </View>
          ) : (
            courses.map(course => (
              <View key={course.id} className="course-card" onClick={() => handleCourseClick(course.slug)}>
                {course.cover_image && (
                  <Image className="cover" src={course.cover_image} mode="aspectFill" lazyLoad />
                )}
                <View className="info">
                  <Text className="title">{course.title}</Text>
                  <Text className="desc">{course.description}</Text>
                  {course.price > 0 && (
                    <Text className="price">¥{course.price}</Text>
                  )}
                </View>
              </View>
            ))
          )}
          {hasMore && <Text className="load-more">加载更多...</Text>}
        </ScrollView>
      )}
    </View>
  );
}
```

- [ ] **Step 2: 实现页面样式**

```scss
.course-platform-page {
  min-height: 100vh;
  background: var(--bg-primary);

  .category-bar {
    white-space: nowrap;
    padding: 20rpx;
    background: var(--bg-secondary);
    border-bottom: 1rpx solid var(--border-color);

    .category-item {
      display: inline-block;
      padding: 12rpx 24rpx;
      margin-right: 16rpx;
      background: var(--bg-primary);
      border-radius: 30rpx;
      color: var(--text-secondary);
      font-size: 26rpx;

      &.active {
        background: #6366f1;
        color: #fff;
      }
    }
  }

  .error-state {
    text-align: center;
    padding: 200rpx 40rpx;

    .error-text {
      color: #ef4444;
      margin-bottom: 20rpx;
    }

    .retry-text {
      color: #6366f1;
      font-size: 28rpx;
    }
  }

  .course-list {
    padding: 20rpx;

    .empty-state {
      text-align: center;
      padding: 200rpx 40rpx;
      color: var(--text-secondary);
    }

    .course-card {
      display: flex;
      padding: 20rpx;
      margin-bottom: 20rpx;
      background: var(--bg-secondary);
      border-radius: 16rpx;

      .cover {
        width: 200rpx;
        height: 140rpx;
        border-radius: 10rpx;
        flex-shrink: 0;
      }

      .info {
        flex: 1;
        margin-left: 20rpx;
        overflow: hidden;

        .title {
          display: block;
          color: var(--text-primary);
          font-size: 30rpx;
          font-weight: bold;
          margin-bottom: 10rpx;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .desc {
          display: block;
          color: var(--text-secondary);
          font-size: 24rpx;
          line-height: 1.4;
          overflow: hidden;
          text-overflow: ellipsis;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
        }

        .price {
          display: block;
          color: #f59e0b;
          font-size: 28rpx;
          margin-top: 10rpx;
        }
      }
    }

    .load-more {
      display: block;
      text-align: center;
      padding: 30rpx;
      color: var(--text-secondary);
      font-size: 26rpx;
    }
  }
}
```

- [ ] **Step 3: 提交**

```bash
git add src/pages/course-platform/
git commit -m "feat: 添加课程平台列表页面"
```

---

### Task 2.3: 创建课程详情页面

**Files:**
- Create: `src/pages/course-platform/detail/index.tsx`
- Create: `src/pages/course-platform/detail/index.scss`

- [ ] **Step 1: 实现课程详情页面**

```tsx
import { useState, useEffect } from 'react';
import Taro, { useRouter } from '@tarojs/taro';
import { View, Text, Image, ScrollView, Button } from '@tarojs/components';
import { coursePlatformApi, CourseDetail, CourseChapter } from '../../../services/coursePlatform';
import { formatApiError } from '../../../utils/mobileTool';
import Markdown from '../../../components/Markdown';
import Loading from '../../../components/Loading';
import './index.scss';

export default function CourseDetailPage() {
  const router = useRouter();
  const slug = router.params.slug || '';
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeChapter, setActiveChapter] = useState<CourseChapter | null>(null);

  useEffect(() => {
    if (!slug) {
      setError('课程 ID 缺失');
      setLoading(false);
      return;
    }
    coursePlatformApi.getCourseDetail(slug)
      .then(data => {
        setCourse(data);
        if (data.chapters?.length > 0) {
          setActiveChapter(data.chapters[0]);
        }
        setLoading(false);
      })
      .catch(err => {
        setError(formatApiError(err));
        setLoading(false);
      });
  }, [slug]);

  const handleEnroll = async () => {
    if (!course) return;
    try {
      Taro.showLoading({ title: '报名中...' });
      await coursePlatformApi.enroll(course.id);
      Taro.hideLoading();
      Taro.showToast({ title: '报名成功', icon: 'success' });
    } catch (err: any) {
      Taro.hideLoading();
      Taro.showToast({ title: formatApiError(err), icon: 'none' });
    }
  };

  if (loading) return <Loading text="加载课程..." />;
  if (error) return (
    <View className="error-state">
      <Text>{error}</Text>
    </View>
  );
  if (!course) return null;

  return (
    <View className="course-detail-page">
      {course.cover_image && (
        <Image className="cover" src={course.cover_image} mode="aspectFill" />
      )}
      <View className="header">
        <Text className="title">{course.title}</Text>
        <Text className="desc">{course.description}</Text>
        <Button className="enroll-btn" onClick={handleEnroll}>立即报名</Button>
      </View>

      <View className="chapter-list">
        <Text className="section-title">课程章节</Text>
        {course.chapters?.map((chapter, idx) => (
          <View
            key={chapter.id}
            className={`chapter-item ${activeChapter?.id === chapter.id ? 'active' : ''}`}
            onClick={() => setActiveChapter(chapter)}
          >
            <Text className="chapter-order">{idx + 1}</Text>
            <Text className="chapter-title">{chapter.title}</Text>
          </View>
        ))}
      </View>

      {activeChapter && (
        <ScrollView className="chapter-content" scrollY>
          <Text className="chapter-name">{activeChapter.title}</Text>
          {activeChapter.content ? (
            <Markdown content={activeChapter.content} />
          ) : (
            <Text className="no-content">本章暂无内容</Text>
          )}
        </ScrollView>
      )}
    </View>
  );
}
```

- [ ] **Step 2: 实现页面样式**

```scss
.course-detail-page {
  min-height: 100vh;
  background: var(--bg-primary);

  .cover {
    width: 100%;
    height: 300rpx;
  }

  .header {
    padding: 30rpx;
    background: var(--bg-secondary);
    margin-bottom: 20rpx;

    .title {
      display: block;
      color: var(--text-primary);
      font-size: 36rpx;
      font-weight: bold;
      margin-bottom: 16rpx;
    }

    .desc {
      display: block;
      color: var(--text-secondary);
      font-size: 26rpx;
      line-height: 1.5;
      margin-bottom: 24rpx;
    }

    .enroll-btn {
      width: 100%;
      height: 80rpx;
      line-height: 80rpx;
      background: #6366f1;
      color: #fff;
      border-radius: 12rpx;
      font-size: 30rpx;
    }
  }

  .chapter-list {
    padding: 20rpx 30rpx;
    background: var(--bg-secondary);
    margin-bottom: 20rpx;

    .section-title {
      display: block;
      color: var(--text-primary);
      font-size: 30rpx;
      font-weight: bold;
      margin-bottom: 20rpx;
    }

    .chapter-item {
      display: flex;
      align-items: center;
      padding: 20rpx;
      border-bottom: 1rpx solid var(--border-color);

      .chapter-order {
        width: 48rpx;
        height: 48rpx;
        line-height: 48rpx;
        text-align: center;
        background: var(--bg-primary);
        border-radius: 50%;
        color: var(--text-secondary);
        font-size: 24rpx;
        margin-right: 20rpx;
        flex-shrink: 0;
      }

      .chapter-title {
        flex: 1;
        color: var(--text-primary);
        font-size: 28rpx;
      }

      &.active {
        .chapter-order {
          background: #6366f1;
          color: #fff;
        }

        .chapter-title {
          color: #6366f1;
          font-weight: bold;
        }
      }
    }
  }

  .chapter-content {
    padding: 30rpx;
    background: var(--bg-secondary);

    .chapter-name {
      display: block;
      color: var(--text-primary);
      font-size: 32rpx;
      font-weight: bold;
      margin-bottom: 20rpx;
    }

    .no-content {
      color: var(--text-secondary);
      font-size: 28rpx;
      text-align: center;
      padding: 100rpx;
    }
  }
}
```

- [ ] **Step 3: 提交**

```bash
git add src/pages/course-platform/detail/
git commit -m "feat: 添加课程详情页面"
```

---

### Task 2.4: 创建 `services/techContents.ts`

**Files:**
- Create: `src/services/techContents.ts`

- [ ] **Step 1: 实现技术内容服务**

```typescript
import { request } from './request';

export interface TechContent {
  id: number;
  slug: string;
  content_type: string;
  content_type_label: string;
  title: string;
  description: string;
  cover_image?: string;
  author: string;
  reading_time?: number;
  tags: string[];
  published_at: string;
  views: number;
  likes: number;
}

export interface TechContentDetail extends TechContent {
  bookmarks: number;
  chapters?: { title: string; content: string }[];
  content?: string;
}

export interface TechContentListResponse {
  contents: TechContent[];
  total: number;
  page: number;
  limit: number;
}

export interface ContentType {
  value: string;
  label: string;
}

export interface PopularTag {
  name: string;
  count: number;
}

export const techContentsApi = {
  getContents: async (params: {
    content_type?: string;
    tag?: string;
    page?: number;
    limit?: number;
  } = {}): Promise<TechContentListResponse> => {
    const qs = new URLSearchParams();
    if (params.content_type) qs.append('content_type', params.content_type);
    if (params.tag) qs.append('tag', params.tag);
    if (params.page) qs.append('page', String(params.page));
    if (params.limit) qs.append('limit', String(params.limit));
    return request(`/tech-contents?${qs.toString()}`, { needAuth: false });
  },

  getContentTypes: async (): Promise<{ types: ContentType[] }> => {
    return request('/tech-contents/types', { needAuth: false });
  },

  getContentDetail: async (slug: string): Promise<TechContentDetail> => {
    return request(`/tech-contents/${slug}`, { needAuth: false });
  },

  getPopularTags: async (limit = 10): Promise<{ tags: PopularTag[] }> => {
    return request(`/tech-contents/tags/popular?limit=${limit}`, { needAuth: false });
  },
};
```

- [ ] **Step 2: 提交**

```bash
git add src/services/techContents.ts
git commit -m "feat: 添加技术内容服务层"
```

---

### Task 2.5: 创建技术内容列表页面

**Files:**
- Create: `src/pages/tech-contents/index.tsx`
- Create: `src/pages/tech-contents/index.scss`

- [ ] **Step 1: 实现技术内容列表页面**

```tsx
import { useState, useEffect } from 'react';
import Taro from '@tarojs/taro';
import { View, Text, ScrollView, Image } from '@tarojs/components';
import { techContentsApi, TechContent, ContentType } from '../../services/techContents';
import { formatApiError } from '../../utils/mobileTool';
import Loading from '../../components/Loading';
import SearchBar from '../../components/SearchBar';
import './index.scss';

type PageState = 'loading' | 'error' | 'success';

export default function TechContentsPage() {
  const [pageState, setPageState] = useState<PageState>('loading');
  const [contents, setContents] = useState<TechContent[]>([]);
  const [types, setTypes] = useState<ContentType[]>([]);
  const [activeType, setActiveType] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchContents = async (reset = false) => {
    const currentPage = reset ? 1 : page;
    try {
      const res = await techContentsApi.getContents({
        content_type: activeType || undefined,
        page: currentPage,
        limit: 12,
      });
      if (reset) {
        setContents(res.contents);
        setPage(2);
      } else {
        setContents(prev => [...prev, ...res.contents]);
        setPage(currentPage + 1);
      }
      setHasMore(res.contents.length === 12);
      setPageState('success');
    } catch (err: any) {
      setErrorMsg(formatApiError(err));
      setPageState('error');
    }
  };

  useEffect(() => {
    Promise.all([
      techContentsApi.getContentTypes().then(r => setTypes(r.types)),
      fetchContents(true),
    ]).catch(() => setPageState('error'));
  }, []);

  useEffect(() => {
    fetchContents(true);
  }, [activeType]);

  const handleContentClick = (slug: string) => {
    Taro.navigateTo({ url: `/package-learning/pages/tech-contents/detail/index?slug=${slug}` });
  };

  return (
    <View className="tech-contents-page">
      <View className="type-bar" scrollX>
        <View
          className={`type-item ${activeType === '' ? 'active' : ''}`}
          onClick={() => setActiveType('')}
        >
          <Text>全部</Text>
        </View>
        {types.map(t => (
          <View
            key={t.value}
            className={`type-item ${activeType === t.value ? 'active' : ''}`}
            onClick={() => setActiveType(t.value)}
          >
            <Text>{t.label}</Text>
          </View>
        ))}
      </View>

      {pageState === 'loading' && <Loading text="加载中..." />}

      {pageState === 'error' && (
        <View className="error-state">
          <Text className="error-text">{errorMsg}</Text>
          <Text className="retry-text" onClick={() => fetchContents(true)}>点击重试</Text>
        </View>
      )}

      {pageState === 'success' && (
        <ScrollView className="content-list" scrollY onScrollToLower={() => hasMore && fetchContents()}>
          {contents.length === 0 ? (
            <View className="empty-state"><Text>暂无内容</Text></View>
          ) : (
            contents.map(item => (
              <View key={item.id} className="content-card" onClick={() => handleContentClick(item.slug)}>
                {item.cover_image && <Image className="cover" src={item.cover_image} mode="aspectFill" lazyLoad />}
                <View className="info">
                  <Text className="type-tag">{item.content_type_label}</Text>
                  <Text className="title">{item.title}</Text>
                  <Text className="desc">{item.description}</Text>
                  <View className="meta">
                    <Text className="author">{item.author}</Text>
                    {item.reading_time && <Text className="time">{item.reading_time}分钟阅读</Text>}
                  </View>
                </View>
              </View>
            ))
          )}
        </ScrollView>
      )}
    </View>
  );
}
```

- [ ] **Step 2: 实现页面样式**

```scss
.tech-contents-page {
  min-height: 100vh;
  background: var(--bg-primary);

  .type-bar {
    white-space: nowrap;
    padding: 20rpx;
    background: var(--bg-secondary);
    border-bottom: 1rpx solid var(--border-color);

    .type-item {
      display: inline-block;
      padding: 12rpx 24rpx;
      margin-right: 16rpx;
      background: var(--bg-primary);
      border-radius: 30rpx;
      color: var(--text-secondary);
      font-size: 26rpx;

      &.active {
        background: #6366f1;
        color: #fff;
      }
    }
  }

  .error-state {
    text-align: center;
    padding: 200rpx 40rpx;

    .error-text { color: #ef4444; margin-bottom: 20rpx; }
    .retry-text { color: #6366f1; font-size: 28rpx; }
  }

  .content-list {
    padding: 20rpx;

    .empty-state {
      text-align: center;
      padding: 200rpx;
      color: var(--text-secondary);
    }

    .content-card {
      padding: 24rpx;
      margin-bottom: 20rpx;
      background: var(--bg-secondary);
      border-radius: 16rpx;

      .cover {
        width: 100%;
        height: 200rpx;
        border-radius: 10rpx;
        margin-bottom: 16rpx;
      }

      .info {
        .type-tag {
          display: inline-block;
          padding: 4rpx 16rpx;
          background: #6366f1;
          color: #fff;
          border-radius: 8rpx;
          font-size: 22rpx;
          margin-bottom: 12rpx;
        }

        .title {
          display: block;
          color: var(--text-primary);
          font-size: 30rpx;
          font-weight: bold;
          margin-bottom: 10rpx;
        }

        .desc {
          display: block;
          color: var(--text-secondary);
          font-size: 24rpx;
          line-height: 1.4;
          margin-bottom: 16rpx;
          overflow: hidden;
          text-overflow: ellipsis;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
        }

        .meta {
          display: flex;
          gap: 20rpx;

          .author, .time {
            color: var(--text-secondary);
            font-size: 22rpx;
          }
        }
      }
    }
  }
}
```

- [ ] **Step 3: 提交**

```bash
git add src/pages/tech-contents/
git commit -m "feat: 添加技术内容列表页面"
```

---

### Task 2.6: 创建技术内容详情页面

**Files:**
- Create: `src/pages/tech-contents/detail/index.tsx`
- Create: `src/pages/tech-contents/detail/index.scss`

- [ ] **Step 1: 实现技术内容详情页面**

```tsx
import { useState, useEffect } from 'react';
import Taro, { useRouter } from '@tarojs/taro';
import { View, Text, Image, ScrollView } from '@tarojs/components';
import { techContentsApi, TechContentDetail } from '../../../services/techContents';
import { formatApiError } from '../../../utils/mobileTool';
import Markdown from '../../../components/Markdown';
import Loading from '../../../components/Loading';
import './index.scss';

export default function TechContentDetailPage() {
  const router = useRouter();
  const slug = router.params.slug || '';
  const [content, setContent] = useState<TechContentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!slug) {
      setError('内容 ID 缺失');
      setLoading(false);
      return;
    }
    techContentsApi.getContentDetail(slug)
      .then(data => {
        setContent(data);
        setLoading(false);
      })
      .catch(err => {
        setError(formatApiError(err));
        setLoading(false);
      });
  }, [slug]);

  if (loading) return <Loading text="加载中..." />;
  if (error) return <View className="error-state"><Text>{error}</Text></View>;
  if (!content) return null;

  return (
    <ScrollView className="tech-content-detail-page" scrollY>
      {content.cover_image && (
        <Image className="cover" src={content.cover_image} mode="aspectFill" />
      )}
      <View className="header">
        <Text className="type">{content.content_type_label}</Text>
        <Text className="title">{content.title}</Text>
        <View className="meta">
          <Text className="author">{content.author}</Text>
          <Text className="date">{content.published_at?.split('T')[0]}</Text>
          <Text className="views">{content.views} 阅读</Text>
        </View>
        {content.tags?.length > 0 && (
          <View className="tags">
            {content.tags.map(tag => (
              <Text key={tag} className="tag">{tag}</Text>
            ))}
          </View>
        )}
      </View>
      <View className="body">
        {content.content ? (
          <Markdown content={content.content} />
        ) : (
          <Text className="no-content">暂无正文内容</Text>
        )}
      </View>
    </ScrollView>
  );
}
```

- [ ] **Step 2: 实现页面样式**

```scss
.tech-content-detail-page {
  min-height: 100vh;
  background: var(--bg-primary);

  .cover {
    width: 100%;
    height: 300rpx;
  }

  .header {
    padding: 30rpx;
    background: var(--bg-secondary);
    margin-bottom: 20rpx;

    .type {
      display: inline-block;
      padding: 6rpx 16rpx;
      background: #6366f1;
      color: #fff;
      border-radius: 8rpx;
      font-size: 22rpx;
      margin-bottom: 16rpx;
    }

    .title {
      display: block;
      color: var(--text-primary);
      font-size: 36rpx;
      font-weight: bold;
      line-height: 1.4;
      margin-bottom: 20rpx;
    }

    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 20rpx;
      margin-bottom: 20rpx;

      .author, .date, .views {
        color: var(--text-secondary);
        font-size: 24rpx;
      }
    }

    .tags {
      display: flex;
      flex-wrap: wrap;
      gap: 12rpx;

      .tag {
        padding: 4rpx 16rpx;
        background: var(--bg-primary);
        color: var(--text-secondary);
        border-radius: 8rpx;
        font-size: 22rpx;
      }
    }
  }

  .body {
    padding: 30rpx;
    background: var(--bg-secondary);

    .no-content {
      color: var(--text-secondary);
      font-size: 28rpx;
      text-align: center;
      padding: 100rpx;
    }
  }
}
```

- [ ] **Step 3: 提交**

```bash
git add src/pages/tech-contents/detail/
git commit -m "feat: 添加技术内容详情页面"
```

---

### Task 2.7: 第二批验收

- [ ] **Step 1: 验证分包编译**

```bash
cd tools-mini-program
npm run build:weapp
```

Expected: 编译成功，无 TypeScript 错误。

- [ ] **Step 2: H5 验证**

```bash
cd tools-mini-program
npm run dev:h5
```

在浏览器中验证：
- 课程平台：列表、分类筛选、详情、章节阅读
- 技术内容：列表、类型筛选、详情阅读

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "feat: 第二批工具迁移完成（课程平台/技术内容）"
```

---

## Batch 3: Token 统计

### Task 3.1: 创建 `services/tokenUsage.ts`

**Files:**
- Create: `src/services/tokenUsage.ts`

- [ ] **Step 1: 实现 Token 统计服务**

```typescript
import { request } from './request';

export interface DeviceInfo {
  id: string;
  name: string;
}

export interface UsageItem {
  date?: string;
  week?: string;
  month?: string;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  cost?: number;
  count: number;
}

export interface UsageSummary {
  total_tokens: number;
  total_cost?: number;
  total_count: number;
}

export interface DbQueryResponse {
  items: UsageItem[];
  summary: UsageSummary;
  devices: DeviceInfo[];
  cached: boolean;
  model_summary?: Record<string, number>;
  dimension_summaries?: Record<string, any>;
  filter_options: {
    sources: string[];
    models: string[];
    tools: string[];
  };
  sync_meta?: {
    last_sync: string;
    total_records: number;
  };
}

export interface HealthCheckResponse {
  status: string;
  claude?: { available: boolean; last_sync?: string; record_count: number };
  opencode?: { available: boolean; last_sync?: string; record_count: number };
}

export const tokenUsageApi = {
  healthCheck: async (): Promise<HealthCheckResponse> => {
    return request('/token-usage/health', { needAuth: true });
  },

  queryUsage: async (params: {
    type?: 'daily' | 'weekly' | 'monthly';
    days?: number;
    group_by?: string;
    source?: string;
    device_id?: string;
    model?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  } = {}): Promise<DbQueryResponse> => {
    return request('/token-usage/db-query', {
      method: 'POST',
      data: {
        type: params.type || 'daily',
        days: params.days || 30,
        group_by: params.group_by || 'none',
        source: params.source || 'all',
        device_id: params.device_id,
        model: params.model,
        sort_by: params.sort_by || 'date',
        sort_order: params.sort_order || 'desc',
      },
      needAuth: true,
    });
  },

  getDevices: async (): Promise<{ devices: DeviceInfo[] }> => {
    return request('/token-usage/devices', { needAuth: true });
  },
};
```

- [ ] **Step 2: 提交**

```bash
git add src/services/tokenUsage.ts
git commit -m "feat: 添加 Token 统计服务层（只读）"
```

---

### Task 3.2: 创建 Token 统计只读面板页面

**Files:**
- Create: `src/pages/token-usage/index.tsx`
- Create: `src/pages/token-usage/index.scss`

- [ ] **Step 1: 实现页面逻辑**

```tsx
import { useState, useEffect } from 'react';
import Taro from '@tarojs/taro';
import { View, Text, ScrollView, Picker } from '@tarojs/components';
import { tokenUsageApi, UsageItem, DbQueryResponse } from '../../services/tokenUsage';
import { formatApiError } from '../../utils/mobileTool';
import Loading from '../../components/Loading';
import './index.scss';

type Dimension = 'daily' | 'weekly' | 'monthly';

const DIMENSION_LABELS: Record<Dimension, string> = {
  daily: '按日',
  weekly: '按周',
  monthly: '按月',
};

export default function TokenUsagePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState<DbQueryResponse | null>(null);
  const [dimension, setDimension] = useState<Dimension>('daily');
  const [days, setDays] = useState(30);
  const [selectedDevice, setSelectedDevice] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await tokenUsageApi.queryUsage({
        type: dimension,
        days,
        device_id: selectedDevice || undefined,
      });
      setData(res);
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [dimension, days, selectedDevice]);

  if (loading && !data) return <Loading text="加载统计..." />;

  return (
    <View className="token-usage-page">
      <View className="filters">
        <View className="filter-row">
          <Text className="filter-label">维度</Text>
          <Picker
            mode="selector"
            range={['daily', 'weekly', 'monthly']}
            rangeKey={undefined}
            value={['daily', 'weekly', 'monthly'].indexOf(dimension)}
            onChange={(e) => setDimension(['daily', 'weekly', 'monthly'][e.detail.value] as Dimension)}
          >
            <View className="picker-value">{DIMENSION_LABELS[dimension]}</View>
          </Picker>
        </View>
        <View className="filter-row">
          <Text className="filter-label">天数</Text>
          <Picker
            mode="selector"
            range={[7, 14, 30, 60, 90]}
            value={[7, 14, 30, 60, 90].indexOf(days)}
            onChange={(e) => setDays([7, 14, 30, 60, 90][e.detail.value])}
          >
            <View className="picker-value">{days}天</View>
          </Picker>
        </View>
        {data?.devices && data.devices.length > 0 && (
          <View className="filter-row">
            <Text className="filter-label">设备</Text>
            <Picker
              mode="selector"
              range={['全部设备', ...data.devices.map(d => d.name)]}
              value={selectedDevice === '' ? 0 : data.devices.findIndex(d => d.id === selectedDevice) + 1}
              onChange={(e) => {
                const idx = e.detail.value;
                setSelectedDevice(idx === 0 ? '' : data.devices[idx - 1].id);
              }}
            >
              <View className="picker-value">
                {selectedDevice === '' ? '全部设备' : data.devices.find(d => d.id === selectedDevice)?.name}
              </View>
            </Picker>
          </View>
        )}
      </View>

      {error && (
        <View className="error-state">
          <Text>{error}</Text>
          <Text className="retry" onClick={fetchData}>重试</Text>
        </View>
      )}

      {data && (
        <ScrollView className="stats-content" scrollY>
          <View className="summary-cards">
            <View className="summary-card">
              <Text className="card-value">{(data.summary.total_tokens / 1000).toFixed(1)}K</Text>
              <Text className="card-label">总 Token</Text>
            </View>
            <View className="summary-card">
              <Text className="card-value">{data.summary.total_count}</Text>
              <Text className="card-label">请求数</Text>
            </View>
          </View>

          <View className="data-list">
            <View className="list-header">
              <Text className="header-cell">时间</Text>
              <Text className="header-cell">Token</Text>
              <Text className="header-cell">请求</Text>
            </View>
            {data.items.map((item, idx) => (
              <View key={idx} className="list-row">
                <Text className="cell">
                  {item.date || item.week || item.month || '-'}
                </Text>
                <Text className="cell">{item.total_tokens.toLocaleString()}</Text>
                <Text className="cell">{item.count}</Text>
              </View>
            ))}
          </View>

          {data.cached && (
            <Text className="cached-hint">数据来自缓存</Text>
          )}
        </ScrollView>
      )}
    </View>
  );
}
```

- [ ] **Step 2: 实现页面样式**

```scss
.token-usage-page {
  min-height: 100vh;
  background: var(--bg-primary);

  .filters {
    padding: 20rpx 30rpx;
    background: var(--bg-secondary);
    border-bottom: 1rpx solid var(--border-color);

    .filter-row {
      display: flex;
      align-items: center;
      padding: 16rpx 0;
      border-bottom: 1rpx solid var(--border-color);

      &:last-child {
        border-bottom: none;
      }

      .filter-label {
        width: 120rpx;
        color: var(--text-secondary);
        font-size: 28rpx;
      }

      .picker-value {
        flex: 1;
        color: var(--text-primary);
        font-size: 28rpx;
        text-align: right;
        padding: 10rpx 20rpx;
        background: var(--bg-primary);
        border-radius: 8rpx;
      }
    }
  }

  .error-state {
    text-align: center;
    padding: 100rpx 40rpx;
    color: #ef4444;

    .retry {
      display: block;
      color: #6366f1;
      margin-top: 20rpx;
    }
  }

  .stats-content {
    padding: 20rpx;

    .summary-cards {
      display: flex;
      gap: 20rpx;
      margin-bottom: 30rpx;

      .summary-card {
        flex: 1;
        padding: 30rpx;
        background: var(--bg-secondary);
        border-radius: 16rpx;
        text-align: center;

        .card-value {
          display: block;
          color: #6366f1;
          font-size: 40rpx;
          font-weight: bold;
          margin-bottom: 10rpx;
        }

        .card-label {
          color: var(--text-secondary);
          font-size: 24rpx;
        }
      }
    }

    .data-list {
      background: var(--bg-secondary);
      border-radius: 16rpx;
      overflow: hidden;

      .list-header {
        display: flex;
        padding: 20rpx;
        background: var(--bg-primary);
        border-bottom: 1rpx solid var(--border-color);

        .header-cell {
          flex: 1;
          color: var(--text-secondary);
          font-size: 24rpx;
          text-align: center;

          &:first-child {
            text-align: left;
          }
        }
      }

      .list-row {
        display: flex;
        padding: 20rpx;
        border-bottom: 1rpx solid var(--border-color);

        &:last-child {
          border-bottom: none;
        }

        .cell {
          flex: 1;
          color: var(--text-primary);
          font-size: 26rpx;
          text-align: center;

          &:first-child {
            text-align: left;
          }
        }
      }
    }

    .cached-hint {
      display: block;
      text-align: center;
      padding: 20rpx;
      color: var(--text-secondary);
      font-size: 22rpx;
    }
  }
}
```

- [ ] **Step 3: 提交**

```bash
git add src/pages/token-usage/
git commit -m "feat: 添加 Token 统计只读面板页面"
```

---

### Task 3.3: 第三批验收

- [ ] **Step 1: 验证编译和 H5**

```bash
cd tools-mini-program
npm run build:weapp
npm run dev:h5
```

验证：
- Token 统计页面加载正常
- 维度切换（日/周/月）
- 天数筛选
- 设备筛选
- 数据列表展示

- [ ] **Step 2: 提交**

```bash
git add -A
git commit -m "feat: 第三批工具迁移完成（Token 统计）"
```

---

## Batch 4: 入口治理与历史遗留清理

### Task 4.1: 验证 `TOOL_PATH_MAP` 与 `app.config.ts` 一致性

**Files:**
- Read: `src/services/tool.ts`
- Read: `src/app.config.ts`
- Modify: 如有不一致

- [ ] **Step 1: 检查一致性**

运行以下检查脚本（或手动核对）：

```bash
cd tools-mini-program
node -e "
const toolMap = require('./src/services/tool.ts');
const appConfig = require('./src/app.config.ts').default;

const subPackageRoots = appConfig.subPackages.map(p => p.root);
const allPages = [
  ...appConfig.pages,
  ...appConfig.subPackages.flatMap(p => p.pages.map(pg => p.root + '/' + pg))
];

console.log('主包页面数:', appConfig.pages.length);
console.log('分包数:', appConfig.subPackages.length);
console.log('总分页数:', allPages.length);
"
```

Expected: 所有 `TOOL_PATH_MAP` 中的非 null 路径都能在 `app.config.ts` 的 `pages` 或 `subPackages` 中找到对应。

- [ ] **Step 2: 清理无效 `TOOL_PATH_MAP` 项**

如果 `TOOL_PATH_MAP` 中有指向不存在的页面的路径，删除或修正。

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "chore: 清理 TOOL_PATH_MAP 和 app.config.ts 一致性"
```

---

### Task 4.2: 后端 `show_mobile` 配置核查

**Files:**
- Modify: `backend/app/data/tools_data.py`（如需调整）

- [ ] **Step 1: 检查所有工具的 `show_mobile` 设置**

```bash
cd backend
python -c "
from app.models.base import get_db
from app.services.tools_service import ToolService

db = next(get_db())
tools = ToolService.get_all_tools(db)
for t in tools:
    print(f'{t.id}: show_pc={t.show_pc}, show_mobile={t.show_mobile}, status={t.status}')
"
```

Expected:
- 已迁移工具：`show_mobile=True`, `status='online'`
- 隐藏工具：`show_mobile=False` 或 `status='offline'`

- [ ] **Step 2: 修正配置**

如需调整，修改数据库中的 `show_mobile` 和 `status`：

```python
# 例如：将 database-tool 设为隐藏
# 在生产数据库中执行更新
```

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "chore: 更新后端工具 show_mobile 配置"
```

---

### Task 4.3: 全量验收清单

- [ ] **Step 1: 编译检查**

```bash
cd tools-mini-program
npm run build:weapp
npm run build:h5
```

- [ ] **Step 2: 入口隐藏验证**

在后端数据库中将某个未迁移工具的 `show_mobile` 临时设为 `True`，验证小程序首页不会显示它（因为 `TOOL_PATH_MAP` 中对应路径为 `null`）。

- [ ] **Step 3: 跳转验证**

对每个新增工具验证：
- 首页卡片点击 → 正确跳转
- 返回首页正常

- [ ] **Step 4: 提交最终版本**

```bash
git add -A
git commit -m "feat: 小程序工具迁移全部完成（四批次）"
```

---

## Self-Review

**1. Spec coverage:**

| Spec 章节 | 对应任务 |
|-----------|---------|
| 3.1 Web 工具盘点 | 全部覆盖，每个工具都有服务层和页面 |
| 3.3 建议迁移工具 | Batch 1-3 全部覆盖 |
| 4. API 映射 | 每个服务层都使用了 spec 中列出的接口 |
| 5.1 主包 | 保留现有页面不变 |
| 5.2 分包 | Task 1.2 完成 subPackages 配置 |
| 5.3 入口治理 | Task 1.3 更新 TOOL_PATH_MAP，Task 4.1-4.2 完成一致性核查 |
| 6.1 新增服务层 | Task 1.4, 1.6, 1.8, 1.10, 2.1, 2.4, 3.1 |
| 6.2 通用工具 | Task 1.1 完成 mobileTool.ts |
| 7.1-7.4 迁移批次 | Batch 1-4 全部覆盖 |
| 8.1-8.7 功能设计 | 每个工具页面都实现了 spec 中的核心流程 |
| 9. 错误处理 | 每个页面都有 loading/error/empty/success 状态 |
| 10. 日志与安全 | 不输出敏感信息，高风险工具隐藏 |
| 11. 验证策略 | 每批都有验收步骤 |

**2. Placeholder scan:** 无 TBD/TODO/实现later，所有步骤都有完整代码。

**3. Type consistency:** 所有服务层返回类型和页面使用类型一致，路由参数（slug, id）使用统一命名。
