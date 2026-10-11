/** werewolfWs 平台桥接测试：mock @tarojs/taro，验证 task 实例回调绑定与消息分发 */
import { describe, expect, it, vi, beforeEach } from 'vitest'

const setStorageSync = vi.fn((..._args: any[]) => 'test-token')

class FakeTask {
  onOpen = vi.fn()
  onMessage = vi.fn()
  onError = vi.fn()
  onClose = vi.fn()
  send = vi.fn()
  close = vi.fn()
}

let fakeTask: FakeTask

vi.mock('@tarojs/taro', () => ({
  default: {
    // H5 行为：connectSocket 返回 Promise<SocketTask>
    connectSocket: vi.fn(() => Promise.resolve(fakeTask as unknown as import('@tarojs/taro').SocketTask)),
    getStorageSync: (...a: any[]) => setStorageSync(...(a as [string, any])),
  },
}))

vi.mock('../../services/request', () => ({
  API_BASE_URL: 'http://127.0.0.1:19092/api',
}))

import { werewolfWs } from '../../services/werewolfWs'
import Taro from '@tarojs/taro'

describe('werewolfWs 平台桥接', () => {
  beforeEach(() => {
    fakeTask = new FakeTask()
    vi.mocked(Taro.connectSocket).mockReset()
    vi.mocked(Taro.connectSocket).mockImplementation(() => Promise.resolve(fakeTask as unknown as import('@tarojs/taro').SocketTask))
    werewolfWs.close()
  })

  it('connect 后消息经 task.onMessage 分发到 handlers', async () => {
    const onMessage = vi.fn()
    const pending = werewolfWs.connect('123456', { onMessage })
    await Promise.resolve()             // 让 bindTask 的微任务先执行
    fakeTask.onOpen.mock.calls[0][0]()  // 模拟连接建立
    await pending
    expect(fakeTask.onMessage).toHaveBeenCalled()
    // 模拟服务端消息
    const cb = fakeTask.onMessage.mock.calls[0][0]
    cb({ data: '{"type":"pong"}' })
    expect(onMessage).toHaveBeenCalledWith({ type: 'pong' })
  })

  it('send/close 委托给 task 实例', async () => {
    const pending = werewolfWs.connect('123456', { onMessage: vi.fn() })
    await Promise.resolve()
    fakeTask.onOpen.mock.calls[0][0]()
    await pending
    werewolfWs.send({ type: 'ping' })
    expect(fakeTask.send).toHaveBeenCalledWith({ data: '{"type":"ping"}' })
    werewolfWs.close()
    expect(fakeTask.close).toHaveBeenCalled()
  })

  it('房间不存在(4404)时终止重连并回调 onClose', async () => {
    vi.useFakeTimers()
    const onMessage = vi.fn()
    const onClose = vi.fn()
    const pending = werewolfWs.connect('123456', { onMessage, onClose })
    await Promise.resolve()
    fakeTask.onOpen.mock.calls[0][0]()
    await pending
    // 服务端 4404 关闭（房间不存在）
    fakeTask.onClose.mock.calls[0][0]({ code: 4404 })
    await vi.advanceTimersByTimeAsync(10000)
    expect(onClose).toHaveBeenCalled()
    // 只连接过一次，无重连
    expect(vi.mocked(Taro.connectSocket)).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })

  it('正常断开自动重连且重试次数受上限约束', async () => {
    vi.useFakeTimers()
    const onMessage = vi.fn()
    let taskInstance = fakeTask
    vi.mocked(Taro.connectSocket).mockImplementation(() => {
      taskInstance = new FakeTask()
      return Promise.resolve(taskInstance as unknown as import('@tarojs/taro').SocketTask)
    })
    const pending = werewolfWs.connect('123456', { onMessage })
    await Promise.resolve()
    taskInstance.onOpen.mock.calls[0][0]()
    await pending
    // 连续 4 次非正常断开：第 4 次后不再重连
    for (let i = 0; i < 4; i++) {
      taskInstance.onClose.mock.calls[0][0]({ code: 1006 })
      await vi.advanceTimersByTimeAsync(16000)
    }
    expect(vi.mocked(Taro.connectSocket).mock.calls.length).toBeLessThanOrEqual(4)
    vi.useRealTimers()
  })

  it('connect 使用正确的 ws URL 与 token', async () => {
    const pending = werewolfWs.connect('654321', { onMessage: vi.fn() })
    await Promise.resolve()
    fakeTask.onOpen.mock.calls[0][0]()
    await pending
    const url = vi.mocked(Taro.connectSocket).mock.calls[0][0].url
    expect(url).toBe(
      'ws://127.0.0.1:19092/api/games/werewolf/rooms/654321/ws?token=test-token')
  })
})
