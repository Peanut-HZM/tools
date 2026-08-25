/**
 * 额度管理 Tab — 用户配额列表 + 分配/撤销/重置
 */
import { useState, useEffect, useCallback } from 'react';
import { quotaApi, QuotaInfo, GrantQuotaRequest } from '@/services/quotaApi';
import { useToast } from '@/hooks/useToast';

export default function QuotaManagementTab() {
  const [items, setItems] = useState<QuotaInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [showGrantModal, setShowGrantModal] = useState(false);
  const [grantTarget, setGrantTarget] = useState<QuotaInfo | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [resettingId, setResettingId] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);

  const { success, error } = useToast();

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const result = await quotaApi.listUsers({ search: search || undefined });
      setItems(result.items);
      setTotalCount(result.count);
    } catch (err: any) {
      error(err?.response?.data?.detail || '加载配额列表失败');
      setItems([]);
      setTotalCount(0);
    } finally {
      setLoading(false);
    }
  }, [search, error]);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadUsers();
  };

  const handleGrant = async (data: GrantQuotaRequest) => {
    if (!grantTarget) return;
    try {
      await quotaApi.grant(grantTarget.user_id, data);
      success(`已为用户 ${grantTarget.user_id} 分配额度`);
      setShowGrantModal(false);
      setGrantTarget(null);
      loadUsers();
    } catch (err: any) {
      error(err?.response?.data?.detail || '分配额度失败');
    }
  };

  const handleRevoke = async (userId: string) => {
    if (!confirm(`确定撤销用户 ${userId} 的配额？`)) return;
    setDeletingId(userId);
    try {
      await quotaApi.revoke(userId);
      success('配额已撤销');
      loadUsers();
    } catch (err: any) {
      error(err?.response?.data?.detail || '撤销失败');
    }
    setDeletingId(null);
  };

  const handleReset = async (userId: string) => {
    setResettingId(userId);
    try {
      await quotaApi.reset(userId);
      success('计数器已重置');
      loadUsers();
    } catch (err: any) {
      error(err?.response?.data?.detail || '重置失败');
    }
    setResettingId(null);
  };

  const getModeLabel = (mode: string) => {
    const labels: Record<string, string> = { count: '按次数', token: '按 Token', time: '按时间' };
    return labels[mode] || mode;
  };

  const renderRemaining = (info: QuotaInfo) => {
    if (info.quota_mode === 'count') {
      return (
        <div className="text-xs space-y-0.5">
          <span className="text-slate-300">日: {info.daily_remaining}/{info.daily_limit ?? '-'}</span>
          <br />
          <span className="text-slate-300">月: {info.monthly_remaining}/{info.monthly_limit ?? '-'}</span>
        </div>
      );
    }
    if (info.quota_mode === 'token') {
      return (
        <div className="text-xs text-slate-300">
          Token: {info.token_remaining}/{info.token_limit ?? '-'}
          <br />
          <span className="text-slate-500">({info.token_period ?? 'total'})</span>
        </div>
      );
    }
    return (
      <div className="text-xs text-slate-300">
        {info.is_valid ? '有效期正常' : '已过期'}
      </div>
    );
  };

  return (
    <div>
      {/* 头部 */}
      <div className="flex justify-between items-center mb-4">
        <p className="text-slate-400 text-sm">管理用户 LLM 配额（次数/Token/时间三种模式）</p>
        <div className="flex items-center gap-2">
          <form onSubmit={handleSearch} className="flex gap-1">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索用户 ID..."
              className="px-3 py-1.5 bg-slate-800 text-white text-sm rounded-lg border border-slate-600 focus:border-cyan-500 focus:outline-none w-48"
            />
            <button
              type="submit"
              className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors text-sm"
            >
              搜索
            </button>
          </form>
          <button
            onClick={() => { setGrantTarget(null); setShowGrantModal(true); }}
            className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors flex items-center gap-2 text-sm"
          >
            <span>+</span><span>分配额度</span>
          </button>
        </div>
      </div>

      {/* 列表 */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
          <p className="text-slate-400 mt-2">加载中...</p>
        </div>
      ) : (
        <>
          {/* 统计条 */}
          <div className="flex gap-4 mb-4 text-xs text-slate-400">
            <span>共 {totalCount} 个用户有配额</span>
          </div>

          {items.length === 0 ? (
            <div className="bg-slate-700 rounded-lg p-12 text-center border border-slate-600">
              <div className="text-6xl mb-4"></div>
              <h3 className="text-lg font-medium text-white mb-2">暂无配额记录</h3>
              <p className="text-slate-400 mb-4">点击「分配额度」为用户创建配额</p>
            </div>
          ) : (
            <div className="bg-slate-700 rounded-lg border border-slate-600 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-800">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">用户</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">模式</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">余额</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">状态</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">备注</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-600">
              {items.map((info) => (
                <tr key={info.user_id} className="hover:bg-slate-600/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="text-white font-medium text-sm truncate max-w-[200px]" title={info.user_id}>
                      {info.username || <span className="text-slate-400">?</span>}
                    </div>
                    <div className="text-xs text-slate-500 font-mono truncate max-w-[200px]" title={info.user_id}>
                      {info.user_id}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                      info.quota_mode === 'count'
                        ? 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                        : info.quota_mode === 'token'
                        ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
                        : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                    }`}>
                      {getModeLabel(info.quota_mode)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {renderRemaining(info)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      info.is_valid
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {info.is_valid ? '有效' : '失效'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-xs text-slate-500 truncate max-w-[200px]" title={info.notes || undefined}>
                      {info.notes || '-'}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        onClick={() => { setGrantTarget(info); setShowGrantModal(true); }}
                        className="px-2 py-1 text-xs bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 rounded hover:bg-cyan-600/30 transition-colors"
                      >
                        改额度
                      </button>
                      <button
                        onClick={() => handleReset(info.user_id)}
                        disabled={resettingId === info.user_id}
                        className="px-2 py-1 text-xs bg-yellow-600/20 text-yellow-400 border border-yellow-500/30 rounded hover:bg-yellow-600/30 transition-colors disabled:opacity-50"
                      >
                        {resettingId === info.user_id ? '重置中...' : '重置'}
                      </button>
                      <button
                        onClick={() => handleRevoke(info.user_id)}
                        disabled={deletingId === info.user_id}
                        className="px-2 py-1 text-xs bg-red-600/20 text-red-400 border border-red-500/30 rounded hover:bg-red-600/30 transition-colors disabled:opacity-50"
                      >
                        {deletingId === info.user_id ? '撤销中...' : '撤销'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
          )}
        </>
      )}

      {/* 分配/修改额度弹窗 */}
      {showGrantModal && (
        <GrantModal
          isOpen={showGrantModal}
          onClose={() => { setShowGrantModal(false); setGrantTarget(null); }}
          onSubmit={handleGrant}
          targetUser={grantTarget?.user_id || null}
          currentQuota={grantTarget}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------
 * 分配额度弹窗
 * ------------------------------------------------------------------ */

function GrantModal({
  isOpen,
  onClose,
  onSubmit,
  targetUser,
  currentQuota,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: GrantQuotaRequest) => void;
  targetUser: string | null;
  currentQuota: QuotaInfo | null;
}) {
  const [userId, setUserId] = useState(targetUser || '');
  const [quotaMode, setQuotaMode] = useState<string>(currentQuota?.quota_mode || 'count');
  const [dailyLimit, setDailyLimit] = useState<string>(currentQuota?.daily_limit?.toString() || '');
  const [monthlyLimit, setMonthlyLimit] = useState<string>(currentQuota?.monthly_limit?.toString() || '');
  const [tokenLimit, setTokenLimit] = useState<string>(currentQuota?.token_limit?.toString() || '');
  const [tokenPeriod, setTokenPeriod] = useState<string>(currentQuota?.token_period || 'daily');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (targetUser) setUserId(targetUser);
  }, [targetUser]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId.trim()) return;

    const data: GrantQuotaRequest = {
      quota_mode: quotaMode,
      notes: notes || undefined,
    };

    if (quotaMode === 'count') {
      data.daily_limit = dailyLimit ? parseInt(dailyLimit) : undefined;
      data.monthly_limit = monthlyLimit ? parseInt(monthlyLimit) : undefined;
      if (!data.daily_limit && !data.monthly_limit) {
        alert('次数模式必须设置日限额或月限额');
        return;
      }
    } else if (quotaMode === 'token') {
      data.token_limit = tokenLimit ? parseInt(tokenLimit) : undefined;
      data.token_period = tokenPeriod;
      if (!data.token_limit) {
        alert('Token 模式必须设置 Token 限额');
        return;
      }
    }

    setSubmitting(true);
    onSubmit(data);
    setSubmitting(false);
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-slate-800 rounded-xl p-6 w-full max-w-md border border-slate-600 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold text-white mb-4">
          {currentQuota ? '修改配额' : '分配额度'}
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 用户 ID */}
          <div>
            <label className="block text-sm text-slate-300 mb-1">用户 ID</label>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              disabled={!!currentQuota}
              className="w-full px-3 py-2 bg-slate-700 text-white text-sm rounded-lg border border-slate-600 focus:border-cyan-500 focus:outline-none disabled:opacity-50 font-mono"
              placeholder="输入用户 ID"
            />
          </div>

          {/* 模式选择 */}
          <div>
            <label className="block text-sm text-slate-300 mb-1">配额模式</label>
            <div className="flex gap-1">
              {(['count', 'token', 'time'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setQuotaMode(m)}
                  className={`flex-1 py-2 text-sm rounded-lg transition-colors ${
                    quotaMode === m
                      ? 'bg-cyan-600 text-white'
                      : 'bg-slate-700 text-slate-300 border border-slate-600 hover:bg-slate-600'
                  }`}
                >
                  {m === 'count' ? '按次数' : m === 'token' ? '按 Token' : '按时间'}
                </button>
              ))}
            </div>
          </div>

          {/* count 模式字段 */}
          {quotaMode === 'count' && (
            <>
              <div>
                <label className="block text-sm text-slate-300 mb-1">日限额</label>
                <input
                  type="number"
                  value={dailyLimit}
                  onChange={(e) => setDailyLimit(e.target.value)}
                  min={0}
                  className="w-full px-3 py-2 bg-slate-700 text-white text-sm rounded-lg border border-slate-600 focus:border-cyan-500 focus:outline-none"
                  placeholder="每日最大次数"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-1">月限额</label>
                <input
                  type="number"
                  value={monthlyLimit}
                  onChange={(e) => setMonthlyLimit(e.target.value)}
                  min={0}
                  className="w-full px-3 py-2 bg-slate-700 text-white text-sm rounded-lg border border-slate-600 focus:border-cyan-500 focus:outline-none"
                  placeholder="每月最大次数"
                />
              </div>
            </>
          )}

          {/* token 模式字段 */}
          {quotaMode === 'token' && (
            <>
              <div>
                <label className="block text-sm text-slate-300 mb-1">Token 限额</label>
                <input
                  type="number"
                  value={tokenLimit}
                  onChange={(e) => setTokenLimit(e.target.value)}
                  min={0}
                  className="w-full px-3 py-2 bg-slate-700 text-white text-sm rounded-lg border border-slate-600 focus:border-cyan-500 focus:outline-none"
                  placeholder="Token 上限"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-1">Token 周期</label>
                <select
                  value={tokenPeriod}
                  onChange={(e) => setTokenPeriod(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700 text-white text-sm rounded-lg border border-slate-600 focus:border-cyan-500 focus:outline-none"
                >
                  <option value="daily">每日</option>
                  <option value="monthly">每月</option>
                  <option value="total">总量</option>
                </select>
              </div>
            </>
          )}

          {/* time 模式字段 */}
          {quotaMode === 'time' && (
            <p className="text-sm text-slate-400">
              时间模式通过有效起止时间控制，暂不支持前端配置。请联系管理员在数据库设置。
            </p>
          )}

          {/* 备注 */}
          <div>
            <label className="block text-sm text-slate-300 mb-1">备注（可选）</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 text-white text-sm rounded-lg border border-slate-600 focus:border-cyan-500 focus:outline-none"
              placeholder="可选备注"
            />
          </div>

          {/* 按钮 */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-300 hover:text-white transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
            >
              {submitting ? '提交中...' : currentQuota ? '修改' : '分配'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
