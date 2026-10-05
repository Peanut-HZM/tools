import { useMemo, useState } from 'react'
import { View, Text, Input, Picker } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { gameApi, BoardInfo } from '../../../services/gameCenter'
import './index.scss'

export const ROLE_LABELS: Record<string, string> = {
  WEREWOLF: '狼人', VILLAGER: '村民', SEER: '预言家', WITCH: '女巫',
  HUNTER: '猎人', GUARD: '守卫', IDIOT: '白痴',
}
const CUSTOM_ROLE_KEYS = Object.keys(ROLE_LABELS)
const SELF_RESCUE_OPTIONS = [
  { value: 'never', label: '不可自救' },
  { value: 'first_night', label: '仅首夜' },
  { value: 'always', label: '随时' },
]
const SPEECH_OPTIONS = [30, 60, 90, 120]

export default function WerewolfLobby() {
  const [boards, setBoards] = useState<BoardInfo[]>([])
  const [boardId, setBoardId] = useState('9p')
  const [custom, setCustom] = useState<Record<string, number>>({})
  const [speechSeconds, setSpeechSeconds] = useState(60)
  const [selfRescue, setSelfRescue] = useState('never')
  const [milkThrough, setMilkThrough] = useState(true)
  const [joinCode, setJoinCode] = useState('')
  const [busy, setBusy] = useState(false)

  useDidShow(() => {
    gameApi.getBoards().then((res) => setBoards(res.boards)).catch(() =>
      Taro.showToast({ title: '板子加载失败', icon: 'none' }))
  })

  const isCustom = boardId === 'custom'
  const customTotal = useMemo(
    () => CUSTOM_ROLE_KEYS.reduce((s, k) => s + (custom[k] || 0), 0), [custom])

  const createRoom = async () => {
    setBusy(true)
    try {
      const payload: any = {
        speech_seconds: speechSeconds,
        witch_self_rescue: selfRescue,
        witch_guard_conflict: milkThrough,
      }
      if (isCustom) {
        payload.custom_roles = custom
        payload.board_name = `自定义${customTotal}人局`
      } else {
        payload.board_id = boardId
      }
      const { room_id } = await gameApi.createRoom(payload)
      Taro.navigateTo({ url: `/package-game/pages/werewolf/room/index?room_id=${room_id}` })
    } catch (e: any) {
      Taro.showToast({ title: e?.message || '创建失败', icon: 'none' })
    } finally {
      setBusy(false)
    }
  }

  const joinRoom = async () => {
    if (!/^\d{6}$/.test(joinCode)) {
      Taro.showToast({ title: '请输入 6 位房号', icon: 'none' })
      return
    }
    setBusy(true)
    try {
      await gameApi.joinRoom(joinCode)
      Taro.navigateTo({ url: `/package-game/pages/werewolf/room/index?room_id=${joinCode}` })
    } catch (e: any) {
      Taro.showToast({ title: e?.message || '加入失败', icon: 'none' })
    } finally {
      setBusy(false)
    }
  }

  const changeCustom = (key: string, delta: number) => {
    setCustom((prev) => {
      const next = { ...prev, [key]: Math.max(0, (prev[key] || 0) + delta) }
      if (next[key] === 0) delete next[key]
      return next
    })
  }

  return (
    <View className='werewolf-lobby'>
      <View className='glass-card lobby-card'>
        <Text className='lobby-card__title'>创建房间</Text>
        <View className='lobby-boards'>
          {boards.map((b) => (
            <View key={b.id}
                  className={`board-chip ${boardId === b.id ? 'board-chip--active' : ''}`}
                  onClick={() => setBoardId(b.id)}>
              <Text className='board-chip__name'>{b.name}</Text>
              <Text className='board-chip__roles'>
                {Object.entries(b.roles).map(([r, n]) => `${ROLE_LABELS[r]}×${n}`).join(' ')}
              </Text>
            </View>
          ))}
          <View className={`board-chip ${isCustom ? 'board-chip--active' : ''}`}
                onClick={() => setBoardId('custom')}>
            <Text className='board-chip__name'>自定义局</Text>
            <Text className='board-chip__roles'>{customTotal} 人</Text>
          </View>
        </View>

        {isCustom && (
          <View className='lobby-custom'>
            <View className='lobby-custom__head'>
              <Text className='lobby-custom__clear'
                    onClick={() => setCustom({})}>清空</Text>
            </View>
            {CUSTOM_ROLE_KEYS.map((k) => (
              <View key={k} className='custom-row'>
                <Text className='custom-row__name'>{ROLE_LABELS[k]}</Text>
                <View className='custom-row__stepper'>
                  <Text className='custom-row__btn' onClick={() => changeCustom(k, -1)}>−</Text>
                  <Text className='custom-row__num'>{custom[k] || 0}</Text>
                  <Text className='custom-row__btn' onClick={() => changeCustom(k, 1)}>＋</Text>
                </View>
              </View>
            ))}
            <Text className='lobby-custom__hint'>
              共 {customTotal} 人（6-12 人可开局；狼≥1；预言家/女巫/猎人/守卫/白痴各≤1）
            </Text>
          </View>
        )}

        <View className='lobby-config'>
          <Picker mode='selector' range={SPEECH_OPTIONS}
                  onChange={(e) => setSpeechSeconds(SPEECH_OPTIONS[Number(e.detail.value)])}>
            <View className='config-row'>
              <Text>发言时长</Text>
              <Text className='config-row__value'>{speechSeconds}s ›</Text>
            </View>
          </Picker>
          <Picker mode='selector' range={SELF_RESCUE_OPTIONS.map((o) => o.label)}
                  onChange={(e) => setSelfRescue(SELF_RESCUE_OPTIONS[Number(e.detail.value)].value)}>
            <View className='config-row'>
              <Text>女巫自救</Text>
              <Text className='config-row__value'>
                {SELF_RESCUE_OPTIONS.find((o) => o.value === selfRescue)?.label} ›
              </Text>
            </View>
          </Picker>
          <View className='config-row' onClick={() => setMilkThrough((v) => !v)}>
            <Text>奶穿规则（守+救同夜死亡）</Text>
            <Text className='config-row__value'>{milkThrough ? '开启' : '关闭'}</Text>
          </View>
        </View>

        <View className='btn-primary lobby-btn' onClick={createRoom}>
          {busy ? '创建中...' : '创建房间'}
        </View>
      </View>

      <View className='glass-card lobby-card'>
        <Text className='lobby-card__title'>加入房间</Text>
        <View className='lobby-join'>
          <Input className='lobby-join__input' type='number' maxlength={6}
                 placeholder='输入 6 位房号' value={joinCode}
                 onInput={(e) => setJoinCode(e.detail.value)} />
          <View className='btn-primary lobby-join__btn' onClick={joinRoom}>加入</View>
        </View>
      </View>
    </View>
  )
}
