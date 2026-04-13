import { useState } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, Input } from '@tarojs/components'
import { request } from '../../services/request'
import { useAuthStore } from '../../stores/auth'
import './index.scss'

export default function ChangePasswordPage() {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const { logout } = useAuthStore()

  // 密码强度检测
  const getPasswordStrength = (pwd: string): { level: number; label: string; color: string } => {
    if (!pwd) return { level: 0, label: '', color: '' }

    let score = 0
    if (pwd.length >= 8) score++
    if (pwd.length >= 12) score++
    if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) score++
    if (/\d/.test(pwd)) score++
    if (/[^a-zA-Z0-9]/.test(pwd)) score++

    if (score <= 1) return { level: 1, label: '弱', color: 'var(--color-danger)' }
    if (score === 2) return { level: 2, label: '一般', color: 'var(--color-warning)' }
    if (score === 3) return { level: 3, label: '中等', color: 'var(--color-info)' }
    if (score === 4) return { level: 4, label: '强', color: 'var(--color-success)' }
    return { level: 5, label: '非常强', color: 'var(--color-success)' }
  }

  const strength = getPasswordStrength(newPassword)

  // 提交修改
  const handleSubmit = async () => {
    setError('')

    if (!oldPassword || !newPassword || !confirmPassword) {
      setError('请填写所有字段')
      return
    }

    if (newPassword !== confirmPassword) {
      setError('两次输入的新密码不一致')
      return
    }

    if (newPassword.length < 8) {
      setError('新密码长度不能少于 8 位')
      return
    }

    if (oldPassword === newPassword) {
      setError('新密码不能与旧密码相同')
      return
    }

    setLoading(true)
    try {
      await request('/auth/change-password', {
        method: 'POST',
        data: {
          old_password: oldPassword,
          new_password: newPassword
        }
      })
      setSuccess(true)
      Taro.showToast({ title: '密码修改成功', icon: 'success' })

      // 2秒后跳转登录页
      setTimeout(() => {
        logout()
        Taro.redirectTo({ url: '/pages/login/index?redirect=/pages/change-password/index' })
      }, 2000)
    } catch (err: any) {
      setError(err.message || '修改失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <View className='change-password-page'>
      {success ? (
        <View className='success-state'>
          <Text className='success-icon'>✓</Text>
          <Text className='success-text'>密码修改成功</Text>
          <Text className='success-hint'>正在跳转到登录页...</Text>
        </View>
      ) : (
        <>
          {/* 旧密码 */}
          <View className='form-group'>
            <Text className='form-label'>旧密码</Text>
            <Input
              className='form-input'
              type='password'
              value={oldPassword}
              onInput={(e) => setOldPassword(e.detail.value)}
              placeholder='请输入旧密码'
            />
          </View>

          {/* 新密码 */}
          <View className='form-group'>
            <Text className='form-label'>新密码</Text>
            <Input
              className='form-input'
              type='password'
              value={newPassword}
              onInput={(e) => setNewPassword(e.detail.value)}
              placeholder='请输入新密码（至少 8 位）'
            />
            {/* 强度指示器 */}
            {newPassword && (
              <View className='strength-bar'>
                {[1, 2, 3, 4, 5].map(level => (
                  <View
                    key={level}
                    className={`strength-segment ${level <= strength.level ? 'active' : ''}`}
                    style={level <= strength.level ? { background: strength.color } : {}}
                  />
                ))}
                <Text className='strength-label' style={{ color: strength.color }}>
                  {strength.label}
                </Text>
              </View>
            )}
          </View>

          {/* 确认新密码 */}
          <View className='form-group'>
            <Text className='form-label'>确认新密码</Text>
            <Input
              className={`form-input ${confirmPassword && confirmPassword !== newPassword ? 'error' : ''}`}
              type='password'
              value={confirmPassword}
              onInput={(e) => setConfirmPassword(e.detail.value)}
              placeholder='请再次输入新密码'
            />
            {confirmPassword && confirmPassword === newPassword && (
              <Text className='match-hint'>两次密码一致</Text>
            )}
          </View>

          {/* 错误提示 */}
          {error && (
            <View className='error-section'>
              <Text className='error-text'>{error}</Text>
            </View>
          )}

          {/* 提交按钮 */}
          <View className='submit-bar'>
            <button className='submit-btn' onClick={handleSubmit} disabled={loading}>
              {loading ? '提交中...' : '修改密码'}
            </button>
          </View>
        </>
      )}
    </View>
  )
}
