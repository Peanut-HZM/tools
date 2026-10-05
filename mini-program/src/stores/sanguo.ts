import { create } from 'zustand'
import { sanguoWs } from '../services/sanguoWs'

interface SanguoStore {
  view: any | null
  lastError: string | null
  connecting: boolean
  connect: (roomId: string) => Promise<void>
  disconnect: () => void
  playCard: (cardIds: number[], targets?: number[], asName?: string) => void
  respond: (cardIds: number[]) => void
  skill: (payload: Record<string, any>) => void
  nextPhase: () => void
  discard: () => void
  clearError: () => void
}

export const useSanguoStore = create<SanguoStore>((set, get) => {
  function handleMessage(msg: any) {
    const state = get()
    if (msg.type === 'hello' || msg.type === 'state') {
      set({ view: msg.state, lastError: null })
    } else if (msg.type === 'room') {
      const view = state.view
      if (!view) return
      set({ view: { ...msg.room, snapshot: view.snapshot } })
    } else if (msg.type === 'event') {
      const view = state.view
      if (!view) return
      const snap = view.snapshot || view
      const log = snap.log || []
      if (log.length && log[log.length - 1].id >= msg.id) return
      const nextSnap = { ...snap, log: [...log, { id: msg.id, text: msg.text }] }
      set({ view: view.snapshot ? { ...view, snapshot: nextSnap } : nextSnap })
    } else if (msg.type === 'error') {
      set({ lastError: msg.message })
    } else if (msg.type === 'room_closed') {
      set({ lastError: msg.reason })
    } else if (msg.type === 'game_over') {
      const view = state.view
      if (!view) return
      const snap = view.snapshot || view
      const nextSnap = { ...snap, phase: 'GAME_OVER', winner: msg.winner }
      set({ view: view.snapshot ? { ...view, snapshot: nextSnap } : nextSnap })
    }
  }

  return {
    view: null,
    lastError: null,
    connecting: false,
    connect: async (roomId) => {
      set({ connecting: true })
      try {
        await sanguoWs.connect(roomId, { onMessage: handleMessage })
      } finally {
        set({ connecting: false })
      }
    },
    disconnect: () => {
      sanguoWs.close()
      set({ view: null })
    },
    playCard: (cardIds, targets, asName) =>
      sanguoWs.send({ type: 'act', card_ids: cardIds, targets: targets || [],
                      as_name: asName || null }),
    respond: (cardIds) => sanguoWs.send({ type: 'respond', card_ids: cardIds }),
    skill: (payload) => sanguoWs.send({ type: 'skill', ...payload }),
    nextPhase: () => sanguoWs.send({ type: 'next_phase' }),
    discard: () => sanguoWs.send({ type: 'discard' }),
    clearError: () => set({ lastError: null }),
  }
})
