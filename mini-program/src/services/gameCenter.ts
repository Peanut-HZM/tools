import { request } from './request'

/** 游戏接口统一错误处理：后端 4xx 返回 {detail} 错误体，须转为异常（request 只拦 401） */
async function gameRequest<T>(url: string,
                              options: { method?: 'GET' | 'POST'; data?: any } = {}): Promise<T> {
  const res = await request<any>(url, options)
  if (res && typeof res === 'object' && res.detail) {
    throw new Error(typeof res.detail === 'string' ? res.detail : '请求失败')
  }
  return res as T
}

export interface BoardInfo {
  id: string
  name: string
  player_count: number
  roles: Record<string, number>
}

export interface MemberInfo {
  user_id: string
  nickname: string
  connected: boolean
  is_host: boolean
  seat: number
}

export interface RoomView {
  room_id: string
  status: 'WAITING' | 'PLAYING' | 'RESULT'
  host_id: string
  board: BoardInfo
  settings: Record<string, any>
  capacity: number
  members: MemberInfo[]
  snapshot?: any
}

export const gameApi = {
  /** 预置板子与可配置项元数据 */
  getBoards: () => request<{ boards: BoardInfo[]; presets: Record<string, any> }>(
    '/games/werewolf/boards'),
  /** 创建房间 */
  createRoom: (payload: {
    board_id?: string
    custom_roles?: Record<string, number>
    board_name?: string
    speech_seconds?: number
    witch_self_rescue?: string
    witch_guard_conflict?: boolean
  }) => gameRequest<{ room_id: string }>('/games/werewolf/rooms', { method: 'POST', data: payload }),
  /** 加入房间 */
  joinRoom: (roomId: string) =>
    gameRequest(`/games/werewolf/rooms/${roomId}/join`, { method: 'POST' }),
  /** 离开房间 */
  leaveRoom: (roomId: string) =>
    gameRequest(`/games/werewolf/rooms/${roomId}/leave`, { method: 'POST' }),
  /** 踢人（房主） */
  kickMember: (roomId: string, userId: string) =>
    gameRequest(`/games/werewolf/rooms/${roomId}/kick`, { method: 'POST', data: { user_id: userId } }),
  /** 修改配置（房主，等待阶段） */
  updateConfig: (roomId: string, payload: Record<string, any>) =>
    gameRequest(`/games/werewolf/rooms/${roomId}/config`, { method: 'POST', data: payload }),
  /** 开始对局（房主） */
  startGame: (roomId: string) =>
    gameRequest(`/games/werewolf/rooms/${roomId}/start`, { method: 'POST' }),
  /** 再来一局（房主，结算后） */
  replay: (roomId: string) =>
    gameRequest(`/games/werewolf/rooms/${roomId}/replay`, { method: 'POST' }),
  /** 解散房间（房主） */
  dismiss: (roomId: string) =>
    gameRequest(`/games/werewolf/rooms/${roomId}/dismiss`, { method: 'POST' }),
  /** 个人视角房间快照（断线重连兜底） */
  getRoom: (roomId: string) =>
    gameRequest<RoomView>(`/games/werewolf/rooms/${roomId}`),
}
