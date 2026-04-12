import { View } from '@tarojs/components'
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
  if (!content) return null

  const html = marked(content)

  return (
    <View className='markdown-renderer'>
      <rich-text nodes={html} />
    </View>
  )
}
