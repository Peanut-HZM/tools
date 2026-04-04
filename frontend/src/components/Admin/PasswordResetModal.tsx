import { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';

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
        <div className="bg-gradient-to-br from-slate-800 to-slate-900 p-8 rounded-2xl w-full max-w-md border border-slate-600/50 shadow-2xl shadow-cyan-500/10 text-center animate-scaleIn">
          {/* 成功图标 */}
          <div className="relative mx-auto mb-6">
            <div className="w-20 h-20 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-full flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <i className="fa-solid fa-check text-3xl text-white"></i>
            </div>
            <div className="absolute -inset-2 bg-emerald-400/20 rounded-full blur-xl animate-pulse"></div>
          </div>
          
          <h3 className="text-2xl font-bold text-white mb-2">密码重置成功</h3>
          <p className="text-slate-300 mb-6">
            系统已为用户 <span className="text-cyan-400 font-semibold">{username}</span> 生成随机密码
          </p>

          {/* 密码显示框 */}
          <div className="relative bg-slate-950/80 p-5 rounded-xl mb-6 font-mono text-cyan-300 text-lg break-all border-2 border-cyan-500/30 shadow-inner">
            <div className="absolute right-3 top-3 text-cyan-500/60">
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
                ? 'bg-gradient-to-r from-emerald-500 to-emerald-600 text-white shadow-lg shadow-emerald-500/25 cursor-default'
                : 'bg-slate-700 hover:bg-slate-600 text-white hover:shadow-lg hover:shadow-slate-700/25 active:scale-[0.98]'
            }`}
          >
            <i className={`fa-${copied ? 'solid fa-check' : 'regular fa-copy'}`}></i>
            {copied ? '已复制' : '复制密码'}
          </button>

          {/* 完成按钮 */}
          <button
            onClick={handleClose}
            className="w-full px-4 py-3 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-600 hover:to-cyan-700 text-white rounded-xl transition-all duration-200 font-medium text-base shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 active:scale-[0.98]"
          >
            完成
          </button>
        </div>
      </div>
    );
  }

  // Success state for direct mode
  if (success && mode === 'direct') {
    return (
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[9999] animate-fadeIn">
        <div className="bg-gradient-to-br from-slate-800 to-slate-900 p-8 rounded-2xl w-full max-w-md border border-slate-600/50 shadow-2xl shadow-cyan-500/10 text-center animate-scaleIn">
          {/* 成功图标 */}
          <div className="relative mx-auto mb-6">
            <div className="w-20 h-20 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-full flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <i className="fa-solid fa-check text-3xl text-white"></i>
            </div>
            <div className="absolute -inset-2 bg-emerald-400/20 rounded-full blur-xl animate-pulse"></div>
          </div>
          
          <h3 className="text-2xl font-bold text-white mb-2">密码重置成功</h3>
          <p className="text-slate-300 mb-8">用户 <span className="text-cyan-400 font-semibold">{username}</span> 的密码已更新</p>

          <button
            onClick={handleClose}
            className="w-full px-4 py-3 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-600 hover:to-cyan-700 text-white rounded-xl transition-all duration-200 font-medium text-base shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 active:scale-[0.98]"
          >
            完成
          </button>
        </div>
      </div>
    );
  }

  // Form state
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[9999] animate-fadeIn">
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 p-8 rounded-2xl w-full max-w-md border border-slate-600/50 shadow-2xl shadow-cyan-500/10 animate-scaleIn">
        <h3 className="text-2xl font-bold text-white mb-6">重置密码 - {username}</h3>

        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <label className="block text-slate-300 mb-3 text-sm font-medium">重置模式</label>
            <div className="flex gap-6">
              <label className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="radio"
                  name="mode"
                  value="random"
                  checked={mode === 'random'}
                  onChange={() => setMode('random')}
                  className="text-cyan-500 focus:ring-cyan-500 focus:ring-2"
                />
                <span className="text-white text-sm group-hover:text-cyan-300 transition-colors">随机生成密码</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="radio"
                  name="mode"
                  value="direct"
                  checked={mode === 'direct'}
                  onChange={() => setMode('direct')}
                  className="text-cyan-500 focus:ring-cyan-500 focus:ring-2"
                />
                <span className="text-white text-sm group-hover:text-cyan-300 transition-colors">自行设置密码</span>
              </label>
            </div>
          </div>

          {mode === 'direct' && (
            <div className="mb-6">
              <label className="block text-slate-300 mb-2 text-sm font-medium">新密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="至少 8 位，包含大小写字母、数字和特殊字符"
                className="w-full bg-slate-950/80 border border-slate-600 rounded-xl px-4 py-3 text-white focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 outline-none text-sm transition-all"
              />
              <p className="text-slate-500 text-xs mt-2">
                密码要求：8-100 位，至少包含大写字母、小写字母、数字和特殊字符各一个
              </p>
            </div>
          )}

          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm flex items-center gap-2">
              <i className="fa-solid fa-circle-exclamation"></i>
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="px-6 py-3 text-slate-300 hover:text-white hover:bg-slate-700/50 rounded-xl transition-all"
              disabled={loading}
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-600 hover:to-cyan-700 text-white rounded-xl transition-all duration-200 font-medium shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none active:scale-[0.98]"
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
      </div>
    </div>
  );
}
