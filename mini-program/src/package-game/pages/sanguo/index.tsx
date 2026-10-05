import { useState } from 'react'
import { View, Text, Input } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { sanguoApi } from '../../../services/sanguoApi'
import './index.scss'

const HERO_COLORS: Record<string, string> = {
  蜀: 'linear-gradient(135deg,#7a2c2c,#c0392b)',
  魏: 'linear-gradient(135deg,#1f3a93,#2980b9)',
  群: 'linear-gradient(135deg,#7d6608,#b7950b)',
}

export default function SanguoLobby() {
  const [joinCode, setJoinCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [heroes, setHeroes] = useState<{ name: string; kingdom: string }[]>([])

  useDidShow(() => {
    sanguoApi.getHeroes().then((res) => setHeroes(res.heroes)).catch(() => {})
  })

  const createRoom = async () => {
    setBusy(true)
    try {
      const { room_id } = await sanguoApi.createRoom()
      Taro.navigateTo({ url: `/package-game/pages/sanguo/room/index?room_id=${room_id}` })
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
      await sanguoApi.joinRoom(joinCode)
      Taro.navigateTo({ url: `/package-game/pages/sanguo/room/index?room_id=${joinCode}` })
    } catch (e: any) {
      Taro.showToast({ title: e?.message || '加入失败', icon: 'none' })
    } finally {
      setBusy(false)
    }
  }

  const goRecords = () => {
    Taro.navigateTo({ url: '/package-game/pages/sanguo/records/index' })
  }

  return (
    <View className='sanguo-lobby'>
      <View className='sanguo-hero'>
        <Text className='sanguo-hero__title gradient-text'>三国杀 · 身份局</Text>
        <Text className='sanguo-hero__sub'>4 人局 · 主公 / 忠臣 / 反贼 / 内奸</Text>
      </View>

      <View className='glass-card lobby-card'>
        <Text className='lobby-card__title'>武将池（8 名标准武将随机 4 名上场）</Text>
        <View className='hero-grid'>
          {heroes.map((h) => (
            <View key={h.name}
                  className='hero-chip'
                  style={{ background: HERO_COLORS[h.kingdom] || '' }}>
              <Text className='hero-chip__name'>{h.name}</Text>
              <Text className='hero-chip__kingdom'>{h.kingdom}</Text>
            </View>
          ))}
          {heroes.length === 0 && (
            <Text className='hero-grid__loading'>武将加载中...</Text>
          )}
        </View>
        <View className='btn-primary lobby-btn' onClick={createRoom}>
          {busy ? '处理中...' : '创建房间'}
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

      <View className='glass-card lobby-card' onClick={goRecords}>
        <Text className='lobby-card__title'>对局记录</Text>
        <Text className='lobby-card__desc'>回看已完成对局的完整过程 ›</Text>
      </View>
    </View>
  )
}
