/**
 * 额度管理 Tab — 用户配额列表 + 分配/撤销/重置
 */
import { useState, useEffect, useCallback } from 'react';
import { quotaApi, QuotaInfo, GrantQuotaRequest } from '@/services/quotaApi';
import { useToast } from '@/hooks/useToast';
import { listUsers as fetchSystemUsers } from '@/api/adminApi';
import { UserResponse } from '@/api/authApi';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

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

  const handleGrant = async (data: GrantQuotaRequest & { _user_id?: string }) => {
    // 编辑模式用 grantTarget.user_id；新建模式用 modal 传入的 _user_id
    const uid = grantTarget?.user_id || data._user_id;
    if (!uid) {
      error('未指定用户');
      return;
    }
    try {
      await quotaApi.grant(uid, data);
      success(`已为用户 ${uid} 分配额度`);
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
          <span className="text-ink-muted">日: {info.daily_remaining}/{info.daily_limit ?? '-'}</span>
          <br />
          <span className="text-ink-muted">月: {info.monthly_remaining}/{info.monthly_limit ?? '-'}</span>
        </div>
      );
    }
    if (info.quota_mode === 'token') {
      return (
        <div className="text-xs text-ink-muted">
          Token: {info.token_remaining}/{info.token_limit ?? '-'}
          <br />
          <span className="text-ink-faint">({info.token_period ?? 'total'})</span>
        </div>
      );
    }
    return (
      <div className="text-xs text-ink-muted">
        {info.is_valid ? '有效期正常' : '已过期'}
      </div>
    );
  };

  return (
    <div>
      {/* 头部 */}
      <div className="flex justify-between items-center mb-4">
        <p className="text-ink-muted text-sm">管理用户 LLM 配额（次数/Token/时间三种模式）</p>
        <div className="flex items-center gap-2">
          <form onSubmit={handleSearch} className="flex gap-1">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索用户 ID..."
              className="px-3 py-1.5 bg-surface-1 text-ink text-sm rounded-lg border border-border focus:border-accent focus:outline-none w-48"
            />
            <Button type="submit" size="sm">
              搜索
            </Button>
          </form>
          <Button onClick={() => { setGrantTarget(null); setShowGrantModal(true); }} size="sm" className="flex items-center gap-2">
            <span>+</span><span>分配额度</span>
          </Button>
        </div>
      </div>

      {/* 列表 */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-accent-info"></div>
          <p className="text-ink-muted mt-2">加载中...</p>
        </div>
      ) : (
        <>
          {/* 统计条 */}
          <div className="flex gap-4 mb-4 text-xs text-ink-muted">
            <span>共 {totalCount} 个用户有配额</span>
          </div>

          {items.length === 0 ? (
            <Card className="bg-surface-2 p-12 text-center">
              <div className="text-6xl mb-4"></div>
              <h3 className="text-lg font-medium text-ink mb-2">暂无配额记录</h3>
              <p className="text-ink-muted mb-4">点击「分配额度」为用户创建配额</p>
            </Card>
          ) : (
            <Card className="bg-surface-2 overflow-hidden p-0">
          <table className="w-full">
            <thead className="bg-surface-1">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">用户</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">模式</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">余额</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">状态</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">备注</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-ink-muted">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((info) => (
                <tr key={info.user_id} className="hover:bg-surface-3/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="text-ink font-medium text-sm truncate max-w-[200px]" title={info.user_id}>
                      {info.username || <span className="text-ink-muted">?</span>}
                    </div>
                    <div className="text-xs text-ink-faint font-mono truncate max-w-[200px]" title={info.user_id}>
                      {info.user_id}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={info.quota_mode === 'count' ? 'default' : info.quota_mode === 'token' ? 'default' : 'warning'}>
                      {getModeLabel(info.quota_mode)}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    {renderRemaining(info)}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={info.is_valid ? 'success' : 'destructive'}>
                      {info.is_valid ? '有效' : '失效'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-xs text-ink-faint truncate max-w-[200px]" title={info.notes || undefined}>
                      {info.notes || '-'}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        onClick={() => { setGrantTarget(info); setShowGrantModal(true); }}
                        className="px-2 py-1 text-xs bg-accent/20 text-accent border border-accent/30 rounded hover:bg-accent/30 transition-colors"
                      >
                        改额度
                      </button>
                      <button
                        onClick={() => handleReset(info.user_id)}
                        disabled={resettingId === info.user_id}
                        className="px-2 py-1 text-xs bg-warning/20 text-accent-warning border border-warning/30 rounded hover:bg-warning/30 transition-colors disabled:opacity-50"
                      >
                        {resettingId === info.user_id ? '重置中...' : '重置'}
                      </button>
                      <button
                        onClick={() => handleRevoke(info.user_id)}
                        disabled={deletingId === info.user_id}
                        className="px-2 py-1 text-xs bg-danger/20 text-danger border border-danger/30 rounded hover:bg-danger/30 transition-colors disabled:opacity-50"
                      >
                        {deletingId === info.user_id ? '撤销中...' : '撤销'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
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
  const [selectedUser, setSelectedUser] = useState<UserResponse | null>(null);
  const [quotaMode, setQuotaMode] = useState<string>(currentQuota?.quota_mode || 'count');
  const [dailyLimit, setDailyLimit] = useState<string>(currentQuota?.daily_limit?.toString() || '');
  const [monthlyLimit, setMonthlyLimit] = useState<string>(currentQuota?.monthly_limit?.toString() || '');
  const [tokenLimit, setTokenLimit] = useState<string>(currentQuota?.token_limit?.toString() || '');
  const [tokenPeriod, setTokenPeriod] = useState<string>(currentQuota?.token_period || 'daily');
  const [validFrom, setValidFrom] = useState<string>(
    currentQuota?.valid_from ? currentQuota.valid_from.slice(0, 16) : ''
  );
  const [validUntil, setValidUntil] = useState<string>(
    currentQuota?.valid_until ? currentQuota.valid_until.slice(0, 16) : ''
  );
  // 永久有效：勾选后跳过两个时间字段（time 模式允许两个都为 null）
  const [permanent, setPermanent] = useState<boolean>(
    !currentQuota?.valid_from && !currentQuota?.valid_until
  );
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // 用户列表
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [userSearch, setUserSearch] = useState('');
  const [showUserPicker, setShowUserPicker] = useState(false);

  useEffect(() => {
    if (targetUser && !selectedUser) {
      // 编辑模式：从已有数据反查用户信息（尽力而为，找不到就只显示 id）
      setSelectedUser({ user_id: targetUser, username: '(已存在用户)', email: '', role: '' } as UserResponse);
    }
    if (!isOpen) {
      setSelectedUser(null);
      setShowUserPicker(false);
      setUserSearch('');
    }
  }, [targetUser, isOpen]);

  // 打开弹窗且未选用户时加载系统用户
  useEffect(() => {
    if (isOpen && !selectedUser && users.length === 0) {
      loadUsers('');
    }
  }, [isOpen]);

  const loadUsers = async (search: string) => {
    setUsersLoading(true);
    try {
      const data = await fetchSystemUsers({ page: 1, page_size: 50, search: search || undefined });
      setUsers(data.users || []);
    } catch {
      // 静默失败，UI 上显示空列表
    }
    setUsersLoading(false);
  };

  const handleUserSearch = (val: string) => {
    setUserSearch(val);
    loadUsers(val);
  };

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) {
      alert('请先选择用户');
      return;
    }

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
    } else if (quotaMode === 'time') {
      if (permanent) {
        // 永久有效：不发送 valid_from / valid_until
        data.valid_from = undefined;
        data.valid_until = undefined;
      } else {
        data.valid_from = validFrom ? new Date(validFrom).toISOString() : undefined;
        data.valid_until = validUntil ? new Date(validUntil).toISOString() : undefined;
        if (!data.valid_from && !data.valid_until) {
          alert('时间模式必须设置生效时间或过期时间，或勾选「永久有效」');
          return;
        }
      }
    }

    setSubmitting(true);
    // 把 user_id 注入到外层：外层通过 grantTarget 拿到
    onSubmit({ ...data, _user_id: selectedUser.user_id } as any);
    setSubmitting(false);
  };

  const isEditMode = !!currentQuota;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-surface-1 rounded-xl p-6 w-full max-w-md border border-border shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold text-ink mb-4">
          {currentQuota ? '修改配额' : '分配额度'}
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 用户选择器 */}
          <div>
            <label className="block text-sm text-ink-muted mb-1">用户</label>
            {isEditMode && selectedUser ? (
              <div className="flex items-center justify-between px-3 py-2 bg-surface-2 border border-border rounded-lg">
                <div>
                  <div className="text-ink text-sm font-medium">{selectedUser.username}</div>
                  <div className="text-xs text-ink-faint font-mono">{selectedUser.user_id}</div>
                </div>
                <span className="text-xs text-ink-faint">（已有配额，仅修改配置）</span>
              </div>
            ) : selectedUser ? (
              <div className="flex items-center justify-between px-3 py-2 bg-surface-2 border border-accent rounded-lg">
                <div>
                  <div className="text-ink text-sm font-medium">{selectedUser.username}</div>
                  <div className="text-xs text-ink-muted">{selectedUser.email} · {selectedUser.role}</div>
                  <div className="text-xs text-ink-faint font-mono">{selectedUser.user_id}</div>
                </div>
                <button
                  type="button"
                  onClick={() => setShowUserPicker(!showUserPicker)}
                  className="text-xs text-accent hover:text-accent"
                >
                  重新选择
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setShowUserPicker(true)}
                className="w-full px-3 py-2 bg-surface-2 text-ink-muted text-sm rounded-lg border border-border hover:border-accent hover:text-ink transition-colors text-left"
              >
                + 选择系统用户
              </button>
            )}

            {/* 用户选择下拉 */}
            {showUserPicker && !isEditMode && (
              <div className="mt-2 bg-surface-2 border border-border rounded-lg overflow-hidden">
                <input
                  type="text"
                  value={userSearch}
                  onChange={(e) => handleUserSearch(e.target.value)}
                  placeholder="搜索用户名/邮箱..."
                  className="w-full px-3 py-2 bg-surface-1 text-ink text-sm border-b border-border focus:outline-none focus:border-accent"
                  autoFocus
                />
                <div className="max-h-48 overflow-y-auto">
                  {usersLoading ? (
                    <div className="text-center py-4 text-ink-muted text-sm">加载中...</div>
                  ) : users.length === 0 ? (
                    <div className="text-center py-4 text-ink-muted text-sm">无匹配用户</div>
                  ) : (
                    users.map((u) => (
                      <button
                        key={u.user_id}
                        type="button"
                        onClick={() => { setSelectedUser(u); setShowUserPicker(false); }}
                        className="w-full px-3 py-2 text-left hover:bg-surface-3 transition-colors border-b border-border last:border-b-0"
                      >
                        <div className="text-ink text-sm">{u.username}</div>
                        <div className="text-xs text-ink-muted">{u.email} · {u.role}</div>
                        <div className="text-xs text-ink-faint font-mono">{u.user_id}</div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* 模式选择 */}
          <div>
            <label className="block text-sm text-ink-muted mb-1">配额模式</label>
            <div className="flex gap-1">
              {(['count', 'token', 'time'] as const).map((m) => (
                <Button
                  key={m}
                  type="button"
                  onClick={() => setQuotaMode(m)}
                  variant={quotaMode === m ? 'default' : 'secondary'}
                  className="flex-1"
                >
                  {m === 'count' ? '按次数' : m === 'token' ? '按 Token' : '按时间'}
                </Button>
              ))}
            </div>
          </div>

          {/* count 模式字段 */}
          {quotaMode === 'count' && (
            <>
              <div>
                <label className="block text-sm text-ink-muted mb-1">日限额</label>
                <input
                  type="number"
                  value={dailyLimit}
                  onChange={(e) => setDailyLimit(e.target.value)}
                  min={0}
                  className="w-full px-3 py-2 bg-surface-2 text-ink text-sm rounded-lg border border-border focus:border-accent focus:outline-none"
                  placeholder="每日最大次数"
                />
              </div>
              <div>
                <label className="block text-sm text-ink-muted mb-1">月限额</label>
                <input
                  type="number"
                  value={monthlyLimit}
                  onChange={(e) => setMonthlyLimit(e.target.value)}
                  min={0}
                  className="w-full px-3 py-2 bg-surface-2 text-ink text-sm rounded-lg border border-border focus:border-accent focus:outline-none"
                  placeholder="每月最大次数"
                />
              </div>
            </>
          )}

          {/* token 模式字段 */}
          {quotaMode === 'token' && (
            <>
              <div>
                <label className="block text-sm text-ink-muted mb-1">Token 限额</label>
                <input
                  type="number"
                  value={tokenLimit}
                  onChange={(e) => setTokenLimit(e.target.value)}
                  min={0}
                  className="w-full px-3 py-2 bg-surface-2 text-ink text-sm rounded-lg border border-border focus:border-accent focus:outline-none"
                  placeholder="Token 上限"
                />
              </div>
              <div>
                <label className="block text-sm text-ink-muted mb-1">Token 周期</label>
                <Select value={tokenPeriod} onValueChange={setTokenPeriod}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">每日</SelectItem>
                    <SelectItem value="monthly">每月</SelectItem>
                    <SelectItem value="total">总量</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </>
          )}

          {/* time 模式字段 */}
          {quotaMode === 'time' && (
            <>
              <div className="flex items-center gap-2 px-3 py-2 bg-surface-2 border border-border rounded-lg">
                <input
                  id="permanent-checkbox"
                  type="checkbox"
                  checked={permanent}
                  onChange={(e) => setPermanent(e.target.checked)}
                  className="w-4 h-4 accent-cyan-500"
                />
                <label htmlFor="permanent-checkbox" className="text-sm text-ink cursor-pointer select-none">
                  永久有效（不设置生效时间/过期时间）
                </label>
              </div>
              <div>
                <label className="block text-sm text-ink-muted mb-1">生效时间（可选）</label>
                <input
                  type="datetime-local"
                  value={validFrom}
                  disabled={permanent}
                  onChange={(e) => setValidFrom(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-2 text-ink text-sm rounded-lg border border-border focus:border-accent focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>
              <div>
                <label className="block text-sm text-ink-muted mb-1">过期时间（可选）</label>
                <input
                  type="datetime-local"
                  value={validUntil}
                  disabled={permanent}
                  onChange={(e) => setValidUntil(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-2 text-ink text-sm rounded-lg border border-border focus:border-accent focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <p className="text-xs text-ink-faint mt-1">
                  {permanent
                    ? '已勾选「永久有效」，时间输入已禁用'
                    : '至少填一个；填了生效时间后未到时间会被拦截'}
                </p>
              </div>
            </>
          )}

          {/* 备注 */}
          <div>
            <label className="block text-sm text-ink-muted mb-1">备注（可选）</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full px-3 py-2 bg-surface-2 text-ink text-sm rounded-lg border border-border focus:border-accent focus:outline-none"
              placeholder="可选备注"
            />
          </div>

          {/* 按钮 */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-ink-muted hover:text-ink transition-colors"
            >
              取消
            </button>
            <Button type="submit" disabled={submitting} size="sm">
              {submitting ? '提交中...' : currentQuota ? '修改' : '分配'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
