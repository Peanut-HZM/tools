import { useState, useEffect } from 'react';
import { listUsers, updateUserRole, deleteUser, createUser } from '../../api/adminApi';
import { UserResponse } from '../../api/authApi';
import { useToast } from '../../hooks/useToast';
import Toast from '../MarkdownEditor/Toast/Toast';

export default function UserManagement() {
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast, showToast } = useToast();
  
  // Add User Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', email: '', role: 'user' });
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(null);

  const fetchUsers = async () => {
    try {
      const data = await listUsers();
      setUsers(data);
    } catch (error) {
      showToast('获取用户列表失败', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await updateUserRole(userId, newRole);
      setUsers(users.map(u => u.user_id === userId ? { ...u, role: newRole } : u));
      showToast('角色更新成功', 'success');
    } catch (error) {
      showToast('角色更新失败', 'error');
    }
  };

  const handleDelete = async (userId: string) => {
    if (!confirm('确定要删除该用户吗？此操作不可恢复！')) return;
    
    try {
      await deleteUser(userId);
      setUsers(users.filter(u => u.user_id !== userId));
      showToast('用户删除成功', 'success');
    } catch (error) {
      showToast('用户删除失败', 'error');
    }
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const result = await createUser(newUser);
      setGeneratedPassword(result.password);
      showToast('用户创建成功', 'success');
      fetchUsers();
    } catch (error) {
      showToast(error instanceof Error ? error.message : '创建用户失败', 'error');
    }
  };

  const closeGeneratedPasswordModal = () => {
    setGeneratedPassword(null);
    setIsModalOpen(false);
    setNewUser({ username: '', email: '', role: 'user' });
  };

  if (loading) return <div className="text-white">加载中...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">用户管理</h2>
        <button
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg transition-colors text-sm font-medium"
        >
          <i className="fa-solid fa-plus mr-2"></i>添加用户
        </button>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left text-slate-300">
          <thead className="bg-slate-700 text-slate-100 uppercase text-xs">
            <tr>
              <th className="px-6 py-3">用户名</th>
              <th className="px-6 py-3">邮箱</th>
              <th className="px-6 py-3">角色</th>
              <th className="px-6 py-3">注册时间</th>
              <th className="px-6 py-3">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {users.map((user) => (
              <tr key={user.user_id} className="hover:bg-slate-700/50">
                <td className="px-6 py-4">{user.username}</td>
                <td className="px-6 py-4">{user.email}</td>
                <td className="px-6 py-4">
                  <select
                    value={user.role}
                    onChange={(e) => handleRoleChange(user.user_id, e.target.value)}
                    className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-sm focus:border-cyan-500 outline-none"
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </td>
                <td className="px-6 py-4">
                  {new Date(user.created_at).toLocaleString()}
                </td>
                <td className="px-6 py-4">
                  <button
                    onClick={() => handleDelete(user.user_id)}
                    className="text-red-400 hover:text-red-300 transition-colors text-sm"
                  >
                    删除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => {}}
        />
      )}

      {/* Add User Modal */}
      {isModalOpen && !generatedPassword && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 p-6 rounded-lg w-full max-w-md border border-slate-700">
            <h3 className="text-xl font-bold text-white mb-4">添加新用户</h3>
            <form onSubmit={handleAddUser}>
              <div className="mb-4">
                <label className="block text-slate-300 mb-2 text-sm">用户名</label>
                <input
                  type="text"
                  required
                  value={newUser.username}
                  onChange={e => setNewUser({ ...newUser, username: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none"
                />
              </div>
              <div className="mb-4">
                <label className="block text-slate-300 mb-2 text-sm">邮箱</label>
                <input
                  type="email"
                  required
                  value={newUser.email}
                  onChange={e => setNewUser({ ...newUser, email: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none"
                />
              </div>
              <div className="mb-6">
                <label className="block text-slate-300 mb-2 text-sm">角色</label>
                <select
                  value={newUser.role}
                  onChange={e => setNewUser({ ...newUser, role: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded transition-colors"
                >
                  创建用户
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Password Display Modal */}
      {generatedPassword && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 p-6 rounded-lg w-full max-w-md border border-slate-700 text-center">
            <div className="w-16 h-16 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <i className="fa-solid fa-check text-2xl"></i>
            </div>
            <h3 className="text-xl font-bold text-white mb-2">用户创建成功</h3>
            <p className="text-slate-400 mb-6">请复制下方生成的随机密码并发送给用户。</p>
            
            <div className="bg-slate-900 p-4 rounded mb-6 select-all font-mono text-cyan-400 text-lg break-all border border-slate-700">
              {generatedPassword}
            </div>
            
            <button
              onClick={closeGeneratedPasswordModal}
              className="w-full px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded transition-colors"
            >
              完成
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
