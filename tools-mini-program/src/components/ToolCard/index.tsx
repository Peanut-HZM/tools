import { View, Text, Image } from '@tarojs/components'
import type { Tool } from '../../types'
import './ToolCard.scss'

// Font Awesome 图标名到 Emoji 的映射
const FA_TO_EMOJI: Record<string, string> = {
  'fa-file-image': '🖼️',      // OCR 文字识别
  'fa-microphone': '🎤',      // 语音识别
  'fa-share-alt': '🔗',       // CrossShare
  'fa-calendar-alt': '📅',    // 万年历
  'fa-plug': '🔌',            // HTTP API 客户端
  'fa-code': '💻',            // JSON 格式化
  'fa-key': '🔑',             // 密钥生成器
  'fa-robot': '🤖',           // AI 相关
  'fa-image': '🖼️',          // 图片相关
  'fa-music': '🎵',           // 音频相关
  'fa-video': '🎥',           // 视频相关
  'fa-database': '🗄️',       // 数据库工具
  'fa-terminal': '⌨️',        // 终端/SSH
  'fa-edit': '✏️',            // 编辑器
  'fa-lock': '🔒',            // 加密/密码
  'fa-shield-alt': '🛡️',     // 安全相关
  'fa-globe': '🌐',           // 网络相关
  'fa-download': '📥',        // 下载工具
  'fa-upload': '📤',          // 上传工具
  'fa-search': '🔍',          // 搜索工具
  'fa-cog': '⚙️',             // 设置/工具
  'fa-tools': '🛠️',           // 工具箱
  'fa-lightbulb': '💡',       // 学习/创意
}

interface ToolCardProps {
  tool: Tool;
  onClick: () => void;
}

// 将 icon 字段转换为 emoji
function getToolEmoji(icon?: string): string {
  if (!icon) return '🔧'
  // 如果是 Font Awesome 图标名
  if (icon.startsWith('fa-')) {
    return FA_TO_EMOJI[icon] || '🔧'
  }
  // 如果已经是 emoji 或其他字符，直接返回
  return icon
}

export default function ToolCard({ tool, onClick }: ToolCardProps) {
  return (
    <View className='tool-card' onClick={onClick}>
      <View className='tool-card-icon'>
        <Text className='tool-card-emoji'>{getToolEmoji(tool.icon)}</Text>
      </View>
      <View className='tool-card-info'>
        <Text className='tool-card-name' numberOfLines={1}>{tool.title}</Text>
        <Text className='tool-card-desc' numberOfLines={2}>{tool.description}</Text>
      </View>
    </View>
  )
}
