/** store 消息归约测试（mock 掉 werewolfWs，不依赖 Taro 运行时） */
import { describe, expect, it, vi, beforeEach } from 'vitest'

const sendSpy = vi.fn()
const closeSpy = vi.fn()
const connectSpy = vi.fn()

vi.mock('../../services/werewolfWs', () => ({
  werewolfWs: {
    connect: (roomId: string, handlers: any) => {
      connectSpy(roomId, handlers)
      return Promise.resolve()
    },
    send: (data: any) => sendSpy(data),
    close: () => closeSpy(),
  },
}))

import { useWerewolfStore } from '../werewolf'

function msgHandler(): (m: any) => void {
  useWerewolfStore.getState().connect('123456')
  return connectSpy.mock.calls.at(-1)![1].onMessage
}

describe('werewolf store', () => {
  beforeEach(() => {
    useWerewolfStore.getState().disconnect()
    useWerewolfStore.setState({ view: null, lastError: null })
    sendSpy.mockClear()
    connectSpy.mockClear()
  })

  it('hello 消息写入 view', () => {
    const onMessage = msgHandler()
    onMessage({ type: 'hello', state: { phase: 'NIGHT_WEREWOLF', day: 1, players: [], you: { role: 'WEREWOLF' } } })
    expect(useWerewolfStore.getState().view?.phase).toBe('NIGHT_WEREWOLF')
    expect(useWerewolfStore.getState().view?.you.role).toBe('WEREWOLF')
  })

  it('event 消息追加 log 并去重', () => {
    const onMessage = msgHandler()
    onMessage({ type: 'hello', state: { phase: 'DAWN', log: [{ id: 1, text: 'a' }] } })
    onMessage({ type: 'event', id: 2, text: 'b' })
    onMessage({ type: 'event', id: 2, text: 'b' })  // 重复消息应被去重
    const log = useWerewolfStore.getState().view!.log
    expect(log.map((e: any) => e.id)).toEqual([1, 2])
  })

  it('room 消息更新等待页成员列表', () => {
    const onMessage = msgHandler()
    onMessage({ type: 'hello', state: { room_id: '1', status: 'WAITING',
      members: [{ user_id: '1', nickname: '甲', seat: 1 }] } })
    onMessage({ type: 'room', room: { room_id: '1', status: 'WAITING',
      members: [{ user_id: '1', nickname: '甲', seat: 1 },
                { user_id: '2', nickname: '乙', seat: 2 }] } })
    const view = useWerewolfStore.getState().view!
    expect(view.members).toHaveLength(2)
    expect(view.members[1].nickname).toBe('乙')
  })

  it('sendAct 转发到 ws', () => {
    msgHandler()
    useWerewolfStore.getState().sendAct('werewolf_kill', 3)
    expect(sendSpy).toHaveBeenCalledWith({ type: 'act', action: 'werewolf_kill', target: 3 })
  })

  it('error 消息写入 lastError', () => {
    const onMessage = msgHandler()
    onMessage({ type: 'error', code: 'NOT_YOUR_TURN', message: '还没轮到你' })
    expect(useWerewolfStore.getState().lastError).toBe('还没轮到你')
  })

  it('game_over 消息写入 winner 与 reveal', () => {
    const onMessage = msgHandler()
    onMessage({ type: 'hello', state: { phase: 'DAY_VOTE', you: {} } })
    onMessage({ type: 'game_over', winner: 'VILLAGER', reveal: [{ seat: 1, role: 'WEREWOLF', alive: false }] })
    const snap = useWerewolfStore.getState().view!
    expect(snap.winner).toBe('VILLAGER')
    expect(snap.reveal).toHaveLength(1)
  })

  it('seer_result 私有消息追加查验记录', () => {
    const onMessage = msgHandler()
    onMessage({ type: 'hello', state: { phase: 'NIGHT_SEER', you: { role: 'SEER', checks: [] } } })
    onMessage({ type: 'private', kind: 'seer_result', target: 4, is_werewolf: false })
    const you = useWerewolfStore.getState().view!.you
    expect(you.checks).toEqual([{ seat: 4, is_werewolf: false }])
  })
})
