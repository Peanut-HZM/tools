import Taro from '@tarojs/taro'
import { getHeaders, API_BASE_URL } from './request'

/**
 * OpenClaw 流式对话
 * 使用 enableChunked + onChunkReceived 接收 SSE 流
 */
export async function chatStream(
  message: string,
  sessionKey: string = 'main',
  onChunk: (chunk: string) => void,
  onDone?: () => void,
  onError?: (error: string) => void
): Promise<void> {
  const token = Taro.getStorageSync('auth_token')
  const header: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) {
    header['Authorization'] = `Bearer ${token}`
  }

  let buffer = ''
  let chunkCount = 0
  let hasContent = false

  console.log('[chatStream] 开始请求，消息:', message.substring(0, 50))

  // 处理一行 SSE data，提取 content
  const processSSELine = (trimmed: string) => {
    if (!trimmed || trimmed.startsWith(':')) return
    if (!trimmed.startsWith('data: ')) return

    const jsonStr = trimmed.slice(6).trim()
    if (!jsonStr) return

    try {
      const data = JSON.parse(jsonStr)
      console.log('[chatStream] 解析到 SSE 数据:', data.type, data.content ? data.content.substring(0, 50) : '')
      if (data.type === 'chunk' && data.content) {
        chunkCount++
        hasContent = true
        onChunk(data.content)
      } else if (data.type === 'error') {
        onError?.(data.message || '服务端错误')
      } else if (data.type === 'done') {
        console.log('[chatStream] 收到 done 信号')
      }
    } catch (e) {
      console.warn('[chatStream] JSON 解析失败，保留到 buffer:', trimmed.substring(0, 100))
      // JSON 不完整，保留到 buffer
      buffer = trimmed + '\n' + buffer
    }
  }

  // 分块数据解析
  const parseChunk = (chunkText: string) => {
    buffer += chunkText
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      processSSELine(line.trim())
    }
  }

  try {
    const requestTask = Taro.request({
      url: `${API_BASE_URL}/openclaw/chat`,
      method: 'POST',
      data: { message, session_key: sessionKey },
      header,
      timeout: 120000,
      enableChunked: true,
      success: (res) => {
        console.log('[chatStream] success 回调触发，statusCode:', res.statusCode)
        // 处理 buffer 剩余数据
        if (buffer.trim()) {
          console.log('[chatStream] 处理 buffer 剩余数据，长度:', buffer.length)
          parseChunk('\n')
        }
        // 兜底：如果 onChunkReceived 没有触发，尝试从完整响应中解析
        if (!hasContent && res.data) {
          console.log('[chatStream] 兜底：从完整响应中解析')
          const respStr = typeof res.data === 'string' ? res.data : JSON.stringify(res.data)
          if (respStr && respStr.includes('data:')) {
            respStr.split('\n').forEach(line => processSSELine(line.trim()))
          }
        }
        console.log(`[chatStream] 完成，共收到 ${chunkCount} 个 chunk`)
        onDone?.()
      },
      fail: (err) => {
        console.error('[chatStream] 请求失败', err)
        onError?.(err.errMsg || '请求失败')
      }
    })

    console.log('[chatStream] requestTask 创建成功，onChunkReceived:', !!requestTask.onChunkReceived)

    // 分块数据回调
    if (requestTask.onChunkReceived) {
      requestTask.onChunkReceived((res: any) => {
        try {
          let chunkText: string
          if (typeof res.data === 'string') {
            chunkText = res.data
          } else if (res.data instanceof ArrayBuffer) {
            chunkText = arrayBufferToString(res.data)
          } else {
            chunkText = String(res.data)
          }
          console.log('[onChunkReceived] 收到数据，长度:', chunkText.length, '内容预览:', chunkText.substring(0, 100))
          parseChunk(chunkText)
        } catch (e) {
          console.error('[SSE Parse Error]', e)
        }
      })
    } else {
      console.warn('[chatStream] onChunkReceived 不可用，将等待完整响应')
    }
  } catch (err: any) {
    console.error('[chatStream] 异常', err)
    onError?.(err.message || '网络异常')
  }
}

/**
 * 将 ArrayBuffer 解码为 UTF-8 字符串
 */
function arrayBufferToString(buf: ArrayBuffer): string {
  const decoder = new TextDecoder('utf-8')
  return decoder.decode(buf)
}

/** 获取会话历史 */
export async function loadHistory(sessionKey: string = 'main', limit: number = 50) {
  const res = await Taro.request({
    url: `${API_BASE_URL}/openclaw/history`,
    method: 'POST',
    data: { session_key: sessionKey, limit },
    header: getHeaders(),
    timeout: 15000
  })
  return res.data?.messages || []
}

/** 中止生成 */
export async function abortChat(sessionKey: string = 'main') {
  const res = await Taro.request({
    url: `${API_BASE_URL}/openclaw/abort`,
    method: 'POST',
    data: { session_key: sessionKey },
    header: getHeaders(),
    timeout: 10000
  })
  return res.data
}

/** 重置会话 */
export async function resetSession(sessionKey: string = 'main') {
  const res = await Taro.request({
    url: `${API_BASE_URL}/openclaw/reset?session_key=${sessionKey}`,
    method: 'POST',
    header: getHeaders(),
    timeout: 10000
  })
  return res.data
}

/** 获取状态 */
export async function getStatus() {
  const res = await Taro.request({
    url: `${API_BASE_URL}/openclaw/status`,
    method: 'GET',
    timeout: 10000
  })
  return res.data
}

/**
 * WebSocket 流式对话（小程序专用）
 * 使用 Taro 全局 WebSocket API（connectSocket / onSocketOpen / onSocketMessage）
 * 微信小程序中 connectSocket 返回 Promise<SocketTask> 但实际运行时有兼容问题，
 * 改用全局 API + 事件监听方式确保兼容
 */
export function chatWebSocket(
  message: string,
  sessionKey: string = 'main',
  onChunk: (chunk: string) => void,
  onDone?: () => void,
  onError?: (error: string) => void
): { abort: () => void } {
  let isDone = false
  let isOpened = false
  // 将 HTTP URL 转为 WebSocket URL
  const baseUrl = API_BASE_URL.replace('/api', '')
  const wsUrl = baseUrl.startsWith('https')
    ? baseUrl.replace('https', 'wss') + '/api/openclaw/chat/ws'
    : baseUrl.replace('http', 'ws') + '/api/openclaw/chat/ws'

  console.log('[chatWebSocket] 开始连接:', wsUrl)

  // 先注销旧监听器，防止重复注册
  try { Taro.offSocketOpen() } catch (_) {}
  try { Taro.offSocketMessage() } catch (_) {}
  try { Taro.offSocketError() } catch (_) {}
  try { Taro.offSocketClose() } catch (_) {}

  // 监听打开事件
  Taro.onSocketOpen(() => {
    console.log('[chatWebSocket] WebSocket 连接已打开')
    isOpened = true
    // 连接建立后发送消息
    Taro.sendSocketMessage({
      data: JSON.stringify({
        type: 'message',
        content: message,
      }),
      success: () => {
        console.log('[chatWebSocket] 消息发送成功')
      },
      fail: (err) => {
        console.error('[chatWebSocket] 消息发送失败:', err)
        if (!isDone) {
          isDone = true
          onError?.(`消息发送失败: ${JSON.stringify(err)}`)
        }
      }
    })
  })

  // 监听消息
  Taro.onSocketMessage((res) => {
    try {
      const data = typeof res.data === 'string' ? JSON.parse(res.data) : JSON.parse(String(res.data))
      console.log('[chatWebSocket] 收到消息:', data.type, data.content ? data.content.substring(0, 50) : '')

      if (data.type === 'chunk' && data.content) {
        onChunk(data.content)
      } else if (data.type === 'error') {
        if (!isDone) {
          isDone = true
          onError?.(data.message || '服务端错误')
        }
      } else if (data.type === 'done' || data.type === 'aborted') {
        if (!isDone) {
          isDone = true
          onDone?.()
          Taro.closeSocket()
        }
      } else if (data.type === 'started') {
        console.log('[chatWebSocket] 生成已开始, runId:', data.runId)
      }
    } catch (e) {
      console.error('[chatWebSocket] JSON 解析失败:', e, res.data)
    }
  })

  // 监听错误
  Taro.onSocketError((err) => {
    console.error('[chatWebSocket] 连接错误:', err)
    if (!isDone) {
      isDone = true
      onError?.(`连接错误: ${JSON.stringify(err)}`)
    }
  })

  // 监听关闭
  Taro.onSocketClose(() => {
    console.log('[chatWebSocket] 连接已关闭')
    if (!isDone) {
      isDone = true
      onError?.('连接意外关闭')
    }
  })

  // 建立连接
  Taro.connectSocket({
    url: `${wsUrl}?session_key=${encodeURIComponent(sessionKey)}`,
    success: () => {
      console.log('[chatWebSocket] 连接请求已发送')
    },
    fail: (err) => {
      console.error('[chatWebSocket] 连接请求失败:', err)
      if (!isDone) {
        isDone = true
        onError?.(`WebSocket 连接失败: ${JSON.stringify(err)}`)
      }
    }
  })

  // 返回中止函数
  return {
    abort: () => {
      if (isOpened && !isDone) {
        try {
          Taro.sendSocketMessage({
            data: JSON.stringify({ type: 'abort' }),
          })
        } catch (e) {
          console.error('[chatWebSocket] 中止发送失败:', e)
        }
      }
    }
  }
}
