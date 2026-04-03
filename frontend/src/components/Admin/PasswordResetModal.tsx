import { useState } from 'react';

interface PasswordResetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (mode: 'direct' | 'random', password?: string) => Promise<void>;
  username: string;
}

export default function PasswordResetModal({ isOpen, onClose, onConfirm, username }: PasswordResetModalProps) {
  const [mode, setMode] = useState<'direct' | 'random'>('random');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [generatedPassword, setGeneratedPassword] = useState('');

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

      await onConfirm(mode, mode === 'direct' ? password : undefined);
      setSuccess(true);
      if (mode === 'random') {
        setGeneratedPassword(password);
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

  if (!isOpen) return null;

  // Success state - show generated password
  if (success && mode === 'random' && generatedPassword) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-slate-800 p-6 rounded-lg w-full max-w-md border border-slate-700 text-center">
          <div className="w-16 h-16 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <i className="fa-solid fa-check text-2xl"></i>
          </div>
          <h3 className="text-xl font-bold text-white mb-2">密码重置成功</h3>
          <p className="text-slate-400 mb-6">系统已为用户 <span className="text-cyan-400">{username}</span> 生成随机密码</p>

          <div className="bg-slate-900 p-4 rounded mb-6 select-all font-mono text-cyan-400 text-lg break-all border border-slate-700">
            {generatedPassword}
          </div>

          <p className="text-slate-500 text-sm mb-6">请复制上方密码并发送给用户</p>

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

  // Success state for direct mode
  if (success && mode === 'direct') {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-slate-800 p-6 rounded-lg w-full max-w-md border border-slate-700 text-center">
          <div className="w-16 h-16 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <i className="fa-solid fa-check text-2xl"></i>
          </div>
          <h3 className="text-xl font-bold text-white mb-2">密码重置成功</h3>
          <p className="text-slate-400 mb-6">用户 <span className="text-cyan-400">{username}</span> 的密码已更新</p>

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

  // Form state
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 p-6 rounded-lg w-full max-w-md border border-slate-700">
        <h3 className="text-xl font-bold text-white mb-4">重置密码 - {username}</h3>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-slate-300 mb-2 text-sm">重置模式</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="mode"
                  value="random"
                  checked={mode === 'random'}
                  onChange={() => setMode('random')}
                  className="text-cyan-500 focus:ring-cyan-500"
                />
                <span className="text-white text-sm">随机生成密码</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="mode"
                  value="direct"
                  checked={mode === 'direct'}
                  onChange={() => setMode('direct')}
                  className="text-cyan-500 focus:ring-cyan-500"
                />
                <span className="text-white text-sm">自行设置密码</span>
              </label>
            </div>
          </div>

          {mode === 'direct' && (
            <div className="mb-4">
              <label className="block text-slate-300 mb-2 text-sm">新密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="至少 8 位，包含大小写字母、数字和特殊字符"
                className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none text-sm"
              />
              <p className="text-slate-500 text-xs mt-1">
                密码要求：8-100 位，至少包含大写字母、小写字母、数字和特殊字符各一个
              </p>
            </div>
          )}

          {error && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded text-red-400 text-sm">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
              disabled={loading}
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '重置中...' : '确认重置'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
