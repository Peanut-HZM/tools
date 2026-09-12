import { useState } from 'react'
import { View, Text, Button, Switch, Slider } from '@tarojs/components'
import Taro from '@tarojs/taro'
import './index.scss'

/**
 * 密钥生成页 — 玻璃光晕换肤（阶段⑧-⑨ Task 6）：
 * - 配置/结果容器套全局 .glass-card（背景/描边/投影/磨砂模糊，见 styles/_glass.scss）；
 * - 主按钮（生成密钥）套 .btn-primary 品牌渐变，按压反馈走 hover-class='btn-primary-hover'；
 * - 生成/复制逻辑不变。
 */

export default function KeyGenerator() {
  const [keyLength, setKeyLength] = useState(32)
  const [useUpper, setUseUpper] = useState(true)
  const [useLower, setUseLower] = useState(true)
  const [useNumbers, setUseNumbers] = useState(true)
  const [useSymbols, setUseSymbols] = useState(true)
  const [keyCount, setKeyCount] = useState(5)
  const [generatedKeys, setGeneratedKeys] = useState<string[]>([])

  // 生成密钥
  const handleGenerate = () => {
    const chars: string[] = []

    if (useUpper) chars.push('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    if (useLower) chars.push('abcdefghijklmnopqrstuvwxyz')
    if (useNumbers) chars.push('0123456789')
    if (useSymbols) chars.push('!@#$%^&*()-_=+[]{}|;:,.<>?')

    if (chars.length === 0) {
      Taro.showToast({ title: '请至少选择一种字符类型', icon: 'none' })
      return
    }

    const allChars = chars.join('')
    const keys: string[] = []

    for (let i = 0; i < keyCount; i++) {
      let key = ''
      for (let j = 0; j < keyLength; j++) {
        key += allChars[Math.floor(Math.random() * allChars.length)]
      }
      keys.push(key)
    }

    setGeneratedKeys(keys)
    Taro.showToast({ title: `已生成 ${keyCount} 个密钥`, icon: 'success' })
  }

  // 生成 UUID
  const handleGenerateUUID = () => {
    const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0
      const v = c === 'x' ? r : (r & 0x3) | 0x8
      return v.toString(16)
    })
    setGeneratedKeys([uuid])
    Taro.showToast({ title: 'UUID 已生成', icon: 'success' })
  }

  // 复制单个密钥
  const handleCopy = async (key: string) => {
    try {
      await Taro.setClipboardData({ data: key })
      Taro.showToast({ title: '已复制', icon: 'success' })
    } catch (err) {
      Taro.showToast({ title: '复制失败', icon: 'none' })
    }
  }

  // 复制全部
  const handleCopyAll = async () => {
    try {
      await Taro.setClipboardData({ data: generatedKeys.join('\n') })
      Taro.showToast({ title: '已复制全部', icon: 'success' })
    } catch (err) {
      Taro.showToast({ title: '复制失败', icon: 'none' })
    }
  }

  // 清空
  const handleClear = () => {
    setGeneratedKeys([])
  }

  return (
    <View className='key-generator-page'>
      {/* 配置区域（玻璃卡片） */}
      <View className='config-section glass-card'>
        <Text className='section-title'>密钥配置</Text>

        {/* 密钥长度 */}
        <View className='config-item'>
          <Text className='config-label'>密钥长度：{keyLength}</Text>
          <Slider
            min={8}
            max={128}
            value={keyLength}
            onChange={(e) => setKeyLength(e.detail.value)}
            activeColor='var(--color-primary)'
            backgroundColor='var(--bg-tertiary)'
            blockSize={20}
          />
        </View>

        {/* 生成数量 */}
        <View className='config-item'>
          <Text className='config-label'>生成数量：{keyCount}</Text>
          <Slider
            min={1}
            max={20}
            value={keyCount}
            onChange={(e) => setKeyCount(e.detail.value)}
            activeColor='var(--color-primary)'
            backgroundColor='var(--bg-tertiary)'
            blockSize={20}
          />
        </View>

        {/* 字符选项 */}
        <View className='options-grid'>
          <View className='option-item' onClick={() => setUseUpper(!useUpper)}>
            <Switch checked={useUpper} color='var(--color-primary)' />
            <Text className='option-label'>大写字母</Text>
          </View>
          <View className='option-item' onClick={() => setUseLower(!useLower)}>
            <Switch checked={useLower} color='var(--color-primary)' />
            <Text className='option-label'>小写字母</Text>
          </View>
          <View className='option-item' onClick={() => setUseNumbers(!useNumbers)}>
            <Switch checked={useNumbers} color='var(--color-primary)' />
            <Text className='option-label'>数字</Text>
          </View>
          <View className='option-item' onClick={() => setUseSymbols(!useSymbols)}>
            <Switch checked={useSymbols} color='var(--color-primary)' />
            <Text className='option-label'>特殊符号</Text>
          </View>
        </View>
      </View>

      {/* 生成按钮：主按钮走品牌渐变 .btn-primary，次按钮走玻璃描边 */}
      <View className='button-group'>
        <Button className='generate-btn btn-primary' hoverClass='btn-primary-hover' onClick={handleGenerate}>
          生成密钥
        </Button>
        <Button className='uuid-btn' onClick={handleGenerateUUID}>
          生成 UUID
        </Button>
      </View>

      {/* 生成结果（玻璃卡片） */}
      {generatedKeys.length > 0 && (
        <View className='result-section glass-card'>
          <View className='result-header'>
            <Text className='result-title'>生成结果 ({generatedKeys.length})</Text>
            <View className='result-actions'>
              <Text className='action-link' onClick={handleCopyAll}>复制全部</Text>
              <Text className='action-link action-clear' onClick={handleClear}>清空</Text>
            </View>
          </View>

          <View className='keys-list'>
            {generatedKeys.map((key, idx) => (
              <View key={idx} className='key-item'>
                <Text className='key-index'>{idx + 1}</Text>
                <Text className='key-text' selectable>{key}</Text>
                <Text className='key-copy' onClick={() => handleCopy(key)}>复制</Text>
              </View>
            ))}
          </View>
        </View>
      )}
    </View>
  )
}
