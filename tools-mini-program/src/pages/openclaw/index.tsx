import { useState, useRef } from 'react'
import Taro, { useDidShow, useDidHide } from '@tarojs/taro'
import { View, Text, ScrollView, Textarea } from '@tarojs/components'
import { chatStream, resetSession, getStatus, abortChat } from '../../services/openclaw'
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

export default function OpenClawPage() {
  useAuthGuard()

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [connected, setConnected] = useState(true)
  const [scrollTop, setScrollTop] = useState(0)
  const abortRef = useRef(false)

  useDidShow(() => {
    checkStatus()
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
              return [...prev.slice(0, -1), { ...last, content: last.content + chunk }]
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

  return (
    <View className='openclaw-page'>
      {/* 顶部工具栏 */}
      <View className='toolbar'>
        <Text className='toolbar-btn' onClick={handleNewChat}>
          + 新对话
        </Text>
        {!connected && (
          <Text className='disconnected-badge'>连接断开</Text>
        )}
      </View>

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
                <View className={`message-bubble ${msg.role === 'user' ? 'bubble-user' : 'bubble-assistant'}`}>
                  {msg.role === 'user' ? (
                    <Text className='message-text' selectable>{msg.content}</Text>
                  ) : (
                    <Markdown content={msg.content} />
                  )}
                  {msg.isStreaming && <Text className='streaming-indicator'>...</Text>}
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
            disabled={isStreaming}
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
            disabled={!inputValue.trim()}
            onClick={handleSend}
          >
            发送
          </button>
        )}
      </View>
    </View>
  )
}
