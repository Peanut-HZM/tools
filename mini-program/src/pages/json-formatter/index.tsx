import { useState } from 'react'
import Taro, { useDidShow } from '@tarojs/taro'
import { View, Text, Textarea, Button } from '@tarojs/components'
import './index.scss'

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
      {/* 输入区域 */}
      <View className='section'>
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

      {/* 操作按钮 */}
      <View className='action-buttons'>
        <button className='action-btn format-btn' onClick={handleFormat}>
          格式化
        </button>
        <button className='action-btn compress-btn' onClick={handleCompress}>
          压缩
        </button>
      </View>

      {/* 错误提示 */}
      {error && (
        <View className='error-section'>
          <Text className='error-text'>{error}</Text>
        </View>
      )}

      {/* 输出区域 */}
      {output && (
        <View className='section'>
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
