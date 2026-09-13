import { useState, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, ScrollView } from '@tarojs/components'
import { fileApi } from '../../../services/crossShare'
import { useAuthGuard } from '../../../hooks'
import { parseDateSafe } from '../../../utils'
import Icon from '../../../components/Icon'
import './index.scss'

/**
 * 跨设备传文件页 — 玻璃光晕换肤（阶段⑧-⑨ Task 7）：
 * - 文件条目套全局 .glass-card（背景/描边/投影/磨砂模糊），上传按钮套 .btn-primary；
 * - 文件类型/空状态 emoji 换为 SVG Icon（烘色传入，Icon 不能嵌在 Text 内，
 *   容器相应改为 View）；上传/下载/删除逻辑不变。
 */

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

  // 获取文件类型图标：原 emoji 映射为 SVG Icon（颜色烘入 stroke，中性 ink 系；
  // Icon 表无回形针/表格/文件夹，按语义就近映射 file/edit/database）
  const getFileIcon = (mimeType: string) => {
    if (mimeType?.startsWith('image/')) return <Icon name='image' size={22} color='#6E7A8F' />
    if (mimeType === 'application/pdf') return <Icon name='file' size={22} color='#6E7A8F' />
    if (mimeType?.includes('word') || mimeType?.includes('document')) return <Icon name='edit' size={22} color='#6E7A8F' />
    if (mimeType?.includes('excel') || mimeType?.includes('spreadsheet')) return <Icon name='database' size={22} color='#6E7A8F' />
    if (mimeType?.includes('text')) return <Icon name='file' size={22} color='#6E7A8F' />
    return <Icon name='file' size={22} color='#6E7A8F' />
  }

  // 格式化文件大小
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  }

  // 格式化时间（兼容 iOS：用 parseDateSafe 替代直接 new Date()）
  const formatTime = (timeStr: string) => {
    const date = parseDateSafe(timeStr);
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
        <View className='file-list-inner'>
        {loading ? (
          <View className='loading-state'>
            <Text className='loading-text'>加载中...</Text>
          </View>
        ) : files.length === 0 ? (
          <View className='empty-state'>
            {/* 📂 换为文件图标（空状态装饰，品牌默认色） */}
            <View className='empty-icon'>
              <Icon name='file' size={48} />
            </View>
            <Text className='empty-text'>暂无文件</Text>
            <Text className='empty-hint'>点击下方按钮上传文件</Text>
          </View>
        ) : (
          files.map(file => (
            <View key={file.id} className='file-item glass-card'>
              <View className='file-info' onClick={() => handleDownload(file)}>
                {/* Icon（Image）不可嵌于 Text，容器改用 View */}
                <View className='file-icon'>{getFileIcon(file.mime_type)}</View>
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
        </View>
      </ScrollView>

      {/* 上传按钮：主按钮走品牌渐变 .btn-primary */}
      <View className='upload-bar'>
        <button className='upload-btn btn-primary' onClick={handleUpload} disabled={uploading}>
          {uploading ? '上传中...' : '上传文件'}
        </button>
      </View>
    </View>
  )
}
