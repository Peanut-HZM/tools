import { useState } from 'react'
import Taro, { useDidShow } from '@tarojs/taro'
import { View, Text, Textarea, Button } from '@tarojs/components'
import './index.scss'

/**
 * 玻璃光晕换肤（阶段⑧-⑨ Task 6）：
 * - 卡片容器套全局 .glass-card（半透明底+发丝描边+磨砂模糊+投影，见 styles/_glass.scss），
 *   本地样式只保留布局/圆角，勿重复定义背景以免击穿玻璃质感；
 * - 主按钮（格式化）套 .btn-primary 品牌渐变，按压反馈走 hover-class='btn-primary-hover'；
 * - 表单逻辑/API/状态管理不变。
 */

export default function JsonFormatter() {
  const [input, setInput] = useState('')
  const [output, setOutput] = useState('')
  const [error, setError] = useState('')

  useDidShow(() => {
    // 检查剪贴板是否有 JSON
    const clipboard = Taro.getStorageSync('clipboard_json')
    if (clipboard) {
      setInput(clipboard)
    }
  })

  // 格式化 JSON
  const handleFormat = () => {
    if (!input.trim()) {
      setError('请输入 JSON 内容')
      return
    }

    try {
      const parsed = JSON.parse(input)
      const formatted = JSON.stringify(parsed, null, 2)
      setOutput(formatted)
      setError('')
      Taro.showToast({ title: '格式化成功', icon: 'success' })
    } catch (e: any) {
      setError(`JSON 解析错误：${e.message}`)
      setOutput('')
    }
  }

  // 压缩 JSON
  const handleCompress = () => {
    if (!input.trim()) {
      setError('请输入 JSON 内容')
      return
    }

    try {
      const parsed = JSON.parse(input)
      const compressed = JSON.stringify(parsed)
      setOutput(compressed)
      setError('')
      Taro.showToast({ title: '压缩成功', icon: 'success' })
    } catch (e: any) {
      setError(`JSON 解析错误：${e.message}`)
      setOutput('')
    }
  }

  // 复制结果
  const handleCopy = async () => {
    if (!output) return
    try {
      await Taro.setClipboardData({ data: output })
      Taro.showToast({ title: '已复制', icon: 'success' })
    } catch (err) {
      Taro.showToast({ title: '复制失败', icon: 'none' })
    }
  }

  // 清空
  const handleClear = () => {
    setInput('')
    setOutput('')
    setError('')
  }

  return (
    <View className='json-formatter-page'>
      {/* 输入区域（玻璃卡片） */}
      <View className='section glass-card'>
        <View className='section-header'>
          <Text className='section-title'>输入</Text>
          <Text className='clear-btn' onClick={handleClear}>清空</Text>
        </View>
        <Textarea
          className='input-area'
          value={input}
          onInput={(e) => setInput(e.detail.value)}
          placeholder='在此粘贴 JSON 或输入 JSON 内容...'
          maxlength={-1}
          autoHeight
        />
      </View>

      {/* 操作按钮：主按钮走品牌渐变 .btn-primary，次按钮走玻璃描边 */}
      <View className='action-buttons'>
        <Button className='action-btn format-btn btn-primary' hoverClass='btn-primary-hover' onClick={handleFormat}>
          格式化
        </Button>
        <Button className='action-btn compress-btn' onClick={handleCompress}>
          压缩
        </Button>
      </View>

      {/* 错误提示 */}
      {error && (
        <View className='error-section'>
          <Text className='error-text'>{error}</Text>
        </View>
      )}

      {/* 输出区域（玻璃卡片） */}
      {output && (
        <View className='section glass-card'>
          <View className='section-header'>
            <Text className='section-title'>输出</Text>
            <Text className='copy-btn' onClick={handleCopy}>复制</Text>
          </View>
          <View className='output-area'>
            <Text className='output-text' selectable>{output}</Text>
          </View>
        </View>
      )}
    </View>
  )
}
