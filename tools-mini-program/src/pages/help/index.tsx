import Taro from '@tarojs/taro'
import { View, Text } from '@tarojs/components'
import './index.scss'

interface FAQItem {
  question: string
  answer: string
}

const faqData: FAQItem[] = [
  {
    question: '如何使用工具箱？',
    answer: '在工具首页选择你需要的工具，点击对应工具卡片即可进入工具页面。目前支持的工具有 JSON 格式化、日历、密钥生成器、OCR 识别、ASR 语音识别、HTTP API 客户端等。'
  },
  {
    question: '如何登录/注册？',
    answer: '点击底部"我的"tab，再点击"登录/注册"按钮进入登录页。新用户点击"注册"按钮即可创建账号。登录状态会自动保存。'
  },
  {
    question: 'OCR 识别支持哪些语言？',
    answer: '目前支持中文（ch）和英文（en）两种语言的识别。选择对应的语言可以提高识别准确率。'
  },
  {
    question: 'ASR 语音识别最长支持多长录音？',
    answer: '单次录音最长支持 60 秒。建议分段录制以获得更好的识别效果。'
  },
  {
    question: '文件传输支持哪些文件类型？',
    answer: '支持大多数常见文件类型，包括图片、PDF、Word 文档、Excel 表格、文本文件等。单个文件大小限制请参考后端配置。'
  },
  {
    question: 'HTTP 客户端支持哪些请求方法？',
    answer: '支持 GET、POST、PUT、DELETE、PATCH 五种请求方法。请求体支持 JSON 格式。'
  },
  {
    question: '数据是否安全？',
    answer: '所有数据传输均通过 HTTPS 加密，密码使用哈希存储。修改密码后需要重新登录。'
  }
]

export default function HelpPage() {
  const version = '1.0.0'

  const handleCopyVersion = async () => {
    try {
      await Taro.setClipboardData({ data: `工具箱小程序 v${version}` })
      Taro.showToast({ title: '已复制', icon: 'success' })
    } catch (err) {
      Taro.showToast({ title: '复制失败', icon: 'none' })
    }
  }

  return (
    <View className='help-page'>
      {/* 常见问题 */}
      <View className='section'>
        <Text className='section-title'>常见问题</Text>
        {faqData.map((item, index) => (
          <View key={index} className='faq-item'>
            <Text className='faq-question'>{item.question}</Text>
            <Text className='faq-answer'>{item.answer}</Text>
          </View>
        ))}
      </View>

      {/* 关于 */}
      <View className='section'>
        <Text className='section-title'>关于</Text>
        <View className='about-item' onClick={handleCopyVersion}>
          <Text className='about-label'>版本</Text>
          <Text className='about-value'>v{version}（点击复制）</Text>
        </View>
        <View className='about-item'>
          <Text className='about-label'>技术栈</Text>
          <Text className='about-value'>Taro 4 + React 18 + TypeScript</Text>
        </View>
      </View>
    </View>
  )
}
