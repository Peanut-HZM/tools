import { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';

interface PasswordResetResult {
  success: boolean;
  newPassword?: string;
  message?: string;
}

interface PasswordResetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (mode: 'direct' | 'random', password?: string) => Promise<PasswordResetResult>;
  username: string;
}

export default function PasswordResetModal({ isOpen, onClose, onConfirm, username }: PasswordResetModalProps) {
  const { success: toastSuccess, error: toastError } = useToast();
  const [mode, setMode] = useState<'direct' | 'random'>('random');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [generatedPassword, setGeneratedPassword] = useState('');
  const [copied, setCopied] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (mode === 'direct' && !password) {
        setError('请输入新密码');
        setLoading(false);
        return;
      }

      const result = await onConfirm(mode, mode === 'direct' ? password : undefined);
      setSuccess(true);
      if (mode === 'random' && result.newPassword) {
        setGeneratedPassword(result.newPassword);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '重置密码失败');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setSuccess(false);
    setGeneratedPassword('');
    setPassword('');
    setError('');
    setMode('random');
    onClose();
  };

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

  // 密码重置成功后自动复制
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
  }, [success, mode, generatedPassword, isOpen, toastSuccess]);

  if (!isOpen) return null;

  // Success state - show generated password
  if (success && mode === 'random' && generatedPassword) {
    return (
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[9999] animate-fadeIn">
        <Card className="p-8 rounded-2xl w-full max-w-md shadow-lg shadow-accent/10 text-center animate-scaleIn">
          {/* 成功图标 */}
          <div className="relative mx-auto mb-6">
            <div className="w-20 h-20 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-full flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <i className="fa-solid fa-check text-3xl text-ink-inverse"></i>
            </div>
            <div className="absolute -inset-2 bg-emerald-400/20 rounded-full blur-xl animate-pulse"></div>
          </div>

          <h3 className="text-2xl font-bold text-ink-inverse mb-2">密码重置成功</h3>
          <p className="text-ink-muted mb-6">
            系统已为用户 <span className="text-accent font-semibold">{username}</span> 生成随机密码
          </p>

          {/* 密码显示框 */}
          <div className="relative bg-canvas/80 p-5 rounded-xl mb-6 font-mono text-accent text-lg break-all border-2 border-accent/30 shadow-inner">
            <div className="absolute right-3 top-3 text-accent/60">
              <i className="fa-solid fa-key"></i>
            </div>
            <div className="pr-8 select-all">{generatedPassword}</div>
          </div>

          {/* 复制按钮 */}
          <button
            onClick={handleCopyPassword}
            disabled={copied}
            className={`w-full mb-3 px-4 py-3 rounded-xl transition-all duration-200 flex items-center justify-center gap-2 font-medium text-base ${
              copied
                ? 'bg-gradient-to-r from-emerald-500 to-emerald-600 text-ink-inverse shadow-lg shadow-emerald-500/25 cursor-default'
                : 'bg-surface-2 hover:bg-surface-3 text-ink-inverse hover:shadow-lg hover:shadow-surface-2/25 active:scale-[0.98]'
            }`}
          >
            <i className={`fa-${copied ? 'solid fa-check' : 'regular fa-copy'}`}></i>
            {copied ? '已复制' : '复制密码'}
          </button>

          {/* 完成按钮 */}
          <button
            onClick={handleClose}
            className="w-full px-4 py-3 bg-gradient-to-r from-accent to-accent-hover hover:from-accent-hover hover:to-accent text-white rounded-xl transition-all duration-200 font-medium text-base shadow-lg shadow-accent/25 hover:shadow-accent/40 active:scale-[0.98]"
          >
            完成
          </button>
        </Card>
      </div>
    );
  }

  // Success state for direct mode
  if (success && mode === 'direct') {
    return (
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[9999] animate-fadeIn">
        <Card className="p-8 rounded-2xl w-full max-w-md shadow-lg shadow-accent/10 text-center animate-scaleIn">
          {/* 成功图标 */}
          <div className="relative mx-auto mb-6">
            <div className="w-20 h-20 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-full flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <i className="fa-solid fa-check text-3xl text-ink-inverse"></i>
            </div>
            <div className="absolute -inset-2 bg-emerald-400/20 rounded-full blur-xl animate-pulse"></div>
          </div>

          <h3 className="text-2xl font-bold text-ink-inverse mb-2">密码重置成功</h3>
          <p className="text-ink-muted mb-8">用户 <span className="text-accent font-semibold">{username}</span> 的密码已更新</p>

          <button
            onClick={handleClose}
            className="w-full px-4 py-3 bg-gradient-to-r from-accent to-accent-hover hover:from-accent-hover hover:to-accent text-white rounded-xl transition-all duration-200 font-medium text-base shadow-lg shadow-accent/25 hover:shadow-accent/40 active:scale-[0.98]"
          >
            完成
          </button>
        </Card>
      </div>
    );
  }

  // Form state
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[9999] animate-fadeIn">
      <Card className="p-8 rounded-2xl w-full max-w-md shadow-lg shadow-accent/10 animate-scaleIn">
        <h3 className="text-2xl font-bold text-ink-inverse mb-6">重置密码 - {username}</h3>

        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <label className="block text-ink-muted mb-3 text-sm font-medium">重置模式</label>
            <div className="flex gap-6">
              <label className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="radio"
                  name="mode"
                  value="random"
                  checked={mode === 'random'}
                  onChange={() => setMode('random')}
                  className="text-accent focus:ring-accent focus:ring-2"
                />
                <span className="text-ink-inverse text-sm group-hover:text-accent transition-colors">随机生成密码</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="radio"
                  name="mode"
                  value="direct"
                  checked={mode === 'direct'}
                  onChange={() => setMode('direct')}
                  className="text-accent focus:ring-accent focus:ring-2"
                />
                <span className="text-ink-inverse text-sm group-hover:text-accent transition-colors">自行设置密码</span>
              </label>
            </div>
          </div>

          {mode === 'direct' && (
            <div className="mb-6">
              <label className="block text-ink-muted mb-2 text-sm font-medium">新密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="至少 8 位，包含大小写字母、数字和特殊字符"
                className="w-full bg-canvas/80 border border-border rounded-xl px-4 py-3 text-ink-inverse focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none text-sm transition-all"
              />
              <p className="text-ink-faint text-xs mt-2">
                密码要求：8-100 位，至少包含大写字母、小写字母、数字和特殊字符各一个
              </p>
            </div>
          )}

          {error && (
            <div className="mb-6 p-4 bg-danger/10 border border-danger/30 rounded-xl text-danger text-sm flex items-center gap-2">
              <i className="fa-solid fa-circle-exclamation"></i>
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <Button
              variant="ghost"
              type="button"
              onClick={handleClose}
              disabled={loading}
            >
              取消
            </Button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-gradient-to-r from-accent to-accent-hover hover:from-accent-hover hover:to-accent text-white rounded-xl transition-all duration-200 font-medium shadow-lg shadow-accent/25 hover:shadow-accent/40 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none active:scale-[0.98]"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <i className="fa-solid fa-spinner fa-spin"></i>
                  重置中...
                </span>
              ) : '确认重置'}
            </button>
          </div>
        </form>
      </Card>
    </div>
  );
}
