# 小程序 OpenClaw 功能与 Web 前端保持一致 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让小程序 OpenClaw 聊天功能与 Web 前端完全一致（内容过滤、历史消息、消息去重、连接状态、时间戳显示）

**Architecture:** 复用 Web 前端已验证的 extractText 过滤逻辑、历史加载逻辑和连接状态处理，移植到 Taro 小程序框架。API 层完全相同，只修改 UI 层适配小程序组件。

**Tech Stack:** Taro React、微信小程序、后端 SSE 流式 API

---

### Task 1: 添加 extractText 内容过滤函数

**Files:**
- Modify: `tools-mini-program/src/pages/openclaw/index.tsx`

**Step 1: 添加 extractText 函数**

在 `interface ChatMessage` 之后、`export default function OpenClawPage()` 之前，添加完整的 `extractText` 函数：

```tsx
// 从 OpenClaw 消息内容数组中提取用户可见文本
// 过滤 thinking、系统提示、时间戳等非内容文本
const extractText = (content: unknown): string => {
  const cleanText = (raw: string): string | null => {
    let text = raw.trim()
    if (!text) return null
    // 过滤 thinking 内容
    if (text.startsWith('[思考]')) return null
    // 去掉 bootstrap 提示：找到第一个时间戳，去掉它之前的所有内容
    if (text.startsWith('[Bootstrap')) {
      const tsPattern = /\[[A-Z][a-z]{2}\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+GMT[+-]\d+\]/
      const match = text.match(tsPattern)
      if (match && match.index !== undefined) {
        text = text.slice(match.index + match[0].length).trim()
      } else {
        return null
      }
    }
    // 过滤时间戳前缀如 [Sat 2026-04-25 13:53 GMT+8]
    const tsPattern = /^\[[A-Z][a-z]{2}\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+GMT[+-]\d+\]\s*/
    text = text.replace(tsPattern, '')
    return text || null
  }

  if (typeof content === 'string') {
    return cleanText(content) || ''
  }
  if (content === null || content === undefined) return ''
  if (typeof content === 'object' && !Array.isArray(content)) {
    const c = content as Record<string, unknown>
    if (c.type === 'thinking') return ''
    if (typeof c.text === 'string') {
      return cleanText(c.text) || ''
    }
    return ''
  }
  if (!Array.isArray(content)) return ''
  const parts: string[] = []
  for (const item of content) {
    if (typeof item !== 'object' || item === null) continue
    const c = item as Record<string, unknown>
    if (c.type === 'thinking') continue
    if (typeof c.text !== 'string') continue
    const cleaned = cleanText(c.text)
    if (cleaned) parts.push(cleaned)
  }
  return parts.join('\n')
}
```

**Step 2: Commit**

```bash
git add tools-mini-program/src/pages/openclaw/index.tsx
git commit -m "feat: 小程序 OpenClaw 添加内容过滤 extractText 函数"
```

---

### Task 2: 添加历史消息加载

**Files:**
- Modify: `tools-mini-program/src/pages/openclaw/index.tsx`
- Modify: `tools-mini-program/src/pages/openclaw/index.scss`

**Step 1: 导入 loadHistory**

修改 import 语句（第 4 行）：

```tsx
import { chatStream, resetSession, getStatus, abortChat, loadHistory } from '../../services/openclaw'
```

**Step 2: 添加 loadMessages 函数**

在组件内添加：

```tsx
  // 加载历史消息
  const loadMessages = async () => {
    try {
      const history = await loadHistory('main')
      const formatted: ChatMessage[] = []
      for (const [idx, msg] of history.entries()) {
        if (msg.role === 'toolResult') continue
        const text = extractText(msg.content)
        if (!text) continue
        formatted.push({
          id: `hist-${idx}`,
          role: msg.role === 'user' ? 'user' : 'assistant',
          content: text,
          timestamp: msg.timestamp || Date.now(),
        })
      }
      setMessages(formatted)
    } catch {
      // 忽略历史加载错误
    }
  }
```

**Step 3: 在 useDidShow 中调用 loadMessages**

修改 `useDidShow`：

```tsx
  useDidShow(() => {
    checkStatus()
    loadMessages()
  })
```

**Step 4: Commit**

```bash
git add tools-mini-program/src/pages/openclaw/index.tsx
git commit -m "feat: 小程序 OpenClaw 添加历史消息加载"
```

---

### Task 3: 修复消息重复（追加改替换）

**Files:**
- Modify: `tools-mini-program/src/pages/openclaw/index.tsx:81-88`

**Step 1: 修改 onChunk 回调**

找到 `handleSend` 中的 `chatStream` 调用，将 onChunk 从追加改为替换：

```tsx
        (chunk: string) => {
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [...prev.slice(0, -1), { ...last, content: chunk }]
            }
            return prev
          })
          scrollToBottom()
        },
```

注意：将 `last.content + chunk` 改为 `chunk`。

**Step 2: Commit**

```bash
git add tools-mini-program/src/pages/openclaw/index.tsx
git commit -m "fix: 小程序 OpenClaw 消息去重，追加改为替换"
```

---

### Task 4: 添加连接状态引导和 Loading

**Files:**
- Modify: `tools-mini-program/src/pages/openclaw/index.tsx`

**Step 1: 添加 isLoading 状态**

在 state 声明中添加：

```tsx
  const [isLoading, setIsLoading] = useState(true)
```

**Step 2: 修改 checkStatus 设置 loading**

```tsx
  const checkStatus = async () => {
    try {
      const status = await getStatus()
      setConnected(status.connected === true)
    } catch {
      setConnected(false)
    } finally {
      setIsLoading(false)
    }
  }
```

**Step 3: 添加 Loading 渲染**

在 return 语句开头添加（在原有 empty-state 之前）：

```tsx
  if (isLoading) {
    return (
      <View className='openclaw-page'>
        <View className='loading-container'>
          <View className='loading-spinner' />
          <Text className='loading-text'>加载中...</Text>
        </View>
      </View>
    )
  }
```

**Step 4: 添加未连接引导**

修改 toolbar 区域，在未连接时显示引导：

```tsx
      {/* 顶部工具栏 */}
      <View className='toolbar'>
        <Text className='toolbar-btn' onClick={handleNewChat}>
          + 新对话
        </Text>
        {!connected && (
          <Text className='disconnected-badge'>未连接</Text>
        )}
      </View>
      {!connected && (
        <View className='connect-guide'>
          <Text className='connect-guide-text'>服务未连接，请前往管理面板配置 OpenClaw 连接信息</Text>
        </View>
      )}
```

**Step 5: Commit**

```bash
git add tools-mini-program/src/pages/openclaw/index.tsx
git commit -m "feat: 小程序 OpenClaw 添加连接状态引导和 Loading"
```

---

### Task 5: 添加时间戳显示

**Files:**
- Modify: `tools-mini-program/src/pages/openclaw/index.tsx:181-193`
- Modify: `tools-mini-program/src/pages/openclaw/index.scss`

**Step 1: 修改消息渲染 JSX**

将消息渲染改为包含时间戳：

```tsx
            {messages.map((msg) => (
              <View key={msg.id} className={`message-row ${msg.role === 'user' ? 'message-row-user' : 'message-row-assistant'}`}>
                <View className='message-wrapper'>
                  <View className={`message-bubble ${msg.role === 'user' ? 'bubble-user' : 'bubble-assistant'}`}>
                    {msg.role === 'user' ? (
                      <Text className='message-text' selectable>{msg.content}</Text>
                    ) : (
                      <Markdown content={msg.content} />
                    )}
                    {msg.isStreaming && <Text className='streaming-indicator'>...</Text>}
                  </View>
                  <Text className={`message-time ${msg.role === 'user' ? 'time-right' : 'time-left'}`}>
                    {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                  </Text>
                </View>
              </View>
            ))}
```

**Step 2: 添加时间戳样式**

在 `index.scss` 中添加：

```scss
.message-wrapper {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.message-time {
  font-size: 22rpx;
  color: var(--text-tertiary);
  margin-top: 8rpx;
}

.time-right {
  text-align: right;
}

.time-left {
  text-align: left;
}

.loading-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.loading-spinner {
  width: 64rpx;
  height: 64rpx;
  border: 4rpx solid var(--border-color);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-text {
  margin-top: 24rpx;
  font-size: 28rpx;
  color: var(--text-secondary);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.connect-guide {
  padding: 16rpx 32rpx;
  background: rgba(245, 158, 11, 0.1);
  border-bottom: 1px solid var(--border-color);
}

.connect-guide-text {
  font-size: 24rpx;
  color: var(--color-warning);
}
```

**Step 3: Commit**

```bash
git add tools-mini-program/src/pages/openclaw/index.tsx tools-mini-program/src/pages/openclaw/index.scss
git commit -m "style: 小程序 OpenClaw 添加时间戳显示和加载样式"
```

---

### Task 6: 输入框在未连接时禁用

**Files:**
- Modify: `tools-mini-program/src/pages/openclaw/index.tsx:212`

**Step 1: 禁用未连接时的输入**

修改 Textarea 的 disabled：

```tsx
            disabled={isStreaming || !connected}
```

修改 send 按钮的 disabled：

```tsx
            disabled={!inputValue.trim() || isStreaming || !connected}
```

**Step 2: Commit**

```bash
git add tools-mini-program/src/pages/openclaw/index.tsx
git commit -m "fix: 小程序 OpenClaw 未连接时禁用输入"
```

---

### Task 7: 编译验证

**Files:**
- Test: `tools-mini-program/src/pages/openclaw/index.tsx`

**Step 1: 运行小程序编译**

```bash
cd tools-mini-program
npm run dev:weapp
```

Expected: 编译成功，无 TypeScript 错误。

**Step 2: Commit（如有变更）**

```bash
git add -A
git commit -m "chore: 编译验证通过"
```

---

## 测试清单

1. 打开小程序 OpenClaw 页面，确认历史消息正常加载
2. 发送消息，确认 AI 回复不重复
3. 确认用户消息和 AI 消息都有正确的时间戳
4. 确认 thinking 内容、bootstrap 提示、时间戳前缀被过滤
5. 断开 OpenClaw 后端连接，确认页面显示"未连接"引导
6. 确认未连接时输入框和发送按钮被禁用
