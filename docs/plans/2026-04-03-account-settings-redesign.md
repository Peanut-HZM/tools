# 账户设置页面全面重构设计文档

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `/account-settings` 页面从简单信息展示页重构为功能完善、视觉精美的专业账户管理中心，采用侧边栏导航布局，支持多模块切换。

**Architecture:** 采用侧边栏 + 内容区布局，左侧为设置分类导航（基本信息、安全设置、偏好设置），右侧为对应内容区域。组件化设计，每个模块独立管理状态。

**Tech Stack:** React 18 + TypeScript, Tailwind CSS, Zustand (authStore), React Router, lucide-react 图标库

---

## 1. 布局设计

### 1.1 整体结构

```
┌─────────────────────────────────────────────────────────────┐
│                      Header (全局导航)                        │
├─────────────────────────────────────────────────────────────┤
│  Account Settings Header                                     │
│  "账户设置" + 面包屑导航                                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┬─────────────────────────────────────────┐  │
│  │             │                                         │  │
│  │  侧边栏导航  │           主内容区域                     │  │
│  │  (280px)    │          (自适应宽度)                    │  │
│  │             │                                         │  │
│  │ • 基本信息   │     • 用户信息卡片                       │  │
│  │ • 安全设置   │     • 安全设置卡片                       │  │
│  │ • 偏好设置   │     • 偏好设置卡片                       │  │
│  │             │                                         │  │
│  └─────────────┴─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 响应式断点

- **Desktop (>1024px):** 完整侧边栏布局
- **Tablet (768px-1024px):** 顶部标签页导航
- **Mobile (<768px):** 堆叠布局，单列展示

## 2. 组件结构

### 2.1 新建组件

```
frontend/src/components/Account/
├── AccountLayout.tsx          # 主布局容器
├── AccountSidebar.tsx         # 侧边栏导航
├── AccountHeader.tsx          # 页面头部
├── sections/
│   ├── BasicInfoSection.tsx   # 基本信息模块
│   ├── SecuritySettingsSection.tsx  # 安全设置模块
│   └── PreferencesSection.tsx # 偏好设置模块
└── components/
    ├── UserAvatar.tsx         # 用户头像组件
    ├── InfoRow.tsx            # 信息行组件
    ├── PasswordStrengthMeter.tsx  # 密码强度指示器
    └── SettingCard.tsx        # 设置卡片通用组件
```

### 2.2 组件职责

**AccountLayout.tsx**
- 管理当前激活的菜单项状态
- 处理响应式布局切换
- 提供上下文给子组件

**AccountSidebar.tsx**
- 渲染导航菜单项
- 高亮当前激活项
- 处理菜单点击事件

**BasicInfoSection.tsx**
- 展示用户基本信息（ID、用户名、邮箱、角色、注册时间）
- 支持复制用户 ID 到剪贴板
- 显示用户头像（占位符，支持后续扩展）

**SecuritySettingsSection.tsx**
- 修改密码功能（集成现有 ChangePasswordModal）
- 密码强度实时验证
- 显示最后登录时间、登录设备（预留接口）

**PreferencesSection.tsx**
- 语言选择（中文/English）
- 主题切换（深色/浅色/系统）
- 通知设置（邮件通知、系统通知开关）

## 3. 视觉设计

### 3.1 颜色方案

基于现有 Dashboard 设计语言：

```css
/* 背景 */
bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900

/* 卡片 */
bg-slate-800/50 backdrop-blur-sm
border border-slate-700/50

/* 侧边栏 */
bg-slate-800/30
border-r border-slate-700/50

/* 菜单项悬停 */
hover:bg-slate-700/50

/* 激活状态 */
bg-cyan-500/10 border-cyan-500/50 text-cyan-400

/* 强调色 */
cyan-500 (主按钮、激活状态)
orange-500 (危险操作)
emerald-500 (成功状态)
```

### 3.2 卡片样式

```tsx
// 统一卡片样式
<div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6 hover:border-slate-600/50 transition-all duration-200">
  {/* 标题 */}
  <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
    <Icon className="w-5 h-5 text-cyan-400" />
    卡片标题
  </h3>
  
  {/* 内容 */}
  <div className="space-y-4">
    {/* 信息行 */}
    <div className="flex items-center justify-between py-3 border-b border-slate-700/50 last:border-0">
      <span className="text-slate-400">标签</span>
      <span className="text-white font-medium">值</span>
    </div>
  </div>
</div>
```

### 3.3 交互动效

- 卡片悬停：border 亮度提升，轻微阴影
- 菜单项悬停：背景渐变，图标颜色变化
- 按钮点击：缩放 0.98，颜色加深
- 加载状态：骨架屏动画

## 4. 数据流设计

### 4.1 状态管理

```typescript
interface AccountState {
  activeSection: 'basic' | 'security' | 'preferences';
  user: UserResponse | null;
  loading: boolean;
  preferences: UserPreferences;
}

interface UserPreferences {
  language: 'zh' | 'en';
  theme: 'dark' | 'light' | 'system';
  emailNotifications: boolean;
  systemNotifications: boolean;
}
```

### 4.2 用户操作流程

```
用户点击修改密码
  ↓
打开 ChangePasswordModal
  ↓
填写表单并提交
  ↓
调用 authApi.changePassword()
  ↓
后端验证并更新
  ↓
显示 Toast 通知
  ↓
关闭模态框
```

### 4.3 API 接口

```typescript
// 已有接口复用
import { getCurrentUser, changePassword } from '@/api/authApi';

// 新增接口（可选，后续实现）
// PUT /api/users/preferences - 更新用户偏好
// POST /api/users/send-verification-email - 发送验证邮件
```

## 5. 响应式设计

### 5.1 Desktop (>1024px)

- 侧边栏固定宽度 280px
- 主内容区自适应
- 卡片并排展示（如适用）

### 5.2 Tablet (768px-1024px)

- 侧边栏转换为顶部标签页
- 卡片单列展示
- 导航可左右滑动

### 5.3 Mobile (<768px)

- 堆叠布局
- 卡片圆角减小
- 字体大小调整
- 触摸友好型按钮

## 6. 错误处理

### 6.1 数据加载失败

```tsx
const [error, setError] = useState<string | null>(null);

// 显示错误状态
{error && (
  <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-6">
    {error}
    <button onClick={loadUser} className="ml-2 underline">重试</button>
  </div>
)}
```

### 6.2 表单验证

- 前端实时验证（密码强度、邮箱格式）
- 后端验证失败显示具体错误信息
- 表单提交时显示加载状态

## 7. 可访问性

- 使用语义化标签（section, header, nav）
- 所有交互元素支持键盘导航
- 图标按钮添加 aria-label
- 颜色对比度符合 WCAG AA 标准

## 8. 测试要点

### 8.1 功能测试

- [ ] 侧边栏导航切换正常
- [ ] 用户信息加载成功
- [ ] 复制用户 ID 功能正常
- [ ] 修改密码流程完整
- [ ] 密码验证规则生效
- [ ] 响应式布局正确

### 8.2 边界测试

- [ ] 未登录用户重定向
- [ ] 网络错误处理
- [ ] 空状态显示
- [ ] 长文本溢出处理

## 9. 性能优化

- 使用 React.memo 避免不必要的重渲染
- 懒加载非关键组件
- 图片使用 lazy loading
- API 请求添加防抖（如搜索）

## 10. 验收标准

1. ✅ 页面加载无报错
2. ✅ 侧边栏导航功能正常
3. ✅ 三个模块内容完整展示
4. ✅ 修改密码功能可用
5. ✅ 响应式布局适配三种屏幕尺寸
6. ✅ 浏览器 Console 无错误
7. ✅ 视觉设计与设计稿一致
8. ✅ 交互动效流畅
