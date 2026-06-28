import { useState, useEffect, useCallback } from 'react';
import {
  getLoginStatus, getConfig, saveConfig,
  startLogin, startRush, stopRush,
  getStatus, getLogs, getPaymentInfo, closePaymentBrowser,
  getTasks, getTaskLogs, openBrowser,
  RusherConfig, LoginStatus, RusherStatus, RusherLog, PaymentInfo, TaskSummary,
} from '../../../api/glmCodingRusherApi';

const PHASE_LABELS: Record<string, string> = {
  idle: '待命',
  preheating: '预热中',
  refreshing: '刷新检测中',
  clicking: '正在点击',
  awaiting_payment: '等待支付',
  success: '抢购成功',
  failed: '已停止',
};

const PHASE_COLORS: Record<string, string> = {
  idle: 'bg-slate-600',
  preheating: 'bg-blue-500',
  refreshing: 'bg-yellow-500',
  clicking: 'bg-orange-500',
  awaiting_payment: 'bg-purple-500',
  success: 'bg-green-500',
  failed: 'bg-red-500',
};

export default function GlmCodingRusher() {
  const [loginStatus, setLoginStatus] = useState<LoginStatus | null>(null);
  const [config, setConfig] = useState<RusherConfig>({
    target_package: 'pro',
    sale_time: '10:00',
    preheat_seconds: 90,
    refresh_interval_ms: 500,
    timeout_seconds: 60,
    headless: false,
  });
  const [status, setStatus] = useState<RusherStatus>({
    is_running: false,
    current_phase: 'idle',
    message: '待命',
  });
  const [logs, setLogs] = useState<RusherLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paymentInfo, setPaymentInfo] = useState<PaymentInfo | null>(null);
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [justStarted, setJustStarted] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successPaymentUrl, setSuccessPaymentUrl] = useState<string | null>(null);
  const [openingBrowser, setOpeningBrowser] = useState(false);

  // 轮询状态和日志
  const poll = useCallback(async () => {
    try {
      const [s, l, ls, p] = await Promise.all([
        getStatus(), getLogs(), getLoginStatus(), getPaymentInfo(),
      ]);
      setStatus(s);
      setLogs(l.items);
      setLoginStatus(ls);
      setPaymentInfo(p);

      // 加载抢购记录
      try {
        const t = await getTasks();
        setTasks(t.items);
      } catch {
        // 忽略任务列表加载错误
      }

      // 轮询确认任务已启动 → 清除 justStarted
      if (justStarted && s.is_running) {
        setJustStarted(false);
      }

      // 检测抢购成功 → 弹窗 + 记录支付 URL
      if (s.current_phase === 'success' && !showSuccessModal) {
        setSuccessPaymentUrl(s.payment_url || null);
        setShowSuccessModal(true);
      }
    } catch {
      // 忽略轮询错误
    }
  }, [justStarted, showSuccessModal]);

  useEffect(() => {
    poll();
    // 成功弹窗中 → 暂停轮询；运行中 → 1s；空闲 → 5s
    const interval = showSuccessModal
      ? null
      : status.is_running || status.current_phase !== 'idle'
        ? 1000
        : 5000;
    if (interval === null) return;
    const timer = setInterval(poll, interval);
    return () => clearInterval(timer);
  }, [poll, showSuccessModal, status.is_running, status.current_phase]);

  // 加载配置
  useEffect(() => {
    getConfig().then(setConfig).catch(() => {});
  }, []);

  // 选中任务切换 → 从 DB 加载该任务完整日志
  useEffect(() => {
    if (!selectedTaskId) return;
    getTaskLogs(selectedTaskId).then((res) => setLogs(res.items)).catch(() => {});
  }, [selectedTaskId]);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await startLogin(false);
      if (!res.success) throw new Error(res.message);
      // 等待用户完成登录
      const checkTimer = setInterval(async () => {
        const ls = await getLoginStatus();
        setLoginStatus(ls);
        if (ls.logged_in) {
          clearInterval(checkTimer);
          setLoading(false);
        }
      }, 2000);
    } catch (e: any) {
      setError(e.message);
      setLoading(false);
    }
  };

  const handleSaveConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const updated = await saveConfig(config);
      setConfig(updated);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    setJustStarted(true);
    try {
      const res = await startRush();
      if (!res.success) {
        throw new Error(res.message);
      }
      // 保持 justStarted=true，等轮询确认 is_running 后再清除
    } catch (e: any) {
      setError(e.message);
      setJustStarted(false);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await stopRush();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClosePayment = async () => {
    try {
      const res = await closePaymentBrowser();
      if (res.success) {
        await poll(); // 刷新状态
      } else {
        setError(res.message);
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleOpenBrowser = async () => {
    setOpeningBrowser(true);
    setError(null);
    try {
      const res = await openBrowser();
      if (!res.success) {
        setError(res.message);
        // 登录态失效 → 刷新登录状态
        const ls = await getLoginStatus();
        setLoginStatus(ls);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setOpeningBrowser(false);
    }
  };

  const openPaymentWindow = (url?: string | null) => {
    if (!url) {
      return;
    }
    window.open(url, '_blank');
  };

  // 倒计时格式化
  const formatCountdown = (seconds?: number) => {
    if (seconds === undefined || seconds <= 0) return '00:00:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 标题 */}
        <div className="flex items-center gap-3 mb-6">
          <i className="fas fa-bolt text-amber-500 text-2xl" />
          <h1 className="text-2xl font-bold">GLM-Coding Pro 抢购</h1>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* 左右布局：桌面端两列，移动端堆叠 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 左侧：信息区 */}
          <div className="space-y-6">
            {/* 登录状态卡片 */}
            <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold mb-2">登录状态</h2>
                  <p className="text-slate-400 text-sm">
                    {loginStatus?.logged_in ? '✅ 已登录' : '❌ 未登录'}
                  </p>
                  {loginStatus?.message && (
                    <p className="text-slate-500 text-xs mt-1">{loginStatus.message}</p>
                  )}
                </div>
                <button
                  onClick={handleOpenBrowser}
                  disabled={!loginStatus?.logged_in || openingBrowser}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-xs font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 shrink-0"
                >
                  {openingBrowser ? (
                    <>
                      <i className="fas fa-spinner fa-spin" />
                      打开中...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-external-link-alt" />
                      打开网站验证
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* 配置卡片 */}
            <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 space-y-4">
              <h2 className="text-lg font-semibold">抢购配置</h2>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-slate-400 block mb-1">开抢时间</label>
                  <input
                    type="text"
                    value={config.sale_time}
                    onChange={(e) => setConfig({ ...config, sale_time: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                    placeholder="10:00"
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-400 block mb-1">预热时间 (秒)</label>
                  <input
                    type="number"
                    value={config.preheat_seconds}
                    onChange={(e) => setConfig({ ...config, preheat_seconds: parseInt(e.target.value) || 90 })}
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-400 block mb-1">刷新间隔 (ms)</label>
                  <input
                    type="number"
                    value={config.refresh_interval_ms}
                    onChange={(e) => setConfig({ ...config, refresh_interval_ms: parseInt(e.target.value) || 500 })}
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-400 block mb-1">超时时间 (秒)</label>
                  <input
                    type="number"
                    value={config.timeout_seconds}
                    onChange={(e) => setConfig({ ...config, timeout_seconds: parseInt(e.target.value) || 60 })}
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <button
                onClick={handleSaveConfig}
                disabled={loading}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-sm font-medium disabled:opacity-50"
              >
                保存配置
              </button>
            </div>

            {/* 倒计时与状态卡片 */}
            <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">抢购状态</h2>
                <span className={`px-3 py-1 rounded-full text-xs font-medium text-white ${PHASE_COLORS[status.current_phase] || 'bg-slate-600'}`}>
                  {PHASE_LABELS[status.current_phase] || status.current_phase}
                </span>
              </div>

              <div className="text-center mb-4">
                <div className="text-slate-400 text-sm mb-1">下次开抢</div>
                <div className="text-2xl font-mono font-bold">{status.next_sale_time || '--'}</div>
                <div className="text-3xl font-mono text-amber-400 mt-2">
                  {formatCountdown(status.countdown_seconds)}
                </div>
              </div>

              <p className="text-sm text-slate-400 text-center mb-4">{status.message}</p>

              {status.last_error && (
                <p className="text-sm text-red-400 text-center mb-4">错误: {status.last_error}</p>
              )}

              {/* 支付信息卡片 */}
              {paymentInfo?.has_payment && (
                <div className="mt-4 p-4 bg-purple-500/10 border border-purple-500 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <i className="fas fa-credit-card text-purple-400" />
                    <span className="text-sm font-semibold text-purple-300">
                      {paymentInfo.browser_alive ? '支付窗口已打开' : '支付已结束'}
                    </span>
                  </div>
                  {paymentInfo.payment_url && (
                    <div className="text-xs text-slate-400 break-all mb-3">
                      {paymentInfo.payment_url}
                    </div>
                  )}
                  <div className="flex gap-2">
                    <button
                      onClick={() => openPaymentWindow(paymentInfo.payment_url)}
                      disabled={!paymentInfo.payment_url}
                      className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-xs disabled:opacity-50"
                    >
                      支付完成
                    </button>
                  </div>
                </div>
              )}

              <div className="flex justify-center gap-3">
                {justStarted ? (
                  <button
                    disabled
                    className="px-6 py-2 bg-amber-600/50 rounded-lg text-sm font-bold cursor-not-allowed"
                  >
                    <i className="fas fa-spinner fa-spin mr-2" />
                    抢购中...
                  </button>
                ) : status.is_running ? (
                  <button
                    onClick={handleStop}
                    disabled={loading}
                    className="px-6 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-bold disabled:opacity-50"
                  >
                    停止抢购
                  </button>
                ) : (
                  <button
                    onClick={handleStart}
                    disabled={!loginStatus?.logged_in || loading}
                    className="px-6 py-2 bg-amber-600 hover:bg-amber-700 rounded-lg text-sm font-bold disabled:opacity-50"
                  >
                    {status.current_phase === 'success' ? '再次抢购' : '开始抢购'}
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* 右侧：抢购记录 + 实时日志 */}
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 lg:sticky lg:top-6 lg:self-start lg:h-[calc(100vh-3rem)] lg:flex lg:flex-col">
            {/* 上半区：抢购记录 */}
            <div className="mb-4 shrink-0" style={{ maxHeight: '40%' }}>
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-lg font-semibold">
                  <i className="fas fa-clipboard-list text-amber-400 mr-2" />
                  抢购记录
                </h2>
                {selectedTaskId && (
                  <button
                    onClick={() => { setSelectedTaskId(null); }}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    显示全部日志
                  </button>
                )}
              </div>
              <div className="overflow-y-auto space-y-1" style={{ maxHeight: 'calc(40vh - 80px)' }}>
                {tasks.length === 0 ? (
                  <div className="text-slate-500 text-center py-4 text-sm">暂无记录</div>
                ) : (
                  tasks.map((task) => {
                    const RESULT_ICON: Record<string, string> = {
                      success: '✅',
                      timeout: '❌',
                      stopped: '⏹',
                      error: '💥',
                      running: '🔄',
                    };
                    const isSelected = task.id === selectedTaskId;
                    return (
                      <div
                        key={task.id}
                        onClick={() => setSelectedTaskId(isSelected ? null : task.id)}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-blue-600/20 border border-blue-500/40'
                            : 'bg-slate-900/50 hover:bg-slate-700/50 border border-transparent'
                        }`}
                      >
                        <span>{RESULT_ICON[task.result] || '❓'}</span>
                        <span className="text-slate-400 shrink-0">
                          {new Date(task.started_at).toLocaleString('zh-CN', {
                            month: '2-digit', day: '2-digit',
                            hour: '2-digit', minute: '2-digit',
                          })}
                        </span>
                        <span className="text-slate-300 truncate">
                          {task.target_package}
                        </span>
                        <span className="ml-auto text-slate-500 shrink-0">
                          {task.refresh_count}次刷新
                        </span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* 分割线 */}
            <div className="border-t border-slate-700 my-2 shrink-0" />

            {/* 下半区：实时日志 */}
            <div className="flex-1 flex flex-col min-h-0">
              <h2 className="text-lg font-semibold mb-2 shrink-0">
                <i className="fas fa-terminal text-green-400 mr-2" />
                实时日志
                {selectedTaskId && (
                  <span className="text-xs text-blue-400 font-normal ml-2">
                    (筛选中)
                  </span>
                )}
              </h2>
              <div className="bg-slate-900 rounded-lg p-4 overflow-y-auto font-mono text-xs space-y-1 flex-1 min-h-0">
                {logs.length === 0 ? (
                  <div className="text-slate-500 text-center py-8">暂无日志</div>
                ) : (
                  logs.map((log) => (
                    <div key={log.id} className="flex gap-2">
                      <span className="text-slate-500 shrink-0">
                        {new Date(log.created_at).toLocaleTimeString()}
                      </span>
                      <span className={`shrink-0 px-1.5 rounded ${PHASE_COLORS[log.phase] || 'bg-slate-600'} text-white text-[10px]`}>
                        {log.phase}
                      </span>
                      <span className="text-slate-300 break-all">{log.message}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 抢购成功弹窗 */}
      {showSuccessModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-2xl p-8 max-w-md w-full mx-4 border border-green-500/30 shadow-2xl">
            <div className="text-center mb-6">
              <div className="text-5xl mb-4">✅</div>
              <h2 className="text-2xl font-bold text-green-400">抢购成功！</h2>
              <p className="text-slate-400 mt-2">
                支付页面已打开，请在浏览器窗口中完成支付
              </p>
            </div>

            {successPaymentUrl && (
              <div className="bg-slate-900 rounded-lg p-3 mb-6">
                <div className="text-xs text-slate-500 mb-1">支付链接</div>
                <div className="text-sm text-slate-300 break-all font-mono">
                  {successPaymentUrl}
                </div>
              </div>
            )}

            <div className="flex gap-3">
              {successPaymentUrl && (
                <button
                  onClick={() => window.open(successPaymentUrl, '_blank')}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium"
                >
                  在浏览器中打开
                </button>
              )}
              <button
                onClick={() => {
                  setShowSuccessModal(false);
                  setSuccessPaymentUrl(null);
                }}
                className="flex-1 px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg text-sm font-medium"
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
