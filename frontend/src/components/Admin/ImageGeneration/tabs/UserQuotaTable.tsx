/**
 * 用户配额表 Tab — Task 12.1
 * 搜索 + 分页 + 编辑/分配/撤销/重置操作
 */
import { useEffect, useState } from 'react';
import {
  listQuotaUsers,
  revokeQuota,
  resetCounters,
  QuotaUser,
  QuotaUserListResponse,
} from '../../../../api/adminImageGenerationApi';
import { useI18n } from '../../../../i18n';
import GrantQuotaDialog from '../GrantQuotaDialog';

const PAGE_SIZE = 20;

export default function UserQuotaTable() {
  const { t } = useI18n();
  const igT = t.imageGeneration.admin;
  const [data, setData] = useState<QuotaUserListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [page, setPage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 对话框状态
  const [dialogUserId, setDialogUserId] = useState<string | null>(null);
  const [dialogExisting, setDialogExisting] = useState<QuotaUser | null>(null);
  const [showGrantDialog, setShowGrantDialog] = useState(false);

  useEffect(() => {
    loadData();
  }, [page, search]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await listQuotaUsers(page * PAGE_SIZE, PAGE_SIZE, search || undefined);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : igT.loadFailed);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setSearch(searchInput);
    setPage(0);
  };

  const handleOpenGrantDialog = (user?: QuotaUser) => {
    if (user) {
      setDialogUserId(user.user_id);
      setDialogExisting(user);
    } else {
      // 新分配：需要 userId 输入
      const userId = prompt(igT.promptUserId);
      if (!userId) return;
      setDialogUserId(userId);
      setDialogExisting(null);
    }
    setShowGrantDialog(true);
  };

  const handleRevoke = async (userId: string) => {
    if (!confirm(igT.revokeConfirm.replace('{userId}', userId))) return;
    try {
      setMessage(null);
      await revokeQuota(userId);
      setMessage({ type: 'success', text: igT.granted });
      await loadData();
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : igT.revokeFailed });
    }
  };

  const handleReset = async (userId: string) => {
    if (!confirm(igT.resetConfirm.replace('{userId}', userId))) return;
    try {
      setMessage(null);
      await resetCounters(userId);
      setMessage({ type: 'success', text: igT.counterReset });
      await loadData();
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : igT.resetFailed });
    }
  };

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {message && (
        <div
          className={`px-4 py-3 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-500/10 border border-green-500 text-green-400'
              : 'bg-red-500/10 border border-red-500 text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* 搜索栏 */}
      <div className="flex gap-3 items-center">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder={igT.enterUserId}
          className="flex-1 bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
        />
        <button
          onClick={handleSearch}
          className="bg-cyan-600 hover:bg-cyan-700 text-white px-6 py-2 rounded-lg transition-colors"
        >
          {igT.search}
        </button>
        <button
          onClick={() => handleOpenGrantDialog()}
          className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg transition-colors"
        >
          {igT.grantQuota}
        </button>
      </div>

      {/* 表格 */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-700">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300">{igT.userId}</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300">
                  {igT.dailyQuota}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300">
                  {igT.monthlyQuota}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300">{igT.validity}</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300">{igT.status}</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300">
                  {igT.notes}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300">{igT.actions}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                    {igT.loading}
                  </td>
                </tr>
              ) : !data || data.items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                    {igT.noData}
                  </td>
                </tr>
              ) : (
                data.items.map((user) => (
                  <tr key={user.user_id} className="hover:bg-slate-700/50">
                    <td className="px-4 py-3 text-sm text-white font-mono">{user.user_id}</td>
                    <td className="px-4 py-3 text-sm">
                      <div className="text-white">
                        {user.daily_used} / {user.daily_limit}
                      </div>
                      <div className="text-xs text-slate-400">
                        {t.imageGeneration.quota.remaining.replace('{count}', String(user.daily_remaining))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="text-white">
                        {user.monthly_used} / {user.monthly_limit}
                      </div>
                      <div className="text-xs text-slate-400">
                        {t.imageGeneration.quota.remaining.replace('{count}', String(user.monthly_remaining))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-300">
                      {user.valid_from ? (
                        <div>{new Date(user.valid_from).toLocaleDateString()}</div>
                      ) : (
                        <div className="text-slate-500">-</div>
                      )}
                      {user.valid_until ? (
                        <div>~ {new Date(user.valid_until).toLocaleDateString()}</div>
                      ) : (
                        <div className="text-slate-500">{igT.permanent}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {user.is_valid ? (
                        <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs">
                          {igT.valid}
                        </span>
                      ) : (
                        <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs">
                          {igT.invalid}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400 max-w-xs truncate">
                      {user.notes || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleOpenGrantDialog(user)}
                          className="text-cyan-400 hover:text-cyan-300 transition-colors"
                          title={igT.edit}
                        >
                          <i className="fas fa-edit"></i>
                        </button>
                        <button
                          onClick={() => handleReset(user.user_id)}
                          className="text-orange-400 hover:text-orange-300 transition-colors"
                          title={igT.resetCounters}
                        >
                          <i className="fas fa-redo"></i>
                        </button>
                        <button
                          onClick={() => handleRevoke(user.user_id)}
                          className="text-red-400 hover:text-red-300 transition-colors"
                          title={igT.revokeQuota}
                        >
                          <i className="fas fa-trash"></i>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 分页 */}
      {data && data.total > 0 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-slate-400">
            {t.imageGeneration.history.total
              .replace('{count}', String(data.total))
              .replace('{current}', String(page + 1))
              .replace('{total}', String(totalPages || 1))}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0 || loading}
              className="bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:cursor-not-allowed text-white px-4 py-2 rounded transition-colors"
            >
              {t.imageGeneration.history.prevPage}
            </button>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page + 1 >= totalPages || loading}
              className="bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:cursor-not-allowed text-white px-4 py-2 rounded transition-colors"
            >
              {t.imageGeneration.history.nextPage}
            </button>
          </div>
        </div>
      )}

      {/* 分配/编辑配额对话框 */}
      {showGrantDialog && dialogUserId && (
        <GrantQuotaDialog
          userId={dialogUserId}
          existing={dialogExisting}
          onClose={() => setShowGrantDialog(false)}
          onSuccess={() => {
            loadData();
          }}
        />
      )}
    </div>
  );
}