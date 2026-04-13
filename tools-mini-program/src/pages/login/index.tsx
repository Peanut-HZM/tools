import { useState } from 'react'
import Taro, { useDidShow } from '@tarojs/taro'
import { View, Text, Input, Button } from '@tarojs/components'
import { authApi } from '../../services/auth'
import { useAuthStore } from '../../stores/auth'
import './index.scss'

// Unicode 图标组件
const ToolboxIcon = () => (
  <View className='logo-icon'>
    <Text className='logo-char'>⚙</Text>
  </View>
)

const UserIcon = () => (
  <Text className='input-icon'>👤</Text>
)

const LockIcon = () => (
  <Text className='input-icon'>🔒</Text>
)

const MailIcon = () => (
  <Text className='input-icon'>✉</Text>
)

const AlertIcon = () => (
  <Text className='alert-icon'>⚠</Text>
)

export default function Login() {
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const login = useAuthStore(state => state.login)
  const [redirect, setRedirect] = useState('')

  useDidShow(() => {
    // 检查是否已登录
    try {
      const token = Taro.getStorageSync('auth_token')
      if (token) {
        Taro.switchTab({ url: '/pages/index/index' })
        return
      }
    } catch {
      // Storage 未初始化时忽略
    }

    // 优先读取 storage 中的 redirect（TabBar 页面跳转时存入）
    try {
      const storageRedirect = Taro.getStorageSync('login_redirect')
      if (storageRedirect) {
        setRedirect(decodeURIComponent(storageRedirect))
        Taro.removeStorageSync('login_redirect')
        return
      }
    } catch {
      // ignore
    }

    // 读取 URL 参数中的 redirect（非 TabBar 页面跳转时传入）
    try {
      const pages = Taro.getCurrentPages()
      const currentPage = pages[pages.length - 1]
      const options = currentPage?.options
      if (options?.redirect) {
        setRedirect(decodeURIComponent(options.redirect))
      }
    } catch {
      // ignore
    }
  })

  const handleSubmit = async () => {
    if (!username.trim() || !password.trim()) {
      setError('请输入用户名和密码')
      return
    }

    if (!isLogin && !email.trim()) {
      setError('请输入邮箱地址')
      return
    }

    setLoading(true)
    setError('')

    try {
      const res = isLogin
        ? await authApi.login(username.trim(), password)
        : await authApi.register({
            username: username.trim(),
            password,
            email: email.trim() || undefined
          })

      // 保存 token 和用户信息（后端返回字段：token, user_id, username, email, role）
      Taro.setStorageSync('auth_token', res.token)
      Taro.setStorageSync('user_info', JSON.stringify({
        id: res.user_id,
        username: res.username,
        email: res.email,
        role: res.role
      }))
      login(res.token, {
        id: res.user_id,
        username: res.username,
        role: res.role
      })

      Taro.showToast({ title: isLogin ? '登录成功' : '注册成功', icon: 'success' })

      setTimeout(() => {
        if (redirect) {
          // 如果是 TabBar 页面，用 switchTab
          const tabBarPages = ['/pages/index/index', '/pages/cross-share/message/index', '/pages/cross-share/file/index', '/pages/profile/index']
          if (tabBarPages.includes(redirect)) {
            Taro.switchTab({ url: redirect })
          } else {
            Taro.redirectTo({ url: redirect })
          }
        } else {
          // 没有 redirect 参数，尝试返回或跳转首页
          const pages = Taro.getCurrentPages()
          if (pages.length > 1) {
            Taro.navigateBack()
          } else {
            Taro.switchTab({ url: '/pages/index/index' })
          }
        }
      }, 1000)
    } catch (err: any) {
      const msg = err.message || err.data?.detail || (isLogin ? '登录失败' : '注册失败')
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <View className='login-container'>
      {/* 背景装饰 */}
      <View className='login-bg-decoration'>
        <View className='bg-orb bg-orb-1' />
        <View className='bg-orb bg-orb-2' />
      </View>

      <View className='login-content'>
        {/* Logo 区域 */}
        <View className='login-header'>
          <ToolboxIcon />
          <Text className='login-title'>工具箱</Text>
          <Text className='login-subtitle'>
            {isLogin ? '欢迎回来' : '创建新账号'}
          </Text>
        </View>

        {/* 表单区域 */}
        <View className='login-form'>
          {/* Tab 切换器 */}
          <View className='tab-switcher'>
            <View
              className={`tab-item ${isLogin ? 'active' : ''}`}
              onClick={() => { setIsLogin(true); setError('') }}
            >
              <Text className='tab-text'>登录</Text>
              {isLogin && <View className='tab-indicator' />}
            </View>
            <View
              className={`tab-item ${!isLogin ? 'active' : ''}`}
              onClick={() => { setIsLogin(false); setError('') }}
            >
              <Text className='tab-text'>注册</Text>
              {!isLogin && <View className='tab-indicator' />}
            </View>
          </View>

          {/* 错误提示 */}
          {error && (
            <View className='login-error'>
              <View className='error-icon'><AlertIcon /></View>
              <Text className='error-text'>{error}</Text>
            </View>
          )}

          {/* 用户名输入框 */}
          <View className='form-item'>
            <View className='input-wrapper'>
              <View className='input-prefix'><UserIcon /></View>
              <Input
                className='form-input'
                placeholder='请输入用户名'
                value={username}
                onInput={(e) => setUsername(e.detail.value)}
                disabled={loading}
              />
            </View>
          </View>

          {/* 密码输入框 */}
          <View className='form-item'>
            <View className='input-wrapper'>
              <View className='input-prefix'><LockIcon /></View>
              <Input
                className='form-input'
                type='password'
                placeholder='请输入密码'
                value={password}
                onInput={(e) => setPassword(e.detail.value)}
                disabled={loading}
              />
            </View>
          </View>

          {/* 邮箱输入框（注册时显示） */}
          {!isLogin && (
            <View className='form-item'>
              <View className='input-wrapper'>
                <View className='input-prefix'><MailIcon /></View>
                <Input
                  className='form-input'
                  type='text'
                  placeholder='请输入邮箱（选填）'
                  value={email}
                  onInput={(e) => setEmail(e.detail.value)}
                  disabled={loading}
                />
              </View>
            </View>
          )}

          {/* 提交按钮 */}
          <Button
            className='btn-submit'
            loading={loading}
            disabled={loading}
            onClick={handleSubmit}
          >
            {loading ? (isLogin ? '登录中...' : '注册中...') : (isLogin ? '登 录' : '注 册')}
          </Button>

          {/* 切换链接 */}
          <View className='login-switch'>
            <Text className='switch-text'>
              {isLogin ? '还没有账号？' : '已有账号？'}
            </Text>
            <Text
              className='switch-link'
              onClick={() => {
                setIsLogin(!isLogin)
                setError('')
              }}
            >
              {isLogin ? '立即注册' : '去登录'}
            </Text>
          </View>
        </View>
      </View>
    </View>
  )
}
