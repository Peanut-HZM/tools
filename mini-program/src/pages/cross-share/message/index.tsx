import { useState, useEffect } from 'react'
import Taro, { useDidShow } from '@tarojs/taro'
import { View, Text, ScrollView, Button } from '@tarojs/components'
import { messageApi, deviceApi } from '../../../services/crossShare'
import type { Message } from '../../../types/crossShare'
import { formatDateTime, detectContentType, isUrl } from '../../../utils'
import { useAuthGuard } from '../../../hooks'
import Loading from '../../../components/Loading'
import EmptyState from '../../../components/EmptyState'
import './index.scss'

const COLLAPSE_HEIGHT = 400 // 折叠高度阈值（rpx）
const JSON_COLLAPSE_LINES = 10 // JSON 折叠行数阈值

export default function CrossShareMessage() {
  useAuthGuard()

  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [inputValue, setInputValue] = useState('')
  const [sending, setSending] = useState(false)
  const [deviceId, setDeviceId] = useState<string | null>(null)
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set())
  const [collapsibleMessages, setCollapsibleMessages] = useState<Set<string>>(new Set())
  const [showScrollButton, setShowScrollButton] = useState(false)
  const [jsonExpandedMessages, setJsonExpandedMessages] = useState<Set<string>>(new Set())

  useDidShow(() => {
    loadMessages()
    initDevice()
  })

  // 初始化设备
  const initDevice = async () => {
    const savedDeviceId = Taro.getStorageSync('device_id')
    if (savedDeviceId) {
      setDeviceId(savedDeviceId)
      try {
        await deviceApi.pingDevice(savedDeviceId)
      } catch (err) {
        registerNewDevice()
      }
    } else {
      registerNewDevice()
    }
  }

  // 注册新设备
  const registerNewDevice = async () => {
    try {
      const systemInfo = Taro.getSystemInfoSync()
      const deviceName = `${systemInfo.model || 'Mobile'} - 小程序`
      const deviceToken = `mini_program_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
      const device = await deviceApi.registerDevice(deviceName, deviceToken, 'mobile')
      setDeviceId(device.id)
      Taro.setStorageSync('device_id', device.id)
    } catch (err) {
      console.error('Failed to register device:', err)
    }
  }

  // 加载消息
  const loadMessages = async () => {
    try {
      const data = await messageApi.getMessages(100, 0)
      setMessages(data.reverse())
    } catch (err) {
      console.error('Failed to load messages:', err)
    } finally {
      setLoading(false)
    }
  }

  // 检查消息内容高度，确定是否需要折叠
  useEffect(() => {
    const checkContentHeight = () => {
      const newCollapsible = new Set<string>()
      messages.forEach(msg => {
        // 简单估算：每行约 40rpx，超过 15 行且内容长度超过 500 字符才需要折叠
        const content = msg.content || ''
        const lines = content.split('\n').length
        if (lines > 15 && content.length > 500) {
          newCollapsible.add(msg.id)
        }
      })
      setCollapsibleMessages(newCollapsible)
    }

    const timer = setTimeout(checkContentHeight, 100)
    return () => clearTimeout(timer)
  }, [messages])

  // 发送消息
  const handleSend = async () => {
    if (!inputValue.trim() || sending) return

    setSending(true)
    try {
      let messageType = 'text'
      if (isUrl(inputValue.trim())) {
        messageType = 'link'
      }

      await messageApi.sendMessage(inputValue.trim(), messageType)
      setInputValue('')
      await loadMessages()
      Taro.showToast({ title: '发送成功', icon: 'success', duration: 1500 })
    } catch (err: any) {
      const msg = err.message || err.data?.detail || '发送失败'
      Taro.showToast({ title: msg, icon: 'none' })
    } finally {
      setSending(false)
    }
  }

  // 删除消息
  const handleDelete = async (messageId: string) => {
    Taro.showModal({
      title: '确认删除',
      content: '确定要删除这条消息吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await messageApi.deleteMessage(messageId)
            await loadMessages()
            Taro.showToast({ title: '已删除', icon: 'success' })
          } catch (err) {
            Taro.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  }

  // 复制消息内容
  const handleCopy = async (content: string) => {
    try {
      await Taro.setClipboardData({ data: content })
      Taro.showToast({ title: '已复制', icon: 'success' })
    } catch (err) {
      Taro.showToast({ title: '复制失败', icon: 'none' })
    }
  }

  // 切换消息展开/折叠
  const toggleExpand = (messageId: string) => {
    setExpandedMessages(prev => {
      const next = new Set(prev)
      if (next.has(messageId)) {
        next.delete(messageId)
      } else {
        next.add(messageId)
      }
      return next
    })
  }

  // 切换 JSON 展开/折叠
  const toggleJsonExpand = (messageId: string) => {
    setJsonExpandedMessages(prev => {
      const next = new Set(prev)
      if (next.has(messageId)) {
        next.delete(messageId)
      } else {
        next.add(messageId)
      }
      return next
    })
  }

  // 滚动到底部
  const scrollToBottom = () => {
    Taro.createSelectorQuery()
      .select('.messages-scroll')
      .boundingClientRect()
      .exec()
  }

  // 渲染 JSON 内容
  const renderJsonContent = (content: string, messageId: string) => {
    const isJsonExpanded = jsonExpandedMessages.has(messageId)
    let formattedJson = content
    let lineCount = 0

    try {
      const parsed = JSON.parse(content)
      formattedJson = JSON.stringify(parsed, null, 2)
      lineCount = formattedJson.split('\n').length
    } catch {
      lineCount = content.split('\n').length
    }

    const displayLines = !isJsonExpanded && lineCount > JSON_COLLAPSE_LINES
      ? formattedJson.split('\n').slice(0, JSON_COLLAPSE_LINES).join('\n')
      : formattedJson

    return (
      <View className='json-block'>
        <View className='json-header'>
          <Text className='json-label'>JSON</Text>
          {lineCount > JSON_COLLAPSE_LINES && (
            <Text className='json-lines'>
              {isJsonExpanded ? `共 ${lineCount} 行` : `前 ${JSON_COLLAPSE_LINES} 行 / 共 ${lineCount} 行`}
            </Text>
          )}
        </View>
        <Text className='json-text' selectable>{displayLines}</Text>
        {!isJsonExpanded && lineCount > JSON_COLLAPSE_LINES && (
          <View className='json-expand-btn' onClick={() => toggleJsonExpand(messageId)}>
            <Text className='expand-text'>点击展开查看完整内容 ({lineCount} 行)</Text>
          </View>
        )}
      </View>
    )
  }

  // 渲染代码内容
  const renderCodeContent = (content: string) => {
    // 提取代码块（去除 ``` 标记）
    const codeMatch = content.match(/^```[\w]*\n([\s\S]*?)```$/s)
    const code = codeMatch ? codeMatch[1] : content

    return (
      <View className='code-block'>
        <Text className='code-text' selectable>{code}</Text>
      </View>
    )
  }

  // 渲染 Markdown/文本内容（简化版）
  const renderMarkdownContent = (content: string, messageId: string) => {
    const isExpanded = expandedMessages.has(messageId)
    const needsCollapse = collapsibleMessages.has(messageId)

    // 简单的 Markdown 渲染：处理标题、列表、代码块
    const lines = content.split('\n')
    const renderedLines = lines.map((line, index) => {
      // 标题
      if (line.startsWith('# ')) {
        return <Text key={index} className='md-h1'>{line.slice(2)}</Text>
      }
      if (line.startsWith('## ')) {
        return <Text key={index} className='md-h2'>{line.slice(3)}</Text>
      }
      if (line.startsWith('### ')) {
        return <Text key={index} className='md-h3'>{line.slice(4)}</Text>
      }
      // 列表
      if (line.startsWith('- ') || line.startsWith('* ')) {
        return (
          <View key={index} className='md-list-item'>
            <Text className='md-list-bullet'>•</Text>
            <Text className='md-list-text'>{line.slice(2)}</Text>
          </View>
        )
      }
      // 有序列表
      const orderedMatch = line.match(/^(\d+)\. (.*)/)
      if (orderedMatch) {
        return (
          <View key={index} className='md-list-item'>
            <Text className='md-list-number'>{orderedMatch[1]}.</Text>
            <Text className='md-list-text'>{orderedMatch[2]}</Text>
          </View>
        )
      }
      // 空行
      if (line.trim() === '') {
        return <View key={index} className='md-empty-line' />
      }
      // 普通文本
      return <Text key={index} className='md-text'>{line}</Text>
    })

    return (
      <View className={`markdown-content ${!isExpanded && needsCollapse ? 'collapsed' : ''}`}>
        {renderedLines}
        {!isExpanded && needsCollapse && (
          <View className='markdown-gradient'>
            <View className='expand-btn' onClick={() => toggleExpand(messageId)}>
              <Text className='expand-text'>展开</Text>
              <Text className='expand-arrow'>▼</Text>
            </View>
          </View>
        )}
      </View>
    )
  }

  // 渲染消息内容
  const renderMessageContent = (msg: Message) => {
    const content = msg.content || ''
    const contentType = detectContentType(content)

    if (contentType === 'json') {
      return renderJsonContent(content, msg.id)
    }

    if (contentType === 'code') {
      return renderCodeContent(content)
    }

    // Markdown 或普通文本
    return renderMarkdownContent(content, msg.id)
  }

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'text': return '💬'
      case 'file': return '📎'
      case 'link': return '🔗'
      case 'clipboard': return '📋'
      case 'image': return '🖼️'
      default: return '💬'
    }
  }

  return (
    <View className='message-page'>
      {/* 消息列表 */}
      {loading ? (
        <Loading text='加载消息...' />
      ) : messages.length === 0 ? (
        <EmptyState
          icon='💬'
          title='暂无消息'
          description='发送一条消息开始跨设备同步'
        />
      ) : (
        <ScrollView
          className='messages-scroll'
          scrollY
          scrollWithAnimation
          onScroll={(e) => {
            // 检测是否在底部
            const { scrollTop, scrollHeight, clientHeight } = e.detail
            const isAtBottom = scrollHeight - scrollTop - clientHeight < 100
            setShowScrollButton(!isAtBottom)
          }}
        >
          <View className='messages-list'>
            {messages.map((msg) => (
              <View key={msg.id} className='message-item'>
                <View className='message-header'>
                  <Text className='message-icon'>{getMessageIcon(msg.message_type)}</Text>
                  <Text className='message-time'>{formatDateTime(msg.created_at)}</Text>
                </View>
                <View className='message-bubble'>
                  {renderMessageContent(msg)}
                  <View className='message-actions'>
                    <Text
                      className='action-btn'
                      onClick={() => handleCopy(msg.content || '')}
                    >
                      复制
                    </Text>
                    <Text
                      className='action-btn action-delete'
                      onClick={() => handleDelete(msg.id)}
                    >
                      删除
                    </Text>
                  </View>
                </View>
              </View>
            ))}
          </View>

          {/* 滚动到底部按钮 */}
          {showScrollButton && (
            <View className='scroll-bottom-btn' onClick={scrollToBottom}>
              <Text className='scroll-bottom-text'>滚动到底部</Text>
            </View>
          )}
        </ScrollView>
      )}

      {/* 输入框 */}
      <View className='input-area'>
        <View className='input-wrapper'>
          <input
            className='message-input'
            value={inputValue}
            onInput={(e) => setInputValue(e.detail.value)}
            placeholder='输入消息... (支持 Markdown)'
            disabled={sending}
            confirmType='send'
            onConfirm={handleSend}
          />
        </View>
        <button
          className={`send-btn ${!inputValue.trim() || sending ? 'disabled' : ''}`}
          disabled={!inputValue.trim() || sending}
          onClick={handleSend}
        >
          {sending ? '发送中' : '发送'}
        </button>
      </View>
    </View>
  )
}
