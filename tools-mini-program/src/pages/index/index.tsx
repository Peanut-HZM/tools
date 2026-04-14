import { useState, useEffect } from 'react'
import Taro, { useDidShow } from '@tarojs/taro'
import { View, Text, ScrollView, Image } from '@tarojs/components'
import { toolApi } from '../../services/tool'
import type { Tool, ToolCategory } from '../../types'
import ToolCard from '../../components/ToolCard'
import SearchBar from '../../components/SearchBar'
import Loading from '../../components/Loading'
import EmptyState from '../../components/EmptyState'
import './index.scss'

export default function Index() {
  const [tools, setTools] = useState<Tool[]>([])
  const [filteredTools, setFilteredTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState('')

  useDidShow(() => {
    loadTools()
  })

  const loadTools = async () => {
    setLoading(true)
    try {
      const data = await toolApi.getTools()
      setTools(data)
      setFilteredTools(data)
    } catch (err) {
      console.error('Failed to load tools:', err)
      Taro.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  // 搜索过滤
  useEffect(() => {
    let result = tools

    if (searchKeyword.trim()) {
      const kw = searchKeyword.trim().toLowerCase()
      result = result.filter(t =>
        t.title.toLowerCase().includes(kw) ||
        t.description.toLowerCase().includes(kw)
      )
    }

    setFilteredTools(result)
  }, [searchKeyword, tools])

  const handleSearch = (keyword: string) => {
    setSearchKeyword(keyword)
  }

  const handleToolClick = (tool: Tool) => {
    // 记录访问
    toolApi.trackVisit(tool.id).catch(() => {})

    // 登录拦截
    const token = Taro.getStorageSync('auth_token')
    if (tool.require_login && !token) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      setTimeout(() => {
        Taro.redirectTo({ url: '/pages/login/index?redirect=/pages/index/index' })
      }, 1500)
      return
    }

    if (tool.path) {
      Taro.navigateTo({ url: tool.path }).catch(() => {
        // 页面栈满时降级为 redirectTo
        Taro.redirectTo({ url: tool.path })
      })
    }
  }

  return (
    <View className='index-page'>
      {/* 搜索栏 */}
      <SearchBar
        value={searchKeyword}
        onChange={handleSearch}
        placeholder='搜索工具...'
      />

      {/* 工具列表 */}
      {loading ? (
        <Loading text='加载工具列表...' />
      ) : filteredTools.length === 0 ? (
        <EmptyState
          icon='🔍'
          title={searchKeyword ? '未找到相关工具' : '暂无工具'}
          description={searchKeyword ? '试试其他关键词' : '请联系管理员添加工具'}
        />
      ) : (
        <ScrollView className='tools-scroll' scrollY>
          <View className='tools-grid'>
            {filteredTools.map((tool) => (
              <ToolCard
                key={tool.id}
                tool={tool}
                onClick={() => handleToolClick(tool)}
              />
            ))}
          </View>
        </ScrollView>
      )}
    </View>
  )
}
