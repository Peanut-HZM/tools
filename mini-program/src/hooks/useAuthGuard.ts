import { useEffect, useRef } from 'react'
import Taro from '@tarojs/taro'
import { useAuthStore } from '../stores/auth'

// TabBar 页面列表（与 app.config.ts 保持一致）
const TAB_BAR_PAGES = [
  'pages/index/index',
  'pages/cross-share/message/index',
  'pages/cross-share/file/index',
  'pages/profile/index',
]

/**
 * 认证守卫 Hook
 * 在需要登录才能访问的页面组件顶层调用
 *
 * 行为：
 * 1. 检查 Zustand 状态和 Storage 中的 token 是否一致
 * 2. 如果未登录，重定向到登录页并携带当前页面路径作为 redirect 参数
 * 3. TabBar 页面通过 Storage 传递 redirect（switchTab 不支持 query 参数）
 * 4. 如果 Storage 被清空但 Zustand 状态还在，同步调用 logout()
 */
export function useAuthGuard() {
  const { isAuthenticated, logout } = useAuthStore()
  const hasRedirected = useRef(false)

  useEffect(() => {
    let token: string | null = null;
    try {
      token = Taro.getStorageSync('auth_token');
    } catch {
      // Storage 未初始化时忽略
    }

    // 情况 1：Storage 有 token 但 Zustand 未认证（不太可能，但处理一下）
    if (token && !isAuthenticated) {
      // Zustand 状态会在下次渲染时同步，这里不做处理
      return
    }

    // 情况 2：Zustand 已认证但 Storage 中 token 被清空（外部操作导致）
    if (!token && isAuthenticated) {
      logout()
      return
    }

    // 情况 3：未登录且没有 token → 跳转到登录页
    if (!isAuthenticated && !token && !hasRedirected.current) {
      hasRedirected.current = true
      const pages = Taro.getCurrentPages()
      const currentPage = pages[pages.length - 1]
      const route = currentPage?.route || ''
      const redirect = route ? `/${route}` : '/'

      // 检测是否为 TabBar 页面
      const isTabBarPage = TAB_BAR_PAGES.some(page => route.includes(page))

      if (isTabBarPage) {
        // TabBar 页面：通过 Storage 传递 redirect，然后用 reLaunch
        Taro.setStorageSync('login_redirect', redirect)
        Taro.reLaunch({ url: '/pages/login/index' })
      } else {
        // 非 TabBar 页面：使用 redirectTo + query 参数
        Taro.redirectTo({ url: `/pages/login/index?redirect=${encodeURIComponent(redirect)}` })
      }
    }
  }, [isAuthenticated, logout])
}
