import { View, Text } from '@tarojs/components'
import './Loading.scss'

/**
 * 加载组件 — 玻璃光晕换肤（阶段⑧-⑨ Task 7）：
 * spinner 配色对齐 Web/Admin 标准（--border-accent 描边环 + 透明顶口），
 * 尺寸保持 48rpx 不变。
 */

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
