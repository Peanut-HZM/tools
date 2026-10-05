import { useState } from 'react'
import { View, Text, Image } from '@tarojs/components'
import './RoleCard.scss'

import CARD_BACK from '../assets/cards/back.png'
import IMG_WEREWOLF from '../assets/cards/werewolf.png'
import IMG_VILLAGER from '../assets/cards/villager.png'
import IMG_SEER from '../assets/cards/seer.png'
import IMG_WITCH from '../assets/cards/witch.png'
import IMG_HUNTER from '../assets/cards/hunter.png'
import IMG_GUARD from '../assets/cards/guard.png'
import IMG_IDIOT from '../assets/cards/idiot.png'

const ROLE_CARDS: Record<string, any> = {
  WEREWOLF: IMG_WEREWOLF,
  VILLAGER: IMG_VILLAGER,
  SEER: IMG_SEER,
  WITCH: IMG_WITCH,
  HUNTER: IMG_HUNTER,
  GUARD: IMG_GUARD,
  IDIOT: IMG_IDIOT,
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
