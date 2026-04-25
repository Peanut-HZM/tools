import { useState, useRef } from 'react'
import Taro, { useDidShow, useDidHide } from '@tarojs/taro'
import { View, Text, ScrollView, Textarea } from '@tarojs/components'
import { chatWebSocket, resetSession, getStatus, loadHistory } from '../../services/openclaw'
import Markdown from '../../components/Markdown'
import { useAuthGuard } from '../../hooks'
import './index.scss'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  isStreaming?: boolean
}

// 默认头像图标（简单的 SVG 转 base64）
const DEFAULT_USER_AVATAR = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHJ4PSIyMCIgZmlsbD0iIzNCODJGNiIvPjxjaXJjbGUgY3g9IjIwIiBjeT0iMTYiIHI9IjgiIGZpbGw9IndoaXRlIi8+PHBhdGggZD0iTTggMzZjMC04IDUuNS0xMiAxMi0xMnMxMiA0IDEyIDEyIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjMiIGZpbGw9Im5vbmUiLz48L3N2Zz4='
const DEFAULT_AI_AVATAR = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHJ4PSIyMCIgZmlsbD0iIzhCNTY0MiIvPjxjaXJjbGUgY3g9IjIwIiBjeT0iMTUiIHI9IjgiIGZpbGw9IndoaXRlIi8+PHJlY3QgeD0iMTAiIHk9IjI0IiB3aWR0aD0iMjAiIGhlaWdodD0iOCIgcng9IjQiIGZpbGw9IndoaXRlIi8+PC9zdmc+'

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

export default function OpenClawPage() {
  useAuthGuard()

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [connected, setConnected] = useState(true)
  const [isLoading, setIsLoading] = useState(true)
  const [scrollTop, setScrollTop] = useState(0)
  const wsAbortRef = useRef<{ abort: () => void } | null>(null)

  useDidShow(() => {
    checkStatus()
    loadMessages()
  })

  // 页面隐藏时中止生成
  useDidHide(() => {
    if (isStreaming) {
      if (wsAbortRef.current) {
        wsAbortRef.current.abort()
        wsAbortRef.current = null
      }
      setIsStreaming(false)
    }
  })

  const checkStatus = async () => {
    try {
      const status = await getStatus()
      setConnected(status.connected !== false)
    } catch {
      setConnected(false)
    } finally {
      setIsLoading(false)
    }
  }

  // 加载历史消息
  const loadMessages = async () => {
    try {
      const history = await loadHistory('main')
      console.log('[loadMessages] 历史消息数量:', history.length)
      const formatted: ChatMessage[] = []
      for (const [idx, msg] of history.entries()) {
        if (msg.role === 'toolResult') continue
        const text = extractText(msg.content)
        if (!text) {
          console.log('[loadMessages] 跳过空消息, idx:', idx, 'role:', msg.role)
          continue
        }
        console.log('[loadMessages] 添加消息, idx:', idx, 'role:', msg.role, 'text:', text.substring(0, 50))
        formatted.push({
          id: `hist-${idx}`,
          role: msg.role === 'user' ? 'user' : 'assistant',
          content: text,
          timestamp: msg.timestamp || Date.now(),
        })
      }
      console.log('[loadMessages] 最终消息数量:', formatted.length)
      setMessages(formatted)
      if (formatted.length > 0) {
        // 延迟滚动到底部，确保 DOM 已渲染
        setTimeout(() => scrollToBottom(), 300)
      }
    } catch (err) {
      console.error('[loadMessages] 加载失败:', err)
    }
  }

  const scrollToBottom = () => {
    setScrollTop(Date.now())
  }

  const handleSend = async () => {
    Taro.showToast({ title: 'handleSend 被调用', icon: 'none', duration: 1000 })
    console.log('[handleSend] 被调用，inputValue:', inputValue, 'isStreaming:', isStreaming)
    if (!inputValue.trim() || isStreaming) {
      console.log('[handleSend] 提前返回，原因:', !inputValue.trim() ? '内容为空' : '正在流式生成')
      return
    }

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      timestamp: Date.now()
    }

    const assistantMsgId = `assistant-${Date.now()}`
    const assistantMessage: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isStreaming: true
    }

    setMessages(prev => [...prev, userMessage, assistantMessage])
    setInputValue('')
    setIsStreaming(true)
    wsAbortRef.current = null
    scrollToBottom()

    try {
      const wsResult = chatWebSocket(
        userMessage.content,
        'main',
        // onChunk - 通过 ID 精确匹配，与 Web 端一致
        (chunk: string) => {
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantMsgId
                ? { ...msg, content: chunk }
                : msg
            )
          )
          scrollToBottom()
        },
        // onDone
        () => {
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantMsgId
                ? { ...msg, isStreaming: false }
                : msg
            )
          )
          setIsStreaming(false)
          wsAbortRef.current = null
        },
        // onError
        (error: string) => {
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantMsgId
                ? { ...msg, content: msg.content || `[生成失败] ${error}`, isStreaming: false }
                : msg
            )
          )
          setIsStreaming(false)
          wsAbortRef.current = null
        }
      )
      wsAbortRef.current = wsResult
    } catch (err: any) {
      setIsStreaming(false)
      wsAbortRef.current = null
      Taro.showToast({ title: err.message || '发送失败', icon: 'none' })
    }
  }

  const handleStop = () => {
    if (wsAbortRef.current) {
      wsAbortRef.current.abort()
      wsAbortRef.current = null
    }
    setIsStreaming(false)
    setMessages(prev => {
      const last = prev[prev.length - 1]
      if (last && last.role === 'assistant') {
        return [...prev.slice(0, -1), { ...last, isStreaming: false }]
      }
      return prev
    })
    Taro.showToast({ title: '已停止生成', icon: 'none' })
  }

  const handleNewChat = async () => {
    if (isStreaming) {
      Taro.showToast({ title: '请先生成完成', icon: 'none' })
      return
    }
    try {
      await resetSession('main')
      setMessages([])
      Taro.showToast({ title: '已新建对话', icon: 'success' })
    } catch (err: any) {
      Taro.showToast({ title: '新建失败', icon: 'none' })
    }
  }

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

  return (
    <View className='openclaw-page'>
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

      {/* 消息列表 */}
      {messages.length === 0 ? (
        <View className='empty-state'>
          <View className='empty-icon-wrapper'>
            <View className='empty-icon-circle' />
          </View>
          <Text className='empty-title'>OpenClaw AI 助手</Text>
          <Text className='empty-desc'>输入消息开始对话</Text>
        </View>
      ) : (
        <ScrollView
          className='chat-scroll'
          scrollY
          scrollWithAnimation
          scrollTop={scrollTop}
        >
          <View className='messages-list'>
            {messages.map((msg) => (
              <View key={msg.id} className={`message-row ${msg.role === 'user' ? 'message-row-user' : 'message-row-assistant'}`}>
                {/* 头像 */}
                <View className={`message-avatar ${msg.role === 'user' ? 'avatar-user' : 'avatar-assistant'}`}>
                  <image
                    className='avatar-image'
                    src={msg.role === 'user' ? DEFAULT_USER_AVATAR : DEFAULT_AI_AVATAR}
                    mode='aspectFit'
                  />
                </View>
                {/* 消息内容 */}
                <View className='message-content'>
                  <View className={`message-bubble ${msg.role === 'user' ? 'bubble-user' : 'bubble-assistant'}`}>
                    {msg.role === 'user' ? (
                      <Text className='message-text' userSelect>{msg.content}</Text>
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
          </View>
        </ScrollView>
      )}

      {/* 输入区域 */}
      <View className='input-area'>
        <View className='input-wrapper'>
          <Textarea
            className='chat-input'
            value={inputValue}
            onInput={(e) => setInputValue(e.detail.value)}
            placeholder='输入消息...'
            maxlength={4000}
            autoHeight
            maxHeight={200}
            disabled={isStreaming || !connected}
            confirmType='send'
            onConfirm={handleSend}
            adjustPosition={false}
          />
        </View>
        {isStreaming ? (
          <button className='stop-btn' onClick={handleStop}>
            停止
          </button>
        ) : (
          <button
            className={`send-btn ${!inputValue.trim() ? 'disabled' : ''}`}
            disabled={!inputValue.trim() || !connected}
            onClick={handleSend}
          >
            发送
          </button>
        )}
      </View>
    </View>
  )
}
