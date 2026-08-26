import { useState } from 'react';
import { changePassword } from '../../api/authApi';
import { useToast } from '../../hooks/useToast';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Check } from 'lucide-react';

interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function ChangePasswordModal({ isOpen, onClose, onSuccess }: ChangePasswordModalProps) {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const { success: toastSuccess, error: toastError } = useToast();

  const validatePassword = (password: string): string | null => {
    if (password.length < 8 || password.length > 100) {
      return '密码长度必须在 8-100 位之间';
    }
    if (!/[A-Z]/.test(password)) {
      return '密码必须包含至少 1 个大写字母';
    }
    if (!/[a-z]/.test(password)) {
      return '密码必须包含至少 1 个小写字母';
    }
    if (!/\d/.test(password)) {
      return '密码必须包含至少 1 个数字';
    }
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(password)) {
      return '密码必须包含至少 1 个特殊字符';
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validate passwords
    const newPasswordError = validatePassword(newPassword);
    if (newPasswordError) {
      setError(newPasswordError);
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('两次输入的新密码不一致');
      return;
    }

    if (oldPassword === newPassword) {
      setError('新密码不能与当前密码相同');
      return;
    }

    setLoading(true);

    try {
      const result = await changePassword({
        old_password: oldPassword,
        new_password: newPassword
      });

      if (result.success) {
        setSuccess(true);
        toastSuccess('密码修改成功');
        onSuccess?.();
        setTimeout(() => {
          handleClose();
        }, 1500);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '密码修改失败');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setSuccess(false);
    setOldPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setError('');
    onClose();
  };

  if (!isOpen) return null;

  if (success) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-surface-1 p-6 rounded-lg w-full max-w-md border border-border text-center">
          <div className="w-16 h-16 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <Check className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-bold text-white mb-2">密码修改成功</h3>
          <p className="text-ink-muted mb-6">您的密码已更新，请使用新密码登录</p>

          <Button onClick={handleClose} className="w-full">
            完成
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-surface-1 p-6 rounded-lg w-full max-w-md border border-border">
        <h3 className="text-xl font-bold text-white mb-4">修改密码</h3>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-ink-muted mb-2 text-sm">当前密码</label>
            <Input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              required
            />
          </div>

          <div className="mb-4">
            <label className="block text-ink-muted mb-2 text-sm">新密码</label>
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="至少 8 位，包含大小写字母、数字和特殊字符"
              required
            />
            <p className="text-ink-faint text-xs mt-1">
              密码要求：8-100 位，至少包含大写字母、小写字母、数字和特殊字符各一个
            </p>
          </div>

          <div className="mb-4">
            <label className="block text-ink-muted mb-2 text-sm">确认新密码</label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <div className="mb-4 p-3 bg-danger/20 border border-red-500 rounded text-danger text-sm">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <Button
              type="button"
              variant="ghost"
              onClick={handleClose}
              disabled={loading}
            >
              取消
            </Button>
            <Button
              type="submit"
              disabled={loading}
            >
              {loading ? '修改中...' : '确认修改'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
