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

  try {
    const requestTask = Taro.request({
      url: `${API_BASE_URL}/openclaw/chat`,
      method: 'POST',
      data: { message, session_key: sessionKey },
      header,
      timeout: 120000,
      enableChunked: true,
      success: () => {
        parseSSEBuffer(buffer, onChunk)
        onDone?.()
      },
      fail: (err) => {
        onError?.(err.errMsg || '请求失败')
      }
    })

    requestTask.onChunkReceived?.((res: any) => {
      try {
        const chunk = typeof res.data === 'string'
          ? res.data
          : arrayBufferToString(res.data)

        buffer += chunk
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || trimmed.startsWith(':')) continue
          if (trimmed.startsWith('data: ')) {
            const jsonStr = trimmed.slice(6)
            try {
              const data = JSON.parse(jsonStr)
              if (data.type === 'chunk' && data.content) {
                onChunk(data.content)
              } else if (data.type === 'error') {
                onError?.(data.message || '服务端错误')
              }
            } catch {
              buffer = trimmed + '\n' + buffer
            }
          }
        }
      } catch (e) {
        console.error('[SSE Parse Error]', e)
      }
    })
  } catch (err: any) {
    onError?.(err.message || '网络异常')
  }
}

function arrayBufferToString(buf: ArrayBuffer): string {
  const decoder = new TextDecoder('utf-8')
  return decoder.decode(buf)
}

function parseSSEBuffer(buffer: string, onChunk: (chunk: string) => void) {
  const lines = buffer.split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('data: ')) {
      try {
        const data = JSON.parse(trimmed.slice(6))
        if (data.type === 'chunk' && data.content) {
          onChunk(data.content)
        }
      } catch { /* 忽略不完整的 JSON */ }
    }
  }
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
