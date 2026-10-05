/**
 * 狼人杀对局 WS 封装
 * 使用 Taro 全局 socket API（SocketTask 兼容问题，沿用 openclaw.ts 的结论）：
 * 25s 心跳 ping；断线后 2s/4s/8s 退避重连 3 次。
 */
import Taro from '@tarojs/taro'
import { API_BASE_URL } from './request'

type Handlers = {
  onMessage: (msg: any) => void
  onClose?: () => void
}

let heartbeatTimer: ReturnType<typeof setInterval> | null = null
let currentHandlers: Handlers | null = null
let currentRoomId: string | null = null
let retryCount = 0
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

function buildWsUrl(roomId: string): string {
  const token = Taro.getStorageSync('auth_token') || ''
  // API_BASE_URL 形如 https://host/api 或 http://127.0.0.1:19092/api
  const base = API_BASE_URL.replace(/^http/, 'ws').replace(/\/api$/, '')
  return `${base}/api/games/werewolf/rooms/${roomId}/ws?token=${encodeURIComponent(token)}`
}

function startHeartbeat() {
  stopHeartbeat()
  heartbeatTimer = setInterval(() => {
    try {
      task?.send({ data: JSON.stringify({ type: 'ping' }) })
    } catch {
      // 发送失败由 onClose 触发重连
    }
  }, 25000)
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

function scheduleReconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (!currentRoomId || !currentHandlers) return
  if (retryCount >= 3) {
    currentHandlers.onClose?.()
    currentRoomId = null
    return
  }
  retryCount += 1
  const delay = 2000 * Math.pow(2, retryCount - 1)
  const roomId = currentRoomId
  const handlers = currentHandlers
  reconnectTimer = setTimeout(() => {
    connect(roomId, handlers).catch(() => {})
  }, delay)
}

let task: Taro.SocketTask | null = null

export function connect(roomId: string, handlers: Handlers): Promise<void> {
  currentHandlers = handlers
  currentRoomId = roomId
  retryCount = 0
  return new Promise((resolve, reject) => {
    try {
      task = Taro.connectSocket({
        url: buildWsUrl(roomId),
        fail: (err) => reject(new Error(err.errMsg || '连接失败')),
      })
      Taro.onSocketOpen(() => {
        startHeartbeat()
        resolve()
      })
      Taro.onSocketMessage((res) => {
        try {
          handlers.onMessage(JSON.parse(res.data))
        } catch {
          // 非 JSON 消息忽略
        }
      })
      Taro.onSocketError(() => {
        reject(new Error('ws error'))
      })
      Taro.onSocketClose(() => {
        stopHeartbeat()
        scheduleReconnect()
      })
    } catch (e: any) {
      reject(e)
    }
  })
}

export function send(data: any) {
  try {
    task?.send({ data: JSON.stringify(data) })
  } catch {
    // 连接断开时静默，由重连机制恢复
  }
}

export function close() {
  currentRoomId = null
  currentHandlers = null
  stopHeartbeat()
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  try {
    task?.close({})
  } catch {
    // 已关闭
  }
  task = null
}

export const werewolfWs = { connect, send, close }
