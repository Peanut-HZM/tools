# 密码重置弹框展示密码设计文档

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重置密码后自动弹出密码展示框，自动复制密码到剪贴板并提供手动复制按钮。

**Architecture:** 使用 `useEffect` 在成功状态时自动复制密码，同时提供手动复制按钮供用户备用。

**Tech Stack:** React 18 + TypeScript, `navigator.clipboard.writeText`, Toast 通知

---

## 1. 需求说明

### 1.1 功能需求

1. **自动复制密码**：密码重置成功后，自动将生成的密码复制到剪贴板
2. **密码展示**：在弹框中清晰展示生成的密码
3. **手动复制按钮**：提供手动复制按钮，防止自动复制失败或用户需要再次复制
4. **复制反馈**：复制成功后显示 Toast 提示，按钮显示"已复制"状态

### 1.2 用户体验流程

```
1. 管理员点击"重置密码"
2. 选择"随机生成密码"模式
3. 点击"确认重置"
4. → 密码重置成功
5. → 弹框展示生成的密码
6. → 自动复制密码到剪贴板（Toast 提示"密码已复制"）
7. → 用户可点击"复制密码"按钮手动复制（可选）
8. → 点击"完成"关闭弹框
```

---

## 2. 设计方案

### 2.1 组件修改

**文件：** `frontend/src/components/Admin/PasswordResetModal.tsx`

### 2.2 修改内容

#### 2.2.1 添加 useToast hook

```tsx
import { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast'; // 新增

export default function PasswordResetModal({ isOpen, onClose, onConfirm, username }: PasswordResetModalProps) {
  const { success: toastSuccess, error: toastError } = useToast(); // 新增
  // ...
}
```

#### 2.2.2 添加 handleCopyPassword 函数

```tsx
const handleCopyPassword = async () => {
  try {
    await navigator.clipboard.writeText(generatedPassword);
    toastSuccess('密码已复制');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  } catch (err) {
    toastError('复制失败，请手动复制');
  }
};
```

#### 2.2.3 添加 useEffect 自动复制

```tsx
// 在 success 状态且 mode 为 random 时自动复制
useEffect(() => {
  if (success && mode === 'random' && generatedPassword && isOpen) {
    const copyPassword = async () => {
      try {
        await navigator.clipboard.writeText(generatedPassword);
        toastSuccess('密码已自动复制');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (err) {
        console.error('自动复制失败:', err);
      }
    };
    copyPassword();
  }
}, [success, mode, generatedPassword, isOpen]);
```

#### 2.2.4 添加 copied 状态

```tsx
const [copied, setCopied] = useState(false);
```

#### 2.2.5 更新成功界面 UI

```tsx
// 成功状态 - 显示生成的密码
if (success && mode === 'random' && generatedPassword) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 p-6 rounded-lg w-full max-w-md border border-slate-700 text-center">
        <div className="w-16 h-16 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
          <i className="fa-solid fa-check text-2xl"></i>
        </div>
        <h3 className="text-xl font-bold text-white mb-2">密码重置成功</h3>
        <p className="text-slate-400 mb-6">
          系统已为用户 <span className="text-cyan-400">{username}</span> 生成随机密码
        </p>

        {/* 密码显示框 */}
        <div className="relative bg-slate-900 p-4 rounded mb-6 font-mono text-cyan-400 text-lg break-all border border-slate-700">
          <div className="absolute right-2 top-2 text-slate-500 text-xs">
            <i className="fa-solid fa-key"></i>
          </div>
          <div className="pr-8">{generatedPassword}</div>
        </div>

        {/* 复制按钮 */}
        <button
          onClick={handleCopyPassword}
          disabled={copied}
          className={`w-full mb-3 px-4 py-2 rounded transition-colors flex items-center justify-center gap-2 ${
            copied
              ? 'bg-emerald-600 text-white cursor-default'
              : 'bg-slate-700 hover:bg-slate-600 text-white'
          }`}
        >
          <i className={`fa-${copied ? 'solid fa-check' : 'regular fa-copy'}`}></i>
          {copied ? '已复制' : '复制密码'}
        </button>

        {/* 完成按钮 */}
        <button
          onClick={handleClose}
          className="w-full px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded transition-colors"
        >
          完成
        </button>
      </div>
    </div>
  );
}
```

### 2.3 依赖项

- `useToast` hook：已在 `frontend/src/hooks/useToast.ts` 中定义
- `navigator.clipboard.writeText()`：现代浏览器原生 API

---

## 3. 错误处理

### 3.1 自动复制失败

- 静默失败（不弹出错误提示，因为用户还可以手动复制）
- 记录到 console 用于调试

### 3.2 手动复制失败

- 显示 Toast 错误提示："复制失败，请手动复制"
- 用户可以手动选中文本复制

### 3.3 浏览器兼容性

`navigator.clipboard` API 在以下浏览器可用：
- Chrome 66+
- Firefox 63+
- Safari 13.1+
- Edge 79+

对于不支持的浏览器，自动复制会静默失败，用户仍可使用手动复制功能。

---

## 4. 测试要点

### 4.1 功能测试

- [ ] 重置密码后，弹框正确显示生成的密码
- [ ] 弹框打开时自动复制密码
- [ ] 复制成功后显示 Toast 提示
- [ ] 复制按钮状态正确变化（"复制密码" → "已复制"）
- [ ] 2 秒后按钮恢复初始状态
- [ ] 手动复制按钮正常工作
- [ ] "完成"按钮正常关闭弹框

### 4.2 浏览器验证

- [ ] Chrome 浏览器测试
- [ ] 浏览器 Console 无错误
- [ ] Toast 通知显示正常

---

## 5. 验收标准

1. ✅ 密码重置成功后，弹框展示生成的密码
2. ✅ 弹框打开时自动复制密码到剪贴板
3. ✅ 复制成功后显示 Toast 提示"密码已自动复制"
4. ✅ 提供手动复制按钮，点击可再次复制
5. ✅ 复制按钮有状态变化（"复制密码" → "已复制"）
6. ✅ 浏览器 Console 无错误

---

## 6. 视觉设计

### 6.1 密码显示框

```
┌─────────────────────────────────────────┐
│ 🔑 1TE_u8*gp+zi                    │
└─────────────────────────────────────────┘
```

- 深色背景 (`bg-slate-900`)
- 青色密码文本 (`text-cyan-400`)
- 等宽字体 (`font-mono`)
- 钥匙图标 (`fa-key`)

### 6.2 复制按钮状态

**默认状态：**
```
┌─────────────────────────────┐
│ 📋 复制密码                  │
└─────────────────────────────┘
```
- 灰色背景 (`bg-slate-700`)
- 悬停时变浅 (`hover:bg-slate-600`)

**已复制状态：**
```
┌─────────────────────────────┐
│ ✓ 已复制                    │
└─────────────────────────────┘
```
- 绿色背景 (`bg-emerald-600`)
- 持续 2 秒后恢复

---

## 7. 后续优化建议

1. **密码强度指示器**：在密码显示框中显示密码强度
2. **密码可见性切换**：点击密码可显示/隐藏（对于直接输入模式）
3. **发送密码给用户**：添加"发送邮件通知用户"功能
