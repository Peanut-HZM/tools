# 移除我的页面登录空状态 - 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 移除"我的"页面中"请先登录"的中间空状态页面，未登录时自动跳转到登录页，同时优化 useAuthGuard hook 避免 TabBar 页面跳转时页面栈被清空。

**Architecture:** 在 profile/index.tsx 中引入 useAuthGuard hook，删除未登录时的空状态渲染分支及对应 SCSS 样式。优化 useAuthGuard 中对 TabBar 页面的跳转逻辑，使用 switchTab 替代 reLaunch。

**Tech Stack:** Taro 4.1.11, React 18, TypeScript, Zustand 5

---

### Task 1: 优化 useAuthGuard hook — TabBar 页面使用 switchTab

**Files:**
- Modify: `src/hooks/useAuthGuard.ts`

**当前代码（第 38-52 行）：**

```typescript
// 情况 3：未登录且没有 token → 跳转到登录页
if (!isAuthenticated && !token && !hasRedirected.current) {
  hasRedirected.current = true
  const pages = Taro.getCurrentPages()
  const currentPage = pages[pages.length - 1]
  const redirect = currentPage?.route ? `/${currentPage.route}` : '/'

  Taro.redirectTo({
    url: `/pages/login/index?redirect=${encodeURIComponent(redirect)}`,
    fail: () => {
      // 如果 redirectTo 失败（比如是 TabBar 页面），尝试 reLaunch
      Taro.reLaunch({ url: `/pages/login/index?redirect=${encodeURIComponent(redirect)}` })
    }
  })
}
```

**问题：** TabBar 页面不支持 `redirectTo`，会 fallback 到 `reLaunch`，导致整个页面栈被清空，用户登录后无法返回之前的页面。

**修改后（完整文件内容）：**

```typescript
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
 * 3. TabBar 页面使用 switchTab 跳转（保留页面栈），非 TabBar 页面使用 redirectTo
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

      const loginUrl = `/pages/login/index?redirect=${encodeURIComponent(redirect)}`

      if (isTabBarPage) {
        // TabBar 页面：使用 switchTab，保留页面栈
        Taro.switchTab({ url: loginUrl })
      } else {
        // 非 TabBar 页面：使用 redirectTo
        Taro.redirectTo({ url: loginUrl })
      }
    }
  }, [isAuthenticated, logout])
}
```

**关键改动：**
1. 新增 `TAB_BAR_PAGES` 常量，与 app.config.ts 中的 TabBar 列表保持一致
2. 用 `route.includes(page)` 检测当前页面是否为 TabBar 页面
3. TabBar 页面使用 `switchTab`，非 TabBar 页面使用 `redirectTo`
4. 删除 `reLaunch` fallback，不再需要

**验证：**
```bash
pnpm --dir /Users/huazhongmin/IdeaProjects/tools/tools-mini-program run build:weapp
```
预期：`✔ Webpack Compiled successfully`

### Task 2: 修改 profile/index.tsx — 使用 useAuthGuard 替代空状态

**Files:**
- Modify: `src/pages/profile/index.tsx`

**完整修改后文件内容：**

```tsx
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
```

**关键改动：**
1. 新增 `import { useAuthGuard } from '../../hooks'`
2. 组件开头调用 `useAuthGuard()`
3. 原来的空状态 JSX（第 43-58 行）替换为 `return null`（安全兜底）

**验证：**
```bash
pnpm --dir /Users/huazhongmin/IdeaProjects/tools/tools-mini-program run build:weapp
```
预期：`✔ Webpack Compiled successfully`

### Task 3: 删除 SCSS 中的空状态样式

**Files:**
- Modify: `src/pages/profile/index.scss`

删除 `.profile-empty` 样式块（第 105-139 行，共 35 行）：

```scss
/* 删除以下整个块 */
.profile-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120px 40px;

  .empty-icon {
    font-size: 64px;
    margin-bottom: 16px;
  }

  .empty-text {
    font-size: 18px;
    color: #E2E8F0;
    margin-bottom: 8px;
    font-weight: 500;
  }

  .empty-hint {
    font-size: 14px;
    color: #94A3B8;
    margin-bottom: 32px;
  }

  .login-btn {
    background: #3B82F6;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 12px 40px;
    font-size: 15px;
    font-weight: 500;
  }
}
```

**验证：**
```bash
pnpm --dir /Users/huazhongmin/IdeaProjects/tools/tools-mini-program run build:weapp
```
预期：`✔ Webpack Compiled successfully`

### Task 4: 最终构建验证

```bash
pnpm --dir /Users/huazhongmin/IdeaProjects/tools/tools-mini-program run build:weapp
```
预期：`✔ Webpack Compiled successfully`

---

**最终效果：**
- 未登录 → 打开"我的"Tab → switchTab 跳转登录页（页面栈保留）
- 登录成功 → switchTab 返回"我的"页面
- 已登录 → 正常显示个人资料
- 消息页、文件页等子页面 → redirectTo 跳转登录页（行为不变）
