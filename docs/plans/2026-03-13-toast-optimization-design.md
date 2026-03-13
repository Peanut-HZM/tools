# Toast 弹窗优化设计文档

**创建日期**: 2026-03-13
**作者**: AI Assistant
**状态**: 已批准

---

## 1. 背景与目标

### 1.1 问题描述

当前 Toast 弹窗组件存在以下问题：
- 文本内容没有最大宽度限制，长文本显示不美观
- 每个字符占一行，视觉效果差
- 堆叠效果不理想
- 样式较为简陋，缺乏现代感

### 1.2 优化目标

- 使用现代化 Toast 库 `sonner` 替换现有实现
- 保持现有 API 接口不变，降低迁移成本
- 支持暗黑模式，与项目整体风格一致
- 改善文本显示效果，自动换行，美观大方

---

## 2. 技术方案

### 2.1 选型

| 方案 | 库名 | 体积 | 特点 |
|------|------|------|------|
| ✅ 选用 | sonner | ~6KB | 轻量、现代、动画流畅 |
| 备选 | react-hot-toast | ~7.5KB | API 简洁、动画优雅 |
| 备选 | notistack | ~15KB | Material 风格、配置丰富 |

### 2.2 架构设计

```
frontend/src/
├── contexts/
│   └── ToastContext.tsx   # 修改：使用 sonner 实现
├── App.tsx                # 添加 Toaster 组件
├── styles/
│   └── toast.css          # 新增：自定义样式
└── components/
    └── MarkdownEditor/Toast/
        └── Toast.tsx      # 废弃/删除
```

### 2.3 配置参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 位置 | bottom-right | 右下角 |
| 主题 | dark | 暗黑模式 |
| 持续时间 | 3s/5s | success/info 3 秒，error/warning 5 秒 |
| 最大宽度 | 356px | sonner 默认值 |
| 堆叠数量 | 3 | 最多显示 3 个 |

### 2.4 API 设计

保持现有 API 不变：

```typescript
const { success, error, warning, info } = useToast()

success('操作成功')
error('操作失败：详细信息')
warning('请注意此操作')
info('系统通知')
```

---

## 3. 样式设计

### 3.1 Dark 主题覆盖

```css
:root {
  --sonner-toaster-bg: #1e293b;
  --sonner-toaster-text: #f1f5f9;
  --sonner-toaster-border: #334155;
}

.sonner-toaster-dark .toast {
  background-color: #1e293b;
  color: #f1f5f9;
  border: 1px solid #334155;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
}

/* 类型颜色 */
.toast-success { border-left-color: #22c55e; }
.toast-error { border-left-color: #ef4444; }
.toast-warning { border-left-color: #f59e0b; }
.toast-info { border-left-color: #06b6d4; }
```

### 3.2 文本样式

- 字体大小：14px
- 行高：1.5
- 最大宽度：356px
- 自动换行：word-break: break-word

---

## 4. 实施步骤

### 4.1 安装依赖

```bash
cd frontend
npm install sonner
```

### 4.2 修改 ToastContext

- 导入 `toast` from 'sonner'
- 替换 `addToast` 实现使用 `toast()` API
- 添加主题配置

### 4.3 修改 App.tsx

- 导入 `Toaster` from 'sonner'
- 在根组件中添加 `<Toaster />`
- 配置暗黑模式样式

### 4.4 添加样式文件

- 创建 `src/styles/toast.css`
- 定义暗黑主题覆盖样式

### 4.5 清理旧代码

- 删除或标记 `Toast.tsx` 为废弃

---

## 5. 测试验证

### 5.1 功能测试

- [ ] success 类型 Toast 显示正常
- [ ] error 类型 Toast 显示正常
- [ ] warning 类型 Toast 显示正常
- [ ] info 类型 Toast 显示正常
- [ ] 长文本自动换行
- [ ] 多 Toast 堆叠显示正常
- [ ] 自动消失功能正常
- [ ] 手动关闭功能正常

### 5.2 视觉测试

- [ ] 暗黑模式样式正确
- [ ] 动画流畅
- [ ] 与项目整体风格一致

---

## 6. 参考链接

- [sonner GitHub](https://github.com/emilkowalski/sonner)
- [sonner 文档](https://sonner.emilkowal.ski/)
