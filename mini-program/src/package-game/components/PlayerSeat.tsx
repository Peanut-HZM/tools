import { View, Text } from '@tarojs/components'
import './PlayerSeat.scss'

interface Props {
  seat: number
  nickname: string
  alive: boolean
  connected: boolean
  escaped?: boolean
  idiotRevealed?: boolean
  selectable?: boolean
  selected?: boolean
  speaking?: boolean
  onClick?: () => void
}

export default function PlayerSeat(p: Props) {
  const cls = ['seat']
  if (!p.alive) cls.push('seat--dead')
  if (p.selectable && p.alive) cls.push('seat--selectable')
  if (p.selected) cls.push('seat--selected')
  if (p.speaking) cls.push('seat--speaking')
  return (
    <View className={cls.join(' ')} onClick={p.onClick}>
      <View className='seat__num'>{p.seat}</View>
      <View className='seat__avatar'>{p.nickname.slice(0, 1)}</View>
      <Text className='seat__name'>{p.nickname}</Text>
      <View className='seat__badges'>
        {!p.alive && <Text className='seat__badge seat__badge--dead'>出局</Text>}
        {p.alive && p.escaped && <Text className='seat__badge'>托管</Text>}
        {p.alive && !p.connected && !p.escaped && <Text className='seat__badge'>离线</Text>}
        {p.idiotRevealed && <Text className='seat__badge seat__badge--idiot'>白痴</Text>}
      </View>
    </View>
  )
}
