import { useState, useEffect, useCallback } from 'react';
import {
  getLoginStatus, getConfig, saveConfig,
  startLogin, startRush, stopRush,
  getStatus, getLogs,
  RusherConfig, LoginStatus, RusherStatus, RusherLog,
} from '../../../api/glmCodingRusherApi';

const PHASE_LABELS: Record<string, string> = {
  idle: '待命',
  preheating: '预热中',
  refreshing: '刷新检测中',
  clicking: '正在点击',
  success: '抢购成功',
  failed: '已停止',
};

const PHASE_COLORS: Record<string, string> = {
  idle: 'bg-slate-600',
  preheating: 'bg-blue-500',
  refreshing: 'bg-yellow-500',
  clicking: 'bg-orange-500',
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

  // 轮询状态和日志
  const poll = useCallback(async () => {
    try {
      const [s, l, ls] = await Promise.all([getStatus(), getLogs(), getLoginStatus()]);
      setStatus(s);
      setLogs(l.items);
      setLoginStatus(ls);
    } catch {
      // 忽略轮询错误
    }
  }, []);

  useEffect(() => {
    poll();
    const timer = setInterval(poll, 1000);
    return () => clearInterval(timer);
  }, [poll]);

  // 加载配置
  useEffect(() => {
    getConfig().then(setConfig).catch(() => {});
  }, []);

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
    try {
      const res = await startRush();
      if (!res.success) throw new Error(res.message);
    } catch (e: any) {
      setError(e.message);
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
                  onClick={handleLogin}
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium disabled:opacity-50"
                >
                  {loginStatus?.logged_in ? '重新登录' : '打开登录窗口'}
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

              <div className="flex justify-center gap-3">
                {!status.is_running ? (
                  <button
                    onClick={handleStart}
                    disabled={!loginStatus?.logged_in || loading}
                    className="px-6 py-2 bg-amber-600 hover:bg-amber-700 rounded-lg text-sm font-bold disabled:opacity-50"
                  >
                    开始抢购
                  </button>
                ) : (
                  <button
                    onClick={handleStop}
                    disabled={loading}
                    className="px-6 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-bold disabled:opacity-50"
                  >
                    停止抢购
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* 右侧：实时日志区 */}
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 lg:sticky lg:top-6 lg:self-start lg:h-[calc(100vh-3rem)] lg:flex lg:flex-col">
            <h2 className="text-lg font-semibold mb-4">实时日志</h2>
            <div className="bg-slate-900 rounded-lg p-4 overflow-y-auto font-mono text-xs space-y-1 flex-1 min-h-[400px] lg:min-h-0">
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
  );
}
