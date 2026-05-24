import { useState, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, ScrollView } from '@tarojs/components'
import { fileApi } from '../../../services/crossShare'
import { useAuthGuard } from '../../../hooks'
import './index.scss'

interface FileInfo {
  id: string
  name: string
  size: number
  mime_type: string
  uploaded_at: string
  download_count: number
}

export default function FileTransferPage() {
  useAuthGuard()
  const [files, setFiles] = useState<FileInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [stats, setStats] = useState<{ used: number; total: number; file_count: number } | null>(null)

  useEffect(() => {
    fetchFiles()
  }, [])

  const fetchFiles = async () => {
    setLoading(true)
    try {
      const [filesRes, statsRes] = await Promise.all([
        fileApi.getFiles(),
        fileApi.getStorageStats()
      ])
      setFiles(filesRes?.files || [])
      setStats(statsRes as any)
    } catch (err: any) {
      Taro.showToast({ title: err.message || '加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  // 上传文件
  const handleUpload = async () => {
    try {
      const fileRes = await Taro.chooseMessageFile({
        count: 1,
        type: 'file'
      })
      const file = fileRes.tempFiles[0]

      setUploading(true)
      await fileApi.uploadFile(file.path)
      Taro.showToast({ title: '上传成功', icon: 'success' })
      fetchFiles()
    } catch (err: any) {
      if (err.errMsg !== 'chooseMessageFile:fail cancel') {
        Taro.showToast({ title: err.message || '上传失败', icon: 'none' })
      }
    } finally {
      setUploading(false)
    }
  }

  // 删除文件
  const handleDelete = async (fileId: string) => {
    Taro.showModal({
      title: '确认删除',
      content: '确定要删除这个文件吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await fileApi.deleteFile(fileId)
            Taro.showToast({ title: '已删除', icon: 'success' })
            fetchFiles()
          } catch (err: any) {
            Taro.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  }

  // 下载/分享文件
  const handleDownload = async (file: FileInfo) => {
    try {
      Taro.showLoading({ title: '获取下载链接...' })
      const res = await fileApi.getDownloadUrl(file.id)
      Taro.hideLoading()

      const downloadUrl = (res as any)?.download_url
      if (downloadUrl) {
        // 调用系统分享
        Taro.setClipboardData({ data: downloadUrl })
        Taro.showToast({ title: '下载链接已复制', icon: 'success' })
      }
    } catch (err: any) {
      Taro.hideLoading()
      Taro.showToast({ title: err.message || '获取下载链接失败', icon: 'none' })
    }
  }

  // 获取文件类型图标
  const getFileIcon = (mimeType: string) => {
    if (mimeType?.startsWith('image/')) return '🖼️'
    if (mimeType === 'application/pdf') return '📄'
    if (mimeType?.includes('word') || mimeType?.includes('document')) return '📝'
    if (mimeType?.includes('excel') || mimeType?.includes('spreadsheet')) return '📊'
    if (mimeType?.includes('text')) return '📃'
    return '📁'
  }

  // 格式化文件大小
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  }

  // 格式化时间
  const formatTime = (timeStr: string) => {
    const date = new Date(timeStr)
    const month = (date.getMonth() + 1).toString().padStart(2, '0')
    const day = date.getDate().toString().padStart(2, '0')
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')
    return `${month}-${day} ${hours}:${minutes}`
  }

  return (
    <View className='file-page'>
      {/* 存储统计 */}
      {stats && (
        <View className='stats-bar'>
          <Text className='stats-text'>已用 {formatFileSize(stats.used)} / {formatFileSize(stats.total)}</Text>
          <Text className='stats-text'>共 {stats.file_count} 个文件</Text>
        </View>
      )}

      {/* 文件列表 */}
      <ScrollView scrollY className='file-list'>
        {loading ? (
          <View className='loading-state'>
            <Text className='loading-text'>加载中...</Text>
          </View>
        ) : files.length === 0 ? (
          <View className='empty-state'>
            <Text className='empty-icon'>📂</Text>
            <Text className='empty-text'>暂无文件</Text>
            <Text className='empty-hint'>点击下方按钮上传文件</Text>
          </View>
        ) : (
          files.map(file => (
            <View key={file.id} className='file-item'>
              <View className='file-info' onClick={() => handleDownload(file)}>
                <Text className='file-icon'>{getFileIcon(file.mime_type)}</Text>
                <View className='file-detail'>
                  <Text className='file-name'>{file.name}</Text>
                  <Text className='file-meta'>{formatFileSize(file.size)} · {formatTime(file.uploaded_at)}</Text>
                </View>
              </View>
              <View className='file-actions'>
                <Text className='action-btn' onClick={() => handleDelete(file.id)}>删除</Text>
              </View>
            </View>
          ))
        )}
      </ScrollView>

      {/* 上传按钮 */}
      <View className='upload-bar'>
        <button className='upload-btn' onClick={handleUpload} disabled={uploading}>
          {uploading ? '上传中...' : '上传文件'}
        </button>
      </View>
    </View>
  )
}
