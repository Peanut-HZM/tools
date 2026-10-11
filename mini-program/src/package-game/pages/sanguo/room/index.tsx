import { useEffect, useMemo, useRef, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useRouter, useDidShow } from '@tarojs/taro'
import { sanguoApi } from '../../../../services/sanguoApi'
import { useSanguoStore } from '../../../../stores/sanguo'
import { useAuthStore } from '../../../../stores/auth'
import './index.scss'

const PHASE_TIPS: Record<string, string> = {
  READY: '准备阶段', JUDGE: '判定阶段', DRAW: '摸牌阶段', PLAY: '出牌阶段',
  DISCARD: '弃牌阶段', END: '结束阶段', GAME_OVER: '对局结束',
}
const PENDING_TIPS: Record<string, string> = {
  dodge: '请打出闪', wanjian_dodge: '万箭齐发：请打出闪',
  duel_sha: '决斗：请打出杀', nanman_sha: '南蛮入侵：请打出杀',
  dying_peach: '濒死：请打出桃', wuxiao: '是否打出无懈可击？',
}
const SUIT_COLOR: Record<string, string> = {
  '♠': '#8fa3ff', '♥': '#ff6b6b', '♣': '#7dd87d', '♦': '#ffb347',
}

export default function SanguoRoom() {
  const router = useRouter()
  const roomId = router.params.room_id || ''
  const {
    view, lastError, connect, disconnect,
    playCard, respond, nextPhase, discard, clearError,
  } = useSanguoStore()
  const me = useAuthStore((s) => s.user)
  const [selectedCard, setSelectedCard] = useState<number | null>(null)
  const [selectedTarget, setSelectedTarget] = useState<number | null>(null)
  const [now, setNow] = useState(Math.floor(Date.now() / 1000))
  const toastRef = useRef('')

  useDidShow(() => {
    if (roomId) connect(roomId)
  })
  useEffect(() => () => disconnect(), [])
  useEffect(() => {
    const t = setInterval(() => setNow(Math.floor(Date.now() / 1000)), 1000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    if (lastError && toastRef.current !== lastError) {
      toastRef.current = lastError
      Taro.showToast({ title: lastError, icon: 'none' })
      clearError()
    }
  }, [lastError])

  const snap = view?.snapshot || view
  const you = snap?.you || {}
  const myUserId = String(me?.id ?? '')
  const pending = snap?.pending
  const myTurnPending = pending && pending.seat === you.seat && view?.status === 'PLAYING'

  const secondsLeft = useMemo(() => {
    if (!snap?.deadline) return null
    return Math.max(0, Math.ceil(snap.deadline - now))
  }, [snap?.deadline, now])

  const mySeat = you?.seat

  if (!view) {
    return <View className='sg sg--loading'><Text>连接房间中...</Text></View>
  }

  const isWaiting = view.status === 'WAITING'
  const isOver = view.status === 'RESULT' || snap?.gstate === 'GAME_OVER'

  // ---- 等待区 ----
  if (isWaiting) {
    const isHost = view.host_id === myUserId
    return (
      <View className='sg'>
        <View className='glass-card sg-card'>
          <Text className='sg-room-no'>房号 {view.room_id}</Text>
          <Text className='sg-board'>{view.members.length}/{view.capacity} 人</Text>
          <View className='sg-members'>
            {view.members.map((m: any) => (
              <View key={m.user_id} className='sg-member'>
                <Text>{m.seat} 号 {m.nickname}{m.is_host ? '（房主）' : ''}</Text>
              </View>
            ))}
          </View>
          {isHost && view.members.length === view.capacity && (
            <View className='btn-primary sg-start' onClick={async () => {
              try { await sanguoApi.startGame(roomId) } catch (e: any) {
                Taro.showToast({ title: e?.message || '开始失败', icon: 'none' })
              }
            }}>开始对局</View>
          )}
          {!isHost && <Text className='sg-tip'>等待房主开始对局…</Text>}
          <View className='sg-leave' onClick={async () => {
            try { await sanguoApi.leaveRoom(roomId) } catch { /* 忽略 */ }
            disconnect()
            Taro.navigateBack()
          }}>离开房间</View>
        </View>
      </View>
    )
  }

  // ---- 行动提交（确认制）----
  const submitPlay = () => {
    if (selectedCard == null) {
      Taro.showToast({ title: '请先选择一张手牌', icon: 'none' })
      return
    }
    const needsTarget = ['杀', '决斗', '过河拆桥', '顺手牵羊', '乐不思蜀'].includes(
      (snap.you.hand || []).find((c: any) => c.id === selectedCard)?.name)
    const doIt = () => {
      playCard([selectedCard], needsTarget && selectedTarget != null ? [selectedTarget] : [])
      setSelectedCard(null)
      setSelectedTarget(null)
    }
    Taro.showModal({
      title: '确认出牌',
      content: needsTarget && selectedTarget != null
        ? `对 ${selectedTarget} 号使用这张牌？`
        : '确认使用这张牌？',
      success: (res) => { if (res.confirm) doIt() },
    })
  }

  const submitRespond = () => {
    if (selectedCard == null) {
      Taro.showToast({ title: '请先选择一张响应牌', icon: 'none' })
      return
    }
    respond([selectedCard])
    setSelectedCard(null)
  }

  return (
    <View className='sg'>
      {/* 阶段横幅 */}
      <View className='sg-banner'>
        <Text className='sg-banner__phase'>
          第 {snap.turn_count} 回合 · {PHASE_TIPS[snap.phase] || snap.phase}
          {snap.turn_seat === mySeat ? '（你的回合）' : ''}
        </Text>
        {secondsLeft != null && <Text className='sg-banner__timer'>{secondsLeft}s</Text>}
      </View>

      {/* 响应请求提示 */}
      {myTurnPending && (
        <View className='sg-pending'>
          <Text className='sg-pending__text'>
            {PENDING_TIPS[pending.kind] || '请响应'}（{pending.have}/{pending.need}）
          </Text>
          <View className='btn-primary sg-pending__btn' onClick={submitRespond}>打出</View>
        </View>
      )}

      {/* 玩家区（座位横排：血量/装备/判定） */}
      <ScrollView className='sg-players' scrollX>
        <View className='sg-players__row'>
          {(snap.players || []).map((p: any) => (
            <View key={p.seat}
                  className={`sg-player ${p.alive ? '' : 'sg-player--dead'} ${
                    snap.turn_seat === p.seat ? 'sg-player--active' : ''} ${
                    selectedTarget === p.seat ? 'sg-player--target' : ''}`}
                  onClick={() => setSelectedTarget(p.seat)}>
              <Text className='sg-player__seat'>{p.seat} 号</Text>
              <Text className='sg-player__name'>{p.nickname}</Text>
              <Text className='sg-player__hero'>
                {p.hero}
                {p.role === 'LORD' ? '（主公）' : ''}
              </Text>
              <Text className='sg-player__hp'>
                {p.alive ? `${p.hp}/${p.max_hp}` : '阵亡'}
              </Text>
              {p.equips.length > 0 && (
                <Text className='sg-player__equips'>{p.equips.join(' ')}</Text>
              )}
              {p.judge.length > 0 && (
                <Text className='sg-player__judge'>判定：{p.judge.join(' ')}</Text>
              )}
              {p.hand_count > 0 && <Text className='sg-player__hand'>手牌×{p.hand_count}</Text>}
            </View>
          ))}
        </View>
      </ScrollView>

      {/* 出牌阶段行动条 */}
      {snap.phase === 'PLAY' && snap.turn_seat === mySeat && !isOver && (
        <View className='sg-action'>
          <Text className='sg-action__tip'>
            {selectedCard != null ? '选择目标（如有）后确认出牌' : '选择手牌打出，或结束出牌'}
          </Text>
          <View className='sg-action__btns'>
            <View className='wr-action__btn wr-action__btn--ghost' onClick={nextPhase}>
              结束出牌
            </View>
            <View className='btn-primary sg-action__btn' onClick={submitPlay}>确认出牌</View>
          </View>
        </View>
      )}

      {/* 弃牌阶段 */}
      {snap.phase === 'DISCARD' && snap.turn_seat === mySeat && !isOver && (
        <View className='sg-action'>
          <Text className='sg-action__tip'>
            弃牌阶段：手牌需≤体力（当前 {you.hand.length} 张 / 上限 {you.hp}）
          </Text>
          <View className='btn-primary sg-action__btn' onClick={discard}>
            {you.hand.length > you.hp ? '弃Selected（自动弃至上限）' : '无需弃牌，继续'}
          </View>
        </View>
      )}

      {/* 手牌区 */}
      <ScrollView className='sg-hand' scrollX>
        <View className='sg-hand__row'>
          {(you.hand || []).map((c: any) => (
            <View key={c.id}
                  className={`hand-card ${selectedCard === c.id ? 'hand-card--sel' : ''}`}
                  onClick={() => setSelectedCard(c.id)}>
              <Text className='hand-card__name'>{c.name}</Text>
              <Text className='hand-card__suit' style={{ color: SUIT_COLOR[c.suit] || '#fff' }}>
                {c.suit}{c.point}
              </Text>
            </View>
          ))}
          {(you.hand || []).length === 0 && <Text className='sg-tip'>手牌为空</Text>}
        </View>
      </ScrollView>

      {/* 自己信息 */}
      <View className='sg-myinfo'>
        <Text className='sg-myinfo__role'>
          你的身份：{
            { LORD: '主公', LOYAL: '忠臣', REBEL: '反贼', SPY: '内奸' }[you.role] || you.role
          }
        </Text>
        <Text className='sg-myinfo__hero'>
          {you.hero}
          {you.skills?.length ? `（${you.skills.join(' / ')}）` : ''}
        </Text>
      </View>

      {/* 事件日志 */}
      <ScrollView className='sg-log' scrollY>
        {(snap.log || []).map((e: any) => (
          <Text key={e.id} className='sg-log__item'>{e.text}</Text>
        ))}
      </ScrollView>

      {/* 结算浮层 */}
      {isOver && (
        <View className='sg-result'>
          <Text className={`sg-result__winner ${snap.winner === 'REBEL' ? 'sg-result__winner--wolf' : ''}`}>
            {{ LORD: '主公忠臣获胜', REBEL: '反贼获胜', SPY: '内奸获胜' }[snap.winner] || '对局结束'}
          </Text>
          <View className='sg-result__players'>
            {(snap.players || []).map((p: any) => (
              <View key={p.seat} className='sg-result__player'>
                <Text>{p.seat} 号 {p.nickname}</Text>
                <Text className='sg-result__role'>{p.hero} · {p.role}</Text>
              </View>
            ))}
          </View>
          {view.host_id === myUserId ? (
            <View className='btn-primary sg-result__btn' onClick={async () => {
              try { await sanguoApi.replay(roomId) } catch (e: any) {
                Taro.showToast({ title: e?.message || '操作失败', icon: 'none' })
              }
            }}>再来一局</View>
          ) : (
            <Text className='sg-result__waiting'>等待房主开始下一局…</Text>
          )}
          <View className='sg-result__back' onClick={async () => {
            try { await sanguoApi.leaveRoom(roomId) } catch { /* 忽略 */ }
            disconnect()
            Taro.navigateBack()
          }}>返回大厅</View>
        </View>
      )}
    </View>
  )
}
