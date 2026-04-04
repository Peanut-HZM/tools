import { useState, useEffect, useMemo } from 'react';
import { listUsers, updateUserRole, deleteUser, createUser, batchDeleteUsers, batchUpdateUserRole, UserListResponse, resetUserPassword } from '../../api/adminApi';
import { UserResponse } from '../../api/authApi';
import { useToast } from '../../hooks/useToast';
import PasswordResetModal from './PasswordResetModal';

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];
const DEFAULT_PAGE_SIZE = 20;

export default function UserManagement() {
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [totalPages, setTotalPages] = useState(0);

  // Search and filter
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');

  // Batch selection
  const [selectedUserIds, setSelectedUserIds] = useState<Set<string>>(new Set());
  const [isAllSelected, setIsAllSelected] = useState(false);

  // Batch operation mode
  const [batchMode, setBatchMode] = useState(false);
  const [batchRole, setBatchRole] = useState('user');

  const { success, error } = useToast();

  // Add User Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', email: '', role: 'user' });
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(null);

  // Password Reset Modal State
  const [isPasswordResetModalOpen, setIsPasswordResetModalOpen] = useState(false);
  const [selectedUserForReset, setSelectedUserForReset] = useState<{ userId: string; username: string } | null>(null);

  const fetchUsers = async (pageNum = page, searchValue = search, roleValue = roleFilter) => {
    setLoading(true);
    try {
      const params: { page: number; page_size: number; search?: string; role?: string } = {
        page: pageNum,
        page_size: pageSize,
      };
      if (searchValue) params.search = searchValue;
      if (roleValue) params.role = roleValue;

      const data: UserListResponse = await listUsers(params);
      setUsers(Array.isArray(data?.users) ? data.users : []);
      setTotal(data?.total || 0);
      setTotalPages(data?.total_pages || 0);
      setPage(data?.page || 1);
    } catch (e) {
      setUsers([]);
      error('获取用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // Refresh when page size changes
  useEffect(() => {
    fetchUsers(1);
  }, [pageSize]);

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await updateUserRole(userId, newRole);
      setUsers(users.map(u => u.user_id === userId ? { ...u, role: newRole } : u));
      success('角色更新成功');
    } catch (e) {
      error('角色更新失败');
    }
  };

  const handleDelete = async (userId: string) => {
    if (!confirm('确定要删除该用户吗？此操作不可恢复！')) return;

    try {
      await deleteUser(userId);
      setUsers(users.filter(u => u.user_id !== userId));
      setTotal(total - 1);
      success('用户删除成功');
    } catch (e) {
      error('用户删除失败');
    }
  };

  const handleResetPassword = async (userId: string, username: string) => {
    setSelectedUserForReset({ userId, username });
    setIsPasswordResetModalOpen(true);
  };

  const handleConfirmPasswordReset = async (mode: 'direct' | 'random', newPassword?: string) => {
    if (!selectedUserForReset) return { success: false };

    try {
      const result = await resetUserPassword(selectedUserForReset.userId, {
        mode,
        new_password: mode === 'direct' ? newPassword : undefined
      });

      if (result.success) {
        success(result.message);
        return { success: true, newPassword: result.new_password };
      }
      return { success: false };
    } catch (e) {
      throw e;
    }
  };

  // Batch selection handlers
  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    const checked = e.target.checked;
    setIsAllSelected(checked);
    if (checked) {
      setSelectedUserIds(new Set(users.map(u => u.user_id)));
    } else {
      setSelectedUserIds(new Set());
    }
  };

  const handleSelectUser = (userId: string) => {
    const newSelected = new Set(selectedUserIds);
    if (newSelected.has(userId)) {
      newSelected.delete(userId);
    } else {
      newSelected.add(userId);
    }
    setSelectedUserIds(newSelected);
    setIsAllSelected(newSelected.size === users.length && users.length > 0);
  };

  // Batch operations
  const handleBatchDelete = async () => {
    if (selectedUserIds.size === 0) {
      error('请先选择要删除的用户');
      return;
    }

    if (!confirm(`确定要删除选中的 ${selectedUserIds.size} 个用户吗？此操作不可恢复！`)) return;

    try {
      const result = await batchDeleteUsers(Array.from(selectedUserIds));
      if (result.success_count > 0) {
        success(`成功删除 ${result.success_count} 个用户`);
        setSelectedUserIds(new Set());
        setIsAllSelected(false);
        fetchUsers();
      }
      if (result.failed_count > 0) {
        error(`删除失败：${result.failed_count} 个，${result.errors.join(', ')}`);
      }
    } catch (e) {
      error(e instanceof Error ? e.message : '批量删除失败');
    }
  };

  const handleBatchUpdateRole = async () => {
    if (selectedUserIds.size === 0) {
      error('请先选择要修改的用户');
      return;
    }

    try {
      const result = await batchUpdateUserRole(Array.from(selectedUserIds), batchRole);
      if (result.success_count > 0) {
        success(`成功修改 ${result.success_count} 个用户的角色`);
        setSelectedUserIds(new Set());
        setIsAllSelected(false);
        fetchUsers();
      }
      if (result.failed_count > 0) {
        error(`修改失败：${result.failed_count} 个，${result.errors.join(', ')}`);
      }
    } catch (e) {
      error(e instanceof Error ? e.message : '批量修改失败');
    }
  };

  const handleSearch = () => {
    setPage(1);
    fetchUsers(1, search, roleFilter);
  };

  const handleReset = () => {
    setSearch('');
    setRoleFilter('');
    setPage(1);
    fetchUsers(1, '', '');
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const result = await createUser(newUser);
      setGeneratedPassword(result.password);
      success('用户创建成功');
      fetchUsers();
    } catch (e) {
      error(e instanceof Error ? e.message : '创建用户失败');
    }
  };

  const closeGeneratedPasswordModal = () => {
    setGeneratedPassword(null);
    setIsModalOpen(false);
    setNewUser({ username: '', email: '', role: 'user' });
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      fetchUsers(newPage);
    }
  };

  const toggleBatchMode = () => {
    setBatchMode(!batchMode);
    setSelectedUserIds(new Set());
    setIsAllSelected(false);
  };

  // Pagination controls
  const paginationControls = useMemo(() => {
    const pages: (number | string)[] = [];
    const maxVisible = 5;

    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      if (page <= 3) {
        for (let i = 1; i <= 3; i++) pages.push(i);
        pages.push('...');
        pages.push(totalPages);
      } else if (page >= totalPages - 2) {
        pages.push(1);
        pages.push('...');
        for (let i = totalPages - 2; i <= totalPages; i++) pages.push(i);
      } else {
        pages.push(1);
        pages.push('...');
        pages.push(page - 1);
        pages.push(page);
        pages.push(page + 1);
        pages.push('...');
        pages.push(totalPages);
      }
    }
    return pages;
  }, [page, totalPages]);

  if (loading) return <div className="text-white">加载中...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">用户管理</h2>
        <div className="flex gap-3">
          <button
            onClick={toggleBatchMode}
            className={`px-4 py-2 rounded-lg transition-colors text-sm font-medium ${
              batchMode
                ? 'bg-orange-500 hover:bg-orange-600 text-white'
                : 'bg-slate-600 hover:bg-slate-500 text-white'
            }`}
          >
            <i className={`fa-solid ${batchMode ? 'fa-check' : 'fa-list-check'} mr-2`}></i>
            {batchMode ? '完成选择' : '批量操作'}
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg transition-colors text-sm font-medium"
          >
            <i className="fa-solid fa-plus mr-2"></i>添加用户
          </button>
        </div>
      </div>

      {/* Batch operation toolbar */}
      {batchMode && selectedUserIds.size > 0 && (
        <div className="mb-4 p-4 bg-slate-700/50 border border-slate-600 rounded-lg flex items-center justify-between">
          <span className="text-white text-sm">
            已选择 <span className="text-cyan-400 font-bold">{selectedUserIds.size}</span> 个用户
          </span>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <select
                value={batchRole}
                onChange={(e) => setBatchRole(e.target.value)}
                className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:border-cyan-500 outline-none"
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
              <button
                onClick={handleBatchUpdateRole}
                className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm transition-colors"
              >
                <i className="fa-solid fa-user-pen mr-1"></i>
                批量改角色
              </button>
            </div>
            <button
              onClick={handleBatchDelete}
              className="px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white rounded text-sm transition-colors"
            >
              <i className="fa-solid fa-trash mr-1"></i>
              批量删除
            </button>
          </div>
        </div>
      )}

      {/* Search and filter */}
      <div className="mb-4 flex items-center gap-4">
        <div className="flex-1 flex items-center gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="搜索用户名或邮箱..."
            className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white text-sm focus:border-cyan-500 outline-none"
          />
          <button
            onClick={handleSearch}
            className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg transition-colors text-sm"
          >
            <i className="fa-solid fa-search mr-2"></i>
            搜索
          </button>
          <button
            onClick={handleReset}
            className="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white rounded-lg transition-colors text-sm"
          >
            <i className="fa-solid fa-rotate-left mr-2"></i>
            重置
          </button>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-400 text-sm">角色:</span>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:border-cyan-500 outline-none"
          >
            <option value="">全部</option>
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-slate-300">
          <thead className="bg-slate-700 text-slate-100 uppercase text-xs">
            <tr>
              <th className="px-6 py-3 w-12">
                {batchMode && (
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    onChange={handleSelectAll}
                    className="rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500"
                  />
                )}
              </th>
              <th className="px-6 py-3">用户名</th>
              <th className="px-6 py-3">邮箱</th>
              <th className="px-6 py-3">角色</th>
              <th className="px-6 py-3">注册时间</th>
              <th className="px-6 py-3">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {(users || []).map((user) => (
              <tr key={user.user_id} className="hover:bg-slate-700/50">
                <td className="px-6 py-4">
                  {batchMode && (
                    <input
                      type="checkbox"
                      checked={selectedUserIds.has(user.user_id)}
                      onChange={() => handleSelectUser(user.user_id)}
                      className="rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500"
                    />
                  )}
                </td>
                <td className="px-6 py-4">{user.username}</td>
                <td className="px-6 py-4">{user.email}</td>
                <td className="px-6 py-4">
                  {!batchMode ? (
                    <select
                      value={user.role}
                      onChange={(e) => handleRoleChange(user.user_id, e.target.value)}
                      className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-sm focus:border-cyan-500 outline-none"
                    >
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                    </select>
                  ) : (
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      user.role === 'admin'
                        ? 'bg-purple-500/20 text-purple-400'
                        : 'bg-slate-600/50 text-slate-400'
                    }`}>
                      {user.role}
                    </span>
                  )}
                </td>
                <td className="px-6 py-4">
                  {new Date(user.created_at).toLocaleString()}
                </td>
                <td className="px-6 py-4">
                  {!batchMode && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleResetPassword(user.user_id, user.username)}
                        className="text-orange-400 hover:text-orange-300 transition-colors text-sm"
                      >
                        重置密码
                      </button>
                      <button
                        onClick={() => handleDelete(user.user_id)}
                        className="text-red-400 hover:text-red-300 transition-colors text-sm"
                      >
                        删除
                      </button>
                    </div>
                  )}
                  {batchMode && (
                    <span className="text-slate-500 text-xs">批量操作中...</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="mt-4 flex items-center justify-between border-t border-slate-700 pt-4">
        <div className="flex items-center gap-2">
          <span className="text-slate-400 text-sm">每页显示:</span>
          <select
            value={pageSize}
            onChange={(e) => setPageSize(Number(e.target.value))}
            className="bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-white focus:border-cyan-500 outline-none"
          >
            {PAGE_SIZE_OPTIONS.map(size => (
              <option key={size} value={size}>{size}</option>
            ))}
          </select>
          <span className="text-slate-400 text-sm">
            共 <span className="text-cyan-400 font-medium">{total}</span> 条记录
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => handlePageChange(1)}
            disabled={page === 1}
            className={`px-3 py-1.5 rounded text-sm transition-colors ${
              page === 1
                ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            首页
          </button>
          <button
            onClick={() => handlePageChange(page - 1)}
            disabled={page === 1}
            className={`px-3 py-1.5 rounded text-sm transition-colors ${
              page === 1
                ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            <i className="fa-solid fa-chevron-left"></i>
          </button>

          {paginationControls.map((p, index) => (
            <button
              key={index}
              onClick={() => typeof p === 'number' && handlePageChange(p)}
              disabled={p === '...'}
              className={`px-3 py-1.5 rounded text-sm transition-colors ${
                p === page
                  ? 'bg-cyan-500 text-white font-medium'
                  : p === '...'
                    ? 'bg-transparent text-slate-500 cursor-default'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {p}
            </button>
          ))}

          <button
            onClick={() => handlePageChange(page + 1)}
            disabled={page === totalPages}
            className={`px-3 py-1.5 rounded text-sm transition-colors ${
              page === totalPages
                ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            <i className="fa-solid fa-chevron-right"></i>
          </button>
          <button
            onClick={() => handlePageChange(totalPages)}
            disabled={page === totalPages}
            className={`px-3 py-1.5 rounded text-sm transition-colors ${
              page === totalPages
                ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            末页
          </button>
        </div>
      </div>

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

      {/* Password Reset Modal */}
      {isPasswordResetModalOpen && selectedUserForReset && (
        <PasswordResetModal
          isOpen={isPasswordResetModalOpen}
          onClose={() => {
            setIsPasswordResetModalOpen(false);
            setSelectedUserForReset(null);
          }}
          onConfirm={handleConfirmPasswordReset}
          username={selectedUserForReset.username}
        />
      )}
    </div>
  );
}
