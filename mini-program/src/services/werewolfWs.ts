/**
 * 狼人杀对局 WS 封装（跨平台：weapp SocketTask / h5 Promise<SocketTask>）
 *
 * 平台差异（实测结论）：
 * - 微信小程序：Taro.connectSocket 同步返回 SocketTask；全局 onSocketMessage 可用
 * - H5（taro-h5）：connectSocket 返回 Promise<SocketTask>，全局 onSocket* 是
 *   deprecated 空函数（只打警告），必须用 task 实例回调
 * 因此统一走 task 实例回调，兼容两种返回形态。25s 心跳；断线 2s/4s/8s 退避重连 3 次。
 */
import Taro from '@tarojs/taro'
import { API_BASE_URL } from './request'

type Handlers = {
  onMessage: (msg: any) => void
  onClose?: () => void
}

type SocketTaskLike = {
  onOpen: (cb: () => void) => void
  onMessage: (cb: (res: { data: string }) => void) => void
  onError: (cb: () => void) => void
  onClose: (cb: () => void) => void
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
  // API_BASE_URL 形如 https://host/api 或 http://127.0.0.1:19092/api
  const base = API_BASE_URL.replace(/^http/, 'ws').replace(/\/api$/, '')
  return `${base}/api/games/werewolf/rooms/${roomId}/ws?token=${encodeURIComponent(token)}`
}

function startHeartbeat() {
  stopHeartbeat()
  heartbeatTimer = setInterval(() => {
    werewolfWs.send(JSON.stringify({ type: 'ping' }))
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
  if (manuallyClosed || !currentRoomId || !currentHandlers) return
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
      // 非 JSON 消息忽略
    }
  })
  socketTask.onError(() => {
    reject(new Error('ws error'))
  })
  socketTask.onClose(() => {
    stopHeartbeat()
    scheduleReconnect()
  })
}

export function connect(roomId: string, handlers: Handlers): Promise<void> {
  currentHandlers = handlers
  currentRoomId = roomId
  retryCount = 0
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
      // h5：Promise<SocketTask>
      result.then(
        (socketTask: SocketTaskLike) => bindTask(socketTask, handlers, resolve, reject),
        (err: any) => reject(new Error(err?.errMsg || 'connectSocket fail')),
      )
    } else if (result && typeof result.onMessage === 'function') {
      // weapp：同步返回 SocketTask
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
    // 连接断开时静默，由重连机制恢复
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

export const werewolfWs = { connect, send, close }
