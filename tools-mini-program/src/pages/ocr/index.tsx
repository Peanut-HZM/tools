import { useState } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, Image } from '@tarojs/components'
import { request } from '../../services/request'
import './index.scss'

export default function OCRPage() {
  const [imagePath, setImagePath] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lang, setLang] = useState('ch')

  // 选择图片
  const handleChooseImage = async () => {
    try {
      const res = await Taro.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera']
      })
      setImagePath(res.tempFilePaths[0])
      setResult('')
      setError('')
    } catch (err: any) {
      if (err.errMsg !== 'chooseImage:fail cancel') {
        Taro.showToast({ title: '选择图片失败', icon: 'none' })
      }
    }
  }

  // 识别 — 用 base64 JSON 方式（非文件上传）
  const handleRecognize = async () => {
    if (!imagePath) {
      setError('请先选择图片')
      return
    }
    setLoading(true)
    setError('')
    setResult('')
    try {
      // 读取图片为 base64
      const base64Res = await Taro.getFileSystemManager().readFile({
        filePath: imagePath,
        encoding: 'base64'
      })
      const base64Image = `data:image/jpeg;base64,${base64Res.data}`

      // 发送 JSON 请求
      const res = await request('/tools/ocr/predict', {
        method: 'POST',
        data: { image: base64Image, lang },
        needAuth: false
      })
      const text = res?.text || res?.result || JSON.stringify(res)
      setResult(typeof text === 'string' ? text : JSON.stringify(text, null, 2))
      Taro.showToast({ title: '识别成功', icon: 'success' })
    } catch (err: any) {
      setError(err.message || '识别失败')
    } finally {
      setLoading(false)
    }
  }

  // 复制结果
  const handleCopy = async () => {
    if (!result) return
    try {
      await Taro.setClipboardData({ data: result })
      Taro.showToast({ title: '已复制', icon: 'success' })
    } catch (err) {
      Taro.showToast({ title: '复制失败', icon: 'none' })
    }
  }

  return (
    <View className='ocr-page'>
      {/* 语言选择 */}
      <View className='lang-bar'>
        <Text className={`lang-item ${lang === 'ch' ? 'active' : ''}`} onClick={() => setLang('ch')}>中文</Text>
        <Text className={`lang-item ${lang === 'en' ? 'active' : ''}`} onClick={() => setLang('en')}>English</Text>
      </View>

      {/* 图片选择区 */}
      <View className='image-section' onClick={handleChooseImage}>
        {imagePath ? (
          <Image src={imagePath} mode='aspectFit' className='preview-image' />
        ) : (
          <View className='upload-placeholder'>
            <Text className='upload-hint'>点击拍照或选择图片</Text>
          </View>
        )}
      </View>

      {/* 识别按钮 */}
      <View className='action-bar'>
        <button className='recognize-btn' onClick={handleRecognize} disabled={loading || !imagePath}>
          {loading ? '识别中...' : '开始识别'}
        </button>
      </View>

      {/* 错误提示 */}
      {error && (
        <View className='error-section'>
          <Text className='error-text'>{error}</Text>
        </View>
      )}

      {/* 识别结果 */}
      {result && (
        <View className='result-section'>
          <View className='result-header'>
            <Text className='result-title'>识别结果</Text>
            <Text className='copy-link' onClick={handleCopy}>复制</Text>
          </View>
          <View className='result-content'>
            <Text className='result-text' selectable>{result}</Text>
          </View>
        </View>
      )}
    </View>
  )
}
