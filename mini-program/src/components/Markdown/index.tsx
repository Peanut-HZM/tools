import { View, Text, RichText } from '@tarojs/components'
import { marked } from 'marked'
import './index.scss'

interface MarkdownProps {
  content: string
}

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

export default function Markdown({ content }: MarkdownProps) {
  if (!content) {
    return (
      <View className='markdown-renderer'>
        <Text className='markdown-placeholder'>正在输入...</Text>
      </View>
    )
  }

  try {
    const html = marked(content)

    return (
      <View className='markdown-renderer'>
        <RichText nodes={html} />
      </View>
    )
  } catch (e) {
    console.error('[Markdown] 渲染失败:', e)
    return (
      <View className='markdown-renderer'>
        <Text className='message-text'>{content}</Text>
      </View>
    )
  }
}
