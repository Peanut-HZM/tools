import { useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import {
  sanguoApi, SanguoRecordListItem, SanguoRecordDetail, SanguoTimelineItem,
} from '../../../../services/sanguoApi'
import './index.scss'

const WINNER_LABEL: Record<string, string> = {
  LORD: '主公忠臣胜', REBEL: '反贼胜', SPY: '内奸胜',
}
const SUIT_COLOR: Record<string, string> = {
  '♠': '#8fa3ff', '♥': '#ff6b6b', '♣': '#7dd87d', '♦': '#ffb347',
}

function renderItem(item: SanguoTimelineItem, idx: number) {
  if (item.kind === 'judge') {
    return (
      <View key={idx} className='tl-judge'>
        <Text className='tl-judge__text'>
          判定【{item.for}】：{item.suit}{item.point}
        </Text>
      </View>
    )
  }
  return (
    <View key={idx} className='tl-event'>
      <Text className='tl-event__text'>{item.text}</Text>
    </View>
  )
}

export default function SanguoRecords() {
  const [records, setRecords] = useState<SanguoRecordListItem[]>([])
  const [detail, setDetail] = useState<SanguoRecordDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useDidShow(() => {
    setLoading(true)
    sanguoApi.listRecords(20, 0)
      .then((res) => setRecords(res.records))
      .catch(() => Taro.showToast({ title: '记录加载失败', icon: 'none' }))
      .finally(() => setLoading(false))
  })

  if (detail) {
    const r = detail.record
    return (
      <View className='sgrec'>
        <View className='glass-card sgrec-detail'>
          <Text className={`sgrec-detail__winner ${r.winner === 'REBEL' || r.winner === 'SPY' ? 'sgrec-detail__winner--bad' : ''}`}>
            {WINNER_LABEL[r.winner] || r.winner}
          </Text>
          <Text className='sgrec-detail__meta'>
            {r.player_count} 人身份局 · {r.turn_count} 回合 · {Math.round(r.duration_seconds / 60)} 分钟
          </Text>
          <View className='sgrec-detail__tl-title'><Text>对局过程</Text></View>
          <ScrollView className='sgrec-detail__tl' scrollY>
            {(r.timeline?.timeline || []).map(renderItem)}
          </ScrollView>
          <View className='sgrec-detail__back' onClick={() => setDetail(null)}>返回列表</View>
        </View>
      </View>
    )
  }

  return (
    <View className='sgrec'>
      {loading ? (
        <Text className='sgrec__loading'>加载中...</Text>
      ) : records.length === 0 ? (
        <View className='glass-card sgrec__empty'><Text>还没有对局记录</Text></View>
      ) : (
        records.map((r) => (
          <View key={r.id} className='glass-card sgrec-card' onClick={() => {
            sanguoApi.getRecord(r.id).then(setDetail)
              .catch(() => Taro.showToast({ title: '详情加载失败', icon: 'none' }))
          }}>
            <View className='sgrec-card__row'>
              <Text className={`sgrec-card__winner ${r.winner !== 'LORD' ? 'sgrec-card__winner--bad' : ''}`}>
                {WINNER_LABEL[r.winner] || r.winner}
              </Text>
              <Text className='sgrec-card__meta'>
                {r.player_count} 人 · {r.turn_count} 回合
              </Text>
            </View>
            <Text className='sgrec-card__hint'>点击查看对局过程 ›</Text>
          </View>
        ))
      )}
    </View>
  )
}
