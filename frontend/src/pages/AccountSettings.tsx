import { useState } from 'react';
import { useAuth } from '../stores/authStore';
import { getCurrentUser, UserResponse, changePassword, UserPasswordChangeRequest } from '../api/authApi';
import { useToast } from '../hooks/useToast';

export default function AccountSettings() {
  const { user: authUser } = useAuth();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const { success, error } = useToast();

  // Change Password Modal State
  const [isChangePasswordModalOpen, setIsChangePasswordModalOpen] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    old_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [passwordChanging, setPasswordChanging] = useState(false);

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

  const handleLoadUser = async () => {
    setLoading(true);
    try {
      const userData = await getCurrentUser();
      setUser(userData);
      success('用户信息加载成功');
    } catch (e) {
      error(e instanceof Error ? e.message : '加载用户信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate new password
    const passwordError = validatePassword(passwordForm.new_password);
    if (passwordError) {
      error(passwordError);
      return;
    }

    // Check if new passwords match
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      error('两次输入的新密码不一致');
      return;
    }

    // Check if new password is same as old
    if (passwordForm.old_password === passwordForm.new_password) {
      error('新密码不能与当前密码相同');
      return;
    }

    setPasswordChanging(true);
    try {
      await changePassword({
        old_password: passwordForm.old_password,
        new_password: passwordForm.new_password
      } as UserPasswordChangeRequest);
      success('密码修改成功');
      setIsChangePasswordModalOpen(false);
      setPasswordForm({ old_password: '', new_password: '', confirm_password: '' });
    } catch (e) {
      error(e instanceof Error ? e.message : '密码修改失败');
    } finally {
      setPasswordChanging(false);
    }
  };

  const displayUser = user || authUser;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold text-white mb-8">账户设置</h1>

        {/* User Info Card */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-6">
          <h2 className="text-xl font-semibold text-white mb-4">基本信息</h2>

          {displayUser ? (
            <div className="space-y-4">
              <div>
                <label className="text-slate-400 text-sm">用户 ID</label>
                <p className="text-white font-mono text-sm">{displayUser.user_id}</p>
              </div>
              <div>
                <label className="text-slate-400 text-sm">用户名</label>
                <p className="text-white">{displayUser.username}</p>
              </div>
              <div>
                <label className="text-slate-400 text-sm">邮箱</label>
                <p className="text-white">{displayUser.email}</p>
              </div>
              <div>
                <label className="text-slate-400 text-sm">角色</label>
                <p className="text-white">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    displayUser.role === 'admin'
                      ? 'bg-purple-500/20 text-purple-400'
                      : 'bg-slate-600/50 text-slate-400'
                  }`}>
                    {displayUser.role}
                  </span>
                </p>
              </div>
              <div>
                <label className="text-slate-400 text-sm">注册时间</label>
                <p className="text-white">{new Date(displayUser.created_at).toLocaleString()}</p>
              </div>
            </div>
          ) : (
            <p className="text-slate-400">点击下方按钮加载您的账户信息</p>
          )}

          <div className="mt-6">
            <button
              onClick={handleLoadUser}
              disabled={loading}
              className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '加载中...' : '加载用户信息'}
            </button>
          </div>
        </div>

        {/* Security Card */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-6">
          <h2 className="text-xl font-semibold text-white mb-4">安全设置</h2>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-900 rounded border border-slate-700">
              <div>
                <h3 className="text-white font-medium mb-1">修改密码</h3>
                <p className="text-slate-400 text-sm">定期修改密码可以提高账户安全性</p>
              </div>
              <button
                onClick={() => setIsChangePasswordModalOpen(true)}
                className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded transition-colors text-sm font-medium"
              >
                <i className="fa-solid fa-key mr-2"></i>
                修改密码
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Change Password Modal */}
      {isChangePasswordModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 p-6 rounded-lg w-full max-w-md border border-slate-700">
            <h3 className="text-xl font-bold text-white mb-4">修改密码</h3>

            <form onSubmit={handleChangePassword}>
              <div className="mb-4">
                <label className="block text-slate-300 mb-2 text-sm">当前密码</label>
                <input
                  type="password"
                  value={passwordForm.old_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, old_password: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none text-sm"
                  required
                />
              </div>

              <div className="mb-4">
                <label className="block text-slate-300 mb-2 text-sm">新密码</label>
                <input
                  type="password"
                  value={passwordForm.new_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                  placeholder="至少 8 位，包含大小写字母、数字和特殊字符"
                  className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none text-sm"
                  required
                />
                <p className="text-slate-500 text-xs mt-1">
                  密码要求：8-100 位，至少包含大写字母、小写字母、数字和特殊字符各一个
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-slate-300 mb-2 text-sm">确认新密码</label>
                <input
                  type="password"
                  value={passwordForm.confirm_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none text-sm"
                  required
                />
              </div>

              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setIsChangePasswordModalOpen(false);
                    setPasswordForm({ old_password: '', new_password: '', confirm_password: '' });
                  }}
                  className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
                  disabled={passwordChanging}
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={passwordChanging}
                  className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {passwordChanging ? '修改中...' : '确认修改'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
