import { useMemo, useRef, useState } from 'react'
import Taro, { useDidShow } from '@tarojs/taro'
import { View, Text, ScrollView } from '@tarojs/components'
import { toolApi } from '../../services/tool'
import type { Tool } from '../../types'
import ToolCard from '../../components/ToolCard'
import SearchBar from '../../components/SearchBar'
import Loading from '../../components/Loading'
import EmptyState from '../../components/EmptyState'
import Icon from '../../components/Icon'
import './index.scss'

const CATEGORY_LABELS: Record<string, string> = {
  all: '全部',
  dev: '开发',
  media: '媒体',
  text: '文本',
  ai: 'AI',
  utility: '实用',
  share: '协作',
  life: '生活',
  game: '游戏',
}

function categoryLabel(key: string): string {
  return CATEGORY_LABELS[key] || key
}

export default function Index() {
  const [tools, setTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  // 已成功加载过：再次 show 时静默刷新，不切 loading（切 loading 会重渲染整页、把滚动位置打回顶部）
  const loadedRef = useRef(false)

  useDidShow(() => {
    loadTools()
  })

  const loadTools = async () => {
    // 首次加载才显示骨架；后续 show 静默刷新，避免列表闪烁与滚动复位
    if (!loadedRef.current) setLoading(true)
    try {
      const data = await toolApi.getTools()
      setTools(data)
      loadedRef.current = true
    } catch (err) {
      console.error('Failed to load tools:', err)
      Taro.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  // 分类从真实数据生成，避免硬编码与后端不一致
  const categories = useMemo(() => {
    const counts = new Map<string, number>()
    tools.forEach(tool => {
      const key = tool.category || 'utility'
      counts.set(key, (counts.get(key) || 0) + 1)
    })
    return [
      { key: 'all', label: '全部', count: tools.length },
      ...[...counts.entries()]
        .sort((a, b) => b[1] - a[1])
        .map(([key, count]) => ({ key, label: categoryLabel(key), count })),
    ]
  }, [tools])

  const filteredTools = useMemo(() => {
    const kw = searchKeyword.trim().toLowerCase()
    return tools.filter(tool => {
      if (selectedCategory !== 'all' && (tool.category || 'utility') !== selectedCategory) {
        return false
      }
      if (!kw) return true
      return (
        tool.title.toLowerCase().includes(kw) ||
        tool.description.toLowerCase().includes(kw)
      )
    })
  }, [tools, selectedCategory, searchKeyword])

  const handleToolClick = (tool: Tool) => {
    toolApi.trackVisit(tool.id).catch(() => {})

    const token = Taro.getStorageSync('auth_token')
    if (tool.require_login && !token) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      setTimeout(() => {
        Taro.redirectTo({ url: '/pages/login/index?redirect=/pages/index/index' })
      }, 1500)
      return
    }

    const path = tool.path
    if (path) {
      Taro.navigateTo({ url: path }).catch(() => {
        Taro.redirectTo({ url: path })
      })
    }
  }

  return (
    <View className='index-page'>
      <View className='index-hero'>
        <View className='index-hero-row'>
          <View>
            <Text className='index-hero-eyebrow'>开发者工作台</Text>
            <Text className='index-hero-title'>工具箱</Text>
          </View>
          <View className='index-hero-mark'>
            <Icon name='tools' size={22} color='#22C55E' />
          </View>
        </View>

        <View className='index-meta-row'>
          <View className='index-meta-chip'>
            <Text className='index-meta-value'>{tools.length}</Text>
            <Text className='index-meta-label'>个工具</Text>
          </View>
          <View className='index-meta-chip'>
            <Text className='index-meta-value'>{Math.max(categories.length - 1, 0)}</Text>
            <Text className='index-meta-label'>个分类</Text>
          </View>
          <View className='index-meta-chip index-meta-chip--status'>
            <View className='index-status-dot' />
            <Text className='index-meta-label'>即开即用</Text>
          </View>
        </View>
      </View>

      <SearchBar
        value={searchKeyword}
        onChange={setSearchKeyword}
        placeholder='搜索工具名称或功能...'
      />

      {/* 页面级原生滚动：不再用「整页 scroll-view」包住列表。
          原因：微信小程序里 scroll-view 依赖确定高度（flex:1 + padding 计算不稳），
          且内层横向 scroll-view 会吞掉纵向手势，表现为「滚不动 / 卡住」。 */}
      <View className='tools-body'>
        <ScrollView className='category-scroll' scrollX>
          <View className='category-row'>
            {categories.map(category => (
              <View
                key={category.key}
                className={`category-chip ${selectedCategory === category.key ? 'category-chip--active' : ''}`}
                onClick={() => setSelectedCategory(category.key)}
              >
                <Text>{category.label}</Text>
                <Text className='category-count'>{category.count}</Text>
              </View>
            ))}
          </View>
        </ScrollView>

        {loading ? (
          <Loading text='加载工具列表...' />
        ) : filteredTools.length === 0 ? (
          <EmptyState
            icon={<Icon name='search' size={44} color='#6B7A92' />}
            title={searchKeyword ? '未找到相关工具' : '该分类暂无工具'}
            description={searchKeyword ? '试试其他关键词或切换分类' : '切换分类看看其他工具'}
          />
        ) : (
          <View className='tools-grid'>
            {filteredTools.map(tool => (
              <ToolCard
                key={tool.id}
                tool={tool}
                onClick={() => handleToolClick(tool)}
              />
            ))}
          </View>
        )}
        <View className='safe-area-bottom' />
      </View>
    </View>
  )
}