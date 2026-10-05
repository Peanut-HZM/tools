import { useEffect, useMemo, useRef, useState } from 'react'
import { View, Text, Input, ScrollView, Image } from '@tarojs/components'
import Taro, { useRouter, useDidShow, useDidHide } from '@tarojs/taro'
import { gameApi } from '../../../../services/gameCenter'
import { useWerewolfStore } from '../../../../stores/werewolf'
import { useAuthStore } from '../../../../stores/auth'
import PlayerSeat from '../../../components/PlayerSeat'
import RoleCard from '../../../components/RoleCard'
import './index.scss'

const ROLE_LABELS: Record<string, string> = {
  WEREWOLF: '狼人', VILLAGER: '村民', SEER: '预言家', WITCH: '女巫',
  HUNTER: '猎人', GUARD: '守卫', IDIOT: '白痴',
}
const PHASE_TIPS: Record<string, string> = {
  NIGHT_GUARD: '守卫请行动', NIGHT_WEREWOLF: '狼人请睁眼', NIGHT_SEER: '预言家请查验',
  NIGHT_WITCH: '女巫请行动', DAWN: '天亮了', DAY_SPEECH: '发言阶段', DAY_VOTE: '投票放逐',
  PK_SPEECH: 'PK 发言', DAY_VOTE_PK: 'PK 投票', HUNTER_SHOT: '猎人请开枪',
  LAST_WORDS: '遗言', RESULT: '对局结束',
}
const NIGHT_PHASES = ['NIGHT_GUARD', 'NIGHT_WEREWOLF', 'NIGHT_SEER', 'NIGHT_WITCH']

import CARD_BACK from '../../../assets/cards/back.png'
import IMG_WEREWOLF from '../../../assets/cards/werewolf.png'
import IMG_VILLAGER from '../../../assets/cards/villager.png'
import IMG_SEER from '../../../assets/cards/seer.png'
import IMG_WITCH from '../../../assets/cards/witch.png'
import IMG_HUNTER from '../../../assets/cards/hunter.png'
import IMG_GUARD from '../../../assets/cards/guard.png'
import IMG_IDIOT from '../../../assets/cards/idiot.png'

const ROLE_CARDS: Record<string, any> = {
  WEREWOLF: IMG_WEREWOLF,
  VILLAGER: IMG_VILLAGER,
  SEER: IMG_SEER,
  WITCH: IMG_WITCH,
  HUNTER: IMG_HUNTER,
  GUARD: IMG_GUARD,
  IDIOT: IMG_IDIOT,
}

export default function WerewolfRoom() {
  const router = useRouter()
  const roomId = router.params.room_id || ''
  const {
    view, lastError, connect, disconnect,
    sendAct, sendSpeech, sendLastWords, sendSkip, clearError,
  } = useWerewolfStore()
  const me = useAuthStore((s) => s.user)
  const [selected, setSelected] = useState<number | null>(null)
  const [input, setInput] = useState('')
  const [now, setNow] = useState(Math.floor(Date.now() / 1000))
  const toastShownRef = useRef('')

  useDidShow(() => {
    if (roomId) connect(roomId)
  })
  useDidHide(() => {})
  useEffect(() => () => disconnect(), [])
  useEffect(() => {
    const t = setInterval(() => setNow(Math.floor(Date.now() / 1000)), 1000)
    return () => clearInterval(t)
  }, [])

  // 错误 toast（同一 message 只弹一次直到内容变化）
  useEffect(() => {
    if (lastError && toastShownRef.current !== lastError) {
      toastShownRef.current = lastError
      Taro.showToast({ title: lastError, icon: 'none' })
      clearError()
    }
  }, [lastError])

  useEffect(() => { setSelected(null) }, [view?.snapshot?.phase, view?.snapshot?.day])

  const snap = view?.snapshot || view  // WS hello 直接是快照
  const you = snap?.you || {}
  const myUserId = String(me?.id ?? '')
  const mySeat = useMemo(() => {
    if (view?.members) {
      const m = view.members.find((m: any) => m.user_id === myUserId)
      if (m) return m.seat
    }
    return you?.seat || null
  }, [view, myUserId, you])

  const secondsLeft = useMemo(() => {
    if (!snap?.deadline) return null
    return Math.max(0, Math.ceil(snap.deadline - now))
  }, [snap?.deadline, now])

  // ---- 行动选择（hooks 必须在任何条件 return 之前调用，否则 React #310 白屏） ----
  const canAct = !!(you?.acting && Array.isArray(you?.can) && you.can.length > 0)
  const canList: string[] = canAct ? you.can : []
  const hasTargetAction = canAct && canList.some(
    (a: string) => a !== 'skip' && a !== 'witch_save')
  // 女巫解药：目标固定为刀口，无需选座位，一键使用
  const canSaveWitch = canAct && canList.includes('witch_save')
    && !!you.witch?.victim && !!you.witch?.save
  const selectableSeats = useMemo(() => {
    if (!canAct || !hasTargetAction) return []
    const action = canList[0]
    return (snap?.players || [])
      .filter((p: any) => p.alive && p.seat !== mySeat)
      .filter((p: any) => {
        if (action === 'vote_pk') return (snap?.pk_seats || []).includes(p.seat)
        if (action === 'witch_save') return p.seat === you.witch?.victim
        return true
      })
      .map((p: any) => p.seat)
  }, [canAct, hasTargetAction, canList, you, snap, mySeat])

  if (!view) {
    return <View className='wr wr--loading'><Text>连接房间中...</Text></View>
  }

  const isWaiting = view.status === 'WAITING'
  const phase = snap?.phase
  const isNight = NIGHT_PHASES.includes(phase)
  const isResult = phase === 'RESULT'

  const currentAction = canAct
    ? (you.can.find((a: string) => a !== 'skip') || 'skip') : null

  const confirmAction = () => {
    if (selected == null) {
      Taro.showToast({ title: '请先选择目标', icon: 'none' })
      return
    }
    Taro.showModal({
      title: '确认操作',
      content: `确定选择 ${selected} 号吗？提交后不可撤销`,
      success: (res) => {
        if (res.confirm) {
          sendAct(currentAction, selected)
          setSelected(null)
        }
      },
    })
  }

  const submitSpeech = () => {
    const content = input.trim()
    if (!content) return
    if (phase === 'LAST_WORDS') sendLastWords(content)
    else sendSpeech(content)
    setInput('')
  }

  // ---- 等待区 ----
  if (isWaiting) {
    const isHost = view.host_id === myUserId
    return (
      <View className='wr'>
        <View className='glass-card wr-card'>
          <Text className='wr-room-no'>房号 {view.room_id}</Text>
          <Text className='wr-board'>
            {view.board.name} · {view.members.length}/{view.capacity} 人
          </Text>
          <View className='wr-members'>
            {view.members.map((m: any) => (
              <PlayerSeat key={m.user_id} seat={m.seat} nickname={m.nickname}
                          alive connected={m.connected} />
            ))}
          </View>
          {isHost && view.members.length >= 2 && view.members.length === view.capacity && (
            <View className='btn-primary wr-start-btn' onClick={async () => {
              try { await gameApi.startGame(roomId) } catch (e: any) {
                Taro.showToast({ title: e?.message || '开始失败', icon: 'none' })
              }
            }}>开始对局</View>
          )}
          {isHost && view.members.length < view.capacity && (
            <Text className='wr-wait-tip'>还差 {view.capacity - view.members.length} 人，把房号分享给朋友吧</Text>
          )}
          {!isHost && <Text className='wr-wait-tip'>等待房主开始对局…</Text>}
          <View className='wr-leave' onClick={async () => {
            try { await gameApi.leaveRoom(roomId) } catch { /* 已被解散等情况忽略 */ }
            disconnect()
            Taro.navigateBack()
          }}>离开房间</View>
        </View>
      </View>
    )
  }

  return (
    <View className='wr'>
      {/* 阶段横幅 + 倒计时 */}
      <View className={`wr-banner ${isNight ? 'wr-banner--night' : ''}`}>
        <Text className='wr-banner__phase'>
          第 {snap.day} 天 · {PHASE_TIPS[phase] || phase}
        </Text>
        {secondsLeft != null && <Text className='wr-banner__timer'>{secondsLeft}s</Text>}
      </View>

      {/* 我的身份卡 */}
      <View className='wr-myrole'>
        <RoleCard role={you?.role} />
        {you?.role && <Text className='wr-myrole__name'>{ROLE_LABELS[you.role]}</Text>}
        {you?.mates?.length > 0 && (
          <Text className='wr-myrole__mates'>队友：{you.mates.join('、')} 号</Text>
        )}
        {you?.checks?.length > 0 && (
          <Text className='wr-myrole__checks'>
            查验：{you.checks.map((c: any) =>
              `${c.seat}号${c.is_werewolf ? '狼' : '好'}`).join('，')}
          </Text>
        )}
      </View>

      {/* 座位区 */}
      <View className='wr-seats'>
        {(snap?.players || []).map((p: any) => (
          <PlayerSeat key={p.seat} seat={p.seat} nickname={p.nickname} alive={p.alive}
                      connected={p.connected !== false} escaped={p.escaped}
                      idiotRevealed={p.idiot_revealed}
                      selectable={canAct && hasTargetAction && selectableSeats.includes(p.seat)}
                      selected={selected === p.seat}
                      speaking={snap.speaking_seat === p.seat}
                      onClick={() => {
                        if (canAct && hasTargetAction && selectableSeats.includes(p.seat)) {
                          setSelected(p.seat)
                        }
                      }} />
        ))}
      </View>

      {/* 行动确认条 */}
      {canAct && !isResult && (
        <View className='wr-action'>
          <Text className='wr-action__tip'>
            {phase === 'DAY_VOTE' || phase === 'DAY_VOTE_PK'
              ? '请投票放逐一名玩家'
              : canSaveWitch && !hasTargetAction
                ? `今晚 ${you.witch.victim} 号被刀，是否使用解药？`
                : hasTargetAction ? '选择一名玩家' : '是否使用技能？'}
          </Text>
          <View className='wr-action__btns'>
            {you.can.includes('skip') && (
              <View className='wr-action__btn wr-action__btn--ghost' onClick={() => sendSkip()}>放弃</View>
            )}
            {canSaveWitch && (
              <View className='btn-primary wr-action__btn' onClick={() => {
                Taro.showModal({
                  title: '确认操作', content: `确定对 ${you.witch.victim} 号使用解药吗？`,
                  success: (res) => { if (res.confirm) sendAct('witch_save', you.witch.victim) },
                })
              }}>使用解药</View>
            )}
            {hasTargetAction && (
              <View className='btn-primary wr-action__btn' onClick={confirmAction}>确认</View>
            )}
          </View>
        </View>
      )}

      {/* 发言 / 遗言输入 */}
      {(phase === 'DAY_SPEECH' || phase === 'PK_SPEECH' || phase === 'LAST_WORDS')
        && you?.speaking && (
        <View className='wr-speech'>
          <Input className='wr-speech__input' value={input} maxlength={500}
                 placeholder={phase === 'LAST_WORDS' ? '留下你的遗言…' : '说出你的观点…'}
                 onInput={(e) => setInput(e.detail.value)} />
          <View className='btn-primary wr-speech__send' onClick={submitSpeech}>发送</View>
          <View className='wr-speech__skip' onClick={() => sendSkip()}>跳过</View>
        </View>
      )}

      {/* 发言流 */}
      {(snap?.speeches || []).length > 0 && (
        <ScrollView className='wr-speeches' scrollY>
          {snap.speeches.map((s: any, i: number) => (
            <View key={i} className='wr-speech-item'>
              <Text className='wr-speech-item__who'>
                {s.seat} 号 {s.nickname}{s.last_words ? '（遗言）' : ''}
              </Text>
              <Text className='wr-speech-item__text'>{s.content}</Text>
            </View>
          ))}
        </ScrollView>
      )}

      {/* 事件日志 */}
      <ScrollView className='wr-log' scrollY>
        {(snap?.log || []).map((e: any) => (
          <Text key={e.id} className='wr-log__item'>{e.text}</Text>
        ))}
      </ScrollView>

      {/* 结算浮层 */}
      {isResult && (
        <View className='wr-result'>
          <Text className={`wr-result__winner ${snap.winner === 'WEREWOLF' ? 'wr-result__winner--wolf' : ''}`}>
            {snap.winner === 'WEREWOLF' ? '狼人阵营获胜' : '好人阵营获胜'}
          </Text>
          <View className='wr-result__cards'>
            {(snap.reveal || []).map((r: any) => (
              <View key={r.seat} className='wr-result__card'>
                <Image className='wr-result__img'
                       src={ROLE_CARDS[r.role] || CARD_BACK} mode='aspectFill' />
                <Text className='wr-result__seat'>{r.seat} 号</Text>
                <Text className='wr-result__role'>
                  {ROLE_LABELS[r.role] || r.role}{r.alive ? '' : '（出局）'}
                </Text>
              </View>
            ))}
          </View>
          {view.host_id === myUserId ? (
            <View className='btn-primary wr-result__btn' onClick={async () => {
              try { await gameApi.replay(roomId) } catch (e: any) {
                Taro.showToast({ title: e?.message || '操作失败', icon: 'none' })
              }
            }}>再来一局</View>
          ) : (
            <Text className='wr-result__waiting'>等待房主开始下一局…</Text>
          )}
          <View className='wr-result__back' onClick={async () => {
            try { await gameApi.leaveRoom(roomId) } catch { /* 忽略 */ }
            disconnect()
            Taro.navigateBack()
          }}>返回大厅</View>
        </View>
      )}
    </View>
  )
}
