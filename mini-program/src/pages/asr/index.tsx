import { useState, useRef } from 'react'
import Taro from '@tarojs/taro'
import { View, Text } from '@tarojs/components'
import { uploadFile } from '../../services/request'
import './index.scss'

export default function ASRPage() {
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [result, setResult] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [lang, setLang] = useState('zh')
  const timerRef = useRef<any>(null)
  const recorderRef = useRef<any>(null)

  // 开始/停止录音
  const toggleRecording = async () => {
    if (isRecording) {
      // 停止录音
      stopRecording()
    } else {
      // 开始录音
      startRecording()
    }
  }

  const startRecording = () => {
    try {
      recorderRef.current = Taro.getRecorderManager()

      recorderRef.current.onStart(() => {
        setIsRecording(true)
        setRecordingTime(0)
        timerRef.current = setInterval(() => {
          setRecordingTime(prev => prev + 1)
        }, 1000)
      })

      recorderRef.current.onStop(async (res) => {
        clearInterval(timerRef.current)
        setIsRecording(false)
        setRecordingTime(0)

        // 上传并识别
        await handleRecognize(res.tempFilePath)
      })

      recorderRef.current.onError((err) => {
        clearInterval(timerRef.current)
        setIsRecording(false)
        Taro.showToast({ title: '录音失败', icon: 'none' })
      })

      recorderRef.current.start({
        duration: 60000,
        sampleRate: 16000,
        numberOfChannels: 1,
        encodeBitRate: 96000,
        format: 'mp3'
      })
    } catch (err: any) {
      Taro.showToast({ title: '无法启动录音', icon: 'none' })
    }
  }

  const stopRecording = () => {
    if (recorderRef.current) {
      recorderRef.current.stop()
    }
  }

  // 语音识别
  const handleRecognize = async (filePath: string) => {
    if (!filePath) return

    setLoading(true)
    setError('')
    setResult('')

    try {
      Taro.showLoading({ title: '识别中...' })
      const res = await uploadFile('/asr/predict', filePath, 'file', { language: lang }, false)
      const text = res?.text || res?.result || JSON.stringify(res)
      setResult(typeof text === 'string' ? text : JSON.stringify(text, null, 2))
      Taro.hideLoading()
      Taro.showToast({ title: '识别成功', icon: 'success' })
    } catch (err: any) {
      Taro.hideLoading()
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

  // 格式化时间 mm:ss
  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0')
    const s = (seconds % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }

  return (
    <View className='asr-page'>
      {/* 语言选择 */}
      <View className='lang-bar'>
        <Text className={`lang-item ${lang === 'zh' ? 'active' : ''}`} onClick={() => setLang('zh')}>中文</Text>
        <Text className={`lang-item ${lang === 'en' ? 'active' : ''}`} onClick={() => setLang('en')}>English</Text>
      </View>

      {/* 录音按钮 */}
      <View className='record-section'>
        <View className={`record-btn ${isRecording ? 'recording' : ''}`} onClick={toggleRecording}>
          <View className={`record-icon ${isRecording ? 'pulse' : ''}`}>
            {isRecording ? '⏹' : '🎙'}
          </View>
          <Text className='record-label'>
            {isRecording ? '点击停止' : '点击录音'}
          </Text>
        </View>
        {isRecording && (
          <Text className='record-time'>{formatTime(recordingTime)}</Text>
        )}
      </View>

      {/* 加载状态 */}
      {loading && (
        <View className='loading-section'>
          <Text className='loading-text'>正在识别中...</Text>
        </View>
      )}

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
