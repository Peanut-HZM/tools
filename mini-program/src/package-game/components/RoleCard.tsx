import { useState } from 'react'
import { View, Text, Image } from '@tarojs/components'
import './RoleCard.scss'

const CARD_BACK = require('../assets/cards/back.png')

const ROLE_CARDS: Record<string, any> = {
  WEREWOLF: require('../assets/cards/werewolf.png'),
  VILLAGER: require('../assets/cards/villager.png'),
  SEER: require('../assets/cards/seer.png'),
  WITCH: require('../assets/cards/witch.png'),
  HUNTER: require('../assets/cards/hunter.png'),
  GUARD: require('../assets/cards/guard.png'),
  IDIOT: require('../assets/cards/idiot.png'),
}

/** 自己的底牌：点按翻转看牌，可随时重看 */
export default function RoleCard({ role }: { role: string | null }) {
  const [flipped, setFlipped] = useState(false)
  if (!role) return null
  return (
    <View className='role-card' onClick={() => setFlipped((v) => !v)}>
      <Image className='role-card__img' src={flipped ? ROLE_CARDS[role] : CARD_BACK}
             mode='aspectFill' />
      <Text className='role-card__hint'>{flipped ? '点击盖回' : '点击看牌'}</Text>
    </View>
  )
}
