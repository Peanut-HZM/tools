import { useState } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, Textarea, Input, Picker } from '@tarojs/components'
import { request } from '../../services/request'
import './index.scss'

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'

interface HeaderItem {
  key: string
  value: string
}

export default function HttpClientPage() {
  const [url, setUrl] = useState('')
  const [method, setMethod] = useState<HttpMethod>('GET')
  const [headers, setHeaders] = useState<HeaderItem[]>([{ key: '', value: '' }])
  const [body, setBody] = useState('')
  const [response, setResponse] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'headers' | 'body'>('headers')
  const [responseTab, setResponseTab] = useState<'body' | 'headers' | 'status'>('body')

  const methods: HttpMethod[] = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']

  // 添加 Header 行
  const addHeader = () => {
    setHeaders([...headers, { key: '', value: '' }])
  }

  // 更新 Header
  const updateHeader = (index: number, field: 'key' | 'value', value: string) => {
    const newHeaders = [...headers]
    newHeaders[index] = { ...newHeaders[index], [field]: value }
    setHeaders(newHeaders)
  }

  // 删除 Header
  const removeHeader = (index: number) => {
    if (headers.length <= 1) return
    setHeaders(headers.filter((_, i) => i !== index))
  }

  // 发送请求
  const handleSend = async () => {
    if (!url.trim()) {
      setError('请输入 URL')
      return
    }

    // 验证 JSON Body
    if (method !== 'GET' && body.trim()) {
      try {
        JSON.parse(body)
      } catch (e: any) {
        setError(`请求体 JSON 格式错误：${e.message}`)
        return
      }
    }

    setLoading(true)
    setError('')
    setResponse(null)

    try {
      // 构建请求头
      const requestHeaders: Record<string, string> = { 'Content-Type': 'application/json' }
      headers.forEach(h => {
        if (h.key.trim()) {
          requestHeaders[h.key.trim()] = h.value
        }
      })

      const startTime = Date.now()
      const res = await Taro.request({
        url: url.startsWith('http') ? url : `https://${url}`,
        method: method as any,
        data: method !== 'GET' && body.trim() ? JSON.parse(body) : undefined,
        header: requestHeaders,
        timeout: 30000
      })
      const duration = Date.now() - startTime

      // 尝试解析响应体
      let parsedBody = res.data
      if (typeof res.data === 'string') {
        try {
          parsedBody = JSON.parse(res.data)
        } catch {
          parsedBody = res.data
        }
      }

      setResponse({
        statusCode: res.statusCode,
        headers: res.header || {},
        body: parsedBody,
        duration
      })
    } catch (err: any) {
      setError(err.message || '请求失败')
    } finally {
      setLoading(false)
    }
  }

  // 获取状态码颜色
  const getStatusColor = (code: number) => {
    if (code >= 200 && code < 300) return 'var(--color-success)'
    if (code >= 300 && code < 400) return 'var(--color-info)'
    if (code >= 400 && code < 500) return 'var(--color-warning)'
    if (code >= 500) return 'var(--color-danger)'
    return 'var(--text-secondary)'
  }

  return (
    <View className='http-client-page'>
      {/* URL 输入 */}
      <View className='url-bar'>
        <Picker mode='selector' range={methods} value={methods.indexOf(method)} onChange={(e) => setMethod(methods[e.detail.value])}>
          <View className='method-picker'>{method}</View>
        </Picker>
        <Input
          className='url-input'
          value={url}
          onInput={(e) => setUrl(e.detail.value)}
          placeholder='输入 URL...'
          confirmType='send'
          onConfirm={handleSend}
        />
      </View>

      {/* 请求参数折叠面板 */}
      <View className='request-panel'>
        <View className='panel-tabs'>
          <Text className={`tab ${activeTab === 'headers' ? 'active' : ''}`} onClick={() => setActiveTab('headers')}>Headers</Text>
          <Text className={`tab ${activeTab === 'body' ? 'active' : ''}`} onClick={() => setActiveTab('body')}>Body</Text>
        </View>

        {activeTab === 'headers' && (
          <View className='headers-editor'>
            {headers.map((h, i) => (
              <View key={i} className='header-row'>
                <Input
                  className='header-input'
                  placeholder='Key'
                  value={h.key}
                  onInput={(e) => updateHeader(i, 'key', e.detail.value)}
                />
                <Input
                  className='header-input'
                  placeholder='Value'
                  value={h.value}
                  onInput={(e) => updateHeader(i, 'value', e.detail.value)}
                />
                <Text className='remove-btn' onClick={() => removeHeader(i)}>×</Text>
              </View>
            ))}
            <Text className='add-btn' onClick={addHeader}>+ 添加 Header</Text>
          </View>
        )}

        {activeTab === 'body' && method !== 'GET' && (
          <View className='body-editor'>
            <Textarea
              className='body-textarea'
              value={body}
              onInput={(e) => setBody(e.detail.value)}
              placeholder='JSON 格式请求体...'
              maxlength={-1}
            />
          </View>
        )}

        {activeTab === 'body' && method === 'GET' && (
          <View className='body-hint'>
            <Text className='hint-text'>GET 请求无需请求体</Text>
          </View>
        )}
      </View>

      {/* 发送按钮 */}
      <View className='send-bar'>
        <button className='send-btn' onClick={handleSend} disabled={loading}>
          {loading ? '发送中...' : '发送请求'}
        </button>
      </View>

      {/* 错误提示 */}
      {error && (
        <View className='error-section'>
          <Text className='error-text'>{error}</Text>
        </View>
      )}

      {/* 响应区域 */}
      {response && (
        <View className='response-section'>
          <View className='response-tabs'>
            <Text className={`resp-tab ${responseTab === 'status' ? 'active' : ''}`} onClick={() => setResponseTab('status')}>
              状态 <Text style={{ color: getStatusColor(response.statusCode) }}>{response.statusCode}</Text>
            </Text>
            <Text className={`resp-tab ${responseTab === 'body' ? 'active' : ''}`} onClick={() => setResponseTab('body')}>Body</Text>
            <Text className={`resp-tab ${responseTab === 'headers' ? 'active' : ''}`} onClick={() => setResponseTab('headers')}>Headers</Text>
          </View>

          <View className='response-content'>
            {responseTab === 'status' && (
              <View className='status-info'>
                <Text className='status-line'>状态码：<Text style={{ color: getStatusColor(response.statusCode), fontWeight: 600 }}>{response.statusCode}</Text></Text>
                <Text className='status-line'>耗时：{response.duration}ms</Text>
              </View>
            )}
            {responseTab === 'body' && (
              <Text className='response-text' selectable>
                {typeof response.body === 'string' ? response.body : JSON.stringify(response.body, null, 2)}
              </Text>
            )}
            {responseTab === 'headers' && (
              <Text className='response-text' selectable>
                {JSON.stringify(response.headers, null, 2)}
              </Text>
            )}
          </View>
        </View>
      )}
    </View>
  )
}
