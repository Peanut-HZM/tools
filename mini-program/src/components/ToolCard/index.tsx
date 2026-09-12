import { View, Text, Image } from '@tarojs/components'
import type { Tool } from '../../types'
import Icon, { resolveIconName } from '../Icon'
import { tintColorOf } from '../../utils/tint'
import './ToolCard.scss'

interface ToolCardProps {
  tool: Tool;
  onClick: () => void;
}

/**
 * 工具卡片（玻璃光晕改版 Task 3）：
 * - 图标不再使用 emoji，改为 SVG 线性 Icon 组件（custom_icon_url 优先，逻辑不变）
 * - 图标底色走 tint 色板（styles/_glass.scss），由后端 iconColor 解析类名与同源色值
 * - 卡片容器套 .glass-card 玻璃工具类（背景/描边/高光），本地样式只保留布局
 */
export default function ToolCard({ tool, onClick }: ToolCardProps) {
  const hasCustomIcon = !!tool.custom_icon_url
  // tint 底 + 同源图标色（Image 不继承 CSS color，色值需以 prop 烘入 SVG）
  const tint = tintColorOf(tool.iconColor)
  const iconName = resolveIconName(tool.icon)

  return (
    <View className='tool-card glass-card' onClick={onClick}>
      {tool.require_login && (
        <View className='tool-card-login-badge'>
          <Text className='tool-card-login-badge-text'>需登录</Text>
        </View>
      )}
      <View className={`tool-card-icon ${tint.className}`}>
        {hasCustomIcon ? (
          <Image
            src={tool.custom_icon_url!}
            className='tool-card-custom-icon'
            mode='aspectFit'
          />
        ) : (
          <Icon name={iconName} size={22} color={tint.color} />
        )}
      </View>
      <View className='tool-card-info'>
        <Text className='tool-card-name' numberOfLines={1}>{tool.title}</Text>
        <Text className='tool-card-desc' numberOfLines={2}>{tool.description}</Text>
      </View>
    </View>
  )
}
