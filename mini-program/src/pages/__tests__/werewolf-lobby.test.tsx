/** 大厅页自定义板子：清空按钮回归测试 */
import { describe, expect, it, vi } from 'vitest'

vi.mock('@tarojs/taro', () => ({
  default: { showToast: vi.fn(), navigateTo: vi.fn(), getStorageSync: vi.fn(() => '') },
  useDidShow: (fn: () => void) => { fn() },
}))
vi.mock('@tarojs/components', () => ({
  View: (p: any) => React.createElement('div', { onClick: p.onClick }, p.children),
  Text: (p: any) => React.createElement('span', { onClick: p.onClick }, p.children),
  Input: () => React.createElement('input'),
  Picker: (p: any) => React.createElement('div', null, p.children),
}))
vi.mock('../../../services/gameCenter', () => ({
  gameApi: {
    getBoards: vi.fn(() => Promise.resolve({ boards: [
      { id: '6p', name: '6人新手局', player_count: 6, roles: { WEREWOLF: 2 } },
    ], presets: {} })),
    createRoom: vi.fn(),
    joinRoom: vi.fn(),
  },
}))

import React from 'react'
import { render, screen, act, fireEvent } from '@testing-library/react'
import WerewolfLobby from '../../package-game/pages/werewolf/index'

describe('大厅自定义板子', () => {
  it('清空按钮将所有角色计数归零', async () => {
    render(<WerewolfLobby />)
    // 切到自定义局
    await act(async () => {
      fireEvent.click(screen.getByText('自定义局'))
    })
    // 加一些角色
    const pluses = screen.getAllByText('＋')
    await act(async () => { fireEvent.click(pluses[0]) })
    await act(async () => { fireEvent.click(pluses[6]) })
    expect(screen.getByText((_, el) => el?.textContent === '共 2 人（6-12 人可开局；狼≥1；预言家/女巫/猎人/守卫/白痴各≤1）')).toBeTruthy()
    // 清空
    await act(async () => { fireEvent.click(screen.getByText('清空')) })
    expect(screen.getByText((_, el) => el?.textContent?.startsWith('共 0 人') ?? false)).toBeTruthy()
  })
})
