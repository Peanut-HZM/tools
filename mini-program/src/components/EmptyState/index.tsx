import { View, Text } from '@tarojs/components'
import type { ReactNode } from 'react'
import Icon from '../Icon'
import './EmptyState.scss'

/**
 * 空状态组件 — 玻璃光晕换肤（阶段⑧-⑨ Task 7）：
 * 默认图标由 emoji 📭 改为 <Icon name='file' size={48} />（品牌默认色）；
 * icon prop 仍兼容字符串（emoji 旧用法）与自定义组件节点。
 */

interface EmptyStateProps {
  /** 图标：支持 emoji 字符串（旧用法）或组件节点（如 SVG Icon；渲染于 View 容器），缺省为文件图标 */
  icon?: ReactNode;
  title: string;
  description?: string;
}

export default function EmptyState({ icon = <Icon name='file' size={48} />, title, description }: EmptyStateProps) {
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
