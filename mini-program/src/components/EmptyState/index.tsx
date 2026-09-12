import { View, Text } from '@tarojs/components'
import type { ReactNode } from 'react'
import './EmptyState.scss'

interface EmptyStateProps {
  /** 图标：支持 emoji 字符串（旧用法）或组件节点（如 SVG Icon；渲染于 View 容器） */
  icon?: ReactNode;
  title: string;
  description?: string;
}

export default function EmptyState({ icon = '📭', title, description }: EmptyStateProps) {
  return (
    <View className='empty-state'>
      {/* 字符串走 Text（emoji 字形）；组件节点必须用 View 容器——
          小程序中 Image 等组件不允许嵌套在 Text 内（玻璃光晕 Task 4：
          首页空状态 🔍 换为 <Icon name='search' /> 即走此分支） */}
      {typeof icon === 'string' ? (
        <Text className='empty-icon'>{icon}</Text>
      ) : (
        <View className='empty-icon empty-icon-node'>{icon}</View>
      )}
      <Text className='empty-title'>{title}</Text>
      {description && (
        <Text className='empty-desc'>{description}</Text>
      )}
    </View>
  )
}
