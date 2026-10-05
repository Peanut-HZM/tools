import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import './index.scss'

const GAMES = [
  {
    id: 'werewolf',
    name: '狼人杀',
    desc: '3-12 人联机 · 服务端主持 · 经典板子',
    emoji: '🐺',
    gradient: 'linear-gradient(135deg,#4a3f6b,#8B9BFF)',
  },
]

export default function GameCenter() {
  const go = (id: string) => {
    if (id === 'werewolf') {
      Taro.navigateTo({ url: '/package-game/pages/werewolf/index' })
    }
  }
  return (
    <View className='game-center'>
      <View className='game-center__hero'>
        <Text className='game-center__title gradient-text'>游戏中心</Text>
        <Text className='game-center__sub'>多人联机 · 房间制对战</Text>
      </View>
      <View className='game-center__list'>
        {GAMES.map((g) => (
          <View key={g.id} className='glass-card game-card' onClick={() => go(g.id)}>
            <View className='game-card__icon' style={{ background: g.gradient }}>{g.emoji}</View>
            <View className='game-card__info'>
              <Text className='game-card__name'>{g.name}</Text>
              <Text className='game-card__desc'>{g.desc}</Text>
            </View>
            <Text className='game-card__arrow'>›</Text>
          </View>
        ))}
        <View className='glass-card game-card game-card--disabled'>
          <View className='game-card__icon game-card__icon--muted'>🎮</View>
          <View className='game-card__info'>
            <Text className='game-card__name'>更多游戏</Text>
            <Text className='game-card__desc'>敬请期待</Text>
          </View>
        </View>
      </View>
    </View>
  )
}
