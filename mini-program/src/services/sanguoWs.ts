/** 三国杀 WS 封装（与狼人杀同款平台兼容策略：SocketTask 实例回调，兼容 weapp/h5） */
import Taro from '@tarojs/taro'
import { API_BASE_URL } from './request'

type Handlers = {
  onMessage: (msg: any) => void
  onClose?: (code?: number) => void
}

type SocketTaskLike = {
  onOpen: (cb: () => void) => void
  onMessage: (cb: (res: { data: string }) => void) => void
  onError: (cb: () => void) => void
  onClose: (cb: (res?: { code?: number }) => void) => void
  send: (opts: { data: string }) => void
  close: (opts?: { code?: number }) => void
}

let task: SocketTaskLike | null = null
let heartbeatTimer: ReturnType<typeof setInterval> | null = null
let currentHandlers: Handlers | null = null
let currentRoomId: string | null = null
let retryCount = 0
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let manuallyClosed = false

function buildWsUrl(roomId: string): string {
  const token = Taro.getStorageSync('auth_token') || ''
  const base = API_BASE_URL.replace(/^http/, 'ws').replace(/\/api$/, '')
  return `${base}/api/games/sanguo/rooms/${roomId}/ws?token=${encodeURIComponent(token)}`
}

function startHeartbeat() {
  stopHeartbeat()
  heartbeatTimer = setInterval(() => {
    sanguoWs.send(JSON.stringify({ type: 'ping' }))
  }, 25000)
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

function scheduleReconnect(closeCode?: number) {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (manuallyClosed || !currentRoomId || !currentHandlers) return
  if (closeCode === 4401 || closeCode === 4404) {
    currentHandlers.onClose?.(closeCode)
    currentRoomId = null
    return
  }
  if (retryCount >= 3) {
    currentHandlers.onClose?.(closeCode)
    currentRoomId = null
    return
  }
  retryCount += 1
  const delay = 2000 * Math.pow(2, retryCount - 1)
  const roomId = currentRoomId
  const handlers = currentHandlers
  reconnectTimer = setTimeout(() => {
    connectInternal(roomId, handlers).catch(() => {})
  }, delay)
}

function bindTask(socketTask: SocketTaskLike, handlers: Handlers,
                 resolve: () => void, reject: (e: Error) => void) {
  task = socketTask
  socketTask.onOpen(() => {
    startHeartbeat()
    resolve()
  })
  socketTask.onMessage((res) => {
    try {
      handlers.onMessage(JSON.parse(res.data))
    } catch {
      // 非 JSON 忽略
    }
  })
  socketTask.onError(() => reject(new Error('ws error')))
  socketTask.onClose((res) => {
    stopHeartbeat()
    scheduleReconnect(res?.code)
  })
}

export function connect(roomId: string, handlers: Handlers): Promise<void> {
  retryCount = 0
  return connectInternal(roomId, handlers)
}

function connectInternal(roomId: string, handlers: Handlers): Promise<void> {
  currentHandlers = handlers
  currentRoomId = roomId
  manuallyClosed = false
  return new Promise((resolve, reject) => {
    let result: any
    try {
      result = Taro.connectSocket({ url: buildWsUrl(roomId) })
    } catch (e: any) {
      reject(e)
      return
    }
    if (result && typeof result.then === 'function') {
      result.then(
        (socketTask: SocketTaskLike) => bindTask(socketTask, handlers, resolve, reject),
        (err: any) => reject(new Error(err?.errMsg || 'connectSocket fail')),
      )
    } else if (result && typeof result.onMessage === 'function') {
      bindTask(result as SocketTaskLike, handlers, resolve, reject)
    } else {
      reject(new Error('connectSocket 返回了不支持的形态'))
    }
  })
}

export function send(data: any) {
  const payload = typeof data === 'string' ? data : JSON.stringify(data)
  try {
    task?.send({ data: payload })
  } catch {
    // 断线静默
  }
}

export function close() {
  manuallyClosed = true
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

export const sanguoWs = { connect, send, close }
