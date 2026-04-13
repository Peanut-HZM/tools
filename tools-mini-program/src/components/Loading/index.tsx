import { View, Text } from '@tarojs/components'
import './Loading.scss'

interface LoadingProps {
  text?: string;
}

export default function Loading({ text = '加载中...' }: LoadingProps) {
  return (
    <View className='loading'>
      <View className='loading-spinner' />
      <Text className='loading-text'>{text}</Text>
    </View>
  )
}
