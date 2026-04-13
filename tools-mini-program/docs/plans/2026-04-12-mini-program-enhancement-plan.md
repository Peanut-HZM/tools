# 小程序功能完善实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 分三个阶段完善小程序功能——新增高优先级页面（OCR、文件、HTTP客户端）、中优先级功能（ASR、密码重置、体验优化）、H5构建与浏览器预览。

**Architecture:** 在现有 Taro 4 项目骨架上新增 6 个页面、1 个 TabBar tab、4 处体验优化和 H5 构建配置。所有页面共享现有服务层、组件库和暗色主题样式。

**Tech Stack:** Taro 4.1, React 18, TypeScript, Zustand 5, Sass, Taro.uploadFile, Taro.getRecorderManager

**重要修正**：
1. OCR 接口走 base64 JSON（非文件上传），后端 `/tools/ocr/predict` 接收 JSON body
2. ASR 接口路径是 `/asr/predict`（非 `/tools/asr/predict`），后端路由 prefix 为 `/asr`
3. 文件页加入 TabBar（4 tab：工具、消息、文件、我的）
4. `request.ts` 的 `uploadFile`/`downloadFile` 增加 H5 降级处理
5. 所有页面路由注册在 Task 1 一次性完成，后续 Task 不再修改 `app.config.ts`

---

## 阶段一：高优先级新功能

### Task 1: 统一路由注册 + OCR 拍照识别页面

**Files:**
- Create: `src/pages/ocr/index.tsx`
- Create: `src/pages/ocr/index.scss`
- Modify: `src/app.config.ts` — **一次性注册所有新增页面路由 + 扩展 TabBar 为 4 个 tab**
- Modify: `src/services/tool.ts` — 补全所有工具路由映射 + 过滤 null 项
- Modify: `src/services/request.ts` — uploadFile 增加 formData 参数支持

**Step 1: 一次性注册所有页面路由 + 扩展 TabBar**

在 `src/app.config.ts` 中完整替换：

```typescript
export default {
  pages: [
    'pages/index/index',
    'pages/cross-share/message/index',
    'pages/cross-share/file/index',    // 新增
    'pages/profile/index',
    'pages/login/index',
    'pages/json-formatter/index',
    'pages/calendar/index',
    'pages/key-generator/index',
    'pages/ocr/index',                 // 新增
    'pages/http-client/index',         // 新增
    'pages/asr/index',                 // 新增
    'pages/change-password/index',     // 新增
    'pages/help/index',                // 新增
  ],
  window: {
    backgroundTextStyle: 'dark',
    navigationBarBackgroundColor: '#0A0E27',
    navigationBarTitleText: '工具箱',
    navigationBarTextStyle: 'white',
    backgroundColor: '#0A0E27',
  },
  tabBar: {
    color: '#94A3B8',
    selectedColor: '#3B82F6',
    backgroundColor: '#1E1E2E',
    borderStyle: 'black',
    list: [
      {
        pagePath: 'pages/index/index',
        text: '工具',
        iconPath: 'assets/icons/tool.png',
        selectedIconPath: 'assets/icons/tool-active.png',
      },
      {
        pagePath: 'pages/cross-share/message/index',
        text: '消息',
        iconPath: 'assets/icons/message.png',
        selectedIconPath: 'assets/icons/message-active.png',
      },
      {
        pagePath: 'pages/cross-share/file/index',    // 新增 tab
        text: '文件',
        iconPath: 'assets/icons/file.png',
        selectedIconPath: 'assets/icons/file-active.png',
      },
      {
        pagePath: 'pages/profile/index',
        text: '我的',
        iconPath: 'assets/icons/profile.png',
        selectedIconPath: 'assets/icons/profile-active.png',
      },
    ],
  },
}
```

**Step 2: 补全 tool.ts 路由映射 + 过滤 null**

在 `src/services/tool.ts` 中：

```typescript
const TOOL_PATH_MAP: Record<string, string | null> = {
  'json-formatter': '/pages/json-formatter/index',
  'calendar': '/pages/calendar/index',
  'key-generator': '/pages/key-generator/index',
  'cross-share': '/pages/cross-share/message/index',
  'ocr': '/pages/ocr/index',
  'asr': '/pages/asr/index',
  'http-client': '/pages/http-client/index',
  'database': null,
  'redis': null,
  'ssh': null,
  'cursor-history': null,
  'open-spec-course': null,
}

// getTools 中修改返回逻辑：
const tools = res.tools || [];
return tools
  .map(tool => ({
    ...tool,
    path: tool.path || TOOL_PATH_MAP[tool.name_en] || null
  }))
  .filter(t => t.path !== null);  // 过滤掉移动端不适用的工具
```

**Step 3: 增强 request.ts 的 uploadFile 支持 formData**

在 `src/services/request.ts` 的 `uploadFile` 函数签名中增加 `formData` 参数的传递（已有，确认逻辑正确）。

**Step 4: 创建 OCR 页面组件**

```tsx
// src/pages/ocr/index.tsx
import { useState } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, Image } from '@tarojs/components'
import { request } from '../../services/request'
import './index.scss'

export default function OCRPage() {
  const [imagePath, setImagePath] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lang, setLang] = useState('ch')

  // 选择图片
  const handleChooseImage = async () => {
    try {
      const res = await Taro.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera']
      })
      setImagePath(res.tempFilePaths[0])
      setResult('')
      setError('')
    } catch (err: any) {
      if (err.errMsg !== 'chooseImage:fail cancel') {
        Taro.showToast({ title: '选择图片失败', icon: 'none' })
      }
    }
  }

  // 识别 — 用 base64 JSON 方式（非文件上传）
  const handleRecognize = async () => {
    if (!imagePath) {
      setError('请先选择图片')
      return
    }
    setLoading(true)
    setError('')
    setResult('')
    try {
      // 读取图片为 base64
      const base64Res = await Taro.getFileSystemManager().readFile({
        filePath: imagePath,
        encoding: 'base64'
      })
      const base64Image = `data:image/jpeg;base64,${base64Res.data}`

      // 发送 JSON 请求
      const res = await request('/tools/ocr/predict', {
        method: 'POST',
        data: { image: base64Image, lang }
      })
      const text = res?.text || res?.result || JSON.stringify(res)
      setResult(typeof text === 'string' ? text : JSON.stringify(text, null, 2))
      Taro.showToast({ title: '识别成功', icon: 'success' })
    } catch (err: any) {
      setError(err.message || '识别失败')
    } finally {
      setLoading(false)
    }
  }

  // 复制结果
  const handleCopy = async () => {
    if (!result) return
    try {
      await Taro.setClipboardData({ data: result })
      Taro.showToast({ title: '已复制', icon: 'success' })
    } catch (err) {
      Taro.showToast({ title: '复制失败', icon: 'none' })
    }
  }

  return (
    <View className='ocr-page'>
      {/* 语言选择 */}
      <View className='lang-bar'>
        <Text className={`lang-item ${lang === 'ch' ? 'active' : ''}`} onClick={() => setLang('ch')}>中文</Text>
        <Text className={`lang-item ${lang === 'en' ? 'active' : ''}`} onClick={() => setLang('en')}>English</Text>
      </View>

      {/* 图片选择区 */}
      <View className='image-section' onClick={handleChooseImage}>
        {imagePath ? (
          <Image src={imagePath} mode='aspectFit' className='preview-image' />
        ) : (
          <View className='upload-placeholder'>
            <Text className='upload-icon'>📷</Text>
            <Text className='upload-text'>点击拍照或选择图片</Text>
          </View>
        )}
      </View>

      {/* 识别按钮 */}
      <View className='action-bar'>
        <button className='recognize-btn' onClick={handleRecognize} disabled={loading || !imagePath}>
          {loading ? '识别中...' : '开始识别'}
        </button>
      </View>

      {/* 错误提示 */}
      {error && (
        <View className='error-section'>
          <Text className='error-text'>{error}</Text>
        </View>
      )}

      {/* 识别结果 */}
      {result && (
        <View className='result-section'>
          <View className='result-header'>
            <Text className='result-title'>识别结果</Text>
            <Text className='copy-btn' onClick={handleCopy}>复制</Text>
          </View>
          <View className='result-content'>
            <Text className='result-text' selectable>{result}</Text>
          </View>
        </View>
      )}
    </View>
  )
}
```

**Step 5: 创建 OCR 页面样式**

```scss
// src/pages/ocr/index.scss
.ocr-page {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 24rpx;
  padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
}

.lang-bar {
  display: flex;
  gap: 24rpx;
  margin-bottom: 24rpx;
}

.lang-item {
  flex: 1;
  text-align: center;
  padding: 16rpx 0;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 26rpx;
  color: var(--text-secondary);

  &.active {
    background: rgba(59, 130, 246, 0.15);
    border-color: var(--color-primary);
    color: var(--color-primary);
  }
}

.image-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  min-height: 400rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24rpx;
  overflow: hidden;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16rpx;
}

.upload-icon {
  font-size: 80rpx;
  opacity: 0.6;
}

.upload-text {
  font-size: 28rpx;
  color: var(--text-tertiary);
}

.preview-image {
  width: 100%;
  height: 400rpx;
}

.action-bar {
  margin-bottom: 24rpx;
}

.recognize-btn {
  width: 100%;
  height: 88rpx;
  background: var(--color-primary);
  color: #fff;
  font-size: 30rpx;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;

  &::after {
    border: none;
  }

  &:disabled {
    background: var(--text-disabled);
    opacity: 0.5;
  }
}

.error-section {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-sm);
  padding: 20rpx;
  margin-bottom: 24rpx;
}

.error-text {
  font-size: 24rpx;
  color: var(--color-danger);
}

.result-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24rpx;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
}

.result-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text-primary);
}

.copy-btn {
  font-size: 24rpx;
  color: var(--color-primary);
  padding: 8rpx 16rpx;
}

.result-content {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 20rpx;
  max-height: 500rpx;
  overflow-y: auto;
}

.result-text {
  font-size: 26rpx;
  color: var(--text-primary);
  line-height: 1.7;
  word-break: break-all;
}
```

**Step 6: 编译验证**

```bash
npx taro build --type weapp
```

Expected: `Compiled successfully`，无新增错误。

**Step 7: Commit**

```bash
git add src/pages/ocr/ src/app.config.ts src/services/tool.ts src/services/request.ts
git commit -m "feat: 注册所有新增页面路由 + 扩展 TabBar + 新增 OCR 拍照识别"
```

---

### Task 2: 跨设备文件传输页面

**Files:**
- Create: `src/pages/cross-share/file/index.tsx`
- Create: `src/pages/cross-share/file/index.scss`
- Modify: `src/types/crossShare.ts` — 确认 CrossFile 和 StorageStats 类型字段完整

**Step 1: 检查并补充类型**

在 `src/types/crossShare.ts` 中确认：

```typescript
export interface CrossFile {
  id: string
  file_name?: string
  file_size?: number
  file_type?: string
  mime_type?: string
  created_at?: string
  updated_at?: string
  // 根据实际后端返回补充
}

export interface StorageStats {
  used_bytes: number
  total_bytes: number
  file_count?: number
}
```

**Step 2: 创建文件传输页面组件**

```tsx
// src/pages/cross-share/file/index.tsx
import { useState } from 'react'
import Taro, { useDidShow } from '@tarojs/taro'
import { View, Text, ScrollView } from '@tarojs/components'
import { fileApi } from '../../../services/crossShare'
import type { CrossFile, StorageStats } from '../../../types/crossShare'
import { formatFileSize, formatDateTime } from '../../../utils'
import Loading from '../../../components/Loading'
import EmptyState from '../../../components/EmptyState'
import './index.scss'

export default function CrossShareFile() {
  const [files, setFiles] = useState<CrossFile[]>([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<StorageStats | null>(null)

  useDidShow(() => {
    loadFiles()
    loadStats()
  })

  const loadFiles = async () => {
    setLoading(true)
    try {
      const data = await fileApi.getFiles(100, 0)
      setFiles(data)
    } catch (err) {
      console.error('Failed to load files:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const data = await fileApi.getStorageStats()
      setStats(data)
    } catch (err) {
      // 忽略统计失败
    }
  }

  // 上传文件
  const handleUpload = async () => {
    try {
      const res = await Taro.chooseMessageFile({
        count: 1,
        type: 'file'
      })
      const file = res.files[0]
      await fileApi.uploadFile(file.path)
      await loadFiles()
      await loadStats()
      Taro.showToast({ title: '上传成功', icon: 'success' })
    } catch (err: any) {
      if (err.errMsg !== 'chooseMessageFile:fail cancel') {
        Taro.showToast({ title: '上传失败', icon: 'none' })
      }
    }
  }

  // 删除文件
  const handleDelete = async (fileId: string) => {
    Taro.showModal({
      title: '确认删除',
      content: '确定要删除这个文件吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await fileApi.deleteFile(fileId)
            await loadFiles()
            await loadStats()
            Taro.showToast({ title: '已删除', icon: 'success' })
          } catch (err) {
            Taro.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  }

  // 下载/分享文件
  const handleDownload = async (file: CrossFile) => {
    try {
      const urlRes = await fileApi.getDownloadUrl(file.id)
      await Taro.openDocument({
        filePath: urlRes.download_url,
        fail: () => {
          Taro.setClipboardData({ data: urlRes.download_url })
          Taro.showToast({ title: '已复制链接', icon: 'success' })
        }
      })
    } catch (err) {
      Taro.showToast({ title: '获取链接失败', icon: 'none' })
    }
  }

  // 获取文件类型图标
  const getFileIcon = (fileName: string) => {
    const ext = fileName?.split('.').pop()?.toLowerCase()
    const iconMap: Record<string, string> = {
      'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'webp': '🖼️',
      'pdf': '📄', 'doc': '📝', 'docx': '📝',
      'xls': '📊', 'xlsx': '📊',
      'zip': '📦', 'rar': '📦', '7z': '📦',
      'txt': '📃', 'md': '📃',
    }
    return iconMap[ext || ''] || '📎'
  }

  return (
    <View className='file-page'>
      {/* 存储统计 */}
      {stats && (
        <View className='stats-bar'>
          <Text className='stats-text'>已用：{formatFileSize(stats.used_bytes || 0)}</Text>
          <Text className='stats-text'>总量：{formatFileSize(stats.total_bytes || 0)}</Text>
        </View>
      )}

      {/* 文件列表 */}
      {loading ? (
        <Loading text='加载文件...' />
      ) : files.length === 0 ? (
        <EmptyState icon='📁' title='暂无文件' description='上传一个文件开始跨设备传输' />
      ) : (
        <ScrollView className='file-list' scrollY>
          {files.map((file) => (
            <View key={file.id} className='file-item' onClick={() => handleDownload(file)}>
              <View className='file-icon'>{getFileIcon(file.file_name || '')}</View>
              <View className='file-info'>
                <Text className='file-name'>{file.file_name || '未知文件'}</Text>
                <Text className='file-meta'>
                  {formatFileSize(file.file_size || 0)} · {formatDateTime(file.created_at || '')}
                </Text>
              </View>
              <View className='file-actions'>
                <Text className='action-delete' onClick={(e) => {
                  e.stopPropagation()
                  handleDelete(file.id)
                }}>删除</Text>
              </View>
            </View>
          ))}
        </ScrollView>
      )}

      {/* 上传按钮 */}
      <View className='upload-bar'>
        <button className='upload-btn' onClick={handleUpload}>
          📤 上传文件
        </button>
      </View>
    </View>
  )
}
```

**Step 3: 创建文件页面样式**

```scss
// src/pages/cross-share/file/index.scss
.file-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.stats-bar {
  display: flex;
  justify-content: space-between;
  padding: 16rpx 24rpx;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.stats-text {
  font-size: 22rpx;
  color: var(--text-tertiary);
}

.file-list {
  flex: 1;
  padding: 16rpx 24rpx;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 20rpx 16rpx;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  margin-bottom: 12rpx;

  &:active {
    background: var(--bg-tertiary);
  }
}

.file-icon {
  font-size: 48rpx;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 26rpx;
  color: var(--text-primary);
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  font-size: 22rpx;
  color: var(--text-tertiary);
  display: block;
  margin-top: 4rpx;
}

.file-actions {
  flex-shrink: 0;
}

.action-delete {
  font-size: 22rpx;
  color: var(--color-danger);
  padding: 8rpx 12rpx;
}

.upload-bar {
  padding: 24rpx;
  padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
}

.upload-btn {
  width: 100%;
  height: 88rpx;
  background: var(--color-primary);
  color: #fff;
  font-size: 30rpx;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;

  &::after {
    border: none;
  }
}
```

**Step 4: 编译验证 + Commit**

```bash
npx taro build --type weapp
git add src/pages/cross-share/file/ src/types/crossShare.ts
git commit -m "feat: 新增跨设备文件传输页面"
```

---

### Task 3: HTTP API 客户端页面

**Files:**
- Create: `src/pages/http-client/index.tsx`
- Create: `src/pages/http-client/index.scss`

**Step 1: 创建 HTTP 客户端页面**

```tsx
// src/pages/http-client/index.tsx
import { useState } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, Input, Textarea, Picker } from '@tarojs/components'
import './index.scss'

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'

interface HeaderEntry {
  key: string
  value: string
}

export default function HttpClientPage() {
  const [method, setMethod] = useState<HttpMethod>('GET')
  const [url, setUrl] = useState('')
  const [headers, setHeaders] = useState<HeaderEntry[]>([{ key: '', value: '' }])
  const [body, setBody] = useState('')
  const [response, setResponse] = useState<any>(null)
  const [responseStatus, setResponseStatus] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [bodyError, setBodyError] = useState('')

  const methods: HttpMethod[] = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']

  const addHeader = () => setHeaders([...headers, { key: '', value: '' }])

  const updateHeader = (index: number, field: 'key' | 'value', value: string) => {
    const newHeaders = [...headers]
    newHeaders[index][field] = value
    setHeaders(newHeaders)
  }

  const removeHeader = (index: number) => {
    setHeaders(headers.filter((_, i) => i !== index))
  }

  const formatBody = () => {
    if (!body.trim()) return
    try {
      const parsed = JSON.parse(body)
      setBody(JSON.stringify(parsed, null, 2))
      setBodyError('')
    } catch (e: any) {
      setBodyError(`JSON 格式错误: ${e.message}`)
    }
  }

  const handleSend = async () => {
    if (!url.trim()) {
      Taro.showToast({ title: '请输入 URL', icon: 'none' })
      return
    }

    if (body.trim() && method !== 'GET' && method !== 'DELETE') {
      try {
        JSON.parse(body)
        setBodyError('')
      } catch (e: any) {
        setBodyError(`JSON 格式错误: ${e.message}`)
        return
      }
    }

    setLoading(true)
    setResponse(null)
    setResponseStatus(null)

    try {
      const customHeaders: Record<string, string> = {}
      headers.forEach(h => {
        if (h.key.trim()) customHeaders[h.key.trim()] = h.value.trim()
      })

      const res = await Taro.request({
        url: url.trim(),
        method,
        data: (method === 'POST' || method === 'PUT' || method === 'PATCH') && body.trim() ? JSON.parse(body) : undefined,
        header: {
          'Content-Type': 'application/json',
          ...customHeaders
        },
        timeout: 30000
      })

      setResponseStatus(res.statusCode)
      setResponse({
        status: res.statusCode,
        headers: res.header,
        data: res.data
      })
    } catch (err: any) {
      setResponseStatus(err.statusCode || 0)
      setResponse({
        status: err.statusCode || 0,
        error: err.message || err.errMsg || '请求失败'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleCopyResponse = async () => {
    if (!response) return
    try {
      await Taro.setClipboardData({ data: JSON.stringify(response, null, 2) })
      Taro.showToast({ title: '已复制', icon: 'success' })
    } catch (err) {
      Taro.showToast({ title: '复制失败', icon: 'none' })
    }
  }

  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return 'status-success'
    if (status >= 400 && status < 500) return 'status-warning'
    if (status >= 500) return 'status-error'
    return 'status-info'
  }

  return (
    <View className='http-client-page'>
      <View className='url-bar'>
        <Picker mode='selector' range={methods} value={methods.indexOf(method)} onChange={(e) => setMethod(methods[e.detail.value])}>
          <View className='method-picker'>{method}</View>
        </Picker>
        <input className='url-input' value={url} onInput={(e) => setUrl(e.detail.value)} placeholder='https://api.example.com/data' confirmType='go' onConfirm={handleSend} />
      </View>

      <View className='section'>
        <View className='section-header'>
          <Text className='section-title'>Headers</Text>
          <Text className='add-btn' onClick={addHeader}>+ 添加</Text>
        </View>
        {headers.map((h, i) => (
          <View key={i} className='header-row'>
            <input className='header-input' value={h.key} onInput={(e) => updateHeader(i, 'key', e.detail.value)} placeholder='Header 名称' />
            <input className='header-input' value={h.value} onInput={(e) => updateHeader(i, 'value', e.detail.value)} placeholder='值' />
            {headers.length > 1 && <Text className='remove-btn' onClick={() => removeHeader(i)}>×</Text>}
          </View>
        ))}
      </View>

      {(method === 'POST' || method === 'PUT' || method === 'PATCH') && (
        <View className='section'>
          <View className='section-header'>
            <Text className='section-title'>Body (JSON)</Text>
            <Text className='add-btn' onClick={formatBody}>格式化</Text>
          </View>
          <Textarea className='body-textarea' value={body} onInput={(e) => setBody(e.detail.value)} placeholder='{"key": "value"}' maxlength={-1} />
          {bodyError && <Text className='body-error'>{bodyError}</Text>}
        </View>
      )}

      <View className='send-bar'>
        <button className='send-btn' onClick={handleSend} disabled={loading}>
          {loading ? '发送中...' : '发送请求'}
        </button>
      </View>

      {response && (
        <View className='response-section'>
          <View className='response-header'>
            <Text className='response-title'>响应</Text>
            {responseStatus && <Text className={`status-badge ${getStatusColor(responseStatus)}`}>{responseStatus}</Text>}
            <Text className='copy-btn' onClick={handleCopyResponse}>复制</Text>
          </View>
          <View className='response-content'>
            <Text className='response-text' selectable>{JSON.stringify(response, null, 2)}</Text>
          </View>
        </View>
      )}
    </View>
  )
}
```

**Step 2: 创建 HTTP 客户端样式**

```scss
// src/pages/http-client/index.scss
.http-client-page {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 24rpx;
  padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
}

.url-bar {
  display: flex;
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.method-picker {
  background: var(--color-primary);
  color: #fff;
  padding: 0 24rpx;
  border-radius: var(--radius-sm);
  font-size: 26rpx;
  font-weight: 600;
  display: flex;
  align-items: center;
  min-width: 140rpx;
  justify-content: center;
  height: 72rpx;
}

.url-input {
  flex: 1;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 0 20rpx;
  height: 72rpx;
  font-size: 24rpx;
  color: var(--text-primary);
  font-family: 'Courier New', monospace;

  &::placeholder { color: var(--text-tertiary); }
}

.section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20rpx;
  margin-bottom: 24rpx;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.section-title {
  font-size: 26rpx;
  font-weight: 600;
  color: var(--text-primary);
}

.add-btn {
  font-size: 24rpx;
  color: var(--color-primary);
}

.header-row {
  display: flex;
  gap: 12rpx;
  margin-bottom: 8rpx;
  align-items: center;
}

.header-input {
  flex: 1;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 0 16rpx;
  height: 60rpx;
  font-size: 22rpx;
  color: var(--text-primary);

  &::placeholder { color: var(--text-tertiary); }
}

.remove-btn {
  font-size: 32rpx;
  color: var(--color-danger);
  width: 48rpx;
  height: 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.body-textarea {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16rpx;
  font-size: 22rpx;
  color: var(--text-primary);
  font-family: 'Courier New', monospace;
  min-height: 160rpx;
  width: 100%;

  &::placeholder { color: var(--text-tertiary); }
}

.body-error {
  font-size: 22rpx;
  color: var(--color-danger);
  margin-top: 8rpx;
  display: block;
}

.send-bar { margin-bottom: 24rpx; }

.send-btn {
  width: 100%;
  height: 88rpx;
  background: var(--color-primary);
  color: #fff;
  font-size: 30rpx;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;

  &::after { border: none; }
  &:disabled { opacity: 0.5; }
}

.response-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20rpx;
}

.response-header {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 12rpx;
}

.response-title {
  font-size: 26rpx;
  font-weight: 600;
  color: var(--text-primary);
}

.status-badge {
  font-size: 22rpx;
  padding: 4rpx 12rpx;
  border-radius: var(--radius-full);
  font-weight: 600;

  &.status-success { background: rgba(34, 197, 94, 0.15); color: #22C55E; }
  &.status-warning { background: rgba(245, 158, 11, 0.15); color: #F59E0B; }
  &.status-error { background: rgba(239, 68, 68, 0.15); color: #EF4444; }
  &.status-info { background: rgba(59, 130, 246, 0.15); color: #3B82F6; }
}

.copy-btn {
  margin-left: auto;
  font-size: 24rpx;
  color: var(--color-primary);
}

.response-content {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16rpx;
  max-height: 500rpx;
  overflow-y: auto;
}

.response-text {
  font-size: 22rpx;
  color: var(--text-primary);
  font-family: 'Courier New', monospace;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}
```

**Step 3: 编译验证 + Commit**

```bash
npx taro build --type weapp
git add src/pages/http-client/
git commit -m "feat: 新增 HTTP API 客户端页面"
```

---

## 阶段二：中优先级 + 体验优化

### Task 4: ASR 语音识别页面

**Files:**
- Create: `src/pages/asr/index.tsx`
- Create: `src/pages/asr/index.scss`

**Step 1: 创建 ASR 页面组件**

注意：ASR 后端路径是 `/asr/predict`（不是 `/tools/asr/predict`）。

```tsx
// src/pages/asr/index.tsx
import { useState, useRef } from 'react'
import Taro, { useDidShow } from '@tarojs/taro'
import { View, Text } from '@tarojs/components'
import { uploadFile } from '../../services/request'
import './index.scss'

export default function ASRPage() {
  const [isRecording, setIsRecording] = useState(false)
  const [duration, setDuration] = useState(0)
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lang, setLang] = useState('zh')
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const recorderRef = useRef<Taro.RecorderManager | null>(null)

  useDidShow(() => {
    if (!recorderRef.current) {
      recorderRef.current = Taro.getRecorderManager()
      recorderRef.current.onStart(() => {
        setIsRecording(true)
        setDuration(0)
        timerRef.current = setInterval(() => setDuration(d => d + 1), 1000)
      })
      recorderRef.current.onStop(async (res) => {
        setIsRecording(false)
        if (timerRef.current) clearInterval(timerRef.current)
        await handleTranscribe(res.tempFilePath)
      })
      recorderRef.current.onError(() => {
        setIsRecording(false)
        if (timerRef.current) clearInterval(timerRef.current)
        setError('录音失败')
      })
    }
  })

  const handleToggleRecord = () => {
    if (isRecording) {
      recorderRef.current?.stop()
    } else {
      setError('')
      setResult('')
      recorderRef.current?.start({
        duration: 60000,
        sampleRate: 16000,
        numberOfChannels: 1,
        format: 'wav',
        frameSize: 5
      })
    }
  }

  const handleTranscribe = async (filePath: string) => {
    setLoading(true)
    setError('')
    try {
      // 注意：路径是 /asr/predict，不是 /tools/asr/predict
      const res = await uploadFile('/asr/predict', filePath, 'file', { language: lang })
      const text = res?.text || res?.result || JSON.stringify(res)
      setResult(typeof text === 'string' ? text : JSON.stringify(text, null, 2))
      Taro.showToast({ title: '识别成功', icon: 'success' })
    } catch (err: any) {
      setError(err.message || '识别失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async () => {
    if (!result) return
    try {
      await Taro.setClipboardData({ data: result })
      Taro.showToast({ title: '已复制', icon: 'success' })
    } catch (err) {
      Taro.showToast({ title: '复制失败', icon: 'none' })
    }
  }

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }

  return (
    <View className='asr-page'>
      <View className='lang-bar'>
        <Text className={`lang-item ${lang === 'zh' ? 'active' : ''}`} onClick={() => setLang('zh')}>中文</Text>
        <Text className={`lang-item ${lang === 'en' ? 'active' : ''}`} onClick={() => setLang('en')}>English</Text>
      </View>

      <View className='record-section'>
        <View className={`record-btn ${isRecording ? 'recording' : ''}`} onClick={handleToggleRecord}>
          <View className={`record-circle ${isRecording ? 'pulse' : ''}`} />
        </View>
        <Text className='record-text'>
          {isRecording ? `录音中 ${formatDuration(duration)}` : '点击开始录音'}
        </Text>
        {loading && <Text className='loading-text'>识别中...</Text>}
      </View>

      {error && <View className='error-section'><Text className='error-text'>{error}</Text></View>}

      {result && (
        <View className='result-section'>
          <View className='result-header'>
            <Text className='result-title'>识别结果</Text>
            <Text className='copy-btn' onClick={handleCopy}>复制</Text>
          </View>
          <View className='result-content'>
            <Text className='result-text' selectable>{result}</Text>
          </View>
        </View>
      )}
    </View>
  )
}
```

**Step 2: 创建 ASR 样式**

```scss
// src/pages/asr/index.scss
.asr-page {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 24rpx;
  padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
}

.lang-bar {
  display: flex;
  gap: 24rpx;
  margin-bottom: 48rpx;
}

.lang-item {
  flex: 1;
  text-align: center;
  padding: 16rpx 0;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 26rpx;
  color: var(--text-secondary);

  &.active {
    background: rgba(59, 130, 246, 0.15);
    border-color: var(--color-primary);
    color: var(--color-primary);
  }
}

.record-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24rpx;
  margin-bottom: 48rpx;
}

.record-btn {
  width: 200rpx;
  height: 200rpx;
  border-radius: 50%;
  background: var(--bg-secondary);
  border: 3px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;

  &.recording { border-color: var(--color-danger); }
}

.record-circle {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  background: var(--color-primary);

  &.pulse {
    background: var(--color-danger);
    animation: pulse 1.5s ease-in-out infinite;
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: 0.7; }
}

.record-text { font-size: 28rpx; color: var(--text-secondary); }
.loading-text { font-size: 26rpx; color: var(--color-primary); }

.error-section {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-sm);
  padding: 20rpx;
  margin-bottom: 24rpx;
}

.error-text { font-size: 24rpx; color: var(--color-danger); }

.result-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24rpx;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
}

.result-title { font-size: 28rpx; font-weight: 600; color: var(--text-primary); }

.copy-btn { font-size: 24rpx; color: var(--color-primary); padding: 8rpx 16rpx; }

.result-content {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 20rpx;
  max-height: 500rpx;
  overflow-y: auto;
}

.result-text {
  font-size: 26rpx;
  color: var(--text-primary);
  line-height: 1.7;
  word-break: break-all;
}
```

**Step 3: 编译验证 + Commit**

```bash
npx taro build --type weapp
git add src/pages/asr/
git commit -m "feat: 新增 ASR 语音识别页面"
```

---

### Task 5: 修改密码页面

**Files:**
- Create: `src/pages/change-password/index.tsx`
- Create: `src/pages/change-password/index.scss`
- Modify: `src/pages/profile/index.tsx` — "修改密码" 跳转

**Step 1: 创建修改密码页面**

```tsx
// src/pages/change-password/index.tsx
import { useState } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, Input, Button } from '@tarojs/components'
import { authApi } from '../../services/auth'
import './index.scss'

export default function ChangePasswordPage() {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [strength, setStrength] = useState(0)

  const evaluateStrength = (pwd: string) => {
    let score = 0
    if (pwd.length >= 8) score++
    if (pwd.length >= 12) score++
    if (/[A-Z]/.test(pwd)) score++
    if (/[0-9]/.test(pwd)) score++
    if (/[^A-Za-z0-9]/.test(pwd)) score++
    return score
  }

  const handleNewPasswordInput = (value: string) => {
    setNewPassword(value)
    setStrength(evaluateStrength(value))
  }

  const strengthLabels = ['', '弱', '一般', '中等', '强', '非常强']
  const strengthColors = ['', '#EF4444', '#F59E0B', '#3B82F6', '#22C55E', '#10B981']

  const handleSubmit = async () => {
    if (!oldPassword || !newPassword || !confirmPassword) {
      setError('请填写所有字段')
      return
    }
    if (newPassword.length < 6) {
      setError('新密码至少 6 个字符')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }

    setLoading(true)
    setError('')
    try {
      await authApi.changePassword(oldPassword, newPassword)
      Taro.showToast({ title: '密码修改成功', icon: 'success' })
      setTimeout(() => {
        Taro.navigateTo({ url: '/pages/login/index' })
      }, 1500)
    } catch (err: any) {
      setError(err.message || err.data?.detail || '修改失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <View className='change-password-page'>
      <View className='change-password-card'>
        <Text className='card-title'>修改密码</Text>
        {error && <View className='error-msg'><Text>{error}</Text></View>}

        <View className='form-item'>
          <Text className='form-label'>当前密码</Text>
          <Input className='form-input' type='password' placeholder='输入当前密码' value={oldPassword} onInput={(e) => setOldPassword(e.detail.value)} />
        </View>

        <View className='form-item'>
          <Text className='form-label'>新密码</Text>
          <Input className='form-input' type='password' placeholder='至少6个字符' value={newPassword} onInput={(e) => handleNewPasswordInput(e.detail.value)} />
          {newPassword && (
            <View className='strength-bar'>
              {[1, 2, 3, 4, 5].map(i => (
                <View key={i} className='strength-segment' style={{ background: i <= strength ? strengthColors[strength] : 'var(--bg-tertiary)' }} />
              ))}
              <Text className='strength-label' style={{ color: strengthColors[strength] }}>{strengthLabels[strength]}</Text>
            </View>
          )}
        </View>

        <View className='form-item'>
          <Text className='form-label'>确认新密码</Text>
          <Input className='form-input' type='password' placeholder='再次输入新密码' value={confirmPassword} onInput={(e) => setConfirmPassword(e.detail.value)} />
        </View>

        <Button className='submit-btn' loading={loading} disabled={loading} onClick={handleSubmit}>
          {loading ? '修改中...' : '确认修改'}
        </Button>
      </View>
    </View>
  )
}
```

**Step 2: 创建样式**

```scss
// src/pages/change-password/index.scss
.change-password-page {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 48rpx 24rpx;
}

.change-password-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 40rpx 32rpx;
}

.card-title {
  font-size: 36rpx;
  font-weight: 700;
  color: var(--text-primary);
  display: block;
  text-align: center;
  margin-bottom: 40rpx;
}

.error-msg {
  background: rgba(239, 68, 68, 0.1);
  border-radius: var(--radius-sm);
  padding: 16rpx;
  margin-bottom: 24rpx;
  text-align: center;
  text { font-size: 24rpx; color: var(--color-danger); }
}

.form-item { margin-bottom: 32rpx; }

.form-label {
  font-size: 26rpx;
  color: var(--text-secondary);
  margin-bottom: 12rpx;
  display: block;
}

.form-input {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 0 20rpx;
  height: 72rpx;
  font-size: 28rpx;
  color: var(--text-primary);
  &::placeholder { color: var(--text-tertiary); }
}

.strength-bar {
  display: flex;
  align-items: center;
  gap: 6rpx;
  margin-top: 12rpx;
}

.strength-segment {
  flex: 1;
  height: 6rpx;
  border-radius: 3rpx;
  transition: background 0.3s;
}

.strength-label {
  font-size: 20rpx;
  margin-left: 12rpx;
}

.submit-btn {
  width: 100%;
  height: 88rpx;
  background: var(--color-primary);
  color: #fff;
  font-size: 30rpx;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: none;
  margin-top: 16rpx;
  &::after { border: none; }
}
```

**Step 3: 修改个人中心"修改密码"跳转**

在 `src/pages/profile/index.tsx` 中：

```tsx
// 找到"修改密码"菜单项，替换为：
<View className='menu-item' onClick={() => Taro.navigateTo({ url: '/pages/change-password/index' })}>
  <Text className='menu-label'>修改密码</Text>
  <Text className='menu-arrow'>›</Text>
</View>
```

**Step 4: 编译验证 + Commit**

```bash
npx taro build --type weapp
git add src/pages/change-password/ src/pages/profile/index.tsx
git commit -m "feat: 新增修改密码页面并接入个人中心"
```

---

### Task 6: 帮助页 + 个人中心全部菜单接入

**Files:**
- Create: `src/pages/help/index.tsx`
- Create: `src/pages/help/index.scss`
- Modify: `src/pages/profile/index.tsx`

**Step 1: 创建帮助页**

```tsx
// src/pages/help/index.tsx
import { View, Text } from '@tarojs/components'
import './index.scss'

const FAQS = [
  { q: '如何使用跨设备消息同步？', a: '在任意设备发送消息，其他设备打开消息页面即可查看。支持文本、JSON、链接等格式。' },
  { q: '如何上传/下载文件？', a: '点击底部 TabBar 的"文件"标签，选择本地文件上传。点击文件可下载或分享。' },
  { q: 'OCR 识别支持哪些语言？', a: '目前支持中文和英文文字识别。选择图片后可切换识别语言。' },
  { q: '如何修改密码？', a: '进入"我的"页面，点击"修改密码"，输入当前密码和新密码即可。' },
  { q: '数据会保存多久？', a: '消息和文件会保存在服务器，具体保留时间取决于管理员配置。' },
]

export default function HelpPage() {
  return (
    <View className='help-page'>
      <View className='help-header'>
        <Text className='help-title'>使用帮助</Text>
        <Text className='help-desc'>常见问题与使用说明</Text>
      </View>

      <View className='faq-list'>
        {FAQS.map((faq, i) => (
          <View key={i} className='faq-item'>
            <Text className='faq-question'>Q: {faq.q}</Text>
            <Text className='faq-answer'>{faq.a}</Text>
          </View>
        ))}
      </View>

      <View className='help-footer'>
        <Text className='version-text'>工具箱小程序 v1.0.0</Text>
        <Text className='version-text'>基于 Taro 4.x + React 18</Text>
      </View>
    </View>
  )
}
```

**Step 2: 创建帮助页样式**

```scss
// src/pages/help/index.scss
.help-page {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 24rpx;
  padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
}

.help-header {
  text-align: center;
  padding: 48rpx 0;
}

.help-title {
  font-size: 40rpx;
  font-weight: 700;
  color: var(--text-primary);
  display: block;
  margin-bottom: 12rpx;
}

.help-desc {
  font-size: 26rpx;
  color: var(--text-tertiary);
  display: block;
}

.faq-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.faq-item {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24rpx;
}

.faq-question {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text-primary);
  display: block;
  margin-bottom: 12rpx;
}

.faq-answer {
  font-size: 26rpx;
  color: var(--text-secondary);
  line-height: 1.6;
  display: block;
}

.help-footer {
  text-align: center;
  padding: 48rpx 0;
}

.version-text {
  font-size: 24rpx;
  color: var(--text-tertiary);
  display: block;
}
```

**Step 3: 修改个人中心全部菜单项**

在 `src/pages/profile/index.tsx` 中，修改 4 个菜单项：

```tsx
// "账号设置" — 暂未开放
<View className='menu-item' onClick={() => Taro.showToast({ title: '账号设置开发中', icon: 'none' })}>
  <Text className='menu-label'>账号设置</Text>
  <Text className='menu-arrow'>›</Text>
</View>

// "修改密码" — 跳转
<View className='menu-item' onClick={() => Taro.navigateTo({ url: '/pages/change-password/index' })}>
  <Text className='menu-label'>修改密码</Text>
  <Text className='menu-arrow'>›</Text>
</View>

// "使用帮助" — 跳转
<View className='menu-item' onClick={() => Taro.navigateTo({ url: '/pages/help/index' })}>
  <Text className='menu-label'>使用帮助</Text>
  <Text className='menu-arrow'>›</Text>
</View>

// "关于工具箱" — 跳转
<View className='menu-item' onClick={() => Taro.navigateTo({ url: '/pages/help/index' })}>
  <Text className='menu-label'>关于工具箱</Text>
  <Text className='menu-arrow'>›</Text>
</View>
```

**Step 4: 编译验证 + Commit**

```bash
npx taro build --type weapp
git add src/pages/help/ src/pages/profile/index.tsx
git commit -m "feat: 新增帮助页并接入个人中心菜单"
```

---

### Task 7: 登录页优化 + TabBar 图标

**Files:**
- Modify: `src/pages/login/index.tsx` — 登录后返回上一页
- Replace: `src/assets/icons/` — 4 组正式图标（含 file）
- Modify: `src/services/tool.ts` — 已在 Task 1 中完成

**Step 1: 优化登录后跳转**

在 `src/pages/login/index.tsx` 的 `handleSubmit` 成功后替换：

```tsx
setTimeout(() => {
  try {
    const pages = Taro.getCurrentPages()
    if (pages.length > 1) {
      Taro.navigateBack()
    } else {
      Taro.redirectTo({ url: '/pages/index/index' })
    }
  } catch {
    Taro.redirectTo({ url: '/pages/index/index' })
  }
}, 1000)
```

**Step 2: 生成正式 TabBar 图标（4 组）**

用 Python 生成 81x81 PNG 图标：

- `tool.png` / `tool-active.png` — 网格/齿轮
- `message.png` / `message-active.png` — 对话气泡
- `file.png` / `file-active.png` — 文件夹（新增）
- `profile.png` / `profile-active.png` — 用户头像

灰色: `#94A3B8`, 蓝色: `#3B82F6`

```bash
# 生成 8 个 PNG 文件到 src/assets/icons/
python3 scripts/generate_icons.py  # 或直接用内联 Python
```

**Step 3: 编译验证 + Commit**

```bash
npx taro build --type weapp
git add src/pages/login/index.tsx src/assets/icons/
git commit -m "fix: 优化登录跳转逻辑、替换 TabBar 图标"
```

---

## 阶段三：H5 构建与浏览器预览

### Task 8: H5 构建配置

**Files:**
- Modify: `config/index.ts` — 完善 h5 配置
- Modify: `src/services/request.ts` — uploadFile/downloadFile 增加 H5 降级

**Step 1: 完善 config/index.ts 的 H5 配置**

在 `h5` 部分添加路由：

```typescript
h5: {
  publicPath: '/',
  staticDirectory: 'static',
  output: {
    filename: 'js/[name].[hash:8].js',
    chunkFilename: 'js/[name].[chunkhash:8].js'
  },
  router: {
    mode: 'hash' as const
  },
  devServer: {
    port: 10086,
    hot: true
  },
  postcss: {
    pxtransform: {
      enable: true,
      config: {}
    },
    url: { enable: true, config: { limit: 1024 } },
    autoprefixer: { enable: true, config: {} },
    cssModules: {
      enable: false,
      config: {
        namingPattern: 'module',
        generateScopedName: '[name]__[local]___[hash:base64:5]'
      }
    }
  },
  webpackChain(chain) {
    chain.resolve.plugin('tsconfig-paths').use(TsconfigPathsPlugin)
  }
}
```

**Step 2: request.ts 的 uploadFile/downloadFile 增加 H5 降级**

在 `src/services/request.ts` 中，在 `uploadFile` 函数开头添加环境检测：

```typescript
import Taro from '@tarojs/taro';

export async function uploadFile(
  url: string,
  filePath: string,
  name: string = 'file',
  formData: Record<string, any> = {}
): Promise<any> {
  // H5 端降级：使用 FormData + fetch
  if (Taro.getEnv() === Taro.ENV_TYPE.WEB) {
    // H5 端 uploadFile 由页面层通过 <input type="file"> 处理
    throw new Error('文件上传功能仅在小程序中可用')
  }

  // 小程序端保持原有逻辑
  const token = Taro.getStorageSync('auth_token');
  // ... 原有 uploadFile 逻辑
}
```

在 `downloadFile` 中添加类似检测。

**Step 3: 编译验证 H5**

```bash
npm run dev:h5
```

Expected: 开发服务器启动在 `http://localhost:10086`。

**Step 4: Commit**

```bash
git add config/index.ts src/services/request.ts
git commit -m "feat: 配置 H5 构建和 uploadFile H5 降级"
```

---

### Task 9: H5 浏览器验证

**验证步骤（手动）：**

1. 运行 `npm run dev:h5`
2. 浏览器打开 `http://localhost:10086`
3. 打开 Chrome 开发者工具（F12）
4. 逐一验证：
   - [ ] 工具首页渲染正常，工具列表显示
   - [ ] 登录/注册页面渲染正常
   - [ ] 个人中心渲染正常
   - [ ] JSON 格式化功能正常
   - [ ] 日历功能正常
   - [ ] 密钥生成器正常
   - [ ] 消息页面渲染正常
   - [ ] 暗色主题正常
   - [ ] TabBar 切换正常（H5 端可能不显示原生 TabBar）
   - [ ] Chrome DevTools 切换 iPhone 12/ iPad / Desktop 视图无布局错乱

**已知限制（H5 端）：**
- OCR 拍照：显示"该功能仅在小程序中可用"
- ASR 录音：显示"该功能仅在小程序中可用"
- 文件上传：显示"该功能仅在小程序中可用"
- 文件下载：改为 `<a download>` 直接下载

---

## 总结

| 阶段 | Task | 新增/修改文件 | Commit 信息 |
|------|------|-------------|------------|
| 阶段一 | Task 1: 路由注册 + OCR | 2 新增 + 4 修改 | feat: 注册所有页面路由 + TabBar + OCR |
| 阶段一 | Task 2: 文件传输 | 2 新增 + 1 修改 | feat: 新增跨设备文件传输页面 |
| 阶段一 | Task 3: HTTP 客户端 | 2 新增 | feat: 新增 HTTP API 客户端页面 |
| 阶段二 | Task 4: ASR | 2 新增 | feat: 新增 ASR 语音识别页面 |
| 阶段二 | Task 5: 修改密码 | 2 新增 + 1 修改 | feat: 新增修改密码页面 |
| 阶段二 | Task 6: 帮助页 | 2 新增 + 1 修改 | feat: 新增帮助页并接入个人中心 |
| 阶段二 | Task 7: 登录+图标 | 1 修改 + 4 新增图标 | fix: 优化登录跳转/替换图标 |
| 阶段三 | Task 8: H5 构建 | 2 修改 | feat: H5 构建配置和降级 |
| 阶段三 | Task 9: 验证 | 手动 | （手动验证） |

**总计：** 13 个新文件（含 8 个图标）+ 9 个修改文件 + 8 次提交。

**关键修正汇总：**
1. OCR 走 base64 JSON 请求（非 uploadFile）
2. ASR 路径是 `/asr/predict`（非 `/tools/asr/predict`）
3. TabBar 扩展到 4 个 tab（新增"文件"）
4. 所有路由注册在 Task 1 一次性完成
5. `request.ts` 增加 H5 降级处理
