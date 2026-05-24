import { useState, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { View, Text } from '@tarojs/components'
import { useAuthStore } from '../../stores/auth'
import { useAuthGuard } from '../../hooks'
import { authApi } from '../../services/auth'
import './index.scss'

export default function Profile() {
  useAuthGuard()  // 未登录时自动跳转到登录页

  const { user, isAuthenticated, logout } = useAuthStore()
  const [userInfo, setUserInfo] = useState<any>(null)

  // 加载用户信息（store 已持久化，无需重复检查）
  useEffect(() => {
    if (isAuthenticated) {
      loadUserInfo()
    }
  }, [])

  const loadUserInfo = async () => {
    try {
      const info = await authApi.getUserInfo()
      setUserInfo(info)
    } catch (err) {
      console.error('Failed to load user info:', err)
    }
  }

  const handleLogout = () => {
    Taro.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          Taro.removeStorageSync('auth_token')
          Taro.removeStorageSync('user_info')
          logout()
          Taro.switchTab({ url: '/pages/index/index' })
        }
      }
    })
  }

  if (!isAuthenticated) {
    return null  // useAuthGuard 处理跳转，这里仅作为安全兜底
  }

  return (
    <View className='profile-page'>
      {/* 用户信息头部 */}
      <View className='profile-header'>
        <View className='profile-avatar'>
          <Text className='avatar-text'>
            {(userInfo?.username || user?.username || 'U').charAt(0).toUpperCase()}
          </Text>
        </View>
        <Text className='profile-name'>{userInfo?.username || user?.username || '用户'}</Text>
        <Text className='profile-email'>{userInfo?.email || ''}</Text>
        {userInfo?.role && (
          <View className='role-badge'>
            <Text className='role-text'>{userInfo.role === 'admin' ? '管理员' : '普通用户'}</Text>
          </View>
        )}
      </View>

      {/* 功能列表 */}
      <View className='profile-menu'>
        <View className='menu-group'>
          <View className='menu-item' onClick={() => Taro.navigateTo({ url: '/pages/change-password/index' })}>
            <Text className='menu-label'>修改密码</Text>
            <Text className='menu-arrow'>›</Text>
          </View>
        </View>

        <View className='menu-group'>
          <View className='menu-item' onClick={() => Taro.navigateTo({ url: '/pages/help/index' })}>
            <Text className='menu-label'>帮助与关于</Text>
            <Text className='menu-arrow'>›</Text>
          </View>
        </View>

        <View className='menu-group'>
          <View className='menu-item menu-item-danger' onClick={handleLogout}>
            <Text className='menu-label'>退出登录</Text>
            <Text className='menu-arrow'>›</Text>
          </View>
        </View>
      </View>

      {/* 版本信息 */}
      <View className='profile-version'>
        <Text>工具箱小程序 v1.0.0</Text>
      </View>
    </View>
  )
}
