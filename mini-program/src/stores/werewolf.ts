import { create } from 'zustand'
import { werewolfWs } from '../services/werewolfWs'

interface WerewolfStore {
  view: any | null           // 房间视图（含个人视角 snapshot）
  lastError: string | null
  connecting: boolean
  connect: (roomId: string) => Promise<void>
  disconnect: () => void
  sendAct: (action: string, target: number | null) => void
  sendSpeech: (content: string) => void
  sendLastWords: (content: string) => void
  sendSkip: () => void
  clearError: () => void
}

export const useWerewolfStore = create<WerewolfStore>((set, get) => {
  /** WS 消息归约：把服务器推送归约进可渲染的 view */
  function handleMessage(msg: any) {
    const state = get()
    if (msg.type === 'hello' || msg.type === 'state') {
      set({ view: msg.state, lastError: null })
    } else if (msg.type === 'room') {
      // 等待期成员变动：合并 room 视图（保留已有 snapshot 不覆盖对局数据）
      const view = state.view
      if (!view) return
      set({ view: { ...msg.room, snapshot: view.snapshot } })
    } else if (msg.type === 'event') {
      const view = state.view
      if (!view) return
      const snap = view.snapshot || view
      const log = snap.log || []
      if (log.length && log[log.length - 1].id >= msg.id) return  // 去重
      const nextSnap = { ...snap, log: [...log, { id: msg.id, text: msg.text }] }
      set({ view: view.snapshot ? { ...view, snapshot: nextSnap } : nextSnap })
    } else if (msg.type === 'speech') {
      const view = state.view
      if (!view) return
      const snap = view.snapshot || view
      const nextSnap = { ...snap, speeches: [...(snap.speeches || []),
        { seat: msg.seat, nickname: msg.nickname, content: msg.content }] }
      set({ view: view.snapshot ? { ...view, snapshot: nextSnap } : nextSnap })
    } else if (msg.type === 'private') {
      const view = state.view
      if (!view) return
      const snap = view.snapshot || view
      const you = { ...(snap.you || {}) }
      if (msg.kind === 'seer_result') {
        you.checks = [...(you.checks || []), { seat: msg.target, is_werewolf: msg.is_werewolf }]
      } else if (msg.kind === 'hunter_prompt') {
        you.acting = true
        you.can = ['hunter_shot', 'skip']
      }
      const nextSnap = { ...snap, you }
      set({ view: view.snapshot ? { ...view, snapshot: nextSnap } : nextSnap })
    } else if (msg.type === 'game_over') {
      const view = state.view
      if (!view) return
      const snap = view.snapshot || view
      const nextSnap = { ...snap, phase: 'RESULT', winner: msg.winner, reveal: msg.reveal }
      set({ view: view.snapshot ? { ...view, snapshot: nextSnap } : nextSnap })
    } else if (msg.type === 'error') {
      set({ lastError: msg.message })
    } else if (msg.type === 'room_closed') {
      set({ view: null, lastError: msg.reason })
    }
  }

  return {
    view: null,
    lastError: null,
    connecting: false,
    connect: async (roomId) => {
      set({ connecting: true })
      try {
        await werewolfWs.connect(roomId, { onMessage: handleMessage })
      } finally {
        set({ connecting: false })
      }
    },
    disconnect: () => {
      werewolfWs.close()
      set({ view: null })
    },
    sendAct: (action, target) => werewolfWs.send({ type: 'act', action, target }),
    sendSpeech: (content) => werewolfWs.send({ type: 'speech', content }),
    sendLastWords: (content) => werewolfWs.send({ type: 'last_words', content }),
    sendSkip: () => werewolfWs.send({ type: 'skip' }),
    clearError: () => set({ lastError: null }),
  }
})
