# 小程序认证守卫与页面跳转优化实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为小程序添加统一的认证守卫 Hook，修复 401 错误后的用户体验，确保受保护页面在未登录时引导到登录页。

**Architecture:** 创建 `useAuthGuard` 自定义 Hook 作为认证守卫核心逻辑，在受保护页面组件顶层调用。401 错误处理器统一引导到登录页并携带 redirect 参数，登录成功后读取参数返回原页面。

**Tech Stack:** Taro 4.1.11, React 18, TypeScript, Zustand 5

---

### Task 1: 创建 useAuthGuard Hook

**Files:**
- Create: `src/hooks/useAuthGuard.ts`
- Create: `src/hooks/index.ts`

**Step 1: 创建 hooks 目录和 useAuthGuard.ts**

```typescript
// src/hooks/useAuthGuard.ts
import { useEffect, useRef } from 'react'
import Taro from '@tarojs/taro'
import { useAuthStore } from '../stores/auth'

/**
 * 认证守卫 Hook
 * 在需要登录才能访问的页面组件顶层调用
 *
 * 行为：
 * 1. 检查 Zustand 状态和 Storage 中的 token 是否一致
 * 2. 如果未登录，重定向到登录页并携带当前页面路径作为 redirect 参数
 * 3. 如果 Storage 被清空但 Zustand 状态还在，同步调用 logout()
 */
export function useAuthGuard() {
  const { isAuthenticated, logout } = useAuthStore()
  const hasRedirected = useRef(false)

  useEffect(() => {
    const token = Taro.getStorageSync('auth_token')

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
      const redirect = currentPage?.route ? `/${currentPage.route}` : '/'

      Taro.redirectTo({
        url: `/pages/login/index?redirect=${encodeURIComponent(redirect)}`,
        fail: () => {
          // 如果 redirectTo 失败（比如是 TabBar 页面），尝试 reLaunch
          Taro.reLaunch({ url: `/pages/login/index?redirect=${encodeURIComponent(redirect)}` })
        }
      })
    }
  }, [isAuthenticated, logout])
}
```

**Step 2: 创建 hooks 统一导出文件**

```typescript
// src/hooks/index.ts
export { useAuthGuard } from './useAuthGuard'
```

**Step 3: 验证编译**

Run: `./node_modules/.bin/taro build --type weapp`
Expected: Compiled successfully, no errors

---

### Task 2: 修改 request.ts 使 401 后自动引导到登录页

**Files:**
- Modify: `src/services/request.ts:45-51`（主 request 函数 401 处理）
- Modify: `src/services/request.ts:82-86`（uploadFile 401 处理）
- Modify: `src/services/request.ts:112-116`（downloadFile 401 处理）

**当前代码（request 函数 401 处理）**：
```typescript
    if (res.statusCode === 401) {
      Taro.removeStorageSync('auth_token');
      Taro.removeStorageSync('user_info');
      throw new Error('认证已过期，请重新登录');
    }
```

**改为**：401 时清除 Storage 并弹出 Toast，1.5 秒后自动跳转到登录页（带 redirect 参数）

**注意**：由于 `request.ts` 是服务层，不应该直接处理页面跳转。改为抛出包含状态码的错误对象，由调用方或全局错误处理来引导。

但考虑到 Taro 小程序的实际场景，在 request 中处理 401 跳转是合理的做法（业界常见模式）。

```typescript
// request.ts 修改后的 401 处理（三个函数统一修改）
    if (res.statusCode === 401) {
      Taro.removeStorageSync('auth_token')
      Taro.removeStorageSync('user_info')
      Taro.showToast({ title: '认证已过期，请重新登录', icon: 'none', duration: 1500 })
      setTimeout(() => {
        const pages = Taro.getCurrentPages()
        const currentPage = pages[pages.length - 1]
        const redirect = currentPage?.route ? `/${currentPage.route}` : '/'
        Taro.redirectTo({
          url: `/pages/login/index?redirect=${encodeURIComponent(redirect)}`,
          fail: () => {
            Taro.reLaunch({ url: `/pages/login/index?redirect=${encodeURIComponent(redirect)}` })
          }
        })
      }, 1500)
      throw new Error('认证已过期，请重新登录')
    }
```

**Step: 修改 request 函数**

将第 45-51 行改为上述代码。

**Step: 修改 uploadFile 函数**

将第 82-86 行改为上述代码（同样的逻辑）。

**Step: 修改 downloadFile 函数**

将第 112-116 行改为上述代码（同样的逻辑）。

**Step: 验证编译**

Run: `./node_modules/.bin/taro build --type weapp`
Expected: Compiled successfully

---

### Task 3: 修改登录页支持 redirect 参数

**Files:**
- Modify: `src/pages/login/index.tsx`

**Step 1: 添加 redirect 状态**

在现有的 `const login = useAuthStore(state => state.login)` 之后添加：

```typescript
  // 登录后返回来源页面
  const [redirect, setRedirect] = useState('')

  // 读取 URL 中的 redirect 参数
  useDidShow(() => {
    // 检查是否已登录
    const token = Taro.getStorageSync('auth_token')
    if (token) {
      Taro.switchTab({ url: '/pages/index/index' })
      return
    }

    // 读取 redirect 参数
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
```

**Step 2: 修改登录成功后的跳转逻辑**

替换原来的 `handleSubmit` 中的 `setTimeout` 跳转部分（约第 56-64 行）：

```typescript
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
```

**Step 3: 验证编译**

Run: `./node_modules/.bin/taro build --type weapp`
Expected: Compiled successfully

---

### Task 4: 修改修改密码页面，正确调用 logout()

**Files:**
- Modify: `src/pages/change-password/index.tsx:70-76`

**当前代码**：
```typescript
      setTimeout(() => {
        Taro.removeStorageSync('auth_token')
        Taro.removeStorageSync('user_info')
        Taro.redirectTo({ url: '/pages/login/index' })
      }, 2000)
```

**改为**：调用 `logout()` 同步清理 Zustand 状态，并支持 redirect

```typescript
      setTimeout(() => {
        logout()
        Taro.redirectTo({ url: '/pages/login/index?redirect=/pages/change-password/index' })
      }, 2000)
```

**具体修改**：

1. 在组件开头添加：`const { logout } = useAuthStore()`
2. 导入 `useAuthStore`：在 import 中添加 `{ useAuthStore } from '../../stores/auth'`
3. 修改 setTimeout 中的逻辑

**Step: 添加导入和 logout**

在文件顶部 import 中添加：
```typescript
import { useAuthStore } from '../../stores/auth'
```

在 `const [success, setSuccess] = useState(false)` 之后添加：
```typescript
  const { logout } = useAuthStore()
```

**Step: 修改 setTimeout 逻辑**

```typescript
      setTimeout(() => {
        logout()
        Taro.redirectTo({ url: '/pages/login/index?redirect=/pages/change-password/index' })
      }, 2000)
```

**Step: 验证编译**

Run: `./node_modules/.bin/taro build --type weapp`
Expected: Compiled successfully

---

### Task 5: 为消息页面添加认证守卫

**Files:**
- Modify: `src/pages/cross-share/message/index.tsx`

**Step 1: 添加 useAuthGuard**

在文件顶部 import 中添加：
```typescript
import { useAuthGuard } from '../../../hooks'
```

在组件函数体内第一行添加：
```typescript
  useAuthGuard()
```

**Step 2: 移除重复的登录检查**

消息页面目前没有显式的登录检查，但 API 调用都会带 token。加了 `useAuthGuard` 后，未登录用户会被直接引导到登录页。

**Step: 验证编译**

Run: `./node_modules/.bin/taro build --type weapp`
Expected: Compiled successfully

---

### Task 6: 为文件页面添加认证守卫

**Files:**
- Modify: `src/pages/cross-share/file/index.tsx`

**Step 1: 添加 useAuthGuard**

在文件顶部 import 中添加：
```typescript
import { useAuthGuard } from '../../../hooks'
```

在组件函数体内第一行（`const [files, setFiles] = ...` 之前）添加：
```typescript
  useAuthGuard()
```

**Step: 验证编译**

Run: `./node_modules/.bin/taro build --type weapp`
Expected: Compiled successfully

---

### Task 7: 优化"我的"页面未登录状态的显示

**Files:**
- Modify: `src/pages/profile/index.tsx:43-45`

**当前代码**：
```typescript
  if (!isAuthenticated) {
    return null
  }
```

**问题**：未登录时渲染 `null`，用户看到空白页面，不知道发生了什么。

**改为**：显示引导登录的提示

```typescript
  if (!isAuthenticated) {
    return (
      <View className='profile-page'>
        <View className='profile-empty'>
          <Text className='empty-icon'>👤</Text>
          <Text className='empty-text'>请先登录</Text>
          <button
            className='login-btn'
            onClick={() => Taro.redirectTo({ url: '/pages/login/index' })}
          >
            去登录
          </button>
        </View>
      </View>
    )
  }
```

同时在 `src/pages/profile/index.scss` 中添加对应样式：

```scss
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
    font-size: 16px;
    color: #94A3B8;
    margin-bottom: 24px;
  }

  .login-btn {
    background: #3B82F6;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 10px 32px;
    font-size: 15px;
  }
}
```

**Step: 验证编译**

Run: `./node_modules/.bin/taro build --type weapp`
Expected: Compiled successfully

---

### Task 8: 完整构建验证与手动测试

**Step 1: 完整构建**

Run: `./node_modules/.bin/taro build --type weapp`
Expected: Compiled successfully in ~7s, no warnings

**Step 2: 手动测试清单**

在微信开发者工具中依次测试：

1. **未登录状态访问各页面**
   - 清除 Storage（开发者工具 → Storage → 清空）
   - 刷新小程序
   - 点击"消息"Tab → 应自动跳转到登录页
   - 点击"文件"Tab → 应自动跳转到登录页
   - 点击"我的"Tab → 应显示"请先登录"提示和"去登录"按钮
   - 点击工具首页 → 正常显示工具列表（不需要登录）
   - 点击 JSON 格式化 → 正常打开（不需要登录）

2. **登录流程**
   - 从"我的"页面点击"去登录"
   - 输入用户名密码登录
   - 登录成功后应跳转回"我的"页面（因为 redirect 参数）
   - 验证 Zustand 状态正确（页面显示用户信息）

3. **受保护页面 redirect 测试**
   - 退出登录
   - 在地址栏或代码中进入消息页面
   - 应跳转到登录页，URL 中包含 `?redirect=/pages/cross-share/message/index`
   - 登录成功后应自动返回消息页面

4. **401 过期体验**
   - 登录状态下访问消息页面
   - 在 Storage 中手动删除 `auth_token`
   - 点击发送消息 → 应弹出 Toast "认证已过期，请重新登录"，1.5秒后跳转登录页

5. **修改密码流程**
   - 登录 → 我的 → 修改密码
   - 输入新旧密码提交
   - 提示"密码修改成功" → 2秒后跳转登录页（带 redirect）
   - 重新登录后应返回修改密码页面
