/**
 * 对局页渲染回归测试：捕获「条件 return 后调用 hooks」导致的
 * React #310（Rendered more hooks than during the previous render）白屏。
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'

// --- mock 平台与网络层（Room 组件的边界） ---
const useDidShowCb = { fn: () => {} }
const { showModalSpy } = vi.hoisted(() => ({ showModalSpy: vi.fn() }))
vi.mock('@tarojs/taro', () => ({
  default: {
    showToast: vi.fn(),
    showModal: showModalSpy,
    navigateBack: vi.fn(),
    getStorageSync: vi.fn(() => ''),
  },
  useRouter: () => ({ params: { room_id: '123456' } }),
  useDidShow: (fn: () => void) => { useDidShowCb.fn = fn },
  useDidHide: () => {},
}))

vi.mock('../../../../services/gameCenter', () => ({
  gameApi: new Proxy({}, { get: () => vi.fn(() => Promise.resolve({})) }),
}))

vi.mock('../../../assets/cards/back.png', () => ({ default: 'back.png' }))
vi.mock('../../../assets/cards/werewolf.png', () => ({ default: 'werewolf.png' }))
vi.mock('../../../assets/cards/villager.png', () => ({ default: 'villager.png' }))
vi.mock('../../../assets/cards/seer.png', () => ({ default: 'seer.png' }))
vi.mock('../../../assets/cards/witch.png', () => ({ default: 'witch.png' }))
vi.mock('../../../assets/cards/hunter.png', () => ({ default: 'hunter.png' }))
vi.mock('../../../assets/cards/guard.png', () => ({ default: 'guard.png' }))
vi.mock('../../../assets/cards/idiot.png', () => ({ default: 'idiot.png' }))

import { render, screen, act } from '@testing-library/react'
import React from 'react'

// @tarojs/components 为 ES class 组件，esbuild 的 JSX 转换与之不兼容；
// 渲染测试只关心页面逻辑，mock 为透传 div 的函数组件。
vi.mock('@tarojs/components', () => ({
  View: (p: any) => React.createElement('div', { onClick: p.onClick }, p.children),
  Text: (p: any) => React.createElement('span', { onClick: p.onClick }, p.children),
  Input: () => React.createElement('input'),
  ScrollView: (p: any) => React.createElement('div', null, p.children),
  Image: () => React.createElement('img'),
  Picker: (p: any) => React.createElement('div', null, p.children),
}))

import WerewolfRoom from '../../package-game/pages/werewolf/room/index'
import { useWerewolfStore } from '../../stores/werewolf'
import { useAuthStore } from '../../stores/auth'

const WAITING_VIEW = {
  room_id: '123456',
  status: 'WAITING',
  host_id: '1',
  board: { id: '6p', name: '6人新手局', player_count: 6, roles: {} },
  settings: {},
  capacity: 6,
  members: [{ user_id: '1', nickname: '甲', connected: true, is_host: true, seat: 1 }],
}

const PLAYING_VIEW = {
  ...WAITING_VIEW,
  status: 'PLAYING',
  snapshot: {
    phase: 'NIGHT_WEREWOLF',
    day: 1,
    deadline: Math.floor(Date.now() / 1000) + 30,
    players: [
      { seat: 1, nickname: '甲', alive: true, escaped: false },
      { seat: 2, nickname: '乙', alive: true, escaped: false },
    ],
    you: { seat: 1, role: 'WEREWOLF', can_vote: true, mates: [], acting: false, can: [] },
    log: [],
    speeches: [],
    pk_seats: [],
  },
}

describe('对局页渲染（hooks 顺序回归）', () => {
  beforeEach(() => {
    useWerewolfStore.setState({ view: null, lastError: null })
    useAuthStore.setState({ user: { id: '1', username: '甲', role: 'user' } as any })
  })

  it('view 从空到到达不触发 React #310，且渲染等待区', () => {
    const { container } = render(<WerewolfRoom />)
    expect(screen.getByText('连接房间中...')).toBeTruthy()
    act(() => { useWerewolfStore.setState({ view: WAITING_VIEW as any }) })
    expect(screen.getByText('房号 123456')).toBeTruthy()
    expect(container.innerHTML).not.toBe('')
  })

  it('投票阶段渲染确认按钮，可选中投票目标（C1）', () => {
    render(<WerewolfRoom />)
    const view = {
      ...PLAYING_VIEW,
      snapshot: {
        ...PLAYING_VIEW.snapshot,
        phase: 'DAY_VOTE',
        players: [
          { seat: 1, nickname: '甲', alive: true, escaped: false },
          { seat: 2, nickname: '乙', alive: true, escaped: false },
        ],
        you: { seat: 1, role: 'VILLAGER', can_vote: true, mates: null,
               acting: true, can: ['vote', 'skip'] },
      },
    }
    act(() => { useWerewolfStore.setState({ view: view as any }) })
    // 座位可选 + 确认按钮出现
    expect(screen.getAllByText('确认').length).toBeGreaterThan(0)
    // 选中座位 → 点确认 → 确认弹窗发起（确认制）
    const seat2 = screen.getAllByText('乙')[0]
    act(() => { seat2.dispatchEvent(new MouseEvent('click', { bubbles: true })) })
    const confirmBtn = Array.from(document.querySelectorAll('div')).find(
      (d) => d.children.length === 0 && d.textContent === '确认')
    act(() => { confirmBtn!.dispatchEvent(new MouseEvent('click', { bubbles: true })) })
    expect(showModalSpy).toHaveBeenCalledWith(
      expect.objectContaining({ content: '确定选择 2 号吗？提交后不可撤销' }))
  })

  it('女巫有解药时渲染用药按钮（C2）', () => {
    render(<WerewolfRoom />)
    const view = {
      ...PLAYING_VIEW,
      snapshot: {
        ...PLAYING_VIEW.snapshot,
        phase: 'NIGHT_WITCH',
        you: { seat: 1, role: 'WITCH', can_vote: true, mates: null, acting: true,
               can: ['witch_save', 'witch_poison', 'skip'],
               witch: { save: true, poison: true, victim: 2 } },
      },
    }
    act(() => { useWerewolfStore.setState({ view: view as any }) })
    expect(screen.getAllByText('使用解药').length).toBeGreaterThan(0)
    expect(screen.getAllByText('放弃').length).toBeGreaterThan(0)
  })

  it('view 从空到对局快照不白屏，渲染座位与身份', () => {
    render(<WerewolfRoom />)
    act(() => { useWerewolfStore.setState({ view: PLAYING_VIEW as any }) })
    expect(screen.getAllByText(/第 1 天/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('甲').length).toBeGreaterThan(0)
    expect(screen.getAllByText('乙').length).toBeGreaterThan(0)
  })
})
