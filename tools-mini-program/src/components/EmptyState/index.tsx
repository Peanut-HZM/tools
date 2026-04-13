import { View, Text } from '@tarojs/components'
import './EmptyState.scss'

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
}

export default function EmptyState({ icon = '📭', title, description }: EmptyStateProps) {
  return (
    <View className='empty-state'>
      <Text className='empty-icon'>{icon}</Text>
      <Text className='empty-title'>{title}</Text>
      {description && (
        <Text className='empty-desc'>{description}</Text>
      )}
    </View>
  )
}
