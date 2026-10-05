import { useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import {
  gameApi, RecordListItem, RecordDetail, TimelineItem,
} from '../../../../services/gameCenter'
import { ROLE_LABELS } from '..'
import './index.scss'

function fmtDuration(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return m > 0 ? `${m}分${s}秒` : `${s}秒`
}

function renderTimelineItem(item: TimelineItem, idx: number) {
  if (item.kind === 'event') {
    return (
      <View key={idx} className='tl-event'>
        <Text className='tl-event__text'>{item.text}</Text>
      </View>
    )
  }
  if (item.kind === 'speech') {
    return (
      <View key={idx} className='tl-speech'>
        <Text className='tl-speech__who'>
          {item.seat} 号 {item.nickname}
          {item.last_words ? '（遗言）' : ''}{item.pk ? '（PK）' : ''}
        </Text>
        <Text className='tl-speech__text'>{item.text}</Text>
      </View>
    )
  }
  // vote
  const counts: Record<number, number> = {}
  ;(item.detail || []).forEach((d) => {
    if (d.target != null) counts[d.target] = (counts[d.target] || 0) + 1
  })
  const tally = Object.entries(counts).map(([seat, n]) => `${seat}号${n}票`).join('，')
  return (
    <View key={idx} className='tl-vote'>
      <Text className='tl-vote__title'>
        第 {item.day} 天 · {item.vote_kind === 'vote_pk' ? 'PK 投票' : '投票'}
        {item.exiled != null ? `：放逐 ${item.exiled} 号` : '：无人出局'}
      </Text>
      {tally && <Text className='tl-vote__tally'>{tally}</Text>}
    </View>
  )
}

export default function WerewolfRecords() {
  const [records, setRecords] = useState<RecordListItem[]>([])
  const [total, setTotal] = useState(0)
  const [detail, setDetail] = useState<RecordDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useDidShow(() => {
    setLoading(true)
    gameApi.listRecords(20, 0)
      .then((res) => { setRecords(res.records); setTotal(res.total) })
      .catch(() => Taro.showToast({ title: '记录加载失败', icon: 'none' }))
      .finally(() => setLoading(false))
  })

  const openDetail = (id: number) => {
    gameApi.getRecord(id)
      .then(setDetail)
      .catch(() => Taro.showToast({ title: '详情加载失败', icon: 'none' }))
  }

  if (detail) {
    const r = detail.record
    return (
      <View className='records'>
        <View className='glass-card records-detail'>
          <Text className={`records-detail__winner ${r.winner === 'WEREWOLF' ? 'records-detail__winner--wolf' : ''}`}>
            {r.winner === 'WEREWOLF' ? '狼人阵营获胜' : '好人阵营获胜'}
          </Text>
          <Text className='records-detail__meta'>
            {r.board_name} · {r.player_count} 人 · {r.day_count} 天 · {fmtDuration(r.duration_seconds)}
          </Text>
          <View className='records-detail__players'>
            {detail.players.map((p) => (
              <View key={p.user_id} className='records-detail__player'>
                <Text className='records-detail__seat'>{p.nickname}</Text>
                <Text className={`records-detail__role ${p.is_winner ? 'records-detail__role--win' : ''}`}>
                  {ROLE_LABELS[p.role] || p.role}{p.alive_at_end ? '' : '（出局）'}
                </Text>
              </View>
            ))}
          </View>
          <View className='records-detail__tl-title'><Text>对局过程</Text></View>
          <ScrollView className='records-detail__tl' scrollY>
            {(r.timeline?.timeline || []).map(renderTimelineItem)}
          </ScrollView>
          <View className='records-detail__back' onClick={() => setDetail(null)}>返回列表</View>
        </View>
      </View>
    )
  }

  return (
    <View className='records'>
      <Text className='records__total'>共 {total} 场对局</Text>
      {loading ? (
        <Text className='records__loading'>加载中...</Text>
      ) : records.length === 0 ? (
        <View className='glass-card records-empty'><Text>还没有对局记录</Text></View>
      ) : (
        records.map((r) => (
          <View key={r.id} className='glass-card record-card'
                onClick={() => openDetail(r.id)}>
            <View className='record-card__row'>
              <Text className={`record-card__winner ${r.winner === 'WEREWOLF' ? 'record-card__winner--wolf' : ''}`}>
                {r.winner === 'WEREWOLF' ? '狼人胜' : '好人胜'}
              </Text>
              <Text className='record-card__board'>{r.board_name}</Text>
            </View>
            <Text className='record-card__meta'>
              房号 {r.room_id} · {r.day_count} 天 · {fmtDuration(r.duration_seconds)}
              {r.created_at ? ` · ${r.created_at.slice(5, 16).replace('T', ' ')}` : ''}
            </Text>
            <Text className='record-card__hint'>点击查看对局过程 ›</Text>
          </View>
        ))
      )}
    </View>
  )
}
