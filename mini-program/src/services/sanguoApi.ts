/** 三国杀服务 API */
import { request } from './request'

export interface SanguoRecordListItem {
  id: number
  room_id: string
  board_name: string
  player_count: number
  winner: 'LORD' | 'REBEL' | 'SPY'
  turn_count: number
  duration_seconds: number
  created_at: string | null
}

export interface SanguoTimelineItem {
  seq: number
  kind: 'event' | 'judge'
  day?: number
  text?: string
  phase?: string
  for?: string
  suit?: string
  point?: number
}

export interface SanguoRecordDetail {
  record: {
    id: number
    room_id: string
    board_name: string
    player_count: number
    winner: string
    turn_count: number
    duration_seconds: number
    config: Record<string, any>
    timeline: { timeline: SanguoTimelineItem[] }
    created_at: string | null
  }
}

export const sanguoApi = {
  /** 武将列表 */
  getHeroes: () => request<{ heroes: {
    key: string; name: string; kingdom: string
    max_hp: number; skills: string[]; gender: string
  }[] }>('/games/sanguo/heroes'),
  /** 创建房间 */
  createRoom: () => request<{ room_id: string }>('/games/sanguo/rooms', { method: 'POST' }),
  /** 加入房间 */
  joinRoom: (roomId: string) =>
    request(`/games/sanguo/rooms/${roomId}/join`, { method: 'POST' }),
  /** 离开房间 */
  leaveRoom: (roomId: string) =>
    request(`/games/sanguo/rooms/${roomId}/leave`, { method: 'POST' }),
  /** 开始对局（房主） */
  startGame: (roomId: string) =>
    request(`/games/sanguo/rooms/${roomId}/start`, { method: 'POST' }),
  /** 再来一局（房主） */
  replay: (roomId: string) =>
    request(`/games/sanguo/rooms/${roomId}/replay`, { method: 'POST' }),
  /** 解散房间（房主） */
  dismiss: (roomId: string) =>
    request(`/games/sanguo/rooms/${roomId}/dismiss`, { method: 'POST' }),
  /** 房间快照 */
  getRoom: (roomId: string) => request<any>(`/games/sanguo/rooms/${roomId}`),
  /** 对局记录列表 */
  listRecords: (limit = 20, offset = 0) =>
    request<{ total: number; records: SanguoRecordListItem[] }>(
      `/games/sanguo/records?limit=${limit}&offset=${offset}`),
  /** 对局记录详情（含回放） */
  getRecord: (recordId: number) =>
    request<SanguoRecordDetail>(`/games/sanguo/records/${recordId}`),
}
