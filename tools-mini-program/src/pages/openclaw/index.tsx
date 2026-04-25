import { useState, useRef } from 'react'
import Taro, { useDidShow, useDidHide } from '@tarojs/taro'
import { View, Text, ScrollView, Textarea } from '@tarojs/components'
import { chatStream, resetSession, getStatus, abortChat, loadHistory } from '../../services/openclaw'
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
  const abortRef = useRef(false)

  useDidShow(() => {
    checkStatus()
    loadMessages()
  })

  // 页面隐藏时中止生成
  useDidHide(() => {
    if (isStreaming) {
      abortChat('main').catch(() => {})
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

  const scrollToBottom = () => {
    setScrollTop(Date.now())
  }

  const handleSend = async () => {
    if (!inputValue.trim() || isStreaming) return

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      timestamp: Date.now()
    }

    const assistantMessage: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isStreaming: true
    }

    setMessages(prev => [...prev, userMessage, assistantMessage])
    setInputValue('')
    setIsStreaming(true)
    abortRef.current = false
    scrollToBottom()

    try {
      await chatStream(
        userMessage.content,
        'main',
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
        () => {
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [...prev.slice(0, -1), { ...last, isStreaming: false }]
            }
            return prev
          })
          setIsStreaming(false)
        },
        (error: string) => {
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [...prev.slice(0, -1), {
                ...last,
                content: last.content ? `${last.content}\n\n[生成失败] ${error}` : `[生成失败] ${error}`,
                isStreaming: false
              }]
            }
            return prev
          })
          setIsStreaming(false)
        }
      )
    } catch (err: any) {
      setIsStreaming(false)
      Taro.showToast({ title: err.message || '发送失败', icon: 'none' })
    }
  }

  const handleStop = async () => {
    abortRef.current = true
    try {
      await abortChat('main')
    } catch (err) {
      console.error('中止请求失败:', err)
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
            disabled={isStreaming || !connected}
            confirmType='send'
            onConfirm={handleSend}
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
