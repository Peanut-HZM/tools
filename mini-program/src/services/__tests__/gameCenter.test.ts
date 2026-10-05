/** gameCenter 服务层错误处理：后端 4xx 错误体 {detail} 必须转为异常（而非当成功返回） */
import { describe, expect, it, vi, beforeEach } from 'vitest'

const requestSpy = vi.fn()

vi.mock('../request', () => ({
  request: (...a: any[]) => requestSpy(...a),
}))

import { gameApi } from '../gameCenter'

describe('gameCenter 错误处理', () => {
  beforeEach(() => {
    requestSpy.mockReset()
  })

  it('创建失败（422 detail）时抛出明确错误而非返回 undefined', async () => {
    requestSpy.mockResolvedValue({ detail: '总人数必须 6-12，当前 16' })
    await expect(gameApi.createRoom({ custom_roles: { WEREWOLF: 4 } }))
      .rejects.toThrow('总人数必须 6-12，当前 16')
  })

  it('加入失败（409 detail）时抛出错误', async () => {
    requestSpy.mockResolvedValue({ detail: '房间已满员' })
    await expect(gameApi.joinRoom('123456')).rejects.toThrow('房间已满员')
  })

  it('成功响应原样返回', async () => {
    requestSpy.mockResolvedValue({ room_id: '654321' })
    const res = await gameApi.createRoom({ board_id: '6p' })
    expect(res.room_id).toBe('654321')
  })
})
